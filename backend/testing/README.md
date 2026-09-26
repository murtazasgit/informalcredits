# Module: Testing & Quality Assurance

## Goal
Satisfies the spec's explicit "Testing & Quality Assurance" section — this is a **must-have**,
not optional, and judges specifically look for it.

## Tech stack
**pytest** — standard, minimal setup, works for both unit and integration tests.

## What to build

### 1. Data Object Validation (unit tests against ground truth)
Validate that `compute_score()` produces the expected score for known input/output pairs.
```python
# test_scoring_engine.py
from backend.scoring_engine.engine import compute_score
from common.schemas import UserFeatures

def test_high_score_profile():
    features = UserFeatures(
        user_id="TEST1", months_employed=30, housing_status="own", housing_months=24,
        digital_bill_ontime_pct=98, education_level="masters",
        spend_to_income_ratio=0.25, essential_spend_pct=75, cashflow_volatility_pct=3,
        savings_days=200, on_time_payment_pct=99, debt_to_income_ratio=0.15,
        credit_utilization_pct=5, delinquency_flags=[]
    )
    result = compute_score(features)
    assert result.total_score >= 900
    assert result.risk_category == "Excellent"

def test_low_score_profile():
    features = UserFeatures(
        user_id="TEST2", months_employed=3, housing_status="none", housing_months=0,
        digital_bill_ontime_pct=40, education_level="high_school",
        spend_to_income_ratio=0.85, essential_spend_pct=30, cashflow_volatility_pct=25,
        savings_days=10, on_time_payment_pct=60, debt_to_income_ratio=0.60,
        credit_utilization_pct=80, delinquency_flags=["90-day-miss"]
    )
    result = compute_score(features)
    assert result.total_score <= 300
    assert result.risk_category == "Poor"
```
Build a small synthetic "ground truth" CSV (10-20 hand-crafted profiles with expected score
ranges) and loop the test over it — this directly satisfies "validate score accuracy against a
provided synthetic ground truth dataset."

### 2. Integration Test (full stack: API → Dashboard)
```python
# test_integration.py
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

def test_full_flow():
    # 1. register a user
    r = client.post("/users/register", json={...demographic_payload...})
    assert r.status_code == 200

    # 2. upload transactions
    r = client.post("/transactions/upload", files={"file": ("txns.csv", open("test_data/sample_txns.csv", "rb"))})
    assert r.status_code == 200

    # 3. compute score
    r = client.post("/score/U_TEST")
    assert r.status_code == 200
    assert "total_score" in r.json()

    # 4. get explanation
    r = client.get("/explain/U_TEST")
    assert r.status_code == 200
    assert len(r.json()["factors"]) > 0

    # 5. get report
    r = client.get("/report/U_TEST")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
```

### 3. Robustness Test (missing data)
```python
def test_missing_utility_history():
    features = UserFeatures(
        user_id="TEST3", months_employed=12, housing_status="rent", housing_months=6,
        digital_bill_ontime_pct=0,   # no utility history at all
        education_level="bachelor", spend_to_income_ratio=0.4, essential_spend_pct=60,
        cashflow_volatility_pct=10, savings_days=50, on_time_payment_pct=90,
        debt_to_income_ratio=0.3, credit_utilization_pct=0, delinquency_flags=[]
    )
    result = compute_score(features)  # must NOT raise an exception
    assert result.total_score >= 0
```

### 4. Performance test (latency < 15–30s end-to-end)
```python
import time

def test_latency():
    start = time.time()
    client.post("/score/U_TEST")
    client.get("/explain/U_TEST")
    elapsed = time.time() - start
    assert elapsed < 30
```

## Tasks checklist
- [ ] Build a synthetic ground-truth CSV (`test_data/ground_truth.csv`) with 10-20 labeled profiles
- [ ] Write unit tests for the scoring engine against that ground truth
- [ ] Write the full integration test (register → upload → score → explain → report)
- [ ] Write at least 2 robustness tests (missing utility history, missing income, zero transactions)
- [ ] Write the latency test
- [ ] Run `pytest -v` and make sure everything passes before the final demo

## Handoff
No downstream consumer — this module's job is to protect everyone else's code from silent
breakage. Run it after every module is wired into `backend/api/`.
