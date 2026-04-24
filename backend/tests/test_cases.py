"""Tests for business case endpoints and local fallback workflows."""

from fastapi import Request
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_routes
from app.api.routes import reports as report_routes
from app.dependencies import get_current_user
from app.main import app
from app.services.mvp_store import store


async def _demo_user(request: Request) -> dict:
    return {"uid": request.headers.get("X-Demo-User-Id", "test-user")}


def _client() -> TestClient:
    app.dependency_overrides[get_current_user] = _demo_user
    app.dependency_overrides[chat_routes.get_db] = lambda: None
    app.dependency_overrides[report_routes.get_db] = lambda: None
    store.firestore_disabled = True
    return TestClient(app)


def _headers(uid: str = "test-user") -> dict:
    return {"X-Demo-User-Id": uid}


def test_create_case():
    client = _client()
    response = client.post(
        "/api/cases",
        headers=_headers("case-create-user"),
        json={"title": "New cafe", "description": "Breakfast shop"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"]
    assert data["title"] == "New cafe"
    assert data["status"] == "active"


def test_get_case():
    client = _client()
    headers = _headers("case-get-user")
    created = client.post(
        "/api/cases",
        headers=headers,
        json={"title": "Dessert kiosk"},
    ).json()["data"]

    response = client.get(f"/api/cases/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["id"] == created["id"]


def test_frontend_can_use_case_chat_and_report_endpoints_without_firebase():
    client = _client()
    headers = _headers("frontend-flow-user")

    case_response = client.post(
        "/api/cases",
        headers=headers,
        json={
            "title": "KL ramen stall",
            "description": "Evaluate whether a kiosk is viable.",
            "businessStage": "idea",
        },
    )
    assert case_response.status_code == 201
    case_id = case_response.json()["data"]["id"]

    session_response = client.post(f"/api/chat/{case_id}/sessions", headers=headers)
    assert session_response.status_code == 200
    session_id = session_response.json()["id"]

    message_response = client.post(
        f"/api/chat/{case_id}/sessions/{session_id}/messages",
        headers=headers,
        json={"content": "What should I validate first?"},
    )
    assert message_response.status_code == 200
    assert message_response.json()["assistant_message"]["content"]

    report_response = client.post(
        f"/api/reports/{case_id}/report/generate",
        headers=headers,
    )
    assert report_response.status_code == 200
    assert report_response.json()["recommendation"]["summary"]

    pdf_response = client.get(f"/api/reports/{case_id}/report/pdf", headers=headers)
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")
