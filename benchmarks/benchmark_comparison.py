"""
Benchmark comparison between Exact Cryptographic PSI and Fuzzy Matching Baseline.

Measures and compares across dataset sizes:
- Total runtime and throughput (items/sec)
- Precision and recall against synthetic ground truth (exact matches + typos)
- Memory consumption (peak KB)
- Comparison summary table
"""

import sys
import os
import time
import tracemalloc
from typing import Dict, Any, List

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.crypto.psi import OPRFExactPSI
from app.matching.fuzzy_match import FuzzyMatcher


def generate_benchmark_datasets(n: int):
    """
    Generates synthetic datasets with:
    - 20% exact identical records
    - 20% fuzzy typos (1-edit distance difference)
    - 60% disjoint records
    """
    n_exact = max(1, int(n * 0.20))
    n_fuzzy = max(1, int(n * 0.20))
    n_disjoint = n - n_exact - n_fuzzy

    # Curated name list with distinct names
    first_names = [
        "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
        "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
        "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
        "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
        "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
        "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
        "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna",
        "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
        "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Alexander", "Debra",
        "Frank", "Rachel", "Patrick", "Catherine", "Raymond", "Carolyn", "Jack", "Janet",
        "Dennis", "Ruth", "Jerry", "Maria", "Tyler", "Heather", "Aaron", "Diane"
    ]
    surnames = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
        "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
        "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
        "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
        "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
        "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
        "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
        "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
        "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
        "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
        "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers",
        "Long", "Ross", "Foster", "Jimenez", "Powell", "Jenkins", "Perry", "Russell"
    ]

    # Exact matches
    exact_alice = [f"{first_names[i % len(first_names)]} {surnames[i % len(surnames)]} exact_{i}" for i in range(n_exact)]
    exact_bob = list(exact_alice)

    # Fuzzy pairs (1-character typo in surname, e.g., Brown -> Browm)
    fuzzy_alice = []
    fuzzy_bob = []
    for i in range(n_fuzzy):
        idx = (n_exact + i)
        fn = first_names[idx % len(first_names)]
        sn = surnames[idx % len(surnames)]
        # Change last letter of surname
        sn_typo = sn[:-1] + ("x" if sn[-1] != "x" else "y")
        fuzzy_alice.append(f"{fn} {sn} ID{idx}")
        fuzzy_bob.append(f"{fn} {sn_typo} ID{idx}")

    # Truly disjoint records
    disjoint_alice = [f"UniqueAliceUser_{i:04d}" for i in range(n_disjoint)]
    disjoint_bob = [f"IndependentBobRecord_{i:04d}" for i in range(n_disjoint)]

    alice_data = exact_alice + fuzzy_alice + disjoint_alice
    bob_data = exact_bob + fuzzy_bob + disjoint_bob



    ground_truth_exact = set(exact_alice)
    ground_truth_fuzzy_pairs = set(zip(fuzzy_alice, fuzzy_bob)) | set(zip(exact_alice, exact_bob))

    return alice_data, bob_data, ground_truth_exact, ground_truth_fuzzy_pairs


def benchmark_exact(alice_data: List[str], bob_data: List[str], ground_truth: set) -> Dict[str, Any]:
    """Measures exact OPRF-PSI matching."""
    psi = OPRFExactPSI()

    tracemalloc.start()
    t0 = time.perf_counter()
    matches = psi.run_protocol(alice_data, bob_data)
    runtime = time.perf_counter() - t0
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    matched_set = set(matches)
    tp = len(matched_set & ground_truth)
    fp = len(matched_set - ground_truth)
    fn = len(ground_truth - matched_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0

    return {
        "runtime_sec": runtime,
        "matches_count": len(matches),
        "peak_mem_kb": peak_mem / 1024.0,
        "precision": precision,
        "recall": recall,
    }


def benchmark_fuzzy(
    alice_data: List[str],
    bob_data: List[str],
    ground_truth_pairs: set,
    threshold: float = 0.85,
) -> Dict[str, Any]:
    """Measures deterministic fuzzy matching."""
    matcher = FuzzyMatcher(default_threshold=threshold)

    tracemalloc.start()
    t0 = time.perf_counter()
    matches, _, _, _ = matcher.match(alice_data, bob_data, threshold=threshold)
    runtime = time.perf_counter() - t0
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    discovered_pairs = {(m.alice_record, m.bob_record) for m in matches}
    tp = len(discovered_pairs & ground_truth_pairs)
    fp = len(discovered_pairs - ground_truth_pairs)
    fn = len(ground_truth_pairs - discovered_pairs)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0

    return {
        "runtime_sec": runtime,
        "matches_count": len(matches),
        "peak_mem_kb": peak_mem / 1024.0,
        "precision": precision,
        "recall": recall,
    }


def main():
    sizes = [10, 50, 100]
    print("=" * 85)
    print("  COMPARECRYPT BENCHMARK: EXACT OPRF-PSI vs DETERMINISTIC FUZZY BASELINE")
    print("=" * 85)

    for n in sizes:
        alice_data, bob_data, gt_exact, gt_fuzzy = generate_benchmark_datasets(n)
        print(f"\n--- Dataset Size: {n} records per party ---")
        print(f"Ground Truth: {len(gt_exact)} exact matches, {len(gt_fuzzy)} total similar records")

        # Run exact PSI
        res_exact = benchmark_exact(alice_data, bob_data, gt_exact)

        # Run fuzzy matcher
        res_fuzzy = benchmark_fuzzy(alice_data, bob_data, gt_fuzzy, threshold=0.85)

        print(f"\n{'Metric':<25} | {'Exact PSI (OPRF)':<25} | {'Fuzzy Baseline (Edit Dist)':<25}")
        print("-" * 85)
        print(f"{'Runtime (seconds)':<25} | {res_exact['runtime_sec']:<25.4f} | {res_fuzzy['runtime_sec']:<25.4f}")
        print(f"{'Per-Item Overhead (ms)':<25} | {(res_exact['runtime_sec']/n)*1000:<25.2f} | {(res_fuzzy['runtime_sec']/n)*1000:<25.2f}")
        print(f"{'Discovered Matches':<25} | {res_exact['matches_count']:<25} | {res_fuzzy['matches_count']:<25}")
        print(f"{'Precision':<25} | {res_exact['precision']:<25.4f} | {res_fuzzy['precision']:<25.4f}")
        print(f"{'Recall':<25} | {res_exact['recall']:<25.4f} | {res_fuzzy['recall']:<25.4f}")
        print(f"{'Peak Memory (KB)':<25} | {res_exact['peak_mem_kb']:<25.2f} | {res_fuzzy['peak_mem_kb']:<25.2f}")

    print("\n" + "=" * 85)
    print("  BENCHMARK COMPLETE")
    print("=" * 85)


if __name__ == "__main__":
    main()
