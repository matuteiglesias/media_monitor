#!/usr/bin/env python3
"""Run a fresh sensing cycle, then publish the exact resulting digest.

This is the human golden path for making the monitored outlet current. It deliberately
refreshes sensing before publication so deterministic curation is evaluated against
fresh source material rather than an old leased digest.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from roll_site import Result

ROOT = Path(__file__).resolve().parents[1]


def utc_digest() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H")


def command_runner(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> Result:
    done = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    return Result(command, done.returncode, done.stdout, done.stderr)


def refresh(
    *,
    site_id: str,
    target: str,
    repo_root: Path,
    digest_at: str | None = None,
    runner: Callable[..., Result] = command_runner,
    python_executable: str = sys.executable,
) -> tuple[dict, int]:
    root = repo_root.resolve()
    digest = digest_at or utc_digest()
    base = {
        "schema_name": "media_refresh.v1",
        "site_id": site_id,
        "target": target,
        "digest_at": digest,
        "sensing": None,
        "publish": None,
    }

    env = os.environ.copy()
    env.update(
        {
            "DIGEST_AT": digest,
            "DRY_RUN": "0",
            "ACQUIRE_NETWORK": "1",
            "WRITE_ARTIFACTS": "1",
            "ENQUEUE_SCRAPE": "0",
            "DB_RUN_BOOKKEEPING": "0",
            "OPERATOR": "media-cli-refresh",
            "TRIGGER_TYPE": "manual",
        }
    )
    sensing = runner(["bin/run_minimal_loop_once.sh", "--lane", "sensing"], cwd=root, env=env)
    base["sensing"] = {
        "status": "ok" if sensing.exit_code == 0 else "failed",
        "exit_code": sensing.exit_code,
    }
    if sensing.exit_code:
        return base | {
            "status": "failed",
            "failed_stage": "sensing",
            "error": sensing.stderr.strip() or sensing.stdout.strip() or "live sensing failed",
        }, 1

    publish = runner(
        [
            python_executable,
            "scripts/media_ops.py",
            "--repo-root",
            str(root),
            "publish",
            "--site-id",
            site_id,
            "--target",
            target,
            "--digest-at",
            digest,
            "--json",
        ],
        cwd=root,
        env=os.environ.copy(),
    )
    try:
        publish_payload = json.loads(publish.stdout) if publish.stdout.strip() else {}
    except json.JSONDecodeError:
        publish_payload = {}
    base["publish"] = publish_payload or {"exit_code": publish.exit_code}
    if publish.exit_code:
        return base | {
            "status": "failed",
            "failed_stage": publish_payload.get("failed_stage") or "publish",
            "error": publish_payload.get("error") or publish.stderr.strip() or "publish failed",
        }, 1

    return base | {
        "status": "ok",
        "snapshot_id": publish_payload.get("snapshot_id"),
        "deployment_host": publish_payload.get("deployment_host"),
        "item_count": publish_payload.get("item_count"),
        "section_count": publish_payload.get("section_count"),
    }, 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh live sensing, then publish the exact fresh digest")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--site-id", default="argentina-general")
    parser.add_argument("--target", choices=("preview", "production"), default="preview")
    parser.add_argument("--digest-at", help="Explicit UTC digest for controlled/manual recovery")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report, code = refresh(
        site_id=args.site_id,
        target=args.target,
        repo_root=args.repo_root,
        digest_at=args.digest_at,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["status"] == "ok":
        print("MEDIA REFRESH: OK")
        print(f"site={report['site_id']} target={report['target']} digest={report['digest_at']}")
        print(
            f"snapshot={report.get('snapshot_id')} items={report.get('item_count')} "
            f"sections={report.get('section_count')} host={report.get('deployment_host')}"
        )
    else:
        print("MEDIA REFRESH: FAILED")
        print(f"site={report['site_id']} target={report['target']} digest={report['digest_at']}")
        print(f"failed_stage={report.get('failed_stage')} error={report.get('error')}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
