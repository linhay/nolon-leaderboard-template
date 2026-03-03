#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from leaderboard_core import ValidationError, load_json, validate_payload


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_all_submissions.py <repo-root>", file=sys.stderr)
        return 1

    repo_root = Path(sys.argv[1]).resolve()
    submissions_root = repo_root / "data" / "submissions"
    failures: list[str] = []

    for submission in sorted(submissions_root.glob("**/*.json")):
        if not submission.is_file():
            continue
        try:
            payload = load_json(submission)
            validate_payload(payload)
        except (ValidationError, Exception) as exc:
            failures.append(f"{submission}: {exc}")

    if failures:
        for line in failures:
            print(line, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
