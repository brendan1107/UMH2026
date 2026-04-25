# test_full_loop_interactive.py
# Run with: python app/ai/test/test_full_loop_interactive.py
import asyncio, json, os, sys
from pathlib import Path

# ── Fix 1: tell Python where 'app' lives ──
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# ── Fix 2: load .env from backend/ ──
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")


def _prompt_missing_facts(case):
    """After any field task, prompt user for any still-missing required facts."""
    required = {
        "competitor_count":          ("Number of competitors nearby (integer)", int),
        "avg_competitor_rating":     ("Average competitor rating 1-5 (e.g. 4.1)", float),
        "estimated_footfall_lunch":  ("Estimated lunch footfall pax/hr (integer)", int),
        "confirmed_rent_myr":        ("Confirmed monthly rent in RM (e.g. 3200)", float),
        "break_even_covers":         ("Break-even covers per day (integer)", int),
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
    print("═══ F&B GENIE — INTERACTIVE TERMINAL ═══\n")

    from app.ai.schemas import BusinessCase
    from app.ai.orchestrator import run_agent_turn

    # ── Get case details from user ──
    print("Tell me about your business idea.")
    idea = input("Business idea (e.g. RM15 Nasi Lemak cafe): ").strip()
    location = input("Location (e.g. SS15, Subang Jaya): ").strip()
    budget_input = input("Budget in RM (e.g. 30000): ").strip()
    budget_myr = float(budget_input) if budget_input else 30000.0

    case = BusinessCase(
        id="interactive-001",
        idea=idea,
        location=location,
        budget_myr=budget_myr,
        phase="INTAKE",
        fact_sheet={},
        messages=[],
    )

    print(f"\nStarting investigation for: {case.idea}")
    print(f"Location: {case.location} | Budget: RM {case.budget_myr:,.0f}")
    print("─" * 50 + "\n")

    max_turns = 20
    turn = 0
    output = None

    while case.phase != "VERDICT" and turn < max_turns:
        turn += 1
        print(f"[Turn {turn} | Phase: {case.phase}]")

        # Run agent turn
        case, output = await run_agent_turn(case)

        print(f"Agent → {output.type.upper()}\n")

        if output.type == "tool_call":
            print(f"🔍 Running tool: {output.tool}")
            print(f"   Args: {output.args}")
            print("   (tool running automatically...)\n")

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
                    # Store as field note for AI context
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
            })

        elif output.type == "clarify":
            print(f"❓ QUESTION: {output.question}\n")
            for i, opt in enumerate(output.options, 1):
                print(f"   {i}. {opt}")
            print()
            choice = input("Your answer (enter number or type freely): ").strip()

            try:
                idx = int(choice) - 1
                answer = output.options[idx] if 0 <= idx < len(output.options) else choice
            except ValueError:
                answer = choice

            case.messages.append({
                "role": "user",
                "content": f"Answer: {answer}"
            })
            print(f"   You chose: {answer}\n")

        elif output.type == "verdict":
            # Verdict already handled — loop will exit
            pass

        print("─" * 50 + "\n")

    # ── Final verdict ──
    print("═══ INVESTIGATION COMPLETE ═══\n")
    print(f"Turns taken : {turn}")
    print(f"Final phase : {case.phase}")
    print(f"\nFact sheet collected:")
    for k, v in case.fact_sheet.items():
        print(f"  {k}: {v}")

    if output and output.type == "verdict":
        print(f"\n{'='*50}")
        print(f"VERDICT    : {output.decision}")
        print(f"Confidence : {output.confidence * 100:.0f}%")
        print(f"\n{output.summary}")
        if hasattr(output, "pivot_suggestion") and output.pivot_suggestion:
            print(f"\nSuggested pivot: {output.pivot_suggestion}")
        print(f"{'='*50}\n")
    else:
        print(f"\nLoop ended without verdict (last output: {output.type if output else 'none'})")


if __name__ == "__main__":
    asyncio.run(simulate_full_case())