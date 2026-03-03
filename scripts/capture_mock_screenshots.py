#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class UserTrend:
    user_id: str
    username: str
    daily: list[int]


def date_range(reference_date: date, days: int) -> list[str]:
    start = reference_date - timedelta(days=days - 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(days)]


def _rank_rows(user_series: Iterable[dict], ranking_type: str) -> list[dict]:
    rows = []
    for item in user_series:
        values = item["values"]
        daily_value = values[-1]
        prev_value = values[-2] if len(values) > 1 else 0
        seven_value = sum(values[-7:])
        rising_value = daily_value - prev_value

        if ranking_type == "daily":
            value = daily_value
        elif ranking_type == "7d":
            value = seven_value
        elif ranking_type == "rising":
            value = rising_value
        else:
            raise ValueError(f"unsupported ranking_type={ranking_type}")

        rows.append(
            {
                "userId": item["userId"],
                "username": item["username"],
                "displayName": item["displayName"],
                "value": value,
                "delta": rising_value,
                "primaryTool": item.get("primaryTool", "-"),
                "totalTokens": value,
                "inputTokens": int(value * 0.45),
                "outputTokens": int(value * 0.5),
                "lastUpdated": "2026-03-03T12:00:00Z",
            }
        )

    filtered = rows if ranking_type != "rising" else [row for row in rows if row["value"] > 0]
    ordered = sorted(filtered, key=lambda row: (-row["value"], row["userId"]))
    for idx, row in enumerate(ordered, start=1):
        row["rank"] = idx
    return ordered


def _build_dataset(dates: list[str], trends: list[UserTrend]) -> dict:
    users = [
        {
            "userId": trend.user_id,
            "username": trend.username,
            "displayName": trend.username,
            "primaryTool": "-",
            "values": trend.daily,
        }
        for trend in trends
    ]
    return {
        "dates": dates,
        "users": users,
    }


def build_mock_snapshot(reference_date: date = date(2026, 3, 3), days: int = 90) -> dict:
    dates = date_range(reference_date, days)

    def seq(base: int, step: int, wave: int) -> list[int]:
        values = []
        for i in range(days):
            values.append(max(0, base + step * i + ((i % 7) - 3) * wave))
        return values

    codex = [
        UserTrend("u1", "alice", seq(420, 4, 8)),
        UserTrend("u2", "bob", seq(340, 3, 6)),
        UserTrend("u3", "carol", seq(280, 3, 5)),
        UserTrend("u4", "dylan", seq(230, 2, 4)),
        UserTrend("u5", "eric", seq(210, 2, 3)),
        UserTrend("u6", "fiona", seq(160, 1, 2)),
    ]
    gemini = [
        UserTrend("u1", "alice", seq(150, 2, 4)),
        UserTrend("u2", "bob", seq(170, 2, 3)),
        UserTrend("u3", "carol", seq(190, 1, 4)),
        UserTrend("u4", "dylan", seq(130, 2, 2)),
        UserTrend("u5", "eric", seq(120, 1, 2)),
        UserTrend("u6", "fiona", seq(90, 1, 1)),
    ]

    by_tool = {
        "codex": _build_dataset(dates, codex),
        "gemini": _build_dataset(dates, gemini),
    }
    for item in by_tool["codex"]["users"]:
        item["primaryTool"] = "codex"
    for item in by_tool["gemini"]["users"]:
        item["primaryTool"] = "gemini"

    overall_trends: list[UserTrend] = []
    gemini_map = {item.user_id: item.daily for item in gemini}
    for item in codex:
        merged = [item.daily[i] + gemini_map[item.user_id][i] for i in range(days)]
        overall_trends.append(UserTrend(item.user_id, item.username, merged))
    overall = _build_dataset(dates, overall_trends)
    codex_latest = {item.user_id: item.daily[-1] for item in codex}
    gemini_latest = {item.user_id: item.daily[-1] for item in gemini}
    for item in overall["users"]:
        item["primaryTool"] = "codex" if codex_latest[item["userId"]] >= gemini_latest[item["userId"]] else "gemini"

    rankings = {
        "overall": {
            "daily": _rank_rows(overall["users"], "daily"),
            "7d": _rank_rows(overall["users"], "7d"),
            "rising": _rank_rows(overall["users"], "rising"),
        },
        "byTool": {
            "codex": {
                "daily": _rank_rows(by_tool["codex"]["users"], "daily"),
                "7d": _rank_rows(by_tool["codex"]["users"], "7d"),
                "rising": _rank_rows(by_tool["codex"]["users"], "rising"),
            },
            "gemini": {
                "daily": _rank_rows(by_tool["gemini"]["users"], "daily"),
                "7d": _rank_rows(by_tool["gemini"]["users"], "7d"),
                "rising": _rank_rows(by_tool["gemini"]["users"], "rising"),
            },
        },
    }

    return {
        "version": "mock-20260303",
        "generatedAt": datetime(2026, 3, 3, 12, 0, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "referenceDate": reference_date.isoformat(),
        "rankings": rankings,
        "timeseries": {
            "overall": overall,
            "byTool": by_tool,
        },
    }


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\\nstdout:\\n{result.stdout}\\nstderr:\\n{result.stderr}")


def _playwright_screenshot(url: str, output_path: Path) -> None:
    _run([
        "npx",
        "--yes",
        "playwright",
        "screenshot",
        "--browser",
        "chromium",
        "--full-page",
        "--viewport-size",
        "1440,1100",
        "--wait-for-selector",
        "#rows tr",
        "--wait-for-timeout",
        "400",
        url,
        str(output_path),
    ])


def capture_mock_screenshots(repo_root: Path, date_str: str) -> tuple[Path, Path, Path]:
    mock_root = repo_root / ".local" / "mock-data"
    mock_root.mkdir(parents=True, exist_ok=True)

    mock_snapshot = build_mock_snapshot()
    mock_snapshot_path = mock_root / "latest.mock.json"
    mock_snapshot_path.write_text(json.dumps(mock_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _run(["python3", "scripts/build_site_bundle.py", str(repo_root)], cwd=repo_root)

    site_snapshot_path = repo_root / ".site" / "data" / "snapshots" / "latest.json"
    site_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    site_snapshot_path.write_text(mock_snapshot_path.read_text(encoding="utf-8"), encoding="utf-8")

    _run(["npx", "--yes", "playwright", "install", "chromium"])

    screenshots_dir = repo_root / "screenshots" / date_str / "leaderboard"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    before_path = screenshots_dir / f"{date_str}-leaderboard-trend-window-web-before-v01.png"
    after_path = screenshots_dir / f"{date_str}-leaderboard-trend-window-web-after-v01.png"

    port = _find_free_port()
    server = subprocess.Popen(
        ["python3", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(repo_root / ".site"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _playwright_screenshot(f"http://127.0.0.1:{port}/?tool=all&ranking=daily&window=7", before_path)
        _playwright_screenshot(f"http://127.0.0.1:{port}/?tool=all&ranking=daily&window=30", after_path)
    finally:
        server.terminate()
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()

    _run(["python3", "scripts/check_screenshot_regression.py", str(repo_root / "screenshots")], cwd=repo_root)
    return mock_snapshot_path, before_path, after_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture leaderboard screenshots with local mock snapshot data.")
    parser.add_argument("repo_root", nargs="?", default=".", help="repository root")
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"), help="date for screenshot folder and filename")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    try:
        mock_path, before_path, after_path = capture_mock_screenshots(repo_root, args.date)
        print(f"mock snapshot: {mock_path}")
        print(f"before screenshot: {before_path}")
        print(f"after screenshot: {after_path}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
