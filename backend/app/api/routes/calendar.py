"""
Google Calendar Routes

Allows users to save AI-generated investigation tasks
to their Google Calendar for scheduling site visits,
competitor reviews, and evidence collection.

Scheduling metadata is persisted in Firestore even when
the real Google Calendar API is not yet integrated.

Firestore path: business_cases/{case_id}/scheduled_events/{event_id}
"""
# This file defines API endpoints for integrating with Google Calendar.
# The main functionalities include:
# - Handling the OAuth2 callback to obtain access tokens for Google Calendar.
# - Scheduling investigation tasks as calendar events, allowing users to set reminders
#  for site visits, competitor reviews, and evidence collection.
# - Removing scheduled events from Google Calendar if a task is canceled or completed.
# The endpoints defined in this file will interact with the Google Calendar API to 
# create, manage, and delete calendar events based on the investigation tasks generated
#  by the AI. This integration helps users stay organized and ensures they don't miss 
# important deadlines for their business investigations.

# For example, when the AI identifies a task that requires a site visit, the user can
# choose to schedule that task on their Google Calendar directly from the app, which 
# will create a calendar event with the task details and a reminder. If the user 
# completes the task or decides to skip it, they can remove the event from their 
# calendar to keep it up to date with their investigation progress. This seamless 
# integration with Google Calendar enhances the user experience and helps users manage 
# their time effectively as they work through their F&B business cases.

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.dependencies import get_current_user
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()
logger = logging.getLogger(__name__)

TASKS_SUBCOLLECTION = "tasks"
EVENTS_SUBCOLLECTION = "scheduled_events"


class ScheduleRequest(BaseModel):
    """Request body for scheduling a task."""
    caseId: str
    title: Optional[str] = None
    date: str  # ISO date string e.g. "2026-05-01"
    time: Optional[str] = "09:00"
    notes: Optional[str] = None


@router.post("/auth/callback")
async def calendar_auth_callback():
    """Handle Google OAuth2 callback for Calendar access."""
    # TODO: Exchange auth code for tokens when Google Calendar API is integrated
    return {"status": "not_implemented", "message": "Google Calendar OAuth not yet configured"}


@router.post("/tasks/{task_id}/schedule")
async def schedule_task(
    task_id: str,
    data: ScheduleRequest,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Schedule a task and persist scheduling metadata in Firestore.

    The actual Google Calendar event creation is mocked for now.
    Scheduling metadata is always stored in Firestore.
    """
    case_id = data.caseId
    case_ref = db.collection("business_cases").document(case_id)

    # Try to find and update the task status to 'scheduled'
    task_ref = case_ref.collection(TASKS_SUBCOLLECTION).document(task_id)
    task_doc = task_ref.get()

    task_title = data.title or "Scheduled Task"

    if task_doc.exists:
        task_data = task_doc.to_dict()
        task_title = data.title or task_data.get("title", "Scheduled Task")
        task_ref.update({
            "status": "scheduled",
            "updated_at": datetime.utcnow(),
        })
        logger.info("Updated task %s status to 'scheduled'.", task_id)
    else:
        logger.warning(
            "Task %s not found under case %s. "
            "Storing scheduling metadata anyway (demo mode).",
            task_id, case_id,
        )

    # TODO: Create real Google Calendar event here when API is integrated.
    # For now, generate a mock calendar event ID.
    mock_calendar_event_id = f"mock-gcal-{uuid.uuid4().hex[:12]}"

    now = datetime.utcnow()
    event_dict = {
        "task_id": task_id,
        "case_id": case_id,
        "title": task_title,
        "date": data.date,
        "time": data.time,
        "notes": data.notes,
        "status": "scheduled",
        "calendar_event_id": mock_calendar_event_id,
        "created_at": now,
    }

    event_ref = case_ref.collection(EVENTS_SUBCOLLECTION).document()
    event_ref.set(event_dict)

    event_dict["id"] = event_ref.id
    return snake_dict_to_camel(event_dict)


@router.delete("/events/{event_id}")
async def remove_event(
    event_id: str,
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Remove a scheduled event from Firestore (and Google Calendar when integrated)."""
    # Use collection group query since we don't have case_id in path
    events_query = (
        db.collection_group(EVENTS_SUBCOLLECTION)
        .where(firestore.FieldPath.document_id(), "==", event_id)
        .stream()
    )

    event_doc = None
    for doc in events_query:
        event_doc = doc
        break

    if not event_doc:
        raise HTTPException(status_code=404, detail="Scheduled event not found")

    # TODO: Delete the actual Google Calendar event when API is integrated
    event_doc.reference.delete()
    return {"status": "success"}
