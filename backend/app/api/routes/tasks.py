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
        "action_label": data.actionLabel,
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
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Mark a task as completed (legacy convenience endpoint).

    Uses a collection group query since case_id is not in the path.
    """
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

    task_doc.reference.update({
        "status": "completed",
        "completed_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    return {"status": "success"}


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

    task_doc.reference.update({
        "status": "skipped",
        "updated_at": datetime.utcnow(),
    })
    return {"status": "success"}
