"""
Chat Sessions Routes

Handles chat sessions and messages for business cases.
Messages are stored in Firestore subcollections:
  business_cases/{case_id}/chat_sessions/{session_id}
  business_cases/{case_id}/chat_sessions/{session_id}/messages/{msg_id}
"""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.chat import ChatSession, ChatMessage
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()


@router.post("/{case_id}/sessions")
async def create_session(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Create a new chat session for a case."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    if not case_ref.get().exists:
        raise HTTPException(status_code=404, detail="Case not found")

    session = ChatSession(case_id=case_id)
    session_dict = session.to_dict()

    doc_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document()
    doc_ref.set(session_dict)

    session_dict["id"] = doc_ref.id
    return snake_dict_to_camel(session_dict)


@router.get("/{case_id}/sessions")
async def list_sessions(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """List all chat sessions for a case."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    sessions_ref = case_ref.collection(ChatSession.SUBCOLLECTION).stream()

    sessions = []
    for doc in sessions_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        sessions.append(snake_dict_to_camel(data))

    return sessions


@router.post("/{case_id}/sessions/{session_id}/messages")
async def send_message(
    case_id: str,
    session_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Send a message in a chat session. Stores user message and AI response."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)

    # Store user message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=data.get("content", "")
    )
    user_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    user_msg_ref.set(user_msg.to_dict())

    # Store AI response (placeholder for basic CRUD integration)
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=f"Database-stored response to: {user_msg.content}"
    )
    ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()

    ai_dict = ai_msg.to_dict()
    ai_msg_ref.set(ai_dict)

    ai_dict["id"] = ai_msg_ref.id
    return snake_dict_to_camel(ai_dict)


@router.get("/{case_id}/sessions/{session_id}/messages")
async def get_messages(
    case_id: str,
    session_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get all messages in a chat session."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)
    messages_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).order_by("created_at").stream()

    messages = []
    for doc in messages_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        messages.append(snake_dict_to_camel(data))

    return messages
