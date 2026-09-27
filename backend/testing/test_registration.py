"""Self-registration with uploaded data, login, and re-scoring from newer uploads (all persisted)."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "data" / "upload_template"

GOOD = ("user_id,months_at_job,housing,rent_on_time_months,digital_payment_rate,education,monthly_income,"
        "monthly_spend,essential_pct,cashflow_volatility,savings_days,on_time_rate,dti,credit_util,"
        "delinq_30plus,delinq_60plus,delinq_90plus,positive_habits,risk_flags\n"
        "x,36,own,24,0.95,master,8000,3000,0.6,0.05,120,0.98,0.15,0.1,0,0,0,3,0\n")
WEAK = GOOD.replace("x,36,own,24,0.95,master,8000,3000,0.6,0.05,120,0.98,0.15,0.1,0,0,0,3,0",
                    "x,2,none,0,0.3,none,1500,1450,0.9,0.5,2,0.4,0.7,0.9,3,2,1,0,3")


def _csv(text):
    return {"features_csv": ("data.csv", text.encode(), "text/csv")}


def test_register_with_csv_then_login_and_dashboard(client):
    r = client.post("/auth/register", data={"user_id": "new_user_1", "password": "longenough1"}, files=_csv(GOOD))
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    dash = client.get("/me/dashboard", headers=headers).json()
    assert dash["user_id"] == "new_user_1" and dash["score"]["total_score"] > 0
    # the password works for a normal login afterwards
    assert client.post("/auth/login", json={"user_id": "new_user_1", "password": "longenough1"}).status_code == 200
    assert client.post("/auth/login", json={"user_id": "new_user_1", "password": "wrong"}).status_code == 401


def test_register_validation(client):
    ok = {"user_id": "someone_else", "password": "longenough1"}
    assert client.post("/auth/register", data={**ok, "password": "short"}, files=_csv(GOOD)).status_code == 422
    assert client.post("/auth/register", data={**ok, "user_id": "a b"}, files=_csv(GOOD)).status_code == 422
    assert client.post("/auth/register", data=ok).status_code == 400   # no data files at all
    assert client.post("/auth/register", data=ok, files=_csv("user_id\n")).status_code == 400   # header only
    taken = client.get("/users").json()[0]["user_id"]
    assert client.post("/auth/register", data={**ok, "user_id": taken}, files=_csv(GOOD)).status_code == 409
    assert client.post("/auth/login", json={"user_id": "someone_else", "password": "longenough1"}).status_code == 401


def test_register_with_transactions_and_demographics(client):
    files = {
        "transactions": ("transactions.csv", (TEMPLATE / "transactions.csv").read_bytes(), "text/csv"),
        "demographics": ("demographics.json", (TEMPLATE / "demographics.json").read_bytes(), "application/json"),
    }
    r = client.post("/auth/register", data={"user_id": "raw_user_1", "password": "longenough1"}, files=files)
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/me/dashboard", headers=headers).json()["score"]["total_score"] > 0


def test_update_data_rescores_and_persists(client, lender_headers):
    r = client.post("/auth/register", data={"user_id": "updater_1", "password": "longenough1"}, files=_csv(WEAK))
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    before = client.get("/me/dashboard", headers=headers).json()["score"]["total_score"]

    upd = client.post("/me/data", headers=headers, files=_csv(GOOD))
    assert upd.status_code == 200, upd.text
    body = upd.json()
    assert body["previous_score"] == before and body["score"]["total_score"] > before
    assert client.get("/me/dashboard", headers=headers).json()["score"]["total_score"] == body["score"]["total_score"]

    # stored in the database, so it survives a restart-style reload...
    from database.db import load_all_user_data
    stored = {uid: feats for uid, feats, _ in load_all_user_data()}
    assert "updater_1" in stored
    # ...and the lender portal sees the user at the newest score
    listed = {c["user_id"]: c for c in client.get("/lender/candidates", headers=lender_headers).json()}
    assert listed["updater_1"]["score"] == body["score"]["total_score"]

    assert client.post("/me/data", files=_csv(GOOD)).status_code == 401
    assert client.post("/me/data", headers=headers).status_code == 400


def test_check_id_flags_taken_ids_case_insensitively(client):
    taken = client.get("/users").json()[0]["user_id"]
    for candidate in (taken, taken.lower()):
        r = client.get("/auth/check-id", params={"user_id": candidate}).json()
        assert r["available"] is False and "different" in r["reason"]
    assert client.get("/auth/check-id", params={"user_id": "brand_new_id"}).json()["available"] is True
    assert client.get("/auth/check-id", params={"user_id": "a b"}).json()["available"] is False
    r = client.post("/auth/register", data={"user_id": taken.lower(), "password": "longenough1"}, files=_csv(GOOD))
    assert r.status_code == 409
