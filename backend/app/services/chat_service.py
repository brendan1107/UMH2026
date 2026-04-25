"""
Chat Service

Orchestrates the message flow between user, AI, and external services.
This is the main entry point for the iterative investigation workflow.
"""
import json
from datetime import datetime
from google.cloud import firestore
from app.db.session import get_db
from app.models.business_case import BusinessCase
from app.models.chat import ChatSession, ChatMessage
from app.ai.schemas import BusinessCase as AICase
from app.ai.orchestrator import run_agent_turn

# What is chat_service.py for?
# The chat_service.py file defines a service class, ChatService, that contains the core business logic for managing chat sessions and processing messages between users and the AI. This includes functions for creating new chat sessions for business cases, processing user messages through the full AI orchestration pipeline (storing messages, building context, calling the GLM, parsing outputs, and returning responses), and retrieving message history for a session. By centralizing this logic in a service class, we can keep our API route handlers clean and focused on handling HTTP requests and responses, while the ChatService takes care of the underlying mechanics of managing chat interactions. This allows us to maintain a clear structure in our codebase and makes it easier to manage and update our chat-related logic as needed.

class ChatService:

    def __init__(self, db: firestore.Client):
        self.db = db

    async def create_session(self, case_id: str) -> dict:
        """Initialize a new chat session for a case."""
        case_ref = self.db.collection(BusinessCase.COLLECTION).document(case_id)
        session = ChatSession(case_id=case_id)
        session_dict = session.to_dict()
        doc_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document()
        doc_ref.set(session_dict)
        session_dict["id"] = doc_ref.id
        return session_dict

    async def process_message(
        self, case_id: str, session_id: str, content: str
    ) -> dict:
        """
        Process a user message through the full AI pipeline.
        1. Store user message
        2. Load case state from Firestore
        3. Call AI orchestrator
        4. Store AI response
        5. Save updated case state back to Firestore
        6. Return AI response
        """
        case_ref = self.db.collection(BusinessCase.COLLECTION).document(case_id)
        session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)

        # 1. Store user message
        user_msg = ChatMessage(session_id=session_id, role="user", content=content)
        user_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
        user_msg_ref.set(user_msg.to_dict())

        # 2. Load case state from Firestore
        case_doc = case_ref.get().to_dict()

        # Build AICase from Firestore data
        ai_case = AICase(
            id=case_id,
            idea=case_doc.get("description", case_doc.get("title", "")),
            location=case_doc.get("target_location", ""),
            budget_myr=float(case_doc.get("budget_myr")) if case_doc.get("budget_myr") else None,
            phase=case_doc.get("ai_phase", "INTAKE"),
            fact_sheet=case_doc.get("fact_sheet", {}),
            messages=case_doc.get("ai_messages", []),
        )

        # Add the new user message to AI context
        ai_case.messages.append({"role": "user", "content": content})

        # 3. Run AI orchestrator
        ai_case, output = await run_agent_turn(ai_case)

        # 4. Store AI response as chat message
        ai_content = output.model_dump_json()
        ai_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_content,
        )
        ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
        ai_msg_ref.set(ai_msg.to_dict())

        # 5. Save updated case state back to Firestore
        case_ref.update({
            "ai_phase": ai_case.phase,
            "fact_sheet": ai_case.fact_sheet,
            "ai_messages": ai_case.messages,
            "updated_at": datetime.utcnow(),
        })

        # 6. Return AI output
        ai_dict = ai_msg.to_dict()
        ai_dict["id"] = ai_msg_ref.id
        ai_dict["ai_output"] = output.model_dump()
        return ai_dict

    async def get_session_history(self, case_id: str, session_id: str) -> list:
        """Retrieve full message history for a session."""
        case_ref = self.db.collection(BusinessCase.COLLECTION).document(case_id)
        session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)
        messages_ref = (
            session_ref.collection(ChatMessage.SUBCOLLECTION)
            .order_by("created_at")
            .stream()
        )
        messages = []
        for doc in messages_ref:
            data = doc.to_dict()
            data["id"] = doc.id
            messages.append(data)
        return messages