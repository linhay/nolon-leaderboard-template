import unittest
from datetime import date

from scripts.capture_mock_screenshots import build_mock_snapshot


class CaptureMockScreenshotsTests(unittest.TestCase):
    def test_build_mock_snapshot_contains_required_keys(self):
        snapshot = build_mock_snapshot(reference_date=date(2026, 3, 3), days=90)
        self.assertEqual(snapshot["referenceDate"], "2026-03-03")
        self.assertIn("rankings", snapshot)
        self.assertIn("timeseries", snapshot)
        self.assertIn("overall", snapshot["timeseries"])
        self.assertIn("byTool", snapshot["timeseries"])

    def test_build_mock_snapshot_uses_90_day_series(self):
        snapshot = build_mock_snapshot(reference_date=date(2026, 3, 3), days=90)
        dates = snapshot["timeseries"]["overall"]["dates"]
        self.assertEqual(len(dates), 90)
        self.assertEqual(dates[-1], "2026-03-03")
        user = snapshot["timeseries"]["overall"]["users"][0]
        self.assertEqual(len(user["values"]), 90)


if __name__ == "__main__":
    unittest.main()
