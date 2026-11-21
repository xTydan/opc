from __future__ import annotations

import unittest

from olx_pc_flipping.analyzer import analyze_import, analyze_listing


class AnalyzerTests(unittest.TestCase):
    def test_profit_and_max_purchase_price(self):
        listing = {
            "id": "test-1",
            "title": "Test PC",
            "price": 1000,
            "components": [
                {"model": "GPU", "estimated_sale_price": 900},
                {"model": "CPU", "estimated_sale_price": 300},
            ],
        }
        result = analyze_listing(
            listing,
            default_costs={"transport": 50, "packing": 20},
            target_profit=300,
        )
        self.assertEqual(result["component_value_total"], 1200.0)
        self.assertEqual(result["total_investment"], 1070.0)
        self.assertEqual(result["estimated_net_profit"], 130.0)
        self.assertEqual(result["maximum_purchase_price_for_target_profit"], 830.0)

    def test_missing_component_valuation_is_marked(self):
        listing = {
            "price": 500,
            "components": [{"model": "Unknown GPU"}],
        }
        result = analyze_listing(listing)
        self.assertFalse(result["valuation_complete"])
        self.assertEqual(result["missing_valuations"], ["Unknown GPU"])

    def test_import_sorts_by_profit(self):
        payload = {
            "schema_version": 1,
            "listings": [
                {"id": "low", "price": 100, "components": [{"model": "A", "estimated_sale_price": 120}]},
                {"id": "high", "price": 100, "components": [{"model": "B", "estimated_sale_price": 250}]},
            ],
        }
        result = analyze_import(payload)
        self.assertEqual(result["results"][0]["id"], "high")


    def test_import_parses_components_from_description(self):
        listing = {
            "id": "description-only",
            "title": "PC from description",
            "price": 1200,
            "description": "Ryzen 5 5600X, RTX 3070, 32GB DDR4, SSD 1TB",
        }
        result = analyze_listing(listing)
        self.assertTrue(result["components_parsed_from_description"])
        categories = {item["category"] for item in result["components"]}
        self.assertTrue({"cpu", "gpu", "ram", "storage"}.issubset(categories))
        self.assertFalse(result["valuation_complete"])
        self.assertEqual(len(result["missing_valuations"]), 4)

    def test_negative_price_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_listing({"price": -1, "components": []})


if __name__ == "__main__":
    unittest.main()
