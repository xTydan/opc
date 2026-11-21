from __future__ import annotations

import unittest
from datetime import datetime, timezone

from olx_pc_flipping.valuation_engine import estimate_component_value, normalize_model_key


AS_OF = datetime.fromisoformat("2026-11-21T12:00:00+00:00")


def comparable(index: int, price: int, *, model: str = "ZOTAC RTX 3050 8GB", status: str = "active",
               marketplace: str = "olx", collected_at: str = "2026-11-21T11:00:00+00:00"):
    return {
        "id": f"offer-{index}",
        "marketplace": marketplace,
        "model": model,
        "model_key": normalize_model_key(model),
        "price": price,
        "status": status,
        "collected_at": collected_at,
        "url": f"https://www.olx.pl/d/oferta/{index}",
    }


class ValuationEngineTests(unittest.TestCase):
    def test_estimates_conservatively_from_fresh_exact_model_olx_offers(self):
        prices = [800, 810, 820, 830, 840, 850, 5000]
        offers = [comparable(i, price) for i, price in enumerate(prices)]
        result = estimate_component_value(
            {"model": "ZOTAC RTX 3050 8GB", "comparables": offers},
            min_samples=5,
            max_age_hours=24,
            haircut_percent=3,
            as_of=AS_OF,
        )
        self.assertEqual(result["comparables_count"], 6)
        self.assertEqual(result["outlier_count"], 1)
        self.assertEqual(result["median_price"], 825.0)
        self.assertEqual(result["estimated_sale_price"], 788.13)
        self.assertEqual(result["valuation_status"], "estimated_from_fresh_olx_asking_prices")

    def test_rejects_stale_wrong_marketplace_inactive_and_other_models(self):
        offers = [comparable(i, 700 + i * 10) for i in range(5)]
        offers.extend([
            comparable(10, 10_000, marketplace="other"),
            comparable(11, 10_000, status="removed"),
            comparable(12, 10_000, model="RTX 3050 6GB"),
            comparable(13, 10_000, collected_at="2026-11-19T08:00:00+00:00"),
        ])
        result = estimate_component_value(
            {"model": "ZOTAC RTX 3050 8GB", "comparables": offers},
            min_samples=5,
            max_age_hours=24,
            as_of=AS_OF,
        )
        self.assertEqual(result["comparables_count"], 5)
        self.assertEqual(result["excluded"]["not_olx"], 1)
        self.assertEqual(result["excluded"]["not_active"], 1)
        self.assertEqual(result["excluded"]["different_model"], 1)
        self.assertEqual(result["excluded"]["stale_or_future"], 1)

    def test_no_estimate_when_too_few_comparables(self):
        offers = [comparable(1, 700), comparable(2, 750)]
        result = estimate_component_value(
            {"model": "ZOTAC RTX 3050 8GB", "comparables": offers},
            min_samples=5,
            as_of=AS_OF,
        )
        self.assertIsNone(result["estimated_sale_price"])
        self.assertEqual(result["valuation_status"], "insufficient_comparables")

    def test_duplicate_offers_are_not_counted_twice(self):
        offer = comparable(1, 700)
        offers = [offer, dict(offer), comparable(2, 710), comparable(3, 720), comparable(4, 730), comparable(5, 740)]
        result = estimate_component_value(
            {"model": "ZOTAC RTX 3050 8GB", "comparables": offers},
            min_samples=5,
            as_of=AS_OF,
        )
        self.assertEqual(result["excluded"]["duplicate"], 1)
        self.assertEqual(result["comparables_count"], 5)


if __name__ == "__main__":
    unittest.main()
