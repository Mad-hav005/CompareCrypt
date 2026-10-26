"""
Implementation of Oblivious Pseudorandom Function (OPRF) using the 2Hash-DH construction.

Cryptographic Foundation:
- Group: RFC 3526 2048-bit MODP Group (Group 14).
- Safe prime p = 2q + 1, where q is also prime.
- Prime-order subgroup: Quadratic residues modulo p, QR_p = {x^2 mod p : x in Z_p^*}.
  The order of QR_p is exactly q = (p - 1) / 2.
- Security Assumption: Decisional Diffie-Hellman (DDH) assumption in QR_p.
- Blinding: Unconditionally hiding under uniform random scalar r in [2, q-1].
- Randomness: Cryptographically secure pseudo-random number generator (secrets module).
"""

import secrets
from typing import Tuple

from app.crypto.crypto_interface import BaseGroup, BaseOPRFClient, BaseOPRFServer
from app.crypto.hashing import domain_separated_hash, finalize_oprf_hash

# RFC 3526 2048-bit MODP Group (Group 14) safe prime
RFC3526_2048_PRIME_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AACAA68FFFFFFFFFFFFFFFF"
)


class RFC3526Group14(BaseGroup):
    """
    Standard RFC 3526 2048-bit MODP cyclic group.
    Group operations operate on the prime-order subgroup of quadratic residues QR_p.
    """

    def __init__(self) -> None:
        self.p: int = int(RFC3526_2048_PRIME_HEX, 16)
        self.q: int = (self.p - 1) // 2  # Subgroup prime order
        self.g: int = 2

    @property
    def order(self) -> int:
        """Prime order of the quadratic residue subgroup."""
        return self.q

    def hash_to_group(self, data: str) -> int:
        """
        Deterministically maps an arbitrary string to a non-identity element in QR_p.

        Computes: m = int(H_1(data)) mod p.
        Squares: elem = m^2 mod p.
        Since q is prime, every quadratic residue other than 1 and p-1 has exact order q.
        """
        digest = domain_separated_hash("HASH_TO_GROUP", data)
        m = int.from_bytes(digest, byteorder="big") % self.p
        if m <= 1 or m == self.p - 1:
            m = 3  # Deterministic non-trivial fallback
        elem = pow(m, 2, self.p)
        if elem <= 1 or elem == self.p - 1:
            elem = 4
        return elem

    def exponentiate(self, base: int, exponent: int) -> int:
        """Computes base^exponent mod p."""
        return pow(base, exponent, self.p)

    def inverse_scalar(self, scalar: int) -> int:
        """Computes modular inverse of scalar mod q (subgroup order)."""
        return pow(scalar, -1, self.q)

    def random_scalar(self) -> int:
        """
        Generates a cryptographically secure random non-zero scalar in [2, q-1]
        using secrets.randbelow.
        """
        return secrets.randbelow(self.q - 2) + 2

    def serialize_element(self, element: int) -> bytes:
        """Canonical 256-byte representation of a group element."""
        return element.to_bytes(256, byteorder="big")


# Default shared group instance
default_group = RFC3526Group14()


class OPRFClient(BaseOPRFClient):
    """
    OPRF Client implementation.
    
    Flow:
    1. For each input x, client chooses random blinding scalar r in [2, q-1].
    2. Maps x to group point H_G(x) in QR_p.
    3. Computes blinded point: A = H_G(x)^r mod p.
    4. Sends A to OPRFServer.
    5. Receives evaluated point B = A^k mod p.
    6. Unblinds: P = B^{r^{-1} mod q} mod p = H_G(x)^k mod p.
    7. Computes finalized PRF output: F(k, x) = H_2(x, P).
    """

    def __init__(self, group: BaseGroup = default_group) -> None:
        self.group = group

    def blind(self, input_item: str) -> Tuple[int, int]:
        """
        Blinds an input item using a freshly generated secret blinding scalar.

        Returns:
            (blinded_element, blinding_scalar)
        """
        point = self.group.hash_to_group(input_item)
        r = self.group.random_scalar()
        blinded_element = self.group.exponentiate(point, r)
        return blinded_element, r

    def finalize(self, input_item: str, evaluated_element: int, blinding_scalar: int) -> bytes:
        """
        Unblinds evaluated element and returns finalized OPRF output.
        """
        r_inv = self.group.inverse_scalar(blinding_scalar)
        unblinded_element = self.group.exponentiate(evaluated_element, r_inv)
        element_bytes = self.group.serialize_element(unblinded_element)
        return finalize_oprf_hash(input_item, element_bytes)


class OPRFServer(BaseOPRFServer):
    """
    OPRF Server implementation.

    Holds the secret key k in [2, q-1].
    
    Flow:
    1. For blinded client element A, evaluates: B = A^k mod p.
    2. For own dataset item y, computes directly:
       Q = H_G(y)^k mod p
       and returns F(k, y) = H_2(y, Q).
    """

    def __init__(self, group: BaseGroup = default_group, key: int = None) -> None:
        self.group = group
        self._key = key if key is not None else self.group.random_scalar()

    @property
    def key(self) -> int:
        """The server's secret scalar key."""
        return self._key

    def evaluate(self, blinded_element: int) -> int:
        """
        Evaluates the client's blinded element: B = A^k mod p.
        """
        return self.group.exponentiate(blinded_element, self._key)

    def evaluate_direct(self, input_item: str) -> bytes:
        """
        Directly evaluates PRF on server's own item: F(k, y) = H_2(y, H_G(y)^k mod p).
        """
        point = self.group.hash_to_group(input_item)
        evaluated_point = self.group.exponentiate(point, self._key)
        element_bytes = self.group.serialize_element(evaluated_point)
        return finalize_oprf_hash(input_item, element_bytes)
