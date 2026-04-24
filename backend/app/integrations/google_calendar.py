"""
Google Calendar API integration.

Provides OAuth URL generation, token exchange, event creation, and event
deletion for investigation tasks.
"""

from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.config import settings


class GoogleCalendarClient:
    """Client for Google Calendar API."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        http_client_factory=None,
    ):
        self.client_id = (
            client_id if client_id is not None else settings.GOOGLE_CALENDAR_CLIENT_ID
        )
        self.client_secret = (
            client_secret
            if client_secret is not None
            else settings.GOOGLE_CALENDAR_CLIENT_SECRET
        )
        self.redirect_uri = (
            redirect_uri
            if redirect_uri is not None
            else settings.GOOGLE_CALENDAR_REDIRECT_URI
        )
        self.http_client_factory = http_client_factory or httpx.AsyncClient

    async def get_auth_url(self) -> str:
        """Generate OAuth2 authorization URL for Calendar access."""
        if not self.client_id:
            raise RuntimeError("GOOGLE_CALENDAR_CLIENT_ID is not configured")
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar.events",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    async def exchange_code(self, auth_code: str) -> dict:
        """Exchange authorization code for access/refresh tokens."""
        if not auth_code:
            raise ValueError("Authorization code is required")
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Google Calendar OAuth credentials are not configured")

        payload = {
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=payload,
            )
        response.raise_for_status()
        return response.json()

    async def create_event(self, access_token: str, task: dict) -> str:
        """Create a calendar event from an investigation task."""
        if not access_token:
            raise ValueError("Google Calendar access token is required")

        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json=self._build_event_payload(task),
            )
        response.raise_for_status()
        return response.json()["id"]

    async def delete_event(self, access_token: str, event_id: str):
        """Delete a calendar event."""
        if not access_token:
            raise ValueError("Google Calendar access token is required")
        if not event_id:
            raise ValueError("Calendar event ID is required")

        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code not in {200, 204, 410}:
            response.raise_for_status()
        return {"deleted": True, "event_id": event_id}

    @staticmethod
    def _build_event_payload(task: dict) -> dict:
        title = task.get("title") or task.get("scheduleTitle") or "Investigation task"
        description = task.get("description") or task.get("notes") or ""
        scheduled_for = (
            task.get("scheduledFor")
            or task.get("start")
            or f"{task.get('date')}T{task.get('time', '09:00')}:00"
        )
        try:
            starts_at = datetime.fromisoformat(
                str(scheduled_for).replace("Z", "+00:00")
            )
        except ValueError:
            starts_at = datetime.utcnow().replace(
                hour=9,
                minute=0,
                second=0,
                microsecond=0,
            )
        ends_at = starts_at + timedelta(hours=1)
        time_zone = task.get("timeZone", "UTC")
        return {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": starts_at.isoformat(),
                "timeZone": time_zone,
            },
            "end": {
                "dateTime": ends_at.isoformat(),
                "timeZone": time_zone,
            },
        }
