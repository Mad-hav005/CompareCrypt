"""
Tri-Layer Benchmark Comparison:
1. Plaintext Fuzzy Baseline (Normalized Levenshtein)
2. Exact Cryptographic PSI Baseline (2Hash-DH OPRF-PSI)
3. CompareCrypt — Privacy-Preserving Shingle Similarity Matching (Phase 3)

Measures and compares across dataset sizes:
- Runtime (Total and per-record)
- Communication payload size (exchanged bytes)
- Peak memory consumption (KB)
- Precision & Recall against synthetic ground truth (exact matches + typos)
"""

import sys
import os
import time
import tracemalloc
from typing import Dict, Any, List

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.crypto.psi import OPRFExactPSI, AliceParty, BobParty
from app.crypto.threshold_psi import CryptographicThresholdPSI, AliceThresholdParty, BobThresholdParty
from app.matching.fuzzy_match import FuzzyMatcher


def generate_tri_benchmark_datasets(n: int):
    """
    Generates synthetic datasets with realistic names:
    - 20% exact identical records
    - 20% single-character typo records (substitutions like Kumar -> Kumer)
    - 60% disjoint records
    """
    first_names = [
        "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
        "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    ]
    surnames = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
        "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    ]

    n_exact = max(1, int(n * 0.20))
    n_fuzzy = max(1, int(n * 0.20))
    n_disjoint = n - n_exact - n_fuzzy

    # Exact matches
    exact_alice = [f"{first_names[i % len(first_names)]} {surnames[i % len(surnames)]} {i:04d}" for i in range(n_exact)]
    exact_bob = list(exact_alice)

    # Fuzzy pairs (1 character substitution in surname)
    fuzzy_alice = []
    fuzzy_bob = []
    for i in range(n_fuzzy):
        idx = n_exact + i
        fn = first_names[idx % len(first_names)]
        sn = surnames[idx % len(surnames)]
        sn_typo = sn[:-1] + ("x" if sn[-1] != "x" else "y")
        fuzzy_alice.append(f"{fn} {sn} {idx:04d}")
        fuzzy_bob.append(f"{fn} {sn_typo} {idx:04d}")

    # Truly disjoint records
    disjoint_alice = [f"UniqueAlice_{i:04d}" for i in range(n_disjoint)]
    disjoint_bob = [f"UniqueBob_{i:04d}" for i in range(n_disjoint)]

    alice_data = exact_alice + fuzzy_alice + disjoint_alice
    bob_data = exact_bob + fuzzy_bob + disjoint_bob


    ground_truth_exact = set(exact_alice)
    ground_truth_all_similar = set(zip(exact_alice, exact_bob)) | set(zip(fuzzy_alice, fuzzy_bob))

    return alice_data, bob_data, ground_truth_exact, ground_truth_all_similar


def benchmark_plaintext_fuzzy(alice_data: List[str], bob_data: List[str], gt_pairs: set, threshold: float = 0.85) -> Dict[str, Any]:
    matcher = FuzzyMatcher(default_threshold=threshold)

    tracemalloc.start()
    t0 = time.perf_counter()
    matches, _, _, _ = matcher.match(alice_data, bob_data, threshold=threshold)
    runtime = time.perf_counter() - t0
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    discovered = {(m.alice_record, m.bob_record) for m in matches}
    tp = len(discovered & gt_pairs)
    fp = len(discovered - gt_pairs)
    fn = len(gt_pairs - discovered)

    return {
        "runtime_sec": runtime,
        "matches_count": len(matches),
        "comm_kb": 0.0,  # in-process simulation
        "peak_mem_kb": peak_mem / 1024.0,
        "precision": tp / (tp + fp) if (tp + fp) > 0 else 1.0,
        "recall": tp / (tp + fn) if (tp + fn) > 0 else 1.0,
    }


def benchmark_exact_psi(alice_data: List[str], bob_data: List[str], gt_exact: set) -> Dict[str, Any]:
    tracemalloc.start()
    t0 = time.perf_counter()

    alice = AliceParty(alice_data)
    bob = BobParty(bob_data)

    blinded = alice.phase1_blind_inputs()
    comm_a_to_b = len(blinded) * 256

    eval_pts, server_prfs = bob.phase2_evaluate_and_hash(blinded)
    comm_b_to_a = (len(eval_pts) * 256) + (len(server_prfs) * 32)

    matches = alice.phase3_compute_intersection(eval_pts, set(server_prfs))
    runtime = time.perf_counter() - t0
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    matched_set = set(matches)
    tp = len(matched_set & gt_exact)
    fp = len(matched_set - gt_exact)
    fn = len(gt_exact - matched_set)

    return {
        "runtime_sec": runtime,
        "matches_count": len(matches),
        "comm_kb": (comm_a_to_b + comm_b_to_a) / 1024.0,
        "peak_mem_kb": peak_mem / 1024.0,
        "precision": tp / (tp + fp) if (tp + fp) > 0 else 1.0,
        "recall": tp / (tp + fn) if (tp + fn) > 0 else 1.0,
    }
def measure_tracemalloc_overhead(sample_ops: int = 50) -> Dict[str, float]:
    """
    Measures CPU timing overhead introduced by Python's tracemalloc module
    during modular exponentiation and shingle operations.
    """
    from app.crypto.oprf import OPRFClient, RFC3526Group14
    client = OPRFClient(RFC3526Group14())
    sample_items = [f"sample_shingle_{i}" for i in range(sample_ops)]

    # 1. Measure without tracemalloc
    t0 = time.perf_counter()
    for item in sample_items:
        client.blind(item)
    t_no_trace = time.perf_counter() - t0

    # 2. Measure with tracemalloc
    tracemalloc.start()
    t1 = time.perf_counter()
    for item in sample_items:
        client.blind(item)
    t_trace = time.perf_counter() - t1
    tracemalloc.stop()

    overhead_pct = ((t_trace - t_no_trace) / t_no_trace) * 100.0 if t_no_trace > 0 else 0.0
    return {
        "time_without_sec": t_no_trace,
        "time_with_sec": t_trace,
        "overhead_pct": overhead_pct,
    }


def benchmark_threshold_crypto_psi(alice_data: List[str], bob_data: List[str], gt_pairs: set, threshold: float = 0.80) -> Dict[str, Any]:
    tracemalloc.start()
    t_total_start = time.perf_counter()

    alice = AliceThresholdParty(alice_data)
    bob = BobThresholdParty(bob_data)

    # --- Phase 1: Alice Shingle Extraction & Blinding ---
    t_p1_start = time.perf_counter()
    blinded_payload = alice.phase1_blind_shingles()
    p1_time = time.perf_counter() - t_p1_start
    print(f"\n      -> [Phase 1/3] Alice Shingle & Blinding complete: {len(blinded_payload)} blinded shingles in {p1_time:.4f}s", flush=True)

    # Payload: record_id (4 bytes) + group element (256 bytes) = 260 bytes per shingle
    comm_a_to_b = len(blinded_payload) * 260

    # --- Phase 2: Bob Evaluation & Digest ---
    t_p2_start = time.perf_counter()
    eval_pts, bob_digest_sets = bob.phase2_evaluate_and_digest(blinded_payload)
    p2_time = time.perf_counter() - t_p2_start
    total_bob_digests = sum(len(d[2]) for d in bob_digest_sets)
    print(f"      -> [Phase 2/3] Bob Evaluation & Digest complete: {len(eval_pts)} evaluations + {len(bob_digest_sets)} digest sets ({total_bob_digests} PRFs) in {p2_time:.4f}s", flush=True)

    # Bob sends: evaluated points (260 bytes each) + digest sets (32 bytes per PRF digest + header)
    comm_b_to_a = (len(eval_pts) * 260) + (total_bob_digests * 32) + (len(bob_digest_sets) * 8)

    # --- Phase 3: Alice Unblinding & Intersection / Threshold ---
    t_p3_start = time.perf_counter()
    matches = alice.phase3_evaluate_threshold(eval_pts, bob_digest_sets, threshold=threshold)
    p3_time = time.perf_counter() - t_p3_start
    print(f"      -> [Phase 3/3] Alice Unblinding & Intersection complete: {len(matches)} threshold matches identified in {p3_time:.4f}s", flush=True)

    runtime = time.perf_counter() - t_total_start
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    discovered = {(m.alice_record, m.bob_record) for m in matches}
    tp = len(discovered & gt_pairs)
    fp = len(discovered - gt_pairs)
    fn = len(gt_pairs - discovered)

    return {
        "runtime_sec": runtime,
        "p1_time": p1_time,
        "p2_time": p2_time,
        "p3_time": p3_time,
        "matches_count": len(matches),
        "comm_kb": (comm_a_to_b + comm_b_to_a) / 1024.0,
        "peak_mem_kb": peak_mem / 1024.0,
        "precision": tp / (tp + fp) if (tp + fp) > 0 else 1.0,
        "recall": tp / (tp + fn) if (tp + fn) > 0 else 1.0,
    }


def main():
    # Evaluated benchmark dataset sizes: N = 10 and N = 50
    # (Note: Runtime measurements include tracemalloc overhead because peak memory is being measured.
    #  Tracemalloc calibration is reported separately as profiling overhead, not as a correction factor.)
    sizes = [10, 50]
    print("=" * 105, flush=True)
    print("  COMPARECRYPT TRI-LAYER COMPARATIVE BENCHMARK", flush=True)
    print("  1. Plaintext Fuzzy (Levenshtein) | 2. Exact OPRF-PSI | 3. Cryptographic Shingle Threshold-PSI", flush=True)
    print("=" * 105, flush=True)

    # Measure tracemalloc overhead separately as profiling overhead
    print("\n[*] Calibrating tracemalloc memory-profiler overhead on modular exponentiations...", flush=True)
    tm_bench = measure_tracemalloc_overhead(sample_ops=50)
    print(f"    - Time without tracemalloc (50 ops): {tm_bench['time_without_sec']:.4f}s", flush=True)
    print(f"    - Time with tracemalloc (50 ops):    {tm_bench['time_with_sec']:.4f}s", flush=True)
    print(f"    - Measured tracemalloc overhead:     {tm_bench['overhead_pct']:+.2f}% (profiling overhead)", flush=True)

    for n in sizes:
        print(f"\n=========================================================================================================", flush=True)
        print(f"[START] Dataset Size: N = {n} records per party", flush=True)
        alice_data, bob_data, gt_exact, gt_similar = generate_tri_benchmark_datasets(n)
        print(f"        Ground Truth: {len(gt_exact)} exact identical pairs, {len(gt_similar)} total similar pairs", flush=True)
        print(f"=========================================================================================================", flush=True)

        # 1. Plaintext Fuzzy
        print(f"[*] Case 1/3: Running Plaintext Fuzzy (Normalized Levenshtein) for N={n}...", end="", flush=True)
        res_plain = benchmark_plaintext_fuzzy(alice_data, bob_data, gt_similar, threshold=0.85)
        print(f" DONE in {res_plain['runtime_sec']:.4f}s ({res_plain['matches_count']} matches, precision={res_plain['precision']:.2f}, recall={res_plain['recall']:.2f})", flush=True)

        # 2. Exact OPRF-PSI
        print(f"[*] Case 2/3: Running Exact 2Hash-DH OPRF-PSI for N={n}...", end="", flush=True)
        res_exact = benchmark_exact_psi(alice_data, bob_data, gt_exact)
        print(f" DONE in {res_exact['runtime_sec']:.4f}s ({res_exact['matches_count']} matches, comm={res_exact['comm_kb']:.2f}KB)", flush=True)

        # 3. Cryptographic Shingle Threshold-PSI
        print(f"[*] Case 3/3: Running CompareCrypt Shingle Threshold-PSI for N={n} (Modular Exponentiations on Shingles)...", flush=True)
        res_thresh = benchmark_threshold_crypto_psi(alice_data, bob_data, gt_similar, threshold=0.80)
        print(f"    -> Case 3/3 complete in {res_thresh['runtime_sec']:.4f}s ({res_thresh['matches_count']} matches, comm={res_thresh['comm_kb']:.2f}KB)", flush=True)

        print(f"\n--- Threshold-PSI Phase Timing Breakdown for N = {n} ---", flush=True)
        p1_pct = (res_thresh['p1_time'] / res_thresh['runtime_sec']) * 100.0
        p2_pct = (res_thresh['p2_time'] / res_thresh['runtime_sec']) * 100.0
        p3_pct = (res_thresh['p3_time'] / res_thresh['runtime_sec']) * 100.0
        print(f"  * Phase 1 (Alice Shingle & Blinding):      {res_thresh['p1_time']:.4f}s ({p1_pct:.1f}%)", flush=True)
        print(f"  * Phase 2 (Bob Evaluation & Digest):       {res_thresh['p2_time']:.4f}s ({p2_pct:.1f}%)", flush=True)
        print(f"  * Phase 3 (Alice Unblinding & Overlap):    {res_thresh['p3_time']:.4f}s ({p3_pct:.1f}%)", flush=True)
        print(f"  * Total Threshold-PSI Cryptographic Time:  {res_thresh['runtime_sec']:.4f}s", flush=True)

        print(f"\n--- Summary Table for N = {n} ---", flush=True)
        fmt = "{:<25} | {:<22} | {:<22} | {:<22}"
        print("-" * 105, flush=True)
        print(fmt.format("Metric", "1. Plaintext Fuzzy", "2. Exact OPRF-PSI", "3. Threshold Crypto-PSI"), flush=True)
        print("-" * 105, flush=True)
        print(fmt.format("Runtime (seconds)", f"{res_plain['runtime_sec']:.4f}", f"{res_exact['runtime_sec']:.4f}", f"{res_thresh['runtime_sec']:.4f}"), flush=True)
        print(fmt.format("Per-Record Time (ms)", f"{(res_plain['runtime_sec']/n)*1000:.2f}", f"{(res_exact['runtime_sec']/n)*1000:.2f}", f"{(res_thresh['runtime_sec']/n)*1000:.2f}"), flush=True)
        print(fmt.format("Discovered Matches", f"{res_plain['matches_count']}", f"{res_exact['matches_count']}", f"{res_thresh['matches_count']}"), flush=True)
        print(fmt.format("Communication (KB)", f"{res_plain['comm_kb']:.2f}", f"{res_exact['comm_kb']:.2f}", f"{res_thresh['comm_kb']:.2f}"), flush=True)
        print(fmt.format("Peak Memory (KB)", f"{res_plain['peak_mem_kb']:.2f}", f"{res_exact['peak_mem_kb']:.2f}", f"{res_thresh['peak_mem_kb']:.2f}"), flush=True)
        print(fmt.format("Precision", f"{res_plain['precision']:.4f}", f"{res_exact['precision']:.4f}", f"{res_thresh['precision']:.4f}"), flush=True)
        print(fmt.format("Recall", f"{res_plain['recall']:.4f}", f"{res_exact['recall']:.4f}", f"{res_thresh['recall']:.4f}"), flush=True)

    print("\n" + "=" * 105, flush=True)
    print("  TRI-LAYER BENCHMARK COMPLETE", flush=True)
    print("=" * 105, flush=True)


if __name__ == "__main__":
    main()
