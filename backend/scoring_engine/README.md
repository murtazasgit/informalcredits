# Module: Rule-Based Scoring Engine (CORE — must-have)

## Goal
Turn a user's feature dict (from `data/`) into a 0–1000 point score with a full breakdown,
using the exact rule table from the use-case document. This is the **baseline that must work**
even if ML/SHAP never gets built — it alone satisfies the "Definition of Done".

## Tech stack
Pure Python. No libraries needed beyond the standard library — keep it simple and testable.

## Input
The feature dict produced by `data/` (see that README for exact shape), e.g.:
```json
{
  "user_id": "U1001",
  "months_employed": 18,
  "housing_status": "rent",
  "housing_months": 14,
  "digital_bill_ontime_pct": 92.0,
  "education_level": "bachelor",
  "spend_to_income_ratio": 0.42,
  "essential_spend_pct": 68.0,
  "cashflow_volatility_pct": 7.5,
  "savings_days": 45,
  "on_time_payment_pct": 96.0,
  "debt_to_income_ratio": 0.18,
  "credit_utilization_pct": 0,
  "delinquency_flags": []
}
```

## Output (this is the contract with `backend/explainability/` and `backend/api/`)
```json
{
  "user_id": "U1001",
  "total_score": 742,
  "risk_category": "Good",
  "breakdown": {
    "employment_stability": 100,
    "housing_status": 60,
    "digital_footprint": 45,
    "education": 40,
    "spend_to_income": 80,
    "expense_diversity": 45,
    "cashflow_volatility": 40,
    "savings": 20,
    "on_time_payment": 150,
    "debt_to_income": 80,
    "credit_utilization": 100,
    "delinquency": 150,
    "bonus": 0,
    "penalty": 0
  }
}
```
`risk_category` bands (pick 4, as required): e.g. `Poor <400`, `Fair 400–599`, `Good 600–799`, `Excellent 800+`.

## Point rules (from the spec — implement exactly)

**Lifestyle (max 350)**
- Employment: ≥24mo → 150, 12–23 → 100, 6–11 → 50, else 0
- Housing: own → 80, rent ≥12mo → 60, rent <12mo → 30, none → 0
- Digital footprint (on-time %): ≥95 → 70, 80–94 → 45, 60–79 → 20, <60 → 0
- Education: Masters/PhD → 50, Bachelor → 40, Cert → 30, HS → 20, <HS → 0

**Spending Behavior (max 350)**
- Spend/income: ≤30% → 120, 30–50 → 80, 50–70 → 40, >70 → 0
- Essential spend %: ≥70 → 80, 55–69 → 45, 40–54 → 20, <40 → 0
- Cash-flow volatility: ≤5% → 70, 5–10 → 40, 10–20 → 15, >20 → 0
- Savings days: ≥180 → 80, 90–179 → 50, 30–89 → 20, <30 → 0

**Repayment Discipline (max 570)**
- On-time payment %: ≥98 → 200, 95–97 → 150, 90–94 → 100, 80–89 → 50, <80 → 0
- Debt/income: ≤20% → 120, 21–35 → 80, 36–50 → 40, >50 → 0
- Credit utilization: ≤10% → 100, 11–30 → 70, 31–50 → 30, >50 → 0
- Delinquency: none → 150, 1×30-day → 100, 1×60-day → 50, 90+/multiple → 0

**Bonus/Penalty**
- +20 per positive habit, max +50
- -20 per risk flag, max -50

## Starter code
```python
def score_employment(months: int) -> int:
    if months >= 24: return 150
    if months >= 12: return 100
    if months >= 6: return 50
    return 0

def score_housing(status: str, months: int) -> int:
    if status == "own": return 80
    if status == "rent" and months >= 12: return 60
    if status == "rent": return 30
    return 0

def score_digital_footprint(pct: float) -> int:
    if pct >= 95: return 70
    if pct >= 80: return 45
    if pct >= 60: return 20
    return 0

def score_education(level: str) -> int:
    return {"masters": 50, "phd": 50, "bachelor": 40, "certification": 30, "high_school": 20}.get(level, 0)

def score_spend_to_income(ratio: float) -> int:
    if ratio <= 0.30: return 120
    if ratio <= 0.50: return 80
    if ratio <= 0.70: return 40
    return 0

# ... repeat this pattern for the remaining sub-factors (see table above) ...

def compute_score(features: dict) -> dict:
    breakdown = {
        "employment_stability": score_employment(features["months_employed"]),
        "housing_status": score_housing(features["housing_status"], features["housing_months"]),
        "digital_footprint": score_digital_footprint(features["digital_bill_ontime_pct"]),
        "education": score_education(features["education_level"]),
        "spend_to_income": score_spend_to_income(features["spend_to_income_ratio"]),
        # ... add every sub-factor here ...
    }
    total = sum(breakdown.values())
    total = max(0, min(1000, total))
    risk = ("Excellent" if total >= 800 else
            "Good" if total >= 600 else
            "Fair" if total >= 400 else "Poor")
    return {"user_id": features["user_id"], "total_score": total,
            "risk_category": risk, "breakdown": breakdown}
```

## Tasks checklist
- [ ] Implement one scoring function per sub-factor (12 total + bonus/penalty)
- [ ] Implement `compute_score()` that sums everything and clamps 0–1000
- [ ] Write unit tests for at least one input per point bracket (positive + edge cases)
- [ ] Handle missing fields (e.g., no credit lines → utilization = 100 pts by default, not 0)

## Handoff
Expose `compute_score(features: dict) -> dict` as an importable function for `backend/api/`.

## What-If Simulator — worked examples (implement these exactly)

The simulator re-runs `compute_score()` with one or more features hypothetically changed. Use
`common.schemas.SimulationRequest` / `SimulationResult`. These four scenarios are given
explicitly in the spec — use them as your test cases:

### 1. Saving Buffer Boost
- **Input**: "What if I save extra ₹1000/month for the next 3 months?"
- **System impact**: increases `savings_days` (sub-factor 2.4) and lowers `cashflow_volatility_pct` (2.3)
- **Expected output**: score increases by ~+35 points

### 2. Utility & Rent Consistency Builder
- **Input**: "What if I set up auto-pay for my rent and/or utility bills?"
- **System impact**: maximizes `on_time_payment_pct` (3.1) and `housing_status`/`digital_bill_ontime_pct` consistency (1.2/1.3)
- **Expected output**: score increases by ~+60 points

### 3. Cash-flow & Discretionary Spend Spike
- **Input**: "What if I spend 75% of my income on non-essentials for 2 consecutive months?"
- **System impact**: lowers `essential_spend_pct` (2.2) and worsens `spend_to_income_ratio` (2.1)
- **Expected output**: score drops by ~-50 points, flags high cash-flow volatility

### 4. Utility & Rent Delinquency
- **Input**: "What if I miss my internet/mobile/gas/electricity bill by 45 days and delay rent by 15 days?"
- **System impact**: triggers `delinquency_flags` (3.4) and slashes `on_time_payment_pct` (3.1)
- **Expected output**: score drops by ~-110 points immediately, pre-approved offers revoked

### Starter code
```python
def simulate_change(features: UserFeatures, hypothetical_changes: dict) -> SimulationResult:
    old_result = compute_score(features)
    updated = features.copy(update=hypothetical_changes)
    new_result = compute_score(updated)
    delta = new_result.total_score - old_result.total_score
    return SimulationResult(
        user_id=features.user_id, old_score=old_result.total_score,
        new_score=new_result.total_score, delta=delta,
        message=f"Score {'increases' if delta >= 0 else 'drops'} by {abs(delta)} points."
    )
```

## Tasks checklist (additions)
- [ ] Implement `simulate_change()` and hardcode-test all 4 worked examples above to confirm
      point deltas land in a believable range vs. the spec's expected numbers
- [ ] Expose via `backend/api/` `/simulate` endpoint
