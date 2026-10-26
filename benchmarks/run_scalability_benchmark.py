"""
Scalability Benchmark for Entity Resolution after Alice-side OPRF Precomputation/Memoization.

Runs:
- 100 x 100
- 500 x 500
- 1000 x 1000
"""

from __future__ import annotations

import asyncio
import os
import platform
import random
import sys
import time
import tracemalloc
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.entity_resolution.blocking import generate_candidate_pairs, BLOCKING_THRESHOLD
from app.entity_resolution.er_service import run_er_job
from app.entity_resolution.job_manager import ERJobState
from app.models.er_schemas import AttributeMapping, MatchStrategy, StartERJobRequest


FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
]

STREETS = [
    "Main St", "High St", "Broad St", "Park Ave", "Maple St", "Oak Ave", "Pine Rd",
    "Cedar Ln", "Elm St", "Washington Blvd", "Lakeview Dr", "Sunset Blvd", "Springfield Rd",
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
]


def generate_benchmark_datasets(n: int, seed: int = 42) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], int]:
    rng = random.Random(seed)

    n_exact = max(1, int(n * 0.15))
    n_fuzzy = max(1, int(n * 0.15))
    expected_matches = n_exact + n_fuzzy

    rows_a: List[Dict[str, str]] = []
    rows_b: List[Dict[str, str]] = []

    # 1. Exact matches
    for i in range(n_exact):
        fn = rng.choice(FIRST_NAMES)
        ln = rng.choice(LAST_NAMES)
        name = f"{fn} {ln}"
        st_num = rng.randint(100, 9999)
        street = rng.choice(STREETS)
        addr = f"{st_num} {street}"
        phone = f"555-{rng.randint(100, 999):03d}-{rng.randint(1000, 9999):04d}"
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        city = rng.choice(CITIES)

        rows_a.append({
            "Name": name,
            "Address": addr,
            "Phone": phone,
            "Email": email,
            "City": city,
        })
        rows_b.append({
            "Full Name": name,
            "Residential Address": addr,
            "Mobile": phone,
            "Email ID": email,
            "Location": city,
        })

    # 2. Fuzzy matches
    for i in range(n_exact, n_exact + n_fuzzy):
        fn = rng.choice(FIRST_NAMES)
        ln = rng.choice(LAST_NAMES)
        st_num = rng.randint(100, 9999)
        street = rng.choice(STREETS)
        phone = f"555-{rng.randint(100, 999):03d}-{rng.randint(1000, 9999):04d}"
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        city = rng.choice(CITIES)

        variation_type = i % 3
        if variation_type == 0:
            name_a = f"{fn} {ln}"
            name_b = f"{ln}, {fn}"
        elif variation_type == 1:
            name_a = f"{fn} {ln}"
            typo_ln = ln[:-1] + ("x" if ln[-1] != "x" else "y")
            name_b = f"{fn} {typo_ln}"
        else:
            name_a = f"Dr. {fn} {ln}"
            name_b = f"{fn} {ln}"

        addr_a = f"{st_num} {street}"
        addr_b = addr_a.replace(" St", " Street").replace(" Ave", " Avenue").replace(" Rd", " Road")

        rows_a.append({
            "Name": name_a,
            "Address": addr_a,
            "Phone": phone,
            "Email": email,
            "City": city,
        })
        rows_b.append({
            "Full Name": name_b,
            "Residential Address": addr_b,
            "Mobile": phone,
            "Email ID": email,
            "Location": city,
        })

    # 3. Disjoint non-matching records
    for i in range(n_exact + n_fuzzy, n):
        fn_a = rng.choice(FIRST_NAMES)
        ln_a = rng.choice(LAST_NAMES)
        rows_a.append({
            "Name": f"{fn_a} {ln_a}_{i}",
            "Address": f"{rng.randint(100, 9999)} {rng.choice(STREETS)}",
            "Phone": f"555-010-{i:04d}",
            "Email": f"user_a_{i}@corp-a.com",
            "City": rng.choice(CITIES),
        })

        fn_b = rng.choice(FIRST_NAMES)
        ln_b = rng.choice(LAST_NAMES)
        rows_b.append({
            "Full Name": f"{fn_b} {ln_b}_B_{i}",
            "Residential Address": f"{rng.randint(100, 9999)} {rng.choice(STREETS)}",
            "Mobile": f"555-020-{i:04d}",
            "Email ID": f"user_b_{i}@corp-b.com",
            "Location": rng.choice(CITIES),
        })

    return rows_a, rows_b, expected_matches


def get_configured_mappings() -> List[AttributeMapping]:
    return [
        AttributeMapping(column_a="Name", column_b="Full Name", strategy=MatchStrategy.FUZZY, weight=2.0, fuzzy_threshold=0.75),
        AttributeMapping(column_a="Address", column_b="Residential Address", strategy=MatchStrategy.FUZZY, weight=1.0, fuzzy_threshold=0.70),
        AttributeMapping(column_a="Phone", column_b="Mobile", strategy=MatchStrategy.EXACT, weight=2.0),
        AttributeMapping(column_a="Email", column_b="Email ID", strategy=MatchStrategy.EXACT, weight=3.0),
        AttributeMapping(column_a="City", column_b="Location", strategy=MatchStrategy.FUZZY, weight=1.0, fuzzy_threshold=0.80),
    ]


async def run_benchmark_size(n: int) -> Dict[str, Any]:
    print(f"\n==================================================================", flush=True)
    print(f"BENCHMARK RUN: {n} x {n} records ({n * n:,} possible pairs)", flush=True)
    print(f"==================================================================", flush=True)

    rows_a, rows_b, expected_matches = generate_benchmark_datasets(n, seed=42)
    mappings = get_configured_mappings()

    # Measure blocking
    t_b0 = time.perf_counter()
    candidates, blocking_applied, note = generate_candidate_pairs(rows_a, rows_b, "Name", "Full Name")
    t_blocking = time.perf_counter() - t_b0
    num_candidates = len(candidates)
    possible_pairs = n * n
    reduction = (1.0 - (num_candidates / possible_pairs)) * 100.0

    print(f"Blocking applied: {blocking_applied} ({t_blocking * 1000.0:.2f} ms)", flush=True)
    print(f"Candidate pairs: {num_candidates:,} ({reduction:.2f}% reduction)", flush=True)

    # Count unique values in A
    unique_vals_a = {
        col: len({r[col] for r in rows_a})
        for col in ["Name", "Address", "Phone", "Email", "City"]
    }
    print(f"Unique Alice values: {unique_vals_a}", flush=True)

    # Run full ER job
    job = ERJobState(f"bench-{n}")
    job.rows_a = rows_a
    job.rows_b = rows_b
    request = StartERJobRequest(
        job_id=job.job_id,
        mappings=mappings,
        overall_threshold=0.75,
        normalize=True,
    )

    tracemalloc.start()
    t_er0 = time.perf_counter()
    await run_er_job(job, request)
    t_total = time.perf_counter() - t_er0
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_mem / (1024 * 1024)
    crypto_time = t_total - t_blocking

    # Ground truth verification
    gt_pairs = {(i, i) for i in range(expected_matches)}
    discovered_pairs = {(r.row_index_a, r.row_index_b) for r in job.results}
    true_positives = len(gt_pairs & discovered_pairs)
    precision = true_positives / max(1, len(discovered_pairs))
    recall = true_positives / max(1, len(gt_pairs))

    matched_a = {r.row_index_a for r in job.results}
    matched_b = {r.row_index_b for r in job.results}

    ms_per_candidate = (crypto_time / max(1, num_candidates)) * 1000.0

    matcher_stats = getattr(job, "matcher_stats", {})
    pairs_sc = matcher_stats.get("pairs_short_circuited", 0)
    pairs_full = matcher_stats.get("pairs_fully_evaluated", 0)
    attr_skipped = matcher_stats.get("attributes_skipped", 0)
    sc_pct = (pairs_sc / max(1, num_candidates)) * 100.0

    print(f"Total ER runtime: {t_total:.2f} s", flush=True)
    print(f"Crypto/matching time: {crypto_time:.2f} s ({ms_per_candidate:.3f} ms / candidate pair)", flush=True)
    print(f"Short-circuited pairs: {pairs_sc:,} ({sc_pct:.2f}%)", flush=True)
    print(f"Fully evaluated pairs: {pairs_full:,}", flush=True)
    print(f"Attributes skipped: {attr_skipped:,}", flush=True)
    print(f"Matcher stats: {matcher_stats}", flush=True)
    print(f"Peak memory: {peak_mb:.2f} MB", flush=True)
    print(f"Discovered matches: {len(job.results)} (Expected ground truth: {expected_matches})", flush=True)
    print(f"Precision: {precision:.4f}, Recall: {recall:.4f}", flush=True)
    print(f"Unmatched A: {len(rows_a) - len(matched_a)}, Unmatched B: {len(rows_b) - len(matched_b)}", flush=True)

    return {
        "size": n,
        "possible_pairs": possible_pairs,
        "candidate_pairs": num_candidates,
        "reduction_pct": reduction,
        "blocking_time_s": t_blocking,
        "crypto_time_s": crypto_time,
        "total_time_s": t_total,
        "ms_per_pair": ms_per_candidate,
        "peak_mb": peak_mb,
        "matches": len(job.results),
        "expected_matches": expected_matches,
        "precision": precision,
        "recall": recall,
        "unmatched_a": len(rows_a) - len(matched_a),
        "unmatched_b": len(rows_b) - len(matched_b),
        "pairs_short_circuited": pairs_sc,
        "short_circuit_pct": sc_pct,
        "attributes_skipped": attr_skipped,
        "matcher_stats": matcher_stats,
    }


async def main():
    print("================================================================================", flush=True)
    print("SCALABILITY BENCHMARK: OPTIMIZATION 2 (SHORT-CIRCUIT ATTRIBUTE EVALUATION)", flush=True)
    print(f"Platform: {platform.system()} {platform.release()}, Python: {platform.python_version()}", flush=True)
    print("================================================================================", flush=True)

    results = []
    # Test 100x100
    res_100 = await run_benchmark_size(100)
    results.append(res_100)

    # Test 500x500
    res_500 = await run_benchmark_size(500)
    results.append(res_500)

    # Test 1000x1000
    res_1000 = await run_benchmark_size(1000)
    results.append(res_1000)

    # Previous baseline from Optimization 1 (Alice OPRF precomputation only)
    baselines = {
        100: {"time": 64.23, "ms_pair": 6.422},
        500: {"time": 147.22, "ms_pair": 1.544},
        1000: {"time": 265.50, "ms_pair": 0.738},
    }

    print("\n\n" + "=" * 115, flush=True)
    print("FINAL MEASURED SUMMARY TABLE: BEFORE VS AFTER SHORT-CIRCUITING", flush=True)
    print("=" * 115, flush=True)
    header = f"{'Size':<10} | {'Candidate Pairs':<16} | {'Opt 1 Runtime':<14} | {'Opt 2 Runtime':<14} | {'Speedup':<9} | {'Short-Circuited':<16} | {'Attr Skipped':<13} | {'Matches':<8}"
    print(header, flush=True)
    print("-" * 115, flush=True)
    for r in results:
        sz = r["size"]
        cand_str = f"{r['candidate_pairs']:,}"
        b_time = baselines[sz]["time"]
        a_time = r["total_time_s"]
        speedup = f"{b_time / max(0.01, a_time):.2f}x"
        sc_str = f"{r['pairs_short_circuited']:,} ({r['short_circuit_pct']:.1f}%)"
        sk_str = f"{r['attributes_skipped']:,}"
        m_str = f"{r['matches']}"
        print(f"{f'{sz}x{sz}':<10} | {cand_str:<16} | {f'{b_time:.2f}s':<14} | {f'{a_time:.2f}s':<14} | {speedup:<9} | {sc_str:<16} | {sk_str:<13} | {m_str:<8}", flush=True)
    print("=" * 115, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
