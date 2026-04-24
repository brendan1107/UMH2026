"""
Chat Service

Orchestrates the message flow between user, AI, and external services.
This is the main entry point for the iterative investigation workflow.
"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from google.cloud.firestore_v1 import Query

from app.db.database import db as default_db
from app.models.business_case import BusinessCase
from app.models.chat import ChatMessage, ChatSession
from app.models.extracted_fact import ExtractedFact
from app.models.investigation_task import InvestigationTask
from app.models.recommendation import Recommendation
from app.services.mvp_store import store

_DB_CLIENT_UNSET = object()

# What is chat_service.py for?
# The chat_service.py file defines a service class, ChatService, that contains the core business logic for managing chat sessions and processing messages between users and the AI. This includes functions for creating new chat sessions for business cases, processing user messages through the full AI orchestration pipeline (storing messages, building context, calling the GLM, parsing outputs, and returning responses), and retrieving message history for a session. By centralizing this logic in a service class, we can keep our API route handlers clean and focused on handling HTTP requests and responses, while the ChatService takes care of the underlying mechanics of managing chat interactions. This allows us to maintain a clear structure in our codebase and makes it easier to manage and update our chat-related logic as needed.

class ChatService:
    """Service for chat session and message operations."""

    _fallback_sessions: dict[tuple[str, str], dict[str, dict]] = {}
    _fallback_messages: dict[tuple[str, str, str], list[dict]] = {}

    def __init__(
        self,
        db_client: Any = _DB_CLIENT_UNSET,
        ai_orchestrator: Any | None = None,
    ):
        self.db = default_db if db_client is _DB_CLIENT_UNSET else db_client
        self.ai_orchestrator = ai_orchestrator

    async def create_session(self, case_id: str, user_id: str | None = None):
        """Initialize a new chat session for a case."""
        case_id = (case_id or "").strip()
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case ID is required",
            )
        if self.db is None and user_id:
            return self._fallback_create_session(user_id, case_id)
        self._require_firestore()

        case_ref = self._get_existing_case_ref(case_id, user_id=user_id)
        session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document()
        now = datetime.now(timezone.utc)
        session = ChatSession(
            id=session_ref.id,
            case_id=case_id,
            summary=None,
            created_at=now,
            updated_at=now,
        )

        try:
            session_ref.set(session.to_dict())
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create chat session: {exc}",
            )

        return self._serialize_session(session)

    async def process_message(
        self,
        case_id: str,
        session_id: str,
        content: str,
        user_id: str | None = None,
    ):
        """
        Process a user message through the full AI pipeline.

        Steps:
        1. Store user message
        2. Load context (facts, summary, place data, uploads)
        3. Call AI orchestrator
        4. Parse and store structured outputs
        5. Update recommendation if applicable
        6. Return AI response
        """
        case_id = (case_id or "").strip()
        session_id = (session_id or "").strip()
        content = (content or "").strip()
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case ID is required",
            )
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID is required",
            )
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message content is required",
            )
        if self.db is None and user_id:
            return await self._fallback_process_message(
                user_id,
                case_id,
                session_id,
                content,
            )
        self._require_firestore()

        case_ref, session_ref = self._get_existing_session_ref(
            case_id,
            session_id,
            user_id=user_id,
        )

        user_message = self._create_message(
            session_ref=session_ref,
            session_id=session_id,
            role="user",
            content=content,
        )

        ai_response = await self._process_with_ai(case_id, session_id, content)
        ai_message_content = self._extract_ai_message(ai_response)
        stored_outputs = self._persist_structured_outputs(case_ref, case_id, ai_response)

        assistant_message = self._create_message(
            session_ref=session_ref,
            session_id=session_id,
            role="assistant",
            content=ai_message_content,
            structured_output=ai_response,
        )

        self._merge_document(
            session_ref,
            {
                "updated_at": datetime.now(timezone.utc),
                "summary": self._extract_session_summary(ai_response),
            },
            remove_none=True,
        )

        return {
            "message": ai_message_content,
            "follow_up_questions": ai_response.get("follow_up_questions"),
            "extracted_facts": ai_response.get("extracted_facts"),
            "generated_tasks": ai_response.get("generated_tasks"),
            "recommendation_update": ai_response.get("recommendation_update"),
            "user_message": self._serialize_message(user_message),
            "assistant_message": self._serialize_message(assistant_message),
            "stored_outputs": stored_outputs,
        }

    async def list_sessions(self, case_id: str, user_id: str | None = None):
        """List chat sessions for a business case."""
        case_id = (case_id or "").strip()
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case ID is required",
            )
        if self.db is None and user_id:
            self._require_fallback_case(user_id, case_id)
            sessions = self._fallback_sessions.get((user_id, case_id), {})
            return sorted(
                sessions.values(),
                key=lambda item: item["updated_at"],
                reverse=True,
            )
        self._require_firestore()

        case_ref = self._get_existing_case_ref(case_id, user_id=user_id)
        session_docs = self._documents(
            case_ref.collection(ChatSession.SUBCOLLECTION),
            order_field="updated_at",
            descending=True,
        )
        return [
            self._serialize_session(
                ChatSession.from_dict(doc.id, self._document_data(doc))
            )
            for doc in session_docs
        ]

    async def get_session_history(
        self,
        case_id: str,
        session_id: str,
        user_id: str | None = None,
    ):
        """Retrieve message history with pagination."""
        case_id = (case_id or "").strip()
        session_id = (session_id or "").strip()
        if not case_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Case ID is required",
            )
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session ID is required",
            )
        if self.db is None and user_id:
            self._require_fallback_session(user_id, case_id, session_id)
            return list(
                self._fallback_messages.get((user_id, case_id, session_id), [])
            )
        self._require_firestore()

        _, session_ref = self._get_existing_session_ref(
            case_id,
            session_id,
            user_id=user_id,
        )
        message_docs = self._documents(
            session_ref.collection(ChatMessage.SUBCOLLECTION),
            order_field="created_at",
        )
        return [
            self._serialize_message(
                ChatMessage.from_dict(doc.id, self._document_data(doc))
            )
            for doc in message_docs
        ]

    def _require_firestore(self):
        if self.db is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firestore is not configured",
            )

    def _get_existing_case_ref(self, case_id: str, user_id: str | None = None):
        refs = []
        if user_id:
            refs.append(
                self.db.collection("users")
                .document(user_id)
                .collection("cases")
                .document(case_id)
            )
        refs.append(self.db.collection(BusinessCase.COLLECTION).document(case_id))

        try:
            for case_ref in refs:
                if case_ref.get().exists:
                    return case_ref
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business case not found",
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to load business case: {exc}",
            )

    @staticmethod
    def _serialize_session(session: ChatSession) -> dict:
        return {
            "id": session.id,
            "case_id": session.case_id,
            "summary": session.summary,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    def _get_existing_session_ref(
        self,
        case_id: str,
        session_id: str,
        user_id: str | None = None,
    ):
        case_ref = self._get_existing_case_ref(case_id, user_id=user_id)
        try:
            session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(
                session_id
            )
            if not session_ref.get().exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat session not found",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to load chat session: {exc}",
            )

        return case_ref, session_ref

    def _require_fallback_case(self, user_id: str, case_id: str) -> dict:
        case = store.get_case(user_id, case_id)
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business case not found",
            )
        return case

    def _fallback_create_session(self, user_id: str, case_id: str) -> dict:
        self._require_fallback_case(user_id, case_id)
        now = datetime.now(timezone.utc)
        session_id = f"chat_sessions-{uuid4().hex}"
        session = {
            "id": session_id,
            "case_id": case_id,
            "summary": None,
            "created_at": now,
            "updated_at": now,
        }
        self._fallback_sessions.setdefault((user_id, case_id), {})[session_id] = session
        self._fallback_messages[(user_id, case_id, session_id)] = []
        return dict(session)

    def _require_fallback_session(
        self,
        user_id: str,
        case_id: str,
        session_id: str,
    ) -> dict:
        self._require_fallback_case(user_id, case_id)
        session = self._fallback_sessions.get((user_id, case_id), {}).get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )
        return session

    async def _fallback_process_message(
        self,
        user_id: str,
        case_id: str,
        session_id: str,
        content: str,
    ) -> dict:
        session = self._require_fallback_session(user_id, case_id, session_id)
        messages = self._fallback_messages.setdefault(
            (user_id, case_id, session_id),
            [],
        )

        user_message = self._fallback_message(session_id, "user", content)
        messages.append(user_message)

        ai_response = await self._process_with_ai(case_id, session_id, content)
        ai_message_content = self._extract_ai_message(ai_response)
        assistant_message = self._fallback_message(
            session_id,
            "assistant",
            ai_message_content,
            structured_output=ai_response,
        )
        messages.append(assistant_message)

        session["updated_at"] = datetime.now(timezone.utc)
        summary = self._extract_session_summary(ai_response)
        if summary:
            session["summary"] = summary

        return {
            "message": ai_message_content,
            "follow_up_questions": ai_response.get("follow_up_questions"),
            "extracted_facts": ai_response.get("extracted_facts"),
            "generated_tasks": ai_response.get("generated_tasks"),
            "recommendation_update": ai_response.get("recommendation_update"),
            "user_message": user_message,
            "assistant_message": assistant_message,
            "stored_outputs": {
                "facts": 0,
                "tasks": 0,
                "recommendation_id": None,
            },
        }

    def _fallback_message(
        self,
        session_id: str,
        role: str,
        content: str,
        structured_output: dict | None = None,
    ) -> dict:
        return {
            "id": f"messages-{uuid4().hex}",
            "session_id": session_id,
            "role": role,
            "content": content,
            "structured_output": (
                self._json_dumps(structured_output)
                if structured_output is not None
                else None
            ),
            "created_at": datetime.now(timezone.utc),
        }

    @staticmethod
    def _documents(query: Any, order_field: str | None = None, descending: bool = False):
        try:
            if order_field:
                direction = Query.DESCENDING if descending else Query.ASCENDING
                query = query.order_by(order_field, direction=direction)
            return list(query.stream())
        except AttributeError:
            documents = [
                doc
                for doc in getattr(query, "documents", {}).values()
                if doc.get().exists
            ]
            if order_field:
                documents.sort(
                    key=lambda doc: ChatService._document_data(doc).get(order_field),
                    reverse=descending,
                )
            return documents

    @staticmethod
    def _document_data(doc: Any) -> dict:
        if hasattr(doc, "to_dict"):
            return doc.to_dict() or {}
        snapshot = doc.get()
        if hasattr(snapshot, "to_dict"):
            return snapshot.to_dict() or {}
        return getattr(doc, "data", None) or {}

    def _create_message(
        self,
        session_ref: Any,
        session_id: str,
        role: str,
        content: str,
        structured_output: dict | None = None,
    ) -> ChatMessage:
        message_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
        message = ChatMessage(
            id=message_ref.id,
            session_id=session_id,
            role=role,
            content=content,
            structured_output=self._json_dumps(structured_output)
            if structured_output is not None
            else None,
            created_at=datetime.now(timezone.utc),
        )
        try:
            message_ref.set(message.to_dict())
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store {role} message: {exc}",
            )
        return message

    async def _process_with_ai(
        self,
        case_id: str,
        session_id: str,
        content: str,
    ) -> dict:
        if self.ai_orchestrator is None:
            return {
                "message": (
                    "I recorded your input. The AI orchestration pipeline is not "
                    "configured yet, so no new analysis was generated."
                ),
                "follow_up_questions": None,
                "extracted_facts": [],
                "generated_tasks": [],
                "recommendation_update": None,
            }

        try:
            raw_response = await self.ai_orchestrator.process_user_input(
                case_id=case_id,
                session_id=session_id,
                user_message=content,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI processing failed: {exc}",
            )

        return self._normalize_ai_response(raw_response)

    def _normalize_ai_response(self, raw_response: Any) -> dict:
        if raw_response is None:
            return {
                "message": "I could not generate a response for this message.",
                "follow_up_questions": None,
                "extracted_facts": [],
                "generated_tasks": [],
                "recommendation_update": None,
            }
        if isinstance(raw_response, str):
            return {
                "message": raw_response,
                "follow_up_questions": None,
                "extracted_facts": [],
                "generated_tasks": [],
                "recommendation_update": None,
            }
        if isinstance(raw_response, tuple) and raw_response:
            raw_response = raw_response[-1]
        if hasattr(raw_response, "model_dump"):
            raw_response = raw_response.model_dump()
        elif hasattr(raw_response, "dict"):
            raw_response = raw_response.dict()
        if not isinstance(raw_response, dict):
            return {
                "message": str(raw_response),
                "follow_up_questions": None,
                "extracted_facts": [],
                "generated_tasks": [],
                "recommendation_update": None,
            }

        normalized = dict(raw_response)
        normalized.setdefault("follow_up_questions", None)
        normalized.setdefault("extracted_facts", [])
        normalized.setdefault("generated_tasks", [])
        normalized.setdefault("recommendation_update", None)
        normalized["message"] = self._extract_ai_message(normalized)
        return normalized

    @staticmethod
    def _extract_ai_message(ai_response: dict) -> str:
        if ai_response.get("message"):
            return str(ai_response["message"])
        response_type = ai_response.get("type")
        if response_type == "clarify" and ai_response.get("question"):
            return str(ai_response["question"])
        if response_type == "field_task":
            return str(ai_response.get("instruction") or ai_response.get("title"))
        if response_type == "verdict" and ai_response.get("summary"):
            return str(ai_response["summary"])
        return json.dumps(ai_response, default=str)

    @staticmethod
    def _extract_session_summary(ai_response: dict) -> str | None:
        if ai_response.get("conversation_summary"):
            return str(ai_response["conversation_summary"])
        if ai_response.get("summary"):
            return str(ai_response["summary"])
        recommendation = (
            ai_response.get("recommendation_update")
            or ai_response.get("recommendation")
            or {}
        )
        if isinstance(recommendation, dict) and recommendation.get("summary"):
            return str(recommendation["summary"])
        return None

    def _persist_structured_outputs(
        self,
        case_ref: Any,
        case_id: str,
        ai_response: dict,
    ) -> dict:
        facts = ai_response.get("extracted_facts") or []
        tasks = self._extract_tasks_from_response(ai_response)
        recommendation_update = (
            ai_response.get("recommendation_update")
            or ai_response.get("recommendation")
        )

        fact_count = self._persist_facts(case_ref, case_id, facts)
        recommendation_id = None
        if recommendation_update:
            recommendation_id = self._persist_recommendation(
                case_ref,
                case_id,
                recommendation_update,
            )
        if tasks and recommendation_id is None:
            recommendation_id = self._persist_recommendation(
                case_ref,
                case_id,
                {
                    "summary": "Generated investigation tasks",
                    "is_provisional": True,
                },
            )
        task_count = self._persist_tasks(case_ref, recommendation_id, tasks)

        return {
            "facts": fact_count,
            "tasks": task_count,
            "recommendation_id": recommendation_id,
        }

    def _persist_facts(self, case_ref: Any, case_id: str, facts: list) -> int:
        count = 0
        for fact in facts:
            if hasattr(fact, "model_dump"):
                fact = fact.model_dump()
            if not isinstance(fact, dict):
                continue
            fact_ref = case_ref.collection(ExtractedFact.SUBCOLLECTION).document()
            extracted_fact = ExtractedFact(
                id=fact_ref.id,
                case_id=case_id,
                category=fact.get("category"),
                key=str(fact.get("key") or fact.get("name") or ""),
                value=str(fact.get("value") or ""),
                confidence=fact.get("confidence") or "ai_inferred",
                source=fact.get("source") or "ai_response",
                created_at=datetime.now(timezone.utc),
            )
            fact_ref.set(extracted_fact.to_dict())
            count += 1
        return count

    def _persist_recommendation(
        self,
        case_ref: Any,
        case_id: str,
        recommendation_update: dict,
    ) -> str:
        if hasattr(recommendation_update, "model_dump"):
            recommendation_update = recommendation_update.model_dump()
        recommendation_update = recommendation_update or {}
        recommendation_ref = case_ref.collection(Recommendation.SUBCOLLECTION).document()
        recommendation = Recommendation(
            id=recommendation_ref.id,
            case_id=case_id,
            verdict=recommendation_update.get("verdict")
            or recommendation_update.get("decision"),
            confidence_score=self._normalize_confidence_score(
                recommendation_update.get("confidence_score")
                or recommendation_update.get("confidence")
            ),
            summary=recommendation_update.get("summary"),
            strengths=recommendation_update.get("strengths"),
            weaknesses=recommendation_update.get("weaknesses"),
            action_items=recommendation_update.get("action_items")
            or recommendation_update.get("next_steps"),
            full_report=recommendation_update.get("full_report"),
            is_provisional=recommendation_update.get("is_provisional", True),
            version=recommendation_update.get("version", 1),
            created_at=datetime.now(timezone.utc),
        )
        recommendation_ref.set(recommendation.to_dict())
        return recommendation_ref.id

    def _persist_tasks(
        self,
        case_ref: Any,
        recommendation_id: str | None,
        tasks: list,
    ) -> int:
        if not recommendation_id:
            return 0

        recommendation_ref = case_ref.collection(Recommendation.SUBCOLLECTION).document(
            recommendation_id
        )
        count = 0
        for task in tasks:
            if hasattr(task, "model_dump"):
                task = task.model_dump()
            if not isinstance(task, dict):
                continue
            task_ref = recommendation_ref.collection(
                InvestigationTask.SUBCOLLECTION
            ).document()
            investigation_task = InvestigationTask(
                id=task_ref.id,
                recommendation_id=recommendation_id,
                title=str(task.get("title") or "Investigation task"),
                description=task.get("description") or task.get("instruction"),
                location=task.get("location"),
                priority=task.get("priority") or "medium",
                status=task.get("status") or "pending",
                due_date=task.get("due_date"),
                created_at=datetime.now(timezone.utc),
            )
            task_ref.set(investigation_task.to_dict())
            count += 1
        return count

    @staticmethod
    def _extract_tasks_from_response(ai_response: dict) -> list:
        tasks = ai_response.get("generated_tasks") or []
        if ai_response.get("type") == "field_task":
            tasks = [
                {
                    "title": ai_response.get("title"),
                    "description": ai_response.get("instruction"),
                }
            ]
        return tasks

    @staticmethod
    def _normalize_confidence_score(value: Any) -> int | None:
        if value is None:
            return None
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        if 0 <= score <= 1:
            score *= 100
        return max(0, min(100, int(round(score))))

    def _merge_document(
        self,
        doc_ref: Any,
        data: dict,
        remove_none: bool = False,
    ):
        if remove_none:
            data = {key: value for key, value in data.items() if value is not None}
        if not data:
            return
        try:
            doc_ref.update(data)
            return
        except AttributeError:
            pass

        existing = {}
        try:
            snapshot = doc_ref.get()
            if snapshot.exists:
                existing = snapshot.to_dict()
        except Exception:
            existing = {}
        existing.update(data)
        doc_ref.set(existing)

    @staticmethod
    def _serialize_message(message: ChatMessage) -> dict:
        return {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "structured_output": message.structured_output,
            "created_at": message.created_at,
        }

    @staticmethod
    def _json_dumps(value: Any) -> str:
        return json.dumps(value, default=str)
