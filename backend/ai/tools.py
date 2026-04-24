# Tool definitions

# ai/tools.py
import os, httpx
from ai.schemas import CompetitorResult, FootfallEstimate, BreakevenModel

PLACES_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

async def fetch_competitors(
    location: str,
    category: str = "nasi lemak",
    radius_km: float = 1.0,
) -> CompetitorResult:
    # Step 1: geocode the location string → lat,lng
    geo_resp = await _geocode(location)
    lat, lng = geo_resp["lat"], geo_resp["lng"]

    # Step 2: hit Google Places Nearby Search
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params={
                "location": f"{lat},{lng}",
                "radius": int(radius_km * 1000),
                "keyword": category,
                "type": "restaurant",
                "key": PLACES_KEY,
            }
        )
    places = resp.json().get("results", [])

    if not places:
        return CompetitorResult(count=0, avg_rating=0.0, nearest_m=9999, price_levels=[])

    ratings = [p["rating"] for p in places if "rating" in p]
    price_levels = [p.get("price_level", 2) for p in places]

    return CompetitorResult(
        count=len(places),
        avg_rating=round(sum(ratings) / len(ratings), 1) if ratings else 0.0,
        nearest_m=100,         # simplified — use distance matrix for accuracy
        price_levels=price_levels,
    )


async def estimate_footfall(
    location: str,
    time_of_day: str = "lunch",
) -> FootfallEstimate:
    # Google Places Popular Times is not in the free API
    # Use a reasonable heuristic based on place type counts
    # In a real system: integrate a third-party foot traffic API
    # For hackathon: use a calibrated estimate + note the assumption

    competitor_data = await fetch_competitors(location)

    # Heuristic: busier areas have more competitors
    base = 80
    if competitor_data.count > 10:
        base = 150
    elif competitor_data.count > 5:
        base = 110

    return FootfallEstimate(
        estimated_pax_per_hour=base,
        peak_hours=["12:00-14:00", "18:00-20:00"],
        confidence="medium",   # be honest about estimation
    )


async def calculate_breakeven(
    avg_price_myr: float,
    monthly_rent_myr: float,
    staff_count: int,
    avg_food_cost_pct: float = 0.35,
) -> BreakevenModel:
    # Staff cost estimate for Malaysia (rough)
    staff_cost = staff_count * 1800
    monthly_fixed = monthly_rent_myr + staff_cost + 500  # 500 = utilities

    # Revenue needed per month to cover fixed costs
    # Contribution margin = price × (1 - food_cost_pct)
    contribution_per_cover = avg_price_myr * (1 - avg_food_cost_pct)

    covers_per_month = monthly_fixed / contribution_per_cover
    covers_per_day   = covers_per_month / 26  # 26 trading days/month

    # Months to breakeven assuming startup costs = budget
    # Simplified: budget / monthly_profit_at_120%_capacity
    monthly_revenue_at_capacity = covers_per_day * 1.2 * 26 * avg_price_myr
    monthly_profit = monthly_revenue_at_capacity - monthly_fixed
    months = 9999 if monthly_profit <= 0 else round(30000 / monthly_profit, 1)

    return BreakevenModel(
        breakeven_covers_per_day=round(covers_per_day),
        months_to_breakeven=months,
        min_viable_revenue_myr=round(monthly_fixed, 0),
    )


async def _geocode(location: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": f"{location}, Malaysia", "key": PLACES_KEY}
        )
    result = resp.json()["results"][0]["geometry"]["location"]
    return {"lat": result["lat"], "lng": result["lng"]}


# Registry — agent uses this to dispatch tool calls
TOOL_REGISTRY = {
    "fetch_competitors":  fetch_competitors,
    "estimate_footfall":  estimate_footfall,
    "calculate_breakeven": calculate_breakeven,
}