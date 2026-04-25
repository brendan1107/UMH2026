# test_full_loop_interactive.py
# Run with: python app/ai/test/test_full_loop_interactive.py
import asyncio, json, sys
from pathlib import Path

# Tell Python where 'app' lives
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")


def _prompt_missing_facts(case):
    """After any field task, prompt user for any still-missing required facts."""
    required = {
        "competitor_count":         ("Number of competitors nearby (integer)", int),
        "avg_competitor_rating":    ("Average competitor rating 1-5 (e.g. 4.1)", float),
        "estimated_footfall_lunch": ("Estimated lunch footfall pax/hr (integer)", int),
        "confirmed_rent_myr":       ("Confirmed monthly rent in RM (e.g. 3200)", float),
        "break_even_covers":        ("Break-even covers per day (integer)", int),
    }
    any_missing = False
    for key, (prompt, cast) in required.items():
        if key not in case.fact_sheet:
            if not any_missing:
                print("\n   [Collecting required facts for verdict]")
                any_missing = True
            val = input(f"   {prompt} (or Enter to skip): ").strip()
            if val:
                try:
                    case.fact_sheet[key] = cast(val)
                except ValueError:
                    print(f"   Invalid value for {key}, skipping.")
    return case


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

    max_turns = 30  # increased to allow multiple verdict cycles
    turn = 0

    while turn < max_turns:
        turn += 1
        print(f"[Turn {turn} | Phase: {case.phase}]")

        from app.ai.schemas import CompetitorResult, FootfallEstimate, BreakevenModel
        mock_comp.return_value  = CompetitorResult(count=6, avg_rating=4.1, nearest_m=120, price_levels=[1, 2, 2, 1, 2, 2])
        mock_foot.return_value  = FootfallEstimate(estimated_pax_per_hour=90, peak_hours=["12:00-14:00"], confidence="medium")
        mock_bev.return_value   = BreakevenModel(breakeven_covers_per_day=87, months_to_breakeven=8.5, min_viable_revenue_myr=13500.0)

        while case.phase != "VERDICT" and turn < max_turns:
            turn += 1
            print(f"── Turn {turn} | Phase: {case.phase} ──")
            
            case, output = await run_agent_turn(case)

            print(f"   GLM output type : {output.type}")

        elif output.type == "field_task":
            print(f"📋 FIELD TASK: {output.title}")
            print(f"   {output.instruction}")
            print(f"   Evidence needed: {output.evidence_type}\n")

            print("Submit your finding (or press Enter to skip):")

            if output.evidence_type == "count":
                val = input("   Count: ").strip()
                if val:
                    print("   What does this count represent?")
                    print("   1. competitor_count")
                    print("   2. break_even_covers")
                    choice = input("   Choice (1/2): ").strip()
                    key = "competitor_count" if choice == "1" else "break_even_covers"
                    case.fact_sheet[key] = int(val)

            elif output.evidence_type == "rating":
                val = input("   Average rating (e.g. 4.1): ").strip()
                if val:
                    case.fact_sheet["avg_competitor_rating"] = float(val)

            elif output.evidence_type == "text":
                val = input("   Your finding: ").strip()
                if val:
                    case.fact_sheet["field_notes"] = val

            elif output.evidence_type == "photo":
                print("   (photo evidence noted)")
                rent = input("   Monthly rent in RM (or Enter to skip): ").strip()
                if rent:
                    case.fact_sheet["confirmed_rent_myr"] = float(rent)

            # Always prompt for any still-missing required facts
            case = _prompt_missing_facts(case)

            # Append full fact sheet to AI context so agent sees everything
            case.messages.append({
                "role": "user",
                "content": json.dumps({
                    "task_completed": output.title,
                    "submitted_facts": case.fact_sheet,
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

            case.messages.append({
                "role": "user",
                "content": f"Answer: {answer}"
            })
            print(f"   You chose: {answer}\n")

        elif output.type == "verdict":
            # ── Print verdict ──
            print(f"\n{'='*50}")
            print(f"VERDICT    : {output.decision}")
            print(f"Confidence : {output.confidence * 100:.0f}%")
            print(f"\n{output.summary}")
            if hasattr(output, "pivot_suggestion") and output.pivot_suggestion:
                print(f"\nSuggested pivot: {output.pivot_suggestion}")
            print(f"{'='*50}\n")

            # ── Ask if user wants to revise ──
            cont = input("Add more information for a revised verdict? (y/n): ").strip().lower()
            if cont != "y":
                break

            # Let user update facts
            print("\nWhat new information do you have?")
            case = _prompt_missing_facts(case)
            extra = input("Any additional context? (or Enter to skip): ").strip()

            if extra:
                case.messages.append({
                    "role": "user",
                    "content": f"New information: {extra}. Please revise your verdict based on all updated facts."
                })
            else:
                case.messages.append({
                    "role": "user",
                    "content": "I have updated the facts. Please revise your verdict based on the new information."
                })

            # Reopen phase so agent re-evaluates
            case.phase = "EVIDENCE"
            print()

        print("─" * 50 + "\n")

    # ── Final summary ──
    print("═══ INVESTIGATION COMPLETE ═══\n")
    print(f"Turns taken : {turn}")
    print(f"Final phase : {case.phase}")
    print(f"\nFact sheet collected:")
    for k, v in case.fact_sheet.items():
        print(f"  {k}: {v}")

    if output and output.type != "verdict":
        print(f"\nNote: Loop ended without final verdict (last output: {output.type})")


if __name__ == "__main__":
    asyncio.run(simulate_full_case())