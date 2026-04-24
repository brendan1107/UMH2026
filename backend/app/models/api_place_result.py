"""
API Place Result Model (Firestore Document Schema)

Subcollection: business_cases/{case_id}/place_results/{place_id}
Caching reduces repeated external API usage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# What is api_place_result.py for?
# The api_place_result.py file defines a data model for representing the results of Google Places API calls that we cache in our Firestore database. This model, ApiPlaceResult, includes fields for storing relevant information about a place, such as its name, address, coordinates, rating, and the raw API response data. By defining this model, we can easily serialize and deserialize place results when storing them in Firestore and retrieving them for use in our application. This caching mechanism helps us reduce redundant API calls to Google Places, improving performance and ensuring that we have access to place data even if there are issues with the external API.

@dataclass
class ApiPlaceResult:
    """Firestore document schema for cached Google Places results."""
    id: str = ""
    case_id: str = ""
    place_id: Optional[str] = None  # Google Place ID
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_type: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[str] = None
    price_level: Optional[str] = None
    raw_data: Optional[str] = None  # Full JSON response
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "place_id": self.place_id,
            "name": self.name,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "place_type": self.place_type,
            "rating": self.rating,
            "review_count": self.review_count,
            "price_level": self.price_level,
            "raw_data": self.raw_data,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(doc_id: str, data: dict) -> "ApiPlaceResult":
        return ApiPlaceResult(
            id=doc_id,
            case_id=data.get("case_id", ""),
            place_id=data.get("place_id"),
            name=data.get("name"),
            address=data.get("address"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            place_type=data.get("place_type"),
            rating=data.get("rating"),
            review_count=data.get("review_count"),
            price_level=data.get("price_level"),
            raw_data=data.get("raw_data"),
            created_at=data.get("created_at", datetime.utcnow()),
        )

    SUBCOLLECTION = "place_results"
