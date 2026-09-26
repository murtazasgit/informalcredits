# REQUIREMENTS_COVERAGE.md — audit of the repo against the full spec

Audit method: every item below was checked by reading the code; where possible it was also run
(backend started on :8010, endpoints hit with curl, `pytest` run — 12 existing tests pass).
Status: DONE / PARTIAL / MISSING. Tables show the **pre-implementation** audit (Part 1); the
"After Part 2" section at the bottom records what changed.

## A. Input / data ingestion
| # | Item | Status | Evidence | Notes |
|---|---|---|---|---|
| 1 | Transaction ingestion (ID, Date, Amount, Category, Type) | PARTIAL | `data/feature_engineering.py::load_transactions`, `common/schemas.py::Transaction`, `data/synthetic/transactions.csv` | CSV only — no JSON transaction loader. Transaction path is only used as a fallback when `merged_data.json` is absent. |
| 2 | Timely-payment markers for recurring bills | DONE | `Transaction.on_time`; `compute_user_features` (digital_bill_ontime_pct, on_time_payment_pct) | Users with no bill history silently get 0% (i.e. penalised, not neutral). |
| 3 | Demographic ingestion (JSON) | DONE | `load_demographics`, `data/synthetic/demographics.json`, `common/schemas.py::Demographic` | All 6 required fields present. |
| 4 | Stability markers (employment / residency length) | DONE | `months_employed`, `housing_months` in `Demographic` / `UserFeatures` | |
| 5 | Lifestyle / "new-age" fields | DONE | `data/Datasets_AltCredit/new_age_sample_data.json`, `features_from_merged`, `/upload-csv` aliases | Local, git-ignored dataset. |
| 6 | Product catalog ingestion (JSON) | DONE | `load_products`, `data/synthetic/product_catalog.json` | |

## B. Scoring pipeline
| # | Item | Status | Evidence | Notes |
|---|---|---|---|---|
| 7 | Feature engineering | DONE | `compute_user_features`, `features_from_merged` | **Bugs:** `ZeroDivisionError` when monthly_income = 0, `TypeError` when None (verified by running). Merged path collapses `delinq_30plus=3` into a single `30_day_late` flag (spec: multiple → 0). |
| 8 | Rule-based 0–1000 score, exact point table | DONE | `backend/scoring_engine/engine.py` (all 14 sub-factors) | Thresholds and points checked line-by-line against the spec: all match. Note the factor maxima sum to 1320 and are clamped to 1000 (spec-inherent). No test asserted the boundaries — see E20. |
| 9 | ML (PD) pipeline wired end to end | DONE | `backend/ml_engine/predictor.py`, `/upload-csv` (`ml_score` + drivers), `GET /score/{id}/ml` | Wired into API; failure is isolated so rule score still returns. |

## C. User-mode outputs
| # | Item | Status | Evidence | Notes |
|---|---|---|---|---|
| 10 | Dashboard: score + breakdown + risk category | DONE | `frontend/user-dashboard` (ScoreGauge, FactorBreakdown, ScoreDetail), `/dashboard/{id}`, `/upload-csv` | |
| 11 | ≥4 colour-coded tiers | DONE | `ScoreGauge.jsx` RISK_COLORS (Excellent/Good/Fair/Poor) | |
| 12 | Natural-language explainability | PARTIAL | `backend/explainability/explainer.py` | Returns label + points and a generic summary, but no per-factor sentence like "Consistency in utility bills +15 pts". |
| 13 | Recommendation engine | DONE | `backend/recommendations/recommender.py` | |
| 14 | Offer click → separate bank API (API key) | MISSING | — | No `bank-partner-api/`, no click handler in `Recommendations.jsx`. |
| 15 | Downloadable PDF Transparency Report | MISSING | — | `/report/*` → 404. No PDF library in requirements. |

## D. Business user mode (lender portal)
| # | Item | Status | Evidence | Notes |
|---|---|---|---|---|
| 16 | Business login | MISSING | — | No auth anywhere; `/lender/login` → 404. |
| 17 | Candidate search & filter | PARTIAL | `GET /lender/candidates` (min/max score, city_tier) | Works (returns data) but is **unauthenticated** and there is no lender UI. |
| 18 | PII anonymisation until acceptance | PARTIAL | `CandidateSummary` returns only ref/score/tier | Data set has no name/address/phone, so nothing to mask and no accept-reveal flow. `candidate_ref` is an unsalted MD5 prefix of user_id. |
| 19 | Push offers to consumers | MISSING | `OfferRequest/OfferResult` schemas and `database.models.Offer` exist but no endpoint | Nothing appears on user dashboard. |

## E. Testing & quality
| # | Item | Status | Evidence | Notes |
|---|---|---|---|---|
| 20 | Score accuracy vs synthetic ground truth | MISSING | `backend/testing/test_mvp_models.py` has 1 hand-computed case only | No per-threshold boundary tests. |
| 21 | Full-stack integration test | MISSING | — | `httpx` (needed for TestClient) is not installed / not in requirements. |
| 22 | Missing-data robustness | MISSING | — | Confirmed crash on zero/None income (see #7). |
| 23 | Latency < 15–30 s | MISSING (not measured) | — | Ad hoc measurement: `/dashboard/USR_001` 0.22 s, `/upload-csv` (template) 0.40 s. Needs a committed timing test. |

## F. Architecture
| # | Item | Status | Evidence | Notes |
|---|---|---|---|---|
| 24 | Modular layers | DONE | `data/`, `backend/scoring_engine`, `backend/ml_engine`, `backend/api`, `frontend/` | |
| 25 | Single requirements.txt | PARTIAL | root `requirements.txt` | Lacks `pytest`, `httpx`, PDF lib; stale `common/requirements.txt` was deleted in working tree. |

## After Part 2 (implemented, all verified by `python -m pytest backend` -> 131 passed)
| # | Now | What / where | Verified by |
|---|---|---|---|
| 1 | DONE | JSON transaction loading — `data/feature_engineering.py::load_transactions` | `test_robustness.py::test_json_transactions_are_ingested` |
| 7 | DONE | Zero/None/invalid income no longer crashes; multiple delinquency events -> `multiple_late`; CSV `monthly_spend=0` no longer replaced by 0.5; missing-column warnings | `test_robustness.py` |
| 8 | DONE | Engine unchanged (already matched); now proven | `test_scoring_ground_truth.py` (85 cases) |
| 12 | DONE | `Factor.text` per factor, e.g. "Utility & bill payment consistency +45 pts (of 70 possible, moderate)" — `explainer.py`, `common/schemas.py` | `test_integration_and_latency.py`, PDF |
| 14 | DONE (mock) | `bank-partner-api/app.py` (own port 8100, `X-API-Key`), client `backend/integrations/bank_client.py`, `POST /offers/preapprove`, `GET /offers/preapprove/{id}`, "Get pre-approved" button in `Recommendations.jsx` | `test_bank_and_report.py`; live two-process curl |
| 15 | DONE | `backend/reports/transparency_report.py`, `GET /report/{user_id}`, `POST /report/pdf`, download button in `ScoreDetail.jsx` | `test_bank_and_report.py`; PDF rendered and inspected |
| 16 | DONE (mock creds) | `POST /lender/login` -> bearer token, all lender routes gated — `backend/lender/router.py` | `test_lender_portal.py::test_endpoints_are_gated` |
| 17 | DONE | `GET /lender/candidates` (min/max score, city tier, risk category) + UI at `#/lender` (`src/lender/LenderPortal.jsx`) | `test_candidate_search_filters` |
| 18 | DONE | Server-side allow-list; PII (synthetic, `backend/lender/pii.py`) released only after that lender's offer is accepted; refs are HMACs | `test_pii_and_real_ids_never_in_candidate_responses`, accept/reject tests |
| 19 | DONE | `POST /lender/offers` (multi-candidate), consumer `GET /users/{id}/offers` + `POST .../respond`, "My offers" view (`OffersInbox.jsx`) | `test_push_offer_consumer_sees_it_and_accept_unlocks_pii` |
| 20 | DONE | `test_scoring_ground_truth.py`: every threshold boundary, 300-profile oracle comparison, hand-computed totals/tiers | pytest |
| 21 | DONE | `test_integration_and_latency.py` (CSV in -> full dashboard payload incl. ML score; exact 950 case; dataset dashboard) | pytest |
| 22 | DONE | `test_robustness.py` | pytest |
| 23 | DONE (measured) | single profile 0.03-0.10 s; dashboard 0.004 s; cold ingest+score of 500 users 0.03 s; **200-row upload 6.5-7.1 s** | `pytest -s test_integration_and_latency.py` |
| 25 | DONE | `requirements.txt` now includes httpx, reportlab, pytest | — |

Known limits / assumptions: offers are stored in memory (lost on restart); there is no consumer login
(user_id in the URL identifies the consumer); lender credentials are mock defaults from env; the bundled
data has no real names/addresses, so contact PII is synthetic; bulk CSV upload costs ~30 ms/row because the
ML model is called per row (a 500+ row file would approach the 15 s budget — batch the ML call to fix);
the new frontend screens were compiled (`npm run build`) but not exercised in a browser.

### Update: lender view and split synthetic data
- Lender portal now identifies candidates by **user_id**; only contact details (name, address, phone) stay masked
  server-side until acceptance. Clicking a user opens the same score analysis the consumer sees
  (`GET /lender/candidates/{user_id}`: score breakdown, explanation, ML cross-check, products, features).
- `data/synthetic/<poor|fair|good>/user_<n>/` holds each synthetic user's own `demographics.json`,
  `transactions.csv` and `expected_score.json` (`data/split_synthetic.py`; tests in `test_synthetic_split.py`).
