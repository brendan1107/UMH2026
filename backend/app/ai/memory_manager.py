"""
Memory Manager

Manages conversation summarization and structured memory to work
within GLM's shorter context window (SAD Section 5, PRD Section 4.3.4).

Summarizes older turns, retains key facts as structured memory,
and keeps only decision-relevant details in active context.
"""


"""
Memory Manager — summarizes old turns and retains key facts.
Keeps GLM context lean for long investigations.
"""

from app.ai.schemas import BusinessCase
from app.ai.prompt_templates import REQUIRED_FACTS


class MemoryManager:
    """Manages conversation memory and summarization."""

    async def summarize_conversation(self, case: BusinessCase) -> str:
        """
        Produce a short summary of what's been investigated so far.
        Injected at the top of context when message history is long.
        """
        facts = case.fact_sheet
        collected = [f for f in REQUIRED_FACTS if f in facts]
        missing = [f for f in REQUIRED_FACTS if f not in facts]

        lines = [
            f"Investigation summary for: {case.idea}",
            f"Location: {case.location} | Budget: RM {case.budget_myr:,.0f}",
            f"Phase: {case.phase}",
            f"Facts collected ({len(collected)}/{len(REQUIRED_FACTS)}): {', '.join(collected) or 'none'}",
            f"Still missing: {', '.join(missing) or 'none — ready for verdict'}",
        ]

        if facts:
            lines.append("Key numbers so far:")
            for k, v in facts.items():
                lines.append(f"  - {k}: {v}")

        return "\n".join(lines)

    async def get_structured_memory(self, case: BusinessCase) -> dict:
        """Return organized facts and phase state for a case."""
        return {
            "phase": case.phase,
            "fact_sheet": case.fact_sheet,
            "message_count": len(case.messages),
            "facts_collected": [f for f in REQUIRED_FACTS if f in case.fact_sheet],
            "facts_missing": [f for f in REQUIRED_FACTS if f not in case.fact_sheet],
        }

    async def update_memory(self, case: BusinessCase, new_facts: dict) -> BusinessCase:
        """Merge new facts into the case fact sheet, no overwrite of existing."""
        for k, v in new_facts.items():
            if k not in case.fact_sheet:
                case.fact_sheet[k] = v
        return case