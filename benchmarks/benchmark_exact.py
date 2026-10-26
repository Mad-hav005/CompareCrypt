"""
Reproducible Benchmark Framework for Exact Private Set Intersection (PSI).

Measures:
- Dataset size (N items)
- Intersection size
- Execution time (Total, Alice Phase 1, Bob Phase 2, Alice Phase 3)
- Communication payload size (Bytes exchanged Alice -> Bob and Bob -> Alice)
- Peak memory usage (tracemalloc)
- Accuracy (Precision, Recall, False Positives, False Negatives against Ground Truth)
"""

import sys
import os
import time
import tracemalloc
from typing import List, Dict, Any

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.crypto.psi import AliceParty, BobParty


def generate_synthetic_datasets(n: int, overlap_ratio: float = 0.3):
    """
    Generates deterministic synthetic datasets for Alice and Bob with known overlap.
    """
    num_overlap = int(n * overlap_ratio)
    num_disjoint = n - num_overlap

    overlap = [f"shared_identity_record_{i:06d}@org.example" for i in range(num_overlap)]
    alice_only = [f"alice_unique_record_{i:06d}@alice.example" for i in range(num_disjoint)]
    bob_only = [f"bob_unique_record_{i:06d}@bob.example" for i in range(num_disjoint)]

    alice_data = overlap + alice_only
    bob_data = overlap + bob_only
    ground_truth = set(overlap)

    return alice_data, bob_data, ground_truth


def run_benchmark(n: int, overlap_ratio: float = 0.3) -> Dict[str, Any]:
    """Runs a single benchmark instance for dataset size n."""
    alice_data, bob_data, ground_truth = generate_synthetic_datasets(n, overlap_ratio)

    tracemalloc.start()
    start_total = time.perf_counter()

    # 1. Alice setup
    alice = AliceParty(alice_data)
    bob = BobParty(bob_data)

    # 2. Phase 1: Alice blinding
    t0 = time.perf_counter()
    blinded_payload = alice.phase1_blind_inputs()
    t_phase1 = time.perf_counter() - t0

    # Alice -> Bob communication (256 bytes per 2048-bit group element)
    comm_alice_to_bob = len(blinded_payload) * 256

    # 3. Phase 2: Bob evaluation and direct PRF
    t0 = time.perf_counter()
    eval_elements, server_prfs = bob.phase2_evaluate_and_hash(blinded_payload)
    t_phase2 = time.perf_counter() - t0

    # Bob -> Alice communication (256 bytes per evaluated point + 32 bytes per PRF hash)
    comm_bob_to_alice = (len(eval_elements) * 256) + (len(server_prfs) * 32)

    # 4. Phase 3: Alice unblinding & intersection
    t0 = time.perf_counter()
    server_prf_set = set(server_prfs)
    discovered_matches = alice.phase3_compute_intersection(eval_elements, server_prf_set)
    t_phase3 = time.perf_counter() - t0

    total_time = time.perf_counter() - start_total
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Accuracy calculations
    matched_set = set(discovered_matches)
    tp = len(matched_set & ground_truth)
    fp = len(matched_set - ground_truth)
    fn = len(ground_truth - matched_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0

    return {
        "dataset_size": n,
        "ground_truth_matches": len(ground_truth),
        "discovered_matches": len(discovered_matches),
        "precision": precision,
        "recall": recall,
        "false_positives": fp,
        "false_negatives": fn,
        "phase1_time_sec": t_phase1,
        "phase2_time_sec": t_phase2,
        "phase3_time_sec": t_phase3,
        "total_time_sec": total_time,
        "alice_to_bob_bytes": comm_alice_to_bob,
        "bob_to_alice_bytes": comm_bob_to_alice,
        "total_comm_bytes": comm_alice_to_bob + comm_bob_to_alice,
        "peak_memory_kb": peak_mem / 1024.0,
    }


def main():
    sizes = [10, 50, 100, 250]
    print("=" * 80)
    print("  EXACT PRIVATE SET INTERSECTION (OPRF-PSI) BENCHMARK SUITE")
    print("  Group: RFC 3526 2048-bit MODP | Protocol: 2Hash-DH-OPRF-PSI")
    print("=" * 80)

    for n in sizes:
        print(f"\n[*] Running benchmark for N = {n} records per party...")
        results = run_benchmark(n, overlap_ratio=0.3)
        print(f"    - Ground Truth Overlap : {results['ground_truth_matches']}")
        print(f"    - Discovered Matches   : {results['discovered_matches']}")
        print(f"    - Precision / Recall   : {results['precision']:.4f} / {results['recall']:.4f}")
        print(f"    - Total Runtime        : {results['total_time_sec']:.3f} s ({(results['total_time_sec']/n)*1000:.2f} ms/item)")
        print(f"      * Phase 1 (Blinding) : {results['phase1_time_sec']:.3f} s")
        print(f"      * Phase 2 (Server)   : {results['phase2_time_sec']:.3f} s")
        print(f"      * Phase 3 (Client)   : {results['phase3_time_sec']:.3f} s")
        print(f"    - Total Communication  : {results['total_comm_bytes'] / 1024.0:.2f} KB")
        print(f"    - Peak Memory Usage    : {results['peak_memory_kb']:.2f} KB")

    print("\n" + "=" * 80)
    print("  BENCHMARK COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
