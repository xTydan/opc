"""Import and query freely licensed hardware benchmark datasets.

This module deliberately does not scrape benchmark websites. It accepts
user-downloaded or officially published CSV/JSON datasets and preserves
provenance, license, sample count and observation date with every score.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


def normalize_hardware_name(value: str) -> str:
    """Normalize punctuation/case without discarding meaningful model numbers."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _positive_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 and number < float("inf") else None


def load_benchmark_dataset(path: str | Path) -> dict[str, Any]:
    """Load normalized benchmark records from JSON or CSV.

    Required dataset metadata: source, license, updated_at.
    Required row fields: category, model, benchmark, score.
    Optional row fields: samples, url, methodology.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError(f"Benchmark dataset not found: {file_path}")
    if file_path.suffix.casefold() == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
    elif file_path.suffix.casefold() == ".csv":
        with file_path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise ValueError("Benchmark CSV contains no records")
        metadata_fields = ("source", "license", "updated_at")
        for field in metadata_fields:
            if not str(rows[0].get(field) or "").strip():
                raise ValueError(
                    f"Benchmark CSV requires metadata columns: {', '.join(metadata_fields)}"
                )
            expected = str(rows[0][field]).strip()
            if any(str(row.get(field) or "").strip() != expected for row in rows):
                raise ValueError(f"Benchmark CSV metadata column '{field}' must be consistent across rows")
        payload = {
            "source": rows[0]["source"],
            "license": rows[0]["license"],
            "updated_at": rows[0]["updated_at"],
            "records": rows,
        }
    else:
        raise ValueError("Supported benchmark dataset formats: .json and .csv")

    if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
        raise ValueError("Benchmark dataset must contain records[]")
    source = str(payload.get("source") or "").strip()
    license_name = str(payload.get("license") or "").strip()
    updated = _date(payload.get("updated_at"))
    if not source or not license_name or not updated:
        raise ValueError("Benchmark dataset requires source, license and ISO updated_at")
    if not payload["records"]:
        raise ValueError("Benchmark dataset contains no records")

    cleaned = []
    for index, row in enumerate(payload["records"], start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Benchmark record {index} must be an object")
        category = str(row.get("category") or "").casefold().strip()
        model = str(row.get("model") or "").strip()
        benchmark = str(row.get("benchmark") or "").strip()
        score = _positive_number(row.get("score"))
        if category not in {"cpu", "gpu", "storage", "ram"} or not model or not benchmark or score is None:
            raise ValueError(f"Benchmark record {index} has invalid category/model/benchmark/score")
        samples = row.get("samples")
        try:
            samples = int(samples) if samples not in (None, "") else None
        except (TypeError, ValueError):
            samples = None
        cleaned.append({
            "category": category,
            "model": model,
            "normalized_model": normalize_hardware_name(model),
            "benchmark": benchmark,
            "score": score,
            "samples": samples,
            "methodology": row.get("methodology"),
            "url": row.get("url"),
            "source": source,
            "license": license_name,
            "dataset_updated_at": updated.isoformat(),
        })
    return {"source": source, "license": license_name, "updated_at": updated.isoformat(), "records": cleaned}


def find_benchmark_score(
    dataset: dict[str, Any],
    *,
    category: str,
    model: str,
    benchmark: str,
    max_age_days: int = 180,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Return an exact normalized model score; never guess cross-model scores."""
    if max_age_days < 1:
        raise ValueError("max_age_days must be >= 1")
    today = as_of or date.today()
    updated = _date(dataset.get("updated_at"))
    if updated is None or (today - updated).days < 0 or (today - updated).days > max_age_days:
        return {"score": None, "status": "stale_or_invalid_dataset"}
    key = normalize_hardware_name(model)
    matches = [
        row for row in dataset.get("records", [])
        if row.get("category") == category.casefold()
        and row.get("benchmark", "").casefold() == benchmark.casefold()
        and row.get("normalized_model") == key
    ]
    if not matches:
        return {"score": None, "status": "model_not_found"}
    # If duplicate rows exist, prefer the row with the largest sample count.
    matches.sort(key=lambda row: row.get("samples") or 0, reverse=True)
    result = dict(matches[0])
    result["status"] = "matched"
    return result
