"""AI-assisted fact extraction and evidence readiness assessment."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai.glm_client import glm_json_call
from app.ai.prompts_templates import REQUIRED_FACTS

logger = logging.getLogger(__name__)


STRUCTURED_FACT_KEYS = {
    "competitor_count",
    "avg_competitor_rating",
    "estimated_footfall_lunch",
    "estimated_daily_footfall",
    "confirmed_rent_myr",
    "break_even_covers",
    "avg_price_myr",
    "staff_count",
    "avg_food_cost_pct",
    "monthly_utilities_myr",
    "monthly_staff_cost_myr",
    "trading_days_per_month",
    "monthly_fixed_cost_myr",
}

FACT_KEY_ALIASES = {
    "lunch_footfall": "estimated_footfall_lunch",
    "lunch_traffic": "estimated_footfall_lunch",
    "daily_footfall": "estimated_daily_footfall",
    "daily_traffic": "estimated_daily_footfall",
    "rent": "confirmed_rent_myr",
    "monthly_rent": "confirmed_rent_myr",
    "competitors": "competitor_count",
    "competitor_rating": "avg_competitor_rating",
    "average_competitor_rating": "avg_competitor_rating",
    "average_price": "avg_price_myr",
    "avg_price": "avg_price_myr",
    "food_cost": "avg_food_cost_pct",
    "food_cost_percentage": "avg_food_cost_pct",
    "utilities": "monthly_utilities_myr",
    "staff_cost": "monthly_staff_cost_myr",
    "salary_cost": "monthly_staff_cost_myr",
    "trading_days": "trading_days_per_month",
    "operating_days": "trading_days_per_month",
    "break_even": "break_even_covers",
    "breakeven": "break_even_covers",
    "break_even_covers_per_day": "break_even_covers",
}

NUMERIC_FACT_RANGES = {
    "competitor_count": (0, 500, "int"),
    "avg_competitor_rating": (0, 5, "float"),
    "estimated_footfall_lunch": (0, 100000, "int"),
    "estimated_daily_footfall": (0, 1000000, "int"),
    "confirmed_rent_myr": (0, 1000000, "int"),
    "break_even_covers": (0, 100000, "int"),
    "avg_price_myr": (0, 10000, "float"),
    "staff_count": (0, 1000, "int"),
    "avg_food_cost_pct": (0, 1, "float"),
    "monthly_utilities_myr": (0, 100000, "int"),
    "monthly_staff_cost_myr": (0, 1000000, "int"),
    "trading_days_per_month": (1, 31, "int"),
    "monthly_fixed_cost_myr": (0, 1000000, "int"),
}

READINESS_STATUSES = {"verdict_ready", "needs_more_evidence", "insufficient"}


def _empty_analysis() -> dict[str, Any]:
    return {
        "structured_facts": {},
        "structured_fact_items": [],
        "supporting_facts": [],
        "evidence_assessment": None,
    }


def _snake_key(value: Any) -> str:
    key = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return key


def _canonical_key(value: Any) -> str:
    key = _snake_key(value)
    return FACT_KEY_ALIASES.get(key, key)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        match = re.search(r"-?\d[\d,]*(?:\.\d+)?", value)
        if not match:
            return None
        value = match.group(0)
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _normalize_fact_value(key: str, value: Any) -> Any | None:
    if key not in NUMERIC_FACT_RANGES:
        return value if value not in (None, "") else None

    minimum, maximum, value_type = NUMERIC_FACT_RANGES[key]
    number = _number(value)
    if number is None:
        return None

    if key == "avg_food_cost_pct" and number > 1:
        number = number / 100

    if not minimum <= number <= maximum:
        return None

    if value_type == "int":
        return int(round(number))
    return round(number, 3 if key == "avg_food_cost_pct" else 2)


def _analysis_prompt() -> str:
    required = ", ".join(REQUIRED_FACTS)
    structured = ", ".join(sorted(STRUCTURED_FACT_KEYS))
    return f"""You extract business facts from Malaysian small-business investigation messages, including F&B and retail.

Return JSON only with this exact shape:
{{
  "structured_facts": [
    {{"key":"snake_case_key","value":123,"unit":"optional unit","importance":"required|supporting|background|ignore","confidence":0.0,"evidence":"exact short source text","reason":"why it matters"}}
  ],
  "supporting_facts": [
    {{"key":"snake_case_key","value":"short value","importance":"supporting|background","confidence":0.0,"evidence":"exact short source text","reason":"why it matters"}}
  ],
  "evidence_assessment": {{"status":"verdict_ready|needs_more_evidence|insufficient","reason":"plain English","missing_or_weak_facts":["fact_key"]}}
}}

Rules:
1. Use structured_facts only for these known keys: {structured}.
2. Required verdict facts are: {required}.
3. Unknown but useful information goes into supporting_facts, not structured_facts.
4. Do not invent facts. Only extract what the user or task submission actually says.
5. Use confidence below 0.65 for vague, implied, or uncertain claims.
6. Mark evidence_assessment.status as verdict_ready only when the required facts are present or clearly answered and the evidence is strong enough to generate a verdict.
7. If the required facts are still missing or weak, use needs_more_evidence and list what is missing.
8. If the message is not business evidence, return empty fact arrays and keep assessment based on current_fact_sheet.
"""


def _normalize_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = _empty_analysis()

    for item in raw.get("structured_facts") or []:
        if not isinstance(item, dict):
            continue

        key = _canonical_key(item.get("key"))
        confidence = _number(item.get("confidence")) or 0
        if key not in STRUCTURED_FACT_KEYS or confidence < 0.6:
            continue

        value = _normalize_fact_value(key, item.get("value"))
        if value is None:
            continue

        fact_item = {
            "key": key,
            "value": value,
            "unit": item.get("unit"),
            "importance": item.get("importance") or ("required" if key in REQUIRED_FACTS else "supporting"),
            "confidence": round(confidence, 2),
            "evidence": str(item.get("evidence") or "")[:300],
            "reason": str(item.get("reason") or "")[:300],
            "source": "ai_fact_analyzer",
        }
        normalized["structured_facts"][key] = value
        normalized["structured_fact_items"].append(fact_item)

    for item in raw.get("supporting_facts") or []:
        if not isinstance(item, dict):
            continue

        confidence = _number(item.get("confidence")) or 0
        if confidence < 0.5:
            continue

        key = _canonical_key(item.get("key"))
        if not key or key in STRUCTURED_FACT_KEYS:
            continue

        value = item.get("value")
        if value in (None, "") or isinstance(value, (dict, list)):
            continue

        normalized["supporting_facts"].append({
            "key": key,
            "value": str(value)[:300],
            "importance": item.get("importance") or "supporting",
            "confidence": round(confidence, 2),
            "evidence": str(item.get("evidence") or "")[:300],
            "reason": str(item.get("reason") or "")[:300],
            "source": "ai_fact_analyzer",
        })

    assessment = raw.get("evidence_assessment")
    if isinstance(assessment, dict):
        status = assessment.get("status")
        if status in READINESS_STATUSES:
            missing_or_weak = assessment.get("missing_or_weak_facts") or []
            normalized["evidence_assessment"] = {
                "status": status,
                "reason": str(assessment.get("reason") or "")[:500],
                "missing_or_weak_facts": [
                    _canonical_key(item) for item in missing_or_weak if _canonical_key(item)
                ][:10],
                "source": "ai_fact_analyzer",
            }

    return normalized


async def analyze_message_facts(
    text: Any,
    current_fact_sheet: dict[str, Any],
    case_context: dict[str, Any] | None = None,
    timeout: float = 18,
) -> dict[str, Any]:
    """Extract facts with AI. Fail closed so primary chat/task flows continue."""
    source_text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=True, default=str)
    if not source_text.strip():
        return _empty_analysis()

    payload = {
        "text": source_text,
        "current_fact_sheet": current_fact_sheet or {},
        "required_facts": REQUIRED_FACTS,
        "case_context": case_context or {},
    }

    try:
        raw = await glm_json_call(
            system=_analysis_prompt(),
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=True, default=str)}],
            max_tokens=1400,
            timeout=timeout,
        )
    except Exception:
        logger.exception("AI fact analysis failed; continuing with deterministic extraction only.")
        return _empty_analysis()

    return _normalize_analysis(raw)


def merge_supporting_facts(
    existing: list[dict[str, Any]] | None,
    new_facts: list[dict[str, Any]] | None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    """Merge supporting facts while preserving newest useful context."""
    merged = []
    seen = set()

    for item in [*(existing or []), *(new_facts or [])]:
        if not isinstance(item, dict):
            continue
        key = _snake_key(item.get("key"))
        evidence = str(item.get("evidence") or "")[:300]
        value = str(item.get("value") or "")[:300]
        dedupe_key = (key, value, evidence)
        if not key or not value or dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        merged.append({
            "key": key,
            "value": value,
            "importance": item.get("importance") or "supporting",
            "confidence": item.get("confidence"),
            "evidence": evidence,
            "reason": str(item.get("reason") or "")[:300],
            "source": item.get("source") or "unknown",
        })

    return merged[-limit:]
