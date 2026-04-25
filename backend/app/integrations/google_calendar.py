# app/integrations/calendar.py
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

CALENDAR_ID = "f63e6201a772661da1d482c40d1aefc3e302714213ddd41002e9f86265cf7958@group.calendar.google.com"
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
SERVICE_ACCOUNT_FILE = "firebase-service-account.json"


def _get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=credentials)


def create_task_event(title: str, description: str = "") -> str:
    """Create a Google Calendar event for a task. Returns the event_id."""
    service = _get_calendar_service()

    start = datetime.utcnow() + timedelta(days=7)
    end = start + timedelta(hours=1)

    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat() + "Z", "timeZone": "Asia/Kuala_Lumpur"},
        "end":   {"dateTime": end.isoformat() + "Z",   "timeZone": "Asia/Kuala_Lumpur"},
    }

    result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    return result["id"]


def complete_task_event(event_id: str, title: str) -> None:
    """Mark a calendar event as done by updating its title."""
    service = _get_calendar_service()
    event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
    event["summary"] = f"✅ {title}"
    service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=event).execute()


def delete_task_event(event_id: str) -> None:
    """Delete a calendar event when task is skipped."""
    service = _get_calendar_service()
    service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()