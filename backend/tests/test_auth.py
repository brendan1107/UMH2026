"""Tests for authentication and health-check endpoints."""


def test_health_check(client):
    """GET /health should return a healthy status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert "service" in body


def test_get_me(client):
    """GET /api/auth/me should return the current user's claims."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["uid"] == "dev-user-001"
    assert data["email"] == "dev@test.com"


def test_get_me_dev_bypass(client_no_auth):
    """Bearer dev-bypass token should be accepted in development mode."""
    resp = client_no_auth.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer dev-bypass"},
    )
    assert resp.status_code == 200
    assert resp.json()["uid"] == "dev-user-001"


def test_get_me_no_auth(client_no_auth):
    """Missing Authorization header should return 401."""
    resp = client_no_auth.get("/api/auth/me")
    assert resp.status_code == 401


def test_get_me_invalid_token(client_no_auth):
    """An unrecognised token should return 401 (Firebase verify will fail)."""
    resp = client_no_auth.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


def test_sync_session_creates_user(client):
    """POST /api/auth/session should sync the user to Firestore and return ok."""
    resp = client.post("/api/auth/session")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["uid"] == "dev-user-001"


def test_sync_session_idempotent(client):
    """Calling POST /api/auth/session twice should succeed both times."""
    assert client.post("/api/auth/session").status_code == 200
    assert client.post("/api/auth/session").status_code == 200


def test_logout(client):
    """POST /api/auth/logout should return ok (client-side logout)."""
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_not_implemented(client):
    """POST /api/auth/register is reserved for Firebase and returns 501."""
    resp = client.post("/api/auth/register")
    assert resp.status_code == 501


def test_login_not_implemented(client):
    """POST /api/auth/login is reserved for Firebase and returns 501."""
    resp = client.post("/api/auth/login")
    assert resp.status_code == 501
