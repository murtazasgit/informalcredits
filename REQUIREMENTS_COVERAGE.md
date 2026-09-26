# REQUIREMENTS_COVERAGE.md — every line of the spec, mapped to where it's built

Use this to sanity-check nothing was missed. ✅ = must-have, covered. 🟡 = good-to-have/stretch, covered. 

## IV.1 Functional Requirements
| Spec requirement | Covered in |
|---|---|
| Bundled dataset loading and feature engineering | `data/feature_engineering.py` |
| Applicant CSV upload and row-by-row scoring | `POST /upload-csv` in `backend/api/main.py` |
| Integrated rule-based scoring pipeline | `backend/scoring_engine/engine.py` + `backend/api/main.py` |
| Rule table, sub-factors, bonus/penalty | `backend/scoring_engine/engine.py` |
| User score dashboard | `frontend/user-dashboard/` |
| Factor explanations | `backend/explainability/explainer.py` |
| Product recommendations | `backend/recommendations/recommender.py` |
| Bank integration | Not implemented |
| PDF transparency report | Not implemented |
| User authentication and lender UI | Not implemented |
| Candidate search | Basic API endpoint: `GET /lender/candidates`; no lender UI or authentication |
| Candidate anonymization | `backend/api/main.py` (`CandidateSummary`) |
| Offer campaigns | Not implemented |

## IV.2 Testing & Quality Assurance
| Spec requirement | Covered in |
|---|---|
| Scoring/model regression tests | `backend/testing/test_mvp_models.py` |
| Full API-to-dashboard integration tests | Not implemented |
| Robustness tests for missing data | Not implemented |

## IV.3 Performance & Accuracy
| Spec requirement | Covered in |
|---|---|
| End-to-end scoring latency < 15–30s | Not measured yet |

## IV.4 Code Quality & Reproducibility
| Spec requirement | Covered in |
|---|---|
| Modular architecture (Data / API / Frontend separated) | Repository structure — see root `README.md` |
| Backend dependency manifest | Root `requirements.txt` |
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
| PD, propensity, and counterfactual ML models | Not implemented |
| Export options | JSON profile: `GET /export/{user_id}`; PDF not implemented |
| API-first architecture | `backend/api/README.md` |
| Self-contained SQLite store | `database/README.md` |
| Synthetic-data-ready (no manual preprocessing) | `data/README.md` |
| New User Login Portal (profile creation + upload CSV/PDF) | 🟡 `frontend/user-dashboard/README.md` §Onboarding |
| OCR Integration (Tesseract, scan PDF bank statement) | 🟡 `data/README.md` §OCR |
| Docker deployment | Not implemented |

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
| No deep-learning black boxes | Root `README.md` §6; current MVP uses rule-based scoring |
| No external credit bureau APIs | Root `README.md` §6 |
| No production-grade deployment needed | Root `README.md` §6 |
| No legal/compliance certification needed | Root `README.md` §6 |

---
**Bottom line:** The runnable MVP covers rule-based scoring, explanations, recommendations, the
dashboard, and what-if simulation. Items marked "Not implemented" are future work, not working
starter modules.
