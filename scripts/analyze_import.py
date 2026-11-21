#!/usr/bin/env python3
"""Analyze a batch of listings imported from JSON or CSV."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from olx_pc_flipping.analyzer import analyze_import  # noqa: E402
from olx_pc_flipping.importers import load_import_file  # noqa: E402
from olx_pc_flipping.hardware_benchmarks import load_benchmark_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze imported PC listings from JSON or CSV.")
    parser.add_argument("input", type=Path, help="Path to listings .json or .csv")
    parser.add_argument("--config", type=Path, default=ROOT / "config.example.json")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--benchmarks", type=Path, default=None, help="Optional licensed benchmark dataset (.json or .csv)")
    args = parser.parse_args()

    try:
        payload = load_import_file(args.input)
        config = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else {}
        benchmark_dataset = load_benchmark_dataset(args.benchmarks) if args.benchmarks else None
        report = analyze_import(payload, config, benchmark_dataset=benchmark_dataset)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Saved report: {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
