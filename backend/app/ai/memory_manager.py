"""
Memory Manager

Manages conversation summarization and structured memory to work
within GLM's shorter context window (SAD Section 5, PRD Section 4.3.4).

Summarizes older turns, retains key facts as structured memory,
and keeps only decision-relevant details in active context.
"""


class MemoryManager:
    """Manages conversation memory and summarization."""

    _memory: dict[str, dict] = {}

    async def summarize_conversation(self, session_id: str) -> str:
        """Summarize older conversation turns to save context space."""
        session_memory = self._memory.get(session_id, {})
        summary = session_memory.get("summary")
        if summary:
            return summary
        facts = session_memory.get("facts", [])
        if not facts:
            return ""
        return "; ".join(
            f"{fact.get('key')}: {fact.get('value')}"
            for fact in facts[-10:]
            if isinstance(fact, dict)
        )

    async def get_structured_memory(self, case_id: str) -> dict:
        """Retrieve all structured facts and state for a case."""
        return self._memory.setdefault(
            case_id,
            {
                "facts": [],
                "tasks": [],
                "recommendation": None,
            },
        )

    async def update_memory(self, case_id: str, new_facts: list):
        """Store newly extracted facts into structured memory."""
        memory = await self.get_structured_memory(case_id)
        existing_by_key = {
            fact.get("key"): fact
            for fact in memory["facts"]
            if isinstance(fact, dict) and fact.get("key")
        }
        for fact in new_facts or []:
            if not isinstance(fact, dict):
                continue
            key = fact.get("key")
            if key:
                existing_by_key[key] = fact
            else:
                memory["facts"].append(fact)
        keyed_facts = list(existing_by_key.values())
        unkeyed_facts = [
            fact
            for fact in memory["facts"]
            if not isinstance(fact, dict) or not fact.get("key")
        ]
        memory["facts"] = [*keyed_facts, *unkeyed_facts]
        return memory
