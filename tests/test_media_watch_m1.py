from __future__ import annotations

import json
from pathlib import Path

from apps.media_watch.api import MediaWatchReadModel
from apps.media_watch.store import MediaObservation, MediaWatchStore
from apps.media_watch.youtube_api import parse_iso8601_duration


def obs(*, title: str = "Economía hoy", views: int = 100, observed_at: str = "2026-08-30T20:00:00Z") -> MediaObservation:
    return MediaObservation(source_id="outlet-youtube", video_id="abcDEF_1234", title=title, description="Descripción publicada", published_at="2026-08-30T18:00:00Z", duration_seconds=3661, view_count=views, like_count=10, comment_count=2, availability="public", observed_at=observed_at)


def seed_source(store: MediaWatchStore) -> None:
    store.update_source_state(source_id="outlet-youtube", display_name="Outlet", channel_id="UCabcdef123456", channel_title="Outlet", uploads_playlist_id="UUabcdef123456", observed_at="2026-08-30T20:00:00Z", latest_published_at="2026-08-30T18:00:00Z", health="healthy", error=None, item_count=1, api_calls=3, quota_units_estimated=3)


def test_duration_parser() -> None:
    assert parse_iso8601_duration("PT1H1M1S") == 3661
    assert parse_iso8601_duration("PT8M") == 480
    assert parse_iso8601_duration("PT42S") == 42
    assert parse_iso8601_duration(None) is None


def test_replay_is_idempotent_and_metadata_mutation_keeps_item_identity(tmp_path: Path) -> None:
    store = MediaWatchStore(tmp_path / "store")
    first, failures, _ = store.materialize([obs()])
    assert not failures and first.new_items == 1 and first.new_snapshots == 1
    first_item = store.list_items()[0]
    assert first_item["item_uid"] == "youtube:abcDEF_1234"
    replay, failures, _ = store.materialize([obs()])
    assert not failures and replay.new_items == 0 and replay.new_snapshots == 0 and replay.unchanged_snapshots == 1
    assert len(store.list_items()) == 1 and len(store.list_snapshots()) == 1
    changed = obs(title="Economía hoy — título corregido", views=155, observed_at="2026-08-30T21:00:00Z")
    mutation, failures, _ = store.materialize([changed])
    assert not failures and mutation.new_items == 0 and mutation.new_snapshots == 1 and mutation.metadata_mutations == 1
    assert len(store.list_items()) == 1 and len(store.list_snapshots()) == 2
    current = store.list_items()[0]
    assert current["item_uid"] == first_item["item_uid"] and current["first_seen"] == first_item["first_seen"] and current["last_seen"] == "2026-08-30T21:00:00Z"


def test_read_model_exposes_health_separately_from_latest_publication(tmp_path: Path) -> None:
    store = MediaWatchStore(tmp_path / "store"); seed_source(store); store.materialize([obs()]); model = MediaWatchReadModel(store); overview = model.overview()
    assert overview["source_count"] == 1 and overview["item_count"] == 1 and overview["sources"][0]["health"] == "healthy"
    assert overview["sources"][0]["latest_published_at"] == "2026-08-30T18:00:00Z" and overview["text_enrichment"] == "not_attempted_m1"
    detail = model.item("abcDEF_1234"); assert detail is not None and detail["snapshot_count"] == 1 and detail["text_enrichment"]["status"] == "not_attempted_m1"


def test_w0_config_instances_validate() -> None:
    import yaml
    from jsonschema import Draft202012Validator, FormatChecker
    repo = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((repo / "config/media_watch/sources.yaml").read_text(encoding="utf-8"))
    for schema_name, payloads in [("media_watch_spec.v1.json", [config["watch"]]), ("media_source.v1.json", config["sources"])]:
        schema = json.loads((repo / "contracts/schemas" / schema_name).read_text(encoding="utf-8")); validator = Draft202012Validator(schema, format_checker=FormatChecker()); assert all(not list(validator.iter_errors(payload)) for payload in payloads)
