from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.media_watch.api import MediaWatchReadModel
from apps.media_watch.enrichment import MediaEnrichmentStore
from apps.media_watch.fixture import seed
from apps.media_watch.sidecar import build_sidecar, ensure_video_sidecar, parse_youtube_video_id
from apps.media_watch.store import MediaWatchStore
from apps.media_watch.summary import (
    ADAPTER_VERSION,
    PROCESSING_MODE,
    PROMPT_VERSION,
    GeminiSummaryProvider,
    ensure_summary,
)
from apps.media_watch.youtube_api import VideoDetail


class FakeInteractions:
    def __init__(self, *, output: dict | None = None, error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return type("Interaction", (), {"output_text": json.dumps(self.output)})()


class FakeClient:
    def __init__(self, interactions: FakeInteractions) -> None:
        self.interactions = interactions


class FakeYouTubeClient:
    api_calls = 1
    quota_units_estimated = 1

    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_video(self, video_id: str) -> VideoDetail:
        self.calls.append(video_id)
        return VideoDetail(
            video_id=video_id,
            channel_id="UCsidecar123456",
            channel_title="Sidecar Test Channel",
            title="A real-shaped sidecar test video",
            description="Description with enough provenance to materialize metadata.",
            published_at="2026-10-04T20:00:00Z",
            duration_seconds=321,
            view_count=1200,
            like_count=88,
            comment_count=9,
            availability="public",
        )


def provider(
    interactions: FakeInteractions,
    *,
    adapter_version: str = ADAPTER_VERSION,
    processing_mode: str = PROCESSING_MODE,
) -> GeminiSummaryProvider:
    return GeminiSummaryProvider(
        api_key="test-key",
        model="gemini-test",
        adapter_version=adapter_version,
        processing_mode=processing_mode,
        client=FakeClient(interactions),
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("youtube:aZqxNLuf89c", "aZqxNLuf89c"),
        ("aZqxNLuf89c", "aZqxNLuf89c"),
        ("https://www.youtube.com/watch?v=aZqxNLuf89c&t=10", "aZqxNLuf89c"),
        ("https://youtu.be/aZqxNLuf89c", "aZqxNLuf89c"),
        ("https://www.youtube.com/shorts/aZqxNLuf89c", "aZqxNLuf89c"),
        ("youtube.com/watch?v=aZqxNLuf89c", "aZqxNLuf89c"),
    ],
)
def test_parse_youtube_video_id(value: str, expected: str) -> None:
    assert parse_youtube_video_id(value) == expected


def test_arbitrary_url_can_be_ensured_without_watch_enrollment(tmp_path: Path) -> None:
    store = MediaWatchStore(tmp_path / "store")
    youtube = FakeYouTubeClient()

    first = ensure_video_sidecar(
        store,
        "https://youtu.be/sidecar12345",
        metadata_client=youtube,
        observed_at="2026-10-04T21:00:00Z",
    )
    second = ensure_video_sidecar(
        store,
        "youtube:sidecar12345",
        metadata_client=None,
        observed_at="2026-10-04T21:10:00Z",
    )

    assert youtube.calls == ["sidecar12345"]
    assert first == second
    assert first["item_uid"] == "youtube:sidecar12345"
    assert first["channel"]["source_uid"] == "youtube-channel:UCsidecar123456"
    assert first["channel"]["source_id"].startswith("youtube-channel-")
    assert first["metadata"]["statistics"]["view_count"] == 1200
    assert first["summary"]["state"] == "not_attempted"
    assert store.load_item("youtube:sidecar12345") is not None


def test_sidecar_inspection_is_a_pure_projection(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed(root)
    store = MediaWatchStore(root)
    before = store.load_item("youtube:fixtureA01")
    assert before is not None

    first = build_sidecar(store, "fixtureA01")
    second = build_sidecar(store, "https://www.youtube.com/watch?v=fixtureA01")

    assert first == second
    assert first["channel"]["source_uid"] == "youtube-channel:UC5wAqJ9NF0fpGH9dVf3h6HA"
    assert store.load_item("youtube:fixtureA01") == before


def test_summary_is_structured_persistent_provenanced_and_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed(root)
    store = MediaWatchStore(root)
    before = store.load_item("youtube:fixtureA01")
    assert before is not None

    interactions = FakeInteractions(
        output={
            "summary": "Resumen sustantivo de la entrevista económica, con sus argumentos principales.",
            "key_points": ["Punto cuantitativo", "Argumento central", "Conclusión"],
        }
    )
    gemini = provider(interactions)

    first, first_state = ensure_summary(
        store,
        item_uid=before["item_uid"],
        provider=gemini,
        generated_at="2026-10-04T19:00:00Z",
    )
    second, second_state = ensure_summary(
        store,
        item_uid=before["item_uid"],
        provider=gemini,
        generated_at="2026-10-04T19:10:00Z",
    )

    assert first_state == "generated"
    assert second_state == "existing"
    assert first == second
    assert len(interactions.calls) == 1

    call = interactions.calls[0]
    assert call["model"] == "gemini-test"
    assert call["store"] is False
    assert call["input"][1] == {"type": "video", "uri": before["canonical_url"]}
    assert call["response_format"]["mime_type"] == "application/json"
    assert call["response_format"]["schema"]["required"] == ["summary", "key_points"]

    assert first["schema_name"] == "media_summary.v1"
    assert first["item_uid"] == before["item_uid"]
    assert first["provider"] == "google-gemini"
    assert first["model"] == "gemini-test"
    assert first["prompt_version"] == PROMPT_VERSION
    assert first["adapter_version"] == ADAPTER_VERSION
    assert first["processing_mode"] == PROCESSING_MODE
    assert first["generated_at"] == "2026-10-04T19:00:00Z"

    enrichment = MediaEnrichmentStore(store)
    assert len(enrichment.list_summaries(before["item_uid"])) == 1
    attempts = enrichment.list_summary_attempts(before["item_uid"])
    assert len(attempts) == 1
    assert attempts[0]["state"] == "generated"

    detail = MediaWatchReadModel(store).item("fixtureA01")
    assert detail is not None
    assert detail["summary"]["summary_id"] == first["summary_id"]
    assert detail["summaries"] == [first]
    assert store.load_item(before["item_uid"]) == before


def test_derivation_identity_includes_adapter_and_processing_mode(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed(root)
    enrichment = MediaEnrichmentStore(MediaWatchStore(root))
    common = {
        "item_uid": "youtube:fixtureA01",
        "provider": "google-gemini",
        "model": "gemini-test",
        "prompt_version": PROMPT_VERSION,
    }
    a = enrichment.summary_id(
        **common,
        adapter_version="gemini-youtube-url.v1",
        processing_mode="static",
    )
    b = enrichment.summary_id(
        **common,
        adapter_version="gemini-youtube-url.v2",
        processing_mode="static",
    )
    c = enrichment.summary_id(
        **common,
        adapter_version="gemini-youtube-url.v1",
        processing_mode="agentic",
    )
    assert len({a, b, c}) == 3


def test_invalid_structured_output_records_failed_attempt_without_summary(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed(root)
    store = MediaWatchStore(root)
    before = store.load_item("youtube:fixtureA01")
    assert before is not None

    interactions = FakeInteractions(output={"summary": "Too little structure", "key_points": []})
    with pytest.raises(ValueError, match="validation failed"):
        ensure_summary(
            store,
            item_uid=before["item_uid"],
            provider=provider(interactions),
            generated_at="2026-10-04T19:00:00Z",
        )

    enrichment = MediaEnrichmentStore(store)
    assert enrichment.list_summaries(before["item_uid"]) == []
    attempts = enrichment.list_summary_attempts(before["item_uid"])
    assert len(attempts) == 1
    assert attempts[0]["state"] == "failed"
    assert attempts[0]["retryable"] is True
    assert store.load_item(before["item_uid"]) == before


def test_provider_limit_is_explicit_sidecar_state_and_not_immediately_retryable(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed(root)
    store = MediaWatchStore(root)
    before = store.load_item("youtube:fixtureA01")
    assert before is not None

    limited = FakeInteractions(
        error=RuntimeError(
            "invalid_request: input exceeds the maximum number of tokens allowed 1048576"
        )
    )
    with pytest.raises(RuntimeError, match="1048576"):
        ensure_summary(
            store,
            item_uid=before["item_uid"],
            provider=provider(limited),
            generated_at="2026-10-04T19:00:00Z",
        )

    sidecar = build_sidecar(store, before["item_uid"])
    assert sidecar["summary"]["state"] == "provider_limit"
    assert sidecar["summary"]["retryable"] is False
    assert sidecar["summary"]["summary_id"] is None
    assert MediaEnrichmentStore(store).list_summaries(before["item_uid"]) == []
    assert store.load_item(before["item_uid"]) == before


def test_generic_provider_failure_remains_retryable_then_success_reuses_canonical_item(tmp_path: Path) -> None:
    root = tmp_path / "store"
    seed(root)
    store = MediaWatchStore(root)
    before = store.load_item("youtube:fixtureA01")
    assert before is not None

    broken = FakeInteractions(error=RuntimeError("upstream unavailable"))
    with pytest.raises(RuntimeError, match="upstream unavailable"):
        ensure_summary(
            store,
            item_uid=before["item_uid"],
            provider=provider(broken),
            generated_at="2026-10-04T19:00:00Z",
        )

    sidecar = build_sidecar(store, before["item_uid"])
    assert sidecar["summary"]["state"] == "failed"
    assert sidecar["summary"]["retryable"] is True

    healthy = FakeInteractions(
        output={
            "summary": "Retry succeeded without touching canonical metadata.",
            "key_points": ["Retry is safe"],
        }
    )
    artifact, state = ensure_summary(
        store,
        item_uid=before["item_uid"],
        provider=provider(healthy),
        generated_at="2026-10-04T19:05:00Z",
    )
    assert state == "generated"
    assert artifact["summary"].startswith("Retry succeeded")
    assert len(healthy.calls) == 1
    assert build_sidecar(store, before["item_uid"])["summary"]["state"] == "available"
    assert store.load_item(before["item_uid"]) == before
