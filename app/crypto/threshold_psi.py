"""
CompareCrypt — Privacy-Preserving Shingle Similarity Matching (Phase 3).

Cryptographic Construction:
- Underlying Group: RFC 3526 2048-bit MODP Group (Group 14), Quadratic Residue Subgroup QR_p.
- OPRF: 2Hash-DH Oblivious Pseudorandom Function F(k, g) = H_2(g, H_G(g)^k mod p).
- Similarity Metric: Sørensen-Dice similarity over unique character bigram shingle sets.
- Model: Semi-honest two-party protocol with controlled leakage of shingle cardinalities and overlap counts.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Set, Optional

from app.crypto.crypto_interface import BaseGroup
from app.crypto.oprf import OPRFClient, OPRFServer, default_group
from app.crypto.hashing import finalize_oprf_hash
from app.matching.shingle import (
    generate_unique_shingles,
    required_shingle_overlap,
)


@dataclass(frozen=True)
class ThresholdMatchRecord:
    """Represents a validated similarity match between Alice's and Bob's records."""
    alice_record_id: int
    bob_record_id: int
    alice_record: str
    bob_record: str
    intersection_count: int
    dice_similarity: float
    threshold: float
    is_match: bool


class AliceThresholdParty:
    """
    Client party for Privacy-Preserving Shingle Similarity Matching.
    Manages shingle extraction, ephemeral blinding scalars, unblinding, and threshold evaluation.
    """

    def __init__(self, records: List[str], group: BaseGroup = default_group) -> None:
        self.group = group
        self._records = list(dict.fromkeys(records))  # preserve unique records
        # Precompute unique shingles for each record
        self._shingles_by_record: Dict[int, List[str]] = {
            i: generate_unique_shingles(rec) for i, rec in enumerate(self._records)
        }
        self._blinding_factors: Dict[Tuple[int, int], int] = {}  # (record_id, shingle_idx) -> r
        self._client = OPRFClient(self.group)

    @property
    def dataset_size(self) -> int:
        return len(self._records)

    def phase1_blind_shingles(self) -> List[Tuple[int, int]]:
        """
        Extracts unique shingles for each record and blinds each shingle with a fresh random scalar.

        Returns:
            List of (record_id, blinded_point) tuples. Zero plaintext strings are transmitted.
        """
        blinded_payload: List[Tuple[int, int]] = []
        self._blinding_factors.clear()

        for rec_id, shingles in self._shingles_by_record.items():
            for shingle_idx, shingle in enumerate(shingles):
                blinded_point, r = self._client.blind(shingle)
                blinded_payload.append((rec_id, blinded_point))
                self._blinding_factors[(rec_id, shingle_idx)] = r

        return blinded_payload

    def phase3_evaluate_threshold(
        self,
        evaluated_points: List[Tuple[int, int]],
        bob_digest_sets: List[Tuple[int, int, Set[bytes], str]],
        threshold: float,
    ) -> List[ThresholdMatchRecord]:
        """
        Unblinds evaluated points, derives PRF digests for Alice's shingles,
        computes shingle intersection cardinality against Bob's digest sets,
        and applies the Sørensen-Dice threshold condition.

        Args:
            evaluated_points: List of (record_id, evaluated_point) from Bob.
            bob_digest_sets: List of (bob_record_id, shingle_count, digest_set, bob_record_text) from Bob.
            threshold: Minimum Sørensen-Dice similarity threshold in (0.0, 1.0].

        Returns:
            List of ThresholdMatchRecord instances for all pairs satisfying the threshold.
        """
        # 1. Group evaluated points by record_id
        # Map: record_id -> list of evaluated points in order
        eval_by_record: Dict[int, List[int]] = {}
        for rec_id, pt in evaluated_points:
            eval_by_record.setdefault(rec_id, []).append(pt)

        # 2. Unblind and finalize PRF digests for Alice's shingles
        alice_prf_by_record: Dict[int, Set[bytes]] = {}
        for rec_id, shingles in self._shingles_by_record.items():
            eval_pts = eval_by_record.get(rec_id, [])
            if len(eval_pts) != len(shingles):
                raise ValueError(f"Mismatched evaluated shingle points for record {rec_id}")

            prf_set: Set[bytes] = set()
            for shingle_idx, (shingle, pt) in enumerate(zip(shingles, eval_pts)):
                r = self._blinding_factors.get((rec_id, shingle_idx))
                if r is None:
                    raise ValueError(f"Missing blinding scalar for record {rec_id}, shingle {shingle_idx}")
                prf_digest = self._client.finalize(shingle, pt, r)
                prf_set.add(prf_digest)

            alice_prf_by_record[rec_id] = prf_set

        # Clear ephemeral blinding factors
        self._blinding_factors.clear()

        # 3. Evaluate Sørensen-Dice overlap against Bob's digest sets
        matches: List[ThresholdMatchRecord] = []
        for rec_id, alice_prfs in alice_prf_by_record.items():
            alice_shingle_count = len(self._shingles_by_record[rec_id])
            alice_rec_text = self._records[rec_id]

            for bob_id, bob_shingle_count, bob_prfs, bob_rec_text in bob_digest_sets:
                # Shingle intersection
                intersection_count = len(alice_prfs & bob_prfs)
                total_shingles = alice_shingle_count + bob_shingle_count

                if total_shingles == 0:
                    dice = 1.0 if alice_shingle_count == bob_shingle_count else 0.0
                else:
                    dice = round((2.0 * intersection_count) / total_shingles, 5)

                req_overlap = required_shingle_overlap(alice_shingle_count, bob_shingle_count, threshold)

                if intersection_count >= req_overlap and dice >= threshold:
                    matches.append(
                        ThresholdMatchRecord(
                            alice_record_id=rec_id,
                            bob_record_id=bob_id,
                            alice_record=alice_rec_text,
                            bob_record=bob_rec_text,
                            intersection_count=intersection_count,
                            dice_similarity=dice,
                            threshold=threshold,
                            is_match=True,
                        )
                    )

        return matches


class BobThresholdParty:
    """
    Server party for Privacy-Preserving Shingle Similarity Matching.
    Evaluates Alice's blinded shingles and independently derives PRF digests for Bob's shingles.
    """

    def __init__(
        self,
        records: List[str],
        group: BaseGroup = default_group,
        server_key: Optional[int] = None,
    ) -> None:
        self.group = group
        self._records = list(dict.fromkeys(records))
        self._shingles_by_record: Dict[int, List[str]] = {
            j: generate_unique_shingles(rec) for j, rec in enumerate(self._records)
        }
        self._server = OPRFServer(self.group, key=server_key)

    @property
    def dataset_size(self) -> int:
        return len(self._records)

    @property
    def server_key(self) -> int:
        return self._server.key

    def phase2_evaluate_and_digest(
        self,
        blinded_payload: List[Tuple[int, int]],
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int, Set[bytes], str]]]:
        """
        Evaluates Alice's blinded points using Bob's secret key k, and generates
        direct PRF digests for Bob's own unique shingles.

        Args:
            blinded_payload: List of (alice_record_id, blinded_point).

        Returns:
            Tuple of:
            - evaluated_points: List of (alice_record_id, evaluated_point)
            - bob_digest_sets: List of (bob_record_id, shingle_count, prf_digest_set, bob_record_text)
        """
        # 1. Evaluate Alice's blinded points
        evaluated_points = [
            (rec_id, self._server.evaluate(blinded_pt))
            for rec_id, blinded_pt in blinded_payload
        ]

        # 2. Independently compute direct PRF digests for Bob's shingles
        bob_digest_sets: List[Tuple[int, int, Set[bytes], str]] = []
        for rec_id, shingles in self._shingles_by_record.items():
            rec_text = self._records[rec_id]
            prf_set: Set[bytes] = {
                self._server.evaluate_direct(shingle)
                for shingle in shingles
            }
            bob_digest_sets.append((rec_id, len(shingles), prf_set, rec_text))

        return evaluated_points, bob_digest_sets


class CryptographicThresholdPSI:
    """
    Protocol orchestrator for CompareCrypt Privacy-Preserving Shingle Similarity Matching.
    Simulates the two-party interaction between independent Alice and Bob instances.
    """

    def __init__(self, group: BaseGroup = default_group) -> None:
        self.group = group

    def run_protocol(
        self,
        alice_records: List[str],
        bob_records: List[str],
        threshold: float = 0.80,
    ) -> List[ThresholdMatchRecord]:
        """
        Runs the complete 3-phase shingle threshold matching protocol.

        Args:
            alice_records: Alice's dataset.
            bob_records: Bob's dataset.
            threshold: Sørensen-Dice similarity threshold in (0.0, 1.0].

        Returns:
            List of matching records meeting or exceeding threshold.
        """
        alice = AliceThresholdParty(alice_records, group=self.group)
        bob = BobThresholdParty(bob_records, group=self.group)

        # Phase 1: Alice blinds unique shingles
        blinded_payload = alice.phase1_blind_shingles()

        # Phase 2: Bob evaluates Alice's shingles and computes own PRF sets
        evaluated_points, bob_digest_sets = bob.phase2_evaluate_and_digest(blinded_payload)

        # Phase 3: Alice unblinds and evaluates threshold over intersections
        matches = alice.phase3_evaluate_threshold(evaluated_points, bob_digest_sets, threshold=threshold)

        return matches
