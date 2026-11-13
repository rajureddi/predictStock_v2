from fastapi.testclient import TestClient


def test_single_login_gates_the_api(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETMIND_AUTH", "1")
    monkeypatch.setenv("MARKETMIND_AUTH_FILE", str(tmp_path / "auth.json"))
    from app.auth import DEFAULT_PASSWORD, DEFAULT_USERNAME, _FAILS
    from app.main import app

    _FAILS.clear()
    client = TestClient(app)

    blocked = client.get("/api/scan/status")
    assert blocked.status_code == 401

    wrong = client.post("/api/auth/login", json={"username": DEFAULT_USERNAME, "password": "nope"})
    assert wrong.status_code == 401

    ok = client.post("/api/auth/login", json={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD})
    assert ok.status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/scan/status").status_code == 200

    client.post("/api/auth/logout")
    assert client.get("/api/scan/status").status_code == 401
