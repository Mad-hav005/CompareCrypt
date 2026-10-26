"""Matching package."""

from app.matching.exact_match import ExactMatcher
from app.matching.fuzzy_match import (
    FuzzyMatcher,
    FuzzyMatchRecord,
    AliceFuzzyParty,
    BobFuzzyParty,
)
from app.matching.similarity import (
    levenshtein_distance,
    normalized_similarity,
    MatchingPolicy,
    ThresholdPolicy,
)
from app.matching.shingle import (
    generate_unique_shingles,
    dice_similarity,
    required_shingle_overlap,
)

__all__ = [
    "ExactMatcher",
    "FuzzyMatcher",
    "FuzzyMatchRecord",
    "AliceFuzzyParty",
    "BobFuzzyParty",
    "levenshtein_distance",
    "normalized_similarity",
    "MatchingPolicy",
    "ThresholdPolicy",
    "generate_unique_shingles",
    "dice_similarity",
    "required_shingle_overlap",
]
