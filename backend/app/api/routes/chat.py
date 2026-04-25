# app/api/routes/chat.py
"""
Chat Sessions Routes

Handles chat sessions and messages for business cases.
Messages are stored in Firestore subcollections:
  business_cases/{case_id}/chat_sessions/{session_id}
  business_cases/{case_id}/chat_sessions/{session_id}/messages/{msg_id}
"""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from google.cloud import firestore

from app.ai.fact_analyzer import analyze_message_facts, merge_supporting_facts
from app.ai.fact_deriver import derive_fact_sheet_values, remove_legacy_derived_assumptions
from app.ai.fact_extractor import extract_required_facts_from_text
from app.ai.orchestrator import run_agent_turn
from app.ai.prompts_templates import REQUIRED_FACTS
from app.ai.schemas import BusinessCase as AICase
from app.ai.schemas import ClarifyOutput, FieldTaskOutput
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.chat import ChatMessage, ChatSession
from app.services.chat_service import ChatService
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()
logger = logging.getLogger(__name__)

TASKS_SUBCOLLECTION = "tasks"
CHAT_BACKGROUND_FACT_ANALYSIS_TIMEOUT_SECONDS = 15
CHAT_AGENT_TIMEOUT_SECONDS = 45

FALLBACK_TASKS = {
    "competitor_count": FieldTaskOutput(
        type="field_task",
        title="Count nearby competitors",
        instruction=(
            "Provide the number of nearby businesses selling similar products or serving "
            "the same customer need in the target catchment."
        ),
        evidence_type="count",
    ),
    "avg_competitor_rating": FieldTaskOutput(
        type="field_task",
        title="Record competitor ratings",
        instruction="Provide the average rating for the main nearby similar businesses.",
        evidence_type="rating",
    ),
    "estimated_footfall_lunch": FieldTaskOutput(
        type="field_task",
        title="Count lunch footfall",
        instruction="Provide the estimated number of people passing the location during lunch.",
        evidence_type="count",
    ),
    "confirmed_rent_myr": FieldTaskOutput(
        type="field_task",
        title="Confirm monthly rent",
        instruction="Provide the confirmed monthly rent in RM for the target location.",
        evidence_type="text",
    ),
    "break_even_covers": FieldTaskOutput(
        type="field_task",
        title="Calculate break-even covers",
        instruction=(
            "Provide break-even covers per day, or provide average price, food cost percentage, "
            "monthly utilities, monthly staff cost, and trading days per month so it can be calculated."
        ),
        evidence_type="text",
    ),
}


def _build_ai_case(case_id: str, case_data: dict) -> AICase:
    """Build an AI case from Firestore data while normalizing nullable fields."""
    return AICase(
        id=case_id,
        idea=case_data.get("description") or case_data.get("title") or "",
        location=case_data.get("target_location") or "",
        budget_myr=float(case_data.get("budget_myr") or 30000),
        phase=case_data.get("ai_phase") or "INTAKE",
        fact_sheet=remove_legacy_derived_assumptions(case_data.get("fact_sheet") or {}),
        messages=case_data.get("ai_messages") or [],
    )


def _create_calendar_event_for_task(output) -> str | None:
    try:
        from app.integrations.google_calendar import create_task_event

        return create_task_event(
            title=output.title,
            description=output.instruction,
        )
    except Exception:
        logger.exception("Calendar event creation failed for AI field task.")
        return None


def _create_task_from_field_task(case_ref, case_id: str, output, calendar_event_id: str | None = None) -> dict:
    """Persist an AI field_task as a case task document."""
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
        "created_at": now,
        "updated_at": now,
    }
    if calendar_event_id:
        task_dict["calendar_event_id"] = calendar_event_id

    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document()
    task_ref.set(task_dict)
    task_dict["id"] = task_ref.id
    return snake_dict_to_camel(task_dict)


def _missing_required_facts(fact_sheet: dict) -> list[str]:
    return [fact for fact in REQUIRED_FACTS if fact not in fact_sheet or fact_sheet.get(fact) in (None, "")]


def _fallback_ai_output(ai_case: AICase):
    missing_facts = _missing_required_facts(ai_case.fact_sheet)
    if len(ai_case.fact_sheet or {}) < 2 and len(missing_facts) >= 3:
        return ClarifyOutput(
            type="clarify",
            question=(
                "I only have a thin picture so far, so any verdict would be weak. "
                "What is the exact product mix, target customer, and expected average spend per customer?"
            ),
            options=["Answer with details", "Add evidence"],
        )

    for fact in missing_facts:
        fallback_task = FALLBACK_TASKS.get(fact)
        if fallback_task:
            return fallback_task

    return ClarifyOutput(
        type="clarify",
        question="I saved your latest facts. The required fact set is complete enough to generate a verdict.",
        options=["Generate verdict", "Add more evidence"],
    )


async def _analyze_and_persist_chat_facts(
    case_id: str,
    case_ref,
    user_msg_ref,
    content: str,
    deterministic_facts: dict,
    case_context: dict,
) -> None:
    """Run slower AI fact extraction after the chat response is sent."""
    try:
        case_data = case_ref.get().to_dict() or {}
        fact_sheet = remove_legacy_derived_assumptions(case_data.get("fact_sheet") or {})
        fact_analysis = await analyze_message_facts(
            content,
            {**fact_sheet, **(deterministic_facts or {})},
            case_context,
            timeout=CHAT_BACKGROUND_FACT_ANALYSIS_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.exception("Background AI fact analysis failed for case_id=%s.", case_id)
        return

    ai_extracted_facts = fact_analysis.get("structured_facts") or {}
    update_fields = {}
    if ai_extracted_facts:
        update_fields["ai_extracted_facts"] = ai_extracted_facts
        update_fields["extracted_facts"] = {**(deterministic_facts or {}), **ai_extracted_facts}
    if fact_analysis.get("structured_fact_items"):
        update_fields["fact_analysis"] = fact_analysis["structured_fact_items"]
    if fact_analysis.get("supporting_facts"):
        update_fields["supporting_facts"] = fact_analysis["supporting_facts"]
    if fact_analysis.get("evidence_assessment"):
        update_fields["evidence_assessment"] = fact_analysis["evidence_assessment"]
    if update_fields:
        user_msg_ref.update(update_fields)

    case_update = {"updated_at": datetime.utcnow()}
    if ai_extracted_facts:
        fact_sheet.update(ai_extracted_facts)
        derived_facts = derive_fact_sheet_values(fact_sheet, float(case_data.get("budget_myr") or 30000))
        if derived_facts:
            fact_sheet.update(derived_facts)
            user_msg_ref.update({"derived_facts": derived_facts})
        case_update["fact_sheet"] = fact_sheet

    supporting_facts = merge_supporting_facts(
        case_data.get("supporting_facts") or [],
        fact_analysis.get("supporting_facts") or [],
    )
    if supporting_facts:
        case_update["supporting_facts"] = supporting_facts
    if fact_analysis.get("evidence_assessment"):
        case_update["evidence_assessment"] = {
            **fact_analysis["evidence_assessment"],
            "updated_at": datetime.utcnow(),
        }

    if len(case_update) > 1:
        case_ref.update(case_update)


def _format_output_for_chat(output) -> str:
    """Convert AI output to human-readable string for simple display."""
    if output.type == "tool_call":
        return f"Investigating {output.tool.replace('_', ' ')}..."
    if output.type == "field_task":
        return f"{output.title}\n\n{output.instruction}"
    if output.type == "clarify":
        return output.question
    if output.type == "verdict":
        return f"VERDICT: {output.decision}\n\n{output.summary}"
    return ""


@router.post("/{case_id}/sessions")
async def create_session(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new chat session for a case."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    if not case_ref.get().exists:
        raise HTTPException(status_code=404, detail="Case not found")
    service = ChatService(db)
    return await service.create_session(case_id)


@router.get("/{case_id}/sessions")
async def list_sessions(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
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
    background_tasks: BackgroundTasks,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
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

    content = data.get("content", "")
    attachments = data.get("attachments") or []
    if not isinstance(attachments, list):
        attachments = []
    extracted_facts = extract_required_facts_from_text(content)

    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=content,
    )
    user_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    user_msg_dict = user_msg.to_dict()
    if attachments:
        user_msg_dict["attachments"] = attachments

    ai_case = _build_ai_case(case_id, case_data)
    if extracted_facts:
        user_msg_dict["extracted_facts"] = extracted_facts
        ai_case.fact_sheet.update(extracted_facts)

    derived_facts = derive_fact_sheet_values(ai_case.fact_sheet, ai_case.budget_myr)
    if derived_facts:
        ai_case.fact_sheet.update(derived_facts)
        user_msg_dict["derived_facts"] = derived_facts
    user_msg_ref.set(user_msg_dict)

    background_tasks.add_task(
        _analyze_and_persist_chat_facts,
        case_id,
        case_ref,
        user_msg_ref,
        content,
        extracted_facts,
        {
            "case_id": case_id,
            "idea": ai_case.idea,
            "location": ai_case.location,
            "budget_myr": ai_case.budget_myr,
            "source": "chat_message",
        },
    )

    ai_case.messages.append({
        "role": "user",
        "content": content,
    })

    case_ref.update({
        "ai_phase": ai_case.phase,
        "fact_sheet": ai_case.fact_sheet,
        "ai_messages": ai_case.messages,
        "updated_at": datetime.utcnow(),
    })

    evidence_ready = not _missing_required_facts(ai_case.fact_sheet)
    ai_response_source = "glm"
    fallback_reason = None
    fallback_detail = None

    if evidence_ready:
        ai_response_source = "readiness_shortcut"
        ai_output = ClarifyOutput(
            type="clarify",
            question="The required evidence is complete enough to generate the final verdict now.",
            options=["Generate verdict", "Add more evidence"],
        )
        ai_case.messages.append({
            "role": "assistant",
            "content": ai_output.model_dump_json(),
        })
        updated_case = ai_case
    else:
        try:
            updated_case, ai_output = await run_agent_turn(ai_case, timeout=CHAT_AGENT_TIMEOUT_SECONDS)
        except Exception as exc:
            ai_response_source = "local_fallback"
            fallback_reason = exc.__class__.__name__
            fallback_detail = str(exc)[:500]
            logger.exception(
                "AI turn failed for case_id=%s; using local fallback. error_type=%s detail=%s",
                case_id,
                fallback_reason,
                fallback_detail,
            )
            ai_output = _fallback_ai_output(ai_case)
            ai_case.messages.append({
                "role": "assistant",
                "content": ai_output.model_dump_json(),
            })
            updated_case = ai_case

    case_ref.update({
        "ai_phase": updated_case.phase,
        "fact_sheet": updated_case.fact_sheet,
        "ai_messages": updated_case.messages,
        "updated_at": datetime.utcnow(),
    })

    ai_content = _format_output_for_chat(ai_output)
    ai_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=ai_content,
    )
    ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()

    ai_dict = ai_msg.to_dict()
    ai_dict["ai_output_type"] = ai_output.type
    ai_dict["ai_output_data"] = ai_output.model_dump()
    ai_dict["ai_response_source"] = ai_response_source
    if fallback_reason:
        ai_dict["ai_fallback"] = True
        ai_dict["fallback_reason"] = fallback_reason
        ai_dict["fallback_detail"] = fallback_detail
    if ai_output.type == "field_task":
        calendar_event_id = _create_calendar_event_for_task(ai_output)
        ai_dict["created_task"] = _create_task_from_field_task(
            case_ref,
            case_id,
            ai_output,
            calendar_event_id,
        )
    ai_msg_ref.set(ai_dict)

    ai_dict["id"] = ai_msg_ref.id
    return snake_dict_to_camel(ai_dict)


@router.get("/{case_id}/sessions/{session_id}/messages")
async def get_messages(
    case_id: str,
    session_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
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
