"""Lender portal: real auth gate, server-side PII masking, offer push -> consumer sees it -> accept unlocks PII."""
import json

import pytest

from backend.lender.pii import get_pii


@pytest.fixture(autouse=True)
def _fresh_offers(client):
    from backend.api.main import offer_store
    offer_store.clear()
    yield
    offer_store.clear()


def test_endpoints_are_gated(client):
    for method, path in [("get", "/lender/candidates"), ("get", "/lender/candidates/C-x"), ("get", "/lender/offers")]:
        assert getattr(client, method)(path).status_code == 401
    assert client.post("/lender/offers", json={"candidate_refs": ["C-x"], "product_id": "P"}).status_code == 401
    assert client.get("/lender/candidates", headers={"Authorization": "Bearer forged"}).status_code == 401
    assert client.post("/lender/login", json={"username": "lender", "password": "nope"}).status_code == 401
    assert client.post("/lender/login", json={"username": "x", "password": "lender123"}).status_code == 401


def test_candidate_search_filters(client, lender_headers):
    everyone = client.get("/lender/candidates", headers=lender_headers).json()
    assert everyone and everyone == sorted(everyone, key=lambda c: -c["score"])
    high = client.get("/lender/candidates?min_score=650", headers=lender_headers).json()
    assert high and all(c["score"] >= 650 for c in high) and len(high) < len(everyone)
    band = client.get("/lender/candidates?min_score=400&max_score=500", headers=lender_headers).json()
    assert all(400 <= c["score"] <= 500 for c in band)
    tier = client.get("/lender/candidates?city_tier=tier-2", headers=lender_headers).json()
    assert all(c["city_tier"] == "tier-2" for c in tier)
    good = client.get("/lender/candidates?risk_category=good", headers=lender_headers).json()
    assert all(c["risk_category"] == "Good" for c in good)


def test_candidates_show_user_ids_but_never_contact_pii(client, lender_headers):
    raw = client.get("/lender/candidates", headers=lender_headers).text
    rows = json.loads(raw)
    assert all(r["user_id"].startswith("USR_") for r in rows)
    for u in client.get("/users").json()[:50]:
        pii = get_pii(u["user_id"])
        assert pii["name"] not in raw and pii["phone"] not in raw and pii["address"] not in raw
    for key in ("name", "address", "phone", "contact"):
        assert f'"{key}"' not in raw
    detail = client.get(f"/lender/candidates/{rows[0]['user_id']}", headers=lender_headers)
    assert detail.json()["pii_unlocked"] is False and "contact" not in detail.json()
    for pii_value in get_pii(rows[0]["user_id"]).values():
        assert pii_value not in detail.text


def test_candidate_detail_matches_consumer_score_analysis(client, lender_headers):
    uid = client.get("/lender/candidates?min_score=650", headers=lender_headers).json()[0]["user_id"]
    lender_view = client.get(f"/lender/candidates/{uid}", headers=lender_headers).json()
    consumer_view = client.get(f"/dashboard/{uid}").json()
    assert lender_view["score"] == consumer_view["score"]                 # same rule-engine breakdown
    assert lender_view["explanation"] == consumer_view["explanation"]     # same factor explanations
    assert lender_view["features"] == consumer_view["features"]
    assert len(lender_view["score"]["breakdown"]) == 14
    assert lender_view["ml_score"]["method"] == "ml_pd" and lender_view["recommendations"]
    assert lender_view["user_id"] == uid and set(lender_view["profile"]) <= {
        "age", "employment_status", "education_level", "monthly_income", "city_tier"}
    assert client.get("/lender/candidates/NOPE", headers=lender_headers).status_code == 404


def test_offer_can_be_pushed_by_user_id(client, lender_headers):
    cand = client.get("/lender/candidates?min_score=650", headers=lender_headers).json()[0]
    product = _cheapest_eligible_product(client, cand["score"])
    res = client.post("/lender/offers", headers=lender_headers, json={
        "user_ids": [cand["user_id"]], "product_id": product["product_id"]}).json()["results"][0]
    assert res["status"] == "pushed" and res["user_id"] == cand["user_id"]


def _pick(client, headers):
    cand = client.get("/lender/candidates?min_score=650", headers=headers).json()[0]
    users = {__import__("backend.lender.router", fromlist=["x"]).candidate_ref(u["user_id"]): u["user_id"]
             for u in client.get("/users").json()}
    return cand, users[cand["candidate_ref"]]


def _cheapest_eligible_product(client, score):
    return next(p for p in client.get("/products").json() if p["min_score_required"] <= score)


def test_push_offer_consumer_sees_it_and_accept_unlocks_pii(client, lender_headers):
    cand, uid = _pick(client, lender_headers)
    product = _cheapest_eligible_product(client, cand["score"])

    push = client.post("/lender/offers", headers=lender_headers, json={
        "candidate_refs": [cand["candidate_ref"]], "product_id": product["product_id"], "message": "Welcome!"})
    assert push.status_code == 200
    result = push.json()["results"][0]
    assert result["status"] == "pushed"
    offer_id = result["offer_id"]

    # the consumer's side shows the offer (and does not leak lender-internal keys)
    offers = client.get(f"/users/{uid}/offers").json()
    assert len(offers) == 1 and offers[0]["offer_id"] == offer_id
    assert offers[0]["status"] == "pushed" and offers[0]["product_id"] == product["product_id"]
    assert offers[0]["message"] == "Welcome!" and "user_id" not in offers[0]

    # lender sees status but still no PII
    detail = client.get(f"/lender/candidates/{cand['candidate_ref']}", headers=lender_headers).json()
    assert detail["offer_status"] == "pushed" and "contact" not in detail

    # duplicate push is refused
    again = client.post("/lender/offers", headers=lender_headers, json={
        "candidate_refs": [cand["candidate_ref"]], "product_id": product["product_id"]}).json()
    assert again["results"][0]["status"] == "duplicate"

    # consumer accepts -> PII released, only now
    r = client.post(f"/users/{uid}/offers/{offer_id}/respond", json={"action": "accept"})
    assert r.status_code == 200 and r.json()["status"] == "accepted"
    detail = client.get(f"/lender/candidates/{cand['candidate_ref']}", headers=lender_headers).json()
    assert detail["pii_unlocked"] is True and detail["contact"] == get_pii(uid)
    listed = [c for c in client.get("/lender/candidates", headers=lender_headers).json()
              if c["candidate_ref"] == cand["candidate_ref"]][0]
    assert listed["pii_unlocked"] is True and "contact" not in listed   # list view never carries PII

    # cannot answer twice
    assert client.post(f"/users/{uid}/offers/{offer_id}/respond", json={"action": "reject"}).status_code == 409


def test_rejected_offer_keeps_pii_hidden(client, lender_headers):
    cand, uid = _pick(client, lender_headers)
    product = _cheapest_eligible_product(client, cand["score"])
    oid = client.post("/lender/offers", headers=lender_headers, json={
        "candidate_refs": [cand["candidate_ref"]], "product_id": product["product_id"]}).json()["results"][0]["offer_id"]
    client.post(f"/users/{uid}/offers/{oid}/respond", json={"action": "reject"})
    detail = client.get(f"/lender/candidates/{cand['candidate_ref']}", headers=lender_headers).json()
    assert detail["pii_unlocked"] is False and "contact" not in detail and detail["offer_status"] == "rejected"


def test_push_validation(client, lender_headers):
    cand, uid = _pick(client, lender_headers)
    real_pid = client.get("/products").json()[0]["product_id"]
    assert client.post("/lender/offers", headers=lender_headers,
                       json={"candidate_refs": [cand["candidate_ref"]], "product_id": "NOPE"}).status_code == 404
    assert client.post("/lender/offers", headers=lender_headers,
                       json={"candidate_refs": [], "product_id": real_pid}).status_code == 422
    mixed = client.post("/lender/offers", headers=lender_headers,
                        json={"candidate_refs": ["C-doesnotexist"], "product_id": real_pid}).json()
    assert mixed["results"][0]["status"] == "unknown_candidate"
    # an offer for a product the candidate doesn't qualify for is refused
    top = max(client.get("/products").json(), key=lambda p: p["min_score_required"])
    low = client.get("/lender/candidates?max_score=%d" % (top["min_score_required"] - 1), headers=lender_headers).json()
    if low:
        res = client.post("/lender/offers", headers=lender_headers, json={
            "candidate_refs": [low[0]["candidate_ref"]], "product_id": top["product_id"]}).json()
        assert res["results"][0]["status"] == "ineligible"


def test_consumer_cannot_answer_someone_elses_offer(client, lender_headers):
    cand, uid = _pick(client, lender_headers)
    product = _cheapest_eligible_product(client, cand["score"])
    oid = client.post("/lender/offers", headers=lender_headers, json={
        "candidate_refs": [cand["candidate_ref"]], "product_id": product["product_id"]}).json()["results"][0]["offer_id"]
    other = next(u["user_id"] for u in client.get("/users").json() if u["user_id"] != uid)
    assert client.post(f"/users/{other}/offers/{oid}/respond", json={"action": "accept"}).status_code == 404
    assert client.post(f"/users/{uid}/offers/{oid}/respond", json={"action": "bogus"}).status_code == 422
    assert client.get("/users/NOPE/offers").status_code == 404


def test_lender_offers_listing_shows_user_id(client, lender_headers):
    cand, uid = _pick(client, lender_headers)
    product = _cheapest_eligible_product(client, cand["score"])
    client.post("/lender/offers", headers=lender_headers, json={
        "candidate_refs": [cand["candidate_ref"]], "product_id": product["product_id"]})
    listing = client.get("/lender/offers", headers=lender_headers)
    assert listing.status_code == 200 and listing.json()[0]["user_id"] == uid and listing.json()[0]["status"] == "pushed"


def test_username_is_case_and_whitespace_insensitive_password_is_exact(client):
    assert client.post("/lender/login", json={"username": " Lender ", "password": "lender123"}).status_code == 200
    assert client.post("/lender/login", json={"username": "lender", "password": "LENDER123"}).status_code == 401
