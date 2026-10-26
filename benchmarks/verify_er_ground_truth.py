"""
Ground truth verification script for Entity Resolution.
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from benchmarks.benchmark_er import generate_benchmark_datasets, get_configured_mappings
from app.entity_resolution.er_service import run_er_job
from app.entity_resolution.job_manager import ERJobState
from app.models.er_schemas import StartERJobRequest


async def verify_ground_truth(n: int = 50) -> None:
    rows_a, rows_b, expected_matches = generate_benchmark_datasets(n, seed=42)
    mappings = get_configured_mappings()

    job = ERJobState(f"verify-{n}")
    job.rows_a = rows_a
    job.rows_b = rows_b
    request = StartERJobRequest(
        job_id=job.job_id,
        mappings=mappings,
        overall_threshold=0.75,
        normalize=True,
    )

    await run_er_job(job, request)

    gt_pairs = {(i, i) for i in range(expected_matches)}
    discovered_pairs = {(r.row_index_a, r.row_index_b) for r in job.results}

    tp = len(gt_pairs & discovered_pairs)
    fp = len(discovered_pairs - gt_pairs)
    fn = len(gt_pairs - discovered_pairs)

    print(f"Dataset size: {n} x {n}")
    print(f"Expected ground truth matches: {expected_matches}")
    print(f"Discovered matches: {len(discovered_pairs)}")
    print(f"True Positives: {tp}, False Positives: {fp}, False Negatives: {fn}")
    print(f"Precision: {tp / max(1, len(discovered_pairs)):.4f}")
    print(f"Recall: {tp / max(1, expected_matches):.4f}")

    assert fp == 0, f"Found {fp} false positives!"
    assert fn == 0, f"Missed {fn} matches!"
    print("Verification PASSED!")


if __name__ == "__main__":
    asyncio.run(verify_ground_truth(50))
