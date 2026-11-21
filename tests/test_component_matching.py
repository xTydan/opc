from __future__ import annotations

import unittest

from olx_pc_flipping.component_matching import match_comparable


class ComponentMatchingTests(unittest.TestCase):
    def test_storage_matches_different_brands_with_same_class_and_capacity(self):
        target = {
            "category": "storage", "model": "VIST 1TB NVMe",
            "capacity_gb": 1000, "storage_type": "NVMe SSD", "interface": "NVMe",
        }
        candidate = {
            "category": "storage", "model": "Kingston 1TB NVMe",
            "capacity_gb": 1000, "storage_type": "NVMe SSD", "interface": "NVMe",
        }
        result = match_comparable(target, candidate)
        self.assertTrue(result["matched"])
        self.assertEqual(result["method"], "specification_similarity")
        self.assertEqual(result["price_multiplier"], 1.0)

    def test_storage_does_not_mix_sata_and_nvme(self):
        target = {
            "category": "storage", "model": "Target 1TB NVMe",
            "capacity_gb": 1000, "storage_type": "NVMe SSD", "interface": "NVMe",
        }
        candidate = {
            "category": "storage", "model": "Other 1TB SATA",
            "capacity_gb": 1000, "storage_type": "SATA SSD", "interface": "SATA",
        }
        result = match_comparable(target, candidate)
        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "different_storage_type")

    def test_storage_requires_interface_and_type_in_both_records(self):
        target = {
            "category": "storage", "model": "Target 1TB NVMe",
            "capacity_gb": 1000, "storage_type": "NVMe SSD", "interface": "NVMe",
        }
        candidate = {
            "category": "storage", "model": "Unknown 1TB",
            "capacity_gb": 1000,
        }
        result = match_comparable(target, candidate)
        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "storage_type_required")

    def test_gpu_cross_model_requires_benchmark_and_vram(self):
        target = {"category": "gpu", "model": "GPU A", "benchmark_score": 10000, "benchmark_name": "gaming", "vram_gb": 8}
        candidate = {"category": "gpu", "model": "GPU B", "benchmark_score": 10100, "benchmark_name": "gaming"}
        result = match_comparable(target, candidate)
        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "vram_required_for_cross_model_match")

    def test_different_categories_never_match(self):
        result = match_comparable(
            {"category": "storage", "model": "Same"},
            {"category": "ram", "model": "Same"},
        )
        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "different_category")


if __name__ == "__main__":
    unittest.main()
