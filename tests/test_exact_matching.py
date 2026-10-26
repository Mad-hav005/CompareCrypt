"""
Integration tests for exact private set intersection matching.
"""

import pytest
from app.crypto.psi import OPRFExactPSI, AliceParty, BobParty
from app.matching.exact_match import ExactMatcher


def test_psi_example_from_specification():
    """
    Test the canonical example from the project specification:
    Alice: {"alice@example.com", "bob@example.com", "charlie@example.com"}
    Bob:   {"bob@example.com", "charlie@example.com", "david@example.com"}
    Expected intersection: {"bob@example.com", "charlie@example.com"}
    """
    alice_data = ["alice@example.com", "bob@example.com", "charlie@example.com"]
    bob_data = ["bob@example.com", "charlie@example.com", "david@example.com"]

    psi = OPRFExactPSI()
    matches = psi.run_protocol(alice_data, bob_data)

    assert set(matches) == {"bob@example.com", "charlie@example.com"}


def test_psi_name_dataset_exact_match():
    """
    Test the name matching example from Section 1:
    Alice: "Madhav Kumar", "John Smith", "Rahul Sharma"
    Bob:   "Madhav Kumer", "Alice Brown", "John Smith"
    Expected exact match: "John Smith"
    """
    alice_data = ["Madhav Kumar", "John Smith", "Rahul Sharma"]
    bob_data = ["Madhav Kumer", "Alice Brown", "John Smith"]

    psi = OPRFExactPSI()
    matches = psi.run_protocol(alice_data, bob_data)

    assert matches == ["John Smith"]


def test_psi_disjoint_datasets():
    """Verify that completely disjoint sets return an empty intersection."""
    alice_data = ["apple", "banana", "cherry"]
    bob_data = ["durian", "elderberry", "fig"]

    psi = OPRFExactPSI()
    matches = psi.run_protocol(alice_data, bob_data)

    assert matches == []


def test_psi_identical_datasets():
    """Verify that identical sets return all elements."""
    data = ["user_1", "user_2", "user_3"]

    psi = OPRFExactPSI()
    matches = psi.run_protocol(data, list(reversed(data)))

    assert set(matches) == set(data)


def test_psi_empty_datasets():
    """Verify graceful handling when one or both datasets are empty."""
    psi = OPRFExactPSI()

    # Both empty
    assert psi.run_protocol([], []) == []

    # Alice empty
    assert psi.run_protocol([], ["item1", "item2"]) == []

    # Bob empty
    assert psi.run_protocol(["item1", "item2"], []) == []


def test_exact_matcher_with_normalization():
    """Verify ExactMatcher handles casing and trailing whitespaces appropriately."""
    matcher = ExactMatcher()

    alice_data = ["  Alice@Example.COM  ", "bob@example.com "]
    bob_data = ["alice@example.com", "BOB@EXAMPLE.COM"]

    matches, a_len, b_len = matcher.match(alice_data, bob_data, normalize=True)

    assert set(matches) == {"alice@example.com", "bob@example.com"}
    assert a_len == 2
    assert b_len == 2
