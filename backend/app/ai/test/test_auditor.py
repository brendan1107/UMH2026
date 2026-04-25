# app/ai/test/test_auditor.py
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")

async def test_auditor():
    from app.ai.review_layer import run_audit
    from app.ai.schemas import BusinessCase as AICase

    fake_case = AICase(
        id="audit-test",
        idea="RM15 Nasi Lemak cafe in SS15",
        location="SS15, Subang Jaya",
        budget_myr=30000,
        phase="VERDICT",
        fact_sheet={
            "competitor_count": 6,
            "avg_competitor_rating": 4.1,
            "estimated_footfall_lunch": 90,
            "confirmed_rent_myr": 3200,
            "break_even_covers": 87,
        },
        messages=[],
    )

    print("Running auditor (Pass 2)...")
    result = await run_audit(fake_case, "Cafe looks viable but competition is high.")

    print(f"Risks returned: {len(result.risks)}")
    for r in result.risks:
        print(f"  [{r.severity.upper()}] {r.title}")
        print(f"    → {r.reasoning}")

    assert len(result.risks) == 3, "Expected exactly 3 risks"
    print("\nPASS ✓ — auditor working correctly")

if __name__ == "__main__":
    asyncio.run(test_auditor())