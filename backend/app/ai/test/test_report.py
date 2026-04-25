import asyncio
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 1. Fix Python path so it can find the 'app' module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# 2. Load .env BEFORE importing tools so the API key is injected
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent.parent / ".env")
from app.ai.schemas import BusinessCase, AuditResult, RiskItem, VerdictOutput
from app.ai.report import generate_report

async def test_report():
    case = BusinessCase(
        id="test-001",
        idea="RM15 Nasi Lemak cafe in SS15",
        location="SS15, Subang Jaya",
        budget_myr=30000,
        phase="VERDICT",
        fact_sheet={
            "competitor_count": 6,
            "avg_competitor_rating": 4.1,
            "estimated_footfall_lunch": 90,
            "break_even_covers": 87,
            "months_to_breakeven": 8.5,
        },
        messages=[],
    )

    verdict = VerdictOutput(
        type="verdict",
        decision="PIVOT",
        confidence=0.85,
        summary="Market is oversaturated. 6 competitors within 1km with 4.1 avg rating. Break-even requires 87 covers/day against 90 footfall.",
        pivot_suggestion="Consider cloud kitchen model to cut rent costs by 60%.",
    )

    audit = AuditResult(risks=[
        RiskItem(
            category="financial",
            severity="high",
            title="Runway under 2 months at current burn",
            reasoning="RM30,000 budget covers only 1.8 months of RM8,200 fixed costs",
            mitigation="Secure 6-month runway before opening or reduce fixed costs below RM5,000/month",
        ),
        RiskItem(
            category="market",
            severity="high",
            title="Oversaturated nasi lemak market in SS15",
            reasoning="6 competitors with 4.1 avg rating means customer loyalty is already established",
            mitigation="Differentiate with a unique format — e.g. nasi lemak burritos or premium plating",
        ),
        RiskItem(
            category="ops",
            severity="medium",
            title="Break-even requires near-impossible capture rate",
            reasoning="87 covers/day from 90 footfall = 97% capture rate required",
            mitigation="Target dinner crowd as well to double addressable footfall",
        ),
    ])

    print("Generating PDF...")
    pdf_bytes = await generate_report(case, verdict, audit)
    
    with open("test_output.pdf", "wb") as f:
        f.write(pdf_bytes)
    
    print(f"PASS ✓ — PDF generated: {len(pdf_bytes):,} bytes → test_output.pdf")

if __name__ == "__main__":
    asyncio.run(test_report())