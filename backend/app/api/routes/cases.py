from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore
from datetime import datetime

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.schemas.business_case import CaseCreate

router = APIRouter()

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
        mode=data.mode,
        business_type=data.business_type,
        target_location=data.target_location,
        status="active"
    )
    case_dict = case.to_dict()
    # Firestore generates an ID if we don't specify one in doc()
    doc_ref = db.collection(BusinessCase.COLLECTION).document()
    doc_ref.set(case_dict)
    
    # Return with ID
    case_dict["id"] = doc_ref.id
    return case_dict

@router.get("/")
async def list_cases(
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """List all business cases for the current user."""
    uid = user["uid"]
    cases_ref = db.collection(BusinessCase.COLLECTION).where("user_id", "==", uid).stream()
    
    cases = []
    for doc in cases_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        cases.append(data)
    
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
        
    data["id"] = doc.id
    return data

@router.put("/{case_id}")
async def update_case(
    case_id: str, 
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")
        
    update_data = {**data, "updated_at": datetime.utcnow()}
    # Remove id or user_id if they accidentally sent it
    update_data.pop("id", None)
    update_data.pop("user_id", None)
    
    doc_ref.update(update_data)
    return {"status": "success"}

@router.delete("/{case_id}")
async def delete_case(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc = doc_ref.get()
    if not doc.exists or doc.to_dict().get("user_id") != user["uid"]:
        raise HTTPException(status_code=404, detail="Case not found")
        
    doc_ref.delete()
    return {"status": "success"}

@router.post("/{case_id}/insight")
async def save_insight(
    case_id: str, 
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc_ref.update({"final_insight": data})
    return {"status": "success"}

@router.put("/{case_id}/status")
async def update_status(
    case_id: str, 
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc_ref.update({"status": data.get("status"), "updated_at": datetime.utcnow()})
    return {"status": "success"}

@router.post("/{case_id}/archive")
async def archive_case(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc_ref.update({"status": "archived", "updated_at": datetime.utcnow()})
    return {"status": "success"}

@router.post("/{case_id}/end_session")
async def end_session(
    case_id: str, 
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    decision = data.get("decision")
    status = "archived" if decision == "archive" else "insight_generated"
    
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc_ref.update({
        "status": status, 
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
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc_ref.update({"status": "active", "updated_at": datetime.utcnow()})
    return {"status": "success"}

@router.put("/{case_id}/title")
async def update_title(
    case_id: str, 
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc_ref.update({"title": data.get("title"), "updated_at": datetime.utcnow()})
    return {"status": "success"}

@router.post("/{case_id}/checkpoint")
async def save_checkpoint(
    case_id: str, 
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    doc_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    doc_ref.update({"conversation_checkpoint": data, "updated_at": datetime.utcnow()})
    return {"status": "success"}
