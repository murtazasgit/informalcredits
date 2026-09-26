# REQUIREMENTS_COVERAGE.md — every line of the spec, mapped to where it's built

Use this to sanity-check nothing was missed. ✅ = must-have, covered. 🟡 = good-to-have/stretch, covered. 

## IV.1 Functional Requirements
| Spec requirement | Covered in |
|---|---|
| Multi-source ingestion (Transactional CSV/JSON, Demographic JSON, Product Catalog JSON) | `data/README.md` |
| Integrated scoring pipeline, feature engineering | `data/README.md` (features) + `backend/scoring_engine/README.md` (scoring) |
| Full rule-based point table (all 12 sub-factors + bonus/penalty) | `backend/scoring_engine/README.md` |
| Real-time Risk Dashboard | `frontend/user-dashboard/README.md` |
| Explainability Module (Factor Analysis) | `backend/explainability/README.md` |
| Automated Recommendation Engine | `backend/recommendations/README.md` |
| "Connect to banking system via API" for pre-approved loan/card redemption (separate app + API key link) | 🟡 `backend/bank_integration_mock/README.md` |
| Transparency Report (downloadable PDF, Accept/Reject) | `backend/reports/README.md` |
| Business User Login (Lender Portal) | `backend/api/README.md` (auth) + `frontend/lender-portal/README.md` |
| Candidate Search & filter (score range e.g. 650+) | `backend/api/README.md` (`/lender/candidates`) + `frontend/lender-portal/README.md` |
| Anonymization until offer accepted | `backend/api/README.md` (`CandidateSummary` schema — no PII fields) |
| Push offers / campaign (single + bulk) | `backend/api/README.md` (`/lender/offer`) + `frontend/lender-portal/README.md` |

## IV.2 Testing & Quality Assurance
| Spec requirement | Covered in |
|---|---|
| Data Object Validation vs. ground-truth dataset | `backend/testing/README.md` |
| Integration Test (full flow: API → Dashboard) | `backend/testing/README.md` |
| Robustness Test (missing data, no crash) | `backend/testing/README.md` |

## IV.3 Performance & Accuracy
| Spec requirement | Covered in |
|---|---|
| End-to-end scoring latency < 15–30s | `backend/testing/README.md` (perf test) + noted in root `README.md` |

## IV.4 Code Quality & Reproducibility
| Spec requirement | Covered in |
|---|---|
| Modular architecture (Data / ML / API / Frontend separated) | Overall repo structure — see root `README.md` |
| Single dependency manifest | `deployment/README.md` (`requirements.txt`) |
| Version control practices | `CONTRIBUTING.md` |
| No hard-coded secrets | `CONTRIBUTING.md` §7, `.gitignore` |
| Logging | `backend/api/README.md` (add basic `logging` calls — noted in tasks checklist) |

## V. Expected Outcomes
| Spec requirement | Covered in |
|---|---|
| Alternative risk engine using non-traditional features | `backend/scoring_engine/README.md` |
| Color-coded score, ≥4 risk bands | `common/schemas.py` (`risk_category` enum: Poor/Fair/Good/Excellent) + `frontend/user-dashboard/README.md` |
| Visualized "Credit Drivers" | `frontend/user-dashboard/README.md` (`FactorBreakdownChart`) |
| Curated "Next Steps" product recommendations | `backend/recommendations/README.md` |
| Financial inclusion demo (good borrower, no credit history) | Achieved by design of the rule-based engine — call this out explicitly in your demo script |
| XAI natural-language explanations | `backend/explainability/README.md` |
| Modular, scalable stack | Overall repo structure |

## VI. Solution Requirements (Good to Have)
| Spec requirement | Covered in |
|---|---|
| Advanced feature engineering (Income Volatility Index, Savings Velocity) | 🟡 `data/README.md` — noted as stretch addition to feature engineering |
| Dynamic Product Mapping (recs update as score changes) | 🟡 `backend/recommendations/README.md` |
| Advanced XAI (mathematically grounded) | 🟡 `backend/explainability/README.md` (SHAP section) |
| Consumer-centric, fintech-style UI | `frontend/user-dashboard/README.md` |
| "What-If" Simulator | `backend/scoring_engine/README.md` (`simulate_change`) + `backend/api/README.md` (`/simulate`) |
| 4 worked What-If examples (Saving Buffer, Utility Auto-pay, Discretionary Spike, Delinquency) | 🟡 `backend/scoring_engine/README.md` §What-If worked examples |
| Case 1 — PD model (XGBoost, Score = 1000×(1-PD)) | 🟡 `backend/ml_engine/README.md` §Case 1 |
| Case 2 — Propensity to Purchase model | 🟡 `backend/ml_engine/README.md` §Case 2 |
| Case 3 — Counterfactual "Target Achievement" | 🟡 `backend/ml_engine/README.md` §Case 3 |
| Export options (PDF + JSON credit profile) | `backend/reports/README.md` (PDF) + `backend/api/README.md` (`/export/{user_id}` JSON) |
| API-first architecture | `backend/api/README.md` |
| Self-contained SQLite store | `database/README.md` |
| Synthetic-data-ready (no manual preprocessing) | `data/README.md` |
| New User Login Portal (profile creation + upload CSV/PDF) | 🟡 `frontend/user-dashboard/README.md` §Onboarding |
| OCR Integration (Tesseract, scan PDF bank statement) | 🟡 `data/README.md` §OCR |
| Docker deployment | `deployment/README.md` |

## VIII. Input formats
| Spec requirement | Covered in |
|---|---|
| Transactional Data exact fields | `common/schemas.py` (`Transaction`) + `data/README.md` |
| Demographic Data exact fields | `common/schemas.py` (`Demographic`) + `data/README.md` |
| Product Catalog exact fields | `common/schemas.py` (`Product`) + `data/README.md` |

## IX. Guardrails
| Spec requirement | Covered in |
|---|---|
| No real PII, synthetic only | Root `README.md` §6, reinforced in `data/README.md` and `backend/api/README.md` (anonymization) |
| No deep-learning black boxes | Root `README.md` §6, `backend/ml_engine/README.md` (shallow models only) |
| No external credit bureau APIs | Root `README.md` §6 |
| No production-grade deployment needed | `deployment/README.md` (Docker Compose only, no k8s/HA) |
| No legal/compliance certification needed | Root `README.md` §6 |

---
**Bottom line: every Must-Have requirement (IV.1 core flow, IV.2 testing, IV.3 latency, IV.4 code
quality) has a dedicated file with working starter code. Every Good-to-Have (🟡) is scoped and
documented so your team can pick them up only if time allows, in priority order:**
1. What-If simulator worked examples (cheap, high demo value)
2. Export JSON + OCR (medium effort, nice demo value)
3. New User onboarding portal
4. Case 1 (PD model) → Case 3 (counterfactual) → Case 2 (propensity) → bank integration mock
   (in that order — each is progressively more effort for less judge-visible payoff under time
   pressure)
