"""Tests for external integration clients."""

import pytest

from app.integrations.glm_client import GLMClient
from app.integrations.google_calendar import GoogleCalendarClient
from app.integrations.google_places import GooglePlacesClient


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.request = None

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeAsyncClient:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.response

    async def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.response


def _factory(response: FakeResponse):
    return lambda **_: FakeAsyncClient(response)


@pytest.mark.asyncio
async def test_glm_client():
    response = FakeResponse(
        {"choices": [{"message": {"content": "Use a smaller pilot location."}}]}
    )
    client = GLMClient(
        api_key="key",
        base_url="https://glm.example",
        model="glm-test",
        http_client_factory=_factory(response),
    )

    result = await client.chat_completion([{"role": "user", "content": "Analyze"}])

    assert result == "Use a smaller pilot location."


@pytest.mark.asyncio
async def test_google_places():
    response = FakeResponse(
        {
            "status": "OK",
            "results": [
                {
                    "place_id": "place-1",
                    "name": "Cafe One",
                    "vicinity": "Kuala Lumpur",
                    "geometry": {"location": {"lat": 3.1, "lng": 101.6}},
                    "types": ["restaurant", "food"],
                    "rating": 4.2,
                    "user_ratings_total": 18,
                }
            ],
        }
    )
    client = GooglePlacesClient(
        api_key="key",
        http_client_factory=_factory(response),
    )

    places = await client.nearby_search(3.1, 101.6)

    assert places[0]["place_id"] == "place-1"
    assert places[0]["latitude"] == 3.1


@pytest.mark.asyncio
async def test_google_calendar():
    client = GoogleCalendarClient(
        client_id="calendar-client",
        client_secret="calendar-secret",
        redirect_uri="http://localhost/callback",
    )

    auth_url = await client.get_auth_url()

    assert "calendar-client" in auth_url
    assert "calendar.events" in auth_url
