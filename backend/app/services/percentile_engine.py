"""
Zero to GEO — Percentile Scoring Engine.

Objective percentile-based search performance scoring.
No invented confidence scores. No generic SEO scores.

This measures actual visibility:
  - Google Map Pack position → percentile
  - AI search citation state → percentile
  - Combined → overall visibility percentile
  - Market loss = 100 - overall percentile

The percentile tells the customer exactly where they stand
relative to the market, not an arbitrary score.
"""

from typing import Optional


def calculate_map_percentile(rank: Optional[int]) -> int:
    """
    Maps Google Map Pack position (1-10) to an objective percentile.

    Rank #1 = 90th percentile (top of local pack)
    Rank #2 = 80th percentile
    ...
    Rank #10 = 0th percentile
    Unranked = 0th percentile
    """
    if rank is None or rank > 10 or rank < 1:
        return 0
    return int(round(((10 - rank) / 10) * 100))


def calculate_ai_percentile(mentioned: bool, is_top_pick: bool) -> int:
    """
    Maps AI search citation state to an objective percentile.

    Top recommendation = 90th percentile
    Cited/mentioned = 70th percentile
    Not mentioned = 0th percentile
    """
    if not mentioned:
        return 0
    return 90 if is_top_pick else 70


def calculate_query_percentile(
    map_rank: Optional[int],
    ai_mentioned: bool,
    ai_is_top_pick: bool,
) -> dict:
    """
    Calculate combined percentile for a single query.

    Returns dict with map_percentile, ai_percentile, combined_percentile.
    """
    map_perc = calculate_map_percentile(map_rank)
    ai_perc = calculate_ai_percentile(ai_mentioned, ai_is_top_pick)
    combined = int(round((map_perc + ai_perc) / 2))

    return {
        "map_percentile": map_perc,
        "ai_percentile": ai_perc,
        "combined_percentile": combined,
    }


def run_business_audit(business_name: str, query_inputs: list[dict]) -> dict:
    """
    Run a full percentile audit for a business across multiple queries.

    Each query_input should have:
      - query: str (the search term)
      - map_rank: int | None (1-10, or None if unranked)
      - ai_mentioned: bool (cited in AI overview)
      - ai_is_top_pick: bool (primary AI recommendation)

    Returns:
      - business_name
      - query_results: list of per-query breakdowns
      - overall_percentile: average combined percentile
      - market_loss_percentage: how much market they're losing (100 - percentile)
    """
    results = []

    for q in query_inputs:
        map_rank = q.get("map_rank")
        ai_mentioned = q.get("ai_mentioned", False)
        ai_is_top_pick = q.get("ai_is_top_pick", False)

        perc = calculate_query_percentile(map_rank, ai_mentioned, ai_is_top_pick)

        # Determine AI status label
        if ai_is_top_pick:
            ai_status = "Top Recommendation"
        elif ai_mentioned:
            ai_status = "Cited"
        else:
            ai_status = "Omitted"

        results.append({
            "query": q.get("query", ""),
            "map_rank": map_rank if map_rank else None,
            "map_percentile": perc["map_percentile"],
            "ai_status": ai_status,
            "ai_percentile": perc["ai_percentile"],
            "combined_percentile": perc["combined_percentile"],
        })

    # Overall percentile = average of all query combined percentiles
    if results:
        total = sum(r["combined_percentile"] for r in results)
        overall_percentile = round(total / len(results), 1)
    else:
        overall_percentile = 0.0

    # Market loss = how much of the market you're NOT capturing
    market_loss_percentage = round(100 - overall_percentile, 1)

    return {
        "business_name": business_name,
        "query_results": results,
        "overall_percentile": overall_percentile,
        "market_loss_percentage": market_loss_percentage,
    }


def estimate_visibility_impact(severity: str, overall_percentile: float) -> dict:
    """
    Estimate the visibility impact of a finding based on severity
    and current overall percentile.

    Returns estimated percentile point loss and potential gain if fixed.
    These are ranges, not exact numbers.
    """
    # Impact scales based on severity
    impact_ranges = {
        "critical": {"loss_min": 8, "loss_max": 12, "gain_min": 10, "gain_max": 15},
        "high": {"loss_min": 5, "loss_max": 8, "gain_min": 6, "gain_max": 10},
        "medium": {"loss_min": 3, "loss_max": 5, "gain_min": 3, "gain_max": 6},
        "low": {"loss_min": 1, "loss_max": 3, "gain_min": 1, "gain_max": 3},
    }

    impact = impact_ranges.get(severity, impact_ranges["medium"])

    return {
        "estimated_loss": f"{impact['loss_min']}–{impact['loss_max']}",
        "potential_gain": f"{impact['gain_min']}–{impact['gain_max']}",
        "loss_min": impact["loss_min"],
        "loss_max": impact["loss_max"],
        "gain_min": impact["gain_min"],
        "gain_max": impact["gain_max"],
    }
