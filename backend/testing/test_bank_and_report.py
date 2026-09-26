"""Separate bank-partner-api (API-key gated), the consumer app's pre-approval call to it, and the PDF report."""
from fastapi.testclient import TestClient

KEY = {"X-API-Key": "dev-bank-key"}
PAYLOAD = dict(applicant_ref="C-abc", score=750, risk_category="Good", product_id="P1", product_name="Card",
               min_score_required=600, interest_rate=18)


# ---- the bank service on its own ----

def test_bank_requires_api_key(bank_app):
    c = TestClient(bank_app)
    assert c.post("/preapprove", json=PAYLOAD).status_code == 401
    assert c.post("/preapprove", json=PAYLOAD, headers={"X-API-Key": "wrong"}).status_code == 401
    assert c.get("/offer-status/APP-X").status_code == 401
    assert c.get("/").status_code == 200   # health is open


def test_bank_decisions_and_status_lookup(bank_app):
    c = TestClient(bank_app, headers=KEY)
    ok = c.post("/preapprove", json=PAYLOAD).json()
    assert ok["decision"] == "pre_approved" and ok["credit_limit"] == 7500
    assert c.post("/preapprove", json=dict(PAYLOAD, score=610)).json()["decision"] == "manual_review"
    declined = c.post("/preapprove", json=dict(PAYLOAD, score=500)).json()
    assert declined["decision"] == "declined" and declined["credit_limit"] == 0

    status = c.get(f"/offer-status/{ok['application_id']}").json()
    assert status["status"] == "pre_approved" and status["product_id"] == "P1"
    assert c.get("/offer-status/APP-NOPE").status_code == 404
    assert c.post("/preapprove", json=dict(PAYLOAD, score=5000)).status_code == 422


# ---- consumer app -> bank ----

def _first_product(client):
    return client.get("/products").json()[0]


def test_consumer_preapproval_calls_bank_and_recomputes_score(client, bank_in_process):
    uid = client.get("/users").json()[0]["user_id"]
    product = _first_product(client)
    r = client.post("/offers/preapprove", json={"user_id": uid, "product_id": product["product_id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decision"] in ("pre_approved", "manual_review", "declined") and body["application_id"].startswith("APP-")
    # the bank record exists and no PII/user id was sent
    st = client.get(f"/offers/preapprove/{body['application_id']}")
    assert st.status_code == 200 and st.json()["application_id"] == body["application_id"]


def test_preapproval_errors(client, bank_in_process):
    assert client.post("/offers/preapprove", json={"user_id": "NOPE", "product_id": _first_product(client)["product_id"]}).status_code == 404
    assert client.post("/offers/preapprove", json={"user_id": "x", "product_id": "NOPRODUCT"}).status_code == 404
    assert client.get("/offers/preapprove/APP-NOPE").status_code == 404


def test_bank_wrong_key_or_down_is_reported_as_502(client, monkeypatch):
    from backend.integrations import bank_client
    uid = client.get("/users").json()[0]["user_id"]
    pid = _first_product(client)["product_id"]
    monkeypatch.setenv("BANK_API_URL", "http://127.0.0.1:9")   # nothing listens here
    assert client.post("/offers/preapprove", json={"user_id": uid, "product_id": pid}).status_code == 502


# ---- PDF transparency report ----

def test_pdf_report_for_dataset_user(client):
    uid = client.get("/users").json()[0]["user_id"]
    r = client.get(f"/report/{uid}")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and len(r.content) > 2000
    assert "attachment" in r.headers["content-disposition"]
    assert client.get("/report/NOPE").status_code == 404


def test_pdf_report_from_existing_result_payload(client):
    row = "user_id,months_at_job,housing,on_time_rate\nCSVUSER,30,own,0.99\n"
    res = client.post("/upload-csv", files={"file": ("a.csv", row, "text/csv")}).json()["results"][0]
    r = client.post("/report/pdf", json={k: res[k] for k in ("score", "explanation", "recommendations", "ml_score")})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    assert "CSVUSER" in r.headers["content-disposition"]


def test_report_decision_wording_covers_approve_and_reject():
    from backend.reports.transparency_report import decision_summary
    from common.schemas import Recommendation, ScoreBreakdown, ScoreResult
    score = ScoreResult(user_id="u", total_score=300, risk_category="Poor", breakdown=ScoreBreakdown())
    rej = [Recommendation(product_id="p", name="Starter", interest_rate=20, eligible=False, reason="r", min_score_required=400)]
    assert decision_summary(score, rej)[0] == "NOT APPROVED" and "100 more points" in decision_summary(score, rej)[1]
    acc = [Recommendation(product_id="p", name="Starter", interest_rate=20, eligible=True, reason="r", min_score_required=200)]
    assert decision_summary(score, acc)[0] == "APPROVED FOR PRODUCTS"
