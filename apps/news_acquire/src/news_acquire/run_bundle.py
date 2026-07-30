"""Immutable local sensing-run bundle construction.

This module owns producer evidence only.  Promotion into cumulative/latest local
state is deliberately implemented by a separate compatibility command.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


DIGEST_RE = re.compile(r"^\d{8}T\d{2}$")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_run_id(value: str) -> str:
    if not value or value in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
        raise ValueError("run_id must contain only letters, digits, '.', '_', ':', or '-'")
    return value


def default_run_id(digest_at: str, attempt: int) -> str:
    return f"sensing:{digest_at}:attempt:{attempt}:{uuid.uuid4().hex}"


@dataclass(frozen=True)
class StageResult:
    stage: str
    command: list[str]
    returncode: int
    started_at: str
    ended_at: str
    stdout: str
    stderr: str

    @property
    def status(self) -> str:
        return "success" if self.returncode == 0 else "error"

    def public_record(self) -> dict:
        return {
            "stage": self.stage,
            "command": self.command,
            "returncode": self.returncode,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


def execute_stage(stage: str, command: Sequence[str], env: dict[str, str], cwd: Path) -> StageResult:
    started_at = utc_now_iso()
    proc = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    return StageResult(
        stage=stage,
        command=list(command),
        returncode=proc.returncode,
        started_at=started_at,
        ended_at=utc_now_iso(),
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def pipeline_commands(python: str, digest_at: str, work_root: Path, repo_root: Path) -> list[tuple[str, list[str]]]:
    data = work_root / "data"
    storage = work_root / "storage"
    contracts = repo_root / "contracts"
    return [
        ("s01", [python, "-m", "apps.news_acquire.src.news_acquire.stage01_digests"]),
        ("s02", [python, "-m", "apps.news_acquire.src.news_acquire.stage02_master_index_update"]),
        ("s03", [python, "-m", "apps.news_acquire.src.news_acquire.stage03_headlines_digests"]),
        (
            "export_pr3a",
            [python, "scripts/export_pr3a_buses.py", "--digest-at", digest_at, "--data-dir", str(data), "--storage-dir", str(storage), "--contracts-dir", str(contracts)],
        ),
        (
            "build_news_access_indexes",
            [python, "scripts/build_news_access_indexes.py", "--digest-at", digest_at, "--storage-dir", str(storage), "--allow-empty"],
        ),
    ]


def run_pipeline(
    python: str, digest_at: str, work_root: Path, repo_root: Path, extra_env: dict[str, str]
) -> list[StageResult]:
    env = {
        **os.environ,
        **extra_env,
        "PYTHONPATH": str(repo_root),
        "DIGEST_AT": digest_at,
        "DATA_DIR": str(work_root / "data"),
        "WRITE_ARTIFACTS": "1",
    }
    results: list[StageResult] = []
    for stage, command in pipeline_commands(python, digest_at, work_root, repo_root):
        result = execute_stage(stage, command, env, repo_root)
        results.append(result)
        if result.returncode != 0:
            break
    return results


def _copy_tree_contents(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    for path in sorted(source.rglob("*")):
        if path.is_file():
            relative = path.relative_to(source)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _copy_if_exists(source: Path, destination: Path) -> None:
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _jsonl_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def finalize_bundle(
    *,
    run_root: Path,
    run_id: str,
    digest_at: str,
    attempt: int,
    work_root: Path,
    feed_config: Path,
    stage_results: Sequence[StageResult],
    started_at: str,
    source_commit: str,
    image_digest: str | None = None,
) -> Path:
    """Create a new finalized bundle without overwriting prior run evidence."""
    safe_run_id(run_id)
    final_dir = run_root / "runs" / run_id
    if final_dir.exists():
        raise FileExistsError(f"immutable run bundle already exists: {final_dir}")
    staging = run_root / ".staging" / run_id
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        _copy_if_exists(feed_config, staging / "inputs" / "sensing_feeds.v1.yaml")
        _copy_if_exists(
            work_root / "input_snapshot" / "master_ref.csv", staging / "inputs" / "master_ref.csv"
        )
        _copy_tree_contents(work_root / "data" / "rss_slices", staging / "stage_outputs" / "rss_slices")
        _copy_tree_contents(work_root / "data" / "digest_map", staging / "stage_outputs" / "digest_map")
        _copy_tree_contents(work_root / "data" / "digest_jsonls", staging / "stage_outputs" / "digest_jsonls")
        _copy_tree_contents(work_root / "data" / "output_digests", staging / "stage_outputs" / "output_digests")
        _copy_tree_contents(work_root / "data" / "quarantine", staging / "evidence" / "quarantine")
        _copy_tree_contents(work_root / "storage" / "buses", staging / "contracts" / "buses")
        _copy_tree_contents(work_root / "storage" / "runs", staging / "evidence" / "export_runs")
        _copy_if_exists(work_root / "data" / "master_ref.csv", staging / "candidates" / "master_ref.csv")
        _copy_if_exists(
            work_root / "storage" / "indexes" / "news_recent_refs_latest.jsonl",
            staging / "candidates" / "news_recent_refs.jsonl",
        )
        _copy_if_exists(
            work_root / "storage" / "indexes" / "news_recent_groups_latest.jsonl",
            staging / "candidates" / "news_recent_groups.jsonl",
        )

        evidence = staging / "evidence"
        evidence.mkdir(parents=True, exist_ok=True)
        with (evidence / "stage_results.jsonl").open("w", encoding="utf-8") as fh:
            for result in stage_results:
                fh.write(json.dumps(result.public_record(), ensure_ascii=False) + "\n")
                (evidence / "logs").mkdir(parents=True, exist_ok=True)
                (evidence / "logs" / f"{result.stage}.stdout.log").write_text(result.stdout, encoding="utf-8")
                (evidence / "logs" / f"{result.stage}.stderr.log").write_text(result.stderr, encoding="utf-8")

        failed = next((result for result in stage_results if result.returncode != 0), None)
        if failed:
            (evidence / "exception.json").write_text(
                json.dumps(
                    {"stage": failed.stage, "returncode": failed.returncode, "stderr": failed.stderr},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        quarantine_count = sum(_jsonl_count(path) for path in (evidence / "quarantine").rglob("*.jsonl"))
        refs_count = _jsonl_count(staging / "candidates" / "news_recent_refs.jsonl")
        groups_count = _jsonl_count(staging / "candidates" / "news_recent_groups.jsonl")
        if failed:
            status = "error"
        elif quarantine_count:
            status = "partial_success"
        elif refs_count == 0 and groups_count == 0:
            status = "empty_success"
        else:
            status = "success"

        artifact_paths = sorted(
            path.relative_to(staging).as_posix()
            for path in staging.rglob("*")
            if path.is_file()
        )
        checksums = {relative: sha256_file(staging / relative) for relative in artifact_paths}
        (evidence / "checksums.json").write_text(
            json.dumps(checksums, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        manifest = {
            "schema_version": "sensing_run_bundle.v1",
            "logical_run_id": f"sensing:{digest_at}",
            "run_id": run_id,
            "attempt": attempt,
            "digest_at": digest_at,
            "source_commit": source_commit,
            "image_digest": image_digest,
            "feed_config_sha256": checksums.get("inputs/sensing_feeds.v1.yaml"),
            "input_state_digest": checksums.get("inputs/master_ref.csv"),
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "status": status,
            "stage_results": [result.public_record() for result in stage_results],
            "output_artifacts": artifact_paths,
            "checksums_path": "evidence/checksums.json",
            "counts": {"news_ref": refs_count, "news_digest_group": groups_count},
            "quarantine_count": quarantine_count,
            "failure_code": f"{failed.stage}_exit_{failed.returncode}" if failed else None,
        }
        (staging / "run_record.json").write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        # Manifest and marker are finalization metadata and are intentionally last.
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        (staging / "FINALIZED").write_text(f"{status}\n", encoding="utf-8")
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(final_dir)
        return final_dir
    except Exception:
        # Staging remains inspectable, but it is never discoverable as a finalized run.
        raise


def git_commit(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True, check=False
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def execute_bundle(
    *,
    run_root: Path,
    digest_at: str,
    attempt: int,
    run_id: str | None = None,
    python: str = sys.executable,
    source_commit: str | None = None,
    image_digest: str | None = None,
) -> Path:
    if not DIGEST_RE.fullmatch(digest_at):
        raise ValueError("digest_at must use YYYYMMDDTHH")
    repo_root = Path(__file__).resolve().parents[4]
    selected_run_id = safe_run_id(run_id or default_run_id(digest_at, attempt))
    work_root = run_root / ".work" / selected_run_id
    if work_root.exists():
        raise FileExistsError(f"run workspace already exists: {work_root}")
    work_root.mkdir(parents=True)
    local_master = repo_root / "data" / "master_ref.csv"
    if local_master.exists():
        (work_root / "data").mkdir(parents=True, exist_ok=True)
        (work_root / "input_snapshot").mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_master, work_root / "data" / "master_ref.csv")
        shutil.copy2(local_master, work_root / "input_snapshot" / "master_ref.csv")
    started_at = utc_now_iso()
    feed_config = Path(os.getenv("SENSING_FEED_CONFIG", repo_root / "config" / "sensing_feeds.v1.yaml"))
    extra_env = {
        "SENSING_FEED_CONFIG": str(feed_config),
        "ACQUIRE_NETWORK": os.getenv("ACQUIRE_NETWORK", "1"),
        "ENQUEUE_SCRAPE": os.getenv("ENQUEUE_SCRAPE", "0"),
        "DB_RUN_BOOKKEEPING": os.getenv("DB_RUN_BOOKKEEPING", "0"),
    }
    results = run_pipeline(python, digest_at, work_root, repo_root, extra_env)
    bundle = finalize_bundle(
        run_root=run_root,
        run_id=selected_run_id,
        digest_at=digest_at,
        attempt=attempt,
        work_root=work_root,
        feed_config=feed_config,
        stage_results=results,
        started_at=started_at,
        source_commit=source_commit or git_commit(repo_root),
        image_digest=image_digest,
    )
    shutil.rmtree(work_root)
    return bundle
