# common/ — Shared Contracts (READ THIS FIRST, before writing any code)

## Why this folder exists
The #1 cause of merge pain in a 7-person hackathon repo isn't Git conflicts — it's **silent
schema drift**: person A's scoring engine returns `{"score": 742}`, person B's API expects
`{"total_score": 742}`, and nothing fails until integration night at 2am.

`schemas.py` in this folder is the single source of truth for every JSON shape that crosses a
module boundary. Every module's README below tells you which of these classes to import.

## The one rule
**Every function that returns data another module consumes must return (or be validated
against) a class from `common/schemas.py` — never a raw hand-built dict with your own field
names.**

```python
# ❌ Don't do this in scoring_engine/
def compute_score(features: dict) -> dict:
    return {"score": 742, "band": "Good"}   # field names not agreed with anyone

# ✅ Do this
from common.schemas import ScoreResult, ScoreBreakdown

def compute_score(features: UserFeatures) -> ScoreResult:
    breakdown = ScoreBreakdown(employment_stability=100, ...)
    return ScoreResult(user_id=features.user_id, total_score=742,
                        risk_category="Good", breakdown=breakdown)
```

## If you need a field that isn't in `schemas.py` yet
1. Don't add it silently to your own local dict.
2. Add it to `common/schemas.py` in your own commit, message the team channel with what you
   added and why (one line is enough), and use it.
3. Whoever owns `backend/api/` should skim every PR that touches this file, since it's the one
   file everyone shares.

## What's in here
| Class | Produced by | Consumed by |
|---|---|---|
| `Transaction`, `Demographic`, `Product` | `data/` (raw input parsing) | `data/` internally |
| `UserFeatures` | `data/` | `scoring_engine/`, `ml_engine/` |
| `ScoreBreakdown`, `ScoreResult` | `scoring_engine/` or `ml_engine/` | `explainability/`, `reports/`, `api/` |
| `Factor`, `ExplainResult` | `explainability/` | `reports/`, `api/`, frontend |
| `Recommendation` | `backend/recommendations/` | `api/`, frontend |
| `SimulationRequest`, `SimulationResult` | `api/` (calls `scoring_engine/`) | frontend |
| `CandidateSummary`, `OfferRequest`, `OfferResult` | `api/` | `frontend/lender-portal/` |

This keeps merges clean: as long as everyone imports from here, two people can build their
modules in parallel all week and the integration step is "wire the functions together", not
"debug why the field names don't match."
