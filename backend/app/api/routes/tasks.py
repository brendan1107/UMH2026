from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.models.investigation_task import InvestigationTask

router = APIRouter()

@router.get("/{case_id}/tasks")
async def list_tasks(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
    tasks_ref = case_ref.collection(InvestigationTask.SUBCOLLECTION).stream()
    
    tasks = []
    for doc in tasks_ref:
        data = doc.to_dict()
        data["id"] = doc.id
        tasks.append(data)
        
    return tasks

@router.put("/{task_id}")
async def update_task(
    task_id: str, 
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # Task ID doesn't easily map back to Case ID unless we query across all subcollections or send case_id.
    # We will use a collection group query to find the task, or the frontend must send case_id.
    # To keep it simple, we'll do a collection group query to find the task.
    tasks_query = db.collection_group(InvestigationTask.SUBCOLLECTION).where(firestore.FieldPath.document_id(), "==", task_id).stream()
    
    task_doc = None
    for doc in tasks_query:
        task_doc = doc
        break
        
    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_doc.reference.update({"status": data.get("status", "completed")})
    return {"id": task_id, "status": data.get("status", "completed")}

@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    tasks_query = db.collection_group(InvestigationTask.SUBCOLLECTION).where(firestore.FieldPath.document_id(), "==", task_id).stream()
    
    task_doc = None
    for doc in tasks_query:
        task_doc = doc
        break
        
    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_doc.reference.update({"status": "completed"})
    return {"status": "success"}

@router.post("/{task_id}/skip")
async def skip_task(
    task_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    tasks_query = db.collection_group(InvestigationTask.SUBCOLLECTION).where(firestore.FieldPath.document_id(), "==", task_id).stream()
    
    task_doc = None
    for doc in tasks_query:
        task_doc = doc
        break
        
    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_doc.reference.update({"status": "skipped"})
    return {"status": "success"}
