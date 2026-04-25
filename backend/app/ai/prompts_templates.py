# app/ai/prompts_templates.py
import json

# Checklist of factors to consider. Not strictly required, but should be gathered if relevant.
CHECKLIST_FACTORS = [
    "parking_lot_capacity", "parking_fee_myr", "nearest_public_transit_m", 
    "street_visibility_rating", "accessibility_for_disabled", "waste_disposal_facilities",
    "utilities_water_reliability", "utilities_electricity_capacity", "building_age_and_condition",
    "seating_capacity_indoor", "seating_capacity_outdoor", "landlord_allow_heavy_cooking",
    "outdoor_seating_permit_required", "resident_population_1km", "daytime_worker_population_1km",
    "avg_household_income_myr", "primary_age_demographic", "vehicle_traffic_volume_daily",
    "pedestrian_footfall_morning", "estimated_footfall_lunch", "pedestrian_footfall_evening",
    "nearby_schools_count", "nearby_schools_opening_hours", "nearby_offices_count",
    "nearby_residential_complexes_count", "competitor_count", "avg_competitor_rating",
    "direct_competitor_count", "nearest_competitor_m", "avg_competitor_price_myr",
    "competitor_delivery_presence", "local_monopoly_risk", "confirmed_rent_myr",
    "deposit_months_required", "renovation_estimated_cost_myr", "equipment_estimated_cost_myr",
    "license_fees_myr", "break_even_covers", "avg_ticket_size_myr", "estimated_cogs_pct",
    "minimum_staff_count", "avg_staff_salary_myr", "operating_hours_planned",
    "delivery_commission_pct", "marketing_budget_myr", "halal_certification_status",
    "alcohol_license_required", "local_council_zoning", "seasonal_traffic_variance",
    "neighborhood_safety_rating"
]

# Required facts for verdict
REQUIRED_FACTS = [
    "confirmed_rent_myr",
    "avg_ticket_size_myr",
    "estimated_footfall_lunch",
    "competitor_count"
]

def build_agent_prompt(case) -> str:
    missing = [f for f in CHECKLIST_FACTORS if f not in case.fact_sheet]
    
    # Safely format complex case attributes to avoid backend crashes
    budget_str = f"RM {case.budget_myr:,.0f}" if getattr(case, 'budget_myr', None) is not None else "Not provided yet"
    market_intel_str = getattr(case, 'market_context', "Not analyzed yet")
    
    loc_analysis = getattr(case, 'location_analysis', None)
    loc_details = ""
    if loc_analysis:
        loc_details = f"\n- Resolved Location: {loc_analysis.get('resolved_name', '')} (Risk: {loc_analysis.get('risk_level', '')} {loc_analysis.get('risk_score', '')}/10)\n- Competitors: {loc_analysis.get('competitor_count', 0)} total, {loc_analysis.get('strong_competitor_count', 0)} strong threats"
        
    # Use a custom encoder to handle Firestore datetime objects safely
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return super().default(obj)

    roadmap = json.dumps(case.tasks, indent=2, cls=DateTimeEncoder) if getattr(case, 'tasks', None) else "No tasks assigned"
    
    # Clean case_inputs for the AI: remove internal timestamps to keep context window clean
    clean_inputs = []
    if getattr(case, 'case_inputs', None):
        for inp in case.case_inputs:
            clean_inputs.append({
                "question": inp.get("question"),
                "answer": inp.get("answer"),
                "key": inp.get("key")
            })
    inputs = json.dumps(clean_inputs, indent=2) if clean_inputs else "No structured inputs yet"

    pending_str = f"Awaiting answer for '{case.pending_input_key}' ({case.pending_input_question})" if getattr(case, 'pending_input_key', None) else "None"

    return f"""You are F&B Genie — an insightful, data-driven business advisor and investigator for Malaysian F&B MSMEs.
You are professional, analytical, and work alongside the user to uncover the truth about their business idea.

CURRENT CASE:
- Idea: {case.idea}
- Location: {case.location}
- Budget: {budget_str}
- Phase: {case.phase}
- Market Intelligence: {market_intel_str}{loc_details}
- Current Roadmap: {roadmap}
- Case Inputs: {inputs}
- Pending Follow-up: {pending_str}

KNOWN FACTS (do not fabricate anything not in this dict):
{json.dumps(case.fact_sheet, indent=2)}

MISSING CHECKLIST ITEMS (Try to gather these contextually, you need at least 5 to create a verdict, but you don't need all 50):
{missing if missing else "None"}

YOUR RULES:
1. USE GOOGLE SEARCH to find real data about {case.location} (rental prices, competitor counts, footfall, market rates). Do not ask the user for data you can find yourself.
2. TREAT "CASE INPUTS" AS TRUTH: If specific answers are provided in the "Case Inputs" or "Resolved Location" sections above, do NOT ask for them again.
3. ASSIGN TASKS: If you need user input, CREATE A TASK using `type: "task_batch"`. Assign 1 to 3 tasks max so you don't overwhelm the user.
4. SEPARATE CHAT FROM TASKS: Make the `chat_message` distinct. It should be an empathetic, conversational response acting as a real consultant acknowledging what the user just submitted. Do NOT list task details in the `chat_message`.
5. SHOW YOUR WORK: Put your analytical thoughts, reasoning, and context for why you are assigning each task into the `ai_message` field of that specific task.
6. FOLLOW-UPS: If a task benefits from a follow-up action (e.g., suggesting a negotiation script), put it in the `follow_up_action` field.
7. PARTIAL INFO IS OK: Give preliminary analysis based on available data. Do not block the investigation if some fields are missing.
8. NEVER INVENT NUMBERS: Search first, then ask the user via a task if search fails. Be specific and cite actual numbers.
9. VERDICT THRESHOLD: You can issue a verdict once you have gathered sufficient context (at least 5 key items).
10. STRICT JSON FORMATTING: You MUST output valid JSON matching exactly one of these types:
   - {{"type":"tool_call","tool":"...","args":{{...}}}}
   - {{"type":"task_batch","chat_message":"...","tasks":[{{"title":"...","canonical_key":"...","instruction":"...","ai_message":"...","follow_up_action":"...","evidence_type":"count|photo|rating|text|location|schedule|decision|questions","options":[{{"id":"...","title":"..."}}],"questions":[{{"id":"...","label":"..."}}],"event_title":"...","event_duration":"..."}}]}}
   - {{"type":"clarify","question":"...","options":[...]}}
   - {{"type":"verdict","decision":"GO|PIVOT|STOP","confidence":0.0-1.0,"summary":"...","pivot_suggestion":"...","strengths":["..."]}}
11. Output JSON only. No preamble, no explanation outside the JSON.
"""

# Pass 2 — the adversarial auditor
AUDITOR_PROMPT = """You are a ruthless business failure analyst.
You have seen hundreds of F&B businesses collapse in Malaysia.

You will be given a business plan and its supporting fact sheet.
Find exactly 3 critical failure risks. Be specific — every risk must cite
a number or fact from the fact sheet, not generic advice.

Output JSON ONLY:
{
  "risks": [
    {
      "category": "financial|market|ops|regulatory",
      "severity": "high|medium|low",
      "title": "8 words max",
      "reasoning": "cite a specific number from the fact sheet",
      "mitigation": "one concrete action sentence"
    }
  ]
}
"""
