"""
Context Builder

Assembles the prompt context from structured memory, conversation summary,
external API results, uploaded evidence, and current recommendation state.

Handles GLM's shorter context window through summarization and filtering
(SAD Section 5, PRD Section 4.3.4).
"""


class ContextBuilder:
    """Builds optimized context for GLM prompts."""

    def build_context(self, case_id: str) -> dict:
        """
        Assemble full context for AI reasoning.

        Includes:
        - Latest user input
        - Structured business facts
        - Conversation summary (not full raw history)
        - Google Places/Maps results
        - Uploaded evidence summaries
        - Generated tasks and their status
        - Prior recommendation state
        """
        return {
            "case_id": case_id,
            "facts": [],
            "uploads": [],
            "places": [],
            "tasks": [],
            "recommendation": None,
            "conversation_summary": None,
        }

    def truncate_context(self, context: dict, max_tokens: int) -> dict:
        """Truncate context to fit within GLM's token limit."""
        if max_tokens <= 0:
            return {}
        truncated = dict(context)
        for key in ("facts", "uploads", "places", "tasks"):
            value = truncated.get(key)
            if isinstance(value, list):
                truncated[key] = value[-25:]
        return truncated
