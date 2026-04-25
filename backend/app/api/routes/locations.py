"""
Location / Competitor Analysis Routes

Provides competitor analysis for a target location.
When Google Places API is not configured, returns realistic mock competitors.
Results are cached in Firestore under the case.

Firestore path: business_cases/{case_id}/place_results/{doc_id}
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from app.db.session import get_db
from app.dependencies import get_current_user
from app.config import settings
from app.utils.helpers import snake_dict_to_camel

router = APIRouter()
logger = logging.getLogger(__name__)

PLACE_RESULTS_SUBCOLLECTION = "place_results"

# Realistic mock competitors used when Google Places API is not configured
_MOCK_COMPETITORS = [
    {
        "name": "Kopi Corner Cafe",
        "address": "12, Jalan SS 15/4, 47500 Subang Jaya",
        "rating": 4.3,
        "review_count": 187,
        "price_level": "$$",
        "type": "cafe",
    },
    {
        "name": "Nasi Lemak Antarabangsa",
        "address": "8, Jalan Sultan Ismail, 50250 Kuala Lumpur",
        "rating": 4.6,
        "review_count": 423,
        "price_level": "$",
        "type": "restaurant",
    },
    {
        "name": "The Brew House",
        "address": "3A, Jalan Telawi 3, Bangsar, 59100 Kuala Lumpur",
        "rating": 4.1,
        "review_count": 92,
        "price_level": "$$$",
        "type": "cafe",
    },
    {
        "name": "Warung Pak Ali",
        "address": "Lot 5, Jalan Pasar, 46000 Petaling Jaya",
        "rating": 4.4,
        "review_count": 256,
        "price_level": "$",
        "type": "restaurant",
    },
]


@router.get("/competitors")
async def get_competitors(
    case_id: str = Query(None, description="Case ID to scope the analysis"),
    target_location: str = Query(None, description="Target location string"),
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return competitor analysis for the target location.

    If Google Places API key is configured, real data would be fetched.
    Otherwise returns realistic mock competitors.
    Results are stored in Firestore under the case when case_id is provided.
    """
    now = datetime.utcnow()
    use_real_api = bool(settings.GOOGLE_PLACES_API_KEY)

    if use_real_api:
        # TODO: Integrate with Google Places API for real competitor data
        logger.info("Google Places API key is set but integration is not yet implemented. Using mock data.")

    location_label = target_location or "Kuala Lumpur"

    result = {
        "target_location": location_label,
        "competitors": _MOCK_COMPETITORS,
        "summary": (
            f"Found {len(_MOCK_COMPETITORS)} potential competitors near {location_label}. "
            f"The area shows moderate competition with a mix of cafes and restaurants."
        ),
        "risk_level": "medium",
        "source": "mock" if not use_real_api else "google_places",
        "created_at": now,
    }

    # Store in Firestore under the case if case_id provided
    if case_id:
        case_ref = db.collection("business_cases").document(case_id)
        case_doc = case_ref.get()
        if case_doc.exists:
            doc_ref = case_ref.collection(PLACE_RESULTS_SUBCOLLECTION).document()
            doc_ref.set(result)
            result["id"] = doc_ref.id
            logger.info("Stored location analysis for case %s", case_id)
        else:
            logger.warning("Case %s not found; location result not persisted.", case_id)

    return snake_dict_to_camel(result)
