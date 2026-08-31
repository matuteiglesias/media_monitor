from __future__ import annotations

from pathlib import Path

from apps.media_watch.api import MediaWatchReadModel
from apps.media_watch.enrichment import MediaEnrichmentStore, parse_description_timestamps
from apps.media_watch.enrichment_fixture import seed_enriched
from apps.media_watch.store import MediaWatchStore


def test_timestamp_segments_are_deterministic() -> None:
    rows = parse_description_timestamps("00:00 Inicio\n05:10 Entrevista\n12:00 Cierre", duration_seconds=900)
    assert rows == [(0.0, 310.0, "Inicio"), (310.0, 720.0, "Entrevista"), (720.0, 900.0, "Cierre")]


def test_m2_text_states_and_segments_remain_explicit(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed_enriched(root)
    store = MediaWatchStore(root)
    enrichment = MediaEnrichmentStore(store)

    statuses = {row["status"] for row in enrichment.list_text_assets()}
    assert {"publisher_article_text", "authorized_asr", "unavailable", "blocked_by_policy"} <= statuses
    available = [row for row in enrichment.list_text_assets() if row["text"]]
    assert all(row["text_sha256"] for row in available)
    assert all(row["text"] is None and row["text_sha256"] is None for row in enrichment.list_text_assets() if row["status"] in {"unavailable", "blocked_by_policy"})

    item_a = store.load_item("youtube:fixtureA01")
    assert item_a is not None
    segments = enrichment.list_segments(item_a["item_uid"])
    assert any(row["boundary_source"] == "whole_item" for row in segments)
    assert any(row["boundary_source"] == "description_timestamp" and row["label"] == "Entrevista económica" for row in segments)

    counts_before = (len(enrichment.list_text_assets()), len(enrichment.list_segments()), len(enrichment.list_appearances()))
    seed_enriched(root)
    counts_after = (len(enrichment.list_text_assets()), len(enrichment.list_segments()), len(enrichment.list_appearances()))
    assert counts_after == counts_before


def test_m3_people_appearances_and_indexes_are_evidence_bearing(tmp_path: Path) -> None:
    root = tmp_path / "store"
    result = seed_enriched(root)
    store = MediaWatchStore(root)
    enrichment = MediaEnrichmentStore(store)

    appearances = enrichment.list_appearances()
    assert {row["person_id"] for row in appearances} == {"carlos-melconian", "marina-dal-poggetto"}
    assert all(row["evidence_source"] in {"title", "description", "transcript"} for row in appearances)
    assert all(row["matched_alias"] for row in appearances)
    assert result["appearance_count"] == len(appearances)
    for name in result["index_names"]:
        assert (root / "indexes" / name).exists()


def test_m4_read_model_search_and_item_truthfulness(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed_enriched(root)
    model = MediaWatchReadModel(MediaWatchStore(root))

    overview = model.overview()
    assert overview["text_enrichment"] == "governed_m2"
    assert overview["person_count"] == 2
    assert overview["appearance_count"] >= 2

    people = model.people()["people"]
    assert {row["person_id"] for row in people} == {"carlos-melconian", "marina-dal-poggetto"}
    assert all(row["appearance_count"] >= 1 for row in people)

    title_hits = model.search("Melconian")["hits"]
    assert title_hits and title_hits[0]["evidence"][0]["source"] == "title"
    text_hits = model.search("inflación")["hits"]
    assert any(any(ev["source"] == "text_asset" for ev in hit["evidence"]) for hit in text_hits)

    detail = model.item("fixtureA02")
    assert detail is not None
    assert detail["text_enrichment"]["status"] == "unavailable"
    assert detail["text_enrichment"]["available"] is False
    assert detail["segments"]
