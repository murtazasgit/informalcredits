import os
import pathlib
import tempfile

import pytest
from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Tests get their own throwaway SQLite file so they never touch database/altcredit.db.
os.environ["DATABASE_URL"] = "sqlite:///" + str(pathlib.Path(tempfile.mkdtemp()) / "test.db")


@pytest.fixture(scope="session")
def client():
    from backend.api.main import app
    with TestClient(app) as c:   # runs the startup hook (loads data, scores all users)
        yield c


@pytest.fixture()
def lender_headers(client):
    r = client.post("/lender/login", json={"username": "lender", "password": "lender123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def user_auth(client):
    """user_auth(uid) -> Authorization headers for that seeded consumer account."""
    def _login(uid, password="altcredit123"):
        r = client.post("/auth/login", json={"user_id": uid, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}
    return _login
