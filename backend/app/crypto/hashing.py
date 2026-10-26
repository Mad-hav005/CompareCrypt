"""
Cryptographic hashing functions with domain separation.

Provides deterministic mapping and random oracle behavior using SHA-256.
Follows standard practices: all hash usages employ distinct domain separation tags
to prevent cross-protocol and cross-context collision attacks.
"""

import hashlib
from typing import Union


def sha256_digest(data: Union[str, bytes]) -> bytes:
    """Computes standard SHA-256 digest of input."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).digest()


def domain_separated_hash(domain_tag: str, *data: Union[str, bytes]) -> bytes:
    """
    Computes SHA-256 with an explicit domain separation prefix.

    Args:
        domain_tag: Context-specific prefix preventing domain confusion.
        *data: Data chunks to be sequentially absorbed.

    Returns:
        32-byte digest.
    """
    hasher = hashlib.sha256()
    hasher.update(f"COMPARECRYPT_DOMAIN_{domain_tag}:".encode("utf-8"))
    for item in data:
        if isinstance(item, str):
            item = item.encode("utf-8")
        # Prefix length to prevent canonicalization / length extension ambiguity
        hasher.update(len(item).to_bytes(4, byteorder="big"))
        hasher.update(item)
    return hasher.digest()


def finalize_oprf_hash(item: str, evaluated_point_bytes: bytes) -> bytes:
    """
    Finalizes the OPRF output using domain-separated hash: H_2(tag || item || evaluated_point).

    Args:
        item: The input string.
        evaluated_point_bytes: Canonical byte representation of the evaluated group element.

    Returns:
        32-byte pseudorandom evaluation.
    """
    return domain_separated_hash("OPRF_FINALIZE", item.encode("utf-8"), evaluated_point_bytes)
