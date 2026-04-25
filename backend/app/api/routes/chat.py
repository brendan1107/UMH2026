# app/api/routes/chat.py
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.chat import ChatSession, ChatMessage
from app.services.chat_service import ChatService

# ──  AI imports ──
from app.ai.orchestrator import run_agent_turn
from app.ai.schemas import BusinessCase as AICase

router = APIRouter()


@router.post("/{case_id}/sessions")
async def create_session(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    if not case_ref.get().exists:
        raise HTTPException(status_code=404, detail="Case not found")
    service = ChatService(db)
    return await service.create_session(case_id)


@router.get("/{case_id}/sessions")
async def list_sessions(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    sessions_ref = case_ref.collection(ChatSession.SUBCOLLECTION).stream()
    sessions = []
    for doc in sessions_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        sessions.append(data)
    return sessions

# keep create_session, list_sessions, get_messages unchanged 
# only fix this send_message function to run the agent and save AI response as a message in Firestore
# The AI response should also be saved in the case document for context management and future retrieval. 
# The AI output should be formatted into a human-readable string for the chat message content, and the raw AI output data should be included in the message document for frontend rendering.:

@router.post("/{case_id}/sessions/{session_id}/messages")
async def send_message(
    case_id: str,
    session_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)

    # 1. Save user message to Firestore
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=data.get("content", "")
    )
    user_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    user_msg_ref.set(user_msg.to_dict())

    # 2. Load current case state from Firestore
    doc = case_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")
    case_data = doc.to_dict()

    # 3. Build AICase from Firestore data
    ai_case = AICase(
        id=case_id,
        idea=case_data.get("description", case_data.get("title", "")),
        location=case_data.get("target_location", ""),
        budget_myr=float(case_data.get("budget_myr", 30000)),
        phase=case_data.get("ai_phase", "INTAKE"),
        fact_sheet=case_data.get("fact_sheet", {}),
        messages=case_data.get("ai_messages", []),
    )

    # 4. Append user message to AI conversation history
    ai_case.messages.append({
        "role": "user",
        "content": data.get("content", "")
    })

    # 5. Run one agent turn — GLM thinks and responds
    updated_case, ai_output = await run_agent_turn(ai_case)

    # 6. Save updated AI state back to Firestore
    case_ref.update({
        "ai_phase":    updated_case.phase,
        "fact_sheet":  updated_case.fact_sheet,
        "ai_messages": updated_case.messages,
        "updated_at":  datetime.utcnow(),
    })

    # 7. Save AI output as a chat message
    ai_content = _format_output_for_chat(ai_output)
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=ai_content
    )
    ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    ai_dict = ai_msg.to_dict()
    ai_dict["ai_output_type"] = ai_output.type   # so frontend knows what to render
    ai_dict["ai_output_data"] = ai_output.model_dump()
    ai_msg_ref.set(ai_dict)

    ai_dict["id"] = ai_msg_ref.id
    return ai_dict


def _format_output_for_chat(output) -> str:
    """Convert AI output to human-readable string for simple display."""
    if output.type == "tool_call":
        return f"Investigating {output.tool.replace('_', ' ')}..."
    elif output.type == "field_task":
        return f"Mission: {output.title}\n\n{output.instruction}"
    elif output.type == "clarify":
        return output.question
    elif output.type == "verdict":
        return f"VERDICT: {output.decision}\n\n{output.summary}"
    return ""



@router.get("/{case_id}/sessions/{session_id}/messages")
async def get_messages(
    case_id: str,
    session_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    service = ChatService(db)
    return await service.get_session_history(case_id, session_id)