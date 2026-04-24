"""Tests for chat and AI orchestration."""

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_routes
from app.services.chat_service import ChatService


class FakeSnapshot:
    def __init__(self, exists: bool, data: dict | None = None):
        self.exists = exists
        self._data = data or {}

    def to_dict(self):
        return self._data


class FakeDocument:
    def __init__(self, document_id: str):
        self.id = document_id
        self.data = None
        self.collections = {}

    def set(self, data):
        self.data = data

    def update(self, data):
        if self.data is None:
            self.data = {}
        self.data.update(data)

    def get(self):
        return FakeSnapshot(self.data is not None, self.data)

    def to_dict(self):
        return self.data or {}

    def collection(self, collection_name):
        self.collections.setdefault(collection_name, FakeCollection(collection_name))
        return self.collections[collection_name]


class FakeCollection:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.documents = {}
        self.auto_id_counter = 0

    def document(self, document_id: str | None = None):
        if document_id is None:
            self.auto_id_counter += 1
            document_id = f"{self.collection_name}-{self.auto_id_counter}"
        self.documents.setdefault(document_id, FakeDocument(document_id))
        return self.documents[document_id]


class FakeFirestore:
    def __init__(self):
        self.collections = {}

    def collection(self, collection_name):
        self.collections.setdefault(collection_name, FakeCollection(collection_name))
        return self.collections[collection_name]


class FakeAIOrchestrator:
    def __init__(self):
        self.calls = []

    async def process_user_input(self, case_id: str, session_id: str, user_message: str):
        self.calls.append(
            {
                "case_id": case_id,
                "session_id": session_id,
                "user_message": user_message,
            }
        )
        return {
            "message": "What is your expected monthly rent?",
            "follow_up_questions": ["What is your expected monthly rent?"],
            "extracted_facts": [
                {
                    "category": "location",
                    "key": "target_area",
                    "value": "SS15",
                }
            ],
            "generated_tasks": [
                {
                    "title": "Count lunch foot traffic",
                    "description": "Visit the location during lunch.",
                    "priority": "high",
                }
            ],
            "recommendation_update": {
                "summary": "More validation is needed.",
                "confidence_score": 40,
                "action_items": ["Validate rent and lunch traffic."],
            },
        }


class FakeChatService:
    instances = []

    def __init__(self, db_client=None):
        self.db_client = db_client
        self.calls = []
        self.__class__.instances.append(self)

    async def create_session(self, case_id: str):
        self.calls.append(("create_session", case_id))
        return {"id": "session-123", "case_id": case_id}

    async def list_sessions(self, case_id: str):
        self.calls.append(("list_sessions", case_id))
        return [{"id": "session-123", "case_id": case_id}]

    async def process_message(self, case_id: str, session_id: str, content: str):
        self.calls.append(("process_message", case_id, session_id, content))
        return {
            "message": "AI response",
            "assistant_message": {
                "id": "message-2",
                "session_id": session_id,
                "role": "assistant",
                "content": "AI response",
            },
        }

    async def get_session_history(self, case_id: str, session_id: str):
        self.calls.append(("get_session_history", case_id, session_id))
        return [
            {
                "id": "message-1",
                "session_id": session_id,
                "role": "user",
                "content": "Hello",
            }
        ]


def build_chat_test_client(monkeypatch, db):
    FakeChatService.instances = []
    monkeypatch.setattr(chat_routes, "ChatService", FakeChatService)

    app = FastAPI()
    app.include_router(chat_routes.router, prefix="/api/chat")
    app.dependency_overrides[chat_routes.get_db] = lambda: db
    return TestClient(app)


@pytest.mark.asyncio
async def test_create_session_creates_chat_session_under_case():
    db = FakeFirestore()
    case_ref = db.collection("business_cases").document("case-123")
    case_ref.set({"title": "Cafe launch"})

    service = ChatService(db_client=db)
    result = await service.create_session(" case-123 ")

    assert result["id"] == "chat_sessions-1"
    assert result["case_id"] == "case-123"
    assert result["summary"] is None
    assert result["created_at"] == result["updated_at"]

    stored_session = (
        db.collection("business_cases")
        .document("case-123")
        .collection("chat_sessions")
        .document("chat_sessions-1")
        .data
    )
    assert stored_session["case_id"] == "case-123"
    assert stored_session["summary"] is None


@pytest.mark.asyncio
async def test_create_session_raises_404_when_case_is_missing():
    service = ChatService(db_client=FakeFirestore())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_session("missing-case")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_list_sessions_returns_sessions_for_case_newest_first():
    db = FakeFirestore()
    case_ref = db.collection("business_cases").document("case-123")
    case_ref.set({"title": "Cafe launch"})
    case_ref.collection("chat_sessions").document("session-old").set(
        {
            "case_id": "case-123",
            "summary": "Old summary",
            "created_at": 1,
            "updated_at": 1,
        }
    )
    case_ref.collection("chat_sessions").document("session-new").set(
        {
            "case_id": "case-123",
            "summary": "New summary",
            "created_at": 2,
            "updated_at": 2,
        }
    )

    result = await ChatService(db_client=db).list_sessions(" case-123 ")

    assert [session["id"] for session in result] == ["session-new", "session-old"]
    assert result[0]["summary"] == "New summary"


@pytest.mark.asyncio
async def test_process_message_stores_messages_and_structured_outputs():
    db = FakeFirestore()
    case_ref = db.collection("business_cases").document("case-123")
    case_ref.set({"title": "Cafe launch"})
    session_ref = case_ref.collection("chat_sessions").document("session-123")
    session_ref.set(
        {
            "case_id": "case-123",
            "summary": None,
            "created_at": "created",
            "updated_at": "created",
        }
    )
    ai_orchestrator = FakeAIOrchestrator()
    service = ChatService(db_client=db, ai_orchestrator=ai_orchestrator)

    result = await service.process_message(
        " case-123 ",
        " session-123 ",
        " I want to open in SS15. ",
    )

    assert ai_orchestrator.calls == [
        {
            "case_id": "case-123",
            "session_id": "session-123",
            "user_message": "I want to open in SS15.",
        }
    ]
    assert result["message"] == "What is your expected monthly rent?"
    assert result["stored_outputs"]["facts"] == 1
    assert result["stored_outputs"]["tasks"] == 1
    assert result["stored_outputs"]["recommendation_id"] == "recommendations-1"

    messages = session_ref.collection("messages").documents
    assert messages["messages-1"].data["role"] == "user"
    assert messages["messages-1"].data["content"] == "I want to open in SS15."
    assert messages["messages-2"].data["role"] == "assistant"
    assert messages["messages-2"].data["content"] == (
        "What is your expected monthly rent?"
    )
    assert messages["messages-2"].data["structured_output"] is not None

    facts = case_ref.collection("extracted_facts").documents
    assert facts["extracted_facts-1"].data["key"] == "target_area"
    assert facts["extracted_facts-1"].data["value"] == "SS15"

    recommendation_ref = case_ref.collection("recommendations").document(
        "recommendations-1"
    )
    assert recommendation_ref.data["summary"] == "More validation is needed."
    assert recommendation_ref.data["confidence_score"] == 40
    task_ref = recommendation_ref.collection("tasks").document("tasks-1")
    assert task_ref.data["title"] == "Count lunch foot traffic"
    assert task_ref.data["priority"] == "high"
    assert session_ref.data["summary"] == "More validation is needed."


@pytest.mark.asyncio
async def test_get_session_history_returns_messages_in_created_order():
    db = FakeFirestore()
    case_ref = db.collection("business_cases").document("case-123")
    case_ref.set({"title": "Cafe launch"})
    session_ref = case_ref.collection("chat_sessions").document("session-123")
    session_ref.set(
        {
            "case_id": "case-123",
            "summary": None,
            "created_at": 1,
            "updated_at": 1,
        }
    )
    session_ref.collection("messages").document("message-2").set(
        {
            "session_id": "session-123",
            "role": "assistant",
            "content": "Hi",
            "created_at": 2,
        }
    )
    session_ref.collection("messages").document("message-1").set(
        {
            "session_id": "session-123",
            "role": "user",
            "content": "Hello",
            "created_at": 1,
        }
    )

    result = await ChatService(db_client=db).get_session_history(
        " case-123 ",
        " session-123 ",
    )

    assert [message["id"] for message in result] == ["message-1", "message-2"]
    assert result[0]["content"] == "Hello"
    assert result[1]["content"] == "Hi"


def test_create_session_endpoint_calls_chat_service(monkeypatch):
    db = FakeFirestore()
    client = build_chat_test_client(monkeypatch, db)

    response = client.post("/api/chat/case-123/sessions")

    assert response.status_code == 200
    assert response.json() == {"id": "session-123", "case_id": "case-123"}
    assert FakeChatService.instances[0].db_client is db
    assert FakeChatService.instances[0].calls == [("create_session", "case-123")]


def test_list_sessions_endpoint_calls_chat_service(monkeypatch):
    db = FakeFirestore()
    client = build_chat_test_client(monkeypatch, db)

    response = client.get("/api/chat/case-123/sessions")

    assert response.status_code == 200
    assert response.json() == [{"id": "session-123", "case_id": "case-123"}]
    assert FakeChatService.instances[0].db_client is db
    assert FakeChatService.instances[0].calls == [("list_sessions", "case-123")]


def test_send_message_endpoint_calls_chat_service(monkeypatch):
    db = FakeFirestore()
    client = build_chat_test_client(monkeypatch, db)

    response = client.post(
        "/api/chat/case-123/sessions/session-123/messages",
        json={"content": "Hello"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "AI response"
    assert FakeChatService.instances[0].db_client is db
    assert FakeChatService.instances[0].calls == [
        ("process_message", "case-123", "session-123", "Hello")
    ]


def test_get_messages_endpoint_calls_chat_service(monkeypatch):
    db = FakeFirestore()
    client = build_chat_test_client(monkeypatch, db)

    response = client.get("/api/chat/case-123/sessions/session-123/messages")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "message-1",
            "session_id": "session-123",
            "role": "user",
            "content": "Hello",
        }
    ]
    assert FakeChatService.instances[0].db_client is db
    assert FakeChatService.instances[0].calls == [
        ("get_session_history", "case-123", "session-123")
    ]


def test_ai_response_parsing():
    pass
