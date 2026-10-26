"""
Service layer for private matching operations.
"""

from app.models.schemas import (
    ExactMatchRequest,
    ExactMatchResponse,
    FuzzyMatchRequest,
    FuzzyMatchResponse,
    FuzzyMatchPair,
    ThresholdMatchRequest,
    ThresholdMatchResponse,
    ThresholdMatchPair,
)
from app.matching.exact_match import ExactMatcher
from app.matching.fuzzy_match import FuzzyMatcher
from app.crypto.threshold_psi import CryptographicThresholdPSI


class PrivateMatchingService:
    """
    Coordinates private matching requests between independent parties.
    Ensures that response payloads reveal only permitted intersection data.
    """

    def __init__(self) -> None:
        self.exact_matcher = ExactMatcher()
        self.fuzzy_matcher = FuzzyMatcher()
        self.threshold_psi = CryptographicThresholdPSI()


    def perform_exact_matching(self, request: ExactMatchRequest) -> ExactMatchResponse:
        """
        Executes exact private set matching between Alice and Bob.

        Args:
            request: ExactMatchRequest containing alice_data, bob_data, normalize.

        Returns:
            ExactMatchResponse with identified intersection and metadata.
        """
        matches, alice_len, bob_len = self.exact_matcher.match(
            alice_data=request.alice_data,
            bob_data=request.bob_data,
            normalize=request.normalize,
        )

        return ExactMatchResponse(
            matches=matches,
            match_count=len(matches),
            alice_dataset_size=alice_len,
            bob_dataset_size=bob_len,
            protocol_name="2Hash-DH-OPRF-PSI (RFC 3526 2048-bit MODP)",
        )

    def perform_fuzzy_matching(self, request: FuzzyMatchRequest) -> FuzzyMatchResponse:
        """
        Executes deterministic fuzzy matching baseline between Alice and Bob.

        Args:
            request: FuzzyMatchRequest containing alice_data, bob_data, threshold, normalize.

        Returns:
            FuzzyMatchResponse containing identified match pairs and metadata.
        """
        matches, alice_len, bob_len, policy_name = self.fuzzy_matcher.match(
            alice_data=request.alice_data,
            bob_data=request.bob_data,
            threshold=request.threshold,
            normalize=request.normalize,
        )

        match_pairs = [
            FuzzyMatchPair(
                alice_record=m.alice_record,
                bob_record=m.bob_record,
                similarity=m.similarity,
            )
            for m in matches
        ]

        return FuzzyMatchResponse(
            matches=match_pairs,
            match_count=len(match_pairs),
            alice_dataset_size=alice_len,
            bob_dataset_size=bob_len,
            threshold=request.threshold,
            policy=policy_name,
        )

    def perform_threshold_matching(self, request: ThresholdMatchRequest) -> ThresholdMatchResponse:
        """
        Executes FuzzyCrypt Privacy-Preserving Shingle Similarity Matching.

        Args:
            request: ThresholdMatchRequest containing alice_data, bob_data, threshold.

        Returns:
            ThresholdMatchResponse containing match pairs, overlap counts, and Dice scores.
        """
        alice_unique = list(dict.fromkeys(request.alice_data))
        bob_unique = list(dict.fromkeys(request.bob_data))

        matches = self.threshold_psi.run_protocol(
            alice_records=alice_unique,
            bob_records=bob_unique,
            threshold=request.threshold,
        )

        match_pairs = [
            ThresholdMatchPair(
                alice_record_id=m.alice_record_id,
                bob_record_id=m.bob_record_id,
                alice_record=m.alice_record,
                bob_record=m.bob_record,
                intersection_count=m.intersection_count,
                dice_similarity=m.dice_similarity,
                threshold=m.threshold,
                match_decision=m.is_match,
            )
            for m in matches
        ]

        return ThresholdMatchResponse(
            matches=match_pairs,
            match_count=len(match_pairs),
            alice_dataset_size=len(alice_unique),
            bob_dataset_size=len(bob_unique),
            threshold=request.threshold,
            protocol_name="FuzzyCrypt — Privacy-Preserving Shingle Similarity Matching (2Hash-DH OPRF)",
        )


