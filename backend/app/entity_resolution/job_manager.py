"""
In-memory job manager for entity resolution jobs.

Each job stores:
- Uploaded datasets (rows A and B, schemas)
- Job configuration
- Job status
- Job results (after completion)

Uses asyncio.Lock for thread-safe updates inside a single FastAPI process.
For production deployment, this would be replaced with a Redis/Celery
or database-backed implementation.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Dict, List, Optional

from app.models.er_schemas import (
    DatasetSchema,
    EntityMatchResult,
    ERJobPhase,
    ERJobStatus,
)


class ERJobState:
    """Mutable state for a single entity resolution job."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self.created_at = time.time()

        # Uploaded data (populated incrementally as parties upload)
        self.rows_a: Optional[List[Dict]] = None
        self.rows_b: Optional[List[Dict]] = None
        self.schema_a: Optional[DatasetSchema] = None
        self.schema_b: Optional[DatasetSchema] = None

        # Job status
        self.phase: ERJobPhase = ERJobPhase.QUEUED
        self.progress_pct: float = 0.0
        self.candidate_pairs: int = 0
        self.processed_pairs: int = 0
        self.match_count: int = 0
        self.error_message: Optional[str] = None
        self.started_at: Optional[float] = None
        self.finished_at: Optional[float] = None

        # Results
        self.results: List[EntityMatchResult] = []
        self.overall_threshold: float = 0.75
        self.candidate_pairs_evaluated: int = 0
        self.blocking_note: str = ""

    def elapsed_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at or time.time()
        return (end - self.started_at) * 1000.0

    def to_status(self) -> ERJobStatus:
        return ERJobStatus(
            job_id=self.job_id,
            phase=self.phase,
            progress_pct=self.progress_pct,
            candidate_pairs=self.candidate_pairs,
            processed_pairs=self.processed_pairs,
            match_count=self.match_count,
            error_message=self.error_message,
            elapsed_ms=self.elapsed_ms(),
        )


class JobManager:
    """
    Thread-safe in-memory store of ERJobState instances.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, ERJobState] = {}
        self._lock = asyncio.Lock()

    def generate_job_id(self) -> str:
        return uuid.uuid4().hex[:16]

    async def create_job(self, job_id: Optional[str] = None) -> ERJobState:
        async with self._lock:
            jid = job_id or self.generate_job_id()
            state = ERJobState(jid)
            self._jobs[jid] = state
            return state

    async def get_job(self, job_id: str) -> Optional[ERJobState]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def get_or_create_job(self, job_id: str) -> ERJobState:
        async with self._lock:
            if job_id not in self._jobs:
                self._jobs[job_id] = ERJobState(job_id)
            return self._jobs[job_id]

    async def update_phase(self, job_id: str, phase: ERJobPhase, progress: float = 0.0) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.phase = phase
                job.progress_pct = progress
                if phase == ERJobPhase.BLOCKING and job.started_at is None:
                    job.started_at = time.time()
                if phase in (ERJobPhase.COMPLETE, ERJobPhase.ERROR):
                    job.finished_at = time.time()

    async def update_progress(self, job_id: str, processed: int, matched: int, pct: float) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.processed_pairs = processed
                job.match_count = matched
                job.progress_pct = pct

    async def set_error(self, job_id: str, message: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.phase = ERJobPhase.ERROR
                job.error_message = message
                job.finished_at = time.time()


# Singleton instance used across the application
job_manager = JobManager()
