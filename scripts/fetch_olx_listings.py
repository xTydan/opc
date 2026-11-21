#!/usr/bin/env python3
"""Download descriptions from a manually collected list of public OLX URLs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from olx_pc_flipping.olx_fetcher import fetch_listings, load_urls  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch public OLX Poland listing descriptions from a text file of URLs."
    )
    parser.add_argument("input", type=Path, help="UTF-8 .txt file with one OLX listing URL per line")
    parser.add_argument("--output", type=Path, default=Path("data/imports/olx-listings.json"))
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between page requests (default: 3)")
    args = parser.parse_args()
    if args.delay < 1.0:
        parser.error("--delay must be at least 1 second")

    try:
        urls = load_urls(args.input)
        payload = fetch_listings(urls, delay_seconds=args.delay)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    successful = sum(1 for item in payload["listings"] if item["fetch_status"] == "ok")
    print(f"Saved {len(payload['listings'])} listings to {args.output}")
    print(f"Descriptions retrieved: {successful}/{len(payload['listings'])}")
    if successful < len(payload["listings"]):
        print("Some pages could not be read. Check fetch_status/http_status in the output JSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
