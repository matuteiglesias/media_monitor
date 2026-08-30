#!/usr/bin/env python3
"""Compile, prebuild, deploy, and verify one immutable source-site snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from error_surface import redact, summarize_failure


@dataclass
class Result:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str


def subprocess_runner(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> Result:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    return Result(command, completed.returncode, completed.stdout, completed.stderr)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def utciso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def stamp() -> str:
    return utcnow().strftime("%Y%m%dT%H%M%SZ")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return "unknown"


def hostname(output: str) -> str:
    values = set(re.findall(r"(?:https?://)?([a-z0-9][a-z0-9-]*\.vercel\.app)(?:\b|/)", output, re.I))
    if len(values) != 1:
        raise ValueError("expected exactly one deployment *.vercel.app hostname")
    return values.pop().lower()


def vercel_command(*args: str) -> list[str]:
    token = os.getenv("VERCEL_TOKEN", "").strip()
    if token and args and args[0] == "curl":
        return ["vercel", "--token", token, *args]
    command = ["vercel", *args]
    if token:
        command.extend(["--token", token])
    return command


def _safe_stage(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "stage"


def _write_stage_log(
    root: Path,
    *,
    site_id: str,
    digest_at: str,
    stage: str,
    started_at: str,
    stdout: str = "",
    stderr: str = "",
) -> str:
    directory = root / "storage/observability/site_roll_logs"
    directory.mkdir(parents=True, exist_ok=True)
    tag = re.sub(r"[^0-9]", "", started_at)[:17] or stamp()
    path = directory / f"{site_id}_{digest_at}_{tag}_{_safe_stage(stage)}.log"
    chunks: list[str] = []
    if stdout:
        chunks.extend(("[stdout]", redact(stdout).rstrip()))
    if stderr:
        chunks.extend(("[stderr]", redact(stderr).rstrip()))
    if not chunks:
        chunks.append("(no command output)")
    path.write_text("\n".join(chunks) + "\n", encoding="utf-8")
    return str(path.relative_to(root))


def _append_stage(
    record: dict,
    *,
    stage: str,
    status: str,
    started_at: str,
    completed_at: str,
    duration_ms: int,
    log_path: str | None = None,
    exit_code: int | None = None,
    summary: str | None = None,
) -> dict:
    event = {
        "stage": stage,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": max(0, int(duration_ms)),
        "exit_code": exit_code,
        "log_path": log_path,
        "summary": summary,
    }
    record.setdefault("stages", []).append(event)
    return event


def call(
    runner,
    command,
    root,
    env=None,
    stage="command",
    expose_output: bool = False,
    *,
    record: dict | None = None,
    site_id: str | None = None,
    digest_at: str | None = None,
) -> Result:
    started_at = utciso()
    started_ns = time.perf_counter_ns()
    result = runner(command, cwd=root, env=env)
    completed_at = utciso()
    duration_ms = round((time.perf_counter_ns() - started_ns) / 1_000_000)

    log_path = None
    summary = None
    if record is not None and site_id and digest_at:
        log_path = _write_stage_log(
            root,
            site_id=site_id,
            digest_at=digest_at,
            stage=stage,
            started_at=started_at,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        if result.exit_code:
            summary = summarize_failure(result.stdout, result.stderr, f"{stage} failed")
        _append_stage(
            record,
            stage=stage,
            status="failed" if result.exit_code else "ok",
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            exit_code=result.exit_code,
            log_path=log_path,
            summary=summary,
        )

    if result.exit_code:
        message = f"{stage} failed (exit {result.exit_code})"
        # Repository-controlled stages and instrumented publication stages may expose
        # a redacted semantic summary. Full output remains in the local diagnostic log.
        if expose_output or record is not None:
            detail = summary or summarize_failure(result.stdout, result.stderr, stage + " failed")
            if detail:
                message += f": {detail[:700]}"
        raise RuntimeError(message)
    return result


def record_base(site, target, digest, started, root) -> dict:
    return {
        "schema_name": "site_roll.v1",
        "status": "failed",
        "site_id": site,
        "target": target,
        "digest_at": digest,
        "snapshot_id": None,
        "snapshot_sha256": None,
        "expected": {},
        "observed": {},
        "git_sha": git_sha(root),
        "deployment_host": None,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "completed_at": None,
        "failed_stage": None,
        "error": None,
        "stages": [],
    }


def write_record(root: Path, record: dict) -> None:
    finished = utcnow()
    record["completed_at"] = finished.isoformat().replace("+00:00", "Z")
    run = root / "storage/runs" / f"site_roll_{record['site_id']}_{record['digest_at']}_{stamp()}.json"
    atomic_json(run, record)
    atomic_json(root / "storage/observability" / f"site_roll_latest_{record['site_id']}.json", record)


def _validate_production_freshness(observed: dict) -> dict:
    publication = observed.get("publication_health")
    if not isinstance(publication, dict):
        raise RuntimeError("production health is missing publication_health")
    if publication.get("schema_name") != "publication_health.v1":
        raise RuntimeError("production health has unexpected publication health schema")
    if publication.get("freshness_status") != "FRESH":
        raise RuntimeError(f"production publication is not fresh: {publication.get('freshness_status')}")
    if publication.get("is_current") is not True:
        raise RuntimeError("production publication does not report current state")
    if publication.get("within_target") is not True:
        raise RuntimeError(
            "production publication missed freshness target: "
            f"age_minutes={publication.get('age_minutes')}"
        )
    return publication


def roll(
    site_id: str,
    digest_at: str,
    target: str,
    repo_root: Path,
    runner: Callable = subprocess_runner,
    sleep: Callable = time.sleep,
):
    if target not in {"preview", "production"}:
        raise ValueError("--target must be preview or production")
    root = repo_root.resolve()
    started = utcnow()
    record = record_base(site_id, target, digest_at, started, root)

    def run(command, *, env=None, stage="command", expose_output=False):
        return call(
            runner,
            command,
            root,
            env=env,
            stage=stage,
            expose_output=expose_output,
            record=record,
            site_id=site_id,
            digest_at=digest_at,
        )

    stage = "publication-index"
    try:
        run(["make", "build-published-article-indexes", f"PYTHON={sys.executable}"], stage=stage)

        stage = "editorial-selection"
        selection_as_of = utcnow().isoformat().replace("+00:00", "Z")
        run(
            [
                sys.executable,
                "scripts/build_editorial_selection.py",
                "--digest-at",
                digest_at,
                "--as-of",
                selection_as_of,
            ],
            stage=stage,
            expose_output=True,
        )

        stage = "story-contexts"
        run(
            [
                sys.executable,
                "scripts/build_story_contexts.py",
                "--digest-at",
                digest_at,
            ],
            stage=stage,
        )

        stage = "compile"
        run(["make", "build-site-snapshot", f"SITE_ID={site_id}", f"DIGEST_AT={digest_at}"], stage=stage)
        stage = "validate"
        run(["make", "validate-site-snapshot", f"SITE_ID={site_id}", f"DIGEST_AT={digest_at}"], stage=stage)

        stage = "identity"
        identity_started_at = utciso()
        identity_started_ns = time.perf_counter_ns()
        snapshot = root / "apps/news_site/public/data/site_snapshot.json"
        payload = json.loads(snapshot.read_text())
        expected = {
            "item_count": payload["metrics"]["item_count"],
            "section_count": payload["metrics"]["section_count"],
            "published_article_count": payload["metrics"].get("published_article_count", 0),
            "curated_signal_count": payload["metrics"].get("curated_signal_count", 0),
            "story_context_count": payload["metrics"].get("story_context_count", 0),
        }
        if payload["site"]["site_id"] != site_id or payload["digest_at"] != digest_at:
            raise ValueError("snapshot identity does not match command arguments")
        record.update(snapshot_id=payload["snapshot_id"], snapshot_sha256=sha256(snapshot), expected=expected)
        _append_stage(
            record,
            stage=stage,
            status="ok",
            started_at=identity_started_at,
            completed_at=utciso(),
            duration_ms=round((time.perf_counter_ns() - identity_started_ns) / 1_000_000),
            summary=f"snapshot={payload['snapshot_id'][:12]} items={expected['item_count']} curated={expected['curated_signal_count']}",
        )

        stage = "pull"
        environment = "production" if target == "production" else "preview"
        run(vercel_command("pull", "--yes", f"--environment={environment}"), stage=stage)

        stage = "build"
        output = root / ".vercel/output"
        shutil.rmtree(output, ignore_errors=True)
        build_started = time.time_ns()
        build_env = os.environ.copy()
        build_env.update({"SITE_ID": site_id, "DIGEST_AT": digest_at})
        build_args = ["build"] + (["--prod"] if target == "production" else [])
        run(vercel_command(*build_args), env=build_env, stage=stage)
        if not output.exists() or output.stat().st_mtime_ns < build_started:
            raise RuntimeError("missing or stale .vercel/output")
        if sha256(snapshot) != record["snapshot_sha256"]:
            raise RuntimeError("source snapshot changed during Vercel build")

        stage = "deploy"
        deploy_args = ["deploy", "--prebuilt"] + (["--prod"] if target == "production" else [])
        deployed = run(vercel_command(*deploy_args), stage=stage)
        host = hostname(deployed.stdout)
        record["deployment_host"] = host

        stage = "health"
        health_started_at = utciso()
        health_started_ns = time.perf_counter_ns()
        health_logs: list[str] = []
        observed = None
        for attempt in range(3):
            health = runner(vercel_command("curl", "/api/health", "--deployment", host), cwd=root, env=None)
            health_logs.append(f"[attempt {attempt + 1} stdout]\n{health.stdout}\n[attempt {attempt + 1} stderr]\n{health.stderr}")
            if health.exit_code == 0:
                try:
                    observed = json.loads(health.stdout)
                except json.JSONDecodeError:
                    observed = None
                if observed is not None:
                    break
            if attempt < 2:
                sleep(5)
        health_log_path = _write_stage_log(
            root,
            site_id=site_id,
            digest_at=digest_at,
            stage=stage,
            started_at=health_started_at,
            stdout="\n".join(health_logs),
        )
        if observed is None:
            _append_stage(
                record,
                stage=stage,
                status="failed",
                started_at=health_started_at,
                completed_at=utciso(),
                duration_ms=round((time.perf_counter_ns() - health_started_ns) / 1_000_000),
                log_path=health_log_path,
                summary="health endpoint did not return valid JSON",
            )
            raise RuntimeError("health endpoint did not return valid JSON")

        required = {
            "status": "ok",
            "site_id": site_id,
            "snapshot_id": record["snapshot_id"],
            "digest_at": digest_at,
            "item_count": expected["item_count"],
            "section_count": expected["section_count"],
            "published_article_count": expected["published_article_count"],
            "curated_signal_count": expected["curated_signal_count"],
            "story_context_count": expected["story_context_count"],
        }
        if any(observed.get(key) != value for key, value in required.items()):
            raise RuntimeError("deployed health identity mismatch")

        observed_record = {
            key: observed[key]
            for key in (
                "site_id",
                "digest_at",
                "snapshot_id",
                "item_count",
                "section_count",
                "published_article_count",
                "curated_signal_count",
                "story_context_count",
            )
        }
        if target == "production":
            publication = _validate_production_freshness(observed)
            observed_record.update(
                freshness_status=publication.get("freshness_status"),
                within_target=publication.get("within_target"),
                age_minutes=publication.get("age_minutes"),
            )

        _append_stage(
            record,
            stage=stage,
            status="ok",
            started_at=health_started_at,
            completed_at=utciso(),
            duration_ms=round((time.perf_counter_ns() - health_started_ns) / 1_000_000),
            log_path=health_log_path,
            summary=f"host={host} identity=MATCH",
        )
        record.update(status="ok", observed=observed_record, failed_stage=None, error=None)
    except Exception as exc:
        # Pure-Python stages may fail outside `call`; make sure they still appear in
        # the ledger instead of leaving only a top-level failed_stage.
        if not any(event.get("stage") == stage and event.get("status") == "failed" for event in record.get("stages", [])):
            _append_stage(
                record,
                stage=stage,
                status="failed",
                started_at=utciso(),
                completed_at=utciso(),
                duration_ms=0,
                summary=redact(str(exc))[:700],
            )
        record.update(status="failed", failed_stage=stage, error=redact(str(exc))[:1200])
        write_record(root, record)
        return record, 1

    write_record(root, record)
    return record, 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--target", required=True, choices=("preview", "production"))
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    result, code = roll(args.site_id, args.digest_at, args.target, args.repo_root)
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
