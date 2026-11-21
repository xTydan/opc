#!/usr/bin/env python3
"""Analyze an imported JSON file of PC listings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from olx_pc_flipping.analyzer import analyze_import  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze imported PC listings.")
    parser.add_argument("input", type=Path, help="Path to listings JSON")
    parser.add_argument("--config", type=Path, default=ROOT / "config.example.json")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        config = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else {}
        report = analyze_import(payload, config)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
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
