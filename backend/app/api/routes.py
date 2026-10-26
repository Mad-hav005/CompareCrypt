"""
API route definitions for Private Matching endpoints.
"""

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    ExactMatchRequest,
    ExactMatchResponse,
    FuzzyMatchRequest,
    FuzzyMatchResponse,
    ThresholdMatchRequest,
    ThresholdMatchResponse,
)
from app.services.private_matching_service import PrivateMatchingService


router = APIRouter(prefix="/api/matching", tags=["Private Matching"])
service = PrivateMatchingService()


@router.post(
    "/exact",
    response_model=ExactMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Exact Private Set Intersection",
    description=(
        "Executes a 2Hash-DH OPRF-based Private Set Intersection between Alice and Bob. "
        "Neither party's non-matching elements are exposed to the other."
    ),
)
async def match_exact(request: ExactMatchRequest) -> ExactMatchResponse:
    try:
        response = service.perform_exact_matching(request)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cryptographic protocol execution failed: {str(exc)}",
        ) from exc


@router.post(
    "/fuzzy",
    response_model=FuzzyMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Deterministic Fuzzy Private Matching",
    description=(
        "Executes deterministic approximate matching between Alice and Bob using "
        "normalized Levenshtein similarity and a configurable threshold. "
        "Non-matching private records from either party are not exposed in the response."
    ),
)
async def match_fuzzy(request: FuzzyMatchRequest) -> FuzzyMatchResponse:
    try:
        response = service.perform_fuzzy_matching(request)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fuzzy matching execution failed: {str(exc)}",
        ) from exc


@router.post(
    "/threshold-crypto",
    response_model=ThresholdMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute FuzzyCrypt Privacy-Preserving Shingle Similarity Matching",
    description=(
        "Executes a semi-honest 2Hash-DH OPRF-based threshold Private Set Intersection "
        "over unique character bigram shingles. Matches pairs whose Sørensen-Dice similarity "
        "meets or exceeds the configured threshold. Non-matching records are excluded from the response."
    ),
)
async def match_threshold_crypto(request: ThresholdMatchRequest) -> ThresholdMatchResponse:
    try:
        response = service.perform_threshold_matching(request)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cryptographic threshold matching failed: {str(exc)}",
        ) from exc


