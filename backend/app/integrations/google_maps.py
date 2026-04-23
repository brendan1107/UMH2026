"""
Google Maps / Geocoding API Integration

Location normalization, geocoding, and map display support (SAD Section 7).
"""

import httpx
from app.config import settings


class GoogleMapsClient:
    """Client for Google Maps and Geocoding APIs."""

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY

    async def geocode(self, address: str):
        """Convert address to latitude/longitude coordinates."""
        # TODO: Call Geocoding API
        pass

    async def reverse_geocode(self, latitude: float, longitude: float):
        """Convert coordinates to human-readable address."""
        # TODO: Call Reverse Geocoding API
        pass

    async def get_directions(self, origin: str, destination: str):
        """Get transit/driving directions between two points."""
        # TODO: Call Directions API (useful for accessibility analysis)
        pass
