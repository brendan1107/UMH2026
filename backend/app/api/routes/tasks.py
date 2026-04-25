"""
Investigation Tasks Routes

CRUD endpoints for tasks associated with a business case.
Tasks are stored as a Firestore subcollection:
  business_cases/{case_id}/tasks/{task_id}
"""
import base64
import io
import json
import logging
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from app.ai.fact_analyzer import analyze_message_facts, merge_supporting_facts
from app.ai.fact_deriver import derive_fact_sheet_values, remove_legacy_derived_assumptions
from app.ai.fact_extractor import extract_required_facts_from_task_submission
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.business_case import BusinessCase
from app.schemas.task import TaskCreate, TaskStatusUpdate
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()
logger = logging.getLogger(__name__)

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


def _case_budget(case_data: dict) -> float:
    return float(case_data.get("budget_myr") or 30000)


def _merge_fact_updates(case_data: dict, extracted_facts: dict) -> tuple[dict, dict]:
    fact_sheet = remove_legacy_derived_assumptions(case_data.get("fact_sheet") or {})
    if extracted_facts:
        fact_sheet.update(extracted_facts)

    derived_facts = derive_fact_sheet_values(fact_sheet, _case_budget(case_data))
    if derived_facts:
        fact_sheet.update(derived_facts)

    return fact_sheet, derived_facts


def _is_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _submitted_file_urls(value: Any) -> list[str]:
    """Extract evidence file URLs from raw strings or frontend upload payloads."""
    urls: list[str] = []

    if _is_url(value):
        urls.append(value)
    elif isinstance(value, dict):
        for key in ("url", "download_url", "downloadUrl"):
            if _is_url(value.get(key)):
                urls.append(value[key])

        for key in ("uploads", "files"):
            nested = value.get(key)
            if isinstance(nested, list):
                for item in nested:
                    urls.extend(_submitted_file_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_submitted_file_urls(item))

    deduped = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def _parsed_file_summaries(parsed_files: list[dict]) -> list[str]:
    summaries = []
    for item in parsed_files:
        if item.get("type") == "text" and item.get("text"):
            summaries.append(str(item["text"])[:15000])
        elif item.get("type") == "image_url":
            summaries.append("[Uploaded image evidence attached for AI vision analysis.]")
    return summaries


def _submission_for_fact_analysis(submitted_value: Any, parsed_files: list[dict]) -> Any:
    summaries = _parsed_file_summaries(parsed_files)
    if not summaries:
        return submitted_value
    return {
        "submitted_value": submitted_value,
        "parsed_file_evidence": summaries,
    }


def _task_submission_payload(
    task_id: str,
    task_data: dict,
    submitted_value: Any,
    extracted_facts: dict,
    derived_facts: dict,
    parsed_files: list[dict] | None = None,
) -> dict:
    payload = {
        "task_completed": task_id,
        "task_title": task_data.get("title"),
        "task_description": task_data.get("description"),
        "submitted_value": submitted_value,
        "extracted_facts": extracted_facts,
        "derived_facts": derived_facts,
    }
    summaries = _parsed_file_summaries(parsed_files or [])
    if summaries:
        payload["parsed_file_evidence"] = summaries
    return payload


def _task_submission_message(
    task_id: str,
    task_data: dict,
    submitted_value: Any,
    extracted_facts: dict,
    derived_facts: dict,
    parsed_files: list[dict] | None = None,
) -> dict:
    return {
        "role": "user",
        "content": json.dumps(
            _task_submission_payload(
                task_id,
                task_data,
                submitted_value,
                extracted_facts,
                derived_facts,
                parsed_files,
            )
        ),
    }


def _task_submission_agent_message(
    task_id: str,
    task_data: dict,
    submitted_value: Any,
    extracted_facts: dict,
    derived_facts: dict,
    parsed_files: list[dict],
) -> dict:
    if not parsed_files:
        return _task_submission_message(
            task_id,
            task_data,
            submitted_value,
            extracted_facts,
            derived_facts,
        )

    return {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    _task_submission_payload(
                        task_id,
                        task_data,
                        submitted_value,
                        extracted_facts,
                        derived_facts,
                        parsed_files,
                    )
                ),
            },
            *parsed_files,
        ],
    }


def _complete_calendar_event(task_data: dict, task_id: str) -> None:
    calendar_event_id = task_data.get("calendar_event_id")
    if not calendar_event_id:
        return

    try:
        from app.integrations.google_calendar import complete_task_event

        complete_task_event(calendar_event_id, task_data.get("title", task_id))
    except Exception:
        logger.exception("Calendar complete failed for task_id=%s.", task_id)


def _delete_calendar_event(task_data: dict, task_id: str) -> None:
    calendar_event_id = task_data.get("calendar_event_id")
    if not calendar_event_id:
        return

    try:
        from app.integrations.google_calendar import delete_task_event

        delete_task_event(calendar_event_id)
    except Exception:
        logger.exception("Calendar delete failed for task_id=%s.", task_id)


async def parse_submitted_file(url: str) -> dict:
    """Download an uploaded evidence file and convert it for AI review."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            file_bytes = resp.content
            content_type = resp.headers.get("Content-Type", "").lower()

        url_lower = url.lower()

        if "image" in content_type or any(ext in url_lower for ext in [".jpg", ".jpeg", ".png", ".webp"]):
            b64_encoded = base64.b64encode(file_bytes).decode("utf-8")
            mime = content_type if "image" in content_type else "image/jpeg"
            return {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64_encoded}"},
            }

        if "pdf" in content_type or ".pdf" in url_lower:
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return {
                "type": "text",
                "text": f"[Extracted Text from Uploaded PDF Document]:\n{text[:15000]}",
            }

        if (
            "csv" in content_type
            or "excel" in content_type
            or "spreadsheet" in content_type
            or any(ext in url_lower for ext in [".csv", ".xlsx", ".xls"])
        ):
            import pandas as pd

            if ".csv" in url_lower or "csv" in content_type:
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            text = df.to_string(index=False)
            return {
                "type": "text",
                "text": f"[Extracted Data from Uploaded Spreadsheet]:\n{text[:15000]}",
            }

        return {"type": "text", "text": f"User submitted a file here: {url}"}

    except Exception as exc:
        logger.warning("File parse failed for task evidence url=%s error=%s", url, exc)
        return {
            "type": "text",
            "text": f"User submitted a file, but the system could not read it. URL: {url}",
        }


async def _parse_submitted_files(submitted_value: Any) -> list[dict]:
    parsed_files = []
    for url in _submitted_file_urls(submitted_value):
        parsed_files.append(await parse_submitted_file(url))
    return parsed_files


async def _analyze_task_submission(
    case_id: str,
    case_data: dict,
    task_data: dict,
    submitted_value: Any,
    extracted_facts: dict,
) -> dict:
    fact_sheet = remove_legacy_derived_assumptions(case_data.get("fact_sheet") or {})
    fact_sheet.update(extracted_facts or {})
    return await analyze_message_facts(
        {
            "task_title": task_data.get("title"),
            "task_description": task_data.get("description"),
            "submitted_value": submitted_value,
        },
        fact_sheet,
        {
            "case_id": case_id,
            "idea": case_data.get("description") or case_data.get("title") or "",
            "location": case_data.get("target_location") or "",
            "budget_myr": _case_budget(case_data),
            "source": "task_submission",
        },
    )


@router.get("/{case_id}")
async def list_tasks(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
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
    user: dict = Depends(get_current_user),
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
    user: dict = Depends(get_current_user),
):
    """Update a task's status and merge submitted evidence into AI memory."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document(task_id)
    task_doc = task_ref.get()

    if not task_doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")

    task_data = task_doc.to_dict()
    update_fields = {"status": data.status, "updated_at": datetime.utcnow()}
    extracted_facts = {}
    derived_facts = {}
    case_update = None

    if data.submitted_value is not None:
        update_fields["submitted_value"] = data.submitted_value

    if data.status == "completed":
        update_fields["completed_at"] = datetime.utcnow()
        _complete_calendar_event(task_data, task_id)

        if data.submitted_value is not None:
            parsed_files = await _parse_submitted_files(data.submitted_value)
            submitted_for_analysis = _submission_for_fact_analysis(data.submitted_value, parsed_files)
            extracted_facts = extract_required_facts_from_task_submission(task_data, submitted_for_analysis)
            case_data = case_ref.get().to_dict() or {}
            fact_analysis = await _analyze_task_submission(
                case_id,
                case_data,
                task_data,
                submitted_for_analysis,
                extracted_facts,
            )
            ai_extracted_facts = fact_analysis.get("structured_facts") or {}
            if ai_extracted_facts:
                extracted_facts.update(ai_extracted_facts)
                update_fields["ai_extracted_facts"] = ai_extracted_facts
            if extracted_facts:
                update_fields["extracted_facts"] = extracted_facts
            if parsed_files:
                update_fields["parsed_file_evidence"] = _parsed_file_summaries(parsed_files)
            if fact_analysis.get("structured_fact_items"):
                update_fields["fact_analysis"] = fact_analysis["structured_fact_items"]
            if fact_analysis.get("supporting_facts"):
                update_fields["supporting_facts"] = fact_analysis["supporting_facts"]
            if fact_analysis.get("evidence_assessment"):
                update_fields["evidence_assessment"] = fact_analysis["evidence_assessment"]

            fact_sheet, derived_facts = _merge_fact_updates(case_data, extracted_facts)
            if derived_facts:
                update_fields["derived_facts"] = derived_facts

            ai_messages = list(case_data.get("ai_messages") or [])
            ai_messages.append(
                _task_submission_message(
                    task_id,
                    task_data,
                    data.submitted_value,
                    extracted_facts,
                    derived_facts,
                    parsed_files,
                )
            )
            case_update = {
                "fact_sheet": fact_sheet,
                "ai_messages": ai_messages,
                "updated_at": datetime.utcnow(),
            }
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
    elif data.status == "skipped":
        _delete_calendar_event(task_data, task_id)

    task_ref.update(update_fields)
    if case_update:
        case_ref.update(case_update)

    updated = task_ref.get().to_dict()
    return _task_response(task_id, updated, case_id)


@router.delete("/{case_id}/{task_id}")
async def delete_task(
    case_id: str,
    task_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Delete a task."""
    case_ref = _get_case_ref(db, case_id, user["uid"])
    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document(task_id)
    task_doc = task_ref.get()

    if not task_doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")

    task_ref.delete()
    return {"status": "success"}


@router.get("/{case_id}/tasks")
async def list_tasks_compat(
    case_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Backward-compatible alias: GET /tasks/{case_id}/tasks."""
    return await list_tasks(case_id, db, user)


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    data: dict,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
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

    case_ref = _get_case_ref(db, case_id, user["uid"])

    submitted_value = data.get("submitted_value", data.get("submittedValue"))
    parsed_files = await _parse_submitted_files(submitted_value)
    submitted_for_analysis = _submission_for_fact_analysis(submitted_value, parsed_files)
    task_data = task_doc.to_dict()
    _complete_calendar_event(task_data, task_id)

    extracted_facts = extract_required_facts_from_task_submission(task_data, submitted_for_analysis)
    case_data = case_ref.get().to_dict() or {}
    fact_analysis = await _analyze_task_submission(
        case_id,
        case_data,
        task_data,
        submitted_for_analysis,
        extracted_facts,
    )
    ai_extracted_facts = fact_analysis.get("structured_facts") or {}
    if ai_extracted_facts:
        extracted_facts.update(ai_extracted_facts)
    fact_sheet, derived_facts = _merge_fact_updates(case_data, extracted_facts)

    task_update = {
        "status": "completed",
        "submitted_value": submitted_value,
        "completed_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    if ai_extracted_facts:
        task_update["ai_extracted_facts"] = ai_extracted_facts
    if extracted_facts:
        task_update["extracted_facts"] = extracted_facts
    if parsed_files:
        task_update["parsed_file_evidence"] = _parsed_file_summaries(parsed_files)
    if fact_analysis.get("structured_fact_items"):
        task_update["fact_analysis"] = fact_analysis["structured_fact_items"]
    if fact_analysis.get("supporting_facts"):
        task_update["supporting_facts"] = fact_analysis["supporting_facts"]
    if fact_analysis.get("evidence_assessment"):
        task_update["evidence_assessment"] = fact_analysis["evidence_assessment"]
    if derived_facts:
        task_update["derived_facts"] = derived_facts
    task_doc.reference.update(task_update)

    from app.ai.orchestrator import run_agent_turn
    from app.ai.schemas import BusinessCase as AICase

    ai_case = AICase(
        id=case_id,
        idea=case_data.get("description") or case_data.get("title") or "",
        location=case_data.get("target_location") or "",
        budget_myr=_case_budget(case_data),
        phase=case_data.get("ai_phase") or "EVIDENCE",
        fact_sheet=fact_sheet,
        messages=case_data.get("ai_messages") or [],
    )

    ai_case.messages.append(
        _task_submission_agent_message(
            task_id,
            task_data,
            submitted_value,
            extracted_facts,
            derived_facts,
            parsed_files,
        )
    )

    case_ref.update({
        "ai_phase": ai_case.phase,
        "fact_sheet": ai_case.fact_sheet,
        "ai_messages": ai_case.messages,
        **({
            "supporting_facts": merge_supporting_facts(
                case_data.get("supporting_facts") or [],
                fact_analysis.get("supporting_facts") or [],
            )
        } if fact_analysis.get("supporting_facts") else {}),
        **({
            "evidence_assessment": {
                **fact_analysis["evidence_assessment"],
                "updated_at": datetime.utcnow(),
            }
        } if fact_analysis.get("evidence_assessment") else {}),
        "updated_at": datetime.utcnow(),
    })

    updated_case, _ = await run_agent_turn(ai_case)

    case_ref.update({
        "ai_phase": updated_case.phase,
        "fact_sheet": updated_case.fact_sheet,
        "ai_messages": updated_case.messages,
        "updated_at": datetime.utcnow(),
    })

    return {"status": "success", "task_id": task_id}


@router.post("/{task_id}/skip")
async def skip_task(
    task_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
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

    task_data = task_doc.to_dict()
    _delete_calendar_event(task_data, task_id)

    task_doc.reference.update({
        "status": "skipped",
        "updated_at": datetime.utcnow(),
    })
    return {"status": "success"}
