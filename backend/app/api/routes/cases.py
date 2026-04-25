"""
Business Cases Routes

CRUD endpoints for business investigation cases.
All case data is persisted in Firestore under the ``business_cases`` collection
and scoped to the authenticated user via the ``user_id`` field.

Firestore path: business_cases/{case_id}
"""
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.schemas.business_case import CaseCreate, CaseUpdate
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()


def _case_response(doc_id: str, data: dict) -> dict:
    """Build a consistent camelCase response dict for a case document."""
    data["id"] = doc_id
    return snake_dict_to_camel(data)


# ────────────────────────────────────────────────────────────────
# CRUD
# ────────────────────────────────────────────────────────────────

@router.post("/")
async def create_case(
    data: CaseCreate,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Create a new business investigation case."""
    uid = user["uid"]
    case = BusinessCase(
        user_id=uid,
        title=data.title,
        description=data.description,
        stage=data.stage,
        business_type=data.business_type,
        target_location=data.target_location,
        status="active"
    )
    case_dict = case.to_dict()
    # Firestore generates an ID if we don't specify one in doc()
    doc_ref = db.collection(BusinessCase.COLLECTION).document()
    doc_ref.set(case_dict)

    return _case_response(doc_ref.id, case_dict)


@router.get("/")
async def list_cases(
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """List all business cases for the current user."""
    uid = user["uid"]
    # NOTE: Combining where() + order_by() on different fields requires a
    # composite Firestore index.  To avoid that setup step we filter only
    # and sort in-memory (case counts per user are small).
    cases_ref = (
        db.collection(BusinessCase.COLLECTION)
        .where("user_id", "==", uid)
        .stream()
    )

    cases = []
    for doc in cases_ref:
        cases.append(_case_response(doc.id, doc.to_dict()))

    # Sort newest first
    cases.sort(key=lambda c: c.get("createdAt", ""), reverse=True)
    return cases


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get detailed info for a specific business case."""
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Case not found")

    data = doc.to_dict()
    if data.get("user_id") != user["uid"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

    return _case_response(doc.id, data)


@router.put("/{case_id}")
async def update_case(
    case_id: str,
    data: CaseUpdate,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update allowed fields on a case. Returns the full updated case."""
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")

    # Only update fields that were explicitly provided
    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=422, detail="No fields to update")

    update_fields["updated_at"] = datetime.utcnow()
    doc_ref.update(update_fields)

    # Return the full updated document
    updated = doc_ref.get().to_dict()
    return _case_response(case_id, updated)


@router.delete("/{case_id}")
async def delete_case(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Hard-delete a case document.

    NOTE: Subcollections (tasks, uploads, chat_sessions, etc.) are NOT
    automatically deleted by Firestore when the parent document is deleted.
    For a full cascade delete, each subcollection would need to be cleaned
    up separately.  For MVP this performs a document-level delete only.
    """
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")

    doc_ref.delete()
    return {"status": "success"}


# ────────────────────────────────────────────────────────────────
# Convenience / workflow endpoints (used by frontend)
# ────────────────────────────────────────────────────────────────

@router.post("/{case_id}/insight")
async def save_insight(
    case_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Save a final insight object on a case."""
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")
    doc_ref.update({"final_insight": data, "updated_at": datetime.utcnow()})
    return {"status": "success"}


@router.put("/{case_id}/status")
async def update_status(
    case_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update only the status field of a case."""
    new_status = data.get("status")
    if new_status not in ("active", "insight_generated", "archived"):
        raise HTTPException(status_code=422, detail="Invalid status value")

    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")

    doc_ref.update({"status": new_status, "updated_at": datetime.utcnow()})
    return {"status": "success"}


@router.post("/{case_id}/archive")
async def archive_case(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Set case status to 'archived'."""
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")
    doc_ref.update({"status": "archived", "updated_at": datetime.utcnow()})
    return {"status": "success"}


@router.post("/{case_id}/end_session")
async def end_session(
    case_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """End session workflow — archive or mark insight_generated."""
    decision = data.get("decision")
    new_status = "archived" if decision == "archive" else "insight_generated"

    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")

    doc_ref.update({
        "status": new_status,
        "final_insight": data.get("insight"),
        "updated_at": datetime.utcnow()
    })
    return {"status": "success"}


@router.post("/{case_id}/reopen")
async def reopen_case(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Reopen an archived/completed case back to active."""
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")
    doc_ref.update({"status": "active", "updated_at": datetime.utcnow()})
    return {"status": "success"}


@router.put("/{case_id}/title")
async def update_title(
    case_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update only the title of a case."""
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")
    doc_ref.update({"title": data.get("title"), "updated_at": datetime.utcnow()})
    return {"status": "success"}


@router.post("/{case_id}/checkpoint")
async def save_checkpoint(
    case_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Save a conversation checkpoint for future AI context."""
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")
    doc_ref.update({"conversation_checkpoint": data, "updated_at": datetime.utcnow()})
    return {"status": "success"}
