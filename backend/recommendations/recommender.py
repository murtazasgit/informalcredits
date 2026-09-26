"""
Recommendation engine — matches user score to eligible financial products.
Simple filter/rank logic, no ML needed.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.schemas import Recommendation, Product


def recommend_products(total_score: int, products: list[Product]) -> list[Recommendation]:
    """
    Given a user's total score and product catalog, return a ranked list
    of recommendations with eligibility and reasons.
    """
    recs = []
    for p in sorted(products, key=lambda x: x.min_score_required):
        eligible = total_score >= p.min_score_required
        gap = p.min_score_required - total_score
        if eligible:
            reason = f"Score {total_score} meets the minimum {p.min_score_required} required for {p.name}"
        else:
            reason = f"Score {total_score} is {gap} points below the {p.min_score_required} required for {p.name}"
        recs.append(Recommendation(
            product_id=p.product_id,
            name=p.name,
            interest_rate=p.interest_rate,
            eligible=eligible,
            reason=reason,
            min_score_required=p.min_score_required,
        ))

    # Sort: eligible first (by lowest interest), then ineligible
    recs.sort(key=lambda r: (not r.eligible, r.interest_rate))
    return recs
