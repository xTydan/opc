"""Conservative component extraction from user-provided PC descriptions.

No network access, marketplace scraping, price lookup, or guessed prices.
Every result includes the text evidence that triggered the match.
"""
from __future__ import annotations

import re
from typing import Any


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n,;:-")


def _add(
    found: list[dict[str, Any]],
    category: str,
    model: str,
    confidence: str,
    evidence: str,
    **extra: Any,
) -> None:
    model = _clean(model)
    evidence = _clean(evidence)
    if not model or not evidence:
        return
    key = (category, model.casefold())
    if any((item["category"], item["model"].casefold()) == key for item in found):
        return
    item: dict[str, Any] = {
        "category": category,
        "model": model,
        "confidence": confidence,
        "evidence": evidence,
        "estimated_sale_price": None,
        "valuation_status": "needs_market_comparables",
    }
    item.update(extra)
    found.append(item)


CPU_PATTERNS = [
    re.compile(r"\b(?:AMD\s+)?Ryzen\s+[3579]\s+\d{4,5}[A-Z]{0,4}\b", re.I),
    re.compile(r"\b(?:Intel\s+)?Core\s+i[3579]\s*[- ]?\s*\d{4,5}[A-Z]{0,3}\b", re.I),
    re.compile(r"\bIntel\s+Core\s+Ultra\s+[579]\s+\d{3,4}[A-Z]{0,3}\b", re.I),
]

GPU_PATTERNS = [
    re.compile(
        r"\b(?:(?:NVIDIA|GeForce)\s+)*(?:RTX|GTX)\s*\d{3,4}\s*(?:Ti|SUPER|XT)?\b",
        re.I,
    ),
    re.compile(r"\b(?:AMD\s+)?Radeon\s+RX\s*\d{3,4}\s*(?:XT|XTX)?\b", re.I),
    re.compile(r"\bRX\s*\d{3,4}\s*(?:XT|XTX)?\b", re.I),
]

RAM_PATTERN = re.compile(
    r"\b(?:(?P<count>\d{1,2})\s*[x×]\s*)?"
    r"(?P<size>\d{1,3})\s*GB\s*(?P<kind>DDR\s?[45])\b",
    re.I,
)

STORAGE_PATTERNS = [
    re.compile(
        r"\b(?P<size>\d+(?:[.,]\d+)?)\s*(?P<unit>TB|GB)\s*"
        r"(?P<kind>NVMe|SSD|HDD)\b",
        re.I,
    ),
    re.compile(
        r"\b(?P<kind>NVMe|SSD|HDD)\s*"
        r"(?P<size>\d+(?:[.,]\d+)?)\s*(?P<unit>TB|GB)\b",
        re.I,
    ),
]

MOTHERBOARD_PATTERN = re.compile(
    r"\b(?P<brand>MSI|ASUS|Gigabyte|ASRock)\s+"
    r"(?P<model>(?:MAG\s+|TUF\s+|ROG\s+|PRIME\s+|AORUS\s+|"
    r"Steel\s+Legend\s+|Pro\s+)?"
    r"(?:B\d{3,4}|X\d{3,4}|Z\d{3,4}|H\d{3,4})"
    r"[A-Z0-9\- ]{0,24})\b",
    re.I,
)

CHIPSET_PATTERN = re.compile(r"\b(B\d{3,4}|X\d{3,4}|Z\d{3,4}|H\d{3,4})\b", re.I)

PSU_CONTEXT_PATTERN = re.compile(
    r"\b(?:zasilacz|psu|power supply)\b[^.\n,;]{0,55}",
    re.I,
)


def parse_description(description: str) -> dict[str, Any]:
    """Extract likely parts while preserving uncertainty and source evidence."""
    if not isinstance(description, str):
        raise ValueError("description must be a string")

    text = description.strip()
    found: list[dict[str, Any]] = []

    for pattern in CPU_PATTERNS:
        match = pattern.search(text)
        if match:
            _add(found, "cpu", match.group(0), "high", match.group(0))
            break

    for pattern in GPU_PATTERNS:
        match = pattern.search(text)
        if match:
            _add(found, "gpu", match.group(0), "high", match.group(0))
            break

    for match in RAM_PATTERN.finditer(text):
        sticks = int(match.group("count") or "1")
        size = int(match.group("size"))
        memory_type = re.sub(r"\s+", "", match.group("kind").upper())
        total = sticks * size
        model = f"{sticks}x{size}GB {memory_type}" if match.group("count") else f"{size}GB {memory_type}"
        _add(
            found,
            "ram",
            model,
            "high",
            match.group(0),
            capacity_gb=total,
            memory_type=memory_type,
            stick_count=sticks,
        )

    storage_seen: set[tuple[str, str]] = set()
    for pattern in STORAGE_PATTERNS:
        for match in pattern.finditer(text):
            size = match.group("size").replace(",", ".")
            unit = match.group("unit").upper()
            kind = match.group("kind").upper()
            model = f"{size}{unit} {kind}"
            key = (size, kind)
            if key in storage_seen:
                continue
            storage_seen.add(key)
            _add(found, "storage", model, "medium", match.group(0), capacity=size + unit, storage_type=kind)

    motherboard = MOTHERBOARD_PATTERN.search(text)
    if motherboard:
        model = f"{motherboard.group('brand')} {motherboard.group('model')}"
        _add(found, "motherboard", model, "medium", motherboard.group(0))
    else:
        chipset = CHIPSET_PATTERN.search(text)
        if chipset:
            _add(
                found,
                "motherboard",
                f"Chipset {chipset.group(1).upper()} (exact board model unknown)",
                "low",
                chipset.group(0),
            )

    psu_context = PSU_CONTEXT_PATTERN.search(text)
    if psu_context:
        wattage = re.search(r"\b(\d{3,4})\s?W\b", psu_context.group(0), re.I)
        if wattage:
            _add(
                found,
                "psu",
                f"Power supply {wattage.group(1)}W (brand/model unknown)",
                "low",
                psu_context.group(0),
                wattage=int(wattage.group(1)),
            )

    return {
        "components": found,
        "recognized_count": len(found),
        "unrecognized_categories": [
            category
            for category in ("cpu", "gpu", "motherboard", "ram", "storage", "psu")
            if not any(item["category"] == category for item in found)
        ],
        "note": "Extracted from description only. Prices were not estimated.",
    }
