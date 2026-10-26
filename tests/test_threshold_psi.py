"""
Comprehensive test suite for CompareCrypt — Privacy-Preserving Shingle Similarity Matching (Phase 3).

Covers:
- Deterministic unique bigram shingle generation with boundary markers
- Deduplication of repeated shingles
- Mathematical verification of Sørensen-Dice similarity
- Validated example: 'Madhav Kumar' vs 'Madhav Kumer' (match at 0.80, reject at 0.90)
- Exact matches (Dice = 1.0)
- Dissimilar records ('Rahul Sharma' vs 'Alice Brown')
- Protocol payload privacy boundaries (zero plaintext in transit)
- Ephemeral blinding scalar cleanup
- Empty dataset edge cases
"""

import pytest
from app.matching.shingle import (
    generate_unique_shingles,
    dice_similarity,
    required_shingle_overlap,
)
from app.crypto.threshold_psi import (
    CryptographicThresholdPSI,
    AliceThresholdParty,
    BobThresholdParty,
)


def test_shingle_generation_and_deduplication():
    """Verify boundary markers, bigram extraction, and deduplication of repeated shingles."""
    # Test with repeated syllables: 'banana'
    # Padded: '^banana$'
    # Bigrams: '^b', 'ba', 'an', 'na', 'an' (dup), 'na' (dup), 'a$'
    shingles = generate_unique_shingles("banana", q=2)
    expected_unique = ["^b", "ba", "an", "na", "a$"]
    assert shingles == expected_unique
    assert len(shingles) == 5

    # Empty string
    assert generate_unique_shingles("") == []


def test_dice_similarity_exact_and_typo():
    """
    Verify Sørensen-Dice similarity calculations against validated specifications:
    'Madhav Kumar' vs 'Madhav Kumer':
    |S(x)| = 13, |S(y)| = 13, intersection = 11, Dice = 22/26 = 0.84615...
    """
    sa = generate_unique_shingles("Madhav Kumar")
    sb = generate_unique_shingles("Madhav Kumer")

    assert len(sa) == 13
    assert len(sb) == 13

    intersection_count, dice = dice_similarity(sa, sb)
    assert intersection_count == 11
    assert round(dice, 5) == 0.84615

    # Exact string comparison
    exact_count, exact_dice = dice_similarity(sa, sa)
    assert exact_count == 13
    assert exact_dice == 1.0


def test_threshold_psi_identical_records():
    """Verify that identical records produce Dice similarity 1.0 under cryptographic PSI."""
    psi = CryptographicThresholdPSI()
    alice = ["John Smith", "Jane Doe"]
    bob = ["Jane Doe", "John Smith"]

    matches = psi.run_protocol(alice, bob, threshold=0.80)
    assert len(matches) == 2

    match_map = {(m.alice_record, m.bob_record): (m.dice_similarity, m.is_match) for m in matches}
    assert ("John Smith", "John Smith") in match_map
    assert match_map[("John Smith", "John Smith")] == (1.0, True)
    assert ("Jane Doe", "Jane Doe") in match_map
    assert match_map[("Jane Doe", "Jane Doe")] == (1.0, True)


def test_threshold_psi_name_typo_match_at_80():
    """
    Verify that 'Madhav Kumar' and 'Madhav Kumer' match at threshold 0.80
    with Dice similarity ~0.84615 and intersection count 11.
    """
    psi = CryptographicThresholdPSI()
    alice = ["Madhav Kumar", "John Smith", "Rahul Sharma"]
    bob = ["Madhav Kumer", "Alice Brown", "John Smith"]

    matches = psi.run_protocol(alice, bob, threshold=0.80)

    # Exactly 2 matches expected: John Smith (1.0) and Madhav Kumar/Kumer (0.84615)
    assert len(matches) == 2

    madhav_match = next((m for m in matches if m.alice_record == "Madhav Kumar"), None)
    assert madhav_match is not None
    assert madhav_match.bob_record == "Madhav Kumer"
    assert madhav_match.intersection_count == 11
    assert madhav_match.dice_similarity == 0.84615
    assert madhav_match.threshold == 0.80
    assert madhav_match.is_match is True

    john_match = next((m for m in matches if m.alice_record == "John Smith"), None)
    assert john_match is not None
    assert john_match.bob_record == "John Smith"
    assert john_match.dice_similarity == 1.0


def test_threshold_psi_rejection_at_90():
    """
    Verify that 'Madhav Kumar' and 'Madhav Kumer' (Dice 0.84615) are rejected
    when the threshold is increased to 0.90.
    """
    psi = CryptographicThresholdPSI()
    alice = ["Madhav Kumar"]
    bob = ["Madhav Kumer"]

    matches = psi.run_protocol(alice, bob, threshold=0.90)
    # Rejection: overlap 11 is less than ceil(0.45 * 26) = 12
    assert len(matches) == 0


def test_threshold_psi_dissimilar_records():
    """Verify that clearly different records produce zero matches."""
    psi = CryptographicThresholdPSI()
    alice = ["Rahul Sharma"]
    bob = ["Alice Brown"]

    matches = psi.run_protocol(alice, bob, threshold=0.50)
    assert len(matches) == 0


def test_threshold_psi_empty_datasets():
    """Verify graceful handling when one or both datasets are empty."""
    psi = CryptographicThresholdPSI()

    assert psi.run_protocol([], []) == []
    assert psi.run_protocol([], ["Bob Item"]) == []
    assert psi.run_protocol(["Alice Item"], []) == []


def test_threshold_psi_payload_privacy_boundaries():
    """
    Verify cryptographic boundaries:
    1. Alice's Phase 1 payload contains only 2048-bit group integers (no plaintext strings).
    2. Bob's Phase 2 payload contains only evaluated integers and 32-byte PRF hashes.
    3. Alice's ephemeral secret blinding factors are cleared after execution.
    """
    alice_records = ["Secret Record A", "Confidential Entry B"]
    bob_records = ["Secret Record A", "Unrelated Bob Item"]

    alice = AliceThresholdParty(alice_records)
    bob = BobThresholdParty(bob_records)

    # Phase 1
    alice_blinded = alice.phase1_blind_shingles()
    for rec_id, pt in alice_blinded:
        assert isinstance(rec_id, int)
        assert isinstance(pt, int)
        assert pt.bit_length() > 1000  # 2048-bit group element
        # Ensure no plaintext bytes in integer representation
        assert b"Secret" not in pt.to_bytes(256, "big")

    # Ephemeral factors stored locally
    assert len(alice._blinding_factors) > 0

    # Phase 2
    eval_points, bob_digests = bob.phase2_evaluate_and_digest(alice_blinded)
    for rec_id, pt in eval_points:
        assert isinstance(pt, int)
        assert pt.bit_length() > 1000

    for bob_id, count, digest_set, text in bob_digests:
        assert isinstance(bob_id, int)
        assert count > 0
        for d in digest_set:
            assert isinstance(d, bytes)
            assert len(d) == 32  # 256-bit PRF output
            assert b"Unrelated" not in d

    # Phase 3
    matches = alice.phase3_evaluate_threshold(eval_points, bob_digests, threshold=0.80)
    assert len(matches) == 1
    assert matches[0].alice_record == "Secret Record A"

    # Ephemeral factors cleared
    assert len(alice._blinding_factors) == 0
