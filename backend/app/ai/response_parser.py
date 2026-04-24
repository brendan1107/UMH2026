"""
Response Parser

Parses structured JSON outputs from GLM into typed Python objects.
Handles extraction of facts, tasks, questions, and recommendation updates.
(SAD Section 17: Use structured JSON outputs for easier backend parsing)
"""

import json
import re
from typing import Optional


class ResponseParser:
    """Parses GLM structured responses."""

    def parse_ai_response(self, raw_response: str) -> dict:
        """Parse the full AI response into structured components."""
        if raw_response is None:
            return {}
        if isinstance(raw_response, dict):
            return raw_response

        text = str(raw_response).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return {"message": text}
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return {"message": text}

        if not isinstance(parsed, dict):
            return {"message": str(parsed)}
        return parsed

    def extract_facts(self, parsed: dict) -> list:
        """Extract new business facts from AI response."""
        facts = parsed.get("extracted_facts") or parsed.get("facts") or []
        return facts if isinstance(facts, list) else []

    def extract_tasks(self, parsed: dict) -> list:
        """Extract generated investigation tasks."""
        tasks = parsed.get("generated_tasks") or parsed.get("tasks") or []
        if parsed.get("type") == "field_task":
            tasks = [
                {
                    "title": parsed.get("title") or "Investigation task",
                    "description": parsed.get("instruction"),
                    "priority": parsed.get("priority", "medium"),
                }
            ]
        return tasks if isinstance(tasks, list) else []

    def extract_recommendation(self, parsed: dict) -> Optional[dict]:
        """Extract recommendation update if present."""
        recommendation = (
            parsed.get("recommendation_update")
            or parsed.get("recommendation")
            or None
        )
        return recommendation if isinstance(recommendation, dict) else None
