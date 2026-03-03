import json
import tempfile
import unittest
from pathlib import Path
import subprocess
from datetime import date, timedelta


ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "scripts" / "build_snapshot.py"


class BuildSnapshotTests(unittest.TestCase):
    def _mk_submission(
        self,
        root: Path,
        user_id: str,
        timestamp: str,
        points: list[dict],
        username: str = "tester",
    ) -> None:
        user_dir = root / "data" / "submissions" / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        submitted_at = (
            f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]}T"
            f"{timestamp[9:11]}:{timestamp[11:13]}:{timestamp[13:15]}Z"
        )
        payload = {
            "userId": user_id,
            "username": username,
            "submittedAt": submitted_at,
            "clientVersion": "1.0.0",
            "points": points,
        }
        (user_dir / f"{timestamp}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def test_builds_overall_and_tool_rankings(self):
        temp_root = Path(tempfile.mkdtemp(prefix="leaderboard-build-"))
        (temp_root / "data" / "submissions").mkdir(parents=True)
        (temp_root / "data" / "snapshots").mkdir(parents=True)

        self._mk_submission(
            temp_root,
            "u1",
            "20260303T010101Z",
            [
                {
                    "date": "2026-03-02",
                    "tool": "codex",
                    "totalTokens": 100,
                    "inputTokens": 40,
                    "outputTokens": 50,
                    "cacheReadTokens": 10,
                },
                {
                    "date": "2026-03-03",
                    "tool": "codex",
                    "totalTokens": 300,
                    "inputTokens": 120,
                    "outputTokens": 150,
                    "cacheReadTokens": 30,
                },
            ],
            username="alice",
        )
        self._mk_submission(
            temp_root,
            "u2",
            "20260303T020202Z",
            [
                {
                    "date": "2026-03-02",
                    "tool": "gemini",
                    "totalTokens": 200,
                    "inputTokens": 80,
                    "outputTokens": 100,
                    "cacheReadTokens": 20,
                },
                {
                    "date": "2026-03-03",
                    "tool": "gemini",
                    "totalTokens": 100,
                    "inputTokens": 40,
                    "outputTokens": 50,
                    "cacheReadTokens": 10,
                },
            ],
            username="bob",
        )

        result = subprocess.run(
            ["python3", str(BUILD_SCRIPT), str(temp_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        snapshot_path = temp_root / "data" / "snapshots" / "latest.json"
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))

        self.assertIn("overall", payload["rankings"])
        self.assertIn("byTool", payload["rankings"])
        self.assertIn("codex", payload["rankings"]["byTool"])
        self.assertIn("gemini", payload["rankings"]["byTool"])

        overall_daily = payload["rankings"]["overall"]["daily"]
        self.assertEqual(overall_daily[0]["userId"], "u1")
        self.assertEqual(overall_daily[0]["value"], 300)
        self.assertEqual(overall_daily[0]["primaryTool"], "codex")
        self.assertEqual(overall_daily[0]["totalTokens"], 300)
        self.assertEqual(overall_daily[0]["inputTokens"], 120)
        self.assertEqual(overall_daily[0]["outputTokens"], 150)

        codex_daily = payload["rankings"]["byTool"]["codex"]["daily"]
        self.assertEqual(codex_daily[0]["userId"], "u1")
        self.assertEqual(codex_daily[0]["primaryTool"], "codex")

    def test_latest_submission_wins_for_same_user_date_tool(self):
        temp_root = Path(tempfile.mkdtemp(prefix="leaderboard-dedupe-"))
        (temp_root / "data" / "submissions").mkdir(parents=True)
        (temp_root / "data" / "snapshots").mkdir(parents=True)

        self._mk_submission(
            temp_root,
            "u1",
            "20260303T010101Z",
            [
                {
                    "date": "2026-03-03",
                    "tool": "codex",
                    "totalTokens": 100,
                    "inputTokens": 30,
                    "outputTokens": 60,
                    "cacheReadTokens": 10,
                }
            ],
            username="alice",
        )
        self._mk_submission(
            temp_root,
            "u1",
            "20260303T090909Z",
            [
                {
                    "date": "2026-03-03",
                    "tool": "codex",
                    "totalTokens": 500,
                    "inputTokens": 200,
                    "outputTokens": 250,
                    "cacheReadTokens": 50,
                }
            ],
            username="alice",
        )

        result = subprocess.run(
            ["python3", str(BUILD_SCRIPT), str(temp_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        snapshot_path = temp_root / "data" / "snapshots" / "latest.json"
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        daily = payload["rankings"]["byTool"]["codex"]["daily"]
        self.assertEqual(daily[0]["value"], 500)

    def test_snapshot_contains_timeseries_overall_and_tool(self):
        temp_root = Path(tempfile.mkdtemp(prefix="leaderboard-timeseries-"))
        (temp_root / "data" / "submissions").mkdir(parents=True)
        (temp_root / "data" / "snapshots").mkdir(parents=True)

        self._mk_submission(
            temp_root,
            "u1",
            "20260303T010101Z",
            [
                {
                    "date": "2026-03-02",
                    "tool": "codex",
                    "totalTokens": 120,
                    "inputTokens": 40,
                    "outputTokens": 70,
                    "cacheReadTokens": 10,
                },
                {
                    "date": "2026-03-03",
                    "tool": "codex",
                    "totalTokens": 300,
                    "inputTokens": 120,
                    "outputTokens": 150,
                    "cacheReadTokens": 30,
                },
            ],
            username="alice",
        )

        result = subprocess.run(
            ["python3", str(BUILD_SCRIPT), str(temp_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        payload = json.loads((temp_root / "data" / "snapshots" / "latest.json").read_text(encoding="utf-8"))
        self.assertIn("timeseries", payload)
        self.assertIn("overall", payload["timeseries"])
        self.assertIn("byTool", payload["timeseries"])
        self.assertIn("codex", payload["timeseries"]["byTool"])

        overall_users = payload["timeseries"]["overall"]["users"]
        self.assertEqual(overall_users[0]["userId"], "u1")
        self.assertEqual(overall_users[0]["values"][-1], 300)

    def test_timeseries_fills_missing_dates_with_zero(self):
        temp_root = Path(tempfile.mkdtemp(prefix="leaderboard-timeseries-zero-"))
        (temp_root / "data" / "submissions").mkdir(parents=True)
        (temp_root / "data" / "snapshots").mkdir(parents=True)

        self._mk_submission(
            temp_root,
            "u1",
            "20260303T010101Z",
            [
                {
                    "date": "2026-03-01",
                    "tool": "codex",
                    "totalTokens": 100,
                    "inputTokens": 30,
                    "outputTokens": 60,
                    "cacheReadTokens": 10,
                },
                {
                    "date": "2026-03-03",
                    "tool": "codex",
                    "totalTokens": 300,
                    "inputTokens": 100,
                    "outputTokens": 180,
                    "cacheReadTokens": 20,
                },
            ],
            username="alice",
        )

        result = subprocess.run(
            ["python3", str(BUILD_SCRIPT), str(temp_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        payload = json.loads((temp_root / "data" / "snapshots" / "latest.json").read_text(encoding="utf-8"))
        dates = payload["timeseries"]["byTool"]["codex"]["dates"]
        user = payload["timeseries"]["byTool"]["codex"]["users"][0]
        date_to_value = dict(zip(dates, user["values"]))
        self.assertEqual(date_to_value["2026-03-01"], 100)
        self.assertEqual(date_to_value["2026-03-02"], 0)
        self.assertEqual(date_to_value["2026-03-03"], 300)

    def test_timeseries_limited_to_recent_90_days(self):
        temp_root = Path(tempfile.mkdtemp(prefix="leaderboard-timeseries-90d-"))
        (temp_root / "data" / "submissions").mkdir(parents=True)
        (temp_root / "data" / "snapshots").mkdir(parents=True)

        reference = date(2026, 3, 3)
        points = []
        for offset in range(0, 100):
            day = reference - timedelta(days=99 - offset)
            points.append(
                {
                    "date": day.isoformat(),
                    "tool": "codex",
                    "totalTokens": 10 + offset,
                    "inputTokens": 4,
                    "outputTokens": 5,
                    "cacheReadTokens": 1,
                }
            )
        self._mk_submission(temp_root, "u1", "20260303T010101Z", points, username="alice")

        result = subprocess.run(
            ["python3", str(BUILD_SCRIPT), str(temp_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        payload = json.loads((temp_root / "data" / "snapshots" / "latest.json").read_text(encoding="utf-8"))
        dates = payload["timeseries"]["overall"]["dates"]
        self.assertEqual(len(dates), 90)
        self.assertEqual(dates[0], (reference - timedelta(days=89)).isoformat())
        self.assertEqual(dates[-1], reference.isoformat())


if __name__ == "__main__":
    unittest.main()
