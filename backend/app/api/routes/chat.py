# app/api/routes/chat.py
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
from app.services.chat_service import ChatService

# ──  AI imports ──
from app.ai.orchestrator import run_agent_turn
from app.ai.schemas import BusinessCase as AICase

router = APIRouter()
TASKS_SUBCOLLECTION = "tasks"


def _build_ai_case(context: dict) -> AICase:
    """Build an AI case from the aggregated service context."""
    case_data = context["case"]
    latest_analysis = context["latest_analysis"]
    tasks = context["tasks"]
    messages = context["messages"]
    
    return AICase(
        id=case_data.get("id", ""),
        idea=case_data.get("description") or case_data.get("title") or "",
        location=case_data.get("target_location") or "",
        budget_myr=float(case_data.get("budget_myr") or 30000),
        phase=case_data.get("ai_phase") or "INTAKE",
        fact_sheet=case_data.get("fact_sheet") or {},
        messages=messages or case_data.get("ai_messages") or [],
        market_context=case_data.get("latest_market_summary") or case_data.get("latest_market_risk_explanation"),
        tasks=tasks,
        location_analysis={
            "resolved_name": case_data.get("latest_resolved_location_name"),
            "resolved_address": case_data.get("latest_resolved_address"),
            "risk_score": case_data.get("latest_market_risk_score"),
            "risk_level": case_data.get("latest_market_risk_level"),
            "competitor_count": case_data.get("latest_competitor_count"),
            "strong_competitor_count": case_data.get("latest_strong_competitor_count"),
            "updated_at": case_data.get("latest_analysis_updated_at")
        } if case_data.get("latest_location_analysis_id") else None
    )


def _create_task_from_field_task(case_ref, case_id: str, output) -> dict:
    """Persist an AI field_task as a case task document."""
    now = datetime.utcnow()
    task_type_by_evidence = {
        "count": "provide_text_input",
        "photo": "upload_image",
        "rating": "provide_text_input",
        "text": "provide_text_input",
        "location": "select_location",
        "schedule": "schedule_event",
        "decision": "choose_option",
        "questions": "answer_questions",
    }
    action_label_by_evidence = {
        "count": "Submit count",
        "photo": "Upload evidence",
        "rating": "Submit rating",
        "text": "Submit finding",
        "location": "Select Location",
        "schedule": "Schedule Event",
        "decision": "Make Decision",
        "questions": "Answer Questions",
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
            "options": [opt.model_dump() for opt in output.options] if getattr(output, 'options', None) else None,
            "questions": [q.model_dump() for q in output.questions] if getattr(output, 'questions', None) else None,
            "eventTitle": getattr(output, 'event_title', None),
            "eventDuration": getattr(output, 'event_duration', None),
        },
        "source": "ai",
        "created_at": now,
        "updated_at": now,
    }

    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document()
    task_ref.set(task_dict)
    task_dict["id"] = task_ref.id
    return snake_dict_to_camel(task_dict)


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
    service = ChatService(db)
    return await service.create_session(case_id)

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
    """Send a message in a chat session. Stores user message and AI response."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")

    case_data = case_doc.to_dict()
    if case_data.get("user_id") != user["uid"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)

    # 1. Save user message to Firestore
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=data.get("content", "")
    )
    user_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    user_msg_ref.set(user_msg.to_dict())

    # 3. Build AICase from Firestore data
    ai_case = _build_ai_case(case_id, case_data)

    # 4. Append user message to AI conversation history
    ai_case.messages.append({
        "role": "user",
        "content": data.get("content", "")
    })

    # 5. Run one agent turn — GLM thinks and responds
    try:
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
        ai_dict = {
            "session_id": session_id,
            "role": "assistant",
            "content": ai_content,
            "created_at": datetime.utcnow(),
            "ai_output_type": ai_output.type,
            "ai_output_data": ai_output.model_dump()
        }
        if ai_output.type == "field_task":
            ai_dict["created_task"] = _create_task_from_field_task(case_ref, case_id, ai_output)
            
    except Exception as e:
        import logging
        logging.error(f"AI Turn failed: {e}")
        # Fallback message
        ai_content = "I'm having trouble reaching my high-level reasoning service right now. However, you can continue exploring the current roadmap or manually investigate nearby locations using the 'Location Intelligence' tool."
        ai_dict = {
            "session_id": session_id,
            "role": "assistant",
            "content": ai_content,
            "created_at": datetime.utcnow(),
            "ai_output_type": "text",
            "ai_output_data": {"type": "text", "content": ai_content}
        }

    ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    ai_msg_ref.set(ai_dict)
    ai_dict["id"] = ai_msg_ref.id
    return snake_dict_to_camel(ai_dict)



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
    service = ChatService(db)
    return await service.get_session_history(case_id, session_id)
