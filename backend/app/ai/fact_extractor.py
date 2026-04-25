"""Extract structured investigation facts from user-provided text."""

import json
import re
from typing import Any


NUMBER = r"(?P<value>\d[\d,]*(?:\.\d+)?)(?P<suffix>k)?"


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return value
        return _flatten_text(parsed)
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _parse_number(match: re.Match) -> float:
    raw_value = match.group("value").replace(",", "")
    number = float(raw_value)
    if (match.groupdict().get("suffix") or "").lower() == "k":
        number *= 1000
    return number


def _as_int(value: float) -> int:
    return int(round(value))


def _set_if_valid(facts: dict[str, Any], key: str, value: float) -> None:
    if key == "competitor_count" and 0 <= value <= 500:
        facts[key] = _as_int(value)
    elif key == "avg_competitor_rating" and 0 <= value <= 5:
        facts[key] = round(value, 2)
    elif key == "estimated_footfall_lunch" and 0 <= value <= 100000:
        facts[key] = _as_int(value)
    elif key == "estimated_daily_footfall" and 0 <= value <= 1000000:
        facts[key] = _as_int(value)
    elif key == "confirmed_rent_myr" and 0 < value <= 1000000:
        facts[key] = _as_int(value)
    elif key == "break_even_covers" and 0 <= value <= 100000:
        facts[key] = _as_int(value)
    elif key == "avg_price_myr" and 0 < value <= 10000:
        facts[key] = round(value, 2)
    elif key == "staff_count" and 0 <= value <= 1000:
        facts[key] = _as_int(value)
    elif key == "avg_food_cost_pct" and 0 < value <= 100:
        facts[key] = round(value / 100 if value > 1 else value, 3)
    elif key == "monthly_utilities_myr" and 0 <= value <= 100000:
        facts[key] = _as_int(value)
    elif key == "monthly_staff_cost_myr" and 0 <= value <= 1000000:
        facts[key] = _as_int(value)
    elif key == "trading_days_per_month" and 1 <= value <= 31:
        facts[key] = _as_int(value)


PATTERNS: dict[str, list[re.Pattern]] = {
    "competitor_count": [
        re.compile(
            rf"\b(?:competitor(?:s)?|cake shops?|bakeries|bakery|kuih stalls?)\b"
            rf"[^.\n]{{0,60}}?\b(?:count|number|total|found|exist|exists|:|-)\s*{NUMBER}"
            rf"(?!\s*(?:km|m\b|sqm|m2|rm|myr))",
            re.I,
        ),
        re.compile(
            rf"(?<!top\s)\b{NUMBER}\s+(?:nearby\s+)?"
            rf"(?:competitor(?:s)?|cake shops?|bakeries|bakery|kuih stalls?)\b",
            re.I,
        ),
    ],
    "avg_competitor_rating": [
        re.compile(
            rf"\b(?:average|avg)\s+(?:competitor\s+)?rating(?:s)?\b"
            rf"\s*(?:is|=|:|of)?\s*{NUMBER}\s*(?:/5|stars?)?",
            re.I,
        ),
        re.compile(
            rf"\b(?:competitor\s+)?rating(?:s)?\b"
            rf"\s*(?:is|=|:|of|avg|average)?\s*{NUMBER}\s*(?:/5|stars?)?",
            re.I,
        ),
        re.compile(
            rf"\b{NUMBER}\s*(?:/5|stars?)\b[^.\n]{{0,30}}\b(?:rating|competitor)\b",
            re.I,
        ),
    ],
    "estimated_footfall_lunch": [
        re.compile(
            rf"\b(?:lunch|lunchtime|noon|midday)\b[^.\n]{{0,40}}?"
            rf"\b(?:footfall|pax|people|customers|count)\b[^0-9]{{0,20}}{NUMBER}",
            re.I,
        ),
        re.compile(
            rf"\b(?:footfall|pax|people|customers)\b[^.\n]{{0,40}}?"
            rf"\b(?:lunch|lunchtime|noon|midday)\b[^0-9]{{0,20}}{NUMBER}",
            re.I,
        ),
        re.compile(
            rf"\b(?:lunch|lunchtime|noon|midday)\b[^.\n]{{0,20}}?"
            rf"{NUMBER}\s*(?:pax|people|customers)\b",
            re.I,
        ),
    ],
    "estimated_daily_footfall": [
        re.compile(
            rf"\b{NUMBER}\s*(?:daily|per\s+day)?\s*"
            rf"(?:footfall|pax|people|customers)\b",
            re.I,
        ),
        re.compile(
            rf"\b(?:daily|day|per\s+day)\b[^.\n]{{0,40}}?"
            rf"\b(?:footfall|pax|people|customers|traffic)\b[^0-9.\n]{{0,20}}{NUMBER}",
            re.I,
        ),
        re.compile(
            rf"\b(?:footfall|pax|people|customers|traffic)\b[^.\n]{{0,40}}?"
            rf"\b(?:daily|day|per\s+day)\b[^0-9.\n]{{0,20}}{NUMBER}",
            re.I,
        ),
    ],
    "confirmed_rent_myr": [
        re.compile(
            rf"\b(?:rm|myr)\s*{NUMBER}\b[^.\n,]{{0,30}}?\b(?:rent|rental|lease)\b",
            re.I,
        ),
        re.compile(
            rf"\b(?:monthly\s+)?(?:rent|rental|lease)\b"
            rf"\s*(?:is|was|around|about|expected|confirmed|=|:|-)?\s*"
            rf"(?:rm|myr)?\s*{NUMBER}\b",
            re.I,
        ),
        re.compile(
            rf"\b{NUMBER}\s*(?:monthly\s+)?(?:rent|rental|lease)\b",
            re.I,
        ),
    ],
    "break_even_covers": [
        re.compile(
            rf"\b(?:break[- ]?even|breakeven)\b[^.\n]{{0,40}}?"
            rf"(?:covers?|pax|customers)?[^0-9]{{0,20}}{NUMBER}",
            re.I,
        ),
        re.compile(
            rf"\b{NUMBER}\s*(?:covers?|pax|customers)\b[^.\n]{{0,30}}?"
            rf"\b(?:break[- ]?even|breakeven)\b",
            re.I,
        ),
    ],
    "avg_price_myr": [
        re.compile(
            rf"\b(?:avg|average)\s+(?:spend|ticket|price|basket|order)\b"
            rf"[^.\n]{{0,25}}?(?:rm|myr)?\s*{NUMBER}\b",
            re.I,
        ),
        re.compile(
            rf"\b(?:rm|myr)\s*{NUMBER}\b[^.\n]{{0,25}}?"
            rf"\b(?:avg|average)\s+(?:spend|ticket|price|basket|order)\b",
            re.I,
        ),
    ],
    "staff_count": [
        re.compile(
            rf"\b(?:staff|worker|employee|headcount|crew)\b"
            rf"[^.\n]{{0,25}}?(?:count|number|total|is|are|:|-)?\s*{NUMBER}\b",
            re.I,
        ),
        re.compile(
            rf"\b{NUMBER}\s+(?:staff|workers|employees|crew)\b",
            re.I,
        ),
    ],
    "avg_food_cost_pct": [
        re.compile(
            rf"\b(?:food\s+cost|cogs|cost\s+of\s+goods)\b"
            rf"[^.\n]{{0,25}}?{NUMBER}\s*%?",
            re.I,
        ),
    ],
    "monthly_utilities_myr": [
        re.compile(
            rf"\b(?:utilities|utility|electricity|water)\b"
            rf"[^.\n]{{0,25}}?(?:rm|myr)?\s*{NUMBER}\b",
            re.I,
        ),
    ],
    "monthly_staff_cost_myr": [
        re.compile(
            rf"\b(?:monthly\s+)?(?:staff|salary|wage|payroll|labou?r)\s+"
            rf"(?:cost|costs|salary|salaries|wages|payroll)\b"
            rf"[^.\n]{{0,25}}?(?:rm|myr)?\s*{NUMBER}\b",
            re.I,
        ),
        re.compile(
            rf"\b(?:rm|myr)\s*{NUMBER}\b[^.\n]{{0,25}}?"
            rf"\b(?:monthly\s+)?(?:staff|salary|wage|payroll|labou?r)\s+"
            rf"(?:cost|costs|salary|salaries|wages|payroll)\b",
            re.I,
        ),
    ],
    "trading_days_per_month": [
        re.compile(
            rf"\b(?:trading|operating|open)\s+days?\b"
            rf"[^.\n]{{0,25}}?(?:per\s+month|monthly|/month)?[^0-9]{{0,10}}{NUMBER}\b",
            re.I,
        ),
        re.compile(
            rf"\b{NUMBER}\s+(?:trading|operating|open)\s+days?\s+(?:per\s+month|monthly|/month)\b",
            re.I,
        ),
    ],
}


def extract_required_facts_from_text(text: Any) -> dict[str, Any]:
    source = _flatten_text(text)
    facts: dict[str, Any] = {}

    for key, patterns in PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(source)
            if not match:
                continue
            _set_if_valid(facts, key, _parse_number(match))
            break

    return facts


def extract_required_facts_from_messages(messages: list[dict]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for message in messages:
        if message.get("role") != "user":
            continue
        facts.update(extract_required_facts_from_text(message.get("content")))
    return facts


def _first_number(value: Any) -> float | None:
    match = re.search(rf"\b{NUMBER}\b", _flatten_text(value), re.I)
    if not match:
        return None
    return _parse_number(match)


def _infer_fact_key_from_task_context(context: str) -> str | None:
    normalized = context.lower()
    has_competitor = any(term in normalized for term in ("competitor", "cake shop", "bakery", "kuih stall"))
    has_footfall = any(term in normalized for term in ("footfall", "lunch", "pax"))
    has_daily = any(term in normalized for term in ("daily", "per day", "day"))

    if "break" in normalized and "even" in normalized:
        return "break_even_covers"
    if "food cost" in normalized or "cogs" in normalized or "cost of goods" in normalized:
        return "avg_food_cost_pct"
    if any(term in normalized for term in ("staff cost", "salary cost", "wage cost", "payroll", "labour cost", "labor cost")):
        return "monthly_staff_cost_myr"
    if "trading days" in normalized or "operating days" in normalized or "open days" in normalized:
        return "trading_days_per_month"
    if "average spend" in normalized or "avg spend" in normalized or "ticket" in normalized or "basket" in normalized:
        return "avg_price_myr"
    if "staff" in normalized or "worker" in normalized or "employee" in normalized or "crew" in normalized:
        return "staff_count"
    if "utilities" in normalized or "utility" in normalized or "electricity" in normalized or "water" in normalized:
        return "monthly_utilities_myr"
    if "rent" in normalized or "rental" in normalized or "lease" in normalized:
        return "confirmed_rent_myr"
    if "rating" in normalized or "star" in normalized:
        return "avg_competitor_rating"
    if has_footfall and has_daily:
        return "estimated_daily_footfall"
    if has_competitor and any(term in normalized for term in ("competitor count", "number of competitor", "total competitor", "competitor scan", "cake shop", "bakery", "kuih stall")):
        return "competitor_count"
    if has_footfall and any(term in normalized for term in ("footfall count", "lunch count", "lunch-period", "lunch period", "pax")):
        return "estimated_footfall_lunch"
    if has_competitor and not has_footfall:
        return "competitor_count"
    if has_footfall and not has_competitor:
        return "estimated_footfall_lunch"
    return None


def extract_required_facts_from_task_submission(task_data: dict, submitted_value: Any) -> dict[str, Any]:
    facts = extract_required_facts_from_text(submitted_value)
    if facts:
        return facts

    context = _flatten_text({
        "title": task_data.get("title"),
        "description": task_data.get("description"),
        "action_label": task_data.get("action_label"),
        "data": task_data.get("data"),
    })
    key = _infer_fact_key_from_task_context(context)
    value = _first_number(submitted_value)

    if not key or value is None:
        return {}

    inferred: dict[str, Any] = {}
    _set_if_valid(inferred, key, value)
    return inferred
