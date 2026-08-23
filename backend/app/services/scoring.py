"""
Zero to GEO — Scoring engine (Phase 7).

Calculates the weighted overall GEO score from six pillar scores.
Weights sourced from ScoringWeights config — never hard-coded here.
"""

from app.config import ScoringWeights


def calculate_overall_score(pillar_scores: dict) -> float:
    """
    Calculate the weighted overall GEO score (0–100).

    pillar_scores: dict of pillar_key → {"score": float, ...}
    Weights come from ScoringWeights configuration (ADR-003).
    """
    weights = ScoringWeights.as_dict()

    weighted_sum = 0.0
    total_weight = 0.0

    for pillar_key, weight in weights.items():
        if pillar_key in pillar_scores:
            score = float(pillar_scores[pillar_key]["score"])
            weighted_sum += score * weight
            total_weight += weight

    if total_weight == 0:
        return 0.0

    # Normalize in case some pillars are missing (shouldn't happen, but defensive)
    overall = weighted_sum / total_weight
    return round(min(100.0, max(0.0, overall)), 2)
