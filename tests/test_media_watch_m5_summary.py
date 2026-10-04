from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.media_watch.enrichment import MediaEnrichmentStore
from apps.media_watch.fixture import seed
from apps.media_watch.store import MediaWatchStore
from apps.media_watch.summary import (
    PROMPT_VERSION,
    GeminiSummaryProvider,
    ensure_summary,
)


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


def provider(interactions: FakeInteractions) -> GeminiSummaryProvider:
    return GeminiSummaryProvider(
        api_key="test-key",
        model="gemini-test",
        client=FakeClient(interactions),
    )


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
    assert call["input"][1] == {
        "type": "video",
        "uri": before["canonical_url"],
    }
    assert call["response_format"]["mime_type"] == "application/json"
    assert call["response_format"]["schema"]["required"] == ["summary", "key_points"]

    assert first["schema_name"] == "media_summary.v1"
    assert first["item_uid"] == before["item_uid"]
    assert first["provider"] == "google-gemini"
    assert first["model"] == "gemini-test"
    assert first["prompt_version"] == PROMPT_VERSION
    assert first["generated_at"] == "2026-10-04T19:00:00Z"
    assert len(MediaEnrichmentStore(store).list_summaries(before["item_uid"])) == 1
    assert store.load_item(before["item_uid"]) == before


def test_invalid_structured_output_is_not_persisted(tmp_path: Path) -> None:
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

    assert MediaEnrichmentStore(store).list_summaries(before["item_uid"]) == []
    assert store.load_item(before["item_uid"]) == before


def test_provider_failure_leaves_canonical_state_untouched_and_retryable(tmp_path: Path) -> None:
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

    enrichment = MediaEnrichmentStore(store)
    assert enrichment.list_summaries(before["item_uid"]) == []
    assert store.load_item(before["item_uid"]) == before

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
    assert store.load_item(before["item_uid"]) == before
