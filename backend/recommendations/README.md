# Module: Automated Recommendation Engine

## Goal
Map a user's score to eligible financial products from the catalog — this is its own required
output ("Automated Recommendation Engine"), separate from the raw score.

## Tech stack
Pure Python. Simple filter/rank logic — no ML needed for the must-have version.

## Input
- `ScoreResult` (from `scoring_engine/` or `ml_engine/`) — specifically `total_score`
- `Product` list (from `data/`, parsed from `product_catalog.json`)

## Output (contract with `backend/api/` and frontend)
```json
{
  "user_id": "U1001",
  "recommendations": [
    {"product_id": "P001", "name": "Starter Credit Card", "interest_rate": 24.0,
     "eligible": true, "reason": "Score 742 meets minimum 650 for Starter Card"},
    {"product_id": "P004", "name": "Premium Card", "interest_rate": 14.0,
     "eligible": false, "reason": "Score 742 is 108 points below the 850 required"}
  ]
}
```

## Starter code
```python
from common.schemas import Recommendation, Product

def recommend_products(total_score: int, products: list[Product]) -> list[Recommendation]:
    recs = []
    for p in sorted(products, key=lambda x: x.min_score_required):
        eligible = total_score >= p.min_score_required
        gap = p.min_score_required - total_score
        reason = (f"Score {total_score} meets minimum {p.min_score_required} for {p.name}"
                  if eligible else
                  f"Score {total_score} is {gap} points below the {p.min_score_required} required")
        recs.append(Recommendation(product_id=p.product_id, name=p.name,
                                    interest_rate=p.interest_rate, eligible=eligible, reason=reason))
    return recs
```

## Good-to-have: Dynamic Product Mapping
Re-run `recommend_products()` every time the score changes (e.g. after the What-If simulator
runs) so recommendations update live — no separate code needed, just call this function again
with the new score.

## Tasks checklist
- [ ] Implement `recommend_products(total_score, products) -> list[Recommendation]`
- [ ] Sort output so eligible products appear first, ranked by lowest interest rate
- [ ] (Stretch) re-call this after `/simulate` runs, so frontend shows "before vs after" recs

## Handoff
Expose `recommend_products(total_score: int, products: list[Product]) -> list[Recommendation]`
for `backend/api/` (used in `GET /recommendations/{user_id}` and inside `/score/{user_id}`).
