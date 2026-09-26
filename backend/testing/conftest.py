import importlib.util
import pathlib

import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def client():
    from backend.api.main import app
    with TestClient(app) as c:   # runs the startup hook (loads data, scores all users)
        yield c


@pytest.fixture(scope="session")
def bank_app():
    spec = importlib.util.spec_from_file_location("bank_partner_app", ROOT / "bank-partner-api" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture()
def bank_in_process(monkeypatch, bank_app):
    """Point the consumer app's bank client at the separate bank app, in-process, with the API key."""
    from backend.integrations import bank_client
    monkeypatch.setattr(
        bank_client, "_client",
        lambda: TestClient(bank_app, base_url="http://bank", headers={"X-API-Key": "dev-bank-key"}),
    )
    return bank_app


@pytest.fixture()
def lender_headers(client):
    r = client.post("/lender/login", json={"username": "lender", "password": "lender123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}
