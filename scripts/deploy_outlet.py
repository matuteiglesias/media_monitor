#!/usr/bin/env python3
"""Compile, materialize and deploy one configured outlet without cross-outlet state."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Callable

from outlet_runtime import resolve_outlet_runtime
from roll_site import Result, hostname, sha256, subprocess_runner, vercel_command, _validate_production_freshness


def utciso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def deployment_env(site: dict[str, Any], *, base: dict[str, str] | None = None) -> dict[str, str]:
    config = site.get("deployment")
    if not isinstance(config, dict) or config.get("provider") != "vercel":
        raise ValueError("site deployment.provider must be vercel")
    env = dict(base or os.environ)
    org_name = str(config.get("org_id_env") or "").strip()
    project_name = str(config.get("project_id_env") or "").strip()
    for configured_name, standard_name in ((org_name, "VERCEL_ORG_ID"), (project_name, "VERCEL_PROJECT_ID")):
        if not configured_name:
            raise ValueError(f"site deployment is missing {standard_name.lower()} source")
        value = env.get(configured_name, "").strip()
        if not value:
            raise ValueError(f"missing deployment environment variable {configured_name}")
        env[standard_name] = value
    return env


def call(runner, command: list[str], *, root: Path, env: dict[str, str] | None = None) -> Result:
    result = runner(command, cwd=root, env=env)
    if result.exit_code:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{' '.join(command[:3])} failed (exit {result.exit_code}): {detail[:500]}")
    return result


def deploy(
    *,
    repo_root: Path,
    site_id: str,
    digest_at: str,
    target: str,
    runner: Callable = subprocess_runner,
    sleep: Callable[[float], None] = time.sleep,
    now: str | None = None,
) -> tuple[dict[str, Any], int]:
    if target not in {"preview", "production"}:
        raise ValueError("target must be preview or production")
    root = repo_root.resolve()
    runtime = resolve_outlet_runtime(root, site_id)
    site = read_json(runtime.site_config)
    env = deployment_env(site)
    env.update({"SITE_ID": site_id, "DIGEST_AT": digest_at})

    public_url_env = str((site.get("deployment") or {}).get("public_url_env") or "").strip()
    if target == "production" and public_url_env and not env.get(public_url_env, "").strip():
        raise ValueError(f"production requires canonical outlet URL in {public_url_env}")

    record: dict[str, Any] = {
        "schema_name": "configured_outlet_roll.v1",
        "status": "failed",
        "site_id": site_id,
        "digest_at": digest_at,
        "target": target,
        "storage_dir": str(runtime.storage_dir),
        "snapshot_id": None,
        "snapshot_sha256": None,
        "deployment_host": None,
        "expected": {},
        "observed": {},
        "started_at": utciso(),
        "completed_at": None,
        "failed_stage": None,
        "error": None,
    }
    stage = "compile"
    try:
        compile_cmd = [
            sys.executable, "scripts/compile_outlet.py",
            "--site-id", site_id,
            "--digest-at", digest_at,
        ]
        if now:
            compile_cmd += ["--now", now]
        call(runner, compile_cmd, root=root, env=env)

        stage = "validate"
        validate_cmd = [
            sys.executable, "scripts/validate_site_snapshot.py",
            "--site-id", site_id,
            "--digest-at", digest_at,
            "--input", str(runtime.snapshot_path),
        ]
        if now:
            validate_cmd += ["--now", now]
        call(runner, validate_cmd, root=root, env=env)

        stage = "materialize"
        call(
            runner,
            [sys.executable, "scripts/materialize_outlet_site.py", "--site-id", site_id],
            root=root,
            env=env,
        )
        materialized = root / "apps/news_site/public/data/site_snapshot.json"
        payload = read_json(materialized)
        if payload.get("site", {}).get("site_id") != site_id or payload.get("digest_at") != digest_at:
            raise ValueError("materialized snapshot identity mismatch")
        expected = {
            "item_count": payload["metrics"]["item_count"],
            "section_count": payload["metrics"]["section_count"],
            "published_article_count": payload["metrics"].get("published_article_count", 0),
            "curated_signal_count": payload["metrics"].get("curated_signal_count", 0),
            "story_context_count": payload["metrics"].get("story_context_count", 0),
        }
        record.update(
            snapshot_id=payload["snapshot_id"],
            snapshot_sha256=sha256(materialized),
            expected=expected,
        )

        stage = "pull"
        environment = "production" if target == "production" else "preview"
        call(runner, vercel_command("pull", "--yes", f"--environment={environment}"), root=root, env=env)

        stage = "build"
        output = root / ".vercel/output"
        shutil.rmtree(output, ignore_errors=True)
        build_started = time.time_ns()
        build_args = ["build"] + (["--prod"] if target == "production" else [])
        call(runner, vercel_command(*build_args), root=root, env=env)
        if not output.exists() or output.stat().st_mtime_ns < build_started:
            raise RuntimeError("missing or stale .vercel/output")
        if sha256(materialized) != record["snapshot_sha256"]:
            raise RuntimeError("materialized snapshot changed during Vercel build")

        stage = "deploy"
        deploy_args = ["deploy", "--prebuilt"] + (["--prod"] if target == "production" else [])
        deployed = call(runner, vercel_command(*deploy_args), root=root, env=env)
        host = hostname(deployed.stdout)
        record["deployment_host"] = host

        stage = "health"
        observed = None
        for attempt in range(3):
            health = runner(vercel_command("curl", "/api/health", "--deployment", host), cwd=root, env=env)
            if health.exit_code == 0:
                try:
                    observed = json.loads(health.stdout)
                except json.JSONDecodeError:
                    observed = None
                if isinstance(observed, dict):
                    break
            if attempt < 2:
                sleep(5)
        if not isinstance(observed, dict):
            raise RuntimeError("health endpoint did not return valid JSON")
        required = {
            "status": "ok",
            "site_id": site_id,
            "snapshot_id": record["snapshot_id"],
            "digest_at": digest_at,
            **expected,
        }
        mismatches = {
            key: {"expected": value, "observed": observed.get(key)}
            for key, value in required.items()
            if observed.get(key) != value
        }
        if mismatches:
            raise RuntimeError(f"deployed health identity mismatch: {mismatches}")
        observed_record = {key: observed.get(key) for key in required if key != "status"}
        if target == "production":
            publication = _validate_production_freshness(observed)
            observed_record.update(
                freshness_status=publication.get("freshness_status"),
                within_target=publication.get("within_target"),
                age_minutes=publication.get("age_minutes"),
            )
        record["observed"] = observed_record
        record["status"] = "ok"
    except Exception as exc:
        record["failed_stage"] = stage
        record["error"] = str(exc)

    record["completed_at"] = utciso()
    roll_path = runtime.storage_dir / "observability" / f"configured_outlet_roll_latest_{site_id}.json"
    atomic_json(roll_path, record)
    return record, 0 if record["status"] == "ok" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--target", choices=["preview", "production"], required=True)
    parser.add_argument("--now")
    args = parser.parse_args()
    record, code = deploy(
        repo_root=args.repo_root,
        site_id=args.site_id,
        digest_at=args.digest_at,
        target=args.target,
        now=args.now,
    )
    print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
