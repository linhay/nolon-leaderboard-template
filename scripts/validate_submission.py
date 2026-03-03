#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from leaderboard_core import ValidationError, load_json, validate_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate leaderboard submission JSON file")
    parser.add_argument("submission", type=Path, help="Path to submission JSON file")
    args = parser.parse_args()

    try:
        payload = load_json(args.submission)
        validate_payload(payload)
    except FileNotFoundError:
        print(f"submission file not found: {args.submission}", file=sys.stderr)
        return 1
    except ValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"unexpected validation error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
