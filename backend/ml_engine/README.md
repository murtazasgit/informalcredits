# Module: ML Model — Case 1, 2, 3 (all stretch goals, "Good to Have")

Build in this priority order if time allows: **Case 1 → Case 3 → Case 2** (each is progressively
more effort for less judge-visible payoff — Case 1 replaces the core score with a "real" model,
Case 3 is a flashy demo feature, Case 2 is the least visible in a live demo).

---

## Case 1 — Probability of Default (PD) model

### Goal
Instead of a fixed point sum, train a model on a "ground truth" dataset of past
Successful/Defaulted borrowers to predict PD, then convert:
```
Score = 1000 × (1 - PD)
```
Only attempt this after the rule-based engine (`backend/scoring_engine/`) is working — it's the
must-have fallback if this doesn't get finished.

### Tech stack
- **XGBoost** or **scikit-learn RandomForestClassifier** — interpretable enough, fast to train
- **imbalanced-learn (SMOTE)** if defaults are rare in the ground-truth set

### Input
Labeled training dataset — one row per historical user (same features as `UserFeatures` in
`common/schemas.py`, plus a `defaulted` column: 0 or 1).

For inference: a single `UserFeatures` object.

### Output
```json
{"user_id": "U1001", "probability_of_default": 0.12, "total_score": 880, "method": "ml_pd"}
```
This maps directly onto `common.schemas.ScoreResult` with `method="ml_pd"` and
`probability_of_default` set.

### Starter code
```python
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y)
model = xgb.XGBClassifier(max_depth=4, n_estimators=100, eval_metric="logloss",
                           scale_pos_weight=(len(y_train) - sum(y_train)) / sum(y_train))
model.fit(X_train, y_train)
print("AUC:", roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))

def predict_score(features: UserFeatures) -> ScoreResult:
    X = feature_dict_to_array(features)  # must match training column order — keep this mapping documented!
    pd_prob = model.predict_proba([X])[0][1]
    score = round(1000 * (1 - pd_prob))
    band = ("Excellent" if score >= 800 else "Good" if score >= 600 else
            "Fair" if score >= 400 else "Poor")
    return ScoreResult(user_id=features.user_id, total_score=score, risk_category=band,
                        breakdown=ScoreBreakdown(), method="ml_pd", probability_of_default=round(pd_prob, 3))
```

### Watch for
- **Class imbalance** — use `scale_pos_weight` or SMOTE
- **Calibration** — check `sklearn.calibration.calibration_curve` (a predicted 10% PD should
  roughly match a 10% real default rate in test data)
- **Keep `max_depth` low (3–5)** — stay interpretable per the guardrails

---

## Case 2 — Propensity to Purchase model

### Goal
Predict the probability a user will accept a specific product offer, so lenders can prioritize
who to push offers to.

### Input Features
- `total_score` (from AltCredit engine)
- Lifestyle/spending pattern flags (e.g. high discretionary spend → likely wants a lifestyle card)
- `simulator_usage_count` — how many times the user ran the What-If simulator (a proxy for
  "high intent" — track this counter in `scores`/`users` table)

### Target Variable
`accepted_offer`: 1 (accepted) or 0 (rejected/ignored) — comes from the `offers` table status
history once you have enough historical offer data (synthetic).

### Output
```json
{"user_id": "U1001", "product_id": "P004", "propensity_score": 0.68}
```

### Starter code
```python
from sklearn.linear_model import LogisticRegression

# Features: [total_score, discretionary_spend_pct, simulator_usage_count]
propensity_model = LogisticRegression()
propensity_model.fit(X_train, y_train)

def predict_propensity(total_score, discretionary_spend_pct, simulator_usage_count, product_id):
    X = [[total_score, discretionary_spend_pct, simulator_usage_count]]
    prob = propensity_model.predict_proba(X)[0][1]
    return {"product_id": product_id, "propensity_score": round(prob, 2)}
```

### Handoff
Feed this into `backend/recommendations/` to re-rank recommendations by propensity, and expose
to `frontend/lender-portal/` so lenders can sort candidates by "most likely to convert."

---

## Case 3 — Counterfactual "Target Achievement" module

### Goal
Given a target product the user wants, tell them the *minimum* change needed to qualify —
a simple counterfactual explanation, not full "advanced XAI" math.

### Input
- Current `UserFeatures` + `ScoreResult`
- Target `Product` (with its `min_score_required`)

### Output
```json
{
  "user_id": "U1001",
  "target_product": "Premium Card",
  "score_gap": 108,
  "suggested_change": {
    "sub_factor": "cashflow_volatility",
    "current_value": "12%",
    "target_value": "≤10%",
    "expected_point_gain": 55
  },
  "message": "To unlock the Premium Card, reduce your Cash-flow Volatility from 12% to under 10%. Try setting up auto-pay for your electricity bill."
}
```

### Starter code (simple greedy search — good enough for a hackathon demo)
```python
def find_min_change(features: UserFeatures, target_score: int, compute_score_fn) -> dict:
    """Try adjusting one sub-factor at a time, pick whichever single change closes the gap
    with the smallest, most achievable adjustment."""
    current = compute_score_fn(features)
    gap = target_score - current.total_score
    if gap <= 0:
        return {"message": "You already qualify."}

    candidates = []
    # Try nudging cashflow volatility down by 2%, 5%, 10%
    for delta in [2, 5, 10]:
        trial = features.copy(update={"cashflow_volatility_pct": max(0, features.cashflow_volatility_pct - delta)})
        trial_score = compute_score_fn(trial).total_score
        candidates.append(("cashflow_volatility_pct", delta, trial_score - current.total_score))
    # Repeat for savings_days, on_time_payment_pct, etc.

    best = max(candidates, key=lambda c: c[2])
    return {
        "sub_factor": best[0], "expected_point_gain": best[2],
        "message": f"Reduce {best[0]} by {best[1]} to gain ~{best[2]} points."
    }
```
This is intentionally simple (try-a-few-deltas, pick the best) rather than a true gradient-based
counterfactual solver — fully sufficient for the demo and avoids over-engineering under time
pressure.

### Handoff
Expose `find_min_change(features, target_score, compute_score_fn) -> dict` for `backend/api/`
(`/target-achievement` endpoint) and `frontend/user-dashboard/`.
