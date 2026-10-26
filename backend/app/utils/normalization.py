"""
String normalization utilities.
"""

import unicodedata
from typing import List


def normalize_string(s: str, case_fold: bool = True, strip_whitespace: bool = True) -> str:
    """
    Normalizes input string for reliable deterministic cryptographic hashing.

    Args:
        s: Raw input string.
        case_fold: Whether to apply unicode case folding.
        strip_whitespace: Whether to strip leading/trailing whitespace.

    Returns:
        Normalized string.
    """
    if s is None:
        return ""
    # Unicode canonical decomposition and recomposition (NFC)
    normalized = unicodedata.normalize("NFC", s)
    if strip_whitespace:
        normalized = normalized.strip()
    if case_fold:
        normalized = normalized.casefold()
    return normalized


def normalize_dataset(items: List[str], case_fold: bool = True, strip_whitespace: bool = True) -> List[str]:
    """
    Normalizes a list of strings and deduplicates while preserving order.
    """
    normalized_list = []
    seen = set()
    for item in items:
        norm = normalize_string(item, case_fold=case_fold, strip_whitespace=strip_whitespace)
        if norm and norm not in seen:
            seen.add(norm)
            normalized_list.append(norm)
    return normalized_list
