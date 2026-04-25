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


# ────────────────────────────────────────────────────────────────
# CRUD
# ────────────────────────────────────────────────────────────────

@router.get("/{case_id}")
async def list_tasks(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """List all tasks for a business case."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    tasks_ref = case_ref.collection(TASKS_SUBCOLLECTION).order_by("created_at").stream()

    tasks = []
    for doc in tasks_ref:
        tasks.append(_task_response(doc.id, doc.to_dict(), case_id))

    return tasks


@router.post("/{case_id}")
async def create_task(
    case_id: str,
    data: TaskCreate,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Create a new task under a case."""
    case_ref = _get_case_ref(db, case_id, user["uid"])

    now = datetime.utcnow()
    task_dict = {
        "case_id": case_id,
        "title": data.title,
        "description": data.description,
        "type": data.type,
        "status": data.status,
        "action_label": data.action_label,
        "data": data.data,
        "source": data.source,
        "created_at": now,
        "updated_at": now,
    }

    doc_ref = case_ref.collection(TASKS_SUBCOLLECTION).document()
    doc_ref.set(task_dict)

    return _task_response(doc_ref.id, task_dict, case_id)


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

    update_fields = {"status": data.status, "updated_at": datetime.utcnow()}
    if data.submitted_value is not None:
        update_fields["submitted_value"] = data.submitted_value
    if data.status == "completed":
        update_fields["completed_at"] = datetime.utcnow()

    task_ref.update(update_fields)

    updated = task_ref.get().to_dict()
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

    submitted_value = data.get("submitted_value", data.get("submittedValue"))
    target_status = data.get("status", "completed")
    task_dict = task_doc.to_dict()
    task_doc.reference.update({
        "status": target_status,
        "submitted_value": submitted_value,
        "completed_at": datetime.utcnow() if target_status == "completed" else None,
        "updated_at": datetime.utcnow(),
    })

    # ── Sync with case_inputs ──
    from app.services.case_service import CaseService
    # Generate a key from the title (e.g. "Analyze Audience" -> "analyze_audience")
    input_key = task_dict.get("title", "unnamed_task").lower().replace(" ", "_").replace("(", "").replace(")", "")
    await CaseService().save_case_input(db, case_id, input_key, {
        "answer": str(submitted_value) if submitted_value else "",
        "structured_answer": submitted_value if isinstance(submitted_value, (dict, list)) else None,
        "question": task_dict.get("title"),
        "status": "partial" if target_status != "completed" else "submitted",
        "source": "task",
        "related_task_id": task_id
    })

    # ── Re-trigger agent now that user submitted evidence ──
    if case_id:
        from app.ai.orchestrator import run_agent_turn
        from app.services.case_service import CaseService
        
        # 1. Fetch unified context
        context = await CaseService().get_case_ai_context(db, case_id)
        if not context:
            return {"status": "success", "task_id": task_id}
            
        # 2. Build AI Case
        # We reuse the helper from chat.py if available, or just build it here
        case_data = context["case"]
        ai_case = AICase(
            id=case_id,
            idea=case_data.get("description") or case_data.get("title") or "",
            location=case_data.get("target_location") or "",
            budget_myr=float(case_data.get("budget_myr") or 30000),
            phase=case_data.get("ai_phase") or "EVIDENCE",
            fact_sheet=case_data.get("fact_sheet") or {},
            messages=context["messages"],
            market_context=case_data.get("latest_market_summary") or case_data.get("latest_market_risk_explanation"),
            tasks=context["tasks"],
            location_analysis={
                "resolved_name": case_data.get("latest_resolved_location_name"),
                "resolved_address": case_data.get("latest_resolved_address"),
                "risk_score": case_data.get("latest_market_risk_score"),
                "risk_level": case_data.get("latest_market_risk_level"),
                "competitor_count": case_data.get("latest_competitor_count"),
                "strong_competitor_count": case_data.get("latest_strong_competitor_count")
            } if case_data.get("latest_location_analysis_id") else None
        )

        # Tell the agent what the user submitted
        ai_case.messages.append({
            "role": "user",
            "content": f"I've completed the task: {task_doc.to_dict().get('title')}. Answer: {submitted_value}"
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
