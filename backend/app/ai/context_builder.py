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
        # TODO: Query all relevant data and build context dict
        pass

    def truncate_context(self, context: dict, max_tokens: int) -> dict:
        """Truncate context to fit within GLM's token limit."""
        # TODO: Prioritize decision-relevant data, summarize older turns
        pass
