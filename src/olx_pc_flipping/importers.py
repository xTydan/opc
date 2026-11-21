"""Load listing imports from JSON or spreadsheet-friendly CSV files."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


CSV_REQUIRED_COLUMNS = {"title", "price", "description"}
CSV_OPTIONAL_COLUMNS = {
    "id", "url", "location", "date_added", "collected_at", "status", "currency"
}


def parse_pln_price(raw: Any, row_number: int) -> int | float:
    """Parse common Polish price formats such as '1 599 zł' or '1.599,50'."""
    if raw is None:
        raise ValueError(f"CSV row {row_number}: missing price")
    value = str(raw).strip().replace("\u00a0", " ")
    value = value.replace("PLN", "").replace("pln", "").replace("zł", "").replace("ZŁ", "")
    value = "".join(value.split())
    if not value:
        raise ValueError(f"CSV row {row_number}: missing price")

    if "," in value and "." in value:
        # Polish format: 1.599,50 -> 1599.50
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    elif value.count(".") >= 1:
        # Treat groups of three digits as thousands separators.
        parts = value.split(".")
        if all(part.isdigit() for part in parts) and len(parts[-1]) == 3 and all(len(p) == 3 for p in parts[1:]):
            value = "".join(parts)

    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"CSV row {row_number}: invalid price {raw!r}") from None
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"CSV row {row_number}: price must be finite and >= 0")
    if amount == amount.to_integral_value():
        return int(amount)
    return float(amount)


def _read_csv(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("CSV import is empty")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    except csv.Error:
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV needs a header row")
    fields = {str(name).strip() for name in reader.fieldnames if name}
    missing = CSV_REQUIRED_COLUMNS - fields
    if missing:
        raise ValueError("CSV missing required columns: " + ", ".join(sorted(missing)))

    now = datetime.now(timezone.utc).isoformat()
    listings: list[dict[str, Any]] = []
    for row_number, row in enumerate(reader, start=2):
        normalized = {str(key).strip(): (value.strip() if isinstance(value, str) else value)
                      for key, value in row.items() if key is not None}
        if not any(value for value in normalized.values()):
            continue
        title = normalized.get("title", "")
        description = normalized.get("description", "")
        if not title and not description:
            raise ValueError(f"CSV row {row_number}: title or description is required")
        price = parse_pln_price(normalized.get("price"), row_number)
        currency = normalized.get("currency") or "PLN"
        identity = normalized.get("id") or normalized.get("url")
        if not identity:
            identity = hashlib.sha256(
                f"{row_number}|{title}|{price}|{normalized.get('location', '')}".encode("utf-8")
            ).hexdigest()[:16]

        listings.append({
            "id": str(identity),
            "title": title,
            "url": normalized.get("url") or None,
            "price": price,
            "currency": currency,
            "location": normalized.get("location") or None,
            "date_added": normalized.get("date_added") or None,
            "collected_at": normalized.get("collected_at") or now,
            "status": normalized.get("status") or "unverified",
            "description": description,
        })

    if not listings:
        raise ValueError("CSV contains no listing rows")
    return {
        "schema_version": 1,
        "source": "csv-import",
        "exported_at": now,
        "listings": listings,
    }


def load_import_file(path: Path) -> dict[str, Any]:
    """Load a supported import file and normalize it to schema version 1."""
    if not path.exists() or not path.is_file():
        raise ValueError(f"Import file does not exist: {path}")
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return _read_csv(path)
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}") from None
        if not isinstance(payload, dict):
            raise ValueError("JSON import must be an object")
        if payload.get("schema_version") != 1:
            raise ValueError("JSON import must use schema_version 1")
        if not isinstance(payload.get("listings"), list):
            raise ValueError("JSON import must contain listings[]")
        return payload
    raise ValueError("Supported import formats: .json and .csv")
