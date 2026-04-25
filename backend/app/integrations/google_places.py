import httpx
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

class GooglePlacesClient:
    """Client for Google Places API (New/v1)."""

    def __init__(self):
        self.api_key = settings.GOOGLE_PLACES_API_KEY
        self.base_url = "https://places.googleapis.com/v1"

    async def resolve_location_text(self, query: str):
        """
        Resolves a text query to a specific place with coordinates using searchText (v1).
        """
        if not self.api_key:
            logger.warning("GOOGLE_PLACES_API_KEY is missing; cannot resolve location.")
            return None

        url = f"{self.base_url}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.googleMapsUri"
        }
        payload = {"textQuery": query}

        async with httpx.AsyncClient() as client:
            logger.info(f"Resolving location: '{query}' via searchText (v1)")
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if data.get("places"):
                place = data["places"][0]
                lat = float(place["location"]["latitude"])
                lng = float(place["location"]["longitude"])
                place_id = place.get("id")
                
                logger.info(f"Resolved '{query}' to '{place['displayName']['text']}' at ({lat}, {lng})")
                return {
                    "name": place["displayName"]["text"],
                    "address": place.get("formattedAddress"),
                    "lat": lat,
                    "lng": lng,
                    "place_id": place_id,
                    "google_maps_url": place.get("googleMapsUri"),
                    "rating": place.get("rating", 0),
                    "review_count": place.get("userRatingCount", 0)
                }
        return None

    async def search_nearby_v1(self, latitude: float, longitude: float, radius: float = 1000.0, included_types: list = None):
        """
        Search for nearby places using searchNearby (v1).
        Max 20 results per request.
        """
        if not self.api_key:
            return []

        url = f"{self.base_url}/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.googleMapsUri,places.primaryType,places.types"
        }
        
        payload = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": radius
                }
            },
            "maxResultCount": 20,
            "rankPreference": "DISTANCE"
        }
        
        if included_types:
            payload["includedTypes"] = included_types

        async with httpx.AsyncClient() as client:
            logger.info(f"Nearby search (v1) at ({latitude}, {longitude}) with types {included_types}")
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            results = data.get("places", [])
            logger.info(f"Nearby search (v1) returned {len(results)} results")
            return results

    async def get_multi_category_competitors(self, latitude: float, longitude: float, radius: float = 1000.0):
        """
        Run multiple searches for different F&B categories and merge results.
        """
        # Google Places v1 Types: https://developers.google.com/maps/documentation/places/web-service/place-types
        categories = [
            ["cafe"],
            ["restaurant"],
            ["bakery"],
            ["coffee_shop"],
            ["fast_food_restaurant"],
            ["ice_cream_shop"],
            ["meal_takeaway"]
        ]
        
        tasks = [self.search_nearby_v1(latitude, longitude, radius, cat) for cat in categories]
        all_results = await asyncio.gather(*tasks)
        
        # Flatten and deduplicate by ID
        merged = {}
        for result_set in all_results:
            for place in result_set:
                merged[place["id"]] = place
        
        return list(merged.values())

    async def get_place_details(self, place_id: str):
        """Get detailed info for a specific place (Legacy support or v1)."""
        # For simplicity, keeping v1 details if needed, but searchNearby v1 usually returns enough
        if not self.api_key: return None
        url = f"{self.base_url}/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,location,rating,userRatingCount,googleMapsUri"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
        return None
