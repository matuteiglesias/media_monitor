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
    command = ["vercel", *args]
    token = os.getenv("VERCEL_TOKEN", "").strip()
    if token:
        command.extend(["--token", token])
    return command


def call(runner, command, root, env=None, stage="command") -> Result:
    result = runner(command, cwd=root, env=env)
    if result.exit_code:
        raise RuntimeError(f"{stage} failed (exit {result.exit_code})")
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
    stage = "publication-index"
    try:
        call(runner, ["make", "build-published-article-indexes", f"PYTHON={sys.executable}"], root, stage=stage)
        stage = "compile"
        call(runner, ["make", "build-site-snapshot", f"SITE_ID={site_id}", f"DIGEST_AT={digest_at}"], root, stage=stage)
        stage = "validate"
        call(runner, ["make", "validate-site-snapshot", f"SITE_ID={site_id}", f"DIGEST_AT={digest_at}"], root, stage=stage)
        stage = "identity"
        snapshot = root / "apps/news_site/public/data/site_snapshot.json"
        payload = json.loads(snapshot.read_text())
        expected = {
            "item_count": payload["metrics"]["item_count"],
            "section_count": payload["metrics"]["section_count"],
            "published_article_count": payload["metrics"].get("published_article_count", 0),
            "curated_signal_count": payload["metrics"].get("curated_signal_count", 0),
        }
        if payload["site"]["site_id"] != site_id or payload["digest_at"] != digest_at:
            raise ValueError("snapshot identity does not match command arguments")
        record.update(snapshot_id=payload["snapshot_id"], snapshot_sha256=sha256(snapshot), expected=expected)

        stage = "pull"
        environment = "production" if target == "production" else "preview"
        call(runner, vercel_command("pull", "--yes", f"--environment={environment}"), root, stage=stage)

        stage = "build"
        output = root / ".vercel/output"
        shutil.rmtree(output, ignore_errors=True)
        build_started = time.time_ns()
        build_env = os.environ.copy()
        build_env.update({"SITE_ID": site_id, "DIGEST_AT": digest_at})
        build_args = ["build"] + (["--prod"] if target == "production" else [])
        call(runner, vercel_command(*build_args), root, build_env, stage)
        if not output.exists() or output.stat().st_mtime_ns < build_started:
            raise RuntimeError("missing or stale .vercel/output")
        if sha256(snapshot) != record["snapshot_sha256"]:
            raise RuntimeError("source snapshot changed during Vercel build")

        stage = "deploy"
        deploy_args = ["deploy", "--prebuilt"] + (["--prod"] if target == "production" else [])
        deployed = call(runner, vercel_command(*deploy_args), root, stage=stage)
        host = hostname(deployed.stdout)
        record["deployment_host"] = host

        stage = "health"
        observed = None
        for attempt in range(3):
            health = runner(vercel_command("curl", "/api/health", "--deployment", host), cwd=root, env=None)
            if health.exit_code == 0:
                try:
                    observed = json.loads(health.stdout)
                except json.JSONDecodeError:
                    observed = None
                if observed is not None:
                    break
            if attempt < 2:
                sleep(5)
        if observed is None:
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
            )
        }
        if target == "production":
            publication = _validate_production_freshness(observed)
            observed_record.update(
                freshness_status=publication.get("freshness_status"),
                within_target=publication.get("within_target"),
                age_minutes=publication.get("age_minutes"),
            )

        record.update(status="ok", observed=observed_record, failed_stage=None, error=None)
    except Exception as exc:
        record.update(status="failed", failed_stage=stage, error=str(exc))
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
