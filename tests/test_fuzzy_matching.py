"""
Comprehensive tests for deterministic fuzzy matching baseline.

Covers:
- Exact identical strings
- Small spelling differences ("Madhav Kumar" <-> "Madhav Kumer")
- Clearly different strings ("Rahul Sharma" <-> "Alice Brown")
- Threshold behavior (varying sensitivity thresholds)
- Empty datasets
- Invalid thresholds (validation errors)
- Logical party isolation and privacy preservation
"""

import pytest
from pydantic import ValidationError

from app.matching.similarity import (
    levenshtein_distance,
    normalized_similarity,
    ThresholdPolicy,
)
from app.matching.fuzzy_match import (
    FuzzyMatcher,
    AliceFuzzyParty,
    BobFuzzyParty,
)
from app.models.schemas import FuzzyMatchRequest


def test_levenshtein_distance_and_similarity():
    """Verify core deterministic string distance calculations."""
    # Identical
    assert levenshtein_distance("hello", "hello") == 0
    assert normalized_similarity("hello", "hello") == 1.0

    # Empty cases
    assert levenshtein_distance("", "") == 0
    assert normalized_similarity("", "") == 1.0
    assert levenshtein_distance("abc", "") == 3
    assert normalized_similarity("abc", "") == 0.0

    # 1 edit substitution ("Madhav Kumar" vs "Madhav Kumer", len 12)
    dist = levenshtein_distance("Madhav Kumar", "Madhav Kumer")
    assert dist == 1
    sim = normalized_similarity("Madhav Kumar", "Madhav Kumer")
    assert abs(sim - (1.0 - 1.0 / 12.0)) < 1e-6


def test_fuzzy_exact_identical_strings():
    """Verify that identical strings produce matches with similarity 1.0."""
    matcher = FuzzyMatcher(default_threshold=0.85)
    alice = ["John Smith", "Jane Doe"]
    bob = ["Jane Doe", "John Smith"]

    matches, a_len, b_len, policy = matcher.match(alice, bob)

    assert a_len == 2
    assert b_len == 2
    assert len(matches) == 2

    match_dict = {(m.alice_record, m.bob_record): m.similarity for m in matches}
    assert ("John Smith", "John Smith") in match_dict
    assert match_dict[("John Smith", "John Smith")] == 1.0
    assert ("Jane Doe", "Jane Doe") in match_dict
    assert match_dict[("Jane Doe", "Jane Doe")] == 1.0


def test_fuzzy_small_spelling_differences():
    """
    Verify approximate matching for small spelling variations:
    'Madhav Kumar' <-> 'Madhav Kumer'
    """
    matcher = FuzzyMatcher(default_threshold=0.85)
    alice = ["Madhav Kumar", "John Smith", "Rahul Sharma"]
    bob = ["Madhav Kumer", "Alice Brown", "John Smith"]

    matches, a_len, b_len, _ = matcher.match(alice, bob, threshold=0.85)

    assert a_len == 3
    assert b_len == 3
    # Exactly two matches expected: John Smith (exact) and Madhav Kumar/Kumer (fuzzy)
    assert len(matches) == 2

    # Check the fuzzy match
    fuzzy_pair = next((m for m in matches if m.alice_record == "Madhav Kumar"), None)
    assert fuzzy_pair is not None
    assert fuzzy_pair.bob_record == "Madhav Kumer"
    assert fuzzy_pair.similarity > 0.90  # ~0.9167

    # Check exact match
    exact_pair = next((m for m in matches if m.alice_record == "John Smith"), None)
    assert exact_pair is not None
    assert exact_pair.bob_record == "John Smith"
    assert exact_pair.similarity == 1.0


def test_fuzzy_clearly_different_strings():
    """Verify that dissimilar strings produce no matches."""
    matcher = FuzzyMatcher(default_threshold=0.80)
    alice = ["Rahul Sharma", "Red Apple"]
    bob = ["Alice Brown", "Green Zebra"]

    matches, a_len, b_len, _ = matcher.match(alice, bob)

    assert a_len == 2
    assert b_len == 2
    assert len(matches) == 0


def test_fuzzy_threshold_behavior():
    """
    Verify that increasing or decreasing the threshold dynamically alters match decisions:
    'Madhav Kumar' vs 'Madhav Kumer' similarity is ~0.9167.
    """
    matcher = FuzzyMatcher()
    alice = ["Madhav Kumar"]
    bob = ["Madhav Kumer"]

    # Threshold 0.90: similarity 0.9167 >= 0.90 -> Match
    matches_90, _, _, _ = matcher.match(alice, bob, threshold=0.90)
    assert len(matches_90) == 1
    assert matches_90[0].similarity == 0.9167

    # Threshold 0.95: similarity 0.9167 < 0.95 -> No Match
    matches_95, _, _, _ = matcher.match(alice, bob, threshold=0.95)
    assert len(matches_95) == 0

    # Threshold 0.50: similarity 0.9167 >= 0.50 -> Match
    matches_50, _, _, _ = matcher.match(alice, bob, threshold=0.50)
    assert len(matches_50) == 1


def test_fuzzy_empty_datasets():
    """Verify handling when either or both datasets are empty."""
    matcher = FuzzyMatcher()

    # Both empty
    matches, a_len, b_len, _ = matcher.match([], [])
    assert matches == []
    assert a_len == 0
    assert b_len == 0

    # Alice empty
    matches, a_len, b_len, _ = matcher.match([], ["Record A"])
    assert matches == []
    assert a_len == 0
    assert b_len == 1

    # Bob empty
    matches, a_len, b_len, _ = matcher.match(["Record A"], [])
    assert matches == []
    assert a_len == 1
    assert b_len == 0


def test_fuzzy_invalid_thresholds():
    """Verify that invalid threshold values trigger validation errors."""
    # Policy level validation
    with pytest.raises(ValueError):
        ThresholdPolicy(threshold=-0.1)

    with pytest.raises(ValueError):
        ThresholdPolicy(threshold=1.01)

    # Pydantic schema validation
    with pytest.raises(ValidationError):
        FuzzyMatchRequest(
            alice_data=["item"],
            bob_data=["item"],
            threshold=-0.5,
        )

    with pytest.raises(ValidationError):
        FuzzyMatchRequest(
            alice_data=["item"],
            bob_data=["item"],
            threshold=1.5,
        )


def test_fuzzy_party_logical_separation_and_privacy():
    """
    Verify that party datasets remain encapsulated in party objects and
    unmatched records are never surfaced.
    """
    alice_data = ["sensitive_alice_only_1", "shared_target"]
    bob_data = ["sensitive_bob_only_2", "shared_target"]

    alice_party = AliceFuzzyParty(alice_data)
    bob_party = BobFuzzyParty(bob_data)

    assert alice_party.dataset_size == 2
    assert bob_party.dataset_size == 2
    # Ensure distinct objects
    assert alice_party.items != bob_party.items

    matcher = FuzzyMatcher(default_threshold=0.90)
    matches, _, _, _ = matcher.match(alice_data, bob_data)

    # Only shared_target matches
    assert len(matches) == 1
    assert matches[0].alice_record == "shared_target"
    assert matches[0].bob_record == "shared_target"

    # Verify sensitive unshared records are NOT anywhere in the matched output
    output_records = [m.alice_record for m in matches] + [m.bob_record for m in matches]
    assert "sensitive_alice_only_1" not in output_records
    assert "sensitive_bob_only_2" not in output_records
