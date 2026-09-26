"""Missing / malformed data must degrade gracefully (scored with warnings), never crash."""
import json

import pytest

from backend.scoring_engine.engine import compute_score
from data.feature_engineering import _build_delinquency_flags, compute_user_features, load_transactions

TXNS_NO_UTILITY = [
    {"type": "Credit", "date": "2025-01-01", "amount": 50000.0, "category": "Salary", "on_time": None},
    {"type": "Debit", "date": "2025-01-05", "amount": 1200.0, "category": "Food", "on_time": None},
    {"type": "Debit", "date": "2025-02-05", "amount": 1500.0, "category": "Food", "on_time": None},
]


def test_user_with_no_utility_history_scores_without_crashing():
    f = compute_user_features("NOUTIL", {"monthly_income": 50000, "months_employed": 12}, TXNS_NO_UTILITY)
    r = compute_score(f)
    assert 0 <= r.total_score <= 1000
    assert f.digital_bill_ontime_pct == 0.0   # no bill history -> no credit for it (documented behaviour)


def test_user_with_no_transactions_at_all():
    f = compute_user_features("EMPTY", {"monthly_income": 30000}, [])
    assert 0 <= compute_score(f).total_score <= 1000


@pytest.mark.parametrize("income", [0, None, "", -5, "abc"])
def test_zero_null_or_invalid_income_does_not_crash(income):
    f = compute_user_features("BADINC", {"monthly_income": income}, TXNS_NO_UTILITY)
    assert 0 <= compute_score(f).total_score <= 1000


def test_demographics_with_missing_fields():
    f = compute_user_features("SPARSE", {}, [])
    assert compute_score(f).total_score >= 0


def test_json_transactions_are_ingested(tmp_path):
    rows = [{"transaction_id": "T1", "user_id": "U1", "date": "2025-03-01", "amount": "100.5",
             "category": "Utility Bill", "type": "DEBIT", "on_time": True}]
    p = tmp_path / "tx.json"
    p.write_text(json.dumps(rows))
    tx = load_transactions(str(p))
    assert tx[0]["amount"] == 100.5 and tx[0]["category"] == "Utility" and tx[0]["type"] == "Debit"
    assert tx[0]["on_time"] is True


def test_csv_upload_with_missing_columns_returns_scores_and_warnings(client):
    csv_body = "user_id,monthly_income\nonly_income,4000\n"
    r = client.post("/upload-csv", files={"file": ("sparse.csv", csv_body, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["processed"] == 1 and body["failed"] == 0
    warnings = " ".join(body["results"][0]["warnings"])
    assert "Missing columns" in warnings and "spend-to-income" in warnings


def test_csv_upload_with_blank_and_garbage_values(client):
    csv_body = ("user_id,months_employed,savings_days,dti,monthly_income,monthly_spend\n"
                "blank,,, ,,\n"
                "garbage,abc,xyz,n/a,-1,zzz\n"
                "zero_spend,12,30,0.2,4000,0\n")
    r = client.post("/upload-csv", files={"file": ("bad.csv", csv_body, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["processed"] == 3 and body["failed"] == 0
    zero_spend = body["results"][2]["features"]
    assert zero_spend["spend_to_income_ratio"] == 0.0   # genuine zero spend is not replaced by the 0.5 default


def test_csv_upload_rejects_non_csv_and_empty(client):
    assert client.post("/upload-csv", files={"file": ("x.txt", "a,b", "text/plain")}).status_code == 400
    assert client.post("/upload-csv", files={"file": ("x.csv", "a,b\n", "text/csv")}).status_code == 400


def test_multiple_delinquency_events_collapse_to_multiple_late():
    assert _build_delinquency_flags({"delinq_30plus": 3}) == ["multiple_late"]
    assert _build_delinquency_flags({"delinq_30plus": 1}) == ["30_day_late"]
    assert _build_delinquency_flags({"delinq_60plus": 1}) == ["60_day_late"]
    assert _build_delinquency_flags({}) == []
