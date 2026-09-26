# Module: Backend API (FastAPI) — integration hub

## Goal
Wire together `data/`, `scoring_engine/`, `ml_engine/`, `explainability/`, and `reports/` behind
a REST API, backed by SQLite, with auth for the two user modes (User / Business-Lender).

## Tech stack
- **FastAPI** — routing, validation, auto `/docs`
- **SQLAlchemy + SQLite** — persistence (`database/` owns the schema)
- **FastAPI-Users** or **python-jose (JWT)** — auth with two roles: `user`, `lender`

## Endpoints

| Method | Path | Input | Output | Notes |
|---|---|---|---|---|
| POST | `/users/register` | demographic JSON | `{user_id}` | creates profile |
| POST | `/transactions/upload` | CSV/JSON file | `{status}` | calls `data/` ingestion |
| POST | `/score/{user_id}` | — | score breakdown JSON | calls `scoring_engine` (+ `ml_engine` if flag set) |
| GET | `/score/{user_id}` | — | cached score JSON | reads from DB |
| GET | `/explain/{user_id}` | — | factors JSON | calls `explainability` |
| GET | `/report/{user_id}` | — | PDF file | calls `reports` |
| POST | `/simulate` | `{user_id, hypothetical_changes}` | new score + delta | "What-If" simulator |
| POST | `/auth/login` | `{username, password, role}` | JWT token | role = user or lender |
| GET | `/lender/candidates` | query params (score range, city_tier) | anonymized list | lender-only, JWT required |
| POST | `/lender/offer` | `{user_id, product_id}` | `{status}` | push offer to user dashboard |

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
from reports import generate_report

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

## Tasks checklist
- [ ] Set up SQLAlchemy models (see `database/README.md`)
- [ ] Implement all endpoints in the table above
- [ ] Implement JWT auth with two roles
- [ ] Implement anonymization logic for `/lender/candidates`
- [ ] Wire CORS so the frontend (different port) can call the API
- [ ] Write at least 2 integration tests (happy path + missing-data path)

## Handoff
This is the integration point — everyone else's module gets imported here. Keep interfaces
matching exactly what each module's README promises as its "Output"/"Handoff".

## Additional endpoints (added for full spec coverage)

| Method | Path | Input | Output | Notes |
|---|---|---|---|---|
| GET | `/recommendations/{user_id}` | — | `list[Recommendation]` | calls `backend/recommendations/` |
| GET | `/export/{user_id}` | — | JSON credit profile | full `ScoreResult` + `ExplainResult` as downloadable JSON — satisfies "Export Options" |
| POST | `/target-achievement` | `{user_id, target_product_id}` | counterfactual suggestion | calls `backend/ml_engine/` Case 3 (stretch) |
| POST | `/offers/{offer_id}/accept` | — | bank disbursal result | calls `backend/bank_integration_mock/` (stretch) |
| POST | `/auth/register` | `{username, password, role}` | `{user_id}` | for new user onboarding |

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
