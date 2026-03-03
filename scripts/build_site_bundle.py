#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: build_site_bundle.py <repo-root>", file=sys.stderr)
        return 1

    repo_root = Path(sys.argv[1]).resolve()
    source_web = repo_root / "web"
    source_snapshot = repo_root / "data" / "snapshots" / "latest.json"
    out_dir = repo_root / ".site"

    if out_dir.exists():
        shutil.rmtree(out_dir)

    shutil.copytree(source_web, out_dir)
    target_snapshot = out_dir / "data" / "snapshots"
    target_snapshot.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_snapshot, target_snapshot / "latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
