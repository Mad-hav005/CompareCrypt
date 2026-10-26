"""
Private Set Intersection (PSI) Protocol based on Oblivious Pseudorandom Functions (OPRF).

Protocol Flow (Client Alice, Server Bob):
--------------------------------------------------------------------------------
Alice (Private inputs: X = {x_1, ..., x_n})
Bob   (Private inputs: Y = {y_1, ..., y_m}, Secret key: k)

Phase 1: Blinding (Alice)
  - For each x_i in X:
      Alice generates random scalar r_i in [2, q-1]
      Blinded point: A_i = H_G(x_i)^{r_i} mod p
  - Alice sends [A_1, ..., A_n] to Bob.
  - PRIVACY NOTE: A_i is uniformly distributed in QR_p; Bob learns nothing about x_i.

Phase 2: Evaluation & Hash Set Generation (Bob)
  - For each blinded point A_i from Alice:
      Evaluated point: B_i = (A_i)^k mod p
  - For each y_j in Y:
      Bob computes direct PRF output: Z_j = F(k, y_j) = H_2(y_j, H_G(y_j)^k mod p)
  - Bob shuffles the set of {Z_j} so index ordering does not leak information.
  - Bob sends back ([B_1, ..., B_n], shuffled({Z_j})) to Alice.

Phase 3: Unblinding & Intersection (Alice)
  - For each x_i in X:
      Alice unblinds: P_i = (B_i)^{r_i^{-1} mod q} mod p = H_G(x_i)^k mod p
      Alice finalizes PRF output: F(k, x_i) = H_2(x_i, P_i)
  - Alice checks if F(k, x_i) in {Z_j}.
  - If match is found, x_i is in the intersection X cap Y.
  - Alice outputs Intersection = {x_i in X : F(k, x_i) in {Z_j}}.
--------------------------------------------------------------------------------
Information Exchanged:
- Alice -> Bob: Blinded group elements {A_i} (2048-bit integers). No plaintext.
- Bob -> Alice: Evaluated group elements {B_i} and pseudorandom 32-byte hash digests {Z_j}.
  No plaintext from Bob's dataset is ever sent or recoverable (under DDH assumption).
"""

import random
from typing import List, Tuple, Set

from app.crypto.crypto_interface import BasePSIProtocol
from app.crypto.oprf import OPRFClient, OPRFServer, default_group


class AliceParty:
    """
    Represents the client party (Alice) in the PSI protocol.
    Maintains complete isolation of Alice's dataset and secret blinding scalars.
    """

    def __init__(self, items: List[str]) -> None:
        self._items: List[str] = list(dict.fromkeys(items))  # preserve order, eliminate duplicates
        self._client: OPRFClient = OPRFClient(default_group)
        self._blinding_factors: List[int] = []

    @property
    def dataset_size(self) -> int:
        return len(self._items)

    def phase1_blind_inputs(self) -> List[int]:
        """
        Computes blinded group elements for all private inputs.
        Stores secret blinding factors locally.
        """
        blinded_elements: List[int] = []
        self._blinding_factors = []

        for item in self._items:
            blinded_elem, r = self._client.blind(item)
            blinded_elements.append(blinded_elem)
            self._blinding_factors.append(r)

        return blinded_elements

    def phase3_compute_intersection(
        self,
        evaluated_elements: List[int],
        server_prf_digests: Set[bytes],
    ) -> List[str]:
        """
        Unblinds server evaluations, computes Alice's PRF outputs,
        and matches against server's PRF digests.

        Returns:
            List of matching items from Alice's dataset.
        """
        if len(evaluated_elements) != len(self._items):
            raise ValueError("Mismatched number of evaluated elements received from server.")

        matches: List[str] = []
        for item, eval_elem, r in zip(self._items, evaluated_elements, self._blinding_factors):
            alice_prf = self._client.finalize(item, eval_elem, r)
            if alice_prf in server_prf_digests:
                matches.append(item)

        # Clear secret blinding factors after protocol completion
        self._blinding_factors.clear()
        return matches


class BobParty:
    """
    Represents the server party (Bob) in the PSI protocol.
    Maintains complete isolation of Bob's dataset and secret scalar key.
    """

    def __init__(self, items: List[str], server_key: int = None) -> None:
        self._items: List[str] = list(dict.fromkeys(items))
        self._server: OPRFServer = OPRFServer(default_group, key=server_key)

    @property
    def dataset_size(self) -> int:
        return len(self._items)

    def phase2_evaluate_and_hash(
        self,
        blinded_elements: List[int],
    ) -> Tuple[List[int], List[bytes]]:
        """
        Evaluates client's blinded elements and computes PRF outputs for Bob's own items.

        Returns:
            Tuple of:
            - evaluated_elements: Client's points raised to Bob's secret key k mod p
            - server_prf_digests: Shuffled list of Bob's 32-byte PRF hashes
        """
        # Evaluate Alice's blinded points
        evaluated_elements = [
            self._server.evaluate(blinded_point)
            for blinded_point in blinded_elements
        ]

        # Evaluate Bob's own dataset directly
        server_prf_digests = [
            self._server.evaluate_direct(item)
            for item in self._items
        ]

        # Shuffle Bob's PRF outputs so positional alignment reveals no information
        random.shuffle(server_prf_digests)

        return evaluated_elements, server_prf_digests


class OPRFExactPSI(BasePSIProtocol):
    """
    Orchestrator for the OPRF-based exact Private Set Intersection protocol.
    Simulates the two-party exchange with strict logical isolation between parties.
    """

    def run_protocol(self, client_items: List[str], server_items: List[str]) -> List[str]:
        """
        Runs the PSI protocol between simulated independent Alice and Bob parties.

        Args:
            client_items: Alice's dataset.
            server_items: Bob's dataset.

        Returns:
            The exact intersection discovered by Alice.
        """
        # 1. Instantiate independent parties
        alice = AliceParty(client_items)
        bob = BobParty(server_items)

        # Phase 1: Alice blinds her inputs
        blinded_payload = alice.phase1_blind_inputs()

        # Phase 2: Bob evaluates Alice's elements and computes PRF on his items
        evaluated_elements, server_prf_digests = bob.phase2_evaluate_and_hash(blinded_payload)

        # Phase 3: Alice unblinds and matches against server PRF digests
        server_prf_set = set(server_prf_digests)
        matches = alice.phase3_compute_intersection(evaluated_elements, server_prf_set)

        return matches
