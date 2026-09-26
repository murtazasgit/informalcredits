# AltCredit — Full Input/Output Flow

This traces one user's data through the entire system, exact payload at each step.

```
1. RAW INPUT (provided synthetic dataset)
   ├─ transactions.csv        (transaction_id, user_id, date, amount, category, type, on_time)
   ├─ demographics.json       (user_id, age, employment_status, months_employed, education_level,
   │                           monthly_income, city_tier, housing_status, housing_months)
   └─ product_catalog.json    (product_id, name, type, min_score_required, interest_rate)
        │
        ▼
2. DATA INGESTION  [data/]
   IN:  raw CSV/JSON above
   OUT: feature dict per user →
        { user_id, months_employed, housing_status, housing_months, digital_bill_ontime_pct,
          education_level, spend_to_income_ratio, essential_spend_pct, cashflow_volatility_pct,
          savings_days, on_time_payment_pct, debt_to_income_ratio, credit_utilization_pct,
          delinquency_flags }
        │
        ▼
3a. RULE-BASED SCORING  [backend/scoring_engine/]        3b. ML SCORING (optional)  [backend/ml_engine/]
    IN:  feature dict                                        IN:  same feature dict
    OUT: { user_id, total_score, risk_category, breakdown }  OUT: { user_id, probability_of_default, score }
        │                                                        │
        └───────────────────────┬────────────────────────────────┘
                                 ▼
4. EXPLAINABILITY  [backend/explainability/]
   IN:  breakdown dict (or SHAP values if ML path used)
   OUT: { user_id, factors: [{label, points, direction}], summary_text }
        │
        ▼
5. PERSISTENCE  [database/]
   Score + breakdown + factors saved to `scores` table, keyed by user_id + timestamp
        │
        ├──────────────────────────────┬─────────────────────────────┐
        ▼                              ▼                             ▼
6a. USER DASHBOARD API           6b. REPORT GENERATION         6c. LENDER PORTAL API
    [backend/api/]                   [backend/reports/]            [backend/api/]
    GET /score/{user_id}             IN: score+factors+decision     GET /lender/candidates
    GET /explain/{user_id}           OUT: report_{user_id}.pdf      (anonymized: candidate_ref,
    POST /simulate                                                  score, risk_category — NO
        │                                                            name/address/phone)
        ▼                                                                  │
7a. USER DASHBOARD UI                                              7b. LENDER PORTAL UI
    [frontend/user-dashboard/]                                         [frontend/lender-portal/]
    Renders: ScoreGauge, FactorBreakdownChart,                         Renders: candidate search/filter,
    RecommendationCards, WhatIfSimulator, ReportButton                 "Push Offer" action
                                                                              │
                                                                              ▼
                                                                  8. OFFER PUSHED
                                                                     POST /lender/offer →
                                                                     appears on user's dashboard
                                                                     (7a) as a recommendation;
                                                                     PII revealed only after
                                                                     user accepts
```

## What-If Simulator flow (detail)
```
User input (frontend/user-dashboard): "What if I save ₹1000 extra for 3 months?"
        │
        ▼
POST /simulate  { user_id, hypothetical_changes: {"savings_days": +30} }
        │
        ▼
backend/api/ re-runs scoring_engine.compute_score() with modified feature dict
        │
        ▼
Response: { old_score: 742, new_score: 777, delta: +35, message: "Increases savings sub-score" }
```

## Counterfactual / "Target Achievement" flow (Case 3, stretch)
```
User selects target product (e.g. "Premium Card", min_score_required: 850)
        │
        ▼
backend computes: gap = 850 - current_score
        │
        ▼
Search feature space for minimal changes that close the gap
(simple approach: try adjusting one sub-factor at a time, see which gives the best score/effort ratio)
        │
        ▼
Output: "Reduce cash-flow volatility by 12% — try auto-pay for your electricity bill."
```
