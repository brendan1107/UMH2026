"""
Response Parser

Parses structured JSON outputs from GLM into typed Python objects.
Handles extraction of facts, tasks, questions, and recommendation updates.
(SAD Section 17: Use structured JSON outputs for easier backend parsing)
"""

import json
from typing import Optional


class ResponseParser:
    """Parses GLM structured responses."""

    def parse_ai_response(self, raw_response: str) -> dict:
        """Parse the full AI response into structured components."""
        # TODO: Extract JSON from response, handle markdown code blocks
        pass

    def extract_facts(self, parsed: dict) -> list:
        """Extract new business facts from AI response."""
        # TODO: Return list of fact dicts
        pass

    def extract_tasks(self, parsed: dict) -> list:
        """Extract generated investigation tasks."""
        # TODO: Return list of task dicts
        pass

    def extract_recommendation(self, parsed: dict) -> Optional[dict]:
        """Extract recommendation update if present."""
        # TODO: Return recommendation dict or None
        pass
