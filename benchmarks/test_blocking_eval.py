import os, sys
sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

from benchmarks.run_scalability_benchmark import generate_benchmark_datasets, get_configured_mappings
from app.entity_resolution.blocking import generate_candidate_pairs

for n in [100, 500, 1000]:
    rows_a, rows_b, expected_matches = generate_benchmark_datasets(n, seed=42)
    pairs, applied, note = generate_candidate_pairs(rows_a, rows_b, "Name", "Full Name")
    gt_pairs = {(i, i) for i in range(expected_matches)}
    surviving_gt = gt_pairs & set(pairs)
    print(f"\n--- Current Blocking for {n}x{n} ---")
    print(f"Candidate pairs: {len(pairs):,}")
    print(f"Ground truth total: {expected_matches}")
    print(f"Ground truth surviving: {len(surviving_gt)}")
    print(f"Blocking recall: {len(surviving_gt) / expected_matches * 100:.2f}%")
