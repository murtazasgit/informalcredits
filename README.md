# AltCredit — The "New-Age" Credit-Score Framework
BNP Paribas Hackathon Use Case — Alternative Credit Scoring for users with no formal credit history.

**Start here, in this order:**
1. Read this file fully (5 min)
2. Read `CONTRIBUTING.md` — git workflow, folder ownership, how we avoid merge conflicts
3. Read `common/README.md` — the shared data contracts everyone must use
4. Open `REQUIREMENTS_COVERAGE.md` — confirms every spec requirement maps to a file in this repo
5. Go to your assigned folder's `README.md` and start building

## 1. What we're building
A platform that scores creditworthiness using non-traditional data (utility bills, rent, gig
income, spending patterns) instead of traditional credit bureau history, and explains *why*
every score was given.

Two user modes:
- **User Mode** — score dashboard, factor breakdown, product recommendations, "what-if"
  simulator, PDF report, JSON export
- **Business Mode (Lender Portal)** — banks/NBFCs search & filter candidates, push loan/card offers

## 2. Full repo structure — who owns what
```
altcredit/
├── common/                        → SHARED SCHEMAS — read this before writing any code
├── data/                          → Data ingestion + synthetic data + OCR (stretch)      [Member 1]
├── backend/
│   ├── scoring_engine/            → Rule-based point system + What-If simulator (MUST-HAVE, CORE) [Member 2]
│   ├── ml_engine/                 → Case 1 (PD model), Case 2 (propensity), Case 3 (counterfactual) — stretch [Member 3]
│   ├── explainability/            → SHAP + factor analysis                                [Member 3 or 4]
│   ├── recommendations/           → Product recommendation engine                         [Member 4]
│   ├── reports/                   → PDF Transparency Report + JSON export                 [Member 4]
│   ├── bank_integration_mock/     → Mock bank API (separate service) — stretch            [Member 4 or 5]
│   ├── testing/                   → pytest: unit, integration, robustness, latency tests   [Member 5]
│   └── api/                       → FastAPI integration hub, auth, all endpoints          [Member 5]
├── frontend/
│   ├── user-dashboard/            → Score dashboard + onboarding portal (stretch)          [Member 6]
│   └── lender-portal/             → Business user UI                                      [Member 7]
├── database/                      → SQLite schema
├── deployment/                    → Docker Compose, Dockerfiles, requirements.txt
├── docs/ARCHITECTURE.md           → Full end-to-end data flow, exact payloads at every step
├── CONTRIBUTING.md                → Git workflow + merge-conflict prevention rules
├── REQUIREMENTS_COVERAGE.md       → Every spec line ↔ file traceability matrix
└── .gitignore
```
Each folder's `README.md` is fully self-contained — read it and start implementing directly, no
need to re-read the whole spec every time. Every README tells you exactly what to import from `common/schemas.py` — this is what prevents merge conflicts, since
nobody invents their own field names.

## 3. Tech stack (and why)
| Layer | Choice | Why |
|---|---|---|
| Backend/API | **FastAPI** | Async, auto-generated `/docs`, Pydantic validation matches our JSON input schemas |
| Core scoring | **Plain Python (rule engine)** | Deterministic, auditable, satisfies "no black-box" guardrail, zero training time needed |
| ML (stretch) | **XGBoost / scikit-learn** | Fast to train on synthetic data, interpretable, industry-standard for tabular PD models |
| Explainability | **SHAP** | Ready-made factor-attribution values, works with tree models and the rule engine's own breakdown |
| Database | **SQLite + SQLAlchemy** | Zero setup — judges can clone & run instantly; ORM makes swapping to Postgres trivial |
| Frontend | **React + Tailwind + Recharts** | Most common stack among students; fast to build a clean fintech-style dashboard |
| PDF reports | **WeasyPrint** | Write an HTML/CSS template → PDF, no complex drawing code |
| Auth | **FastAPI-Users / python-jose (JWT)** | Don't hand-roll auth; battle-tested, minimal setup |
| Testing | **pytest** | Standard, minimal setup for unit + integration + robustness tests |
| OCR (stretch) | **Tesseract / pytesseract** | Free, well-documented, good enough for clean synthetic PDF statements |
| Deployment | **Docker Compose** | One command to run everything, satisfies "reproducible build" requirement |

## 4. High-level data flow
```
Raw CSV/JSON (transactions, demographics, product catalog)
        │
        ▼
  [data/] ingestion + cleaning + feature engineering  →  UserFeatures (common/schemas.py)
        │
        ▼
  [backend/scoring_engine/] rule-based score (0–1000)  →  ScoreResult
        │ (optional, parallel path)
        ▼
  [backend/ml_engine/] XGBoost → PD → Score = 1000×(1-PD)
        │
        ▼
  [backend/explainability/] factor breakdown → ExplainResult
        │
        ▼
  [backend/recommendations/] score → eligible products
        │
        ▼
  [backend/api/] stores in SQLite, exposes REST endpoints
        │
        ├──▶ [frontend/user-dashboard/] score, factors, recommendations, what-if simulator, report
        ├──▶ [backend/reports/] downloadable PDF + JSON export
        ├──▶ [backend/bank_integration_mock/] disburse pre-approved offer (stretch)
        └──▶ [frontend/lender-portal/] anonymized candidate search + offer push
```
See `docs/ARCHITECTURE.md` for the fully detailed version with exact JSON payloads at each arrow.

## 5. How to run (once each part is built)
```bash
cp .env.example .env   # set BANK_API_KEY
docker compose up --build
# backend  → http://localhost:8000/docs
# bank mock (stretch) → http://localhost:9000
# frontend → http://localhost:3000
```

## 6. Guardrails (don't break these)
- No real PII — only synthetic data
- No deep-learning black boxes — keep models interpretable (Decision Tree / Logistic Regression / shallow XGBoost)
- No external credit bureau APIs
- Prototype only — no need for production-grade HA/DevOps
- No legal/compliance certification implied — this is a demo, not a real credit decision

## 7. Priority order if time runs out
1. **Must-have** (do these first, in this order): `data/` → `scoring_engine/` → `database/` →
   `api/` (core endpoints) → `frontend/user-dashboard/` (basic) → `explainability/` →
   `reports/` (PDF) → `backend/testing/`
2. **Then Business Mode**: `frontend/lender-portal/` + lender endpoints in `api/`
3. **Then stretch, in this order**: What-If simulator worked examples → `recommendations/`
   dynamic mapping → JSON export → onboarding portal → OCR → Case 1 (PD model) → Case 3
   (counterfactual) → Case 2 (propensity) → `bank_integration_mock/`

See `REQUIREMENTS_COVERAGE.md` for the full traceability matrix confirming nothing from the
spec is missing.
