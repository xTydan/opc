"""Conservative profitability analysis for imported PC listings.

The module does not fetch marketplace data and never invents missing prices.
OLX comparables must be supplied separately and pass freshness/model checks.
A full profit estimate is withheld until all core component categories and
their valuations are present.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .component_parser import parse_description
from .valuation_engine import estimate_component_value

CENT = Decimal("0.01")
VALID_CONFIDENCE = {"low", "medium", "high"}
CORE_CATEGORIES = ("cpu", "gpu", "motherboard", "ram", "storage", "psu")


def money(value: Any, field_name: str) -> Decimal:
    """Convert a value to a non-negative PLN amount."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid monetary value for {field_name}: {value!r}") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"Monetary value for {field_name} must be finite and >= 0")
    return result.quantize(CENT, rounding=ROUND_HALF_UP)


def analyze_listing(
    listing: dict[str, Any],
    default_costs: dict[str, Any] | None = None,
    target_profit: Any = 0,
    minimum_roi_percent: Any = 0,
    valuation_options: dict[str, Any] | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Analyze one listing; do not publish a full profit figure for an incomplete PC."""
    if not isinstance(listing, dict):
        raise ValueError("Each listing must be a JSON object")
    if str(listing.get("currency", "PLN")).upper() != "PLN":
        raise ValueError("Only PLN listings are supported by the current calculator")

    listing_price = money(listing.get("price"), "listing.price")
    default_costs = default_costs or {}
    listing_costs = listing.get("additional_costs") or {}
    if not isinstance(default_costs, dict):
        raise ValueError("default_additional_costs must be an object")
    if not isinstance(listing_costs, dict):
        raise ValueError("additional_costs must be an object")

    costs = {
        key: money(listing_costs.get(key, value), f"additional_costs.{key}")
        for key, value in default_costs.items()
    }
    for key, value in listing_costs.items():
        if key not in costs:
            costs[key] = money(value, f"additional_costs.{key}")

    options = valuation_options or {}
    min_comparables = int(options.get("minimum_comparable_listings", 5))
    max_age_hours = int(options.get("maximum_valuation_age_hours", 24))
    haircut_percent = options.get("conservative_haircut_percent", 3)
    total_extra_costs = sum(costs.values(), Decimal("0.00"))
    known_component_total = Decimal("0.00")
    component_details: list[dict[str, Any]] = []
    missing_valuations: list[str] = []
    missing_optional_valuations: list[str] = []
    low_confidence_components: list[str] = []
    low_confidence_core_components: list[str] = []

    components = listing.get("components") or []
    if not isinstance(components, list):
        raise ValueError("components must be an array")

    parsed_description = None
    if not components:
        description_parts = [
            str(listing.get("title") or "").strip(),
            str(listing.get("description") or "").strip(),
        ]
        source_text = " ".join(part for part in description_parts if part)
        if source_text:
            parsed_description = parse_description(source_text)
            components = parsed_description["components"]

    seen_categories: set[str] = set()
    internal_component_keys = {
        "category", "model", "confidence", "evidence", "estimated_sale_price",
        "valuation_status", "comparable_listings", "valuation_confidence",
        "comparables", "model_key",
    }
    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise ValueError(f"components[{index}] must be an object")
        category = str(component.get("category") or "unknown").lower()
        if category != "unknown":
            seen_categories.add(category)
        model = str(component.get("model") or category or f"component {index + 1}")

        identification_confidence = str(component.get("confidence") or "low").lower()
        if identification_confidence not in VALID_CONFIDENCE:
            identification_confidence = "low"

        valuation_data = None
        raw_price = component.get("estimated_sale_price")
        if component.get("comparables") is not None:
            valuation_data = estimate_component_value(
                component,
                min_samples=min_comparables,
                max_age_hours=max_age_hours,
                haircut_percent=haircut_percent,
                as_of=as_of,
            )
            # Fresh exact-model OLX comparisons take precedence over any stale manual figure.
            raw_price = valuation_data.get("estimated_sale_price")

        if raw_price is None:
            if category in CORE_CATEGORIES or category == "unknown":
                missing_valuations.append(model)
            else:
                missing_optional_valuations.append(model)
            component_details.append({
                "category": category,
                "model": model,
                "estimated_sale_price": None,
                "confidence": (
                    valuation_data.get("confidence", "none")
                    if valuation_data else "none"
                ),
                "identification_confidence": identification_confidence,
                "comparable_listings": (
                    valuation_data.get("comparables_count", 0)
                    if valuation_data else component.get("comparable_listings", 0)
                ),
                "evidence": component.get("evidence"),
                "attributes": {key: value for key, value in component.items() if key not in internal_component_keys},
                "valuation": valuation_data,
                "valuation_status": (
                    valuation_data.get("valuation_status", "missing")
                    if valuation_data else "missing"
                ),
            })
            if identification_confidence == "low":
                low_confidence_components.append(model)
                if category in CORE_CATEGORIES:
                    low_confidence_core_components.append(model)
            continue

        sale_price = money(raw_price, f"components[{index}].estimated_sale_price")
        known_component_total += sale_price

        if valuation_data:
            price_confidence = valuation_data.get("confidence", "none")
            comparable_count = valuation_data.get("comparables_count", 0)
            valuation_status = valuation_data.get("valuation_status", "estimated")
        else:
            price_confidence = str(component.get("valuation_confidence") or component.get("confidence") or "low").lower()
            if price_confidence not in VALID_CONFIDENCE:
                price_confidence = "low"
            comparable_count = component.get("comparable_listings", 0)
            valuation_status = "manually_provided"
        if not isinstance(comparable_count, int) or comparable_count < 0:
            comparable_count = 0

        if identification_confidence == "low" or price_confidence == "low":
            low_confidence_components.append(model)
            if category in CORE_CATEGORIES:
                low_confidence_core_components.append(model)
        component_details.append({
            "category": category,
            "model": model,
            "estimated_sale_price": float(sale_price),
            "confidence": price_confidence,
            "identification_confidence": identification_confidence,
            "comparable_listings": comparable_count,
            "evidence": component.get("evidence"),
            "attributes": {key: value for key, value in component.items() if key not in internal_component_keys},
            "valuation": valuation_data,
            "valuation_status": valuation_status,
        })

    missing_required_categories = [
        category for category in CORE_CATEGORIES if category not in seen_categories
    ]
    if parsed_description:
        missing_required_categories = parsed_description.get(
            "missing_required_categories", missing_required_categories
        )

    inventory_complete = not missing_required_categories
    valuations_complete = not missing_valuations and bool(components)
    valuation_complete = inventory_complete and valuations_complete

    total_investment = listing_price + total_extra_costs
    required_profit = money(target_profit, "target_profit")
    try:
        minimum_roi = Decimal(str(minimum_roi_percent))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("minimum_roi_percent must be a valid number") from None
    if not minimum_roi.is_finite() or minimum_roi < 0:
        raise ValueError("minimum_roi_percent must be finite and >= 0")

    if valuation_complete:
        component_value_total: float | None = float(known_component_total)
        gross_difference: float | None = float(known_component_total - listing_price)
        net_profit: float | None = float(known_component_total - total_investment)
        roi_value = (
            (known_component_total - total_investment) / total_investment * Decimal("100")
            if total_investment else Decimal("0")
        )
        roi_percent: float | None = float(
            roi_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
        profit_price_cap = known_component_total - total_extra_costs - required_profit
        roi_multiplier = Decimal("1") + minimum_roi / Decimal("100")
        roi_price_cap = known_component_total / roi_multiplier - total_extra_costs
        max_purchase_price: float | None = float(max(
            Decimal("0.00"),
            min(profit_price_cap, roi_price_cap),
        ))
        meets_target = (
            net_profit >= required_profit
            and roi_value >= minimum_roi
            and not low_confidence_core_components
        )
        analysis_status = "ready"
    else:
        component_value_total = None
        gross_difference = None
        net_profit = None
        roi_percent = None
        max_purchase_price = None
        meets_target = False
        if missing_required_categories:
            analysis_status = "incomplete_inventory"
        else:
            analysis_status = "missing_component_valuations"

    return {
        "id": listing.get("id"),
        "title": listing.get("title"),
        "description": listing.get("description"),
        "url": listing.get("url"),
        "location": listing.get("location"),
        "date_added": listing.get("date_added"),
        "collected_at": listing.get("collected_at"),
        "status": listing.get("status", "unknown"),
        "listing_price": float(listing_price),
        "known_component_value_partial": float(known_component_total),
        "component_value_total": component_value_total,
        "gross_difference_before_costs": gross_difference,
        "additional_costs": {key: float(value) for key, value in costs.items()},
        "additional_costs_total": float(total_extra_costs),
        "total_investment": float(total_investment),
        "estimated_net_profit": net_profit,
        "roi_percent": roi_percent,
        "target_profit": float(required_profit),
        "minimum_roi_percent": float(minimum_roi),
        "maximum_purchase_price_for_target_profit": max_purchase_price,
        "meets_target": meets_target,
        "analysis_status": analysis_status,
        "inventory_complete": inventory_complete,
        "valuations_complete": valuations_complete,
        "valuation_complete": valuation_complete,
        "missing_required_categories": missing_required_categories,
        "missing_valuations": missing_valuations,
        "missing_optional_valuations": missing_optional_valuations,
        "low_confidence_components": sorted(set(low_confidence_components)),
        "low_confidence_core_components": sorted(set(low_confidence_core_components)),
        "profit_basis": (
            "Core component value only; unvalued optional parts are excluded conservatively."
            if missing_optional_valuations else "All detected and required components valued."
        ),
        "components_parsed_from_description": parsed_description is not None,
        "unrecognized_categories": (
            parsed_description["unrecognized_categories"] if parsed_description else []
        ),
        "components": component_details,
    }


def analyze_import(payload: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Analyze all listings in a versioned import payload."""
    if not isinstance(payload, dict):
        raise ValueError("Import must be a JSON object")
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported or missing schema_version; expected 1")
    listings = payload.get("listings")
    if not isinstance(listings, list):
        raise ValueError("listings must be an array")

    analysis_config = (config or {}).get("analysis", {})
    if not isinstance(analysis_config, dict):
        raise ValueError("config.analysis must be an object")
    default_costs = analysis_config.get("default_additional_costs", {})
    target_profit = analysis_config.get("minimum_target_profit", 0)
    minimum_roi = analysis_config.get("minimum_roi_percent", 0)
    valuation_options = {
        "minimum_comparable_listings": analysis_config.get("minimum_comparable_listings", 5),
        "maximum_valuation_age_hours": analysis_config.get("maximum_valuation_age_hours", 24),
        "conservative_haircut_percent": analysis_config.get("conservative_haircut_percent", 3),
    }

    results = [
        analyze_listing(
            item,
            default_costs=default_costs,
            target_profit=target_profit,
            minimum_roi_percent=minimum_roi,
            valuation_options=valuation_options,
        )
        for item in listings
    ]
    results.sort(
        key=lambda item: (
            item["meets_target"],
            item["estimated_net_profit"] if item["estimated_net_profit"] is not None else Decimal("-Infinity"),
            item["known_component_value_partial"],
        ),
        reverse=True,
    )
    return {
        "schema_version": 1,
        "source": payload.get("source", "unknown"),
        "exported_at": payload.get("exported_at"),
        "analyzed_count": len(results),
        "results": results,
    }
