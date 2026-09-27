"""Plain-language explanation endpoint."""


def _dash(client):
    uid = client.get("/users").json()[0]["user_id"]
    return client.get(f"/dashboard/{uid}").json()


def test_xai_is_sentences_that_match_the_score(client):
    d = _dash(client)
    x = client.post("/xai", json={"features": d["features"]}).json()
    assert x["score"] == d["score"]["total_score"]
    assert str(x["score"]) in x["headline"] and x["risk_category"] in x["headline"]
    for item in x["helping"] + x["holding_back"] + x["actions"] + x["watch_outs"]:
        assert isinstance(item["text"], str) and len(item["text"]) > 10
    assert all(a["points"] > 0 for a in x["actions"]) and all(w["points"] < 0 for w in x["watch_outs"])
    assert all(h["points_lost"] > 0 for h in x["holding_back"])
    assert "age" in x["fairness"]


def test_xai_actions_are_real_rule_engine_gains(client):
    """Every promised gain must equal what /simulate returns for that same change."""
    from backend.explainability.xai import _ACTIONS
    d = _dash(client)
    x = client.post("/xai", json={"features": d["features"]}).json()
    promised = {a["text"]: a["points"] for a in x["actions"]}
    for field, (text, strong, _, _) in _ACTIONS.items():
        if text in promised:
            sim = client.post("/simulate", json={"user_id": d["features"]["user_id"], "hypothetical_changes": {field: strong}}).json()
            assert sim["delta"] == promised[text]


def test_xai_second_opinion_in_words(client):
    x = client.post("/xai", json={"features": _dash(client)["features"]}).json()
    so = x["second_opinion"]
    assert so["verdict"] in ("agree", "close", "differ") and "chance of default" in so["text"]
    assert so["drivers"] and all(d["direction"] in ("helps", "hurts") for d in so["drivers"])


def test_xai_rejects_bad_features(client):
    assert client.post("/xai", json={"features": {"user_id": "x"}}).status_code == 422
