# test_full_loop.py
# Run with: python test_full_loop.py
import asyncio, json, os
from dotenv import load_dotenv
from unittest.mock import AsyncMock, patch

load_dotenv()

# ── Mock tool results (no Google API needed for this test) ──
MOCK_COMPETITORS = {
    "count": 6, "avg_rating": 4.1,
    "nearest_m": 120, "price_levels": [1, 2, 2, 1, 2, 2]
}
MOCK_FOOTFALL = {
    "estimated_pax_per_hour": 90,
    "peak_hours": ["12:00-14:00"],
    "confidence": "medium"
}
MOCK_BREAKEVEN = {
    "breakeven_covers_per_day": 87,
    "months_to_breakeven": 8.5,
    "min_viable_revenue_myr": 13500.0
}

async def simulate_full_case():
    print("═══ FULL AGENT LOOP SIMULATION ═══\n")

    # Import your actual agent files
    from ai.schemas import BusinessCase
    from ai.agent import run_agent_turn

    # Start a fake case
    case = BusinessCase(
        id="test-001",
        idea="A RM15 Nasi Lemak cafe targeting office workers in SS15",
        location="SS15, Subang Jaya",
        budget_myr=30000,
        phase="INTAKE",
        fact_sheet={},
        messages=[],
    )

    print(f"Starting case: {case.idea}")
    print(f"Budget: RM {case.budget_myr:,.0f}\n")

    max_turns = 10   # safety cap — agent should finish in fewer
    turn = 0

    # Patch tool calls so we don't hit Google API
    with patch("ai.tools.fetch_competitors", new_callable=AsyncMock) as mock_comp, \
         patch("ai.tools.estimate_footfall", new_callable=AsyncMock) as mock_foot, \
         patch("ai.tools.calculate_breakeven", new_callable=AsyncMock) as mock_bev:

        # Return mock data from tools
        from ai.schemas import CompetitorResult, FootfallEstimate, BreakevenModel
        mock_comp.return_value  = CompetitorResult(**MOCK_COMPETITORS)
        mock_foot.return_value  = FootfallEstimate(**MOCK_FOOTFALL)
        mock_bev.return_value   = BreakevenModel(**MOCK_BREAKEVEN)

        while case.phase != "VERDICT" and turn < max_turns:
            turn += 1
            print(f"── Turn {turn} | Phase: {case.phase} ──")
            print(f"   Fact sheet keys: {list(case.fact_sheet.keys())}")

            case, output = await run_agent_turn(case)

            print(f"   GLM output type : {output.type}")

            if output.type == "tool_call":
                print(f"   Tool called     : {output.tool}")
                print(f"   Tool args       : {output.args}")

            elif output.type == "field_task":
                print(f"   Task emitted    : {output.title}")
                print(f"   Evidence needed : {output.evidence_type}")
                # Simulate user completing the task
                print(f"   [Simulating user submitting evidence...]")
                # Inject the missing fact manually (as backend would after task submit)
                case.fact_sheet["estimated_footfall_lunch"] = 90
                case.fact_sheet["confirmed_rent_myr"] = 3200
                case.messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "task_completed": output.title,
                        "submitted_value": 90,
                        "confirmed_rent_myr": 3200,
                    })
                })

            elif output.type == "clarify":
                print(f"   Question        : {output.question}")
                print(f"   Options         : {output.options}")
                # Simulate user picking first option
                case.messages.append({
                    "role": "user",
                    "content": f"Answer: {output.options[0]}"
                })

            print()

    # ── Final verdict ──
    print("═══ VERDICT REACHED ═══")
    print(f"Turns taken  : {turn}")
    print(f"Final phase  : {case.phase}")
    print(f"Fact sheet   : {json.dumps(case.fact_sheet, indent=2)}")

    if output.type == "verdict":
        print(f"\nDecision     : {output.decision}")
        print(f"Confidence   : {output.confidence * 100:.0f}%")
        print(f"Summary      : {output.summary}")

        if output.decision in ("GO", "PIVOT", "STOP"):
            print("\nPASS ✓ — agent completed full loop correctly")
        else:
            print("\nFAIL ✗ — unexpected decision value")
    else:
        print(f"\nFAIL ✗ — loop ended without verdict (last output: {output.type})")


if __name__ == "__main__":
    asyncio.run(simulate_full_case())