from __future__ import annotations

import unittest

from olx_pc_flipping.olx_fetcher import _validate_olx_url, extract_listing_data, load_urls


class OlxFetcherTests(unittest.TestCase):
    def test_extracts_description_and_metadata_from_json_ld(self):
        html = """
        <html><head><title>Komputer gamingowy</title>
        <script type="application/ld+json">
        {"@type":"Product","name":"PC Ryzen","description":"Sprzedam komputer gamingowy z procesorem Ryzen 5 5600 i kartą RTX 3060, 16 GB RAM oraz dyskiem SSD 1 TB.","offers":{"price":"1999"},"address":{"addressLocality":"Bielsko-Biała"}}
        </script></head></html>
        """
        result = extract_listing_data(html)
        self.assertIn("Ryzen 5 5600", result["description"])
        self.assertEqual(result["price"], 1999)
        self.assertEqual(result["location"], "Bielsko-Biała")

    def test_extracts_fallback_meta_description(self):
        result = extract_listing_data('<html><head><meta name="description" content="Długi opis komputera gamingowego z procesorem Intel i kartą graficzną NVIDIA."></head></html>')
        self.assertIn("Długi opis", result["description"])

    def test_rejects_non_olx_or_non_listing_urls(self):
        for url in ("https://example.com/d/oferta/123", "https://www.olx.pl/", "http://www.olx.pl/d/oferta/123"):
            with self.assertRaises(ValueError):
                _validate_olx_url(url)

    def test_loads_unique_urls(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "urls.txt"
            path.write_text("https://www.olx.pl/d/oferta/a\nhttps://www.olx.pl/d/oferta/a\n", encoding="utf-8")
            self.assertEqual(load_urls(path), ["https://www.olx.pl/d/oferta/a"])


if __name__ == "__main__":
    unittest.main()
