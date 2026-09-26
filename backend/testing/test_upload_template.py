"""The shipped upload template (data/upload_template/) goes through /upload-raw and spans every tier and risk band."""
import collections
import json
import pathlib

import pytest

TEMPLATE = pathlib.Path(__file__).resolve().parents[2] / "data" / "upload_template"
SPEC_TX_FIELDS = {"transaction_id", "user_id", "date", "amount", "category", "type", "on_time"}
SPEC_DEMO_FIELDS = {"user_id", "age", "employment_status", "education_level", "monthly_income", "city_tier",
                    "months_employed", "housing_status", "housing_months"}


def _upload(client, tx_name="transactions.csv", demo_bytes=None, tx_bytes=None):
    tx_bytes = tx_bytes if tx_bytes is not None else (TEMPLATE / tx_name).read_bytes()
    demo_bytes = demo_bytes if demo_bytes is not None else (TEMPLATE / "demographics.json").read_bytes()
    return client.post("/upload-raw", files={
        "transactions": (tx_name, tx_bytes), "demographics": ("demographics.json", demo_bytes)})


def test_template_files_follow_the_spec_format():
    demos = json.loads((TEMPLATE / "demographics.json").read_text())
    txns = json.loads((TEMPLATE / "transactions.json").read_text())
    assert all(SPEC_DEMO_FIELDS <= set(d) for d in demos)
    assert all(SPEC_TX_FIELDS <= set(t) for t in txns)
    assert {t["type"] for t in txns} == {"Debit", "Credit"}
    assert {"Rent", "Utility", "Salary", "Food"} <= {t["category"] for t in txns}
    assert len({d["user_id"] for d in demos}) == len(demos) == 30
    assert collections.Counter(d["city_tier"] for d in demos) == {"tier-1": 10, "tier-2": 10, "tier-3": 10}


@pytest.mark.parametrize("tx_name", ["transactions.csv", "transactions.json"])
def test_template_uploads_and_covers_every_tier_and_band(client, tx_name):
    r = _upload(client, tx_name)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["processed"] == 30 and body["failed"] == 0
    tier = {d["user_id"]: d["city_tier"] for d in json.loads((TEMPLATE / "demographics.json").read_text())}
    grid = collections.defaultdict(set)
    for res in body["results"]:
        grid[tier[res["user_id"]]].add(res["score"]["risk_category"])
        assert res["warnings"] == [] and res["ml_score"] is not None
    for t in ("tier-1", "tier-2", "tier-3"):
        assert grid[t] == {"Poor", "Fair", "Good", "Excellent"}, (t, grid[t])


def test_csv_and_json_transactions_give_identical_scores(client):
    a = {r["user_id"]: r["score"]["total_score"] for r in _upload(client, "transactions.csv").json()["results"]}
    b = {r["user_id"]: r["score"]["total_score"] for r in _upload(client, "transactions.json").json()["results"]}
    assert a == b


def test_lifestyle_fields_are_honoured(client):
    demos = json.loads((TEMPLATE / "demographics.json").read_text())[:1]
    demos[0].update(credit_util=0.05, delinq_30plus=0, delinq_60plus=0, delinq_90plus=0, positive_habits=3, risk_flags=0)
    good = _upload(client, demo_bytes=json.dumps(demos).encode()).json()["results"][0]["features"]
    assert good["credit_utilization_pct"] == 5.0 and good["delinquency_flags"] == []
    assert good["positive_habits_count"] == 3 and good["risk_flags_count"] == 0
    demos[0].update(credit_util=0.9, delinq_90plus=1, risk_flags=2)
    bad = _upload(client, demo_bytes=json.dumps(demos).encode()).json()["results"][0]["features"]
    assert bad["credit_utilization_pct"] == 90.0 and bad["delinquency_flags"] == ["90_day_late"] and bad["risk_flags_count"] == 2


def test_applicant_without_transactions_and_orphan_transactions(client):
    demos = [{"user_id": "NOTX", "monthly_income": 40000, "city_tier": "tier-2"}]
    tx = b"transaction_id,user_id,date,amount,category,type,on_time\nT1,GHOST,2025-01-01,100,Food,Debit,\n"
    body = _upload(client, demo_bytes=json.dumps(demos).encode(), tx_bytes=tx).json()
    assert body["processed"] == 1 and "No transactions found" in body["results"][0]["warnings"][0]
    assert [e["user_id"] for e in body["errors"]] == ["GHOST"]


def test_bad_uploads_are_rejected_cleanly(client):
    assert _upload(client, demo_bytes=b"not json").status_code == 400
    assert _upload(client, demo_bytes=b"[]").status_code == 400
    assert _upload(client, tx_bytes=b"transaction_id,user_id\nT1,U1\n").status_code == 400   # no amount column


def test_transactions_csv_is_not_scored_as_feature_rows(client):
    r = client.post("/upload-csv", files={"file": ("transactions.csv", (TEMPLATE / "transactions.csv").read_bytes(), "text/csv")})
    assert r.status_code == 400 and "/upload-raw" in r.json()["detail"]
