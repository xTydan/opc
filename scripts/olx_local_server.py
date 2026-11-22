"""Local asynchronous bridge for the OLX browser helper extension."""
from __future__ import annotations

import json
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from olx_pc_flipping.olx_fetcher import fetch_listings  # noqa: E402

OUTPUT = ROOT / "data" / "imports" / "olx-listings.json"
MAX_URLS = 250
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def run_job(job_id: str, urls: list[str]) -> None:
    try:
        with JOBS_LOCK:
            JOBS[job_id].update({"state": "running", "total": len(urls), "completed": 0})
        # Fetch one at a time. The fetcher itself applies the 3-second delay.
        def report_progress(completed: int, total: int, last_status: str | None) -> None:
            with JOBS_LOCK:
                JOBS[job_id].update({
                    "completed": completed,
                    "total": total,
                    "last_status": last_status,
                })

        result = fetch_listings(urls, delay_seconds=3.0, progress_callback=report_progress)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        temp_output = OUTPUT.with_suffix(".tmp")
        temp_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp_output.replace(OUTPUT)
        successful = sum(1 for item in result["listings"] if item["fetch_status"] == "ok")
        with JOBS_LOCK:
            JOBS[job_id].update({
                "state": "completed",
                "completed": len(result["listings"]),
                "successful": successful,
                "output": str(OUTPUT),
            })
    except Exception as exc:
        with JOBS_LOCK:
            JOBS[job_id].update({"state": "failed", "error": str(exc)})


class Handler(BaseHTTPRequestHandler):
    def _headers(self, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", "null"))
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _write_json(self, status: int, payload: dict) -> None:
        try:
            self._headers(status)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # The extension popup may close while a request is in flight.
            pass

    def do_OPTIONS(self) -> None:
        if not self.headers.get("Origin", "").startswith("chrome-extension://"):
            self._write_json(403, {"error": "extension origin required"})
            return
        self._write_json(204, {})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(200, {"status": "ready"})
            return
        if parsed.path == "/status":
            if not self.headers.get("Origin", "").startswith("chrome-extension://"):
                self._write_json(403, {"error": "extension origin required"})
                return
            job_id = parse_qs(parsed.query).get("job", [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                snapshot = dict(job) if job else None
            if snapshot is None:
                self._write_json(404, {"error": "unknown job"})
            else:
                self._write_json(200, snapshot)
            return
        self._write_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/collect":
            self._write_json(404, {"error": "not found"})
            return
        if not self.headers.get("Origin", "").startswith("chrome-extension://"):
            self._write_json(403, {"error": "extension origin required"})
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
            job_id = uuid.uuid4().hex
            with JOBS_LOCK:
                JOBS[job_id] = {"state": "queued", "total": len(unique), "completed": 0}
            threading.Thread(target=run_job, args=(job_id, unique), daemon=True).start()
            self._write_json(202, {"job_id": job_id, "total": len(unique), "state": "queued"})
        except (ValueError, json.JSONDecodeError) as exc:
            self._write_json(400, {"error": str(exc)})

    def log_message(self, fmt: str, *args) -> None:
        print("[OLX bridge] " + fmt % args)


def main() -> None:
    print("OLX helper local server: http://127.0.0.1:8765")
    print("Keep this window open while collecting listings. Ctrl+C stops it.")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()


if __name__ == "__main__":
    main()
