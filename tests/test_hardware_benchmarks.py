from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from olx_pc_flipping.hardware_benchmarks import (
    find_benchmark_score,
    load_benchmark_dataset,
    normalize_hardware_name,
)


class HardwareBenchmarkTests(unittest.TestCase):
    def _dataset(self, directory: str) -> Path:
        path = Path(directory) / "benchmarks.json"
        path.write_text(json.dumps({
            "source": "Example open dataset",
            "license": "CC-BY-4.0",
            "updated_at": "2026-11-20",
            "records": [
                {
                    "category": "gpu",
                    "model": "NVIDIA GeForce RTX 3050 8GB",
                    "benchmark": "gaming_index",
                    "score": 62.5,
                    "samples": 120,
                    "url": "https://example.org/data"
                }
            ]
        }), encoding="utf-8")
        return path

    def test_normalizes_brand_punctuation_but_keeps_model_numbers(self):
        self.assertEqual(
            normalize_hardware_name("NVIDIA GeForce RTX 3050 8GB"),
            normalize_hardware_name("nvidia-geforce-rtx 3050 8gb"),
        )
        self.assertNotEqual(normalize_hardware_name("RTX 3050"), normalize_hardware_name("RTX 3060"))

    def test_loads_and_finds_exact_score_with_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = load_benchmark_dataset(self._dataset(directory))
            result = find_benchmark_score(
                dataset,
                category="gpu",
                model="NVIDIA GeForce RTX 3050 8GB",
                benchmark="gaming_index",
                as_of=date(2026, 11, 21),
            )
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["score"], 62.5)
        self.assertEqual(result["license"], "CC-BY-4.0")
        self.assertEqual(result["samples"], 120)

    def test_does_not_guess_score_for_other_model(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = load_benchmark_dataset(self._dataset(directory))
            result = find_benchmark_score(
                dataset, category="gpu", model="RTX 3060",
                benchmark="gaming_index", as_of=date(2026, 11, 21)
            )
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "model_not_found")

    def test_rejects_missing_license_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._dataset(directory)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["license"] = ""
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source, license"):
                load_benchmark_dataset(path)

    def test_loads_csv_with_provenance_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmarks.csv"
            path.write_text(
                "source,license,updated_at,category,model,benchmark,score,samples\\n"
                "Open dataset,CC-BY-4.0,2026-11-20,gpu,RTX 3050,gaming_index,62.5,120\\n",
                encoding="utf-8",
            )
            dataset = load_benchmark_dataset(path)
        self.assertEqual(dataset["source"], "Open dataset")
        self.assertEqual(dataset["records"][0]["score"], 62.5)

    def test_rejects_inconsistent_csv_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "benchmarks.csv"
            path.write_text(
                "source,license,updated_at,category,model,benchmark,score\\n"
                "Open dataset,CC-BY-4.0,2026-11-20,gpu,RTX 3050,gaming_index,62.5\\n"
                "Other dataset,CC-BY-4.0,2026-11-20,gpu,RTX 3060,gaming_index,75\\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must be consistent"):
                load_benchmark_dataset(path)

    def test_marks_old_dataset_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = load_benchmark_dataset(self._dataset(directory))
            result = find_benchmark_score(
                dataset, category="gpu", model="NVIDIA GeForce RTX 3050 8GB",
                benchmark="gaming_index", as_of=date(2027, 8, 1), max_age_days=180
            )
        self.assertEqual(result["status"], "stale_or_invalid_dataset")


if __name__ == "__main__":
    unittest.main()
