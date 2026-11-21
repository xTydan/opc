"""Conservative component extraction from user-provided PC descriptions.

No network access, marketplace scraping, price lookup, or guessed prices.
Every result includes source evidence and explicit uncertainty.
"""
from __future__ import annotations

import re
from typing import Any


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t\r\n,;:-–—")


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
    r"(?P<size>\d{1,3})\s*GB\s*(?P<kind>DDR\s?[345])\b",
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

STORAGE_BRANDS = re.compile(
    r"\b(?P<brand>VIST|Kingston|Crucial|Samsung|Western\s+Digital|"
    r"Seagate|ADATA|Adata|Goodram|Lexar|Patriot|WD)\b",
    re.I,
)

MOTHERBOARD_PATTERN = re.compile(
    r"\b(?P<brand>MSI|ASUS|Gigabyte|ASRock)\s+"
    r"(?P<model>(?:MAG\s+|TUF\s+|ROG\s+|PRIME\s+|AORUS\s+|"
    r"Steel\s+Legend\s+|Pro\s+)?"
    r"(?:B\d{3,4}|X\d{3,4}|Z\d{3,4}|H\d{3,4})"
    r"[A-Z0-9\- ]{0,24})\b",
    re.I,
)

MOTHERBOARD_ID_PATTERN = re.compile(
    r"\b(?P<brand>MSI|ASUS|Gigabyte|ASRock)\s+"
    r"(?P<model>MS-\d{4,5}|[A-Z]{2,5}-[A-Z0-9]{3,8})\b",
    re.I,
)

CHIPSET_PATTERN = re.compile(r"\b(B\d{3,4}|X\d{3,4}|Z\d{3,4}|H\d{3,4})\b", re.I)

FIELD_STOP = (
    r"(?=\s*(?:[-–—]\s*)?(?:chłodzenie|chlodzenie|obudowa|wentylatory|"
    r"podświetlenie|system operacyjny|wydajność|plyta glowna|płyta główna)\s*:|[.;]|$)"
)

PSU_CONTEXT_PATTERN = re.compile(
    r"\b(?:zasilacz|psu|power supply)\s*[:\-]?\s*(?P<details>.*?)" + FIELD_STOP,
    re.I,
)

COOLER_CONTEXT_PATTERN = re.compile(
    r"\b(?:chłodzenie|chlodzenie)\s+procesora\s*[:\-]?\s*(?P<details>.*?)" + FIELD_STOP,
    re.I,
)

CASE_CONTEXT_PATTERN = re.compile(
    r"\bobudowa\s*[:\-]?\s*(?P<details>.*?)"
    r"(?=\s*(?:[-–—]\s*)?(?:wentylatory|podświetlenie|system operacyjny|wydajność)\s*:|[.;]|$)",
    re.I,
)


def _extract_gpu(text: str, found: list[dict[str, Any]]) -> None:
    for pattern in GPU_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        model_core = _clean(match.group(0))
        context = text[max(0, match.start() - 28): min(len(text), match.end() + 55)]
        vram_match = re.search(r"\b(4|6|8|10|12|16|20|24)\s*GB\b", context, re.I)
        vram = int(vram_match.group(1)) if vram_match else None
        brand_match = re.search(r"\b(ZOTAC|ASUS|MSI|GIGABYTE|GIGABYTE|PALIT|PNY|GAINWARD|INNO3D|SAPPHIRE|XFX)\b", context, re.I)
        manufacturer = brand_match.group(1).upper() if brand_match else None
        gaming = bool(re.search(r"\bGAMING\b", context, re.I))

        display_model = model_core
        if manufacturer:
            display_model = f"{manufacturer} {display_model}"
        if vram:
            display_model += f" {vram}GB"
        if gaming and manufacturer:
            display_model = f"{manufacturer} Gaming {model_core} {vram}GB" if vram else f"{manufacturer} Gaming {model_core}"

        _add(
            found,
            "gpu",
            display_model,
            "medium" if manufacturer or vram else "high",
            context,
            manufacturer=manufacturer,
            vram_gb=vram,
            exact_variant_known=False,
        )
        return


def parse_description(description: str) -> dict[str, Any]:
    """Extract likely parts while preserving uncertainty and source evidence."""
    if not isinstance(description, str):
        raise ValueError("description must be a string")

    text = re.sub(r"\s+", " ", description).strip()
    found: list[dict[str, Any]] = []

    for pattern in CPU_PATTERNS:
        match = pattern.search(text)
        if match:
            _add(found, "cpu", match.group(0), "high", match.group(0))
            break

    _extract_gpu(text, found)

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
            "medium" if not match.group("count") else "high",
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
            prefix = text[max(0, match.start() - 35):match.start()]
            brand_matches = list(STORAGE_BRANDS.finditer(prefix))
            brand = brand_matches[-1].group("brand").upper() if brand_matches else None
            model = f"{brand} {kind} {size}{unit}" if brand else f"{size}{unit} {kind}"
            key = (size, kind)
            if key in storage_seen:
                continue
            storage_seen.add(key)
            _add(
                found,
                "storage",
                model,
                "medium" if brand else "medium",
                match.group(0) if not brand else f"{brand} {match.group(0)}",
                capacity=size + unit,
                storage_type=kind,
                manufacturer=brand,
            )

    motherboard = MOTHERBOARD_PATTERN.search(text)
    motherboard_id = MOTHERBOARD_ID_PATTERN.search(text)
    if motherboard:
        model = f"{motherboard.group('brand')} {motherboard.group('model')}"
        _add(found, "motherboard", model, "medium", motherboard.group(0))
    elif motherboard_id:
        model = f"{motherboard_id.group('brand')} {motherboard_id.group('model')}"
        _add(
            found,
            "motherboard",
            model,
            "medium",
            motherboard_id.group(0),
            board_identifier=motherboard_id.group("model").upper(),
            exact_retail_model_known=False,
        )
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

    psu_match = PSU_CONTEXT_PATTERN.search(text)
    if psu_match:
        details = _clean(psu_match.group("details"))
        wattage_match = re.search(r"\b(\d{3,4})\s?W\b", details, re.I)
        efficiency_match = re.search(r"\b80\s*PLUS(?:\s*(BRONZE|SILVER|GOLD|PLATINUM|TITANIUM))?\b", details, re.I)
        model_part = re.split(r",|\b\d{3,4}\s?W\b|\b80\s*PLUS\b", details, maxsplit=1, flags=re.I)[0]
        model_part = _clean(model_part)
        wattage = int(wattage_match.group(1)) if wattage_match else None
        efficiency = efficiency_match.group(0).upper() if efficiency_match else None
        if model_part or wattage:
            name = model_part or "Power supply"
            if wattage:
                name += f" {wattage}W"
            if efficiency:
                name += f" {efficiency}"
            _add(
                found,
                "psu",
                name,
                "medium" if model_part and wattage else "low",
                details,
                wattage=wattage,
                efficiency=efficiency,
                exact_model_known=bool(re.search(r"[A-Z].*\d", model_part, re.I)),
            )

    cooler_match = COOLER_CONTEXT_PATTERN.search(text)
    if cooler_match:
        details = _clean(cooler_match.group("details"))
        if details:
            _add(
                found,
                "cooler",
                f"CPU cooler: {details}",
                "low",
                details,
                exact_model_known=False,
            )

    case_match = CASE_CONTEXT_PATTERN.search(text)
    if case_match:
        details = _clean(case_match.group("details"))
        if details:
            _add(
                found,
                "case",
                "Gaming case (exact model unknown)",
                "low",
                details,
                exact_model_known=False,
            )

    categories = ("cpu", "gpu", "motherboard", "ram", "storage", "psu", "cooler", "case")
    return {
        "components": found,
        "recognized_count": len(found),
        "unrecognized_categories": [
            category
            for category in categories
            if not any(item["category"] == category for item in found)
        ],
        "note": "Extracted from description only. Prices were not estimated.",
    }
