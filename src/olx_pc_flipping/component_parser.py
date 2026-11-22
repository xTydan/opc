"""Conservative component extraction from noisy Polish PC listings.

The parser extracts only facts evidenced by the supplied title/description.
It never fetches marketplace pages, estimates prices, or fills unknown details.
"""
from __future__ import annotations

import re
from typing import Any


def _clean(value: str) -> str:
    value = value.replace("\u00a0", " ").replace("\u200b", "")
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
    # Common shorthand in Polish listings: "i5 14400" / "i3-12100F".
    re.compile(r"\b(?:Intel\s+)?i[3579]\s*[- ]?\s*\d{4,5}[A-Z]{0,3}\b", re.I),
]

GPU_PATTERNS = [
    re.compile(
        r"\b(?:(?:NVIDIA|GeForce)\s+)*(?:RTX|GTX)\s*\d{3,4}\s*(?:Ti|SUPER|XT)?\b",
        re.I,
    ),
    re.compile(r"\b(?:AMD\s+)?Radeon\s+RX\s*\d{3,4}\s*(?:XTX|XT)?\b", re.I),
    re.compile(r"\bRX\s*\d{3,4}\s*(?:XTX|XT)?\b", re.I),
]

GPU_BRAND_PATTERN = re.compile(
    r"\b(ZOTAC|ASUS|MSI|GIGABYTE|PALIT|PNY|GAINWARD|INNO3D|"
    r"SAPPHIRE|XFX|POWERCOLOUR|POWERCOLOR|EVGA|ASROCK)\b",
    re.I,
)
GPU_VRAM_PATTERN = re.compile(r"\b(4|6|8|10|12|16|20|24)\s*GB\b", re.I)
GPU_VARIANT_PATTERN = re.compile(
    r"\b(TWIN\s*EDGE|AMP\s*EXTREME|GAMING\s*TRIO|GAMING\s*X|GAMING\s*OC|"
    r"ROG\s*STRIX|TUF\s*GAMING|VENTUS\s*[23]?X|AORUS\s*(?:MASTER|ELITE)?|"
    r"WINDFORCE|EAGLE|NITRO\+?|PULSE|RED\s*DEVIL|HELLHOUND|PHANTOM\s*GAMING|"
    r"CHALLENGER|MECH|ARMOR|DUAL|GHOST|TRINITY)\b",
    re.I,
)

RAM_SPEED_PATTERN = re.compile(r"\b(?P<speed>1600|1866|2133|2400|2666|2933|3000|3200|3600|4000|4400|4800|5200|5600|6000|6200|6400|6800|7000|7200|7600|8000)\s*MHz\b", re.I)

RAM_PATTERNS = [
    re.compile(
        r"\b(?:(?P<count>\d{1,2})\s*[x×]\s*)?"
        r"(?P<size>\d{1,3})\s*GB\s*(?P<kind>DDR\s?[345])\b",
        re.I,
    ),
    re.compile(
        r"\b(?P<kind>DDR\s?[345])\s*(?P<size>\d{1,3})\s*GB\b",
        re.I,
    ),
]

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
    r"Seagate|ADATA|Goodram|Lexar|Patriot|WD|Kioxia|TeamGroup)\b",
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

COOLING_WORD = r"(?:chłodzenie|chlodzenie|chtodzenie|chlodz[e]?nie)"
FIELD_NAMES = (
    r"(?:"
    r"chłodzenie|chlodzenie|chtodzenie|obudowa|wentylatory|"
    r"podświetlenie|podswietlenie|system operacyjny|wydajność|wydajnosc|"
    r"płyta główna|plyta glowna|procesor|karta graficzna|"
    r"pamięć RAM|pamiec RAM|dysk|zasilacz"
    r")"
)
FIELD_STOP = rf"(?=\s*(?:[-–—]\s*)?{FIELD_NAMES}\s*:|[.;]|$)"

PSU_CONTEXT_PATTERN = re.compile(
    r"\b(?:zasilacz|psu|power supply)\s*[:\-]?\s*(?P<details>.*?)" + FIELD_STOP,
    re.I,
)
COOLER_CONTEXT_PATTERN = re.compile(
    rf"\b{COOLING_WORD}\s+procesora\s*[:\-]?\s*(?P<details>.*?)"
    + FIELD_STOP,
    re.I,
)
CASE_CONTEXT_PATTERN = re.compile(
    r"\bobudowa\s*[:\-]?\s*(?P<details>.*?)"
    r"(?=\s*(?:[-–—]\s*)?(?:wentylatory|podświetlenie|podswietlenie|"
    r"system operacyjny|wydajność|wydajnosc)\s*:|[.;]|$)",
    re.I,
)


def _extract_gpu(text: str, found: list[dict[str, Any]]) -> None:
    for pattern in GPU_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        model_core = _clean(match.group(0))
        context_start = max(0, match.start() - 42)
        context_end = min(len(text), match.end() + 75)
        context = text[context_start:context_end]

        brand_match = GPU_BRAND_PATTERN.search(context)
        manufacturer = brand_match.group(1).upper() if brand_match else None
        gaming = bool(re.search(r"\bGAMING\b", context, re.I))
        variant_match = GPU_VARIANT_PATTERN.search(context)
        board_variant = _clean(variant_match.group(1)).upper() if variant_match else None

        # VRAM must be adjacent to the GPU mention; do not borrow the PC's RAM size.
        # The title may say "RTX 4060 24GB RAM" while the actual GPU is\n        # specified later as "RTX 4060 8GB". Never treat system RAM as VRAM.\n        after_model = text[match.end(): min(len(text), match.end() + 120)]
        vram_match = re.search(r"\\b(4|6|8|10|12|16|20|24)\\s*GB\\b(?!\\s*RAM\\b)", after_model, re.I)
        vram = int(vram_match.group(1)) if vram_match else None

        display_model = model_core
        if manufacturer:
            display_model = f"{manufacturer} {display_model}"
        if vram:
            display_model += f" {vram}GB"
        if board_variant:
            display_model += f" {board_variant}"
        elif gaming and manufacturer:
            display_model += " Gaming series"

        _add(
            found,
            "gpu",
            display_model,
            "medium" if manufacturer or vram else "high",
            context,
            manufacturer=manufacturer,
            gpu_model=model_core,
            gpu_family="NVIDIA GeForce" if re.search(r"RTX|GTX", model_core, re.I) else "AMD Radeon",
            gpu_series=re.sub(r"^(?:(?:NVIDIA|GeForce|AMD|Radeon)\s*)+", "", model_core, flags=re.I),
            vram_gb=vram,
            product_line="Gaming" if gaming else None,
            board_variant=board_variant,
            exact_variant_known=board_variant is not None,
        )
        return


def _extract_ram(text: str, found: list[dict[str, Any]]) -> None:
    seen: set[tuple[int, str, int | None]] = set()
    for pattern in RAM_PATTERNS:
        for match in pattern.finditer(text):
            size = int(match.group("size"))
            memory_type = re.sub(r"\s+", "", match.group("kind").upper())
            count_text = match.groupdict().get("count")
            count = int(count_text) if count_text else None
            key = (size, memory_type, count)
            if key in seen:
                continue
            seen.add(key)

            nearby = text[match.start():min(len(text), match.end() + 32)]
            speed_match = RAM_SPEED_PATTERN.search(nearby)
            speed = int(speed_match.group("speed")) if speed_match else None
            model = f"{count}x{size}GB {memory_type}" if count else f"{size}GB {memory_type}"
            if speed:
                model += f" {speed}MHz"
            _add(
                found,
                "ram",
                model,
                "high" if count is not None else "medium",
                match.group(0),
                capacity_gb=size * count if count is not None else size,
                memory_type=memory_type,
                stick_count=count,
                stick_count_known=count is not None,
                speed_mhz=speed,
            )


def _extract_storage(text: str, found: list[dict[str, Any]]) -> None:
    seen: set[tuple[str, str, str | None]] = set()
    for pattern in STORAGE_PATTERNS:
        for match in pattern.finditer(text):
            size = match.group("size").replace(",", ".")
            unit = match.group("unit").upper()
            kind = match.group("kind").upper()
            prefix = text[max(0, match.start() - 45):match.start()]
            brand_matches = list(STORAGE_BRANDS.finditer(prefix))
            brand = brand_matches[-1].group("brand").upper() if brand_matches else None
            storage_kind = "NVMe SSD" if kind == "NVME" else kind
            key = (size, unit, kind)
            if key in seen:
                continue
            seen.add(key)

            model = f"{brand} {size}{unit} {storage_kind}" if brand else f"{size}{unit} {storage_kind}"
            evidence_start = max(0, match.start() - (30 if brand else 0))
            capacity_gb = int(float(size) * (1000 if unit == "TB" else 1))
            interface = "NVMe" if kind == "NVME" else None
            _add(
                found,
                "storage",
                model,
                "medium",
                text[evidence_start:match.end()],
                capacity=f"{size}{unit}",
                capacity_gb=capacity_gb,
                storage_type=storage_kind,
                interface=interface,
                manufacturer=brand,
            )



    # Some listings identify drives by model followed by capacity, e.g.
    # "NVMe PCIe: KIOXIA KBG40ZNV, 256 GB" or "HDD: WDC WD5000AZLX, 500 GB".
    contextual_storage = re.compile(
        r"\\b(?P<brand>Western\\s+Digital|WDC|Kingston|Crucial|Samsung|"
        r"Seagate|ADATA|Goodram|Lexar|Patriot|WD|Kioxia|TeamGroup|Micron)\\s+"
        r"(?P<model>[A-Z0-9][A-Z0-9._-]{2,})\\s*[, (:-]+\\s*"
        r"(?P<size>\\d+(?:[.,]\\d+)?)\\s*(?P<unit>TB|GB)\\b",
        re.I,
    )
    for match in contextual_storage.finditer(text):
        prefix = text[max(0, match.start() - 120):match.start()]
        kind_match = re.search(r"\\b(NVMe|SSD|HDD)\\b", prefix, re.I)
        if not kind_match:
            continue
        kind = kind_match.group(1).upper()
        size = match.group("size").replace(",", ".")
        unit = match.group("unit").upper()
        brand = match.group("brand").upper()
        storage_kind = "NVMe SSD" if kind == "NVME" else kind
        model = f"{brand} {match.group('model')} {size}{unit} {storage_kind}"
        capacity_gb = int(float(size) * (1000 if unit == "TB" else 1))
        _add(
            found,
            "storage",
            model,
            "medium",
            text[max(0, match.start() - 35):match.end()],
            capacity=f"{size}{unit}",
            capacity_gb=capacity_gb,
            storage_type=storage_kind,
            interface="NVMe" if kind == "NVME" else None,
            manufacturer=brand,
        )


def _extract_motherboard(text: str, found: list[dict[str, Any]]) -> None:
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


def _extract_psu(text: str, found: list[dict[str, Any]]) -> None:
    match = PSU_CONTEXT_PATTERN.search(text)
    if not match:
        return
    details = _clean(match.group("details"))
    wattage_match = re.search(r"\b(\d{3,4})\s?W\b", details, re.I)
    efficiency_match = re.search(
        r"\b80\s*PLUS(?:\s*(BRONZE|SILVER|GOLD|PLATINUM|TITANIUM))?\b",
        details,
        re.I,
    )
    model_part = re.split(
        r",|\b\d{3,4}\s?W\b|\b80\s*PLUS\b",
        details,
        maxsplit=1,
        flags=re.I,
    )[0]
    model_part = _clean(model_part)
    wattage = int(wattage_match.group(1)) if wattage_match else None
    efficiency = efficiency_match.group(0).upper() if efficiency_match else None
    if not model_part and wattage is None:
        return

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
        manufacturer="Bandit Power" if re.search(r"\bBandit\s+Power\b", model_part, re.I) else None,
        wattage=wattage,
        efficiency=efficiency,
        exact_model_known=bool(re.search(r"[A-Z].*\d", model_part, re.I)),
        quality_assessment="unknown_requires_independent_review",
    )


def _extract_cooler(text: str, found: list[dict[str, Any]]) -> None:
    match = COOLER_CONTEXT_PATTERN.search(text)
    if not match:
        return
    details = _clean(match.group("details"))
    if details:
        _add(
            found,
            "cooler",
            f"CPU cooler: {details}",
            "low",
            details,
            exact_model_known=False,
        )


def _extract_case(text: str, found: list[dict[str, Any]]) -> None:
    match = CASE_CONTEXT_PATTERN.search(text)
    if not match:
        return
    details = _clean(match.group("details"))
    if details:
        _add(
            found,
            "case",
            "Gaming case (exact model unknown)",
            "low",
            details,
            exact_model_known=False,
        )


def _extract_fans(text: str, found: list[dict[str, Any]]) -> None:
    match = re.search(r"\b(?P<count>\d{1,2})\s*(?:wentylator(?:y|ów)?|fan(?:s)?)\b", text, re.I)
    if match:
        count = int(match.group("count"))
        _add(
            found,
            "fans",
            f"{count} case fans",
            "medium",
            match.group(0),
            count=count,
        )


def parse_description(description: str) -> dict[str, Any]:
    """Extract likely parts while preserving uncertainty and source evidence."""
    if not isinstance(description, str):
        raise ValueError("description must be a string")

    text = re.sub(r"[\s\u00a0]+", " ", description).replace("\u200b", "").strip()
    found: list[dict[str, Any]] = []

    for pattern in CPU_PATTERNS:
        match = pattern.search(text)
        if match:
            cpu_model = _clean(match.group(0))
            cpu_details: dict[str, Any] = {"platform_family": "Intel Core" if re.search(r"Intel|Core\s+i", cpu_model, re.I) else "AMD Ryzen"}
            intel_match = re.search(r"i[3579]\s*[- ]?\s*(\d{4,5})([A-Z]{0,3})", cpu_model, re.I)
            ryzen_match = re.search(r"Ryzen\s+[3579]\s+(\d{4,5})([A-Z]{0,4})", cpu_model, re.I)
            if intel_match:
                digits = intel_match.group(1)
                cpu_details["model_number"] = digits + (intel_match.group(2) or "").upper()
                cpu_details["generation"] = int(digits[:2]) if len(digits) == 5 else int(digits[0])
            elif ryzen_match:
                cpu_details["model_number"] = ryzen_match.group(1) + (ryzen_match.group(2) or "").upper()
                cpu_details["model_series"] = ryzen_match.group(1)[0]
            _add(found, "cpu", cpu_model, "high", match.group(0), **cpu_details)
            break

    _extract_gpu(text, found)
    _extract_ram(text, found)
    _extract_storage(text, found)
    _extract_motherboard(text, found)
    _extract_psu(text, found)
    _extract_cooler(text, found)
    _extract_case(text, found)
    _extract_fans(text, found)

    required_categories = ("cpu", "gpu", "motherboard", "ram", "storage", "psu")
    all_categories = required_categories + ("cooler", "case", "fans")
    missing = [
        category
        for category in all_categories
        if not any(item["category"] == category for item in found)
    ]
    return {
        "components": found,
        "recognized_count": len(found),
        "unrecognized_categories": missing,
        "missing_required_categories": [
            category for category in required_categories if category in missing
        ],
        "inventory_complete": not any(category in missing for category in required_categories),
        "note": "Extracted from supplied text only. Prices were not estimated.",
    }
