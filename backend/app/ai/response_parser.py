"""
Response Parser

Parses structured JSON outputs from GLM into typed Python objects.
Handles extraction of facts, tasks, questions, and recommendation updates.
(SAD Section 17: Use structured JSON outputs for easier backend parsing)
"""

"""Response Parser — extracts structured data from GLM output."""

import json
from typing import Optional


class ResponseParser:

    def parse_ai_response(self, raw_response: str) -> dict:
        """Strip markdown fences and parse JSON."""
        content = raw_response.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())

    def extract_facts(self, parsed: dict) -> list:
        return parsed.get("extracted_facts", [])

    def extract_tasks(self, parsed: dict) -> list:
        return parsed.get("generated_tasks", [])

    def extract_recommendation(self, parsed: dict) -> Optional[dict]:
        return parsed.get("recommendation_update")