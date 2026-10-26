"""
Deterministic Unique Shingle (q-gram) Tokenizer and Sørensen-Dice Similarity.

Transforms strings into unique boundary-padded character q-grams and computes
shingle-set intersection and Sørensen-Dice similarity.
No machine learning or external C++ libraries are used.
"""

import math
from typing import List, Set, Tuple


def generate_unique_shingles(s: str, q: int = 2) -> List[str]:
    """
    Pads string with boundary markers '^' and '$' and extracts unique character q-grams.
    
    Args:
        s: Input plaintext string.
        q: Shingle length (default 2 for character bigrams).

    Returns:
        List of unique shingles (deduplicated, order preserved).
    """
    if not s:
        return []

    padded = f"^{s}$"
    if len(padded) < q:
        return [padded]

    shingles: List[str] = []
    seen: Set[str] = set()

    for i in range(len(padded) - q + 1):
        gram = padded[i : i + q]
        if gram not in seen:
            seen.add(gram)
            shingles.append(gram)

    return shingles


def dice_similarity(shingles_a: List[str], shingles_b: List[str]) -> Tuple[int, float]:
    """
    Computes unique shingle intersection count and Sørensen-Dice similarity.
    
    Dice = (2 * |A cap B|) / (|A| + |B|)

    Returns:
        (intersection_count, dice_similarity_score)
    """
    set_a = set(shingles_a)
    set_b = set(shingles_b)

    if not set_a and not set_b:
        return 0, 1.0
    if not set_a or not set_b:
        return 0, 0.0

    intersection_count = len(set_a & set_b)
    total_shingles = len(set_a) + len(set_b)
    dice = (2.0 * intersection_count) / total_shingles

    return intersection_count, dice


def required_shingle_overlap(len_a: int, len_b: int, threshold: float) -> int:
    """
    Calculates the minimum required shingle intersection count to achieve Dice >= threshold:
    required_count = ceil( (threshold / 2) * (|S_a| + |S_b|) )
    """
    if len_a + len_b == 0:
        return 0
    return math.ceil((threshold / 2.0) * (len_a + len_b))
