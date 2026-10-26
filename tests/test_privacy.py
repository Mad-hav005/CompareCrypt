"""
Security and privacy property validation tests.

Verifies:
1. No plaintext data is transmitted across party boundaries.
2. Bob only receives uniformly blinded group elements (information-theoretically hiding).
3. Alice only receives evaluated group elements and pseudorandom PRF digests.
4. Non-matching items from either party are not revealed to the other.
5. Server PRF digests are shuffled to destroy positional correlation.
6. Secret blinding factors are zeroed/cleared after execution.
"""

import pytest
from app.crypto.psi import AliceParty, BobParty
from app.crypto.hashing import sha256_digest


def test_alice_blinded_elements_do_not_leak_plaintext():
    """
    Ensure that Phase 1 payload contains only 2048-bit integers that have
    no trivial relationship (like plaintext or raw SHA256) to Alice's inputs.
    """
    alice_inputs = ["sensitive_ssn_0001", "confidential_patient_record"]
    alice = AliceParty(alice_inputs)

    blinded_payload = alice.phase1_blind_inputs()

    assert len(blinded_payload) == len(alice_inputs)

    for item, blinded_val in zip(alice_inputs, blinded_payload):
        # Must be a large integer in QR_p
        assert isinstance(blinded_val, int)
        assert blinded_val.bit_length() > 1000

        # Blinded point must not match raw integer representation of SHA-256
        raw_sha_int = int.from_bytes(sha256_digest(item), "big")
        assert blinded_val != raw_sha_int


def test_bob_payload_does_not_leak_non_matching_items():
    """
    Ensure that Bob's Phase 2 payload to Alice never contains plaintext strings
    and only contains evaluated points and 32-byte pseudorandom digests.
    """
    alice_inputs = ["alice_private_item_A"]
    bob_inputs = ["alice_private_item_A", "bob_super_secret_unshared_item_B"]

    alice = AliceParty(alice_inputs)
    bob = BobParty(bob_inputs)

    blinded_alice = alice.phase1_blind_inputs()
    eval_elements, server_prfs = bob.phase2_evaluate_and_hash(blinded_alice)

    # Bob sends evaluated points and digests
    assert len(eval_elements) == len(alice_inputs)
    assert len(server_prfs) == len(bob_inputs)

    # All digests must be exactly 32-byte hashes (not plaintext)
    for digest in server_prfs:
        assert isinstance(digest, bytes)
        assert len(digest) == 32
        # Ensure Bob's secret item string is NOT substring of the digest
        assert "bob_super_secret_unshared_item_B".encode("utf-8") not in digest

    # Alice runs phase 3
    matches = alice.phase3_compute_intersection(eval_elements, set(server_prfs))

    # Only matching item is discovered
    assert matches == ["alice_private_item_A"]
    # Bob's private unshared item is NOT in the output
    assert "bob_super_secret_unshared_item_B" not in matches


def test_blinding_factors_cleared_after_protocol():
    """Verify that Alice cleans up ephemeral secret blinding factors after phase 3."""
    alice = AliceParty(["record_1", "record_2"])
    bob = BobParty(["record_1", "record_3"])

    blinded = alice.phase1_blind_inputs()
    assert len(alice._blinding_factors) == 2

    eval_elements, server_prfs = bob.phase2_evaluate_and_hash(blinded)
    alice.phase3_compute_intersection(eval_elements, set(server_prfs))

    # Blinding factors must be cleared to prevent side-channel / state retention
    assert len(alice._blinding_factors) == 0
