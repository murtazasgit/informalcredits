# Module: Explainability (Factor Analysis / XAI)

## Goal
Turn a score breakdown into human-readable "why" statements — this satisfies the
"Explainability Module" and "Factor Analysis" requirements.

## Tech stack
- **Rule-based path**: no library needed — the breakdown dict from `scoring_engine` already IS
  the explanation, just format it into sentences
- **ML path (if `ml_engine` is built)**: **SHAP** (`shap.TreeExplainer` for XGBoost) to get per-feature
  contribution values

## Input

### From rule-based engine
The `breakdown` dict from `backend/scoring_engine/compute_score()`.

### From ML engine (if used)
```python
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)  # array of per-feature contributions
```

## Output (contract with `backend/api/` and frontend)
```json
{
  "user_id": "U1001",
  "factors": [
    {"label": "On-time bill payments", "points": 15, "direction": "positive"},
    {"label": "Weekday dining spend", "points": -5, "direction": "negative"},
    {"label": "Stable employment (18 months)", "points": 100, "direction": "positive"}
  ],
  "summary_text": "Your score is strong mainly due to consistent utility payments and stable employment. Weekday discretionary spending slightly reduced your score."
}
```

## Starter code (template-based, no external API needed)
```python
LABELS = {
    "employment_stability": "Employment stability",
    "housing_status": "Housing/rent history",
    "digital_footprint": "Utility & bill consistency",
    "on_time_payment": "On-time payment history",
    "debt_to_income": "Debt-to-income ratio",
    # ... map every breakdown key to a friendly label
}

def explain_breakdown(breakdown: dict) -> list:
    factors = []
    for key, points in breakdown.items():
        factors.append({
            "label": LABELS.get(key, key),
            "points": points,
            "direction": "positive" if points >= 0 else "negative"
        })
    return sorted(factors, key=lambda f: abs(f["points"]), reverse=True)
```

## Starter code (template-based summary sentence)
```python
def generate_summary(factors: list) -> str:
    top_positive = [f for f in factors if f["direction"] == "positive"][:2]
    top_negative = [f for f in factors if f["direction"] == "negative"][:2]
    parts = []
    if top_positive:
        parts.append("Your score is strong mainly due to " +
                      " and ".join(f["label"].lower() for f in top_positive) + ".")
    if top_negative:
        parts.append(" and ".join(f["label"] for f in top_negative) +
                      " slightly reduced your score.")
    return " ".join(parts) if parts else "No significant factors identified."
```

## Tasks checklist
- [ ] Build the label-mapping dict for every scoring sub-factor
- [ ] Implement `explain_breakdown()` (sorts factors by impact, tags positive/negative)
- [ ] Implement `generate_summary()` for the plain-English summary sentence
- [ ] (Stretch) Wire up SHAP if `ml_engine` is used

## Handoff
Expose `explain_breakdown(breakdown: dict) -> list` for `backend/api/` and `backend/reports/`.
