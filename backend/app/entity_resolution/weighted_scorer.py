"""
Weighted record-level scorer.

Combines per-attribute scores into a single overall weighted similarity
and decides match/no-match against the overall threshold.
"""

from __future__ import annotations

from typing import List, Optional

from app.models.er_schemas import AttributeScore, EntityMatchResult, MatchStrategy


def compute_overall_score(attribute_scores: List[AttributeScore]) -> Optional[float]:
    """
    Compute the weighted average of non-ignored attribute scores.

    Returns None if all attributes are ignored (no meaningful score can be assigned).
    Score = Σ(weight_i * score_i) / Σ(weight_i)  for non-ignored, non-None attributes.
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for attr in attribute_scores:
        if attr.strategy == MatchStrategy.IGNORE or attr.score is None:
            continue
        total_weight += attr.weight
        weighted_sum += attr.weight * attr.score

    if total_weight == 0.0:
        return None

    return round(weighted_sum / total_weight, 5)


def build_match_result(
    row_index_a: int,
    row_index_b: int,
    attribute_scores: List[AttributeScore],
    overall_threshold: float,
    row_a_preview: dict,
    row_b_preview: dict,
) -> Optional[EntityMatchResult]:
    """
    Build an EntityMatchResult if the overall score meets the threshold.
    Returns None if score is below threshold or cannot be computed.
    """
    overall = compute_overall_score(attribute_scores)
    if overall is None or overall < overall_threshold:
        return None

    return EntityMatchResult(
        row_index_a=row_index_a,
        row_index_b=row_index_b,
        overall_score=overall,
        attribute_scores=attribute_scores,
        is_match=True,
        row_a_preview=row_a_preview,
        row_b_preview=row_b_preview,
    )
