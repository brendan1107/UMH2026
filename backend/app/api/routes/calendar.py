"""
Google Calendar Routes

Allows users to save AI-generated investigation tasks
to their Google Calendar for scheduling site visits,
competitor reviews, and evidence collection.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()


@router.post("/auth/callback")
async def calendar_auth_callback():
    """Handle Google OAuth2 callback for Calendar access."""
    # TODO: Exchange auth code for tokens
    pass


@router.post("/tasks/{task_id}/schedule")
async def schedule_task(task_id: str, db: Session = Depends(get_db)):
    """Add an investigation task as a Google Calendar event."""
    # TODO: Create calendar event from task details
    pass


@router.delete("/events/{event_id}")
async def remove_event(event_id: str):
    """Remove a scheduled event from Google Calendar."""
    # TODO: Delete calendar event
    pass
