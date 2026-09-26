# Module: Backend API (FastAPI) — integration hub

## Goal
Wire the implemented data, scoring, explainability, recommendation, and dashboard flow behind a
FastAPI service with SQLite persistence.

## Tech stack
- **FastAPI** — routing, validation, auto `/docs`
- **SQLAlchemy + SQLite** — persistence (`database/` owns the schema)

## Endpoints

| Method | Path | Input | Output | Notes |
|---|---|---|---|---|
| GET | `/` | — | health status | Includes number of loaded users |
| GET | `/users` | — | user list | IDs and score summaries |
| GET | `/users/{user_id}` | user ID | demographic record | Seeded profiles only |
| POST | `/score/{user_id}` | user ID | `ScoreResult` | Recomputes the rule-based score |
| GET | `/score/{user_id}` | user ID | `ScoreResult` | Returns cached score |
| GET | `/explain/{user_id}` | user ID | `ExplainResult` | Factor explanations |
| GET | `/recommendations/{user_id}` | user ID | recommendations | Matches the score against catalog products |
| POST | `/simulate` | `{user_id, hypothetical_changes}` | `SimulationResult` | What-if score calculation |
| GET | `/features/{user_id}` | user ID | `UserFeatures` | Feature values for debugging |
| GET | `/products` | — | product list | Loaded product catalog |
| POST | `/upload-csv` | multipart CSV file | scores and explanations for each row | Main dashboard upload flow |
| GET | `/csv-template` | — | sample row and supported columns | Use to prepare an upload |
| GET | `/lender/candidates` | score range, optional city tier | anonymized candidates | No lender UI or authentication yet |
| GET | `/export/{user_id}` | user ID | JSON credit profile | Score, explanation, and recommendations |
| GET | `/dashboard/{user_id}` | user ID | dashboard payload | Single call for the user dashboard |

## Sample I/O

**POST /score/{user_id} → response**
```json
{
  "user_id": "U1001",
  "total_score": 742,
  "risk_category": "Good",
  "breakdown": { "...": "..." }
}
```

**GET /lender/candidates → response (anonymized until offer accepted)**
```json
[
  {"candidate_ref": "C-8f21", "score": 742, "risk_category": "Good", "city_tier": "tier-1"}
]
```
Do **not** return `user_id`, name, address, or phone here — only a `candidate_ref` — per the
anonymization requirement. Resolve the real identity only after the user accepts an offer.

## Starter code
```python
from fastapi import FastAPI, Depends
from scoring_engine import compute_score
from explainability import explain_breakdown
from backend.recommendations.recommender import recommend_products

app = FastAPI(title="AltCredit API")

@app.post("/score/{user_id}")
def score_user(user_id: str):
    features = get_user_features(user_id)   # from data/
    result = compute_score(features)         # from scoring_engine/
    save_score(user_id, result)              # to database/
    return result

@app.get("/explain/{user_id}")
def explain_user(user_id: str):
    result = load_score(user_id)
    return {"user_id": user_id, "factors": explain_breakdown(result["breakdown"])}
```

The current MVP endpoints above are implemented. Authentication, registration, PDF reports, offer
management, and API integration tests are future work.

## Handoff
This is the integration point — everyone else's module gets imported here. Keep interfaces
matching exactly what each module's README promises as its "Output"/"Handoff".

## Additional endpoints (added for full spec coverage)

| Method | Path | Input | Output | Notes |
|---|---|---|---|---|
| GET | `/recommendations/{user_id}` | — | `list[Recommendation]` | calls `backend/recommendations/` |
| GET | `/export/{user_id}` | — | JSON credit profile | full `ScoreResult` + `ExplainResult` as downloadable JSON — satisfies "Export Options" |

## Use the shared schemas — do not redefine response shapes
Every request/response body in this API must be typed using classes from
`common/schemas.py` (e.g. `ScoreResult`, `ExplainResult`, `Recommendation`,
`CandidateSummary`). FastAPI will auto-validate against them and auto-generate the `/docs`
page correctly. This is what keeps the frontend team's expectations and the backend's actual
output in sync without manual coordination.

```python
from common.schemas import ScoreResult

@app.post("/score/{user_id}", response_model=ScoreResult)
def score_user(user_id: str):
    ...
```

## Logging
Add basic logging (satisfies the spec's "Code Quality & Reproducibility → Logging" requirement):
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("altcredit")

@app.post("/score/{user_id}")
def score_user(user_id: str):
    logger.info(f"Computing score for {user_id}")
    ...
```

## Updated tasks checklist
- [ ] Implement the 5 additional endpoints above
- [ ] Ensure every endpoint has a `response_model=` from `common/schemas.py`
- [ ] Add basic logging on every endpoint (request in, result out, errors)
- [ ] Add try/except around every module call so one module's failure returns a clean 4xx/5xx
      instead of crashing the whole API (robustness requirement)
