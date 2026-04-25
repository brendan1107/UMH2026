# app/api/routes/chat.py
"""
Chat Sessions Routes

Handles chat sessions and messages for business cases.
Messages are stored in Firestore subcollections:
  business_cases/{case_id}/chat_sessions/{session_id}
  business_cases/{case_id}/chat_sessions/{session_id}/messages/{msg_id}
"""
import re
import logging
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from datetime import datetime
from typing import Optional

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
logger = logging.getLogger(__name__)
TASKS_SUBCOLLECTION = "tasks"


def normalize_title(title: str) -> str:
    """Strictly normalize task title for deduplication."""
    return re.sub(r'[^a-z0-9]', '', title.lower().strip())


def _build_ai_case(context: dict) -> AICase:
    """Build an AI case from the aggregated service context."""
    case_data = context["case"]
    tasks = context["tasks"]
    messages = context["messages"]
    latest_analysis = context.get("latest_analysis")
    
    # Prioritize resolved location name for the AI
    location = (
        (latest_analysis.get("resolved_name") if latest_analysis else None) or 
        case_data.get("latest_resolved_location_name") or 
        case_data.get("latestResolvedLocationName") or
        case_data.get("target_location") or 
        ""
    )
    
    # Location analysis metadata
    loc_analysis = None
    if latest_analysis or case_data.get("latest_location_analysis_id"):
        analysis = latest_analysis or {}
        loc_analysis = {
            "resolved_name": analysis.get("resolved_name") or case_data.get("latest_resolved_location_name") or case_data.get("latestResolvedLocationName"),
            "resolved_address": analysis.get("resolved_address") or case_data.get("latest_resolved_address") or case_data.get("latestResolvedAddress"),
            "risk_score": analysis.get("risk_score") or case_data.get("latest_market_risk_score") or case_data.get("latestMarketRiskScore"),
            "risk_level": analysis.get("risk_level") or case_data.get("latest_market_risk_level") or case_data.get("latestMarketRiskLevel"),
            "competitor_count": analysis.get("competitor_count") or case_data.get("latest_competitor_count") or case_data.get("latestCompetitorCount"),
            "strong_competitor_count": analysis.get("strong_competitor_count") or case_data.get("latest_strong_competitor_count") or case_data.get("latestStrongCompetitorCount"),
            "updated_at": analysis.get("created_at") or case_data.get("latest_analysis_updated_at")
        }

    return AICase(
        id=case_data.get("id", ""),
        idea=case_data.get("description") or case_data.get("title") or "",
        location=location,
        budget_myr=float(case_data.get("budget_myr")) if case_data.get("budget_myr") else None,
        phase=case_data.get("ai_phase") or "INTAKE",
        fact_sheet=case_data.get("fact_sheet") or {},
        messages=messages or case_data.get("ai_messages") or [],
        market_context=case_data.get("latest_market_summary") or case_data.get("latest_market_risk_explanation"),
        tasks=tasks,
        case_inputs=context.get("case_inputs"),
        location_analysis=loc_analysis,
        pending_input_key=case_data.get("pending_input_key"),
        pending_input_question=case_data.get("pending_input_question")
    )


async def _create_tasks_from_batch(db: firestore.Client, case_ref, case_id: str, output) -> list[dict]:
    """Persist AI task_batch as case task documents with deduplication."""
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
    
    created_tasks = []
    # Support both single field_task (legacy) and task_batch
    tasks_to_process = output.tasks if hasattr(output, 'tasks') else [output]
    
    from app.services.case_service import CaseService
    case_service = CaseService()
    
    for task_def in tasks_to_process:
        canonical_key = task_def.canonical_key or case_service.derive_canonical_key(task_def.title)
        
        task_dict = {
            "case_id": case_id,
            "title": task_def.title,
            "description": task_def.instruction,
            "type": task_type_by_evidence.get(task_def.evidence_type, "provide_text_input"),
            "status": "pending",
            "ai_message": getattr(task_def, "ai_message", None),
            "follow_up_action": getattr(task_def, "follow_up_action", None),
            "action_label": action_label_by_evidence.get(task_def.evidence_type, "Submit evidence"),
            "canonical_key": canonical_key,
            "data": {
                "description": task_def.instruction,
                "evidence_type": task_def.evidence_type,
                "options": [opt.model_dump() for opt in task_def.options] if getattr(task_def, 'options', None) else None,
                "questions": [q.model_dump() for q in task_def.questions] if getattr(task_def, 'questions', None) else None,
                "eventTitle": getattr(task_def, 'event_title', None),
                "eventDuration": getattr(task_def, 'event_duration', None),
            },
            "source": "ai",
            "created_at": now,
            "updated_at": now,
        }

        # Use upsert_task to prevent duplicates by canonical key
        task_id = await case_service.upsert_task_by_canonical_key(db, case_id, task_dict)
        task_dict["id"] = task_id
        created_tasks.append(snake_dict_to_camel(task_dict))
        
    return created_tasks


@router.post("/{case_id}/sessions")
async def create_session(case_id: str, db: firestore.Client = Depends(get_db), user: dict = Depends(get_current_user)):
    service = ChatService(db)
    return await service.create_session(case_id)


@router.get("/{case_id}/sessions")
async def list_sessions(case_id: str, db: firestore.Client = Depends(get_db), user: dict = Depends(get_current_user)):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    sessions_ref = case_ref.collection(ChatSession.SUBCOLLECTION).stream()
    sessions = []
    for doc in sessions_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        sessions.append(snake_dict_to_camel(data))
    return sessions


@router.post("/{case_id}/messages")
async def send_message_compat(
    case_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Compatibility route: defaults to 'default_session'."""
    return await send_message(case_id, "default_session", data, db, user)


def _detect_pending_input_key(text: str) -> Optional[str]:
    """Detect if the assistant is asking for a specific piece of information."""
    text_lower = text.lower()
    if "monthly rent" in text_lower or "kiosk cost" in text_lower:
        return "monthly_rent"
    if "target customer" in text_lower or "main customers" in text_lower or "students, office workers" in text_lower:
        return "target_customer"
    if "price range" in text_lower or "selling price" in text_lower or "pricing strategy" in text_lower:
        return "pricing_strategy"
    if "cost per drink" in text_lower or "cost per donut" in text_lower or "cost per unit" in text_lower:
        return "cost_per_unit"
    if "daily sales" in text_lower or "sales target" in text_lower or "expected daily sales" in text_lower:
        return "daily_sales_target"
    if "differentiation" in text_lower or "unique" in text_lower:
        return "differentiation"
    if "competitor price" in text_lower or "how much do they charge" in text_lower:
        return "competitor_price"
    return None


def _safe_ai_error_reason(error: Exception) -> str:
    """Return a non-secret reason suitable for logs/responses."""
    status_code = getattr(getattr(error, "response", None), "status_code", None)
    if status_code in (401, 403):
        return f"AI service authentication failed with HTTP {status_code}."
    if status_code == 404:
        return "AI service endpoint or model was not found."
    if status_code == 429:
        return "AI service rate limit was reached."
    if status_code and status_code >= 500:
        return f"AI service returned HTTP {status_code}."
    if isinstance(error, RuntimeError) and "Missing GLM configuration" in str(error):
        return str(error)
    return type(error).__name__


def _assistant_question_from_pending(pending: dict) -> str:
    return f"Next, {pending['question']}"


async def _set_pending_input(case_ref, pending: Optional[dict]):
    now = datetime.utcnow()
    if pending:
        case_ref.update({
            "pending_input_key": pending["key"],
            "pending_input_question": pending["question"],
            "pending_input_type": pending["type"],
            "pending_input_created_at": now,
            "pendingInputKey": pending["key"],
            "pendingInputQuestion": pending["question"],
            "pendingInputType": pending["type"],
            "pendingInputCreatedAt": now,
        })
    else:
        case_ref.update({
            "pending_input_key": None,
            "pending_input_question": None,
            "pending_input_type": None,
            "pending_input_created_at": None,
            "pendingInputKey": None,
            "pendingInputQuestion": None,
            "pendingInputType": None,
            "pendingInputCreatedAt": None,
        })


@router.post("/{case_id}/sessions/{session_id}/messages")
async def send_message(
    case_id: str,
    session_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")

    case_data = case_doc.to_dict()
    if case_data.get("user_id") != user["uid"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)
    content = data.get("content", "").strip()

    # 1. Save user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=content)
    user_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    user_msg_ref.set(user_msg.to_dict())

    from app.services.case_service import CaseService
    case_service = CaseService()

    # 1b. Intercept if there is a pending question
    raw_pending_key = case_data.get("pending_input_key") or case_data.get("pendingInputKey")
    pending_key = case_service.normalize_input_key(raw_pending_key) if raw_pending_key else None
    answered_pending_key = None
    if pending_key and content:
        await case_service.save_case_input(db, case_id, pending_key, {
            "answer": content,
            "question": case_data.get("pending_input_question") or f"Provide {pending_key}",
            "status": "submitted",
            "source": "chat_direct"
        })
        await _set_pending_input(case_ref, None)
        case_data["pending_input_key"] = None
        answered_pending_key = pending_key

    # 2. Build AI Context
    context = await case_service.get_case_ai_context(db, case_id)
    ai_case = _build_ai_case(context)
    
    # Ensure user message is in context for the turn
    if not ai_case.messages or ai_case.messages[-1].get("content") != content:
        ai_case.messages.append({"role": "user", "content": content})

    # 3. Run AI Turn
    try:
        updated_case, ai_output = await run_agent_turn(ai_case)
        
        case_ref.update({
            "ai_phase":    updated_case.phase,
            "fact_sheet":  updated_case.fact_sheet,
            "ai_messages": updated_case.messages,
            "updated_at":  datetime.utcnow(),
        })

        ai_content = _format_output_for_chat(ai_output)
        
        # ── Detect new pending questions from the assistant ──
        new_pending_key = _detect_pending_input_key(ai_content)
        if new_pending_key:
            answered_keys = case_service.get_answered_input_keys(
                context.get("case", {}),
                context.get("case_inputs", []),
                context.get("latest_analysis"),
                context.get("uploads"),
            )
            normalized_pending = case_service.normalize_input_key(new_pending_key)
            if normalized_pending not in answered_keys:
                await _set_pending_input(case_ref, {
                    "key": normalized_pending,
                    "question": ai_content.split("\n")[-1] or ai_content,
                    "type": "text",
                })

        ai_dict = {
            "session_id": session_id,
            "role": "assistant",
            "content": ai_content,
            "created_at": datetime.utcnow(),
            "ai_output_type": ai_output.type,
            "ai_output_data": ai_output.model_dump()
        }
        
        if ai_output.type == "task_batch":
            ai_dict["created_tasks"] = await _create_tasks_from_batch(db, case_ref, case_id, ai_output)
        elif ai_output.type == "field_task":
            ai_dict["created_tasks"] = await _create_tasks_from_batch(db, case_ref, case_id, ai_output)
        elif ai_output.type == "text":
            pass
            
    except Exception as e:
        import traceback
        error_type = type(e).__name__
        error_details = str(e)
        
        from app.config import settings
        logger.error(f"AI Turn failed for case {case_id} ({error_type}): {error_details}")
        logger.error(f"GLM Config: KEY_SET={bool(settings.GLM_API_KEY)}, BASE={settings.GLM_API_BASE_URL}, MODEL={settings.GLM_MODEL_NAME}")
        logger.error(traceback.format_exc())

        context = await case_service.get_case_ai_context(db, case_id)
        pending = case_service.get_next_missing_input(
            context.get("case", {}),
            context.get("case_inputs", []),
            context.get("latest_analysis"),
            context.get("uploads"),
        )

        acknowledgement = ""
        if answered_pending_key:
            acknowledgement = f"Got it. I saved that as your {answered_pending_key.replace('_', ' ')}. "

        if pending:
            await _set_pending_input(case_ref, pending)
            ai_content = acknowledgement + _assistant_question_from_pending(pending)
        else:
            await _set_pending_input(case_ref, None)
            ai_content = acknowledgement + case_service.build_recommendation_from_context(
                context.get("case", {}),
                context.get("case_inputs", []),
                context.get("latest_analysis"),
            )

        ai_dict = {
            "session_id": session_id,
            "role": "assistant",
            "content": ai_content,
            "created_at": datetime.utcnow(),
            "ai_output_type": "text",
            "ai_output_data": {
                "type": "text",
                "content": ai_content,
                "error": error_type,
                "safe_reason": _safe_ai_error_reason(e),
                "is_fallback": True,
            },
        }

        recent_msgs = session_ref.collection(ChatMessage.SUBCOLLECTION).order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).get()
        if recent_msgs:
            last_msg = recent_msgs[0].to_dict()
            if last_msg.get("role") == "assistant" and last_msg.get("content") == ai_content:
                ai_dict["id"] = recent_msgs[0].id
                return snake_dict_to_camel(ai_dict)

        ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
        ai_msg_ref.set(ai_dict)
        ai_dict["id"] = ai_msg_ref.id
        return snake_dict_to_camel(ai_dict)

        # Build context-aware fallback
        analysis = context.get("latest_analysis") or {}
        location = (
            analysis.get("resolved_name") or 
            case_data.get("target_location") or 
            case_data.get("latest_resolved_location_name") or 
            "your target area"
        )
        idea = case_data.get("description") or case_data.get("title") or "your business idea"
        
        # Competitor data
        comp_count = analysis.get("competitor_count", 0)
        risk_level = analysis.get("risk_level", "Unknown")
        
        # Extract inputs for specific advice
        inputs = {}
        for inp in (context.get("case_inputs") or []):
            inputs[inp.get("key")] = inp.get("answer", "")

        # ── Determine what was just answered ──
        # If we reached here, send_message might have just saved a pending input.
        # Let's see if we can acknowledge it.
        acknowledgement = ""
        last_pending_key = case_doc.to_dict().get("pending_input_key")
        if last_pending_key and last_pending_key in inputs:
            ans_val = inputs[last_pending_key]
            if last_pending_key == "monthly_rent":
                acknowledgement = f"Got it — I'll use RM{ans_val} as your estimated monthly rent. "
            elif last_pending_key == "cost_per_unit":
                acknowledgement = f"Acknowledged, your cost per unit is {ans_val}. "
            elif last_pending_key == "expected_daily_sales":
                acknowledgement = f"Understood, targetting {ans_val} sales per day. "
            else:
                acknowledgement = f"Got it, thanks for the info on {last_pending_key.replace('_', ' ')}. "

        # ── Determine the next missing variable ──
        priority_keys = [
            ("target_customer", "Who are your main target customers (e.g., students, office workers)?"),
            ("pricing_strategy", "What is your expected selling price range for a single item?"),
            ("cost_per_unit", "What is your estimated cost per drink or food unit?"),
            ("monthly_rent", "What is your estimated monthly rent or kiosk cost?"),
            ("daily_sales_target", "How many daily sales do you expect or need to break even?"),
            ("differentiation", "What makes your concept different from existing competitors?"),
            ("competitor_price", "How much do your closest competitors charge for a similar item?")
        ]
        
        next_step_key = None
        next_step_question = "What are your next steps for this investigation?"
        
        for key, question in priority_keys:
            if not inputs.get(key):
                next_step_key = key
                next_step_question = question
                break

        # Save new pending state for the fallback
        if next_step_key:
            case_ref.update({
                "pending_input_key": next_step_key,
                "pending_input_question": next_step_question,
                "pending_input_type": "text"
            })

        # Build the final message
        if next_step_key == "monthly_rent" and "pricing_strategy" in inputs:
            ans = inputs["pricing_strategy"]
            cost = inputs.get("cost_per_unit", "your current cost")
            price = inputs.get("pricing_strategy", "your price range")
            
            ai_content = (
                f"{acknowledgement}Based on your {location} analysis, your {price} budget pricing is attractive, "
                f"but your estimated cost of {cost} per unit leaves very little margin. "
                "A safer approach is to push profitable bundles above RM12. "
            )
        elif next_step_key == "differentiation" and inputs.get("differentiation"):
            diff = inputs.get("differentiation", "").lower()
            if "better" in diff or "good" in diff:
                ai_content = (
                    f"{acknowledgement}You mentioned your concept is '{diff}', but that might be too vague for Jaya One. "
                    "What specifically makes your product better: price, taste, speed, portion size, location convenience, or unique flavour?"
                )
                next_step_question = "Can you provide a more specific unique selling point?"
            else:
                ai_content = f"{acknowledgement}Your differentiation strategy '{diff}' looks interesting. "
        elif next_step_key == "target_customer" and not inputs.get("target_customer"):
            ai_content = (
                f"{acknowledgement}Since {location} has {comp_count} competitors and a {risk_level} risk level, "
                "knowing exactly who you are serving is critical. "
            )
        elif not next_step_key:
             ai_content = (
                f"{acknowledgement}You have enough initial information for a preliminary decision. "
                f"Based on {location}’s {risk_level} competition and your inputs, "
                "the main issue is ensuring a sustainable margin. "
                "I recommend validating your differentiation strategy further."
             )
        else:
            # We don't have recent_msgs defined here yet, so we fetch it if needed or just use a flag
            ai_content = (
                f"{acknowledgement}I'm having a bit of trouble connecting to my full reasoning service, but "
                f"based on your project in {location}, we should keep moving forward. "
            )

        if next_step_key:
            ai_content += f"\n\nNext, {next_step_question}"
        else:
            ai_content += "\n\nI'll generate a feasibility summary for you next."
        
        # If it was an auth error, override
        if "401" in error_details or "403" in error_details:
            ai_content = f"I'm having trouble authenticating with my reasoning service. Please check the GLM_API_KEY."
        
        ai_dict = {
            "session_id": session_id,
            "role": "assistant",
            "content": ai_content,
            "created_at": datetime.utcnow(),
            "ai_output_type": "text",
            "ai_output_data": {"type": "text", "content": ai_content, "error": error_type, "is_fallback": True}
        }


    # 4. Save AI output as a chat message (with deduplication)
    # Check if the last assistant message is identical to avoid "fallback loop" spam
    recent_msgs = session_ref.collection(ChatMessage.SUBCOLLECTION).order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).get()
    if recent_msgs:
        last_msg = recent_msgs[0].to_dict()
        if last_msg.get("role") == "assistant" and last_msg.get("content") == ai_content:
            logger.info("Skipping duplicate assistant message.")
            ai_dict["id"] = recent_msgs[0].id
            return snake_dict_to_camel(ai_dict)

    ai_msg_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).document()
    ai_msg_ref.set(ai_dict)
    ai_dict["id"] = ai_msg_ref.id
    return snake_dict_to_camel(ai_dict)


def _format_output_for_chat(output) -> str:
    if output.type == "tool_call":
        return f"Investigating {output.tool.replace('_', ' ')}..."
    elif output.type == "task_batch":
        chat_message = getattr(output, "chat_message", None)
        if chat_message:
            return chat_message
        task_count = len(getattr(output, "tasks", []) or [])
        if task_count:
            return f"I created {task_count} focused investigation task{'s' if task_count != 1 else ''} for the next missing input."
        return "I created the next investigation step."
    elif output.type == "field_task":
        return f"Mission: {output.title}\n\n{output.instruction}"
    elif output.type == "clarify":
        return output.question
    elif output.type == "verdict":
        return f"VERDICT: {output.decision}\n\n{output.summary}"
    elif output.type == "text":
        return output.content
    return ""


@router.get("/{case_id}/messages")
async def get_messages_compat(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Compatibility route: defaults to 'default_session'."""
    return await get_messages(case_id, "default_session", db, user)


@router.get("/{case_id}/sessions/{session_id}/messages")
async def get_messages(case_id: str, session_id: str, db: firestore.Client = Depends(get_db), user: dict = Depends(get_current_user)):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    session_ref = case_ref.collection(ChatSession.SUBCOLLECTION).document(session_id)
    messages_ref = session_ref.collection(ChatMessage.SUBCOLLECTION).order_by("created_at").stream()
    messages = []
    for doc in messages_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        messages.append(snake_dict_to_camel(data))
    return messages
