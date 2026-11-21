from __future__ import annotations

import unittest

from olx_pc_flipping.component_parser import parse_description


class ComponentParserTests(unittest.TestCase):
    def test_extracts_common_pc_parts(self):
        text = (
            "Sprzedam komputer: Ryzen 5 5600X, RTX 3070 ASUS, "
            "2x16GB DDR4, SSD 1TB, MSI MAG B550 TOMAHAWK, "
            "zasilacz Corsair 650W."
        )
        result = parse_description(text)
        by_category = {item["category"]: item for item in result["components"]}

        self.assertEqual(by_category["cpu"]["model"], "Ryzen 5 5600X")
        self.assertIn("RTX 3070", by_category["gpu"]["model"])
        self.assertEqual(by_category["ram"]["capacity_gb"], 32)
        self.assertEqual(by_category["ram"]["memory_type"], "DDR4")
        self.assertEqual(by_category["storage"]["model"], "1TB SSD")
        self.assertEqual(by_category["psu"]["wattage"], 650)
        self.assertIsNone(by_category["gpu"]["estimated_sale_price"])

    def test_does_not_invent_missing_components(self):
        result = parse_description("Komputer gamingowy, bardzo wydajny, ładna obudowa.")
        self.assertEqual(result["recognized_count"], 0)
        self.assertIn("gpu", result["unrecognized_categories"])
        self.assertEqual(result["note"], "Extracted from supplied text only. Prices were not estimated.")

    def test_chipset_only_is_low_confidence(self):
        result = parse_description("Płyta główna na chipsecie B550.")
        motherboard = next(x for x in result["components"] if x["category"] == "motherboard")
        self.assertEqual(motherboard["confidence"], "low")
        self.assertIn("exact board model unknown", motherboard["model"])


    def test_realistic_polish_listing_with_messy_separators(self):
        text = (
            "Procesor: Intel Core i5-11400F- "
            "Karta graficzna: NVIDIA GeForce RTX 3050 8 GB - ZOTAC GAMING- "
            "Pamięć RAM: 16 GB DDR4- Dysk: SSD VIST NVMe 512 GB- "
            "Płyta główna: MSI MS-7D22- "
            "Zasilacz: Bandit Power XH-490, 650 W, 80 PLUS- "
            "Chłodzenie procesora: Intel- "
            "Obudowa: gamingowa, z bocznym panelem ze szkła- "
            "Wentylatory: 3 wentylatory z przodu obudowy"
        )
        result = parse_description(text)
        by_category = {item["category"]: item for item in result["components"]}

        self.assertEqual(by_category["cpu"]["model"], "Intel Core i5-11400F")
        self.assertIn("RTX 3050", by_category["gpu"]["model"])
        self.assertEqual(by_category["gpu"]["manufacturer"], "ZOTAC")
        self.assertEqual(by_category["gpu"]["vram_gb"], 8)
        self.assertEqual(by_category["ram"]["capacity_gb"], 16)
        self.assertIsNone(by_category["ram"]["stick_count"])
        self.assertFalse(by_category["ram"]["stick_count_known"])
        self.assertEqual(by_category["storage"]["manufacturer"], "VIST")
        self.assertEqual(by_category["motherboard"]["board_identifier"], "MS-7D22")
        self.assertIn("Bandit Power XH-490", by_category["psu"]["model"])
        self.assertEqual(by_category["psu"]["wattage"], 650)
        self.assertIn("80 PLUS", by_category["psu"]["efficiency"])
        self.assertEqual(by_category["cooler"]["model"], "CPU cooler: Intel")
        self.assertEqual(by_category["case"]["model"], "Gaming case (exact model unknown)")
        self.assertTrue(all(item["estimated_sale_price"] is None for item in by_category.values()))


    def test_full_user_supplied_description_including_typo(self):
        text = (
            "Sprzedam komputer gamingowy, w pełni sprawny i gotowy do użytkowania. "
            "Procesor: Intel Core i5-11400F- Karta graficzna: NVIDIA GeForce RTX 3050 8 GB - "
            "ZOTAC GAMING- Pamięć RAM: 16 GB DDR4- Dysk: SSD VIST NVMe 512 GB- "
            "Płyta główna: MSI MS-7D22- Zasilacz: Bandit Power XH-490, 650 W, 80 PLUS- "
            "Chtodzenie procesora: Intel- Obudowa: gamingowa, z bocznym panelem ze szkła- "
            "Wentylatory: 3 wentylatory z przodu obudowy. Windows 11 Home."
        )
        result = parse_description(text)
        by_category = {item["category"]: item for item in result["components"]}

        self.assertEqual(by_category["cpu"]["model"], "Intel Core i5-11400F")
        self.assertEqual(by_category["gpu"]["manufacturer"], "ZOTAC")
        self.assertEqual(by_category["gpu"]["gpu_model"], "NVIDIA GeForce RTX 3050")
        self.assertEqual(by_category["gpu"]["vram_gb"], 8)
        self.assertEqual(by_category["ram"]["capacity_gb"], 16)
        self.assertIsNone(by_category["ram"]["stick_count"])
        self.assertEqual(by_category["storage"]["manufacturer"], "VIST")
        self.assertIn("NVMe SSD", by_category["storage"]["model"])
        self.assertEqual(by_category["motherboard"]["board_identifier"], "MS-7D22")
        self.assertIn("Bandit Power XH-490", by_category["psu"]["model"])
        self.assertEqual(by_category["psu"]["wattage"], 650)
        self.assertTrue(by_category["psu"]["quality_assessment"].startswith("unknown"))
        self.assertEqual(by_category["cooler"]["model"], "CPU cooler: Intel")
        self.assertEqual(by_category["fans"]["count"], 3)
        self.assertFalse(result["missing_required_categories"])
        self.assertIsNone(by_category["gpu"]["estimated_sale_price"])

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_description(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
