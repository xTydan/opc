"""Fetch publicly accessible OLX listing pages into the project's JSON import format.

This client makes ordinary, rate-limited HTTP requests. It does not log in, solve
CAPTCHAs, rotate identities, or bypass access controls.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (compatible; PrivatePCListingResearch/1.0; +https://github.com/xTydan/opc)"
OLX_HOSTS = {"olx.pl", "www.olx.pl"}


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.json_scripts: list[str] = []
        self._script_type = ""
        self._script_data: list[str] = []
        self._in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "meta":
            key = values.get("property") or values.get("name") or values.get("itemprop")
            content = values.get("content")
            if key and content:
                self.meta[key.casefold()] = content.strip()
        elif tag.casefold() == "script":
            self._script_type = values.get("type", "").casefold()
            self._script_data = []
        elif tag.casefold() == "title":
            self._in_title = True

    def handle_data(self, data: str) -> None:
        if self._script_type in {"application/ld+json", "application/json"}:
            self._script_data.append(data)
        if self._in_title:
            self.title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "script":
            if self._script_type in {"application/ld+json", "application/json"}:
                value = "".join(self._script_data).strip()
                if value:
                    self.json_scripts.append(value)
            self._script_type = ""
            self._script_data = []
        elif tag.casefold() == "title":
            self._in_title = False


def _clean(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _extract_from_json_scripts(scripts: list[str]) -> tuple[str, str, int | None, str | None]:
    descriptions: list[str] = []
    titles: list[str] = []
    prices: list[int] = []
    locations: list[str] = []
    for raw in scripts:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, RecursionError):
            continue
        for node in _walk_json(payload):
            for key in ("description", "descriptionText", "body"):
                text = _clean(node.get(key))
                if len(text) >= 35 and text not in descriptions:
                    descriptions.append(text)
            for key in ("name", "title", "headline"):
                text = _clean(node.get(key))
                if 5 <= len(text) <= 180 and text not in titles:
                    titles.append(text)
            offers = node.get("offers")
            if isinstance(offers, dict):
                raw_price = offers.get("price")
                if raw_price is not None:
                    try:
                        prices.append(int(float(str(raw_price).replace(",", "."))))
                    except (TypeError, ValueError):
                        pass
            raw_price = node.get("price")
            if isinstance(raw_price, (int, float)) and raw_price > 0:
                prices.append(int(raw_price))
            address = node.get("address")
            if isinstance(address, dict):
                locality = _clean(address.get("addressLocality"))
                region = _clean(address.get("addressRegion"))
                location = ", ".join(part for part in (locality, region) if part)
                if location and location not in locations:
                    locations.append(location)
    description = max(descriptions, key=len) if descriptions else ""
    title = titles[0] if titles else ""
    price = prices[0] if prices else None
    location = locations[0] if locations else None
    return description, title, price, location


def extract_listing_data(html: str) -> dict[str, Any]:
    parser = _PageParser()
    parser.feed(html)
    description, title, price, location = _extract_from_json_scripts(parser.json_scripts)
    title = title or _clean(parser.meta.get("og:title")) or _clean("".join(parser.title_parts))
    description = (
        description
        or _clean(parser.meta.get("og:description"))
        or _clean(parser.meta.get("description"))
    )
    if price is None:
        raw_price = parser.meta.get("product:price:amount") or parser.meta.get("og:price:amount")
        if raw_price:
            try:
                price = int(float(raw_price.replace(",", ".")))
            except ValueError:
                pass
    return {
        "title": title,
        "description": description,
        "price": price,
        "location": location,
        "extraction_method": "structured_json_or_meta",
        "description_complete": bool(description) and len(description) >= 35,
    }


def _validate_olx_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in OLX_HOSTS or not parsed.path.startswith("/d/"):
        raise ValueError(f"Only public OLX Poland listing URLs are accepted: {url}")
    return url.strip()


def fetch_listing(url: str, timeout: int = 20) -> dict[str, Any]:
    try:
        safe_url = _validate_olx_url(url)
        request = Request(safe_url, headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.5",
        })
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(8_000_000)
            charset = response.headers.get_content_charset() or "utf-8"
        if "html" not in content_type.casefold():
            raise ValueError(f"Unexpected content type: {content_type}")
        html = raw.decode(charset, errors="replace")
        result = extract_listing_data(html)
        result.update({"url": safe_url, "http_status": status, "fetch_status": "ok" if result["description"] else "description_not_found"})
        return result
    except HTTPError as exc:
        reason = "blocked_or_rate_limited" if exc.code in {403, 429, 503} else "http_error"
        return {"url": safe_url, "fetch_status": reason, "http_status": exc.code, "error": str(exc)}
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {"url": url, "fetch_status": "fetch_error", "error": str(exc)}


def load_urls(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    urls = []
    for line in text.splitlines():
        value = line.strip().strip('"')
        if not value or value.startswith("#") or value.casefold() == "url":
            continue
        if "," in value and value.split(",", 1)[0].casefold() in {"url", "link"}:
            value = value.split(",", 1)[1].strip().strip('"')
        if value.startswith("https://"):
            urls.append(value)
    if not urls:
        raise ValueError("No OLX listing URLs found in input file")
    return list(dict.fromkeys(urls))


def fetch_listings(urls: list[str], delay_seconds: float = 3.0, progress_callback=None) -> dict[str, Any]:
    listings = []
    for index, url in enumerate(urls):
        result = fetch_listing(url)
        listings.append({
            "id": url,
            "title": result.get("title") or "Opis niepobrany",
            "url": url,
            "price": result.get("price"),
            "currency": "PLN",
            "location": result.get("location"),
            "date_added": None,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "status": "unverified",
            "description": result.get("description", ""),
            "fetch_status": result.get("fetch_status"),
            "fetch_error": result.get("error"),
            "http_status": result.get("http_status"),
            "description_complete": result.get("description_complete", False),
            "extraction_method": result.get("extraction_method"),
        })
        if index < len(urls) - 1 and delay_seconds > 0:
            time.sleep(delay_seconds)
        if progress_callback is not None:
            progress_callback(index + 1, len(urls), result.get("fetch_status"))
    return {
        "schema_version": 1,
        "source": "olx-public-page-fetch",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "listings": listings,
    }
