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
    data: dict,           # add data param to receive submitted_value + case_id
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    tasks_query = db.collection_group(
        InvestigationTask.SUBCOLLECTION
    ).where(firestore.FieldPath.document_id(), "==", task_id).stream()

    task_doc = None
    for doc in tasks_query:
        task_doc = doc
        break

    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")

    submitted_value = data.get("submitted_value")
    task_doc.reference.update({
        "status": "completed",
        "submitted_value": submitted_value,
    })

    # ── Re-trigger agent now that user submitted evidence ──
    case_id = data.get("case_id")
    if case_id:
        from app.ai.orchestrator import run_agent_turn
        from app.ai.schemas import BusinessCase as AICase
        from datetime import datetime

        case_ref = db.collection(BusinessCase.COLLECTION).document(case_id)
        case_data = case_ref.get().to_dict()

        ai_case = AICase(
            id=case_id,
            idea=case_data.get("description", case_data.get("title", "")),
            location=case_data.get("target_location", ""),
            budget_myr=float(case_data.get("budget_myr", 30000)),
            phase=case_data.get("ai_phase", "EVIDENCE"),
            fact_sheet=case_data.get("fact_sheet", {}),
            messages=case_data.get("ai_messages", []),
        )

        # Tell the agent what the user submitted
        import json
        ai_case.messages.append({
            "role": "user",
            "content": json.dumps({
                "task_completed": task_id,
                "submitted_value": submitted_value,
            })
        })

        updated_case, _ = await run_agent_turn(ai_case)

        case_ref.update({
            "ai_phase":    updated_case.phase,
            "fact_sheet":  updated_case.fact_sheet,
            "ai_messages": updated_case.messages,
            "updated_at":  datetime.utcnow(),
        })

    return {"status": "success", "task_id": task_id}

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
