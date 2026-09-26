"""Full-stack integration (profile in -> dashboard payload out) and measured latency."""
import csv
import io
import random
import time

MAX_SECONDS = 15   # spec: 15-30 s end to end; we hold ourselves to the stricter bound

FULL_ROW = dict(user_id="INT1", months_at_job=24, housing="rent", rent_on_time_months=12,
                digital_payment_rate=0.85, education="bachelor", monthly_income=5000, monthly_spend=2000,
                essential_pct=0.65, cashflow_volatility=0.08, savings_days=90, on_time_rate=0.92, dti=0.25,
                credit_util=0.2, delinq_30plus=0, delinq_60plus=0, delinq_90plus=0, positive_habits=2, risk_flags=0)


def _csv(rows):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return out.getvalue()


def _upload(client, rows, name="p.csv"):
    return client.post("/upload-csv", files={"file": (name, _csv(rows), "text/csv")})


def test_complete_profile_in_dashboard_payload_out(client):
    r = _upload(client, [FULL_ROW])
    assert r.status_code == 200
    res = r.json()["results"][0]
    assert res["score"]["risk_category"] in ("Poor", "Fair", "Good", "Excellent")
    assert len(res["explanation"]["factors"]) == 14
    assert all(f["text"] for f in res["explanation"]["factors"])
    assert res["explanation"]["summary_text"]
    assert res["recommendations"] and {"eligible", "reason", "interest_rate"} <= set(res["recommendations"][0])
    assert res["ml_score"] is not None and res["ml_score"]["method"] == "ml_pd"   # PD model wired end to end
    assert res["features"]["user_id"] == "INT1"


def test_exact_score_for_known_csv_profile(client):
    # emp 24=150, rent 12mo=60, digital 85=45, bachelor=40 | spend .4=80, essentials 65=45, vol 8=40, savings 90=50
    # on-time 92=100, dti .25=80, util 20=70, no delinquency=150 | bonus 2 habits=+40, no risk flags => 950
    res = _upload(client, [FULL_ROW]).json()["results"][0]
    assert res["score"]["total_score"] == 950
    assert res["score"]["risk_category"] == "Excellent"


def test_dataset_user_dashboard(client):
    uid = client.get("/users").json()[0]["user_id"]
    d = client.get(f"/dashboard/{uid}").json()
    assert {"user", "score", "explanation", "recommendations", "features"} <= set(d)
    assert 0 <= d["score"]["total_score"] <= 1000
    assert client.get("/dashboard/NOPE").status_code == 404


def test_latency_single_profile_and_bulk_upload(client):
    t0 = time.perf_counter()
    r = _upload(client, [FULL_ROW])
    single = time.perf_counter() - t0
    assert r.status_code == 200

    rng = random.Random(7)
    rows = [dict(FULL_ROW, user_id=f"BULK{i}", savings_days=rng.randint(0, 300), dti=round(rng.random() * 0.6, 2))
            for i in range(200)]
    t0 = time.perf_counter()
    r = _upload(client, rows, "bulk.csv")
    bulk = time.perf_counter() - t0
    assert r.status_code == 200 and r.json()["processed"] == 200

    uid = client.get("/users").json()[0]["user_id"]
    t0 = time.perf_counter()
    client.get(f"/dashboard/{uid}")
    dash = time.perf_counter() - t0

    print(f"\nLATENCY single-profile upload={single:.3f}s  200-row upload={bulk:.3f}s  dashboard={dash:.3f}s")
    assert single < MAX_SECONDS and bulk < MAX_SECONDS and dash < MAX_SECONDS


def test_latency_cold_ingestion_to_score():
    """Ingestion (load + feature engineering of the whole dataset) through scoring, cold."""
    from backend.api.main import _get_data_dir
    from backend.scoring_engine.engine import compute_score
    from data.feature_engineering import get_all_user_features
    t0 = time.perf_counter()
    feats = get_all_user_features(_get_data_dir())
    scores = [compute_score(f) for f in feats.values()]
    elapsed = time.perf_counter() - t0
    print(f"\nLATENCY cold ingestion+scoring of {len(scores)} users = {elapsed:.3f}s")
    assert scores and elapsed < MAX_SECONDS
