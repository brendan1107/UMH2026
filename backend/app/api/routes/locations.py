import logging
import math
import json
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from google.cloud import firestore

from app.db.session import get_db
from app.dependencies import get_current_user
from app.config import settings
from app.utils.helpers import snake_dict_to_camel
from app.integrations.google_maps import GoogleMapsClient
from app.integrations.google_places import GooglePlacesClient
from app.ai.glm_client import glm_call

router = APIRouter()
logger = logging.getLogger(__name__)

PLACE_RESULTS_SUBCOLLECTION = "place_results"

# Realistic mock competitors used when Google Places API is not configured
_MOCK_COMPETITORS = [
    {
        "id": "mock_1",
        "name": "Kopi Corner Cafe",
        "address": "12, Jalan SS 15/4, 47500 Subang Jaya",
        "category": "Cafe",
        "rating": 4.3,
        "review_count": 245,
        "lat": 3.076,
        "lng": 101.589,
        "distance_meters": 250,
        "risk_level": "Medium",
        "risk_score": 5,
        "insight": "Popular local spot with high morning traffic."
    },
    {
        "id": "mock_2",
        "name": "Nasi Lemak Antarabangsa",
        "address": "8, Jalan Sultan Ismail, 50250 Kuala Lumpur",
        "category": "Restaurant",
        "rating": 4.6,
        "review_count": 1280,
        "lat": 3.158,
        "lng": 101.701,
        "distance_meters": 450,
        "risk_level": "High",
        "risk_score": 9,
        "insight": "Well-known brand with very strong lunch crowd."
    }
]

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def calculate_competitor_risk_v2(distance, rating, review_count):
    """
    Balanced risk scoring (1-10) for a single competitor.
    Higher means more threatening.
    """
    # 1. Proximity threat (up to 4 pts)
    # Only close competitors are high risk
    if distance < 300: p_score = 4
    elif distance < 600: p_score = 2.5
    elif distance < 1000: p_score = 1
    else: p_score = 0.5
    
    # 2. Quality threat (up to 3 pts)
    if rating >= 4.5: r_score = 3
    elif rating >= 4.0: r_score = 2
    elif rating >= 3.5: r_score = 1
    else: r_score = 0
    
    # 3. Popularity threat (up to 3 pts)
    if review_count >= 500: pop_score = 3
    elif review_count >= 150: pop_score = 2
    elif review_count >= 50: pop_score = 1
    else: pop_score = 0
    
    # Combined score (max 10)
    # A competitor is only truly high risk (>=8) if they are CLOSE AND POPULAR AND HIGH-RATED.
    raw_score = p_score + r_score + pop_score
    
    if raw_score >= 8: level = "High"
    elif raw_score >= 5: level = "Medium"
    else: level = "Low"
    
    return round(raw_score, 1), level

def get_market_risk_analysis(competitors):
    """Balanced market risk analysis with opportunity perspective."""
    if not competitors:
        return 2.0, "Low", "No nearby competitors found. While risk is low, market demand must be verified through customer interest."

    # Identify strong threats: Close (<500m) AND well-rated (>=4.2) AND popular (>=100 reviews)
    strong_threats = [
        c for c in competitors 
        if c["distance_meters"] < 500 and c["rating"] >= 4.2 and c["review_count"] >= 100
    ]
    
    # Base score
    score = 3.0
    
    # Add risk for strong threats (max +4 pts)
    if len(strong_threats) >= 3: score += 4
    elif len(strong_threats) >= 2: score += 3
    elif len(strong_threats) >= 1: score += 1.5
    
    # Add density risk (max +2 pts)
    if len(competitors) > 20: score += 2
    elif len(competitors) > 10: score += 1
    elif len(competitors) > 5: score += 0.5
    
    # Cap score
    score = min(10, score)
    
    if score >= 7.0: level = "High"
    elif score >= 4.0: level = "Medium"
    else: level = "Low"
    
    # Business-friendly explanation
    if level == "High":
        explanation = (
            f"Market risk is {level} ({score}/10) due to a high density of established F&B venues. "
            f"We identified {len(strong_threats)} strong competitors within 500m. "
            "This confirms strong local demand, but success will require a highly differentiated concept or superior quality."
        )
    elif level == "Medium":
        explanation = (
            f"Market risk is {level} ({score}/10). There is healthy F&B activity in the area, suggesting consistent foot traffic. "
            f"With {len(strong_threats)} strong competitors nearby, there is room for a new player who can offer a unique value proposition."
        )
    else:
        explanation = (
            f"Market risk is {level} ({score}/10). The area has limited direct competition, which may represent an untapped opportunity. "
            "Focus should be on verifying whether the current lack of competition is due to low demand or a gap in the market."
        )
    
    return round(score, 1), level, explanation

def normalize_title(title: str) -> str:
    """Strictly normalize task title for deduplication."""
    # Remove punctuation, lowercase, trim
    return re.sub(r'[^a-z0-9]', '', title.lower().strip())

@router.get("/competitors")
async def get_competitors(
    case_id: str = Query(None, description="Case ID to scope the analysis"),
    target_location: str = Query(None, description="Target location string"),
    lat: float = Query(None, description="Latitude"),
    lng: float = Query(None, description="Longitude"),
    radius: int = Query(1000, description="Search radius in meters"),
    keyword: str = Query("cafe coffee restaurant food", description="Search keyword"),
    preview_only: bool = Query(False, description="If true, only resolve the location"),
    db: firestore.Client = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return competitor analysis for the target location."""
    now = datetime.utcnow()
    use_real_api = bool(settings.GOOGLE_PLACES_API_KEY)
    
    places_client = GooglePlacesClient()
    
    # Default KL Coordinates
    DEFAULT_LAT = 3.1390
    DEFAULT_LNG = 101.6869
    
    target_lat = lat
    target_lng = lng
    target_place_id = None
    target_google_maps_url = None
    target_rating = 0
    target_review_count = 0
    target_address = ""
    target_name = target_location or "Selected Location"
    
    source = "google_places" if use_real_api else "mock"
    fallback_reason = None
    diagnostics = {
        "radius": radius,
        "queries_run": [],
        "raw_result_count": 0,
        "deduped_count": 0,
        "filtered_count": 0,
        "source": source
    }

    try:
        if use_real_api:
            # 1. Resolve exact target location
            resolved = None
            if target_location:
                resolved = await places_client.resolve_location_text(target_location)
                if resolved:
                    target_lat = resolved["lat"]
                    target_lng = resolved["lng"]
                    target_address = resolved["address"]
                    target_name = resolved["name"]
                    target_place_id = resolved["place_id"]
                    target_google_maps_url = resolved["google_maps_url"]
                    target_rating = resolved.get("rating", 0)
                    target_review_count = resolved.get("review_count", 0)
            
            # Final fallback coordinates if resolution failed
            if target_lat is None or target_lng is None:
                target_lat, target_lng = DEFAULT_LAT, DEFAULT_LNG
                target_address = target_address or "Kuala Lumpur, Malaysia"
            
            if not target_google_maps_url:
                target_google_maps_url = f"https://www.google.com/maps/search/?api=1&query={target_lat},{target_lng}"

            # If preview_only, return early
            if preview_only:
                return snake_dict_to_camel({
                    "source": source,
                    "target_location": {
                        "name": target_name,
                        "lat": target_lat,
                        "lng": target_lng,
                        "address": target_address,
                        "place_id": target_place_id,
                        "google_maps_url": target_google_maps_url,
                        "rating": target_rating,
                        "review_count": target_review_count
                    },
                    "search_diagnostics": diagnostics
                })

            # 2. Multi-category search
            raw_places = await places_client.get_multi_category_competitors(target_lat, target_lng, float(radius))
            
            diagnostics["queries_run"] = ["cafe", "restaurant", "bakery", "coffee_shop", "fast_food_restaurant", "ice_cream_shop", "meal_takeaway"]
            diagnostics["raw_result_count"] = len(raw_places)
            diagnostics["deduped_count"] = len(raw_places)

            # 3. Filter and normalize
            competitors = []
            irrelevant_types = {
                "clothing_store", "furniture_store", "electronics_store", "school", 
                "real_estate_agency", "parking", "gas_station", "atm", "lodging", 
                "convenience_store", "church", "hospital", "bank"
            }

            for p in raw_places:
                try:
                    p_id = p["id"]
                    if p_id == target_place_id: continue

                    # Irrelevant type filtering
                    p_types = set(p.get("types", []))
                    if p_types.intersection(irrelevant_types):
                        if not p_types.intersection({"restaurant", "cafe", "bakery", "coffee_shop"}):
                            continue

                    c_lat = float(p["location"]["latitude"])
                    c_lng = float(p["location"]["longitude"])
                    dist = calculate_haversine_distance(target_lat, target_lng, c_lat, c_lng)
                    
                    if dist > radius: continue

                    rating = float(p.get("rating", 0))
                    reviews = int(p.get("userRatingCount", 0))
                    
                    c_score, c_level = calculate_competitor_risk_v2(dist, rating, reviews)
                    
                    competitors.append({
                        "id": p_id,
                        "place_id": p_id,
                        "name": p["displayName"]["text"],
                        "category": p.get("primaryType", "F&B").replace("_", " ").capitalize(),
                        "types": p.get("types", []),
                        "rating": rating,
                        "review_count": reviews,
                        "address": p.get("formattedAddress"),
                        "lat": c_lat,
                        "lng": c_lng,
                        "distance_meters": int(dist),
                        "risk_level": c_level,
                        "risk_score": c_score,
                        "insight": f"Established {p.get('primaryType', 'venue').replace('_', ' ')} with healthy engagement.",
                        "google_maps_url": p.get("googleMapsUri") or f"https://www.google.com/maps/search/?api=1&query={c_lat},{c_lng}&query_place_id={p_id}"
                    })
                except Exception as e:
                    logger.debug(f"Skipping place {p.get('id')}: {e}")
                    continue
            
            diagnostics["filtered_count"] = len(competitors)
            competitors.sort(key=lambda x: x["distance_meters"])

        else:
            fallback_reason = "API_KEY_MISSING" if not settings.GOOGLE_PLACES_API_KEY else "DEV_FALLBACK"
            if preview_only:
                return snake_dict_to_camel({
                    "source": "mock",
                    "fallback_reason": fallback_reason,
                    "target_location": {
                        "name": "Jaya One (Mock Preview)",
                        "lat": DEFAULT_LAT,
                        "lng": DEFAULT_LNG,
                        "address": "72A, Jalan Universiti, 46200 Petaling Jaya",
                        "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={DEFAULT_LAT},{DEFAULT_LNG}",
                        "rating": 4.2,
                        "review_count": 850
                    },
                    "search_diagnostics": diagnostics
                })
            
            competitors = []
            for mc in _MOCK_COMPETITORS:
                mc_copy = mc.copy()
                mc_copy["google_maps_url"] = f"https://www.google.com/maps/search/?api=1&query={mc['lat']},{mc['lng']}"
                competitors.append(mc_copy)
            target_lat, target_lng = DEFAULT_LAT, DEFAULT_LNG
            target_address = "Mock Address, Kuala Lumpur"
            target_google_maps_url = f"https://www.google.com/maps/search/?api=1&query={target_lat},{target_lng}"

    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Location analysis failed.")

    # 4. Final Risk Analysis
    risk_score, risk_level, risk_explanation = get_market_risk_analysis(competitors)
    
    result = {
        "case_id": case_id,
        "source": source,
        "fallback_reason": fallback_reason,
        "analysis_mode": "gemini" if source == "google_places" else "fallback",
        "resolved_name": target_name,
        "resolved_address": target_address,
        "resolved_lat": target_lat,
        "resolved_lng": target_lng,
        "resolved_place_id": target_place_id,
        "resolved_google_maps_url": target_google_maps_url,
        "target_location": {
            "name": target_name,
            "lat": target_lat,
            "lng": target_lng,
            "address": target_address,
            "place_id": target_place_id,
            "google_maps_url": target_google_maps_url,
            "rating": target_rating,
            "review_count": target_review_count
        },
        "radius": radius,
        "competitors": competitors,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_explanation": risk_explanation,
        "summary": risk_explanation,
        "follow_up_questions": [
            f"Given the {risk_level} market risk, what is your primary strategy to attract customers?" if risk_level == "High" else "How do you plan to verify demand in this low-competition area?",
            "What is your unique value proposition compared to nearby competitors?",
            "What price range are you targeting for your main products?",
            "Are you targeting students, office workers, or residents?"
        ],
        "suggested_tasks": [
            {
                "title": "Analyze target audience",
                "description": "Clarify target audience based on nearby competitor profiles and local demographics.",
                "type": "answer_questions",
                "action_label": "Analyze Audience",
                "questions": [
                    "Who is your main target customer?",
                    "What problem does your business solve for them?",
                    "What is their estimated daily budget for F&B?"
                ]
            },
            {
                "title": "Review pricing strategy",
                "description": f"Evaluate if your pricing is competitive for a {risk_level} risk market.",
                "type": "review_ai_suggestions",
                "action_label": "Review Pricing"
            }
        ],
        "search_diagnostics": diagnostics,
        "created_at": now,
    }

    if case_id:
        try:
            case_ref = db.collection("business_cases").document(case_id)
            if case_ref.get().exists:
                doc_ref = case_ref.collection(PLACE_RESULTS_SUBCOLLECTION).document()
                doc_ref.set(result)
                result["id"] = doc_ref.id

                from app.services.case_service import CaseService
                service = CaseService()
                
                for task in result["suggested_tasks"]:
                    norm_title = normalize_title(task["title"])
                    
                    # Enhance specific tasks with the user's requested questions
                    t_type = task["type"]
                    t_questions = task.get("questions", [])
                    
                    if norm_title == normalize_title("Analyze Audience") or norm_title == normalize_title("Analyze target audience"):
                        t_type = "answer_questions"
                        t_questions = [
                            {"id": "target_group", "label": "Who is your main customer group?", "placeholder": "e.g. University students, office workers..."},
                            {"id": "value_prop", "label": "Why would they buy from you?", "placeholder": "e.g. Convenience, price, unique flavor..."},
                            {"id": "budget", "label": "What budget are they comfortable with?", "placeholder": "e.g. RM 5-10, RM 15-20..."}
                        ]
                    elif norm_title == normalize_title("Review pricing strategy"):
                        t_type = "answer_questions"
                        t_questions = [
                            {"id": "price_range", "label": "What is your expected drink price range?", "placeholder": "e.g. RM 8 - RM 12"},
                            {"id": "positioning", "label": "Are you positioning as budget, mid-range, or premium?", "placeholder": "e.g. Mid-range"},
                            {"id": "cost_per_unit", "label": "What is your estimated cost per drink?", "placeholder": "e.g. RM 3.50"},
                            {"id": "competitor_compare", "label": "What nearby competitor price are you comparing against?", "placeholder": "e.g. Starbucks (RM 16), Local Kiosk (RM 7)"}
                        ]

                    task_dict = {
                        "case_id": case_id,
                        "title": task["title"],
                        "description": task["description"],
                        "type": t_type,
                        "status": "pending",
                        "action_label": task["action_label"],
                        "canonical_key": service.derive_canonical_key(task["title"]),
                        "data": {"questions": t_questions},
                        "source": "location_analysis",
                        "location_analysis_id": doc_ref.id,
                    }
                    await service.upsert_task_by_canonical_key(db, case_id, task_dict)
                
                # 2. Update main case document with summary pointers
                strong_threats_list = [
                    c for c in competitors 
                    if c["distance_meters"] < 500 and c["rating"] >= 4.2 and c["review_count"] >= 100
                ]

                resolved_name = target_name or target_location
                resolved_address = target_address or ""
                resolved_google_maps_url = target_google_maps_url or f"https://www.google.com/maps/search/?api=1&query={target_lat},{target_lng}"

                case_ref.update({
                    "target_location": resolved_name, # Update main location field
                    "latest_location_analysis_id": doc_ref.id,
                    "latest_resolved_location_name": resolved_name,
                    "latest_resolved_address": resolved_address,
                    "latest_location_place_id": target_place_id,
                    "latest_location_lat": target_lat,
                    "latest_location_lng": target_lng,
                    "latest_location_google_maps_url": resolved_google_maps_url,
                    "latest_market_risk_score": risk_score,
                    "latest_market_risk_level": risk_level,
                    "latest_market_risk_explanation": risk_explanation,
                    "latest_market_summary": risk_explanation,
                    "latest_competitor_count": len(competitors),
                    "latest_strong_competitor_count": len(strong_threats_list),
                    "latest_analysis_updated_at": now,
                    "latestLocationAnalysisId": doc_ref.id,
                    "latestResolvedLocationName": resolved_name,
                    "latestResolvedAddress": resolved_address,
                    "latestLocationLat": target_lat,
                    "latestLocationLng": target_lng,
                    "latestMarketRiskScore": risk_score,
                    "latestMarketRiskLevel": risk_level,
                    "latestMarketSummary": risk_explanation,
                    "latestCompetitorCount": len(competitors),
                    "latestStrongCompetitorCount": len(strong_threats_list),
                    "updated_at": now
                })

                # ── Sync with case_inputs ──
                from app.services.case_service import CaseService
                await CaseService().save_case_input(db, case_id, "target_location", {
                    "answer": resolved_name,
                    "structured_answer": {
                        "name": resolved_name,
                        "address": resolved_address,
                        "lat": target_lat,
                        "lng": target_lng,
                        "place_id": target_place_id
                    },
                    "question": "What is your target location?",
                    "status": "submitted",
                    "source": "location_analysis"
                })

                # 3. Create a system/assistant message in chat
                session_ref = case_ref.collection("chat_sessions").document("default_session")
                if not session_ref.get().exists:
                    session_ref.set({
                        "case_id": case_id,
                        "title": "Default Session",
                        "created_at": now,
                        "updated_at": now
                    })

                # Deduplicate by resolved_name within the last 10 messages
                recent_msgs = session_ref.collection("messages").order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).get()
                is_duplicate = any(resolved_name in m.to_dict().get("content", "") for m in recent_msgs)
                
                if not is_duplicate:
                    analysis_content = f"I've analyzed {resolved_name}. I found {len(competitors)} nearby F&B competitors. Market risk is {risk_level} with a score of {risk_score}/10. I'll use this location intelligence for future recommendations."
                    session_ref.collection("messages").document().set({
                        "role": "assistant",
                        "content": analysis_content,
                        "related_location_analysis_id": doc_ref.id,
                        "ai_mode": "location_analysis",
                        "created_at": now
                    })
                    
                    # Also update ai_messages in the case document for context
                    case_ref.update({
                        "ai_messages": firestore.ArrayUnion([{
                            "role": "assistant",
                            "content": analysis_content,
                            "created_at": now.isoformat()
                        }])
                    })
        except Exception as e:
            logger.error(f"Firestore save error: {e}")

    return snake_dict_to_camel(result)
