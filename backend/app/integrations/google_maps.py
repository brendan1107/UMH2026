"""
Google Maps / Geocoding API Integration

Location normalization, geocoding, and map display support (SAD Section 7).
"""
# What is google_maps.py for?
# The google_maps.py file defines a client for integrating with the Google Maps and Geocoding APIs. This client will provide methods for geocoding addresses (converting them to latitude/longitude coordinates), reverse geocoding (converting coordinates back to human-readable addresses), and getting directions between two points. These functionalities will be useful for normalizing location data in our business cases, analyzing accessibility for F&B locations, and providing map-based insights in our reports. By encapsulating the Google Maps interactions in this client, we can keep our code organized and make it easier to manage our location-based features across our application.

import httpx
from app.config import settings


class GoogleMapsClient:
    """Client for Google Maps and Geocoding APIs."""

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    async def geocode(self, address: str):
        """Convert address to latitude/longitude coordinates."""
        if not self.api_key:
            return None

        async with httpx.AsyncClient() as client:
            params = {
                "address": address,
                "key": self.api_key
            }
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                location = result["geometry"]["location"]
                return {
                    "lat": location["lat"],
                    "lng": location["lng"],
                    "formatted_address": result.get("formatted_address"),
                    "place_id": result.get("place_id")
                }
        return None

    async def reverse_geocode(self, latitude: float, longitude: float):
        """Convert coordinates to human-readable address."""
        if not self.api_key:
            return None

        async with httpx.AsyncClient() as client:
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self.api_key
            }
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                return data["results"][0].get("formatted_address")
        return None

    async def get_directions(self, origin: str, destination: str):
        """Get transit/driving directions between two points."""
        # Optional MVP: not strictly required by the prompt's core goal
        pass
