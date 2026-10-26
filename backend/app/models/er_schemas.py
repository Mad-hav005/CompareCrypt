"""
Pydantic schemas for the Entity Resolution (ER) subsystem.

These schemas extend the existing matching system with multi-attribute support
while keeping the core cryptographic protocol unchanged.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Dataset inspection schemas
# ---------------------------------------------------------------------------

class ColumnInfo(BaseModel):
    """Metadata about a single column in an uploaded dataset."""
    name: str = Field(..., description="Original column header name")
    index: int = Field(..., description="Zero-based column index")
    sample_values: List[str] = Field(default_factory=list, description="Up to 5 non-empty sample values")
    non_empty_count: int = Field(..., description="Number of non-empty cells in this column")


class DatasetSchema(BaseModel):
    """Schema and preview info for an uploaded dataset."""
    party: str = Field(..., description="'A' or 'B'")
    filename: str = Field(..., description="Original filename")
    row_count: int = Field(..., description="Total data rows (excluding header)")
    columns: List[ColumnInfo] = Field(..., description="Per-column metadata")
    preview_rows: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Up to 10 preview rows as column_name -> value dicts",
    )


# ---------------------------------------------------------------------------
# Attribute-mapping and job configuration schemas
# ---------------------------------------------------------------------------

class MatchStrategy(str, Enum):
    """Matching strategy for a mapped attribute pair."""
    EXACT = "exact"          # OPRF-based exact PSI
    FUZZY = "fuzzy"          # Cryptographic shingle threshold PSI
    IGNORE = "ignore"        # Attribute is excluded from matching


class AttributeMapping(BaseModel):
    """Maps one column from dataset A to one column from dataset B."""
    column_a: str = Field(..., description="Column name in dataset A")
    column_b: str = Field(..., description="Column name in dataset B")
    strategy: MatchStrategy = Field(default=MatchStrategy.FUZZY)
    weight: float = Field(default=1.0, ge=0.0, description="Importance weight for this attribute")
    fuzzy_threshold: float = Field(
        default=0.80, ge=0.01, le=1.0,
        description="Per-attribute Sørensen-Dice threshold (only used for FUZZY strategy)",
    )


class ERJobConfig(BaseModel):
    """Full configuration for an entity resolution job."""
    job_id: str = Field(..., description="Unique job identifier")
    mappings: List[AttributeMapping] = Field(..., min_length=1, description="Attribute-pair mappings")
    overall_threshold: float = Field(
        default=0.75, ge=0.0, le=1.0,
        description="Minimum weighted overall similarity to report a match",
    )
    normalize: bool = Field(default=True, description="Whether to apply standard string normalization")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "demo-job-001",
                "mappings": [
                    {"column_a": "Name", "column_b": "Full Name", "strategy": "fuzzy", "weight": 2.0, "fuzzy_threshold": 0.80},
                    {"column_a": "Email", "column_b": "Email ID", "strategy": "exact", "weight": 3.0},
                    {"column_a": "City", "column_b": "Location", "strategy": "fuzzy", "weight": 1.0, "fuzzy_threshold": 0.80},
                ],
                "overall_threshold": 0.75,
                "normalize": True,
            }
        }
    }


# ---------------------------------------------------------------------------
# Job lifecycle schemas
# ---------------------------------------------------------------------------

class ERJobPhase(str, Enum):
    QUEUED = "queued"
    BLOCKING = "blocking"          # Candidate generation phase
    MATCHING = "matching"          # Per-attribute crypto matching
    SCORING = "scoring"            # Weighted score aggregation
    COMPLETE = "complete"
    ERROR = "error"


class ERJobStatus(BaseModel):
    """Current status of a running or completed ER job."""
    job_id: str
    phase: ERJobPhase
    progress_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    candidate_pairs: int = Field(default=0, description="Candidate pairs after blocking")
    processed_pairs: int = Field(default=0, description="Pairs evaluated so far")
    match_count: int = Field(default=0, description="Pairs meeting the overall threshold so far")
    error_message: Optional[str] = None
    elapsed_ms: float = Field(default=0.0)


# ---------------------------------------------------------------------------
# Result schemas
# ---------------------------------------------------------------------------

class AttributeScore(BaseModel):
    """Score for a single mapped attribute pair."""
    column_a: str
    column_b: str
    strategy: MatchStrategy
    score: Optional[float] = Field(None, description="Similarity score [0,1] or null if ignored")
    weight: float


class EntityMatchResult(BaseModel):
    """A matched entity pair with attribute-level breakdown."""
    row_index_a: int = Field(..., description="Zero-based row index in dataset A")
    row_index_b: int = Field(..., description="Zero-based row index in dataset B")
    overall_score: float = Field(..., description="Weighted overall similarity score [0,1]")
    attribute_scores: List[AttributeScore] = Field(default_factory=list)
    is_match: bool = Field(default=True)
    # Redacted row previews (only matched rows are ever included in response)
    row_a_preview: Dict[str, str] = Field(default_factory=dict)
    row_b_preview: Dict[str, str] = Field(default_factory=dict)


class ERJobResults(BaseModel):
    """Paginated results for a completed entity resolution job."""
    job_id: str
    total_matches: int
    total_unmatched_a: int
    total_unmatched_b: int
    dataset_size_a: int
    dataset_size_b: int
    candidate_pairs_evaluated: int
    overall_threshold: float
    page: int
    page_size: int
    total_pages: int
    results: List[EntityMatchResult]
    protocol_notes: str = Field(
        default=(
            "Privacy note: Fuzzy attributes use the 2Hash-DH OPRF protocol (RFC 3526 2048-bit MODP). "
            "Exact attributes use OPRF-based exact PSI. "
            "Blocking groups records by multi-token similarity and leaks approximate structural "
            "similarity for the blocking key column; this is disclosed here. "
            "Non-matching records are excluded from the response."
        )
    )


class UploadDatasetResponse(BaseModel):
    """Response after uploading a dataset."""
    job_id: str
    party: str
    dataset_schema: DatasetSchema


class StartERJobRequest(BaseModel):
    """Request to start entity resolution using pre-uploaded datasets."""
    job_id: str
    mappings: List[AttributeMapping] = Field(..., min_length=1)
    overall_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    normalize: bool = Field(default=True)

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "demo-job-001",
                "mappings": [
                    {"column_a": "Name", "column_b": "Full Name", "strategy": "fuzzy", "weight": 2.0, "fuzzy_threshold": 0.80},
                    {"column_a": "Email", "column_b": "Email ID", "strategy": "exact", "weight": 3.0},
                ],
                "overall_threshold": 0.75,
                "normalize": True,
            }
        }
    }
