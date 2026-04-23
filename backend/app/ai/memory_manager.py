"""
Memory Manager

Manages conversation summarization and structured memory to work
within GLM's shorter context window (SAD Section 5, PRD Section 4.3.4).

Summarizes older turns, retains key facts as structured memory,
and keeps only decision-relevant details in active context.
"""


class MemoryManager:
    """Manages conversation memory and summarization."""

    async def summarize_conversation(self, session_id: str) -> str:
        """Summarize older conversation turns to save context space."""
        # TODO: Summarize previous turns, retain key decision points
        pass

    async def get_structured_memory(self, case_id: str) -> dict:
        """Retrieve all structured facts and state for a case."""
        # TODO: Return organized facts, tasks, recommendation state
        pass

    async def update_memory(self, case_id: str, new_facts: list):
        """Store newly extracted facts into structured memory."""
        # TODO: Upsert facts, handle conflicts
        pass
