"""
Pydantic data schemas for requests, responses, and protocol payloads.
"""

from typing import List
from pydantic import BaseModel, Field


class ExactMatchRequest(BaseModel):
    """Request payload for exact private set matching."""
    alice_data: List[str] = Field(..., description="Alice's private dataset records", min_length=0)
    bob_data: List[str] = Field(..., description="Bob's private dataset records", min_length=0)
    normalize: bool = Field(default=True, description="Whether to apply standard string normalization")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alice_data": ["alice@example.com", "bob@example.com", "charlie@example.com"],
                "bob_data": ["bob@example.com", "charlie@example.com", "david@example.com"],
                "normalize": True
            }
        }
    }


class ExactMatchResponse(BaseModel):
    """
    Response schema containing only the permitted matching information.
    Raw private non-matching records are strictly excluded.
    """
    matches: List[str] = Field(..., description="Identified intersection elements")
    match_count: int = Field(..., description="Total number of matching elements")
    alice_dataset_size: int = Field(..., description="Number of unique input records from Alice")
    bob_dataset_size: int = Field(..., description="Number of unique input records from Bob")
    protocol_name: str = Field(default="2Hash-DH-OPRF-PSI", description="Cryptographic protocol utilized")


class ClientBlindedPayload(BaseModel):
    """Payload sent from Client to Server in Phase 1 (Blinded group points)."""
    blinded_elements: List[str] = Field(..., description="Hex-encoded blinded group elements")


class ServerEvaluationPayload(BaseModel):
    """Payload returned from Server to Client in Phase 2."""
    evaluated_elements: List[str] = Field(..., description="Hex-encoded evaluated group elements")
    server_prf_digests: List[str] = Field(..., description="Hex-encoded shuffled PRF digests")


class FuzzyMatchPair(BaseModel):
    """A pair of records matching under the similarity policy."""
    alice_record: str = Field(..., description="Matching record from Alice's dataset")
    bob_record: str = Field(..., description="Matching record from Bob's dataset")
    similarity: float = Field(..., description="Deterministic similarity score in [0.0, 1.0]")


class FuzzyMatchRequest(BaseModel):
    """Request payload for deterministic fuzzy private set matching."""
    alice_data: List[str] = Field(..., description="Alice's private dataset records", min_length=0)
    bob_data: List[str] = Field(..., description="Bob's private dataset records", min_length=0)
    threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Minimum normalized similarity threshold [0.0, 1.0]",
    )
    normalize: bool = Field(default=True, description="Whether to apply string normalization")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alice_data": ["Madhav Kumar", "John Smith", "Rahul Sharma"],
                "bob_data": ["Madhav Kumer", "Alice Brown", "John Smith"],
                "threshold": 0.85,
                "normalize": True,
            }
        }
    }


class FuzzyMatchResponse(BaseModel):
    """
    Response schema for fuzzy matching containing only permitted match pairs.
    Non-matching private records are strictly excluded.
    """
    matches: List[FuzzyMatchPair] = Field(..., description="List of matching record pairs")
    match_count: int = Field(..., description="Total number of matching pairs")
    alice_dataset_size: int = Field(..., description="Number of unique records in Alice's dataset")
    bob_dataset_size: int = Field(..., description="Number of unique records in Bob's dataset")
    threshold: float = Field(..., description="Configured similarity threshold")
    policy: str = Field(..., description="Matching policy name used for evaluation")


class ThresholdMatchPair(BaseModel):
    """A pair of records matching under the shingle Dice similarity threshold."""
    alice_record_id: int = Field(..., description="Alice's local record index")
    bob_record_id: int = Field(..., description="Bob's local record index")
    alice_record: str = Field(..., description="Matching record string from Alice")
    bob_record: str = Field(..., description="Matching record string from Bob")
    intersection_count: int = Field(..., description="Number of shared unique shingles")
    dice_similarity: float = Field(..., description="Sørensen-Dice similarity score")
    threshold: float = Field(..., description="Configured similarity threshold")
    match_decision: bool = Field(default=True, description="Whether pair satisfies threshold")


class ThresholdMatchRequest(BaseModel):
    """Request payload for cryptographic shingle threshold matching."""
    alice_data: List[str] = Field(..., description="Alice's private dataset records", min_length=0)
    bob_data: List[str] = Field(..., description="Bob's private dataset records", min_length=0)
    threshold: float = Field(
        default=0.80,
        gt=0.0,
        le=1.0,
        description="Minimum Sørensen-Dice similarity threshold in (0.0, 1.0]",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "alice_data": ["Madhav Kumar", "John Smith", "Rahul Sharma"],
                "bob_data": ["Madhav Kumer", "Alice Brown", "John Smith"],
                "threshold": 0.80,
            }
        }
    }


class ThresholdMatchResponse(BaseModel):
    """
    Response schema for Privacy-Preserving Shingle Similarity Matching.
    Non-matching private records from either party are strictly excluded.
    """
    matches: List[ThresholdMatchPair] = Field(..., description="Identified threshold matches")
    match_count: int = Field(..., description="Total number of matching pairs")
    alice_dataset_size: int = Field(..., description="Number of unique records in Alice's dataset")
    bob_dataset_size: int = Field(..., description="Number of unique records in Bob's dataset")
    threshold: float = Field(..., description="Configured similarity threshold")
    protocol_name: str = Field(
        default="CompareCrypt — Privacy-Preserving Shingle Similarity Matching (2Hash-DH OPRF)",
        description="Underlying cryptographic protocol utilized",
    )


