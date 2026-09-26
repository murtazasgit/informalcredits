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

The current MVP accepts applicant CSVs and returns scores, factor explanations, product
recommendations, and a "what-if" simulator. Lender tools, trained ML models, and PDF reports are
future work.

## 2. Full repo structure — who owns what
```
altcredit/
├── common/                        → SHARED SCHEMAS — read this before writing any code
├── data/                          → Data ingestion + synthetic data + OCR (stretch)      [Member 1]
├── backend/
│   ├── scoring_engine/            → Rule-based point system + What-If simulator (MUST-HAVE, CORE) [Member 2]
│   ├── explainability/            → Deterministic factor analysis
│   ├── recommendations/           → Product recommendation engine                         [Member 4]
│   ├── testing/                   → MVP regression tests                                  [Member 5]
│   └── api/                       → FastAPI endpoints for the MVP core flow
├── frontend/
│   └── user-dashboard/            → Score dashboard + what-if simulator
├── database/                      → SQLite schema
├── requirements.txt               → Backend dependencies
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
| ML (future) | Not included in the MVP | Current scores use the deterministic rule-based engine |
| Explainability | Plain Python | Deterministic factor attribution from the score breakdown |
| Database | **SQLite + SQLAlchemy** | Zero setup — judges can clone & run instantly; ORM makes swapping to Postgres trivial |
| Frontend | **React + Tailwind + Recharts** | Most common stack among students; fast to build a clean fintech-style dashboard |
| PDF reports and authentication | Future work | Not implemented in the current MVP |
| Testing | **pytest** | Regression coverage for the MVP model flow |
| OCR (stretch) | **Tesseract / pytesseract** | Free, well-documented, good enough for clean synthetic PDF statements |

## 4. High-level data flow
```
Raw CSV/JSON (transactions, demographics, product catalog)
        │
        ▼
  [data/] ingestion + cleaning + feature engineering  →  UserFeatures (common/schemas.py)
        │
        ▼
  [backend/scoring_engine/] rule-based score (0–1000)  →  ScoreResult
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
      └──▶ [frontend/user-dashboard/] upload CSV, review scores, factors, recommendations
```
See `docs/ARCHITECTURE.md` for the fully detailed version with exact JSON payloads at each arrow.

## 5. How to run
In PowerShell, from the project root, start the backend:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn backend.api.main:app --reload
```

In a second terminal, start the dashboard:
```powershell
cd frontend/user-dashboard
npm install
npm run dev
```

Open `http://localhost:3000` for the dashboard or `http://localhost:8000/docs` for the API.
```

## 6. Guardrails (don't break these)
- No real PII — only synthetic data
- No deep-learning black boxes — keep models interpretable (Decision Tree / Logistic Regression / shallow XGBoost)
- No external credit bureau APIs
- Prototype only — no need for production-grade HA/DevOps
- No legal/compliance certification implied — this is a demo, not a real credit decision

## 7. Priority order if time runs out
1. **MVP**: bundled data or applicant CSV → rule-based score → explanation and recommendations
      → dashboard and what-if simulation. The API also exposes JSON profile export and candidate search.
2. **Future work**: user authentication, transaction uploads, lender UI and offers, PDF reports,
      trained ML models, bank integration, and Docker deployment.

See `REQUIREMENTS_COVERAGE.md` for implemented MVP features and outstanding requirements.
