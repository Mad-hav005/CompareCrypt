"""
API routes for the Entity Resolution subsystem.

Endpoints:
  POST /api/er/upload/{party}      — Upload a dataset (CSV/XLSX) for party A or B
  POST /api/er/start               — Start ER job (background)
  GET  /api/er/status/{job_id}     — Poll job status
  GET  /api/er/results/{job_id}    — Paginated results
  GET  /api/er/export/{job_id}     — Export results as CSV download
  POST /api/er/new                 — Create a blank job (returns job_id)
"""

from __future__ import annotations

import asyncio
import csv
import io
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.entity_resolution.dataset_parser import parse_file_bytes
from app.entity_resolution.er_service import get_er_results, run_er_job
from app.entity_resolution.job_manager import job_manager
from app.models.er_schemas import (
    ERJobPhase,
    ERJobStatus,
    ERJobResults,
    StartERJobRequest,
    UploadDatasetResponse,
)

router = APIRouter(prefix="/api/er", tags=["Entity Resolution"])


@router.post(
    "/new",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new entity resolution job",
)
async def create_job() -> dict:
    """Create a blank ER job and return its job_id."""
    job = await job_manager.create_job()
    return {"job_id": job.job_id}


@router.post(
    "/upload/{party}",
    response_model=UploadDatasetResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a dataset (CSV or XLSX) for Party A or B",
)
async def upload_dataset(
    party: str,
    job_id: str = Form(..., description="Job ID to associate this upload with"),
    file: UploadFile = File(..., description="CSV or XLSX dataset file"),
) -> UploadDatasetResponse:
    """
    Upload a dataset file for the specified party ('A' or 'B').
    Returns a schema preview including columns and sample values.
    """
    party = party.upper()
    if party not in ("A", "B"):
        raise HTTPException(status_code=400, detail="Party must be 'A' or 'B'.")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no name.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        rows, schema = parse_file_bytes(raw_bytes, file.filename, party)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse file '{file.filename}': {exc!s}",
        ) from exc

    job = await job_manager.get_or_create_job(job_id)
    if party == "A":
        job.rows_a = rows
        job.schema_a = schema
    else:
        job.rows_b = rows
        job.schema_b = schema

    return UploadDatasetResponse(job_id=job_id, party=party, dataset_schema=schema)


@router.post(
    "/start",
    response_model=ERJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start entity resolution matching",
)
async def start_er_job(request: StartERJobRequest, background_tasks: BackgroundTasks) -> ERJobStatus:
    """
    Start a background entity resolution job for a previously uploaded dataset pair.
    Returns immediately with job status. Poll /api/er/status/{job_id} for progress.
    """
    job = await job_manager.get_job(request.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{request.job_id}' not found. Upload datasets first.")

    if job.rows_a is None:
        raise HTTPException(status_code=422, detail="Dataset A has not been uploaded yet.")
    if job.rows_b is None:
        raise HTTPException(status_code=422, detail="Dataset B has not been uploaded yet.")

    if job.phase not in (ERJobPhase.QUEUED, ERJobPhase.ERROR):
        # Allow restart after error; otherwise block re-run of in-progress/completed jobs
        if job.phase == ERJobPhase.COMPLETE:
            raise HTTPException(status_code=409, detail="Job already completed. Create a new job to run again.")
        if job.phase != ERJobPhase.ERROR:
            raise HTTPException(status_code=409, detail=f"Job is already in phase '{job.phase}'.")

    # Reset state for a fresh run (handles error-restart case)
    job.results = []
    job.processed_pairs = 0
    job.match_count = 0
    job.candidate_pairs = 0
    job.error_message = None
    job.started_at = None
    job.finished_at = None
    job.phase = ERJobPhase.QUEUED

    background_tasks.add_task(run_er_job, job, request)

    return job.to_status()


@router.get(
    "/status/{job_id}",
    response_model=ERJobStatus,
    status_code=status.HTTP_200_OK,
    summary="Poll entity resolution job status",
)
async def get_job_status(job_id: str) -> ERJobStatus:
    """Poll the current status and progress of an ER job."""
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return job.to_status()


@router.get(
    "/results/{job_id}",
    response_model=ERJobResults,
    status_code=status.HTTP_200_OK,
    summary="Get paginated entity resolution results",
)
async def get_results(
    job_id: str,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "overall_score",
    sort_desc: bool = True,
    min_score: Optional[float] = None,
) -> ERJobResults:
    """
    Returns paginated, sortable, filterable entity resolution results.
    Only completed jobs can be queried.
    """
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.phase == ERJobPhase.ERROR:
        raise HTTPException(status_code=500, detail=f"Job failed: {job.error_message}")
    if job.phase != ERJobPhase.COMPLETE:
        raise HTTPException(status_code=202, detail=f"Job is still running (phase: {job.phase}).")

    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if not (1 <= page_size <= 500):
        raise HTTPException(status_code=400, detail="page_size must be between 1 and 500")

    return await get_er_results(
        job,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc,
        min_score=min_score,
    )


@router.get(
    "/export/{job_id}",
    summary="Export entity resolution results as CSV",
    response_class=StreamingResponse,
)
async def export_results(job_id: str) -> StreamingResponse:
    """
    Stream all matched results as a CSV file download.
    """
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.phase != ERJobPhase.COMPLETE:
        raise HTTPException(status_code=409, detail="Job is not yet complete.")

    results = sorted(job.results, key=lambda r: r.overall_score, reverse=True)

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)

        # Header: metadata + attribute columns
        if results:
            attr_headers = [
                f"{a.column_a}/{a.column_b} ({a.strategy})"
                for a in results[0].attribute_scores
            ]
        else:
            attr_headers = []

        writer.writerow(
            ["row_a", "row_b", "overall_score"]
            + attr_headers
            + ["preview_a", "preview_b"]
        )
        yield buf.getvalue()
        buf.truncate(0)
        buf.seek(0)

        for r in results:
            attr_scores = [
                f"{a.score:.4f}" if a.score is not None else "ignored"
                for a in r.attribute_scores
            ]
            preview_a = " | ".join(f"{k}={v}" for k, v in r.row_a_preview.items())
            preview_b = " | ".join(f"{k}={v}" for k, v in r.row_b_preview.items())
            writer.writerow(
                [r.row_index_a, r.row_index_b, f"{r.overall_score:.4f}"]
                + attr_scores
                + [preview_a, preview_b]
            )
            yield buf.getvalue()
            buf.truncate(0)
            buf.seek(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="er_results_{job_id}.csv"'},
    )
