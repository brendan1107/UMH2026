# app/api/routes/tasks.py
import io
import httpx
import base64
import PyPDF2
import pandas as pd

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
import json

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
    tasks_query = db.collection_group(InvestigationTask.SUBCOLLECTION).where(firestore.FieldPath.document_id(), "==", task_id).stream()
    
    task_doc = None
    for doc in tasks_query:
        task_doc = doc
        break
        
    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_doc.reference.update({"status": data.get("status", "completed")})
    return {"id": task_id, "status": data.get("status", "completed")}

async def parse_submitted_file(url: str) -> dict:
    """Downloads the file from the URL and parses it for Gemini."""
    try:
        # 1. Download file to memory (bypasses most 403/400 errors)
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            file_bytes = resp.content
            content_type = resp.headers.get("Content-Type", "").lower()
            
        url_lower = url.lower()

        # 2. Handle Images -> Convert to Base64
        if "image" in content_type or any(ext in url_lower for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            b64_encoded = base64.b64encode(file_bytes).decode('utf-8')
            mime = content_type if "image" in content_type else "image/jpeg"
            return {
                "type": "image_url", 
                "image_url": {"url": f"data:{mime};base64,{b64_encoded}"}
            }

        # 3. Handle PDFs -> Extract Text
        elif "pdf" in content_type or ".pdf" in url_lower:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            return {
                "type": "text", 
                "text": f"[Extracted Text from Uploaded PDF Document]:\n{text[:15000]}" # Limit to 15k chars to be safe
            }

        # 4. Handle Spreadsheets (CSV/Excel) -> Extract Text
        elif "csv" in content_type or "excel" in content_type or "spreadsheet" in content_type or any(ext in url_lower for ext in [".csv", ".xlsx", ".xls"]):
            if ".csv" in url_lower or "csv" in content_type:
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            text = df.to_string(index=False)
            return {
                "type": "text", 
                "text": f"[Extracted Data from Uploaded Spreadsheet]:\n{text[:15000]}"
            }

        # 5. Fallback for unknown files
        return {"type": "text", "text": f"User submitted a file here: {url}"}

    except Exception as e:
        print(f"File Parse Error: {e}")
        return {"type": "text", "text": f"User submitted a file, but the system could not read it. URL: {url}"}


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    data: dict,           
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    # ... (Keep your existing Firebase task fetching logic) ...
    tasks_query = db.collection_group(InvestigationTask.SUBCOLLECTION).where(firestore.FieldPath.document_id(), "==", task_id).stream()
    task_doc = next(tasks_query, None)
    if not task_doc:
        raise HTTPException(status_code=404, detail="Task not found")

    submitted_value = data.get("submitted_value", "")
    task_doc.reference.update({
        "status": "completed",
        "submitted_value": submitted_value,
    })

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

        # ── THE NEW UNIVERSAL FILE LOGIC ──
        if isinstance(submitted_value, str) and submitted_value.startswith("http"):
            # Download and parse the file!
            parsed_content = await parse_submitted_file(submitted_value)
            
            ai_case.messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Task completed: '{task_doc.to_dict().get('title')}'. Here is the evidence:"},
                    parsed_content
                ]
            })
        else:
            # Standard Text format
            ai_case.messages.append({
                "role": "user",
                "content": json.dumps({
                    "task_completed": task_doc.to_dict().get("title", task_id),
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