#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path


NAME_PATTERN = re.compile(
    r"^(?P<date>\d{8})-(?P<module>[a-z0-9-]+)-(?P<scene>[a-z0-9-]+)(?:-(?P<platform>ios|android|web))?-(?P<state>before|after|baseline|failed)-v(?P<ver>\d{2,})\.png$"
)


def read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a png: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def pair_key(match: re.Match[str]) -> tuple[str, str, str, str]:
    return (
        match.group("date"),
        match.group("module"),
        match.group("scene"),
        match.group("platform") or "",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate screenshot naming and before/after regression pairs.")
    parser.add_argument("screenshots_root", nargs="?", default="screenshots", help="screenshots root directory")
    args = parser.parse_args()

    root = Path(args.screenshots_root).resolve()
    if not root.exists():
        print(f"screenshots directory not found: {root}", file=sys.stderr)
        return 1

    before_map: dict[tuple[str, str, str, str], Path] = {}
    after_map: dict[tuple[str, str, str, str], Path] = {}
    errors: list[str] = []

    for file_path in sorted(root.rglob("*.png")):
        match = NAME_PATTERN.match(file_path.name)
        if not match:
            errors.append(f"invalid filename: {file_path}")
            continue
        state = match.group("state")
        key = pair_key(match)
        if state == "before":
            before_map[key] = file_path
        elif state == "after":
            after_map[key] = file_path

    all_keys = sorted(set(before_map.keys()) | set(after_map.keys()))
    for key in all_keys:
        before = before_map.get(key)
        after = after_map.get(key)
        if before is None or after is None:
            errors.append(f"missing pair for key={key}: before={bool(before)} after={bool(after)}")
            continue
        try:
            before_size = read_png_size(before)
            after_size = read_png_size(after)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if before_size != after_size:
            errors.append(
                f"dimension mismatch for key={key}: before={before_size} after={after_size}"
            )

    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1

    print(f"OK: validated {len(all_keys)} before/after screenshot pair(s) in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
