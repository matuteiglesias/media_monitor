#!/usr/bin/env python3
"""Cloud compactor seam: download bundles, compact locally, publish one generation."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.news_acquire.src.news_acquire.compactor import publish_compaction
from apps.news_acquire.src.news_acquire.s3_store import boto3_store


def emit(event: str, **fields) -> None:
    print(json.dumps({"event": event, "lane": "sensing", "component": "compactor", **fields}), flush=True)


def main() -> int:
    bucket = os.environ["SENSING_S3_BUCKET"]
    prefix = os.getenv("SENSING_S3_PREFIX", "media-monitor/sensing")
    store = boto3_store(bucket, prefix, "compactor")
    with tempfile.TemporaryDirectory(prefix="sensing-compactor-") as temporary:
        root = Path(temporary)
        run_root = root / "run-root"
        local_runs = run_root / "runs"
        run_ids = store.list_finalized_runs()
        for run_id in run_ids:
            store.download_run_bundle(run_id, local_runs)
        state_root = root / "state"
        generation = publish_compaction(run_root, state_root)
        pointer = json.loads((state_root / "current.json").read_text(encoding="utf-8"))
        keys = store.upload_compaction(generation, pointer)
        emit("compaction_uploaded", generation=generation.name, run_count=len(run_ids), object_count=len(keys))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit("compaction_error", error_type=type(exc).__name__, error=str(exc))
        raise SystemExit(1)
