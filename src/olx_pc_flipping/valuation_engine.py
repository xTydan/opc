"""Conservative valuation from fresh OLX comparables.

Exact-model matches are supported. Cross-model matches use category-specific
specification similarity and bounded price normalization; brand is not a
required match key. Asking prices are never represented as completed sales.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .component_matching import match_comparable

CENT = Decimal("0.01")


def normalize_model_key(value: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _price(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not result.is_finite() or result <= 0:
        return None
    return result.quantize(CENT, rounding=ROUND_HALF_UP)


def _quantile(values: list[Decimal], probability: Decimal) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires at least one value")
    if len(ordered) == 1:
        return ordered[0]
    position = Decimal(len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def estimate_component_value(
    component: dict[str, Any],
    *,
    min_samples: int = 5,
    max_age_hours: int = 24,
    haircut_percent: Decimal | int | float | str = Decimal("3"),
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Estimate a conservative value from fresh, active, comparable OLX offers.

    Comparable records require marketplace, status, price, collected_at and
    id/url. They may match by exact model or by structured component specs.
    """
    if not isinstance(component, dict):
        raise ValueError("component must be an object")
    if min_samples < 2:
        raise ValueError("min_samples must be >= 2")
    if max_age_hours < 1:
        raise ValueError("max_age_hours must be >= 1")
    try:
        haircut = Decimal(str(haircut_percent))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("haircut_percent must be a number") from None
    if not haircut.is_finite() or haircut < 0 or haircut >= 100:
        raise ValueError("haircut_percent must be between 0 and 100")

    reference_time = as_of or datetime.now(timezone.utc)
    if reference_time.tzinfo is None:
        raise ValueError("as_of must include a timezone")
    reference_time = reference_time.astimezone(timezone.utc)

    expected_key = normalize_model_key(str(component.get("model_key") or component.get("model", "")))
    raw_comparables = component.get("comparables") or []
    if not isinstance(raw_comparables, list):
        raise ValueError("component.comparables must be an array")

    accepted: list[tuple[Decimal, datetime, str, Decimal, str]] = []
    seen: set[str] = set()
    excluded: dict[str, int] = {}
    match_methods: dict[str, int] = {}

    for item in raw_comparables:
        if not isinstance(item, dict):
            excluded["invalid_record"] = excluded.get("invalid_record", 0) + 1
            continue
        if str(item.get("marketplace", "")).casefold() != "olx":
            excluded["not_olx"] = excluded.get("not_olx", 0) + 1
            continue
        if str(item.get("status", "")).casefold() not in {"active", "available"}:
            excluded["not_active"] = excluded.get("not_active", 0) + 1
            continue

        candidate_key = normalize_model_key(str(item.get("model_key") or item.get("model") or ""))
        if not item.get("category"):
            # Backward compatibility for old imports: exact model only.
            if not expected_key or candidate_key != expected_key:
                excluded["different_model"] = excluded.get("different_model", 0) + 1
                continue
            match = {"matched": True, "method": "legacy_exact_model", "price_multiplier": 1.0}
        else:
            match = match_comparable(component, item)
            if not match.get("matched"):
                reason = str(match.get("reason") or "not_comparable")
                excluded[reason] = excluded.get(reason, 0) + 1
                continue

        asking_price = _price(item.get("price"))
        if asking_price is None:
            excluded["invalid_price"] = excluded.get("invalid_price", 0) + 1
            continue
        collected_at = _parse_timestamp(item.get("collected_at"))
        if collected_at is None:
            excluded["missing_timestamp"] = excluded.get("missing_timestamp", 0) + 1
            continue
        age = reference_time - collected_at
        if age < timedelta(0) or age > timedelta(hours=max_age_hours):
            excluded["stale_or_future"] = excluded.get("stale_or_future", 0) + 1
            continue
        identity = str(item.get("id") or item.get("url") or "").strip()
        if not identity:
            excluded["missing_identity"] = excluded.get("missing_identity", 0) + 1
            continue
        if identity in seen:
            excluded["duplicate"] = excluded.get("duplicate", 0) + 1
            continue
        seen.add(identity)
        multiplier = Decimal(str(match.get("price_multiplier", 1)))
        adjusted_price = (asking_price * multiplier).quantize(CENT, rounding=ROUND_HALF_UP)
        method = str(match.get("method") or "unknown")
        accepted.append((adjusted_price, collected_at, identity, asking_price, method))
        match_methods[method] = match_methods.get(method, 0) + 1

    accepted.sort(key=lambda row: row[0])
    prices = [row[0] for row in accepted]
    if not prices:
        return {
            "estimated_sale_price": None, "confidence": "none", "comparables_count": 0,
            "raw_comparables_count": len(raw_comparables), "excluded": excluded,
            "match_methods": match_methods, "reason": "no_fresh_comparable_olx_offers",
            "valuation_status": "missing_comparables",
        }

    q1 = _quantile(prices, Decimal("0.25"))
    q3 = _quantile(prices, Decimal("0.75"))
    iqr = q3 - q1
    lower_fence = q1 - Decimal("1.5") * iqr
    upper_fence = q3 + Decimal("1.5") * iqr
    cleaned = [row for row in accepted if lower_fence <= row[0] <= upper_fence]
    outlier_count = len(accepted) - len(cleaned)
    cleaned_prices = [row[0] for row in cleaned]

    if len(cleaned_prices) < min_samples:
        return {
            "estimated_sale_price": None, "confidence": "none",
            "comparables_count": len(cleaned_prices), "fresh_comparables_count": len(accepted),
            "outlier_count": outlier_count,
            "median_price": float(_quantile(cleaned_prices, Decimal("0.5"))) if cleaned_prices else None,
            "q1_price": float(_quantile(cleaned_prices, Decimal("0.25"))) if cleaned_prices else None,
            "excluded": excluded, "match_methods": match_methods,
            "reason": "too_few_comparables_after_outlier_filter",
            "valuation_status": "insufficient_comparables",
        }

    median = _quantile(cleaned_prices, Decimal("0.5"))
    conservative_q1 = _quantile(cleaned_prices, Decimal("0.25"))
    estimated = (conservative_q1 * (Decimal("1") - haircut / Decimal("100"))).quantize(CENT, rounding=ROUND_HALF_UP)
    spread_ratio = (q3 - q1) / median if median else Decimal("1")
    confidence = "high" if len(cleaned_prices) >= 10 and spread_ratio <= Decimal("0.20") and all(row[4] in {"exact_model", "legacy_exact_model"} for row in cleaned) else "medium"
    latest = max(row[1] for row in cleaned)

    return {
        "estimated_sale_price": float(estimated), "confidence": confidence,
        "comparables_count": len(cleaned_prices), "fresh_comparables_count": len(accepted),
        "outlier_count": outlier_count, "median_price": float(median),
        "q1_price": float(conservative_q1), "q3_price": float(q3),
        "haircut_percent": float(haircut),
        "spread_q1_q3_percent": float((spread_ratio * Decimal("100")).quantize(Decimal("0.1"))),
        "latest_comparable_at": latest.isoformat(), "excluded": excluded,
        "match_methods": match_methods, "reason": None,
        "valuation_status": "estimated_from_fresh_olx_asking_prices",
        "note": "Conservative estimate from active asking prices, not confirmed transaction prices. Cross-model prices are specification-adjusted.",
    }
