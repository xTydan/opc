from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from olx_pc_flipping.importers import load_import_file, parse_pln_price


class ImporterTests(unittest.TestCase):
    def test_parse_polish_price_formats(self):
        self.assertEqual(parse_pln_price("1 599 zł", 2), 1599)
        self.assertEqual(parse_pln_price("1.599,50 PLN", 2), 1599.5)
        self.assertEqual(parse_pln_price("899,99", 2), 899.99)
        self.assertEqual(parse_pln_price("1.599", 2), 1599)

    def test_import_semicolon_csv_with_full_description(self):
        csv_text = (
            "id;title;price;url;location;date_added;description\n"
            'a1;"Komputer gamingowy";"1 599 zł";"https://www.olx.pl/d/oferta/a1";'
            '"Bielsko-Biała";"2026-11-21";"Ryzen 5 5600X, RTX 3070; 32 GB DDR4"\n'
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "listings.csv"
            path.write_text(csv_text, encoding="utf-8")
            payload = load_import_file(path)

        self.assertEqual(payload["source"], "csv-import")
        self.assertEqual(payload["listings"][0]["price"], 1599)
        self.assertEqual(payload["listings"][0]["location"], "Bielsko-Biała")
        self.assertIn("RTX 3070", payload["listings"][0]["description"])
        self.assertEqual(payload["listings"][0]["status"], "unverified")

    def test_rejects_csv_without_required_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.csv"
            path.write_text("title;price\nPC;1000\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_import_file(path)

    def test_rejects_non_pln_or_invalid_price_later_in_analyzer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "listings.csv"
            path.write_text("title,price,description\nPC,do negocjacji,opis\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_import_file(path)


if __name__ == "__main__":
    unittest.main()
