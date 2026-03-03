import json
import tempfile
import unittest
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_submission.py"


class ValidateSubmissionTests(unittest.TestCase):
    def _write_submission(self, payload: dict) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="leaderboard-submission-"))
        file_path = temp_dir / "submission.json"
        file_path.write_text(json.dumps(payload), encoding="utf-8")
        return file_path

    def _run_validate(self, payload: dict) -> subprocess.CompletedProcess:
        file_path = self._write_submission(payload)
        return subprocess.run(
            ["python3", str(VALIDATE_SCRIPT), str(file_path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_accepts_valid_submission_with_multiple_tools(self):
        payload = {
            "userId": "u-100",
            "username": "alice",
            "submittedAt": "2026-03-03T10:10:10Z",
            "clientVersion": "1.0.0",
            "points": [
                {
                    "date": "2026-03-01",
                    "tool": "codex",
                    "totalTokens": 100,
                    "inputTokens": 40,
                    "outputTokens": 50,
                    "cacheReadTokens": 10,
                },
                {
                    "date": "2026-03-01",
                    "tool": "gemini",
                    "totalTokens": 120,
                    "inputTokens": 50,
                    "outputTokens": 60,
                    "cacheReadTokens": 10,
                },
            ],
        }
        result = self._run_validate(payload)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_rejects_missing_tool(self):
        payload = {
            "userId": "u-101",
            "username": "alice",
            "submittedAt": "2026-03-03T10:10:10Z",
            "clientVersion": "1.0.0",
            "points": [
                {
                    "date": "2026-03-01",
                    "totalTokens": 100,
                    "inputTokens": 40,
                    "outputTokens": 50,
                    "cacheReadTokens": 10,
                }
            ],
        }
        result = self._run_validate(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tool", result.stderr)

    def test_rejects_invalid_username_pattern(self):
        payload = {
            "userId": "u-102",
            "username": "alice with space",
            "submittedAt": "2026-03-03T10:10:10Z",
            "clientVersion": "1.0.0",
            "points": [
                {
                    "date": "2026-03-01",
                    "tool": "codex",
                    "totalTokens": 100,
                    "inputTokens": 40,
                    "outputTokens": 50,
                    "cacheReadTokens": 10,
                }
            ],
        }
        result = self._run_validate(payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("username", result.stderr)


if __name__ == "__main__":
    unittest.main()
