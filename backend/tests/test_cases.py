"""Tests for business case CRUD endpoints."""

from datetime import datetime

import pytest

from app.models.business_case import BusinessCase

CASE_PAYLOAD = {
    "title": "My Cafe",
    "description": "Test description",
    "stage": "new",
    "business_type": "cafe",
    "target_location": "Petaling Jaya",
}


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_case(client):
    resp = client.post("/api/cases/", json=CASE_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "My Cafe"
    assert "id" in data
    assert data["status"] == "active"
    assert data["businessType"] == "cafe"


def test_create_case_minimal(client):
    """Only title is required; optional fields should default gracefully."""
    resp = client.post("/api/cases/", json={"title": "Minimal Case"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Minimal Case"


def test_create_case_missing_title(client):
    """Omitting the required title field should return 422."""
    resp = client.post("/api/cases/", json={"description": "no title"})
    assert resp.status_code == 422


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_cases_empty(client):
    resp = client.get("/api/cases/")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_cases(client):
    client.post("/api/cases/", json=CASE_PAYLOAD)
    client.post("/api/cases/", json={**CASE_PAYLOAD, "title": "Second Cafe"})
    resp = client.get("/api/cases/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_cases_only_own(client, mock_db):
    """Cases owned by other users should not appear in the list."""
    # Pre-seed a case owned by a different user directly in the mock store
    doc_ref = mock_db.collection(BusinessCase.COLLECTION).document("foreign-case")
    doc_ref.set({
        "user_id": "other-user-999",
        "title": "Not Mine",
        "stage": "new",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "budget_myr": 30000,
        "ai_phase": "INTAKE",
        "fact_sheet": {},
        "ai_messages": [],
    })
    client.post("/api/cases/", json=CASE_PAYLOAD)
    resp = client.get("/api/cases/")
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert "foreign-case" not in ids


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_case(client, case_id):
    resp = client.get(f"/api/cases/{case_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == case_id


def test_get_case_not_found(client):
    resp = client.get("/api/cases/nonexistent-id")
    assert resp.status_code == 404


def test_get_case_wrong_user(client, mock_db):
    """A case owned by a different user should return 403."""
    doc_ref = mock_db.collection(BusinessCase.COLLECTION).document("other-case")
    doc_ref.set({
        "user_id": "other-user-999",
        "title": "Other User's Case",
        "stage": "new",
        "status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "budget_myr": 30000,
        "ai_phase": "INTAKE",
        "fact_sheet": {},
        "ai_messages": [],
    })
    resp = client.get("/api/cases/other-case")
    assert resp.status_code == 403


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_case(client, case_id):
    resp = client.put(f"/api/cases/{case_id}", json={"description": "Updated!"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated!"


def test_update_case_no_fields(client, case_id):
    """PUT with an empty body should return 422."""
    resp = client.put(f"/api/cases/{case_id}", json={})
    assert resp.status_code == 422


def test_update_case_not_found(client):
    resp = client.put("/api/cases/nonexistent", json={"title": "X"})
    assert resp.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_case(client, case_id):
    resp = client.delete(f"/api/cases/{case_id}")
    assert resp.status_code == 200
    # Confirm the case is gone
    assert client.get(f"/api/cases/{case_id}").status_code == 404


def test_delete_case_not_found(client):
    resp = client.delete("/api/cases/nonexistent")
    assert resp.status_code == 404


# ── Workflow endpoints ────────────────────────────────────────────────────────

def test_archive_case(client, case_id):
    resp = client.post(f"/api/cases/{case_id}/archive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_reopen_case(client, case_id):
    client.post(f"/api/cases/{case_id}/archive")
    resp = client.post(f"/api/cases/{case_id}/reopen")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_update_status_valid(client, case_id):
    resp = client.put(f"/api/cases/{case_id}/status", json={"status": "archived"})
    assert resp.status_code == 200


def test_update_status_invalid(client, case_id):
    resp = client.put(f"/api/cases/{case_id}/status", json={"status": "bad_value"})
    assert resp.status_code == 422


def test_update_title(client, case_id):
    resp = client.put(f"/api/cases/{case_id}/title", json={"title": "New Title"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_save_insight(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/insight",
        json={"verdict": "GO", "summary": "Looks good"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_save_checkpoint(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/checkpoint",
        json={"phase": "EVIDENCE", "step": 2},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_end_session_archive(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/end_session",
        json={"decision": "archive"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_end_session_insight_generated(client, case_id):
    resp = client.post(
        f"/api/cases/{case_id}/end_session",
        json={"decision": "complete", "insight": {"summary": "ok"}},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
