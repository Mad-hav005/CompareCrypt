"""
Deterministic string similarity metrics and policy abstractions.

NOTE: No Machine Learning is used here. These are purely deterministic mathematical
algorithms for string similarity, prepared modularly for future fuzzy matching stages.
"""

from abc import ABC, abstractmethod


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Computes standard Levenshtein (edit) distance between two strings.
    Memory-efficient two-row dynamic programming algorithm.
    """
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1] + [0] * len(s2)
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row[j + 1] = min(insertions, deletions, substitutions)
        previous_row = current_row

    return previous_row[-1]


def normalized_similarity(s1: str, s2: str) -> float:
    """
    Computes normalized string similarity in range [0.0, 1.0].
    similarity = 1.0 - (levenshtein_distance / max_len)
    """
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return max(0.0, 1.0 - (dist / max_len))


class MatchingPolicy(ABC):
    """
    Abstract interface for matching decisions.
    Allows pluggable policies (fixed threshold, adaptive policy, etc.)
    without changing underlying cryptographic or matching layers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the matching policy."""
        pass

    @abstractmethod
    def score(self, item_a: str, item_b: str) -> float:
        """Calculates deterministic similarity score in range [0.0, 1.0]."""
        pass

    @abstractmethod
    def is_match(self, item_a: str, item_b: str) -> bool:
        """Determines if two items match under this policy."""
        pass


class ThresholdPolicy(MatchingPolicy):
    """
    Deterministic threshold-based similarity policy.
    Matches if normalized edit similarity >= threshold.
    """

    def __init__(self, threshold: float = 0.85) -> None:
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def name(self) -> str:
        return f"NormalizedLevenshteinThreshold(threshold={self._threshold:.2f})"

    def score(self, item_a: str, item_b: str) -> float:
        return normalized_similarity(item_a, item_b)

    def is_match(self, item_a: str, item_b: str) -> bool:
        return self.score(item_a, item_b) >= self._threshold

