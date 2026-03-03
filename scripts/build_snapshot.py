#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from leaderboard_core import MAX_DAILY_THRESHOLD, NormalizedPoint, ValidationError, flatten_submission, load_aliases


@dataclass(frozen=True)
class ScoreRow:
    user_id: str
    username: str
    value: int
    delta: int
    last_updated: datetime


def collect_latest_points(repo_root: Path) -> list[NormalizedPoint]:
    submissions_root = repo_root / "data" / "submissions"
    if not submissions_root.exists():
        return []

    aliases = load_aliases(repo_root)
    dedup: dict[tuple[str, str, str], NormalizedPoint] = {}

    for file_path in sorted(submissions_root.glob("**/*.json")):
        if not file_path.is_file():
            continue
        points = flatten_submission(file_path, aliases)
        for point in points:
            key = (point.user_id, point.date, point.tool)
            existing = dedup.get(key)
            if existing is None or point.submitted_at > existing.submitted_at:
                dedup[key] = point

    return list(dedup.values())


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def rank_rows(rows: list[ScoreRow]) -> list[dict]:
    sorted_rows = sorted(rows, key=lambda row: (-row.value, row.last_updated, row.user_id))
    out = []
    for index, row in enumerate(sorted_rows, start=1):
        out.append(
            {
                "rank": index,
                "userId": row.user_id,
                "username": row.username,
                "displayName": row.username,
                "value": row.value,
                "delta": row.delta,
                "lastUpdated": row.last_updated.isoformat().replace("+00:00", "Z"),
            }
        )
    return out


def build_rankings(points: list[NormalizedPoint], reference_date: str) -> dict:
    by_tool_date: dict[str, dict[tuple[str, str], NormalizedPoint]] = defaultdict(dict)
    overall_date: dict[tuple[str, str], dict[str, object]] = {}

    for point in points:
        if point.total_tokens > MAX_DAILY_THRESHOLD:
            continue

        by_tool_date[point.tool][(point.user_id, point.date)] = point

        overall_key = (point.user_id, point.date)
        existing = overall_date.get(overall_key)
        if existing is None:
            overall_date[overall_key] = {
                "userId": point.user_id,
                "username": point.username,
                "submittedAt": point.submitted_at,
                "total": point.total_tokens,
            }
        else:
            existing["total"] = int(existing["total"]) + point.total_tokens
            if point.submitted_at > existing["submittedAt"]:
                existing["submittedAt"] = point.submitted_at
                existing["username"] = point.username

    def _build_for_dataset(dataset: dict[tuple[str, str], object]) -> dict[str, list[dict]]:
        ref_dt = parse_date(reference_date)
        prev_dt = ref_dt - timedelta(days=1)

        user_date_total: dict[tuple[str, str], tuple[int, datetime, str]] = {}
        for (user_id, date), item in dataset.items():
            if isinstance(item, NormalizedPoint):
                user_date_total[(user_id, date)] = (item.total_tokens, item.submitted_at, item.username)
            else:
                user_date_total[(user_id, date)] = (
                    int(item["total"]),
                    item["submittedAt"],
                    str(item["username"]),
                )

        per_user_daily: dict[str, tuple[int, datetime, str]] = {}
        per_user_prev: dict[str, int] = defaultdict(int)
        per_user_7d: dict[str, tuple[int, datetime, str]] = defaultdict(lambda: (0, datetime.fromtimestamp(0, tz=timezone.utc), ""))

        for (user_id, date), (total, submitted_at, username) in user_date_total.items():
            day = parse_date(date)
            if day == ref_dt:
                per_user_daily[user_id] = (total, submitted_at, username)
            if day == prev_dt:
                per_user_prev[user_id] = total
            if ref_dt - timedelta(days=6) <= day <= ref_dt:
                current_total, current_updated, current_name = per_user_7d[user_id]
                newest = submitted_at if submitted_at > current_updated else current_updated
                chosen_name = username if submitted_at >= current_updated else current_name
                per_user_7d[user_id] = (current_total + total, newest, chosen_name)

        daily_rows: list[ScoreRow] = []
        for user_id, (value, updated_at, username) in per_user_daily.items():
            rising = value - per_user_prev.get(user_id, 0)
            daily_rows.append(ScoreRow(user_id, username, value, rising, updated_at))

        seven_rows: list[ScoreRow] = []
        for user_id, (value, updated_at, username) in per_user_7d.items():
            today_val = per_user_daily.get(user_id, (0, updated_at, username))[0]
            rising = today_val - per_user_prev.get(user_id, 0)
            seven_rows.append(ScoreRow(user_id, username, value, rising, updated_at))

        rising_rows = [row for row in daily_rows if row.delta > 0]

        return {
            "daily": rank_rows(daily_rows),
            "7d": rank_rows(seven_rows),
            "rising": rank_rows(rising_rows),
        }

    rankings = {
        "overall": _build_for_dataset(overall_date),
        "byTool": {},
    }
    for tool, dataset in sorted(by_tool_date.items()):
        rankings["byTool"][tool] = _build_for_dataset(dataset)

    return rankings


def infer_reference_date(points: list[NormalizedPoint]) -> str:
    if not points:
        return "1970-01-01"
    return max(points, key=lambda point: point.date).date


def deterministic_metadata(points: list[NormalizedPoint]) -> tuple[str, str]:
    canonical = [
        {
            "userId": point.user_id,
            "username": point.username,
            "submittedAt": point.submitted_at.isoformat(),
            "date": point.date,
            "tool": point.tool,
            "totalTokens": point.total_tokens,
            "inputTokens": point.input_tokens,
            "outputTokens": point.output_tokens,
            "cacheReadTokens": point.cache_read_tokens,
        }
        for point in sorted(points, key=lambda item: (item.user_id, item.date, item.tool, item.submitted_at.isoformat()))
    ]
    digest = hashlib.sha256(json.dumps(canonical, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    generated_at = "1970-01-01T00:00:00Z"
    if points:
        generated_at = max(point.submitted_at for point in points).isoformat().replace("+00:00", "Z")
    return digest, generated_at


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: build_snapshot.py <repo-root>", file=sys.stderr)
        return 1

    repo_root = Path(sys.argv[1]).resolve()
    try:
        points = collect_latest_points(repo_root)
        reference_date = infer_reference_date(points)
        digest, generated_at = deterministic_metadata(points)
        version = f"local-{digest}"
        snapshot = {
            "version": version,
            "generatedAt": generated_at,
            "referenceDate": reference_date,
            "rankings": build_rankings(points, reference_date),
        }

        snapshot_path = repo_root / "data" / "snapshots" / "latest.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"snapshot build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
