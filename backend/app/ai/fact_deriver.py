"""Derive secondary fact_sheet values from confirmed investigation facts."""

from typing import Any


LEGACY_ASSUMPTION_INPUTS = (
    "avg_price_myr",
    "staff_count",
    "avg_food_cost_pct",
    "monthly_utilities_myr",
)
LEGACY_DERIVED_OUTPUTS = (
    "break_even_covers",
    "monthly_fixed_cost_myr",
    "months_to_breakeven",
)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _numbers_equal(left: Any, right: Any) -> bool:
    left_number = _number(left)
    right_number = _number(right)
    if left_number is None or right_number is None:
        return left == right
    return abs(left_number - right_number) < 0.001


def remove_legacy_derived_assumptions(fact_sheet: dict[str, Any]) -> dict[str, Any]:
    """Remove old backend-generated defaults from a persisted fact sheet.

    Older verdict generation saved assumed inputs like RM12 average price and
    2 staff as facts. Keep user-entered facts, but remove values that match the
    old derived_assumptions payload.
    """
    cleaned = dict(fact_sheet or {})
    assumptions = cleaned.pop("derived_assumptions", None)
    if not isinstance(assumptions, dict):
        return cleaned

    removed_legacy_input = False
    for key in LEGACY_ASSUMPTION_INPUTS:
        if key in cleaned and _numbers_equal(cleaned.get(key), assumptions.get(key)):
            cleaned.pop(key, None)
            removed_legacy_input = True

    lunch_share = _number(assumptions.get("lunch_footfall_share_of_daily"))
    daily_footfall = _number(cleaned.get("estimated_daily_footfall"))
    lunch_footfall = _number(cleaned.get("estimated_footfall_lunch"))
    if lunch_share is not None and daily_footfall is not None and lunch_footfall is not None:
        if round(daily_footfall * lunch_share) == round(lunch_footfall):
            cleaned.pop("estimated_footfall_lunch", None)
            removed_legacy_input = True

    if removed_legacy_input:
        for key in LEGACY_DERIVED_OUTPUTS:
            cleaned.pop(key, None)

    return cleaned


def derive_fact_sheet_values(fact_sheet: dict[str, Any], budget_myr: float | None = None) -> dict[str, Any]:
    """Return derived values only when all calculation inputs are confirmed."""
    derived: dict[str, Any] = {}
    fact_sheet = remove_legacy_derived_assumptions(fact_sheet)

    rent = _number(fact_sheet.get("confirmed_rent_myr"))
    avg_price = _number(fact_sheet.get("avg_price_myr"))
    food_cost_pct = _number(fact_sheet.get("avg_food_cost_pct"))
    utilities = _number(fact_sheet.get("monthly_utilities_myr"))
    monthly_staff_cost = _number(fact_sheet.get("monthly_staff_cost_myr"))
    trading_days = _number(fact_sheet.get("trading_days_per_month"))

    if any(value is None for value in (rent, avg_price, food_cost_pct, utilities, monthly_staff_cost, trading_days)):
        return derived
    if rent <= 0 or avg_price <= 0 or not 0 < food_cost_pct < 1 or utilities < 0 or monthly_staff_cost < 0 or trading_days <= 0:
        return derived

    contribution_per_cover = avg_price * (1 - food_cost_pct)
    if contribution_per_cover <= 0:
        return derived

    monthly_fixed = rent + monthly_staff_cost + utilities
    covers_per_month = monthly_fixed / contribution_per_cover
    covers_per_day = max(1, round(covers_per_month / trading_days))

    if "break_even_covers" not in fact_sheet:
        derived["break_even_covers"] = covers_per_day

    if "monthly_fixed_cost_myr" not in fact_sheet:
        derived["monthly_fixed_cost_myr"] = round(monthly_fixed)

    return derived
