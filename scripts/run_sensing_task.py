#!/usr/bin/env python3
"""Cloud-safe sensing task: build one bundle and upload only its run prefix."""

from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.news_acquire.src.news_acquire.run_bundle import execute_bundle
from apps.news_acquire.src.news_acquire.s3_store import boto3_store


def emit(event: str, **fields) -> None:
    print(json.dumps({"event": event, "lane": "sensing", **fields}, ensure_ascii=False), flush=True)


@contextmanager
def task_timeout(seconds: int):
    def expired(_signum, _frame):
        raise TimeoutError(f"sensing task exceeded {seconds}s timeout")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def run_denial_probe(store, prefix: str, run_id: str) -> None:
    key = f"{prefix.strip('/')}/latest/producer-denial-probe-{run_id}"
    try:
        store.client.put_object(Bucket=store.bucket, Key=key, Body=b"must-be-denied")
    except Exception as exc:
        response = getattr(exc, "response", {})
        code = str(response.get("Error", {}).get("Code") or "")
        if code in {"AccessDenied", "403"}:
            emit("iam_denial_confirmed", run_id=run_id, denied_key=key, error_code=code)
            return
        raise
    raise PermissionError(f"IAM denial probe unexpectedly wrote s3://{store.bucket}/{key}")


def main() -> int:
    digest_at = required_env("DIGEST_AT")
    bucket = required_env("SENSING_S3_BUCKET")
    prefix = os.getenv("SENSING_S3_PREFIX", "media-monitor/sensing")
    attempt = int(os.getenv("ATTEMPT", "1"))
    timeout_seconds = int(os.getenv("SENSING_TASK_TIMEOUT_SECONDS", "900"))
    if timeout_seconds < 1 or timeout_seconds > 900:
        raise ValueError("SENSING_TASK_TIMEOUT_SECONDS must be between 1 and 900")
    run_id = os.getenv("RUN_ID") or None
    source_commit = required_env("SOURCE_COMMIT")
    image_digest = required_env("IMAGE_DIGEST")
    emit("task_started", digest_at=digest_at, run_id=run_id, attempt=attempt, source_commit=source_commit, image_digest=image_digest)
    with tempfile.TemporaryDirectory(prefix="sensing-task-") as temporary:
        with task_timeout(timeout_seconds):
            bundle = execute_bundle(
                run_root=Path(temporary),
                digest_at=digest_at,
                attempt=attempt,
                run_id=run_id,
                source_commit=source_commit,
                image_digest=image_digest,
            )
            manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
            for stage_result in manifest["stage_results"]:
                emit(
                    "stage_completed",
                    run_id=manifest["run_id"],
                    digest_at=digest_at,
                    stage=stage_result["stage"],
                    status=stage_result["status"],
                    returncode=stage_result["returncode"],
                )
            emit("bundle_finalized", run_id=manifest["run_id"], digest_at=digest_at, status=manifest["status"])
            store = boto3_store(bucket, prefix, "producer")
            keys = store.upload_run_bundle(bundle)
            emit("bundle_uploaded", run_id=manifest["run_id"], digest_at=digest_at, status=manifest["status"], object_count=len(keys))
            if os.getenv("RUN_IAM_DENIAL_PROBE", "0") == "1":
                run_denial_probe(store, prefix, manifest["run_id"])
            return 1 if manifest["status"] == "error" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        emit("task_error", error_type=type(exc).__name__, error=str(exc))
        raise SystemExit(1)
