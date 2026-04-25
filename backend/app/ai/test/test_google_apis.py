# test_google_apis.py
# Run with: python test_google_apis.py
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 1. Fix Python path so it can find the 'app' module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 2. Load .env BEFORE importing tools so the API key is injected
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

# 3. Import the actual live tools
from app.ai.tools import fetch_competitors, _geocode

async def run_live_tests():
    print("═══ LIVE GOOGLE API INTEGRATION TEST ═══\n")
    
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_PLACES_API_KEY not found in your .env file.")
        print("Please add it and try again.")
        return
        
    print(f"🔑 API Key detected: {api_key[:5]}...{api_key[-4:]}")

    target_location = "SS15, Subang Jaya"
    target_category = "cafe"

    # --- TEST 1: GEOCODING API ---
    print(f"\n── Test 1: Geocoding '{target_location}' ──")
    try:
        coords = await _geocode(target_location)
        print(f"✅ SUCCESS: Converted text to coordinates.")
        print(f"   Latitude : {coords['lat']}")
        print(f"   Longitude: {coords['lng']}")
    except Exception as e:
        print(f"❌ FAIL: Geocoding error -> {e}")
        print("Check if 'Geocoding API' is enabled in your Google Cloud Console.")
        return # Stop here if we can't get coordinates

    # --- TEST 2: PLACES API (NEARBY SEARCH) ---
    print(f"\n── Test 2: Places API for '{target_category}' ──")
    try:
        # We are using the exact function your AI will use
        result = await fetch_competitors(
            location=target_location, 
            category=target_category, 
            radius_km=1.0
        )
        print(f"✅ SUCCESS: Fetched live local data.")
        print(f"   Competitors Found : {result.count}")
        print(f"   Average Rating    : {result.avg_rating}/5.0")
        print(f"   Price Levels      : {result.price_levels}")
        
        if result.count == 0:
            print("\n⚠️ Note: 0 competitors found. This might mean the category is too specific, or the radius is too small.")
            
    except Exception as e:
        print(f"❌ FAIL: Places API error -> {e}")
        print("Check if 'Places API' is enabled in your Google Cloud Console.")

if __name__ == "__main__":
    asyncio.run(run_live_tests())