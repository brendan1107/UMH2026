"""Tests for chat session and message endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.business_case import BusinessCase


# ── Helper: mock AI orchestrator ─────────────────────────────────────────────

def _make_clarify_turn():
    """Return an async side-effect that emits a ClarifyOutput without calling GLM."""
    from app.ai.schemas import ClarifyOutput

    async def _run(case, _depth=0):
        output = ClarifyOutput(
            type="clarify",
            question="What is your target budget?",
            options=["Under RM30k", "RM30k–50k", "Over RM50k"],
        )
        case.messages.append({"role": "assistant", "content": output.model_dump_json()})
        return case, output

    return _run


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def session_id(client, case_id):
    """Pre-create a chat session and return its ID."""
    resp = client.post(f"/api/chat/{case_id}/sessions")
    assert resp.status_code == 200
    return resp.json()["id"]


# ── Session CRUD ──────────────────────────────────────────────────────────────

def test_create_session(client, case_id):
    resp = client.post(f"/api/chat/{case_id}/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["case_id"] == case_id


def test_create_session_case_not_found(client):
    resp = client.post("/api/chat/nonexistent-case/sessions")
    assert resp.status_code == 404


def test_list_sessions_empty(client, case_id):
    resp = client.get(f"/api/chat/{case_id}/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions(client, case_id, session_id):
    resp = client.get(f"/api/chat/{case_id}/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert any(s["id"] == session_id for s in sessions)


# ── Messaging ─────────────────────────────────────────────────────────────────

def test_send_message(client, case_id, session_id):
    with patch(
        "app.api.routes.chat.run_agent_turn",
        new=AsyncMock(side_effect=_make_clarify_turn()),
    ):
        resp = client.post(
            f"/api/chat/{case_id}/sessions/{session_id}/messages",
            json={"content": "I want to open a cafe in KL."},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "assistant"
    assert "aiOutputType" in data
    assert data["aiOutputType"] == "clarify"


def test_get_messages(client, case_id, session_id):
    with patch(
        "app.api.routes.chat.run_agent_turn",
        new=AsyncMock(side_effect=_make_clarify_turn()),
    ):
        client.post(
            f"/api/chat/{case_id}/sessions/{session_id}/messages",
            json={"content": "Hello"},
        )
    resp = client.get(f"/api/chat/{case_id}/sessions/{session_id}/messages")
    assert resp.status_code == 200
    messages = resp.json()
    # Expect at least one user message and one assistant message
    assert len(messages) >= 2
    roles = {m["role"] for m in messages}
    assert "user" in roles
    assert "assistant" in roles


def test_send_message_wrong_user(client, mock_db, case_id, session_id):
    """A case owned by a different user should return 403."""
    case_ref = mock_db.collection(BusinessCase.COLLECTION).document(case_id)
    case_ref.update({"user_id": "other-user-999"})

    with patch(
        "app.api.routes.chat.run_agent_turn",
        new=AsyncMock(side_effect=_make_clarify_turn()),
    ):
        resp = client.post(
            f"/api/chat/{case_id}/sessions/{session_id}/messages",
            json={"content": "Hello"},
        )
    assert resp.status_code == 403


def test_send_message_case_not_found(client, case_id, session_id):
    resp = client.post(
        "/api/chat/nonexistent-case/sessions/some-session/messages",
        json={"content": "Hello"},
    )
    assert resp.status_code == 404
