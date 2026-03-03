from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_DAILY_THRESHOLD = 100_000_000


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class NormalizedPoint:
    user_id: str
    username: str
    submitted_at: datetime
    date: str
    tool: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int


def parse_iso8601(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{field_name} must be a non-empty ISO8601 string")
    raw = value
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError(f"{field_name} is not a valid ISO8601 value: {raw}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_non_negative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer")
    if value < 0:
        raise ValidationError(f"{field_name} must be >= 0")
    return value


def validate_payload(payload: dict[str, Any]) -> None:
    required = ["userId", "username", "submittedAt", "clientVersion", "points"]
    for key in required:
        if key not in payload:
            raise ValidationError(f"missing required field: {key}")

    user_id = payload["userId"]
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValidationError("userId must be a non-empty string")

    username = payload["username"]
    if not isinstance(username, str) or not USERNAME_PATTERN.fullmatch(username):
        raise ValidationError("username must match ^[A-Za-z0-9_]{3,20}$")

    parse_iso8601(payload["submittedAt"], "submittedAt")

    if not isinstance(payload["clientVersion"], str) or not payload["clientVersion"].strip():
        raise ValidationError("clientVersion must be a non-empty string")

    points = payload["points"]
    if not isinstance(points, list) or not points:
        raise ValidationError("points must be a non-empty array")

    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValidationError(f"points[{index}] must be an object")
        for field_name in [
            "date",
            "tool",
            "totalTokens",
            "inputTokens",
            "outputTokens",
            "cacheReadTokens",
        ]:
            if field_name not in point:
                raise ValidationError(f"points[{index}] missing required field: {field_name}")

        date = point["date"]
        if not isinstance(date, str) or not DATE_PATTERN.fullmatch(date):
            raise ValidationError(f"points[{index}].date must match YYYY-MM-DD")

        tool = point["tool"]
        if not isinstance(tool, str) or not tool.strip():
            raise ValidationError(f"points[{index}].tool must be a non-empty string")

        _validate_non_negative_int(point["totalTokens"], f"points[{index}].totalTokens")
        _validate_non_negative_int(point["inputTokens"], f"points[{index}].inputTokens")
        _validate_non_negative_int(point["outputTokens"], f"points[{index}].outputTokens")
        _validate_non_negative_int(point["cacheReadTokens"], f"points[{index}].cacheReadTokens")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError(f"{path} root must be an object")
    return data


def load_aliases(repo_root: Path) -> dict[str, str]:
    aliases_path = repo_root / "config" / "tool_aliases.json"
    if not aliases_path.exists():
        return {}
    raw = json.loads(aliases_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValidationError("config/tool_aliases.json must be an object")
    normalized: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValidationError("tool aliases must be string-to-string")
        normalized[key.strip().lower()] = value.strip().lower()
    return normalized


def normalize_tool(tool: str, aliases: dict[str, str]) -> str:
    key = tool.strip().lower()
    return aliases.get(key, key)


def flatten_submission(path: Path, aliases: dict[str, str]) -> list[NormalizedPoint]:
    payload = load_json(path)
    validate_payload(payload)

    user_id = payload["userId"]
    username = payload["username"]
    submitted_at = parse_iso8601(payload["submittedAt"], "submittedAt")
    points: list[dict[str, Any]] = payload["points"]

    normalized_points: list[NormalizedPoint] = []
    for point in points:
        normalized_points.append(
            NormalizedPoint(
                user_id=user_id,
                username=username,
                submitted_at=submitted_at,
                date=point["date"],
                tool=normalize_tool(point["tool"], aliases),
                total_tokens=point["totalTokens"],
                input_tokens=point["inputTokens"],
                output_tokens=point["outputTokens"],
                cache_read_tokens=point["cacheReadTokens"],
            )
        )
    return normalized_points
