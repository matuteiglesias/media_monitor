from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.news_acquire.src.news_acquire.run_bundle import StageResult, finalize_bundle, sha256_file


def result(stage: str, returncode: int = 0, stderr: str = "") -> StageResult:
    return StageResult(
        stage=stage,
        command=["fixture", stage],
        returncode=returncode,
        started_at="2026-07-29T00:00:00Z",
        ended_at="2026-07-29T00:00:01Z",
        stdout=f"{stage} output\n",
        stderr=stderr,
    )


def fixture_workspace(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    work = tmp_path / "work"
    feed = tmp_path / "sensing_feeds.v1.yaml"
    feed.write_text("schema_version: sensing_feeds.v1\nfeeds: []\n", encoding="utf-8")
    (work / "data" / "digest_map").mkdir(parents=True)
    (work / "data" / "digest_map" / "20260729T00.csv").write_text("article_id\n1\n")
    (work / "data" / "master_ref.csv").write_text("index_id\nabc\n")
    indexes = work / "storage" / "indexes"
    indexes.mkdir(parents=True)
    (indexes / "news_recent_refs_latest.jsonl").write_text('{"index_id":"abc"}\n')
    (indexes / "news_recent_groups_latest.jsonl").write_text('{"topic":"test"}\n')
    return work, feed


def finalize(tmp_path: Path, run_id: str, stage_results: list[StageResult]) -> Path:
    work, feed = fixture_workspace(tmp_path)
    return finalize_bundle(
        run_root=tmp_path / "run-root",
        run_id=run_id,
        digest_at="20260729T00",
        attempt=1,
        work_root=work,
        feed_config=feed,
        stage_results=stage_results,
        started_at="2026-07-29T00:00:00Z",
        source_commit="abc123",
    )


def test_success_bundle_has_candidates_manifest_and_valid_checksums(tmp_path: Path) -> None:
    bundle = finalize(tmp_path, "sensing:20260729T00:attempt:1:one", [result("s01"), result("s02")])

    manifest = json.loads((bundle / "manifest.json").read_text())
    checksums = json.loads((bundle / "evidence" / "checksums.json").read_text())
    assert manifest["status"] == "success"
    assert manifest["logical_run_id"] == "sensing:20260729T00"
    assert manifest["counts"] == {"news_digest_group": 1, "news_ref": 1}
    assert (bundle / "FINALIZED").read_text() == "success\n"
    assert (bundle / "candidates" / "news_recent_refs.jsonl").exists()
    assert not list(bundle.rglob("*latest*"))
    for relative, expected in checksums.items():
        assert sha256_file(bundle / relative) == expected


def test_failed_run_still_finalizes_diagnostic_bundle(tmp_path: Path) -> None:
    bundle = finalize(
        tmp_path,
        "sensing:20260729T00:attempt:1:failed",
        [result("s01"), result("s02", 7, "fixture failure")],
    )

    manifest = json.loads((bundle / "manifest.json").read_text())
    exception = json.loads((bundle / "evidence" / "exception.json").read_text())
    assert manifest["status"] == "error"
    assert manifest["failure_code"] == "s02_exit_7"
    assert exception == {"stage": "s02", "returncode": 7, "stderr": "fixture failure"}
    assert (bundle / "evidence" / "logs" / "s02.stderr.log").read_text() == "fixture failure"


def test_same_digest_attempts_never_overwrite_each_other(tmp_path: Path) -> None:
    # Use one run root with separately fabricated workspaces for the actual replay assertion.
    shared = tmp_path / "shared"
    work1, feed1 = fixture_workspace(tmp_path / "fixture1")
    work2, feed2 = fixture_workspace(tmp_path / "fixture2")
    kwargs = dict(
        run_root=shared,
        digest_at="20260729T00",
        attempt=1,
        stage_results=[result("s01")],
        started_at="2026-07-29T00:00:00Z",
        source_commit="abc123",
    )
    one = finalize_bundle(run_id="sensing:20260729T00:attempt:1:one", work_root=work1, feed_config=feed1, **kwargs)
    two = finalize_bundle(run_id="sensing:20260729T00:attempt:1:two", work_root=work2, feed_config=feed2, **kwargs)

    assert one != two
    assert one.exists() and two.exists()
    with pytest.raises(FileExistsError, match="immutable run bundle already exists"):
        finalize_bundle(run_id=one.name, work_root=work2, feed_config=feed2, **kwargs)
