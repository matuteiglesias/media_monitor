#!/usr/bin/env python3
"""Execute one isolated sensing run and finalize its immutable evidence bundle."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.news_acquire.src.news_acquire.run_bundle import execute_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest-at", required=True, help="UTC hour in YYYYMMDDTHH format")
    parser.add_argument("--run-root", default=os.getenv("SENSING_RUN_ROOT", "artifacts/sensing_runs"))
    parser.add_argument("--run-id")
    parser.add_argument("--attempt", type=int, default=int(os.getenv("ATTEMPT", "1")))
    args = parser.parse_args()
    bundle = execute_bundle(
        run_root=Path(args.run_root), digest_at=args.digest_at, attempt=args.attempt, run_id=args.run_id
    )
    print(f"[sensing-bundle] finalized={bundle}")
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    return 1 if manifest.get("status") == "error" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[sensing-bundle] ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
