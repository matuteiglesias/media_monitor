from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.media_watch.evidence_export import CONTRACT, export_evidence
from apps.media_watch.enrichment import MediaEnrichmentStore
from apps.media_watch.enrichment_fixture import seed_enriched
from apps.media_watch.store import MediaWatchStore


def _seed_summaries(root: Path) -> MediaWatchStore:
    seed_enriched(root)
    store = MediaWatchStore(root)
    enrichment = MediaEnrichmentStore(store)
    enrichment.put_summary(
        item_uid="youtube:fixtureA01",
        summary="El canal describe una desaceleración de la inflación y debate sobre actividad.",
        key_points=["Inflación desacelera", "Actividad débil"],
        provider="google-gemini",
        model="gemini-test",
        prompt_version="youtube-summary.v1",
        adapter_version="gemini-youtube-url.v1",
        processing_mode="static",
        generated_at="2026-09-13T00:00:00Z",
    )
    enrichment.put_summary(
        item_uid="youtube:fixtureB01",
        summary="El segundo canal también discute inflación, salarios y consumo.",
        key_points=["Salarios rezagados", "Consumo en debate"],
        provider="google-gemini",
        model="gemini-test",
        prompt_version="youtube-summary.v1",
        adapter_version="gemini-youtube-url.v1",
        processing_mode="static",
        generated_at="2026-09-13T00:05:00Z",
    )
    return store


def test_media_monitor_owns_generic_evidence_projection(tmp_path: Path) -> None:
    root = tmp_path / "store"
    store = _seed_summaries(root)
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
    assert all(row["meta"]["canonical_url"].startswith("https://www.youtube.com/watch?v=") for row in rows)
    assert {row["meta"]["source_id"] for row in rows} == {
        store.load_item("youtube:fixtureA01")["source_id"],
        store.load_item("youtube:fixtureB01")["source_id"],
    }
    assert all("Key points:" in row["text"] for row in rows)
    assert str(root) not in output.read_text(encoding="utf-8")


def test_export_is_byte_deterministic_for_same_store(tmp_path: Path) -> None:
    root = tmp_path / "store"
    _seed_summaries(root)
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"

    receipt_a = export_evidence(root, first)
    receipt_b = export_evidence(root, second)

    assert first.read_bytes() == second.read_bytes()
    assert receipt_a == receipt_b
