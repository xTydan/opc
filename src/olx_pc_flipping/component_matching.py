"""Cross-model matching for used PC component comparables.

A comparable is matched by category-relevant specifications, not brand/model
name alone. Cross-model price normalization is deliberately bounded.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def _number(value: Any) -> Decimal | None:
    try:
        result = Decimal(str(value))
        return result if result.is_finite() and result > 0 else None
    except Exception:
        return None


def _specs(component: dict[str, Any]) -> dict[str, Any]:
    result = dict(component.get("attributes") or {})
    result.update(component.get("specs") or {})
    # Parser currently stores attributes at the component's top level.
    for key, value in component.items():
        if key not in {"comparables", "attributes", "specs"} and key not in result:
            result[key] = value
    return result


def _ratio(target: Any, candidate: Any) -> Decimal | None:
    left, right = _number(target), _number(candidate)
    if left is None or right is None:
        return None
    return left / right


def match_comparable(target: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Return eligibility, a bounded price multiplier, and the match rationale."""
    category = str(target.get("category") or "").casefold()
    candidate_category = str(candidate.get("category") or "").casefold()
    if category != candidate_category or not category:
        return {"matched": False, "reason": "different_category"}

    t, c = _specs(target), _specs(candidate)
    target_model = str(target.get("model") or "").casefold().strip()
    candidate_model = str(candidate.get("model") or "").casefold().strip()
    exact_model = bool(target_model and candidate_model and target_model == candidate_model)

    # Same exact product remains the strongest comparison, even if the listing
    # does not expose enough structured specifications for cross-model matching.
    if exact_model:
        return {"matched": True, "method": "exact_model", "price_multiplier": 1.0, "similarity": 1.0}

    multiplier = Decimal("1")
    checks: list[str] = []

    if category in {"cpu", "gpu"}:
        target_benchmark = t.get("benchmark_name")
        candidate_benchmark = c.get("benchmark_name")
        if not target_benchmark or not candidate_benchmark:
            return {"matched": False, "reason": "benchmark_name_required_for_cross_model_match"}
        if str(target_benchmark).casefold() != str(candidate_benchmark).casefold():
            return {"matched": False, "reason": "different_benchmark_methodology"}
        target_score = _number(t.get("benchmark_score"))
        candidate_score = _number(c.get("benchmark_score"))
        if target_score is None or candidate_score is None:
            return {"matched": False, "reason": "benchmark_score_required_for_cross_model_match"}
        performance = target_score / candidate_score
        if performance < Decimal("0.88") or performance > Decimal("1.12"):
            return {"matched": False, "reason": "performance_too_different"}
        if category == "gpu":
            tv, cv = _number(t.get("vram_gb")), _number(c.get("vram_gb"))
            if tv is None or cv is None:
                return {"matched": False, "reason": "vram_required_for_cross_model_match"}
            if abs(tv - cv) > 4:
                return {"matched": False, "reason": "vram_too_different"}
        ts, cs = t.get("socket"), c.get("socket")
        if category == "cpu" and ts and cs and str(ts).casefold() != str(cs).casefold():
            return {"matched": False, "reason": "different_socket"}
        # Performance and price are not linear. Use a dampened, capped adjustment.
        multiplier = performance ** Decimal("0.65")
        checks.append("benchmark_performance")

    elif category == "storage":
        target_capacity = _number(t.get("capacity_gb"))
        candidate_capacity = _number(c.get("capacity_gb"))
        if target_capacity is None or candidate_capacity is None:
            return {"matched": False, "reason": "capacity_required"}
        capacity_ratio = target_capacity / candidate_capacity
        if capacity_ratio < Decimal("0.80") or capacity_ratio > Decimal("1.25"):
            return {"matched": False, "reason": "capacity_too_different"}
        target_kind = str(t.get("storage_type") or "").casefold().replace(" ", "")
        candidate_kind = str(c.get("storage_type") or "").casefold().replace(" ", "")
        if not target_kind or not candidate_kind:
            return {"matched": False, "reason": "storage_type_required"}
        if target_kind != candidate_kind:
            return {"matched": False, "reason": "different_storage_type"}
        target_interface = str(t.get("interface") or "").casefold()
        candidate_interface = str(c.get("interface") or "").casefold()
        if not target_interface or not candidate_interface:
            return {"matched": False, "reason": "storage_interface_required"}
        if target_interface != candidate_interface:
            return {"matched": False, "reason": "different_interface"}
        performance_ratio = _ratio(t.get("performance_score"), c.get("performance_score"))
        if performance_ratio is not None and not (Decimal("0.65") <= performance_ratio <= Decimal("1.50")):
            return {"matched": False, "reason": "storage_performance_too_different"}
        multiplier = capacity_ratio ** Decimal("0.70")
        if performance_ratio is not None:
            multiplier *= performance_ratio ** Decimal("0.20")
            checks.append("storage_performance")
        checks.extend(["capacity", "storage_type_or_interface"])

    elif category == "ram":
        target_type, candidate_type = t.get("memory_type"), c.get("memory_type")
        if not target_type or not candidate_type or str(target_type).casefold() != str(candidate_type).casefold():
            return {"matched": False, "reason": "memory_generation_required_and_must_match"}
        capacity_ratio = _ratio(t.get("capacity_gb"), c.get("capacity_gb"))
        if capacity_ratio is None or not (Decimal("0.85") <= capacity_ratio <= Decimal("1.18")):
            return {"matched": False, "reason": "ram_capacity_too_different"}
        speed_ratio = _ratio(t.get("speed_mhz"), c.get("speed_mhz"))
        if speed_ratio is not None and not (Decimal("0.80") <= speed_ratio <= Decimal("1.25")):
            return {"matched": False, "reason": "ram_speed_too_different"}
        multiplier = capacity_ratio ** Decimal("0.75")
        if speed_ratio is not None:
            multiplier *= speed_ratio ** Decimal("0.10")
            checks.append("memory_speed")
        checks.append("memory_generation_and_capacity")

    elif category == "motherboard":
        required = ("socket", "memory_type", "form_factor")
        for field in required:
            if not t.get(field) or not c.get(field):
                return {"matched": False, "reason": f"{field}_required_for_cross_model_match"}
            if str(t[field]).casefold() != str(c[field]).casefold():
                return {"matched": False, "reason": f"different_{field}"}
        target_tier, candidate_tier = _number(t.get("chipset_tier")), _number(c.get("chipset_tier"))
        if target_tier is not None and candidate_tier is not None and abs(target_tier - candidate_tier) > 1:
            return {"matched": False, "reason": "chipset_tier_too_different"}
        checks.extend(required)

    elif category == "psu":
        wattage_ratio = _ratio(t.get("wattage"), c.get("wattage"))
        if wattage_ratio is None or not (Decimal("0.85") <= wattage_ratio <= Decimal("1.18")):
            return {"matched": False, "reason": "psu_wattage_too_different"}
        target_quality, candidate_quality = _number(t.get("quality_tier")), _number(c.get("quality_tier"))
        if target_quality is None or candidate_quality is None:
            return {"matched": False, "reason": "independent_quality_tier_required"}
        if abs(target_quality - candidate_quality) > 1:
            return {"matched": False, "reason": "psu_quality_too_different"}
        multiplier = wattage_ratio ** Decimal("0.35")
        checks.extend(["wattage", "independently_assessed_quality_tier"])

    else:
        return {"matched": False, "reason": "cross_model_matching_not_supported_for_category"}

    # Avoid letting noisy specifications create implausible price extrapolations.
    multiplier = max(Decimal("0.85"), min(Decimal("1.15"), multiplier))
    return {
        "matched": True,
        "method": "specification_similarity",
        "price_multiplier": float(multiplier),
        "similarity": 0.9,
        "matched_on": checks,
    }
