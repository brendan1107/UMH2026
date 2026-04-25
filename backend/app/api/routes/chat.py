# app/api/routes/chat.py
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.chat import ChatSession, ChatMessage
from app.utils.helpers import snake_dict_to_camel
from app.services.chat_service import ChatService
from app.ai.orchestrator import run_agent_turn
from app.ai.schemas import BusinessCase as AICase

router = APIRouter()
TASKS_SUBCOLLECTION = "tasks"


def _build_ai_case(case_id: str, case_data: dict) -> AICase:
    return AICase(
        id=case_id,
        idea=case_data.get("description") or case_data.get("title") or "",
        location=case_data.get("target_location") or "",
        budget_myr=float(case_data.get("budget_myr") or 30000),
        phase=case_data.get("ai_phase") or "INTAKE",
        fact_sheet=case_data.get("fact_sheet") or {},
        messages=case_data.get("ai_messages") or [],
    )


def _create_task_from_field_task(case_ref, case_id: str, output, calendar_event_id: str = None) -> dict:
    now = datetime.utcnow()
    task_type_by_evidence = {
        "count": "provide_text_input",
        "photo": "upload_image",
        "rating": "provide_text_input",
        "text": "provide_text_input",
    }
    action_label_by_evidence = {
        "count": "Submit count",
        "photo": "Upload evidence",
        "rating": "Submit rating",
        "text": "Submit finding",
    }
    task_dict = {
        "case_id": case_id,
        "title": output.title,
        "description": output.instruction,
        "type": task_type_by_evidence.get(output.evidence_type, "provide_text_input"),
        "status": "pending",
        "action_label": action_label_by_evidence.get(output.evidence_type, "Submit evidence"),
        "data": {
            "description": output.instruction,
            "evidence_type": output.evidence_type,
        },
        "source": "ai",
        "calendar_event_id": calendar_event_id,
        "created_at": now,
        "updated_at": now,
    }

    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document()
    task_ref.set(task_dict)
    task_dict["id"] = task_ref.id
    return snake_dict_to_camel(task_dict)


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


@router.post("/{case_id}/sessions")
async def create_session(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
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
    case_doc = case_ref.get()
    if not case_doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")

    case_data = case_doc.to_dict()
    if case_data.get("user_id") != user["uid"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)

    # 1. Extract content and image URL from the incoming data! (THIS WAS MISSING)
    text_content = data.get("content", "")
    image_url = data.get("image_url")

    # 2. Save user message to Firestore
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=text_content
    )
    user_msg_dict = user_msg.to_dict()
    if image_url:
        user_msg_dict["image_url"] = image_url

    user_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    user_msg_ref.set(user_msg_dict)

    # 3. Build AI case
    ai_case = _build_ai_case(case_id, case_data)

    # 4. Format message for AI Conversation History (Multimodal support)
    if image_url:
        ai_msg_content = [
            {"type": "text", "text": text_content},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    else:
        ai_msg_content = text_content

    # 5. Append user message to AI conversation history
    ai_case.messages.append({
        "role": "user",
        "content": ai_msg_content
    })

    # 6. Run agent turn
    updated_case, ai_output = await run_agent_turn(ai_case)

    # 7. Save updated AI state
    case_ref.update({
        "ai_phase":    updated_case.phase,
        "fact_sheet":  updated_case.fact_sheet,
        "ai_messages": updated_case.messages,
        "updated_at":  datetime.utcnow(),
    })

    # 8. If field_task — create Google Calendar event
    calendar_event_id = None
    if ai_output.type == "field_task":
        try:
            from app.integrations.google_calendar import create_task_event
            calendar_event_id = create_task_event(
                title=ai_output.title,
                description=ai_output.instruction,
            )
        except Exception as e:
            print(f"Calendar create error: {e}")

    # 9. Save AI message
    ai_content = _format_output_for_chat(ai_output)

    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=ai_content
    )
    ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    
    ai_dict = ai_msg.to_dict()
    ai_dict["ai_output_type"] = ai_output.type
    ai_dict["ai_output_data"] = ai_output.model_dump()
    
    if ai_output.type == "field_task":
        ai_dict["created_task"] = _create_task_from_field_task(case_ref, case_id, ai_output, calendar_event_id)
        
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
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)
    messages_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).order_by("created_at").stream()

    messages = []
    for doc in messages_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        messages.append(snake_dict_to_camel(data))
        
    return messages