#phase machine

# app/ai/state.py
from app.ai.schemas import BusinessCase, Phase, AgentOutput

# What facts each tool call writes to fact_sheet
TOOL_FACT_KEYS = {
    "fetch_competitors":   ["competitor_count", "avg_competitor_rating", "nearest_m"],
    "estimate_footfall":   ["estimated_footfall_lunch"],
    "calculate_breakeven": ["break_even_covers", "months_to_breakeven"],
}

# Phase transitions — when to move forward
def next_phase(case: BusinessCase, output: AgentOutput) -> Phase:
    current = case.phase

    if current == "INTAKE":
        return "MARKET_SCAN"

    if current == "MARKET_SCAN":
        # Move on when we have competitor data
        if "competitor_count" in case.fact_sheet:
            return "TASK_ASSIGNMENT"
        return "MARKET_SCAN"

    if current == "TASK_ASSIGNMENT":
        # Move to evidence collection after tasks are emitted
        if output.type == "field_task":
            return "EVIDENCE"
        return "TASK_ASSIGNMENT"

    if current == "EVIDENCE":
        # Check if all required facts are now present
        from app.ai.prompts_templates import REQUIRED_FACTS
        if all(k in case.fact_sheet for k in REQUIRED_FACTS):
            return "VERDICT"
        return "EVIDENCE"

    return current   # VERDICT is terminal


def apply_tool_result(case: BusinessCase, tool_name: str, result: dict) -> BusinessCase:
    """Write tool output into the fact_sheet with standardised keys."""
    mapping = {
        "fetch_competitors": {
            "competitor_count":        result.get("count"),
            "avg_competitor_rating":   result.get("avg_rating"),
            "nearest_competitor_m":    result.get("nearest_m"),
        },
        "estimate_footfall": {
            "estimated_footfall_lunch": result.get("estimated_pax_per_hour"),
            "peak_hours":               result.get("peak_hours"),
        },
        "calculate_breakeven": {
            "break_even_covers":        result.get("breakeven_covers_per_day"),
            "months_to_breakeven":      result.get("months_to_breakeven"),
        },
    }
    updates = mapping.get(tool_name, {})
    case.fact_sheet.update({k: v for k, v in updates.items() if v is not None})
    return case
