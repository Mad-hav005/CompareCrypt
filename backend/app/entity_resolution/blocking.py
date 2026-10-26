"""
Candidate generation via multi-token inverted-index blocking.

Purpose
-------
A full O(N*M) cross-join of large datasets would make the O(shingles^2) OPRF
cost prohibitive (e.g., N=M=5000 → 25M pairs). Blocking pre-filters
candidate pairs using token overlap (word tokens and character bigram shingles),
dramatically reducing the number of pairs requiring expensive cryptographic evaluation
while preserving recall for reordered words and character typos.

Algorithm (Token Inverted-Index Blocking)
-----------------------------------------
For the designated blocking key column:
1. Normalize the blocking-key text.
2. Extract word tokens (alphanumeric words with length >= 2) and character bigram shingles.
3. Index dataset B in an inverted index.
4. For each record in dataset A, candidate records in B are selected if:
   - They share at least one word token (handles word reordering, prefix/suffix additions), OR
   - They share at least 2 character bigrams (handles typos and spelling variations;
     or at least 1 bigram for very short inputs).

Privacy implications (disclosed honestly)
-----------------------------------------
- Blocking operates on plaintext values of the blocking-key column on the orchestrator server.
- This reveals coarse token overlap to the orchestrating server.
- The UI explicitly discloses this leakage to the user.
- For small datasets (|A| * |B| <= BLOCKING_THRESHOLD), blocking is bypassed and full
  cross-join is used directly.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, FrozenSet, List, Set, Tuple

from app.matching.shingle import generate_unique_shingles
from app.utils.normalization import normalize_string


# Minimum dataset product to enable blocking (avoid overhead for small datasets)
BLOCKING_THRESHOLD = 200 * 200  # |A| * |B|


def _extract_word_tokens(value: str) -> Set[str]:
    """Extract normalized alphanumeric word tokens of length >= 2."""
    norm = normalize_string(value)
    if not norm:
        return set()
    return {w for w in re.split(r"[^a-zA-Z0-9]+", norm) if len(w) >= 2}


def _extract_shingle_tokens(value: str) -> Set[str]:
    """Extract unique boundary-padded character bigrams."""
    norm = normalize_string(value)
    if not norm:
        return set()
    return set(generate_unique_shingles(norm))


def _extract_block_tokens(value: str) -> FrozenSet[str]:
    """
    Extract token set used for blocking.
    Combines word tokens (prefixed with 'w:') and character bigrams (prefixed with 's:').
    """
    words = {f"w:{w}" for w in _extract_word_tokens(value)}
    shingles = {f"s:{s}" for s in _extract_shingle_tokens(value)}
    return frozenset(words | shingles)


def generate_candidate_pairs(
    rows_a: List[Dict],
    rows_b: List[Dict],
    blocking_key_a: str,
    blocking_key_b: str,
) -> Tuple[List[Tuple[int, int]], bool, str]:
    """
    Generate candidate (row_index_a, row_index_b) pairs using multi-token inverted-index blocking.

    Args:
        rows_a: List of row dicts for dataset A.
        rows_b: List of row dicts for dataset B.
        blocking_key_a: Column name in A to use as blocking key.
        blocking_key_b: Column name in B to use as blocking key.

    Returns:
        (candidate_pairs, blocking_was_applied, privacy_note)
    """
    n, m = len(rows_a), len(rows_b)

    # For small datasets, skip blocking entirely
    if n * m <= BLOCKING_THRESHOLD:
        pairs = [(i, j) for i in range(n) for j in range(m)]
        return pairs, False, "Full cross-join used (dataset small enough to skip blocking)."

    # Build inverted index for dataset B
    word_to_b: Dict[str, Set[int]] = defaultdict(set)
    shingle_to_b: Dict[str, Set[int]] = defaultdict(set)

    for j, row_b in enumerate(rows_b):
        val_b = row_b.get(blocking_key_b, "")
        words_b = _extract_word_tokens(val_b)
        shingles_b = _extract_shingle_tokens(val_b)
        for w in words_b:
            word_to_b[w].add(j)
        for s in shingles_b:
            shingle_to_b[s].add(j)

    # For each A row, collect B candidates sharing words or sufficient shingles
    candidate_set: Set[Tuple[int, int]] = set()
    for i, row_a in enumerate(rows_a):
        val_a = row_a.get(blocking_key_a, "")
        words_a = _extract_word_tokens(val_a)
        shingles_a = _extract_shingle_tokens(val_a)

        # 1. Word token overlap (instant candidate)
        for w in words_a:
            for j in word_to_b.get(w, ()):
                candidate_set.add((i, j))

        # 2. Shingle overlap (requires >= 2 shared shingles, or >= 1 for very short inputs)
        shingle_overlap_counts: Dict[int, int] = defaultdict(int)
        for s in shingles_a:
            for j in shingle_to_b.get(s, ()):
                shingle_overlap_counts[j] += 1

        min_shared_shingles = 2 if len(shingles_a) >= 3 else 1
        for j, count in shingle_overlap_counts.items():
            if count >= min_shared_shingles:
                candidate_set.add((i, j))

    pairs = sorted(candidate_set)
    note = (
        f"Blocking applied: {len(pairs)} candidate pairs from {n}×{m}={n*m} full cross-join. "
        f"Blocking key columns: '{blocking_key_a}' / '{blocking_key_b}'. "
        "PRIVACY NOTE: Blocking uses plaintext multi-token inverted-index matching and reveals coarse "
        "structural token overlap of the blocking-key column to the orchestrating server. "
        "This leakage is weaker than the OPRF-based matching but is present; see protocol notes."
    )
    return pairs, True, note
