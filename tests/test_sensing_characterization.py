"""Characterization tests for the pre-retrofit sensing runtime.

These tests intentionally pin current behaviour, including defects.  PR-A0 is an
inventory PR; changing the assertions belongs in the repair PR that follows it.
"""

from __future__ import annotations

import inspect
import json
import subprocess
import sys
import types
from pathlib import Path

import pandas as pd

# Acquisition's optional runtime dependencies are not required for these isolated
# characterizations.  Stubbing them also documents that no network/DB is used.
sys.modules.setdefault("psycopg", types.SimpleNamespace(connect=lambda *_a, **_k: None))
sys.modules.setdefault("feedparser", types.SimpleNamespace(parse=lambda *_a, **_k: None))

from apps.news_acquire.src.news_acquire import db
from apps.news_acquire.src.news_acquire import stage01_digests as stage01


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_repeated_digest_mirror_replaces_instead_of_appending(tmp_path: Path) -> None:
    """A same-DIGEST_AT mirror retry replaces the previous digest object."""
    output = tmp_path / "20250101T00.jsonl"

    stage01.write_jsonl_mirror_atomic(output, [{"attempt": 1}, {"attempt": 1}])
    stage01.write_jsonl_mirror_atomic(output, [{"attempt": 2}])

    assert [json.loads(line) for line in output.read_text().splitlines()] == [{"attempt": 2}]
    assert not output.with_suffix(".jsonl.tmp").exists()


def test_finish_run_signature_accepts_stage_and_meta_after_a1() -> None:
    """PR-A1 aligns the DB helper with acquisition-stage call sites."""
    signature = inspect.signature(db.finish_run)

    assert list(signature.parameters) == ["run_id", "ok", "fail", "stage", "meta"]


def test_dry_run_skips_network_but_still_attempts_bookkeeping_and_creates_dirs(
    tmp_path: Path, monkeypatch
) -> None:
    """DRY_RUN conflates fetch/enqueue while filesystem and DB-start remain active."""
    data_dir = tmp_path / "data"
    starts: list[tuple] = []

    monkeypatch.setenv("DIGEST_AT", "20250101T00")
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.setattr(stage01, "DATA_DIR", data_dir)
    monkeypatch.setattr(stage01, "SLICE_DIR", data_dir / "rss_slices")
    monkeypatch.setattr(stage01, "RSS_DUMPS_DIR", data_dir / "rss_slices" / "rss_dumps")
    monkeypatch.setattr(stage01, "JSONL_DIR", data_dir / "slices" / "jsonl")
    monkeypatch.setattr(stage01, "QUAR_DIR", data_dir / "quarantine")
    monkeypatch.setattr(stage01.db, "start_run", lambda *args: starts.append(args))
    monkeypatch.setattr(
        stage01,
        "fetch_rss_now",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("network fetched")),
    )
    assert stage01.run() == 0
    assert starts == []
    assert (data_dir / "rss_slices" / "rss_dumps").is_dir()
    assert not list(data_dir.rglob("*.csv"))


def test_failed_stage_wrapper_leaves_partial_telemetry_and_failed_latest(tmp_path: Path) -> None:
    """A child failure is diagnosable but mutates shared latest/summary state."""
    telemetry = tmp_path / "observability"
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_with_run_record.py"),
        "--project-id",
        "media_monitor",
        "--lane",
        "sensing",
        "--stage",
        "s02",
        "--telemetry-root",
        str(telemetry),
        "--",
        sys.executable,
        "-c",
        "import sys; print('partial output'); sys.exit(7)",
    ]

    result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)

    assert result.returncode == 7
    records = [json.loads(line) for line in (telemetry / "run_records.jsonl").read_text().splitlines()]
    assert records[0]["status"] == "failed"
    assert records[0]["error_code"] == "exit_7"
    assert Path(records[0]["manifest_path"]).exists()
    assert "partial output" in Path(records[0]["log_path"]).read_text()
    latest = json.loads((telemetry / "status" / "sensing_latest.json").read_text())
    assert latest["last_status"] == "failed"
    assert (telemetry / "status" / "summary.json").exists()


def test_outer_orchestrator_is_the_sensing_lane_status_owner_after_a1() -> None:
    """The wrapper emits records only when invoked by the sensing orchestrator."""
    shell = (REPO_ROOT / "bin" / "run_minimal_loop_once.sh").read_text()
    wrapper = (REPO_ROOT / "scripts" / "run_with_run_record.py").read_text()

    assert 'status_file="storage/observability/status/${LANE}_latest.json"' in shell
    assert "trap on_exit EXIT" in shell
    assert "--no-lane-status" in shell
    assert "--no-run-record" in shell
    assert '"stage": "lane"' in shell
    assert 'status_path = status_dir / f"{args.lane}_latest.json"' in wrapper
    assert "if args.no_lane_status:" in wrapper
