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
    total_tokens: int
    input_tokens: int
    output_tokens: int
    primary_tool: str
    last_updated: datetime


@dataclass(frozen=True)
class DayAggregate:
    total_tokens: int
    input_tokens: int
    output_tokens: int
    submitted_at: datetime
    username: str
    tool_totals: dict[str, int]


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
                "primaryTool": row.primary_tool,
                "totalTokens": row.total_tokens,
                "inputTokens": row.input_tokens,
                "outputTokens": row.output_tokens,
                "lastUpdated": row.last_updated.isoformat().replace("+00:00", "Z"),
            }
        )
    return out


def build_rankings(points: list[NormalizedPoint], reference_date: str) -> dict:
    by_tool_date: dict[str, dict[tuple[str, str], DayAggregate]] = defaultdict(dict)
    overall_date: dict[tuple[str, str], DayAggregate] = {}

    for point in points:
        if point.total_tokens > MAX_DAILY_THRESHOLD:
            continue

        by_tool_date[point.tool][(point.user_id, point.date)] = DayAggregate(
            total_tokens=point.total_tokens,
            input_tokens=point.input_tokens,
            output_tokens=point.output_tokens,
            submitted_at=point.submitted_at,
            username=point.username,
            tool_totals={point.tool: point.total_tokens},
        )

        overall_key = (point.user_id, point.date)
        existing = overall_date.get(overall_key)
        if existing is None:
            overall_date[overall_key] = DayAggregate(
                total_tokens=point.total_tokens,
                input_tokens=point.input_tokens,
                output_tokens=point.output_tokens,
                submitted_at=point.submitted_at,
                username=point.username,
                tool_totals={point.tool: point.total_tokens},
            )
        else:
            merged_tool_totals = dict(existing.tool_totals)
            merged_tool_totals[point.tool] = merged_tool_totals.get(point.tool, 0) + point.total_tokens
            overall_date[overall_key] = DayAggregate(
                total_tokens=existing.total_tokens + point.total_tokens,
                input_tokens=existing.input_tokens + point.input_tokens,
                output_tokens=existing.output_tokens + point.output_tokens,
                submitted_at=max(existing.submitted_at, point.submitted_at),
                username=point.username if point.submitted_at >= existing.submitted_at else existing.username,
                tool_totals=merged_tool_totals,
            )

    def _pick_primary_tool(tool_totals: dict[str, int]) -> str:
        if not tool_totals:
            return "-"
        return sorted(tool_totals.items(), key=lambda item: (-item[1], item[0]))[0][0]

    def _build_for_dataset(dataset: dict[tuple[str, str], DayAggregate]) -> dict[str, list[dict]]:
        ref_dt = parse_date(reference_date)
        prev_dt = ref_dt - timedelta(days=1)

        user_date_total: dict[tuple[str, str], DayAggregate] = dict(dataset)

        per_user_daily: dict[str, DayAggregate] = {}
        per_user_prev: dict[str, int] = defaultdict(int)
        per_user_7d: dict[str, DayAggregate] = defaultdict(
            lambda: DayAggregate(
                total_tokens=0,
                input_tokens=0,
                output_tokens=0,
                submitted_at=datetime.fromtimestamp(0, tz=timezone.utc),
                username="",
                tool_totals={},
            )
        )

        for (user_id, date), aggregate in user_date_total.items():
            day = parse_date(date)
            if day == ref_dt:
                per_user_daily[user_id] = aggregate
            if day == prev_dt:
                per_user_prev[user_id] = aggregate.total_tokens
            if ref_dt - timedelta(days=6) <= day <= ref_dt:
                current = per_user_7d[user_id]
                merged_tool_totals = dict(current.tool_totals)
                for tool, value in aggregate.tool_totals.items():
                    merged_tool_totals[tool] = merged_tool_totals.get(tool, 0) + value
                per_user_7d[user_id] = DayAggregate(
                    total_tokens=current.total_tokens + aggregate.total_tokens,
                    input_tokens=current.input_tokens + aggregate.input_tokens,
                    output_tokens=current.output_tokens + aggregate.output_tokens,
                    submitted_at=max(current.submitted_at, aggregate.submitted_at),
                    username=aggregate.username if aggregate.submitted_at >= current.submitted_at else current.username,
                    tool_totals=merged_tool_totals,
                )

        daily_rows: list[ScoreRow] = []
        for user_id, aggregate in per_user_daily.items():
            rising = aggregate.total_tokens - per_user_prev.get(user_id, 0)
            daily_rows.append(
                ScoreRow(
                    user_id=user_id,
                    username=aggregate.username,
                    value=aggregate.total_tokens,
                    delta=rising,
                    total_tokens=aggregate.total_tokens,
                    input_tokens=aggregate.input_tokens,
                    output_tokens=aggregate.output_tokens,
                    primary_tool=_pick_primary_tool(aggregate.tool_totals),
                    last_updated=aggregate.submitted_at,
                )
            )

        seven_rows: list[ScoreRow] = []
        for user_id, aggregate in per_user_7d.items():
            today_val = per_user_daily.get(
                user_id,
                DayAggregate(0, 0, 0, aggregate.submitted_at, aggregate.username, {}),
            ).total_tokens
            rising = today_val - per_user_prev.get(user_id, 0)
            seven_rows.append(
                ScoreRow(
                    user_id=user_id,
                    username=aggregate.username,
                    value=aggregate.total_tokens,
                    delta=rising,
                    total_tokens=aggregate.total_tokens,
                    input_tokens=aggregate.input_tokens,
                    output_tokens=aggregate.output_tokens,
                    primary_tool=_pick_primary_tool(aggregate.tool_totals),
                    last_updated=aggregate.submitted_at,
                )
            )

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


def build_timeseries(points: list[NormalizedPoint], reference_date: str, max_days: int = 90) -> dict:
    ref_dt = parse_date(reference_date)
    filtered = [point for point in points if point.total_tokens <= MAX_DAILY_THRESHOLD]

    by_tool_date: dict[str, dict[tuple[str, str], tuple[int, datetime, str]]] = defaultdict(dict)
    overall_date: dict[tuple[str, str], tuple[int, datetime, str]] = {}
    earliest_dt: datetime | None = None

    for point in filtered:
        day_dt = parse_date(point.date)
        if earliest_dt is None or day_dt < earliest_dt:
            earliest_dt = day_dt

        by_tool_date[point.tool][(point.user_id, point.date)] = (
            point.total_tokens,
            point.submitted_at,
            point.username,
        )

        overall_key = (point.user_id, point.date)
        existing = overall_date.get(overall_key)
        if existing is None:
            overall_date[overall_key] = (point.total_tokens, point.submitted_at, point.username)
        else:
            prev_total, prev_submitted_at, prev_username = existing
            next_username = point.username if point.submitted_at >= prev_submitted_at else prev_username
            overall_date[overall_key] = (
                prev_total + point.total_tokens,
                max(prev_submitted_at, point.submitted_at),
                next_username,
            )

    if earliest_dt is None:
        start_dt = ref_dt
    else:
        span = (ref_dt - earliest_dt).days + 1
        window_days = max(1, min(max_days, span))
        start_dt = ref_dt - timedelta(days=window_days - 1)

    dates_dt = [start_dt + timedelta(days=idx) for idx in range((ref_dt - start_dt).days + 1)]
    dates = [item.strftime("%Y-%m-%d") for item in dates_dt]
    date_to_index = {item: idx for idx, item in enumerate(dates)}

    def _build_for_dataset(dataset: dict[tuple[str, str], tuple[int, datetime, str]]) -> dict[str, object]:
        usernames: dict[str, tuple[str, datetime]] = {}
        values_by_user: dict[str, list[int]] = {}

        for (user_id, day), (total, submitted_at, username) in dataset.items():
            index = date_to_index.get(day)
            if index is None:
                continue
            if user_id not in values_by_user:
                values_by_user[user_id] = [0] * len(dates)
            values_by_user[user_id][index] = total

            existing = usernames.get(user_id)
            if existing is None or submitted_at >= existing[1]:
                usernames[user_id] = (username, submitted_at)

        users = []
        for user_id in sorted(values_by_user.keys()):
            values = values_by_user[user_id]
            if not any(values):
                continue
            username = usernames.get(user_id, (user_id, datetime.fromtimestamp(0, tz=timezone.utc)))[0]
            users.append(
                {
                    "userId": user_id,
                    "username": username,
                    "displayName": username,
                    "values": values,
                }
            )

        return {"dates": dates, "users": users}

    by_tool = {}
    for tool, dataset in sorted(by_tool_date.items()):
        by_tool[tool] = _build_for_dataset(dataset)

    return {
        "overall": _build_for_dataset(overall_date),
        "byTool": by_tool,
    }


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
            "timeseries": build_timeseries(points, reference_date),
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
