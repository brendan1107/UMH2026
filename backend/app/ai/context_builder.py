"""
Context Builder

Assembles the prompt context from structured memory, conversation summary,
external API results, uploaded evidence, and current recommendation state.

Handles GLM's shorter context window through summarization and filtering
(SAD Section 5, PRD Section 4.3.4).
"""


"""Context Builder — trims conversation history to fit GLM's context window."""

import json

MAX_MESSAGES = 20
MAX_FACT_CHARS = 2000


class ContextBuilder:
    """Builds optimized context for GLM prompts."""

    def build_context(self, case) -> list[dict]:
        """
        Return trimmed message list safe to send to GLM.
        Keeps first message (original brief) + last MAX_MESSAGES-1 turns.
        """
        messages = case.messages
        if len(messages) > MAX_MESSAGES:
            messages = [messages[0]] + messages[-(MAX_MESSAGES - 1):]
        return messages

    def truncate_context(self, context: dict, max_tokens: int) -> dict:
        """
        Truncate fact sheet if it's getting too large.
        Drops oldest keys first, keeps most recently added facts.
        """
        facts = context.get("fact_sheet", {})
        keys = list(facts.keys())
        while keys and len(json.dumps({k: facts[k] for k in keys})) > MAX_FACT_CHARS:
            keys.pop(0)
        context["fact_sheet"] = {k: facts[k] for k in keys}
        return context
