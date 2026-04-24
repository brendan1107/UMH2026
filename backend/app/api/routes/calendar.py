"""Calendar scheduling routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.db.session import get_db
from app.dependencies import get_current_user
from app.integrations.google_calendar import GoogleCalendarClient

router = APIRouter()

STRICT_TASK_LOOKUP = False
_demo_schedules: dict[tuple[str, str, str], dict] = {}


class ScheduleTaskRequest(BaseModel):
    caseId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    notes: str | None = None
    accessToken: str | None = None
    timeZone: str = "UTC"

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be a valid YYYY-MM-DD date")
        return value

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError:
            raise ValueError("time must be a valid 24-hour HH:MM time")
        return value


class ScheduleTaskResponse(BaseModel):
    success: bool
    taskId: str
    status: str
    calendarEventId: str
    message: str


class CalendarAuthCodeRequest(BaseModel):
    code: str = Field(..., min_length=1)


class CalendarTokenRequest(BaseModel):
    accessToken: str = Field(..., min_length=1)


def _uid(current_user: dict) -> str:
    return current_user["uid"]


def _mock_event_id(task_id: str) -> str:
    suffix = task_id.removeprefix("task_")
    return f"mock_event_{suffix}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _store_demo_schedule(
    uid: str,
    task_id: str,
    payload: ScheduleTaskRequest,
    calendar_event_id: str,
    scheduled_for: str,
) -> None:
    _demo_schedules[(uid, payload.caseId, task_id)] = {
        "taskId": task_id,
        "caseId": payload.caseId,
        "userId": uid,
        "title": payload.title,
        "status": "scheduled",
        "calendarEventId": calendar_event_id,
        "scheduledFor": scheduled_for,
        "notes": payload.notes,
        "updatedAt": _utc_now(),
    }


def _schedule_success(task_id: str, calendar_event_id: str) -> dict:
    return {
        "success": True,
        "taskId": task_id,
        "status": "scheduled",
        "calendarEventId": calendar_event_id,
        "message": "Task scheduled successfully.",
    }


async def _create_calendar_event(
    task_id: str,
    payload: ScheduleTaskRequest,
    scheduled_for: str,
) -> str:
    if not payload.accessToken:
        return _mock_event_id(task_id)

    task_data = {
        "id": task_id,
        "title": payload.title,
        "description": payload.notes,
        "scheduledFor": scheduled_for,
        "timeZone": payload.timeZone,
    }
    try:
        return await GoogleCalendarClient().create_event(payload.accessToken, task_data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Calendar event creation failed: {exc}",
        )


@router.get("/auth/url")
async def get_calendar_auth_url(
    current_user: dict = Depends(get_current_user),
):
    """Return the Google OAuth URL needed to connect Calendar."""
    _uid(current_user)
    try:
        auth_url = await GoogleCalendarClient().get_auth_url()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return {"authUrl": auth_url}


@router.post("/auth/callback")
async def exchange_calendar_code(
    payload: CalendarAuthCodeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Exchange a Google OAuth code for Calendar tokens."""
    _uid(current_user)
    try:
        token_data = await GoogleCalendarClient().exchange_code(payload.code)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Calendar token exchange failed: {exc}",
        )
    return token_data


@router.post("/tasks/{task_id}/schedule", response_model=ScheduleTaskResponse)
async def schedule_task(
    task_id: str,
    payload: ScheduleTaskRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Schedule a task locally, or in Google Calendar when an access token is supplied."""
    uid = _uid(current_user)
    scheduled_for = f"{payload.date}T{payload.time}:00"
    calendar_event_id = await _create_calendar_event(task_id, payload, scheduled_for)

    try:
        if db is None:
            _store_demo_schedule(uid, task_id, payload, calendar_event_id, scheduled_for)
            return _schedule_success(task_id, calendar_event_id)

        task_ref = (
            db.collection("users")
            .document(uid)
            .collection("cases")
            .document(payload.caseId)
            .collection("tasks")
            .document(task_id)
        )
        task_snapshot = task_ref.get()

        if not task_snapshot.exists:
            if STRICT_TASK_LOOKUP:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found",
                )
            _store_demo_schedule(uid, task_id, payload, calendar_event_id, scheduled_for)
            return _schedule_success(task_id, calendar_event_id)

        task_ref.update(
            {
                "status": "scheduled",
                "calendarEventId": calendar_event_id,
                "scheduledFor": scheduled_for,
                "scheduleTitle": payload.title,
                "scheduleNotes": payload.notes,
                "scheduleTimeZone": payload.timeZone,
                "updatedAt": _utc_now(),
            }
        )

        return _schedule_success(task_id, calendar_event_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected calendar scheduling failure",
        )


@router.delete("/events/{event_id}")
async def delete_calendar_event(
    event_id: str,
    payload: CalendarTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    """Delete a Google Calendar event."""
    _uid(current_user)
    try:
        return await GoogleCalendarClient().delete_event(payload.accessToken, event_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Calendar event deletion failed: {exc}",
        )
