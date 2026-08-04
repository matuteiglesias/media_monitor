#!/usr/bin/env python3
"""Compatibility entrypoint for the canonical enrich lane.

The enrichment implementation is owned by ``apps/news_enrich``.  This wrapper
keeps the historical lane contract working while delegating execution to that
module-owned entrypoint instead of duplicating orchestration here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    owner_entrypoint = (
        repo_root / "apps" / "news_enrich" / "entrypoints" / "run_enrich_owner.sh"
    )
    if not owner_entrypoint.is_file():
        print(
            f"Missing enrich owner entrypoint: {owner_entrypoint}",
            file=sys.stderr,
        )
        return 2

    env = os.environ.copy()
    env.setdefault("MODE", "batch")
    command = ["bash", str(owner_entrypoint), *sys.argv[1:]]
    return subprocess.run(command, cwd=repo_root, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
