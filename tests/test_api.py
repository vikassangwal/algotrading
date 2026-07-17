"""End-to-end API tests via FastAPI TestClient (httpx).

Skipped entirely on Python < 3.11: the old starlette/httpx bundled with
such envs crashes the interpreter when TestClient is instantiated (not a
catchable exception). CI/Docker runs Python 3.11 where these execute.
"""
import sys
import pytest

if sys.version_info < (3, 11):
    pytest.skip("Requires Python 3.11+ TestClient/starlette", allow_module_level=True)

from app import auth


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _token(client):
    resp = client.post("/login", json={"password": auth._admin_password()})
    assert resp.status_code == 200
    return resp.json()["token"]


def test_health_no_auth(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_protected_route_requires_auth(client):
    r = client.get("/config")
    assert r.status_code in (401, 403)


def test_login_wrong_password(client):
    r = client.post("/login", json={"password": "definitely-wrong"})
    assert r.status_code == 401


def test_login_and_access_config(client):
    token = _token(client)
    r = client.get("/config", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "capital" in r.json()


def test_old_hardcoded_token_is_rejected(client):
    r = client.get("/config", headers={"Authorization": "Bearer admin-token-123"})
    assert r.status_code in (401, 403)


def test_backtest_endpoint_mock(client):
    token = _token(client)
    r = client.get("/api/backtest/RELIANCE?source=mock&years=1",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "summary" in body
    assert body["summary"]["data_source"] == "mock"
    assert body["summary"]["total_trades"] >= 0
