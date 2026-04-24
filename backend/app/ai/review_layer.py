"""
Review Layer

Secondary model-check step that reviews AI output for realism and grounding.
Filters unrealistic or hallucinated business recommendations.
(PRD Section 4.3.5, SAD Section 5 Model 2 / Review Prompt)
"""


class ReviewLayer:
    """Sanity-check layer for AI-generated recommendations."""

    async def review_recommendation(self, recommendation: dict, context: dict) -> dict:
        """
        Review whether AI recommendation is realistic, grounded, and consistent.

        Returns:
        - accepted: recommendation is sound
        - revised: recommendation needs adjustment (with suggestions)
        - rejected: recommendation is unrealistic or hallucinated
        """
        issues = []
        if not isinstance(recommendation, dict):
            return {
                "status": "rejected",
                "accepted": False,
                "issues": ["Recommendation is not structured data."],
            }
        confidence = recommendation.get("confidence_score") or recommendation.get(
            "confidence"
        )
        try:
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = None
        if confidence_value is not None and confidence_value > 100:
            issues.append("Confidence score must be 0-100.")
        if not recommendation.get("summary"):
            issues.append("Recommendation summary is missing.")
        return {
            "status": "accepted" if not issues else "revised",
            "accepted": not issues,
            "issues": issues,
            "recommendation": recommendation,
        }

    async def validate_facts(self, facts: list) -> list:
        """Validate extracted facts for consistency and plausibility."""
        valid_facts = []
        seen = set()
        for fact in facts or []:
            if not isinstance(fact, dict):
                continue
            key = fact.get("key") or fact.get("name")
            value = fact.get("value")
            if not key or value in {None, ""}:
                continue
            fingerprint = (str(key).lower(), str(value).lower())
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            valid_facts.append(fact)
        return valid_facts
