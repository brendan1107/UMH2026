"""
Investigation Tasks Routes

CRUD endpoints for tasks associated with a business case.
Tasks are stored as a Firestore subcollection:
  business_cases/{case_id}/tasks/{task_id}
"""
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.schemas.task import TaskCreate, TaskStatusUpdate
from app.utils.helpers import snake_dict_to_camel
from app.services.case_service import CaseService

# AI Imports
from app.ai.orchestrator import run_agent_turn
from app.ai.schemas import BusinessCase as AICase

router = APIRouter()

# Subcollection name for tasks directly under a case
TASKS_SUBCOLLECTION = "tasks"


def _task_response(doc_id: str, data: dict, case_id: str) -> dict:
    """Build a consistent camelCase response dict for a task document."""
    data["id"] = doc_id
    data["case_id"] = case_id
    return snake_dict_to_camel(data)


def _get_case_ref(db, case_id: str, user_uid: str):
    """Verify case exists and belongs to user. Returns case doc ref."""
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    case_doc = case_ref.get()
    if not case_doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")
    if case_doc.to_dict().get("user_id") != user_uid:
        raise HTTPException(status_code=403, detail="Not authorized")
    return case_ref


def _clean_submitted_value(value):
    if isinstance(value, dict) and "status" in value:
        return {k: v for k, v in value.items() if k != "status"}
    return value


def _pending_update_fields(pending):
    now = datetime.utcnow()
    if not pending:
        return {
            "pending_input_key": None,
            "pending_input_question": None,
            "pending_input_type": None,
            "pending_input_created_at": None,
            "pendingInputKey": None,
            "pendingInputQuestion": None,
            "pendingInputType": None,
            "pendingInputCreatedAt": None,
            "updated_at": now,
        }
    return {
        "pending_input_key": pending["key"],
        "pending_input_question": pending["question"],
        "pending_input_type": pending["type"],
        "pending_input_created_at": now,
        "pendingInputKey": pending["key"],
        "pendingInputQuestion": pending["question"],
        "pendingInputType": pending["type"],
        "pendingInputCreatedAt": now,
        "updated_at": now,
    }


async def _append_next_step_message(db: firestore.Client, case_id: str, service: CaseService, prefix: str = "Saved."):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    context = await service.get_case_ai_context(db, case_id)
    if not context:
        return

    pending = service.get_next_missing_input(
        context.get("case", {}),
        context.get("case_inputs", []),
        context.get("latest_analysis"),
        context.get("uploads"),
    )

    if pending:
        case_ref.update(_pending_update_fields(pending))
        content = f"{prefix} Next, {pending['question']}"
    else:
        case_ref.update(_pending_update_fields(None))
        content = f"{prefix} {service.build_recommendation_from_context(context.get('case', {}), context.get('case_inputs', []), context.get('latest_analysis'))}"

    session_ref = case_ref.collection("chat_sessions").document("default_session")
    if not session_ref.get().exists:
        session_ref.set({
            "case_id": case_id,
            "title": "Default Session",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

    recent_msgs = session_ref.collection("messages").order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).get()
    if recent_msgs:
        last_msg = recent_msgs[0].to_dict()
        if last_msg.get("role") == "assistant" and last_msg.get("content") == content:
            return

    session_ref.collection("messages").document().set({
        "role": "assistant",
        "content": content,
        "ai_mode": "task_follow_up",
        "created_at": datetime.utcnow(),
    })


# ────────────────────────────────────────────────────────────────
# CRUD
# ────────────────────────────────────────────────────────────────

@router.get("/{case_id}")
async def list_tasks(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """List all tasks for a business case with deduplication."""
    from app.services.case_service import CaseService
    service = CaseService()
    case_data = await service.get_case_with_details(db, case_id)
    
    if not case_data:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if case_data.get("user_id") != user["uid"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    return [snake_dict_to_camel(t) for t in case_data["tasks"]]


@router.post("/{case_id}")
async def create_task(
    case_id: str,
    data: TaskCreate,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Create a new task under a case using upsert logic."""
    case_ref = _get_case_ref(db, case_id, user["uid"])

    task_dict = {
        "case_id": case_id,
        "title": data.title,
        "description": data.description,
        "type": data.type,
        "status": data.status,
        "action_label": data.action_label,
        "canonical_key": data.canonical_key or CaseService().derive_canonical_key(data.title),
        "data": data.data,
        "source": data.source,
    }

    task_id = await CaseService().upsert_task(db, case_id, task_dict)

    return _task_response(task_id, task_dict, case_id)


@router.put("/{case_id}/{task_id}")
async def update_task(
    case_id: str,
    task_id: str,
    data: TaskStatusUpdate,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update a task's status."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document(task_id)
    task_doc = task_ref.get()

    if not task_doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")

    service = CaseService()
    current_task = task_doc.to_dict()
    input_key = current_task.get("canonical_key") or service.derive_canonical_key(current_task.get("title", "unnamed_task"))
    submitted_value = _clean_submitted_value(data.submitted_value)
    response_text = service._summarize_answer(submitted_value, input_key) if submitted_value is not None else ""

    update_fields = {
        "status": data.status,
        "canonical_key": input_key,
        "updated_at": datetime.utcnow(),
    }
    if submitted_value is not None:
        update_fields["submitted_value"] = submitted_value
        update_fields["response_text"] = response_text
        update_fields["structured_response"] = submitted_value
    if data.status == "completed":
        update_fields["completed_at"] = datetime.utcnow()

    task_ref.update(update_fields)
    updated = task_ref.get().to_dict()

    # ── Sync with case_inputs ──
    if data.status == "completed" or (submitted_value is not None and updated.get("status") == "completed"):
        clean_answer = response_text or service._summarize_answer(updated.get("submitted_value"), input_key)

        await service.save_case_input(db, case_id, input_key, {
            "answer": clean_answer,
            "structured_answer": submitted_value,
            "question": updated.get("title"),
            "status": "submitted",
            "source": "task",
            "related_task_id": task_id
        })

        for related_key, related_payload in service.derive_related_inputs(input_key, submitted_value).items():
            await service.save_case_input(db, case_id, related_key, {
                **related_payload,
                "status": "submitted",
                "source": "task",
                "related_task_id": task_id,
            })

        await _append_next_step_message(db, case_id, service)

    return _task_response(task_id, updated, case_id)


@router.delete("/{case_id}/{task_id}")
async def delete_task(
    case_id: str,
    task_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Delete a task."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document(task_id)
    task_doc = task_ref.get()

    if not task_doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")

    task_ref.delete()
    return {"status": "success"}


# ────────────────────────────────────────────────────────────────
# Convenience shortcuts (kept for backward compat with frontend)
# ────────────────────────────────────────────────────────────────

@router.get("/{case_id}/tasks")
async def list_tasks_compat(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Backward-compatible alias: GET /tasks/{case_id}/tasks → same as GET /tasks/{case_id}."""
    return await list_tasks(case_id, db, user)


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    data: dict,           # add data param to receive submitted_value + case_id
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    tasks_query = (
        db.collection_group(TASKS_SUBCOLLECTION)
        .where(firestore.FieldPath.document_id(), "==", task_id)
        .stream()
    )

    task_doc = None
    for doc in tasks_query:
        task_doc = doc
        break


    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")

    case_id = data.get("case_id")
    parent_case_ref = task_doc.reference.parent.parent
    if parent_case_ref is not None:
        case_id = parent_case_ref.id

    if not case_id:
        raise HTTPException(status_code=422, detail="case_id is required")

    _get_case_ref(db, case_id, user["uid"])

    submitted_value = _clean_submitted_value(data.get("submitted_value", data.get("submittedValue")))
    target_status = data.get("status", "completed")
    task_dict = task_doc.to_dict()
    service = CaseService()
    input_key = task_dict.get("canonical_key") or service.derive_canonical_key(task_dict.get("title", "unnamed_task"))
    clean_answer = service._summarize_answer(submitted_value, input_key)
    task_doc.reference.update({
        "status": target_status,
        "canonical_key": input_key,
        "submitted_value": submitted_value,
        "response_text": clean_answer,
        "structured_response": submitted_value,
        "completed_at": datetime.utcnow() if target_status == "completed" else None,
        "updated_at": datetime.utcnow(),
    })

    # ── Sync with case_inputs ──
    await service.save_case_input(db, case_id, input_key, {
        "answer": clean_answer,
        "structured_answer": submitted_value,
        "question": task_dict.get("title"),
        "status": "partial" if target_status != "completed" else "submitted",
        "source": "task",
        "related_task_id": task_id
    })

    for related_key, related_payload in service.derive_related_inputs(input_key, submitted_value).items():
        await service.save_case_input(db, case_id, related_key, {
            **related_payload,
            "status": "submitted",
            "source": "task",
            "related_task_id": task_id,
        })

    await _append_next_step_message(db, case_id, service)
    return {"status": "success", "task_id": task_id}

    # ── Re-trigger agent now that user submitted evidence ──
    if case_id:
        from app.ai.orchestrator import run_agent_turn
        from app.services.case_service import CaseService
        
        # 1. Fetch unified context
        context = await CaseService().get_case_ai_context(db, case_id)
        if not context:
            return {"status": "success", "task_id": task_id}
            
        # 2. Build AI Case
        case_data = context["case"]
        from app.api.routes.chat import _build_ai_case
        ai_case = _build_ai_case(context)

        # Tell the agent what the user submitted (summarized)
        from app.services.case_service import CaseService
        summary = CaseService()._summarize_answer(submitted_value)
        ai_case.messages.append({
            "role": "user",
            "content": f"I've completed the task: {task_doc.to_dict().get('title')}. {summary}"
        })

        try:
            updated_case, _ = await run_agent_turn(ai_case)

            # Update case state
            case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
            case_ref.update({
                "ai_phase":    updated_case.phase,
                "fact_sheet":  updated_case.fact_sheet,
                "ai_messages": updated_case.messages,
                "updated_at":  datetime.utcnow(),
            })

            # Also save AI response to chat if possible (default session)
            session_ref = case_ref.collection("chat_sessions").document("default_session")
            if session_ref.get().exists:
                ai_msg = updated_case.messages[-1]
                ai_msg["created_at"] = datetime.utcnow()
                session_ref.collection("messages").document().set(ai_msg)
        except Exception as e:
            import logging
            logging.error(f"Task re-trigger failed: {e}")

    return {"status": "success", "task_id": task_id}


@router.post("/{task_id}/skip")
async def skip_task(
    task_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Mark a task as skipped (legacy convenience endpoint)."""
    tasks_query = (
        db.collection_group(TASKS_SUBCOLLECTION)
        .where(firestore.FieldPath.document_id(), "==", task_id)
        .stream()
    )

    task_doc = None
    for doc in tasks_query:
        task_doc = doc
        break

    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")

    parent_case_ref = task_doc.reference.parent.parent
    if parent_case_ref is None:
        raise HTTPException(status_code=422, detail="Task has no parent case")

    _get_case_ref(db, parent_case_ref.id, user["uid"])

    task_doc.reference.update({
        "status": "skipped",
        "updated_at": datetime.utcnow(),
    })
    return {"status": "success"}
