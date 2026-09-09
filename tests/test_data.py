"""Offline checks for failure modes that could silently distort the findings."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from market_data import validate_day, load_prices
from metrics import hourly_table, compare_windows

ROOT = Path(__file__).resolve().parents[1]

class DataChecks(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((ROOT / "data/raw/2026-09-07.json").read_text())["payload"]

    def test_complete_day(self):
        self.assertEqual(len(validate_day(self.payload, "2026-09-07")), 96)

    def test_missing_interval(self):
        self.payload["rows"].pop()
        with self.assertRaises(ValueError):
            validate_day(self.payload, "2026-09-07")

    def test_duplicate_interval(self):
        self.payload["rows"][1] = copy.deepcopy(self.payload["rows"][0])
        with self.assertRaises(ValueError):
            validate_day(self.payload, "2026-09-07")

    def test_wrong_bidding_zone(self):
        self.payload["meta"]["spatial_coverage"] = "LV bidding zone"
        with self.assertRaises(ValueError):
            validate_day(self.payload, "2026-09-07")

    def test_invalid_prices(self):
        for value in [None, float("inf"), "not a price"]:
            with self.subTest(value=value):
                self.payload["rows"][0]["price_eur_mwh"] = value
                with self.assertRaises(ValueError):
                    validate_day(self.payload, "2026-09-07")

    def test_clock_change_day_is_rejected_by_hourly_profile(self):
        utc = pd.date_range("2026-10-24T21:00Z", periods=100, freq="15min")
        frame = pd.DataFrame({"time_estonia": utc.tz_convert("Europe/Tallinn"), "price_eur_mwh": 1.0})
        with self.assertRaises(ValueError):
            hourly_table(frame)

    def test_snapshot_results_without_network(self):
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")):
            original = load_prices("2026-08-11", "2026-09-07")
            earlier = load_prices("2026-07-14", "2026-08-10")
        self.assertEqual(len(original) + len(earlier), 5376)
        self.assertAlmostEqual(original.price_eur_mwh.mean(), 69.37, places=2)
        for history, count, mean in [(original, 27, 73.41), (earlier, 28, 63.52)]:
            delta = compare_windows(hourly_table(history))["difference"]
            self.assertEqual(int((delta > 0).sum()), count)
            self.assertAlmostEqual(delta.mean(), mean, places=2)

if __name__ == "__main__":
    unittest.main()
