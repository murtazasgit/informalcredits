# AltCredit

**Explainable alternative credit scoring for people the credit bureaus can't see.**
Built for the BNP Paribas hackathon (Team 03).

AltCredit scores creditworthiness from everyday behaviour (bill payments, rent, employment, spending and
savings) instead of bureau history, explains every point of the score in plain language, and connects
borrowers with lenders through a privacy-preserving marketplace.

> Prototype only. All data is synthetic, no real personal data is used, and scores are a demo, not a real
> credit decision.

## Features

**Scoring and explainability**
- Rule-based 0–1000 score from 14 sub-factors, four colour-coded risk tiers, deterministic and auditable
- Independent ML cross-check (calibrated logistic regression, test AUC 0.80) plus an ML score head
- Plain-language "Why this score" analysis: what helps, what holds you back, exact actions and their point gains
- What-if simulator and target-achievement planner
- Downloadable PDF Transparency Report

**Borrower dashboard**
- Register or sign in, upload a CSV or raw transactions and demographics, or update your data
- Score, factor breakdown, product recommendations
- "Get loan approval": apply to a registered lender, track application status
- Offers inbox: accept or decline offers pushed by lenders

**Lender portal** (`/#/lender`)
- Lender registration and login (token-gated routes)
- Candidate search by score range, city tier and risk category, with the full score analysis per candidate
- Push offers to many candidates; approve or decline loan applications
- Contact details stay masked server-side until the borrower accepts that lender's offer

## Architecture

```
CSV / JSON  ->  data/ (ingest + feature engineering)  ->  UserFeatures
            ->  scoring_engine (rule score 0-1000)     ->  ScoreResult
            ->  explainability + ml_engine             ->  reasons, ML second opinion
            ->  recommendations                        ->  eligible products
            ->  api (FastAPI + SQLite)                 ->  React dashboard / lender portal
```

| Path | Purpose |
|---|---|
| `common/schemas.py` | Shared Pydantic data contracts used by every layer |
| `data/` | Ingestion, feature engineering, synthetic data generators, upload template |
| `backend/scoring_engine/` | Rule-based point system and what-if simulator |
| `backend/explainability/` | Factor explanations and plain-language XAI |
| `backend/ml_engine/` | Trained models, training scripts, predictor (see `MODEL_NOTES.md`) |
| `backend/recommendations/` | Product recommendation engine |
| `backend/lender/` | Lender accounts, candidate search, offers, applications, PII masking |
| `backend/reports/` | PDF transparency report |
| `backend/api/` | FastAPI app and endpoints |
| `backend/testing/` | pytest suite |
| `database/` | SQLAlchemy models and DB setup (SQLite) |
| `frontend/user-dashboard/` | React + Vite app (borrower dashboard and lender portal) |


## Tech stack

FastAPI, Pydantic, SQLAlchemy/SQLite, scikit-learn, ReportLab, React 18, Vite, Recharts, pytest.

## Getting started

Prerequisites: Python 3.11+ and Node.js 18+.

**1. Backend** (from the repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.api.main:app --reload
```

The API runs on http://localhost:8000 (interactive docs at `/docs`).

**2. Frontend** (second terminal)

```powershell
cd frontend/user-dashboard
npm install
npm run dev
```

Open http://localhost:3000. The dev server proxies `/api` to the backend. Lenders use http://localhost:3000/#/lender.

## Configuration

Read from environment variables (see `.env.example` for the list; the defaults are fine for a local demo, so
nothing is required to get started):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Database connection (default `sqlite:///./altcredit.db`) |
| `JWT_SECRET` | Secret for borrower session tokens. Change it |
| `LENDER_USERNAME`, `LENDER_PASSWORD` | Default demo lender credentials |
| `LENDER_REF_SECRET` | Secret used to derive masked candidate references |

## Try it

- Upload `altcredit-template.csv` (or download it from the app) to score an applicant.
- Synthetic users by risk band live in `data/synthetic/<poor|fair|good>/user_<n>/`.
- Regenerate the synthetic data with `python -m data.generate_synthetic_data`.

## Testing

```powershell
python -m pytest backend
```

The suite covers every scoring threshold, a 300-profile oracle comparison, missing-data robustness,
full-stack integration (CSV in to dashboard payload), latency, lender gating and PII masking.

## API overview

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `/auth/logout`, `GET /auth/me` |
| Scoring | `POST /upload-csv`, `/upload-raw`, `/simulate`, `/target-achievement`, `/xai`; `GET /dashboard/{id}`, `/score/{id}`, `/score/{id}/ml`, `/explain/{id}` |
| Reports | `GET /report/{id}`, `POST /report/pdf` |
| Borrower | `GET /products`, `/lenders`, `/users/{id}/offers`, `/users/{id}/applications`; `POST /users/{id}/applications`, `/users/{id}/offers/{offer_id}/respond` |
| Lender | `POST /lender/register`, `/lender/login`, `/lender/offers`, `/lender/applications/{id}/decision`; `GET /lender/candidates`, `/lender/offers`, `/lender/applications` |

## Guardrails and known limits

- Synthetic data only; no external credit bureau APIs; interpretable models only (no deep learning)
- The rule engine is the primary score; an ML failure never blocks a score
- Offers are held in memory and are lost on restart
- Bulk uploads call the ML model per row (about 7 s for 200 rows)
- Demo lender credentials come from environment variables



