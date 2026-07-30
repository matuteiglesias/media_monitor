#!/usr/bin/env python3
"""Publish deterministic cumulative/latest state from immutable sensing bundles."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.news_acquire.src.news_acquire.compactor import publish_compaction


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", default=os.getenv("SENSING_RUN_ROOT", "artifacts/sensing_runs"))
    parser.add_argument("--state-root", default=os.getenv("SENSING_STATE_ROOT", "storage/sensing_compacted"))
    args = parser.parse_args()
    generation = publish_compaction(Path(args.run_root), Path(args.state_root))
    print(f"[sensing-compactor] generation={generation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
