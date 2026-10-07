from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

import requests
from jsonschema import Draft202012Validator, FormatChecker

from apps.media_watch.enrichment import MediaEnrichmentStore, load_watch_config
from apps.media_watch.sidecar_http import (
    ENSURE_PATH,
    INSPECT_PATH,
    SUMMARY_PATH,
    YouTubeSidecarBridge,
    make_server,
)
from apps.media_watch.store import MediaWatchStore
from apps.media_watch.summary import ADAPTER_VERSION, PROCESSING_MODE, PROMPT_VERSION
from apps.media_watch.youtube_api import VideoDetail

VIDEO_ID = "aZqxNLuf89c"
CHANNEL_ID = "UCaaaaaaaaaaaaaaaaaaaaaa"


class FakeYouTubeClient:
    api_calls = 1
    quota_units_estimated = 1

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    def fetch_video(self, video_id: str) -> VideoDetail:
        self.calls.append(video_id)
        if self.error is not None:
            raise self.error
        return VideoDetail(
            video_id=video_id,
            channel_id=CHANNEL_ID,
            channel_title="HTTP Bridge Test Channel",
            title="A governed bridge test video",
            description="Metadata materialized through the existing sidecar path.",
            published_at="2026-10-06T20:00:00Z",
            duration_seconds=321,
            view_count=1200,
            like_count=88,
            comment_count=9,
            availability="public",
        )


class FakeSummaryProvider:
    provider_name = "google-gemini"
    model = "gemini-test"
    adapter_version = ADAPTER_VERSION
    processing_mode = PROCESSING_MODE

    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    def summarize_youtube(self, url: str) -> dict:
        self.calls.append(url)
        if self.error is not None:
            raise self.error
        return {
            "summary": "A deterministic fake summary generated through the governed summary seam.",
            "key_points": ["First point", "Second point", "Third point"],
        }


def bridge(
    tmp_path: Path,
    *,
    youtube: FakeYouTubeClient | None = None,
    summary: FakeSummaryProvider | None = None,
) -> YouTubeSidecarBridge:
    return YouTubeSidecarBridge(
        MediaWatchStore(tmp_path / "store"),
        metadata_client_factory=lambda: youtube,
        summary_provider_factory=lambda: summary,
    )


def ensure_video(target: YouTubeSidecarBridge) -> dict:
    response = target.post(ENSURE_PATH, {"video_id": VIDEO_ID})
    assert response.status == 200
    return response.payload


def test_ensure_unknown_then_known_is_idempotent(tmp_path: Path) -> None:
    youtube = FakeYouTubeClient()
    target = bridge(tmp_path, youtube=youtube)

    first = ensure_video(target)
    second = ensure_video(target)

    assert first == second
    assert youtube.calls == [VIDEO_ID]
    assert first["item_uid"] == f"youtube:{VIDEO_ID}"
    assert first["channel"]["native_channel_id"] == CHANNEL_ID
    assert first["summary"]["state"] == "not_attempted"


def test_inspect_known_is_pure_and_unknown_is_clean_404(tmp_path: Path) -> None:
    youtube = FakeYouTubeClient()
    target = bridge(tmp_path, youtube=youtube)
    expected = ensure_video(target)
    before_calls = list(youtube.calls)

    known = target.post(INSPECT_PATH, {"video_id": VIDEO_ID})
    unknown = target.post(INSPECT_PATH, {"video_id": "abcdefghijk"})

    assert known.status == 200
    assert known.payload == expected
    assert youtube.calls == before_calls
    assert unknown.status == 404
    assert unknown.payload == {
        "error": {
            "code": "video_not_found",
            "message": "Video is not present in governed Media Monitor state",
        }
    }


def test_summary_generated_then_cached_without_second_provider_call(tmp_path: Path) -> None:
    youtube = FakeYouTubeClient()
    summary = FakeSummaryProvider()
    target = bridge(tmp_path, youtube=youtube, summary=summary)
    ensure_video(target)

    first = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})
    second = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})

    assert first.status == 200
    assert second.status == 200
    assert first.payload == second.payload
    assert first.payload["summary"]["state"] == "available"
    assert first.payload["summary"]["provider"] == "google-gemini"
    assert first.payload["summary"]["model"] == "gemini-test"
    assert summary.calls == [f"https://www.youtube.com/watch?v={VIDEO_ID}"]

    artifacts = MediaEnrichmentStore(target.store).list_summaries(f"youtube:{VIDEO_ID}")
    attempts = MediaEnrichmentStore(target.store).list_summary_attempts(f"youtube:{VIDEO_ID}")
    assert len(artifacts) == 1
    assert len(attempts) == 1
    assert attempts[0]["state"] == "generated"


def test_summary_cached_does_not_require_provider_configuration(tmp_path: Path) -> None:
    youtube = FakeYouTubeClient()
    summary = FakeSummaryProvider()
    target = bridge(tmp_path, youtube=youtube, summary=summary)
    ensure_video(target)
    generated = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})
    assert generated.payload["summary"]["state"] == "available"

    cached_only = YouTubeSidecarBridge(
        target.store,
        metadata_client_factory=lambda: None,
        summary_provider_factory=lambda: (_ for _ in ()).throw(AssertionError("provider must not be constructed")),
    )
    cached = cached_only.post(SUMMARY_PATH, {"video_id": VIDEO_ID})

    assert cached.status == 200
    assert cached.payload == generated.payload


def test_provider_limit_state_is_returned_without_partial_summary(tmp_path: Path) -> None:
    youtube = FakeYouTubeClient()
    summary = FakeSummaryProvider(
        error=RuntimeError("input exceeds the maximum number of tokens allowed 1048576")
    )
    target = bridge(tmp_path, youtube=youtube, summary=summary)
    ensure_video(target)

    response = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})
    repeated = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})

    assert response.status == 200
    assert repeated.payload == response.payload
    assert response.payload["summary"]["state"] == "provider_limit"
    assert response.payload["summary"]["summary"] is None
    assert response.payload["summary"]["retryable"] is False
    assert len(summary.calls) == 1
    enrichment = MediaEnrichmentStore(target.store)
    assert enrichment.list_summaries(f"youtube:{VIDEO_ID}") == []
    assert len(enrichment.list_summary_attempts(f"youtube:{VIDEO_ID}")) == 1


def test_failed_summary_state_is_safe_and_persists_no_fake_summary(tmp_path: Path) -> None:
    youtube = FakeYouTubeClient()
    secret = "SECRET-UPSTREAM-PAYLOAD /home/operator/key.json"
    summary = FakeSummaryProvider(error=RuntimeError(secret))
    target = bridge(tmp_path, youtube=youtube, summary=summary)
    ensure_video(target)

    response = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})

    assert response.status == 200
    assert response.payload["summary"]["state"] == "failed"
    assert response.payload["summary"]["summary"] is None
    assert response.payload["summary"]["retryable"] is True
    assert secret not in json.dumps(response.payload)
    assert MediaEnrichmentStore(target.store).list_summaries(f"youtube:{VIDEO_ID}") == []


def test_invalid_video_id_and_shape_are_rejected_before_providers(tmp_path: Path) -> None:
    youtube = FakeYouTubeClient()
    summary = FakeSummaryProvider()
    target = bridge(tmp_path, youtube=youtube, summary=summary)

    invalid_id = target.post(ENSURE_PATH, {"video_id": "short"})
    extra_field = target.post(ENSURE_PATH, {"video_id": VIDEO_ID, "other": "nope"})

    assert invalid_id.status == 400
    assert invalid_id.payload["error"]["code"] == "invalid_video_id"
    assert extra_field.status == 400
    assert extra_field.payload["error"]["code"] == "invalid_request"
    assert youtube.calls == []
    assert summary.calls == []


def test_ensure_does_not_enroll_channel_into_configured_watch(tmp_path: Path) -> None:
    config_path = Path("config/media_watch/sources.yaml")
    before_text = config_path.read_text(encoding="utf-8")
    configured = load_watch_config(config_path)
    configured_channel_ids = {
        source["native_source_id"]
        for source in configured["sources"]
        if source.get("platform") == "youtube"
    }
    assert CHANNEL_ID not in configured_channel_ids

    target = bridge(tmp_path, youtube=FakeYouTubeClient())
    response = target.post(ENSURE_PATH, {"video_id": VIDEO_ID})

    assert response.status == 200
    assert response.payload["channel"]["native_channel_id"] == CHANNEL_ID
    assert config_path.read_text(encoding="utf-8") == before_text
    assert CHANNEL_ID not in {
        source["native_source_id"]
        for source in load_watch_config(config_path)["sources"]
        if source.get("platform") == "youtube"
    }


def test_success_responses_validate_against_sidecar_schema(tmp_path: Path) -> None:
    target = bridge(tmp_path, youtube=FakeYouTubeClient(), summary=FakeSummaryProvider())
    ensure_payload = ensure_video(target)
    inspect_payload = target.post(INSPECT_PATH, {"video_id": VIDEO_ID}).payload
    summary_payload = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID}).payload

    schema = json.loads(
        Path("contracts/schemas/youtube_video_sidecar.v1.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for payload in (ensure_payload, inspect_payload, summary_payload):
        assert list(validator.iter_errors(payload)) == []


def test_safe_metadata_error_does_not_expose_exception_text(tmp_path: Path, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="media_watch.youtube_sidecar_http")
    secret = "AIza-not-a-real-key raw-provider-payload /tmp/private-store"
    youtube = FakeYouTubeClient(error=RuntimeError(secret))
    target = bridge(tmp_path, youtube=youtube)

    response = target.post(ENSURE_PATH, {"video_id": VIDEO_ID})

    assert response.status == 500
    assert response.payload["error"]["code"] == "internal_error"
    rendered = json.dumps(response.payload)
    assert secret not in rendered
    assert "AIza" not in rendered
    assert "/tmp/" not in rendered
    assert secret not in caplog.text
    assert "RuntimeError" in caplog.text


def test_http_transport_round_trip_uses_exact_paths(tmp_path: Path) -> None:
    target = bridge(tmp_path, youtube=FakeYouTubeClient(), summary=FakeSummaryProvider())
    server = make_server(bridge=target, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"

    try:
        health = requests.get(f"{base}/health", timeout=2)
        ensured = requests.post(
            f"{base}{ENSURE_PATH}",
            json={"video_id": VIDEO_ID},
            timeout=2,
        )
        inspected = requests.post(
            f"{base}{INSPECT_PATH}",
            json={"video_id": VIDEO_ID},
            timeout=2,
        )
        summarized = requests.post(
            f"{base}{SUMMARY_PATH}",
            json={"video_id": VIDEO_ID},
            timeout=2,
        )
        malformed = requests.post(
            f"{base}{ENSURE_PATH}",
            data="{",
            headers={"content-type": "application/json"},
            timeout=2,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ensured.status_code == inspected.status_code == summarized.status_code == 200
    assert ensured.json()["item_uid"] == f"youtube:{VIDEO_ID}"
    assert inspected.json()["item_uid"] == f"youtube:{VIDEO_ID}"
    assert summarized.json()["summary"]["state"] == "available"
    assert summarized.headers["cache-control"] == "no-store"
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "invalid_json"


def test_summary_unknown_and_unconfigured_provider_are_bounded(tmp_path: Path) -> None:
    target = bridge(tmp_path, youtube=FakeYouTubeClient(), summary=None)

    unknown = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})
    assert unknown.status == 404
    assert unknown.payload["error"]["code"] == "video_not_found"

    ensure_video(target)
    unconfigured = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})
    assert unconfigured.status == 503
    assert unconfigured.payload["error"]["code"] == "summary_provider_unconfigured"


def test_unknown_route_is_bounded(tmp_path: Path) -> None:
    target = bridge(tmp_path, youtube=FakeYouTubeClient())

    response = target.post("/v1/youtube/videos/nope", {"video_id": VIDEO_ID})

    assert response.status == 404
    assert response.payload["error"]["code"] == "not_found"


def test_summary_artifact_provenance_remains_existing_contract(tmp_path: Path) -> None:
    target = bridge(tmp_path, youtube=FakeYouTubeClient(), summary=FakeSummaryProvider())
    ensure_video(target)
    response = target.post(SUMMARY_PATH, {"video_id": VIDEO_ID})

    summary = response.payload["summary"]
    assert summary["provider"] == "google-gemini"
    assert summary["model"] == "gemini-test"
    assert summary["prompt_version"] == PROMPT_VERSION
    assert summary["adapter_version"] == ADAPTER_VERSION
    assert summary["processing_mode"] == PROCESSING_MODE
