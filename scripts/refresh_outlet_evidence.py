#!/usr/bin/env python3
"""Refresh one configured outlet from RSS through selected full-text evidence."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.compile_outlet import compile_outlet
from scripts.enrich_selected_signals import enrich_selected
from scripts.outlet_runtime import OutletRuntime, resolve_outlet_runtime


@dataclass(frozen=True)
class Result:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def command_runner(command: list[str], *, cwd: Path, env: dict[str, str]) -> Result:
    done = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return Result(command, done.returncode, done.stdout, done.stderr)


def _utc_digest() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sensing_commands(
    runtime: OutletRuntime,
    digest_at: str,
    python_executable: str,
) -> list[tuple[str, list[str]]]:
    root = runtime.repo_root
    return [
        ("s01", [python_executable, "-m", "apps.news_acquire.src.news_acquire.stage01_digests"]),
        ("s02", [python_executable, "-m", "apps.news_acquire.src.news_acquire.stage02_master_index_update"]),
        ("s03", [python_executable, "-m", "apps.news_acquire.src.news_acquire.stage03_headlines_digests"]),
        (
            "export_pr3a",
            [
                python_executable,
                "scripts/export_pr3a_buses.py",
                "--digest-at",
                digest_at,
                "--data-dir",
                str(runtime.data_dir),
                "--storage-dir",
                str(runtime.storage_dir),
                "--contracts-dir",
                str(root / "contracts"),
            ],
        ),
        (
            "build_news_access_indexes",
            [
                python_executable,
                "scripts/build_news_access_indexes.py",
                "--digest-at",
                digest_at,
                "--storage-dir",
                str(runtime.storage_dir),
            ],
        ),
    ]


def run_sensing(
    *,
    runtime: OutletRuntime,
    digest_at: str,
    runner: Callable[..., Result] = command_runner,
    python_executable: str = sys.executable,
    limit: int | None = None,
) -> list[dict]:
    feed_config = runtime.require_feed_config()
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(runtime.repo_root),
            "DIGEST_AT": digest_at,
            "DATA_DIR": str(runtime.data_dir),
            "STORAGE_DIR": str(runtime.storage_dir),
            "SENSING_FEED_CONFIG": str(feed_config),
            "ACQUIRE_NETWORK": "1",
            "WRITE_ARTIFACTS": "1",
            "ENQUEUE_SCRAPE": "0",
            "DB_RUN_BOOKKEEPING": "0",
            "DRY_RUN": "0",
        }
    )
    env.pop("SENSING_SOURCE_NAME", None)
    if runtime.source_name:
        env["SENSING_SOURCE_NAME"] = runtime.source_name
    if limit is not None:
        env["LIMIT"] = str(limit)

    stages: list[dict] = []
    for stage, command in sensing_commands(runtime, digest_at, python_executable):
        result = runner(command, cwd=runtime.repo_root, env=env)
        stages.append(
            {
                "stage": stage,
                "status": "ok" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "command": command,
            }
        )
        if result.returncode:
            detail = (result.stderr or result.stdout or "").strip()[-1000:]
            raise RuntimeError(f"{stage} failed with exit={result.returncode}: {detail}")
    return stages


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def refresh(
    *,
    repo_root: Path,
    site_id: str,
    digest_at: str,
    as_of: str,
    max_enrich: int = 10,
    minimum_enriched: int = 5,
    minimum_text_chars: int = 500,
    timeout: int = 20,
    feed_limit: int | None = None,
    runner: Callable[..., Result] = command_runner,
    python_executable: str = sys.executable,
) -> tuple[dict, int]:
    runtime = resolve_outlet_runtime(repo_root, site_id)
    stages = run_sensing(
        runtime=runtime,
        digest_at=digest_at,
        runner=runner,
        python_executable=python_executable,
        limit=feed_limit,
    )
    compiled = compile_outlet(
        repo_root=repo_root,
        site_id=site_id,
        digest_at=digest_at,
        now=as_of,
    )
    enriched = enrich_selected(
        repo_root=repo_root,
        site_id=site_id,
        digest_at=digest_at,
        max_items=max_enrich,
        minimum_successes=minimum_enriched,
        minimum_text_chars=minimum_text_chars,
        timeout=timeout,
    )
    status = "ok" if enriched["status"] == "ok" else "failed"
    report = {
        "schema_name": "outlet_source_evidence_refresh.v1",
        "status": status,
        "site_id": site_id,
        "digest_at": digest_at,
        "as_of": as_of,
        "feed_config": str(runtime.require_feed_config()),
        "source_name": runtime.source_name,
        "storage_dir": str(runtime.storage_dir),
        "sensing_stages": stages,
        "selection_policy_id": compiled["selection_policy_id"],
        "selected_count": compiled["selected_count"],
        "story_context_count": compiled["story_context_count"],
        "accepted_enrichment_count": enriched["accepted_success_count"],
        "enrichment_written_count": enriched["written_count"],
        "enrichment_skipped_unchanged_count": enriched["skipped_unchanged_count"],
        "snapshot_path": compiled["snapshot_path"],
        "enrichment_report": str(
            runtime.storage_dir / "observability" / "selected_enrichment_latest.json"
        ),
    }
    _atomic_json(
        runtime.storage_dir / "observability" / "outlet_source_evidence_latest.json",
        report,
    )
    return report, 0 if status == "ok" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--site-id", default="southland")
    parser.add_argument("--digest-at", default=None, help="UTC hour YYYYMMDDTHH; defaults to current hour")
    parser.add_argument("--as-of", default=None, help="RFC3339 evaluation instant; defaults to now")
    parser.add_argument("--feed-limit", type=int, default=None, help="Optional per-feed item cap")
    parser.add_argument("--max-enrich", type=int, default=10)
    parser.add_argument("--minimum-enriched", type=int, default=5)
    parser.add_argument("--minimum-text-chars", type=int, default=500)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    digest_at = args.digest_at or _utc_digest()
    as_of = args.as_of or _utc_now()
    try:
        report, code = refresh(
            repo_root=args.repo_root,
            site_id=args.site_id,
            digest_at=digest_at,
            as_of=as_of,
            max_enrich=args.max_enrich,
            minimum_enriched=args.minimum_enriched,
            minimum_text_chars=args.minimum_text_chars,
            timeout=args.timeout,
            feed_limit=args.feed_limit,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema_name": "outlet_source_evidence_refresh.v1",
                    "status": "failed",
                    "site_id": args.site_id,
                    "digest_at": digest_at,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
