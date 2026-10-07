from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.media_watch.evidence_export import CONTRACT, export_evidence
from apps.media_watch.evidence_fixture import seed_evidence_fixture
from apps.media_watch.store import MediaWatchStore


def test_media_monitor_owns_generic_evidence_projection(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed_evidence_fixture(root)
    store = MediaWatchStore(root)
    output = tmp_path / "media.evidence.jsonl"

    receipt = export_evidence(root, output)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

    assert receipt["contract"] == CONTRACT
    assert receipt["records"] == 2
    assert receipt["output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert len(rows) == 2
    assert {row["source_ref"] for row in rows} == set(receipt["source_refs"])
    assert all(row["source_ref"].startswith("media-summary:") for row in rows)
    assert all(row["timestamp"].endswith("Z") for row in rows)
    assert all(row["meta"]["producer"] == "media-monitor" for row in rows)
    assert all(row["meta"]["artifact_family"] == "media_summary" for row in rows)
    assert all(len(row["meta"]["key_points"]) >= 2 for row in rows)
    assert all(row["meta"]["canonical_url"].startswith("https://www.youtube.com/watch?v=") for row in rows)
    assert {row["meta"]["source_id"] for row in rows} == {
        store.load_item("youtube:fixtureA01")["source_id"],
        store.load_item("youtube:fixtureB01")["source_id"],
    }
    assert all("Key points:" in row["text"] for row in rows)
    assert str(root) not in output.read_text(encoding="utf-8")


def test_export_is_byte_deterministic_for_same_store(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed_evidence_fixture(root)
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"

    receipt_a = export_evidence(root, first)
    receipt_b = export_evidence(root, second)

    assert first.read_bytes() == second.read_bytes()
    assert receipt_a == receipt_b
