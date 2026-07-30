from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from apps.news_acquire.src.news_acquire.compactor import plan_compaction, publish_compaction
from apps.news_acquire.src.news_acquire.run_bundle import StageResult, finalize_bundle
from scripts.promote_sensing_bundle_local import promote_current_compaction


def make_bundle(
    root: Path,
    *,
    digest: str,
    run_id: str,
    master_rows: list[dict[str, str]],
    ref_id: str,
    status_error: bool = False,
    malformed_refs: bool = False,
) -> Path:
    work = root / "fixtures" / run_id
    data = work / "data"
    indexes = work / "storage" / "indexes"
    data.mkdir(parents=True)
    indexes.mkdir(parents=True)
    with (data / "master_ref.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"]
        )
        writer.writeheader()
        writer.writerows(master_rows)
    refs = "{broken\n" if malformed_refs else json.dumps({"index_id": ref_id}) + "\n"
    (indexes / "news_recent_refs_latest.jsonl").write_text(refs, encoding="utf-8")
    (indexes / "news_recent_groups_latest.jsonl").write_text(
        json.dumps({"digest_at": digest, "topic": ref_id}) + "\n", encoding="utf-8"
    )
    feed = work / "feed.yaml"
    feed.write_text("schema_version: sensing_feeds.v1\nfeeds: []\n", encoding="utf-8")
    stage = StageResult(
        stage="fixture",
        command=["fixture"],
        returncode=1 if status_error else 0,
        started_at="2026-07-29T00:00:00Z",
        ended_at="2026-07-29T00:00:01Z",
        stdout="",
        stderr="failure" if status_error else "",
    )
    return finalize_bundle(
        run_root=root,
        run_id=run_id,
        digest_at=digest,
        attempt=1,
        work_root=work,
        feed_config=feed,
        stage_results=[stage],
        started_at="2026-07-29T00:00:00Z",
        source_commit="fixture",
    )


def row(index_id: str, first: str, last: str, source: str = "source") -> dict[str, str]:
    return {
        "index_id": index_id,
        "source": source,
        "link": f"https://example.test/{index_id}",
        "first_seen": first,
        "last_seen": last,
        "topics": "[]",
        "meta": "{}",
    }


def read_master(generation: Path) -> list[dict[str, str]]:
    with (generation / "master_ref.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_out_of_order_inputs_produce_cumulative_master_and_newest_latest(tmp_path: Path) -> None:
    older = make_bundle(
        tmp_path,
        digest="20260729T00",
        run_id="sensing:20260729T00:attempt:1:older",
        master_rows=[row("shared", "2026-07-29T00:00:00Z", "2026-07-29T00:10:00Z"), row("old", "1", "1")],
        ref_id="older",
    )
    newer = make_bundle(
        tmp_path,
        digest="20260729T01",
        run_id="sensing:20260729T01:attempt:1:newer",
        master_rows=[row("shared", "2026-07-29T00:00:00Z", "2026-07-29T01:10:00Z", "new"), row("new", "2", "2")],
        ref_id="newer",
    )

    generation = publish_compaction(tmp_path, tmp_path / "state", paths=[newer, older])

    assert [item["index_id"] for item in read_master(generation)] == ["new", "old", "shared"]
    assert next(item for item in read_master(generation) if item["index_id"] == "shared")["source"] == "new"
    assert json.loads((generation / "news_recent_refs.jsonl").read_text())["index_id"] == "newer"
    pointer = json.loads((tmp_path / "state" / "current.json").read_text())
    assert pointer["latest_run_id"] == newer.name


def test_duplicate_invocation_and_duplicate_input_are_idempotent(tmp_path: Path) -> None:
    bundle = make_bundle(
        tmp_path,
        digest="20260729T00",
        run_id="sensing:20260729T00:attempt:1:one",
        master_rows=[row("one", "1", "1")],
        ref_id="one",
    )

    first = publish_compaction(tmp_path, tmp_path / "state", paths=[bundle, bundle])
    pointer_before = (tmp_path / "state" / "current.json").read_bytes()
    second = publish_compaction(tmp_path, tmp_path / "state", paths=[bundle])

    assert first == second
    accepted = json.loads((first / "accepted_runs.json").read_text())
    assert [item["run_id"] for item in accepted] == [bundle.name]
    assert len(list((tmp_path / "state" / "generations").iterdir())) == 1
    assert (tmp_path / "state" / "current.json").read_bytes() == pointer_before


def test_replay_attempt_chooses_one_deterministic_winner_per_digest(tmp_path: Path) -> None:
    alpha = make_bundle(
        tmp_path,
        digest="20260729T00",
        run_id="sensing:20260729T00:attempt:1:alpha",
        master_rows=[row("alpha", "1", "1")],
        ref_id="alpha",
    )
    beta = make_bundle(
        tmp_path,
        digest="20260729T00",
        run_id="sensing:20260729T00:attempt:2:beta",
        master_rows=[row("beta", "1", "1")],
        ref_id="beta",
    )

    plan = plan_compaction([beta, alpha])
    generation = publish_compaction(tmp_path, tmp_path / "state", paths=[alpha, beta])

    assert [bundle.run_id for bundle in plan.accepted] == [beta.name]
    assert [item["index_id"] for item in read_master(generation)] == ["beta"]


def test_error_and_checksum_invalid_bundles_are_rejected_without_regression(tmp_path: Path) -> None:
    valid = make_bundle(
        tmp_path,
        digest="20260729T00",
        run_id="sensing:20260729T00:attempt:1:valid",
        master_rows=[row("valid", "1", "1")],
        ref_id="valid",
    )
    error = make_bundle(
        tmp_path,
        digest="20260729T02",
        run_id="sensing:20260729T02:attempt:1:error",
        master_rows=[row("error", "2", "2")],
        ref_id="error",
        status_error=True,
    )
    corrupt = make_bundle(
        tmp_path,
        digest="20260729T03",
        run_id="sensing:20260729T03:attempt:1:corrupt",
        master_rows=[row("corrupt", "3", "3")],
        ref_id="corrupt",
    )
    (corrupt / "candidates" / "master_ref.csv").write_text("tampered\n", encoding="utf-8")

    plan = plan_compaction([corrupt, error, valid])
    generation = publish_compaction(tmp_path, tmp_path / "state", paths=[corrupt, error, valid])

    assert [bundle.run_id for bundle in plan.accepted] == [valid.name]
    assert len(plan.rejected) == 2
    assert json.loads((tmp_path / "state" / "current.json").read_text())["latest_run_id"] == valid.name
    assert [item["index_id"] for item in read_master(generation)] == ["valid"]


def test_failed_generation_build_does_not_replace_current_pointer(tmp_path: Path) -> None:
    valid = make_bundle(
        tmp_path,
        digest="20260729T00",
        run_id="sensing:20260729T00:attempt:1:valid",
        master_rows=[row("valid", "1", "1")],
        ref_id="valid",
    )
    publish_compaction(tmp_path, tmp_path / "state", paths=[valid])
    before = (tmp_path / "state" / "current.json").read_text()
    malformed = make_bundle(
        tmp_path,
        digest="20260729T01",
        run_id="sensing:20260729T01:attempt:1:malformed",
        master_rows=[row("bad", "2", "2")],
        ref_id="bad",
        malformed_refs=True,
    )

    with pytest.raises(json.JSONDecodeError):
        publish_compaction(tmp_path, tmp_path / "state", paths=[valid, malformed])

    assert (tmp_path / "state" / "current.json").read_text() == before


def test_legacy_mirror_can_only_copy_compactor_selected_generation(tmp_path: Path) -> None:
    bundle = make_bundle(
        tmp_path,
        digest="20260729T00",
        run_id="sensing:20260729T00:attempt:1:selected",
        master_rows=[row("selected", "1", "1")],
        ref_id="selected",
    )
    state = tmp_path / "state"
    legacy = tmp_path / "legacy"

    with pytest.raises(ValueError, match="current pointer is missing"):
        promote_current_compaction(bundle, legacy)
    publish_compaction(tmp_path, state, paths=[bundle])
    promote_current_compaction(state, legacy)

    assert [item["index_id"] for item in read_master(legacy / "data")] == ["selected"]
    assert json.loads(
        (legacy / "storage" / "indexes" / "news_recent_refs_latest.jsonl").read_text()
    )["index_id"] == "selected"
