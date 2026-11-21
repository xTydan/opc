"""Local bridge for the OLX browser helper extension."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from olx_pc_flipping.olx_fetcher import fetch_listings  # noqa: E402

OUTPUT = ROOT / "data" / "imports" / "olx-listings.json"
MAX_URLS = 250


class Handler(BaseHTTPRequestHandler):
    def _headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "null"))
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin", "")
        if not origin.startswith("chrome-extension://"):
            self._headers(403)
            return
        self._headers(204)

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/health":
            self._headers(404)
            self.wfile.write(b'{"error":"not found"}')
            return
        self._headers()
        self.wfile.write(json.dumps({"status": "ready"}).encode())

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/collect":
            self._headers(404)
            self.wfile.write(b'{"error":"not found"}')
            return
        origin = self.headers.get("Origin", "")
        if not origin.startswith("chrome-extension://"):
            self._headers(403)
            self.wfile.write(b'{"error":"extension origin required"}')
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 1_000_000:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            urls = payload.get("urls") if isinstance(payload, dict) else None
            if not isinstance(urls, list) or not urls:
                raise ValueError("No listing URLs supplied")
            if len(urls) > MAX_URLS:
                raise ValueError(f"Limit is {MAX_URLS} URLs per batch")
            unique = list(dict.fromkeys(str(url) for url in urls))
            result = fetch_listings(unique, delay_seconds=3.0)
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
            successful = sum(1 for item in result["listings"] if item["fetch_status"] == "ok")
            response = {"saved": len(result["listings"]), "successful": successful, "output": str(OUTPUT)}
            self._headers(200)
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
        except Exception as exc:
            self._headers(400)
            self.wfile.write(json.dumps({"error": str(exc)}).encode())

    def log_message(self, fmt: str, *args) -> None:
        print("[OLX bridge] " + fmt % args)


def main() -> None:
    host, port = "127.0.0.1", 8765
    print("OLX helper local server: http://127.0.0.1:8765")
    print("Keep this window open while collecting listings. Ctrl+C stops it.")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
