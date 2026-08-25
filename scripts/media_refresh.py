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

from error_surface import failure_details, latest_failed_stage, wrapped_stage_timeline
from provider_preflight import vercel_cli_preflight
from roll_site import Result

ROOT = Path(__file__).resolve().parents[1]


def utc_digest() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H")


def command_runner(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> Result:
    done = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    return Result(command, done.returncode, done.stdout, done.stderr)


def _failed_event(stages: list[dict]) -> dict | None:
    failed = [row for row in stages if row.get("status") == "failed"]
    return failed[-1] if failed else None


def _provider_stage(preflight: dict, started: datetime, completed: datetime) -> dict:
    ok = preflight.get("status") == "ok"
    version = preflight.get("version") or "unknown"
    minimum = preflight.get("minimum_version") or "unknown"
    return {
        "stage": "vercel-cli",
        "status": "ok" if ok else "failed",
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "completed_at": completed.isoformat().replace("+00:00", "Z"),
        "duration_ms": max(0, round((completed - started).total_seconds() * 1000)),
        "exit_code": 0 if ok else 1,
        "log_path": None,
        "summary": (
            f"Vercel CLI {version} (minimum {minimum})"
            if ok
            else str(preflight.get("error") or "Vercel CLI preflight failed")
        ),
    }


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
        "schema_name": "media_refresh.v2",
        "site_id": site_id,
        "target": target,
        "digest_at": digest,
        "provider": None,
        "sensing": None,
        "publish": None,
        "provider_stages": [],
        "sensing_stages": [],
        "publication_stages": [],
    }

    provider_started = datetime.now(timezone.utc)
    preflight = vercel_cli_preflight(runner, cwd=root)
    provider_completed = datetime.now(timezone.utc)
    provider_stage = _provider_stage(preflight, provider_started, provider_completed)
    base["provider"] = preflight
    base["provider_stages"] = [provider_stage]
    if preflight.get("status") != "ok":
        return base | {
            "status": "failed",
            "failed_lane": "provider",
            "failed_stage": "vercel-cli",
            "error": preflight.get("error") or "Vercel CLI preflight failed",
            "diagnostic_log": None,
        }, 1

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
    sensing_started_at = datetime.now(timezone.utc)
    sensing = runner(["bin/run_minimal_loop_once.sh", "--lane", "sensing"], cwd=root, env=env)
    sensing_stages = wrapped_stage_timeline(
        root,
        lane="sensing",
        digest_at=digest,
        since=sensing_started_at,
    )
    base["sensing_stages"] = sensing_stages
    base["sensing"] = {
        "status": "ok" if sensing.exit_code == 0 else "failed",
        "exit_code": sensing.exit_code,
        "stage_count": len(sensing_stages),
    }
    if sensing.exit_code:
        details = latest_failed_stage(
            root,
            lane="sensing",
            digest_at=digest,
            since=sensing_started_at,
        )
        if details is None:
            details = failure_details(sensing.stdout, sensing.stderr, "live sensing failed")
        return base | {
            "status": "failed",
            "failed_lane": details.lane or "sensing",
            "failed_stage": details.stage or "sensing",
            "error": details.summary,
            "diagnostic_log": details.log_path,
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
    roll_payload = publish_payload.get("roll") if isinstance(publish_payload, dict) else None
    publication_stages = list((roll_payload or {}).get("stages") or [])
    base["publication_stages"] = publication_stages

    if publish.exit_code:
        stage_event = _failed_event(publication_stages)
        details = failure_details(publish.stdout, publish.stderr, "publish failed")
        return base | {
            "status": "failed",
            "failed_lane": "publication",
            "failed_stage": (
                (stage_event or {}).get("stage")
                or publish_payload.get("failed_stage")
                or details.stage
                or "publish"
            ),
            "error": (
                (stage_event or {}).get("summary")
                or publish_payload.get("error")
                or details.summary
            ),
            "diagnostic_log": (stage_event or {}).get("log_path") or details.log_path,
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


def _duration(value: object) -> str:
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return "   — "
    if ms < 1000:
        return f"{ms:>4}ms"
    return f"{ms / 1000:>4.1f}s"


def _print_timeline(report: dict) -> None:
    rows: list[tuple[str, dict]] = []
    rows.extend(("provider", row) for row in report.get("provider_stages") or [])
    rows.extend(("sensing", row) for row in report.get("sensing_stages") or [])
    rows.extend(("publication", row) for row in report.get("publication_stages") or [])
    if not rows:
        return
    print("PIPELINE")
    for lane, row in rows:
        status = row.get("status")
        icon = "✓" if status in {"ok", "success"} else "✗" if status == "failed" else "·"
        stage = str(row.get("stage") or "unknown")
        print(f"  {icon} {lane}:{stage:<30} {_duration(row.get('duration_ms'))}")
        if lane == "provider" and status in {"ok", "success"} and row.get("summary"):
            print(f"      info:  {row['summary']}")
        if status == "failed" and row.get("summary"):
            print(f"      error: {row['summary']}")
        if status == "failed" and row.get("log_path"):
            print(f"      log:   {row['log_path']}")


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
        return code

    if report["status"] == "ok":
        print("MEDIA REFRESH: OK")
    else:
        print("MEDIA REFRESH: FAILED")
    print(f"site={report['site_id']} target={report['target']} digest={report['digest_at']}")
    _print_timeline(report)

    if report["status"] == "ok":
        print(
            f"snapshot={report.get('snapshot_id')} items={report.get('item_count')} "
            f"sections={report.get('section_count')} host={report.get('deployment_host')}"
        )
    else:
        print(
            f"failed_lane={report.get('failed_lane')} failed_stage={report.get('failed_stage')} "
            f"error={report.get('error')}"
        )
        if report.get("diagnostic_log"):
            print(f"diagnostic_log={report['diagnostic_log']}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
