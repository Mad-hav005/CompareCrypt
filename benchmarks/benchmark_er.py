"""
Entity Resolution Benchmark module.
Provides dataset generators and execution runners.
"""

from __future__ import annotations

import os
import sys

# Ensure backend and root are on sys.path for runtime execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.entity_resolution.blocking import generate_candidate_pairs, BLOCKING_THRESHOLD
from app.entity_resolution.er_service import run_er_job
from app.entity_resolution.job_manager import ERJobState
from app.models.er_schemas import AttributeMapping, MatchStrategy, StartERJobRequest

from benchmarks.run_scalability_benchmark import (
    FIRST_NAMES,
    LAST_NAMES,
    STREETS,
    CITIES,
    generate_benchmark_datasets,
    get_configured_mappings,
    run_benchmark_size,
    main,
)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
