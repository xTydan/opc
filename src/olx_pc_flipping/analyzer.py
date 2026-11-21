"""Deterministic profitability calculations for imported PC listings.

This module does not fetch OLX data and does not invent component prices.
Prices must be supplied by a trusted valuation step or by the import file.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .component_parser import parse_description

CENT = Decimal("0.01")
VALID_CONFIDENCE = {"low", "medium", "high"}


def money(value: Any, field_name: str) -> Decimal:
    """Convert a value to a non-negative PLN amount."""
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid monetary value for {field_name}: {value!r}") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"Monetary value for {field_name} must be finite and >= 0")
    return result.quantize(CENT, rounding=ROUND_HALF_UP)


def analyze_listing(listing: dict[str, Any], default_costs: dict[str, Any] | None = None,
                    target_profit: Any = 0) -> dict[str, Any]:
    """Calculate resale revenue, net profit, ROI and max purchase price."""
    if not isinstance(listing, dict):
        raise ValueError("Each listing must be a JSON object")

    listing_price = money(listing.get("price"), "listing.price")
    default_costs = default_costs or {}
    listing_costs = listing.get("additional_costs") or {}
    if not isinstance(listing_costs, dict):
        raise ValueError("additional_costs must be an object")

    costs = {
        key: money(listing_costs.get(key, value), f"additional_costs.{key}")
        for key, value in default_costs.items()
    }
    for key, value in listing_costs.items():
        if key not in costs:
            costs[key] = money(value, f"additional_costs.{key}")

    total_extra_costs = sum(costs.values(), Decimal("0.00"))
    component_total = Decimal("0.00")
    component_details: list[dict[str, Any]] = []
    missing_valuations: list[str] = []

    components = listing.get("components") or []
    if not isinstance(components, list):
        raise ValueError("components must be an array")

    parsed_description = None
    if not components and listing.get("description"):
        parsed_description = parse_description(str(listing["description"]))
        components = parsed_description["components"]

    for index, component in enumerate(components):
        if not isinstance(component, dict):
            raise ValueError(f"components[{index}] must be an object")
        model = str(component.get("model") or component.get("category") or f"component {index + 1}")
        raw_price = component.get("estimated_sale_price")
        if raw_price is None:
            missing_valuations.append(model)
            component_details.append({
                "category": component.get("category", "unknown"),
                "model": model,
                "estimated_sale_price": None,
                "confidence": component.get("confidence", "unknown"),
                "comparable_listings": component.get("comparable_listings", 0),
                "evidence": component.get("evidence"),
                "valuation_status": "missing"
            })
            continue

        sale_price = money(raw_price, f"components[{index}].estimated_sale_price")
        component_total += sale_price
        confidence = str(component.get("confidence") or "low").lower()
        if confidence not in VALID_CONFIDENCE:
            confidence = "low"
        comparable_count = component.get("comparable_listings", 0)
        if not isinstance(comparable_count, int) or comparable_count < 0:
            comparable_count = 0

        component_details.append({
            "category": component.get("category", "unknown"),
            "model": model,
            "estimated_sale_price": float(sale_price),
            "confidence": confidence,
            "comparable_listings": comparable_count,
            "evidence": component.get("evidence"),
            "valuation_status": "provided"
        })

    total_investment = listing_price + total_extra_costs
    gross_difference = component_total - listing_price
    net_profit = component_total - total_investment
    roi = (net_profit / total_investment * Decimal("100")) if total_investment else Decimal("0")
    required_profit = money(target_profit, "target_profit")
    max_purchase_price = max(
        Decimal("0.00"),
        component_total - total_extra_costs - required_profit
    )

    return {
        "id": listing.get("id"),
        "title": listing.get("title"),
        "url": listing.get("url"),
        "location": listing.get("location"),
        "status": listing.get("status", "unknown"),
        "listing_price": float(listing_price),
        "component_value_total": float(component_total),
        "gross_difference_before_costs": float(gross_difference),
        "additional_costs": {key: float(value) for key, value in costs.items()},
        "additional_costs_total": float(total_extra_costs),
        "total_investment": float(total_investment),
        "estimated_net_profit": float(net_profit),
        "roi_percent": float(roi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "target_profit": float(required_profit),
        "maximum_purchase_price_for_target_profit": float(max_purchase_price),
        "missing_valuations": missing_valuations,
        "valuation_complete": not missing_valuations and bool(components),
        "components_parsed_from_description": parsed_description is not None,
        "unrecognized_categories": (
            parsed_description["unrecognized_categories"] if parsed_description else []
        ),
        "components": component_details
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
    default_costs = analysis_config.get("default_additional_costs", {})
    target_profit = analysis_config.get("minimum_target_profit", 0)

    results = [
        analyze_listing(item, default_costs=default_costs, target_profit=target_profit)
        for item in listings
    ]
    results.sort(
        key=lambda item: (
            item["estimated_net_profit"],
            item["roi_percent"],
            item["valuation_complete"]
        ),
        reverse=True
    )
    return {
        "schema_version": 1,
        "source": payload.get("source", "unknown"),
        "exported_at": payload.get("exported_at"),
        "analyzed_count": len(results),
        "results": results
    }
