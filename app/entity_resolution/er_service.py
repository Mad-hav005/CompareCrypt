"""
Entity resolution service — orchestrates the full ER pipeline.

Pipeline
--------
1. Load datasets from job state (already parsed at upload time).
2. Identify blocking key (first non-ignored fuzzy or exact attribute mapping).
3. Generate candidate pairs via shingle-prefix blocking.
4. For each candidate pair, evaluate all attribute mappings using OPRF-based
   per-attribute matching (fuzzy → CryptographicThresholdPSI shingle matching,
   exact → OPRF exact PSI).
5. Compute weighted overall score and emit EntityMatchResult if >= overall_threshold.
6. Update job status throughout.

Batching
--------
Candidate pairs are evaluated in configurable batches. After each batch the
job status is updated so the frontend can poll for progress.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple

from app.entity_resolution.blocking import generate_candidate_pairs
from app.entity_resolution.job_manager import ERJobState, JobManager, job_manager
from app.entity_resolution.multi_attribute_matcher import MultiAttributeMatcher
from app.entity_resolution.weighted_scorer import build_match_result
from app.models.er_schemas import (
    AttributeMapping,
    EntityMatchResult,
    ERJobPhase,
    ERJobResults,
    MatchStrategy,
    StartERJobRequest,
)

BATCH_SIZE = 50  # pairs evaluated before yielding to the event loop


def _pick_blocking_key(
    mappings: List[AttributeMapping],
) -> Optional[Tuple[str, str]]:
    """
    Select the first non-ignored mapping's column pair as the blocking key.
    Prefer FUZZY over EXACT (bigram blocking works better on text columns).
    """
    fuzzy_col: Optional[Tuple[str, str]] = None
    exact_col: Optional[Tuple[str, str]] = None

    for m in mappings:
        if m.strategy == MatchStrategy.IGNORE:
            continue
        if m.strategy == MatchStrategy.FUZZY and fuzzy_col is None:
            fuzzy_col = (m.column_a, m.column_b)
        elif m.strategy == MatchStrategy.EXACT and exact_col is None:
            exact_col = (m.column_a, m.column_b)

    return fuzzy_col or exact_col


def _make_preview(row: Dict, columns: List[str]) -> Dict[str, str]:
    """Extract only the mapped columns for the result preview."""
    return {col: str(row.get(col, "")) for col in columns if col in row}


async def run_er_job(job: ERJobState, request: StartERJobRequest) -> None:
    """
    Run the entity resolution pipeline for a given job.
    Designed to be launched as a background task via asyncio.create_task().
    """
    try:
        job.overall_threshold = request.overall_threshold
        await job_manager.update_phase(job.job_id, ERJobPhase.BLOCKING, 0.0)

        rows_a = job.rows_a or []
        rows_b = job.rows_b or []

        if not rows_a or not rows_b:
            await job_manager.set_error(job.job_id, "Both datasets must be uploaded before starting.")
            return

        # ── 1. Select blocking key ──
        blocking_key = _pick_blocking_key(request.mappings)

        if blocking_key is None:
            await job_manager.set_error(job.job_id, "At least one non-ignored attribute mapping is required.")
            return

        bk_a, bk_b = blocking_key

        # ── 2. Generate candidate pairs ──
        candidates, blocking_applied, blocking_note = generate_candidate_pairs(
            rows_a, rows_b, bk_a, bk_b
        )
        total_candidates = len(candidates)

        async with asyncio.Lock():
            job.candidate_pairs = total_candidates
            job.blocking_note = blocking_note
            job.candidate_pairs_evaluated = total_candidates

        await job_manager.update_phase(job.job_id, ERJobPhase.MATCHING, 5.0)

        # ── 3. Per-attribute matching ──
        matcher = MultiAttributeMatcher(normalize=request.normalize)

        mappings = request.mappings
        columns_a = list({m.column_a for m in mappings if m.strategy != MatchStrategy.IGNORE})
        columns_b = list({m.column_b for m in mappings if m.strategy != MatchStrategy.IGNORE})

        # Precompute Alice's protected OPRF representations across candidate rows
        candidate_a_indices = {i for i, j in candidates}
        unique_candidate_rows_a = [rows_a[i] for i in candidate_a_indices]
        matcher.precompute_alice(unique_candidate_rows_a, mappings)

        results: List[EntityMatchResult] = []
        processed = 0
        matched = 0

        for batch_start in range(0, total_candidates, BATCH_SIZE):
            batch = candidates[batch_start : batch_start + BATCH_SIZE]

            for i, j in batch:
                row_a = rows_a[i]
                row_b = rows_b[j]

                attr_scores = matcher.evaluate_pair(
                    row_a, row_b, mappings, overall_threshold=request.overall_threshold
                )
                if attr_scores is None:
                    # Short-circuited: candidate cannot mathematically reach threshold
                    processed += 1
                    continue

                result = build_match_result(
                    row_index_a=i,
                    row_index_b=j,
                    attribute_scores=attr_scores,
                    overall_threshold=request.overall_threshold,
                    row_a_preview=_make_preview(row_a, columns_a),
                    row_b_preview=_make_preview(row_b, columns_b),
                )
                if result is not None:
                    results.append(result)
                    matched += 1
                processed += 1

            pct = 5.0 + 90.0 * (processed / max(total_candidates, 1))
            await job_manager.update_progress(job.job_id, processed, matched, pct)
            # Yield to event loop between batches to keep server responsive
            await asyncio.sleep(0)

        # ── 4. Finalize ──
        async with asyncio.Lock():
            job.results = results
            job.phase = ERJobPhase.SCORING
            job.matcher_stats = dict(matcher.stats)

        await job_manager.update_phase(job.job_id, ERJobPhase.COMPLETE, 100.0)

    except Exception as exc:  # noqa: BLE001
        await job_manager.set_error(job.job_id, f"ER job failed: {exc!s}")


async def get_er_results(
    job: ERJobState,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "overall_score",
    sort_desc: bool = True,
    min_score: Optional[float] = None,
) -> ERJobResults:
    """
    Return paginated, sorted, optionally filtered results.
    """
    results = list(job.results)

    # Filter
    if min_score is not None:
        results = [r for r in results if r.overall_score >= min_score]

    # Sort
    reverse = sort_desc
    if sort_by == "overall_score":
        results.sort(key=lambda r: r.overall_score, reverse=reverse)
    elif sort_by == "row_index_a":
        results.sort(key=lambda r: r.row_index_a, reverse=reverse)
    elif sort_by == "row_index_b":
        results.sort(key=lambda r: r.row_index_b, reverse=reverse)

    total = len(results)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    page_results = results[start : start + page_size]

    size_a = len(job.rows_a) if job.rows_a else 0
    size_b = len(job.rows_b) if job.rows_b else 0
    matched_a = {r.row_index_a for r in job.results}
    matched_b = {r.row_index_b for r in job.results}
    unmatched_a = size_a - len(matched_a)
    unmatched_b = size_b - len(matched_b)

    privacy_note = (
        "Privacy note: Fuzzy attributes use 2Hash-DH OPRF (RFC 3526 2048-bit MODP Group 14, "
        "Sørensen-Dice over unique character bigram shingles). "
        "Exact attributes use OPRF-based PSI. "
        f"{'Blocking was applied: ' + job.blocking_note if job.blocking_note else 'No blocking (small dataset).'} "
        "Non-matching records are excluded from this response. "
        "Protocol operates under the semi-honest adversary model."
    )

    return ERJobResults(
        job_id=job.job_id,
        total_matches=len(job.results),
        total_unmatched_a=max(0, unmatched_a),
        total_unmatched_b=max(0, unmatched_b),
        dataset_size_a=size_a,
        dataset_size_b=size_b,
        candidate_pairs_evaluated=job.candidate_pairs_evaluated,
        overall_threshold=job.overall_threshold,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        results=page_results,
        protocol_notes=privacy_note,
    )
