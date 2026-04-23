"""
Google Calendar API Integration

Allows users to save AI-generated investigation tasks to Google Calendar.
(PRD Section 4.2: Task-to-Action Workflow)

Fallback: allow manual copy of task details if Calendar fails (SAD Section 13).
"""

from app.config import settings


class GoogleCalendarClient:
    """Client for Google Calendar API."""

    def __init__(self):
        self.client_id = settings.GOOGLE_CALENDAR_CLIENT_ID
        self.client_secret = settings.GOOGLE_CALENDAR_CLIENT_SECRET

    async def get_auth_url(self) -> str:
        """Generate OAuth2 authorization URL for Calendar access."""
        # TODO: Build Google OAuth2 URL
        pass

    async def exchange_code(self, auth_code: str) -> dict:
        """Exchange authorization code for access/refresh tokens."""
        # TODO: Token exchange
        pass

    async def create_event(self, access_token: str, task: dict) -> str:
        """Create a calendar event from an investigation task."""
        # TODO: Create event, return event ID
        pass

    async def delete_event(self, access_token: str, event_id: str):
        """Delete a calendar event."""
        # TODO: Delete event
        pass
