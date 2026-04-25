# app/ai/test/test_full_loop.py
import asyncio, json, os, sys
from pathlib import Path

# Tell Python where 'app' lives
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

from unittest.mock import AsyncMock, patch

async def simulate_full_case():
    print("═══ FULL AGENT LOOP SIMULATION ═══\n")

    from app.ai.schemas import BusinessCase
    from app.ai.orchestrator import run_agent_turn
    
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

    max_turns = 10
    turn = 0

    # We patch the tools so we don't spam Google Maps during tests
    with patch("app.ai.tools.fetch_competitors", new_callable=AsyncMock) as mock_comp, \
         patch("app.ai.tools.estimate_footfall", new_callable=AsyncMock) as mock_foot, \
         patch("app.ai.tools.calculate_breakeven", new_callable=AsyncMock) as mock_bev:

        from app.ai.schemas import CompetitorResult, FootfallEstimate, BreakevenModel
        mock_comp.return_value  = CompetitorResult(count=6, avg_rating=4.1, nearest_m=120, price_levels=[1, 2, 2, 1, 2, 2])
        mock_foot.return_value  = FootfallEstimate(estimated_pax_per_hour=90, peak_hours=["12:00-14:00"], confidence="medium")
        mock_bev.return_value   = BreakevenModel(breakeven_covers_per_day=87, months_to_breakeven=8.5, min_viable_revenue_myr=13500.0)

        while case.phase != "VERDICT" and turn < max_turns:
            turn += 1
            print(f"── Turn {turn} | Phase: {case.phase} ──")
            
            case, output = await run_agent_turn(case)

            print(f"   GLM output type : {output.type}")

            if output.type == "tool_call":
                print(f"   Tool called     : {output.tool}")
            
            elif output.type == "clarify":
                print(f"   Question        : {output.question}")
                case.messages.append({
                    "role": "user",
                    "content": f"Answer: {output.options[0]}"
                })
            
            elif output.type == "field_task":
                print(f"   Task emitted    : {output.title}")
                print(f"   [Simulating user submitting ALL realistic evidence...]")
                
                # Give the AI sensible data so it doesn't freak out
                case.fact_sheet["competitor_count"] = 6
                case.fact_sheet["avg_competitor_rating"] = 4.1
                case.fact_sheet["estimated_footfall_lunch"] = 90
                case.fact_sheet["confirmed_rent_myr"] = 3200
                case.fact_sheet["break_even_covers"] = 87
                
                case.messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "task_completed": output.title,
                        "submitted_value": "All missing facts have been collected and updated in the fact sheet."
                    })
                })
                
            elif output.type == "verdict":
                # The AI has made its final decision, break the loop!
                case.phase = "VERDICT"

            print()

    print("═══ VERDICT REACHED ═══")
    print(f"Turns taken  : {turn}")
    print(f"Final phase  : {case.phase}")

    if output.type == "verdict":
        print(f"\nDecision     : {output.decision}")
        print(f"Confidence   : {output.confidence * 100:.0f}%")
        print(f"Summary      : {output.summary}")
        print("\nPASS ✓ — agent completed full loop correctly")
    else:
        print(f"\nFAIL ✗ — loop ended without verdict (last output: {output.type})")

if __name__ == "__main__":
    asyncio.run(simulate_full_case())