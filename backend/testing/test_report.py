"""PDF transparency report."""


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
