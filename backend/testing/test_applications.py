"""Lender self-registration and the borrower -> chosen lender pre-approval application flow."""
import pytest


@pytest.fixture(autouse=True)
def _fresh(client):
    from backend.api.main import application_store
    application_store.clear()
    yield
    application_store.clear()


def _register_lender(client, bank="Test Bank", username="testbank", password="testbank123"):
    r = client.post("/lender/register", json={"bank_name": bank, "username": username, "password": password})
    return r


def _eligible(client, headers_for):
    """A seeded user + product that user qualifies for."""
    products = client.get("/products").json()
    cheapest = min(products, key=lambda p: p["min_score_required"])
    for u in client.get("/users").json():
        uid = u["user_id"]
        if client.get(f"/dashboard/{uid}").json()["score"]["total_score"] >= cheapest["min_score_required"]:
            return uid, cheapest, headers_for(uid)
    pytest.skip("no eligible user in dataset")


FORM = dict(requested_amount=50000, tenure_months=12, purpose="Laptop", full_name="Asha Rao", phone="9999999999")


def test_lender_registration_and_login(client):
    r = _register_lender(client, "Alpha Bank", "alpha", "alphapass1")
    assert r.status_code in (200, 409)
    login = client.post("/lender/login", json={"username": "ALPHA", "password": "alphapass1"})
    assert login.status_code == 200 and login.json()["bank_name"] == "Alpha Bank"
    assert client.post("/lender/login", json={"username": "alpha", "password": "wrong"}).status_code == 401
    assert _register_lender(client, "Alpha Bank", "other", "otherpass1").status_code == 409   # bank name taken
    assert _register_lender(client, "Beta", "alpha", "otherpass1").status_code == 409         # username taken
    assert _register_lender(client, "Gamma", "ab", "otherpass1").status_code == 422
    assert _register_lender(client, "Gamma", "gamma", "short").status_code == 422
    names = [l["bank_name"] for l in client.get("/lenders").json()]
    assert "Alpha Bank" in names and "Demo Bank" in names


def test_application_goes_to_the_chosen_lender_only(client, user_auth):
    _register_lender(client, "Chosen Bank", "chosen", "chosenpass1")
    _register_lender(client, "Other Bank", "otherbank", "otherpass1")
    uid, product, h = _eligible(client, user_auth)
    body = dict(FORM, lender_id="chosen", product_id=product["product_id"])
    r = client.post(f"/users/{uid}/applications", json=body, headers=h)
    assert r.status_code == 201 and r.json()["bank_name"] == "Chosen Bank" and r.json()["status"] == "submitted"
    assert client.post(f"/users/{uid}/applications", json=body, headers=h).status_code == 409   # duplicate

    tok = lambda u, p: {"Authorization": "Bearer " + client.post("/lender/login", json={"username": u, "password": p}).json()["token"]}
    mine = client.get("/lender/applications", headers=tok("chosen", "chosenpass1")).json()
    assert len(mine) == 1 and mine[0]["user_id"] == uid and mine[0]["applicant_name"] == "Asha Rao"
    assert client.get("/lender/applications", headers=tok("otherbank", "otherpass1")).json() == []


def test_lender_decision_reaches_borrower(client, user_auth):
    _register_lender(client, "Decide Bank", "decide", "decidepass1")
    uid, product, h = _eligible(client, user_auth)
    client.post(f"/users/{uid}/applications", json=dict(FORM, lender_id="decide", product_id=product["product_id"]), headers=h)
    lh = {"Authorization": "Bearer " + client.post("/lender/login", json={"username": "decide", "password": "decidepass1"}).json()["token"]}
    app_id = client.get("/lender/applications", headers=lh).json()[0]["application_id"]
    assert client.post(f"/lender/applications/{app_id}/decision", json={"decision": "maybe"}, headers=lh).status_code == 422
    assert client.post(f"/lender/applications/{app_id}/decision", json={"decision": "approve", "note": "Welcome"}, headers=lh).status_code == 200
    assert client.post(f"/lender/applications/{app_id}/decision", json={"decision": "decline"}, headers=lh).status_code == 409
    mine = client.get(f"/users/{uid}/applications", headers=h).json()
    assert mine[0]["status"] == "approved" and mine[0]["lender_note"] == "Welcome" and mine[0]["bank_name"] == "Decide Bank"
    demo = {"Authorization": "Bearer " + client.post("/lender/login", json={"username": "lender", "password": "lender123"}).json()["token"]}
    assert client.post(f"/lender/applications/{app_id}/decision", json={"decision": "approve"}, headers=demo).status_code == 404


def test_application_validation_and_auth(client, user_auth):
    uid, product, h = _eligible(client, user_auth)
    good = dict(FORM, lender_id="lender", product_id=product["product_id"])
    assert client.post(f"/users/{uid}/applications", json=good).status_code == 401
    other = next(u["user_id"] for u in client.get("/users").json() if u["user_id"] != uid)
    assert client.post(f"/users/{other}/applications", json=good, headers=h).status_code == 403
    assert client.post(f"/users/{uid}/applications", json=dict(good, lender_id="nope"), headers=h).status_code == 404
    assert client.post(f"/users/{uid}/applications", json=dict(good, product_id="nope"), headers=h).status_code == 404
    assert client.post(f"/users/{uid}/applications", json=dict(good, requested_amount=0), headers=h).status_code == 422
    assert client.get("/lender/applications").status_code == 401
