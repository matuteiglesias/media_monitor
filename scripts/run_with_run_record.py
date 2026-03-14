#!/usr/bin/env python3
"""Minimal command wrapper that emits producer-side run telemetry.

This utility writes producer emissions under storage/observability by default.
It does not implement single-writer compaction for UI-facing indexes.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

HEALTH_THRESHOLDS_HOURS = {
    "sensing": {"healthy": 2, "degraded": 6},
    "editorial": {"healthy": 12, "degraded": 24},
    "enrich": {"healthy": 12, "degraded": 48},
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def health_state_for_lane(lane: str, last_success_at: str | None, now_dt: datetime) -> str:
    last_success_dt = parse_iso_utc(last_success_at)
    if not last_success_dt:
        return "down"
    threshold = HEALTH_THRESHOLDS_HOURS.get(lane, {"healthy": 6, "degraded": 24})
    age_h = (now_dt - last_success_dt).total_seconds() / 3600
    if age_h <= threshold["healthy"]:
        return "healthy"
    if age_h <= threshold["degraded"]:
        return "degraded"
    return "down"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, record: dict) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_json(path: Path, payload: dict) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def git_commit_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command and emit a producer run record.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--lane", default="unknown")
    parser.add_argument("--stage", default="unspecified")
    parser.add_argument("--trigger-type", default="manual")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--operator", default=os.getenv("USER", "unknown"))
    parser.add_argument("--inputs-count", type=int)
    parser.add_argument("--outputs-count", type=int)
    parser.add_argument("--telemetry-root", default="storage/observability")
    parser.add_argument("--runs-path")
    parser.add_argument("--manifests-dir")
    parser.add_argument("--logs-dir")
    parser.add_argument("--status-dir")
    parser.add_argument("--summary-path")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("missing command; pass command after '--'")
    return args


def _to_int_or_none(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None




def _read_json_file(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_pr3a_compact_summary(telemetry_root: Path) -> dict | None:
    storage_root = telemetry_root.parent
    compact_path = storage_root / "indexes" / "pr3a_export_compact_latest.json"
    return _read_json_file(compact_path)

def write_summary(runs_path: Path, status_dir: Path, summary_path: Path, now_dt: datetime) -> None:
    cutoff = now_dt - timedelta(hours=24)
    per_lane: dict[str, dict[str, object]] = {}

    if runs_path.exists():
        with runs_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                lane = rec.get("lane") or "unknown"
                started = parse_iso_utc(rec.get("started_at"))
                if not started or started < cutoff:
                    continue

                lane_acc = per_lane.setdefault(
                    lane,
                    {
                        "runs_24h": 0,
                        "success_24h": 0,
                        "failed_24h": 0,
                        "inputs_count_24h": 0,
                        "outputs_count_24h": 0,
                    },
                )
                lane_acc["runs_24h"] = int(lane_acc["runs_24h"]) + 1
                if rec.get("status") == "success":
                    lane_acc["success_24h"] = int(lane_acc["success_24h"]) + 1
                else:
                    lane_acc["failed_24h"] = int(lane_acc["failed_24h"]) + 1

                in_count = _to_int_or_none(rec.get("inputs_count"))
                out_count = _to_int_or_none(rec.get("outputs_count"))
                lane_acc["inputs_count_24h"] = int(lane_acc["inputs_count_24h"]) + (in_count or 0)
                lane_acc["outputs_count_24h"] = int(lane_acc["outputs_count_24h"]) + (out_count or 0)

    lane_status = {}
    if status_dir.exists():
        for status_file in sorted(status_dir.glob("*_latest.json")):
            try:
                payload = json.loads(status_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            lane = payload.get("lane") or status_file.name.replace("_latest.json", "")
            lane_status[lane] = payload

    summary = {
        "updated_at": now_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "window": "24h",
        "source": {
            "run_records_path": str(runs_path),
            "status_dir": str(status_dir),
        },
        "lanes": {},
    }

    for lane in sorted(set(per_lane) | set(lane_status)):
        summary["lanes"][lane] = {
            **per_lane.get(
                lane,
                {
                    "runs_24h": 0,
                    "success_24h": 0,
                    "failed_24h": 0,
                    "inputs_count_24h": 0,
                    "outputs_count_24h": 0,
                },
            ),
            "latest": lane_status.get(lane),
        }

    write_json(summary_path, summary)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)

    telemetry_root = Path(args.telemetry_root)
    runs_path = Path(args.runs_path) if args.runs_path else telemetry_root / "run_records.jsonl"
    manifests_dir = Path(args.manifests_dir) if args.manifests_dir else telemetry_root / "manifests"
    logs_dir = Path(args.logs_dir) if args.logs_dir else telemetry_root / "logs"
    status_dir = Path(args.status_dir) if args.status_dir else telemetry_root / "status"
    summary_path = Path(args.summary_path) if args.summary_path else status_dir / "summary.json"

    run_id = str(uuid.uuid4())
    started_at = utc_now_iso()
    now_dt = utc_now()

    log_path = logs_dir / f"{run_id}.log"
    manifest_path = manifests_dir / f"{run_id}.json"
    status_path = status_dir / f"{args.lane}_latest.json"

    ensure_parent(log_path)

    proc = subprocess.run(args.command, capture_output=True, text=True)

    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")

    with log_path.open("w", encoding="utf-8") as lf:
        if proc.stdout:
            lf.write("[stdout]\n")
            lf.write(proc.stdout)
            if not proc.stdout.endswith("\n"):
                lf.write("\n")
        if proc.stderr:
            lf.write("[stderr]\n")
            lf.write(proc.stderr)
            if not proc.stderr.endswith("\n"):
                lf.write("\n")

    status = "success" if proc.returncode == 0 else "failed"
    error_code = "" if proc.returncode == 0 else f"exit_{proc.returncode}"
    ended_at = utc_now_iso()

    manifest = {
        "run_id": run_id,
        "project_id": args.project_id,
        "lane": args.lane,
        "stage": args.stage,
        "trigger_type": args.trigger_type,
        "attempt": args.attempt,
        "command": args.command,
        "cwd": str(Path.cwd()),
        "hostname": socket.gethostname(),
        "git_commit": git_commit_sha(),
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "log_path": str(log_path),
    }
    write_json(manifest_path, manifest)

    run_record = {
        "run_id": run_id,
        "project_id": args.project_id,
        "lane": args.lane,
        "stage": args.stage,
        "trigger_type": args.trigger_type,
        "attempt": args.attempt,
        "operator": args.operator,
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        "error_code": error_code,
        "inputs_count": args.inputs_count,
        "outputs_count": args.outputs_count,
        "command": args.command,
        "cwd": str(Path.cwd()),
        "hostname": socket.gethostname(),
        "git_commit": git_commit_sha(),
        "manifest_path": str(manifest_path),
        "log_path": str(log_path),
    }
    append_jsonl(runs_path, run_record)

    previous = {}
    if status_path.exists():
        try:
            previous = json.loads(status_path.read_text(encoding="utf-8"))
        except Exception:
            previous = {}

    last_success_at = ended_at if status == "success" else previous.get("last_success_at")
    health_state = health_state_for_lane(args.lane, last_success_at, now_dt)

    status_payload = {
        "lane": args.lane,
        "updated_at": ended_at,
        "last_run_id": run_id,
        "last_started_at": started_at,
        "last_ended_at": ended_at,
        "last_status": status,
        "last_error_code": error_code or None,
        "last_success_at": last_success_at,
        "trigger_type": args.trigger_type,
        "attempt": args.attempt,
        "recent_inputs_count": args.inputs_count,
        "recent_outputs_count": args.outputs_count,
        "record_path": str(runs_path),
        "health_state": health_state,
    }

    if args.stage == "export_pr3a":
        compact = load_pr3a_compact_summary(telemetry_root)
        if compact:
            for key in (
                "last_successful_export_at",
                "last_exported_digest_at",
                "news_ref_count",
                "news_digest_group_count",
                "export_status",
                "failure_reason",
            ):
                status_payload[key] = compact.get(key)
    write_json(status_path, status_payload)

    write_summary(runs_path, status_dir, summary_path, now_dt)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
