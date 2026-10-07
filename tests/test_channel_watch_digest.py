from __future__ import annotations

import json
from pathlib import Path

from apps.media_watch.digest import annotate, build_digest_input, render_digest, validate_watch_config
from apps.media_watch.enrichment import MediaEnrichmentStore
from apps.media_watch.enrichment_fixture import seed_enriched
from apps.media_watch.store import MediaWatchStore


def config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config/media_watch/watches/matias-knowledge-channels.yaml"


def test_watch_config_resolves_shared_sources() -> None:
    config = validate_watch_config(config_path())
    assert config["watch"]["monitor_id"] == "matias-knowledge-channels"
    assert {row["source_id"] for row in config["sources"]} == {"el-destape-youtube", "futurock-youtube"}


def test_digest_projection_and_annotations_are_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed_enriched(root)
    config = validate_watch_config(config_path())
    rows = build_digest_input(config, MediaWatchStore(root), limit_per_channel=5)
    assert [row["item_uid"] for row in rows] == ["youtube:fixtureA01", "youtube:fixtureB01", "youtube:fixtureA02", "youtube:fixtureB02"]
    assert rows[0]["text_status"] == "publisher_article_text"
    assert rows[1]["text_status"] == "authorized_asr"
    assert rows[2]["text_status"] == "unavailable"


def test_digest_references_only_real_items_and_replays_with_new_digest_id(tmp_path: Path) -> None:
    from apps.media_watch.digest import annotate

    root = tmp_path / "store"
    seed_enriched(root)
    config = validate_watch_config(config_path())
    rows = build_digest_input(config, MediaWatchStore(root), limit_per_channel=5)
    annotations = [annotate(row) for row in rows]
    first = render_digest(config, rows, annotations, output_root=tmp_path / "digests", digest_id="20260913T000000Z", since=None)
    second = render_digest(config, rows, annotations, output_root=tmp_path / "digests", digest_id="20260913T010000Z", since=None)
    assert first["input_sha256"] == second["input_sha256"]
    assert json.loads((tmp_path / "digests/index.json").read_text())
    assert all(annotation["item_uid"] in {row["item_uid"] for row in rows} for annotation in annotations)



def test_digest_projects_governed_summary_without_changing_decision_semantics(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed_enriched(root)
    store = MediaWatchStore(root)
    enrichment = MediaEnrichmentStore(store)
    artifact = enrichment.put_summary(
        item_uid="youtube:fixtureA01",
        summary="Resumen gobernado sobre inflación, actividad y política económica.",
        key_points=["Inflación desacelera", "Actividad sigue débil", "Política fiscal en debate"],
        provider="google-gemini",
        model="gemini-test",
        prompt_version="youtube-summary.v1",
        adapter_version="gemini-youtube-url.v1",
        processing_mode="static",
        generated_at="2026-09-13T00:00:00Z",
    )

    config = validate_watch_config(config_path())
    rows = build_digest_input(config, store, limit_per_channel=5)
    row = next(item for item in rows if item["item_uid"] == "youtube:fixtureA01")
    assert row["summary_state"] == "available"
    assert row["summary_id"] == artifact["summary_id"]
    assert row["summary"].startswith("Resumen gobernado")
    assert row["summary_key_points"][0] == "Inflación desacelera"

    annotations = [annotate(item) for item in rows]
    target = next(item for item in annotations if item["item_uid"] == "youtube:fixtureA01")
    assert any(
        evidence["kind"] == "summary" and evidence["ref"] == artifact["summary_id"]
        for evidence in target["evidence"]
    )

    render_digest(
        config,
        rows,
        annotations,
        output_root=tmp_path / "digests",
        digest_id="20260913T020000Z",
        since=None,
    )
    rendered = (tmp_path / "digests" / "20260913T020000Z" / "digest.md").read_text(encoding="utf-8")
    assert "Governed summary: Resumen gobernado" in rendered
    assert "Inflación desacelera" in rendered

def test_incremental_since_watermark_excludes_old_items(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed_enriched(root)
    config = validate_watch_config(config_path())
    rows = build_digest_input(config, MediaWatchStore(root), limit_per_channel=5, since="2026-08-30T18:45:00Z")
    assert {row["item_uid"] for row in rows} == {"youtube:fixtureA01"}


def test_receipt_boundary_uses_central_runner_and_current_manifest() -> None:
    wrapper = (Path(__file__).resolve().parents[1] / "bin/channel-watch-digest-receipt").read_text(encoding="utf-8")
    assert 'PROJECTS_ROOT:?PROJECTS_ROOT is required' in wrapper
    assert 'producer_local_receipt.py' in wrapper
    assert 'producer.manual.media-channel-watch-digest' in wrapper
    assert '--evidence-changed' in wrapper
    assert 'DIGEST_ID' in wrapper
