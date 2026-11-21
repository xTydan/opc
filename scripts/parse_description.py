#!/usr/bin/env python3
"""Parse a text file containing a PC listing description."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from olx_pc_flipping.component_parser import parse_description  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract PC components from a description.")
    parser.add_argument("input", type=Path, help="UTF-8 text file with a listing description")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        result = parse_description(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Saved parsed components: {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
