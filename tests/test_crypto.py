"""
Unit tests for cryptographic primitives (RFC 3526 group operations, hashing, OPRF client/server).
"""

import pytest
from app.crypto.oprf import RFC3526Group14, OPRFClient, OPRFServer, default_group
from app.crypto.hashing import domain_separated_hash, finalize_oprf_hash, sha256_digest


def test_rfc3526_group_parameters():
    """Verify group 14 parameters and safe prime structure."""
    group = RFC3526Group14()
    assert group.p.bit_length() == 2048
    assert group.p % 2 == 1
    # Check that q = (p - 1) // 2 is prime-order relation
    assert group.q == (group.p - 1) // 2


def test_hash_to_group_deterministic():
    """Ensure hash_to_group produces deterministic non-trivial elements in QR_p."""
    group = default_group
    item = "user_identifier_12345"
    elem1 = group.hash_to_group(item)
    elem2 = group.hash_to_group(item)
    assert elem1 == elem2
    assert 1 < elem1 < group.p
    # Euler criterion: a^( (p-1)/2 ) mod p == 1 for quadratic residues
    assert pow(elem1, group.q, group.p) == 1


def test_hash_to_group_distinct_for_different_inputs():
    """Ensure distinct inputs produce distinct points."""
    group = default_group
    elem_a = group.hash_to_group("Alice")
    elem_b = group.hash_to_group("Bob")
    assert elem_a != elem_b


def test_oprf_blinding_uniqueness():
    """Verify that multiple blindings of the same input produce distinct blinded elements."""
    client = OPRFClient(default_group)
    item = "secret_record"
    blinded_1, r1 = client.blind(item)
    blinded_2, r2 = client.blind(item)

    # Random scalars should be distinct
    assert r1 != r2
    # Blinded representations must be distinct
    assert blinded_1 != blinded_2


def test_oprf_roundtrip_correctness():
    """
    Verify that Client unblinded evaluation equals Server direct evaluation
    for the exact same item under the same server key.
    """
    server = OPRFServer(default_group)
    client = OPRFClient(default_group)

    item = "common_record_xyz"

    # Client blinds
    blinded_element, r = client.blind(item)

    # Server evaluates blinded point
    evaluated_element = server.evaluate(blinded_element)

    # Client unblinds and computes PRF output
    client_prf = client.finalize(item, evaluated_element, r)

    # Server directly evaluates PRF output
    server_prf = server.evaluate_direct(item)

    # MUST match identically
    assert client_prf == server_prf
    assert len(client_prf) == 32  # 256-bit digest


def test_oprf_distinct_items_produce_distinct_prfs():
    """Verify that different items produce completely different PRF values."""
    server = OPRFServer(default_group)
    client = OPRFClient(default_group)

    blinded_a, r_a = client.blind("item_alpha")
    eval_a = server.evaluate(blinded_a)
    prf_a = client.finalize("item_alpha", eval_a, r_a)

    server_prf_b = server.evaluate_direct("item_beta")

    assert prf_a != server_prf_b


def test_oprf_different_keys_produce_different_prfs():
    """Verify that distinct server keys produce distinct evaluations for the same input."""
    server1 = OPRFServer(default_group)
    server2 = OPRFServer(default_group)
    # Extremely improbable that two random 2048-bit keys collide
    assert server1.key != server2.key

    item = "target_record"
    prf_1 = server1.evaluate_direct(item)
    prf_2 = server2.evaluate_direct(item)
    assert prf_1 != prf_2


def test_domain_separated_hash():
    """Verify domain separation changes the digest even for same suffix."""
    h1 = domain_separated_hash("TAG_A", "common_payload")
    h2 = domain_separated_hash("TAG_B", "common_payload")
    assert h1 != h2
