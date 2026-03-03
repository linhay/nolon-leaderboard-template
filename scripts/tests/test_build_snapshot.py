import json
import tempfile
import unittest
from pathlib import Path
import subprocess


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

        codex_daily = payload["rankings"]["byTool"]["codex"]["daily"]
        self.assertEqual(codex_daily[0]["userId"], "u1")

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


if __name__ == "__main__":
    unittest.main()
