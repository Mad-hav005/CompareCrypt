"""
Deterministic Fuzzy Matching Baseline Module.

Provides approximate matching using normalized Levenshtein edit distance and
configurable matching policies without using machine learning or altering cryptographic primitives.
Maintains logical isolation between Alice's and Bob's private datasets.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from app.matching.similarity import (
    MatchingPolicy,
    ThresholdPolicy,
    normalized_similarity,
)
from app.utils.normalization import normalize_dataset, normalize_string



@dataclass(frozen=True)
class FuzzyMatchRecord:
    """Represents a validated fuzzy match between Alice's and Bob's records."""
    alice_record: str
    bob_record: str
    similarity: float


class AliceFuzzyParty:
    """
    Client party for fuzzy matching simulation.
    Maintains isolation of Alice's dataset.
    """

    def __init__(self, items: List[str]) -> None:
        self._items: List[str] = list(dict.fromkeys(items))

    @property
    def items(self) -> List[str]:
        return list(self._items)

    @property
    def dataset_size(self) -> int:
        return len(self._items)


class BobFuzzyParty:
    """
    Server party for fuzzy matching simulation.
    Maintains isolation of Bob's dataset.
    """

    def __init__(self, items: List[str]) -> None:
        self._items: List[str] = list(dict.fromkeys(items))

    @property
    def items(self) -> List[str]:
        return list(self._items)

    @property
    def dataset_size(self) -> int:
        return len(self._items)


class FuzzyMatcher:
    """
    Coordinates deterministic approximate matching between Alice and Bob.
    Uses normalized Levenshtein similarity and policy-based matching criteria.
    Ensures non-matching private records from either party are not exposed.
    """

    def __init__(self, default_threshold: float = 0.85) -> None:
        self.default_threshold = default_threshold

    def match(
        self,
        alice_data: List[str],
        bob_data: List[str],
        threshold: Optional[float] = None,
        policy: Optional[MatchingPolicy] = None,
        normalize: bool = True,
    ) -> Tuple[List[FuzzyMatchRecord], int, int, str]:
        """
        Executes deterministic fuzzy matching between Alice and Bob.

        Args:
            alice_data: Alice's dataset.
            bob_data: Bob's dataset.
            threshold: Similarity threshold in [0.0, 1.0].
            policy: Optional custom MatchingPolicy (takes precedence over threshold).
            normalize: Whether to apply string canonicalization.

        Returns:
            Tuple of (matches, alice_dataset_size, bob_dataset_size, policy_name).
        """
        # Deduplicate while preserving original input representations
        alice_raw = list(dict.fromkeys(alice_data))
        bob_raw = list(dict.fromkeys(bob_data))

        # Initialize independent parties
        alice = AliceFuzzyParty(alice_raw)
        bob = BobFuzzyParty(bob_raw)

        # Determine policy
        if policy is not None:
            active_policy = policy
        else:
            active_threshold = threshold if threshold is not None else self.default_threshold
            active_policy = ThresholdPolicy(active_threshold)

        # Perform evaluation across logical party boundary
        matches: List[FuzzyMatchRecord] = []
        for a_item in alice.items:
            comp_a = normalize_string(a_item) if normalize else a_item
            for b_item in bob.items:
                comp_b = normalize_string(b_item) if normalize else b_item
                if active_policy.is_match(comp_a, comp_b):
                    score = round(active_policy.score(comp_a, comp_b), 4)
                    matches.append(
                        FuzzyMatchRecord(
                            alice_record=a_item,
                            bob_record=b_item,
                            similarity=score,
                        )
                    )

        return matches, alice.dataset_size, bob.dataset_size, active_policy.name

