"""
Google Places API Integration

Retrieves nearby competitor and area context data (SAD Section 7).
Results are cached in api_place_results table (SAD Section 17).
"""

import httpx
from app.config import settings

# What is google_places.py for?
# The google_places.py file defines a client for integrating with the Google Places API. This client will provide methods for searching nearby places based on latitude and longitude, retrieving detailed information about specific places, and performing text-based searches for places. This integration will allow us to gather contextual information about competitors and landmarks around the F&B locations in our business cases, which can be valuable for analysis and reporting. Additionally, we will implement caching of API results in the api_place_results table to improve performance and reduce redundant API calls, as outlined in SAD Section 17.

class GooglePlacesClient:
    """Client for Google Places API."""

    def __init__(self, api_key: str | None = None, http_client_factory=None):
        self.api_key = api_key if api_key is not None else settings.GOOGLE_PLACES_API_KEY
        self.http_client_factory = http_client_factory or httpx.AsyncClient

    async def nearby_search(self, latitude: float, longitude: float, radius: int = 1000, place_type: str = "restaurant"):
        """Search for nearby places (competitors, landmarks)."""
        if latitude is None or longitude is None or not self.api_key:
            return []
        data = await self._get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            {
                "location": f"{latitude},{longitude}",
                "radius": radius,
                "type": place_type,
                "key": self.api_key,
            },
        )
        return [self._serialize_place(place) for place in data.get("results", [])]

    async def get_place_details(self, place_id: str):
        """Get detailed info for a specific place."""
        if not place_id or not self.api_key:
            return None
        data = await self._get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            {
                "place_id": place_id,
                "fields": (
                    "place_id,name,formatted_address,geometry,rating,"
                    "user_ratings_total,price_level,opening_hours,types,reviews"
                ),
                "key": self.api_key,
            },
        )
        result = data.get("result")
        return self._serialize_place(result) if result else None

    async def text_search(self, query: str, location: str = None):
        """Search places by text query (e.g., 'western food near Li Villas')."""
        if not query or not self.api_key:
            return []
        params = {"query": query, "key": self.api_key}
        if location:
            params["location"] = location
        data = await self._get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params,
        )
        return [self._serialize_place(place) for place in data.get("results", [])]

    async def _get(self, url: str, params: dict) -> dict:
        async with self.http_client_factory(timeout=15.0) as client:
            response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("status") not in {None, "OK", "ZERO_RESULTS"}:
            raise httpx.HTTPStatusError(
                f"Google Places API returned {data.get('status')}",
                request=response.request,
                response=response,
            )
        return data

    @staticmethod
    def _serialize_place(place: dict | None) -> dict:
        place = place or {}
        geometry = place.get("geometry", {})
        location = geometry.get("location", {})
        return {
            "place_id": place.get("place_id"),
            "name": place.get("name"),
            "address": place.get("formatted_address") or place.get("vicinity"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "place_type": ", ".join(place.get("types", [])[:3]),
            "rating": place.get("rating"),
            "review_count": place.get("user_ratings_total"),
            "price_level": place.get("price_level"),
            "raw_data": place,
        }
