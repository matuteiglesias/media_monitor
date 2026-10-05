from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .enrichment import MediaEnrichmentStore
from .store import MediaObservation, MediaWatchStore, _validate, sha256_text, utc_now
from .summary import DEFAULT_GEMINI_MODEL, GeminiSummaryProvider, ensure_summary
from .youtube_api import YouTubeDataClient

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,32}$")
_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}


def parse_youtube_video_id(value: str) -> str:
    raw = value.strip()
    if raw.startswith("youtube:"):
        raw = raw.split(":", 1)[1]
    if _VIDEO_ID_RE.fullmatch(raw):
        return raw
    if "://" not in raw and (
        raw.startswith("youtube.com/")
        or raw.startswith("www.youtube.com/")
        or raw.startswith("m.youtube.com/")
        or raw.startswith("youtu.be/")
    ):
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = parsed.netloc.casefold()
    candidate: str | None = None
    if host in _SHORT_HOSTS:
        candidate = parsed.path.strip("/").split("/", 1)[0]
    elif host in _YOUTUBE_HOSTS:
        if parsed.path.rstrip("/") == "/watch":
            candidate = (parse_qs(parsed.query).get("v") or [None])[0]
        else:
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
                candidate = parts[1]
    if not candidate or not _VIDEO_ID_RE.fullmatch(candidate):
        raise ValueError(f"unsupported YouTube video reference: {value!r}")
    return candidate


def canonical_youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_source_uid(channel_id: str) -> str:
    return f"youtube-channel:{channel_id}"


def _source_id_for_channel(store: MediaWatchStore, channel_id: str) -> str:
    for state in store.list_source_states():
        if state.get("channel_id") == channel_id:
            return state["source_id"]
    return f"youtube-channel-{sha256_text(channel_id)[:16]}"


def ensure_video_metadata(
    store: MediaWatchStore,
    video_ref: str,
    *,
    client: YouTubeDataClient | None,
    observed_at: str | None = None,
) -> tuple[dict, str]:
    video_id = parse_youtube_video_id(video_ref)
    item_uid = f"youtube:{video_id}"
    existing = store.load_item(item_uid)
    if existing is not None:
        return existing, "existing"
    if client is None:
        raise ValueError("YOUTUBE_API_KEY is required to ensure metadata for an unknown video")

    detail = client.fetch_video(video_id)
    source_id = _source_id_for_channel(store, detail.channel_id)
    observed = observed_at or utc_now()
    result = store.ingest(
        MediaObservation(
            source_id=source_id,
            video_id=detail.video_id,
            title=detail.title,
            description=detail.description,
            published_at=detail.published_at,
            duration_seconds=detail.duration_seconds,
            view_count=detail.view_count,
            like_count=detail.like_count,
            comment_count=detail.comment_count,
            availability=detail.availability,
            observed_at=observed,
        )
    )
    source_items = [row for row in store.list_items() if row["source_id"] == source_id]
    prior_source = store.load_source_state(source_id) or {}
    store.update_source_state(
        source_id=source_id,
        display_name=detail.channel_title,
        channel_id=detail.channel_id,
        channel_title=detail.channel_title,
        uploads_playlist_id=str(prior_source.get("uploads_playlist_id") or "unknown"),
        observed_at=observed,
        latest_published_at=max((row["published_at"] for row in source_items), default=detail.published_at),
        health="healthy",
        error=None,
        item_count=len(source_items),
        api_calls=int(getattr(client, "api_calls", 0)),
        quota_units_estimated=int(getattr(client, "quota_units_estimated", 0)),
    )
    item = store.load_item(item_uid)
    assert item is not None
    return item, result.state


def _summary_projection(enrichment: MediaEnrichmentStore, item_uid: str) -> dict:
    summaries = enrichment.list_summaries(item_uid)
    attempts = enrichment.list_summary_attempts(item_uid)
    latest_attempt = attempts[0] if attempts else None
    if summaries:
        summary = summaries[0]
        return {
            "state": "available",
            "summary_id": summary["summary_id"],
            "summary": summary["summary"],
            "key_points": summary["key_points"],
            "provider": summary["provider"],
            "model": summary["model"],
            "prompt_version": summary["prompt_version"],
            "adapter_version": summary["adapter_version"],
            "processing_mode": summary["processing_mode"],
            "generated_at": summary["generated_at"],
            "latest_attempt_id": latest_attempt["attempt_id"] if latest_attempt else None,
            "retryable": False,
        }
    if latest_attempt:
        return {
            "state": latest_attempt["state"],
            "summary_id": None,
            "summary": None,
            "key_points": [],
            "provider": latest_attempt["provider"],
            "model": latest_attempt["model"],
            "prompt_version": latest_attempt["prompt_version"],
            "adapter_version": latest_attempt["adapter_version"],
            "processing_mode": latest_attempt["processing_mode"],
            "generated_at": None,
            "latest_attempt_id": latest_attempt["attempt_id"],
            "retryable": latest_attempt["retryable"],
        }
    return {
        "state": "not_attempted",
        "summary_id": None,
        "summary": None,
        "key_points": [],
        "provider": None,
        "model": None,
        "prompt_version": None,
        "adapter_version": None,
        "processing_mode": None,
        "generated_at": None,
        "latest_attempt_id": None,
        "retryable": None,
    }


def build_sidecar(store: MediaWatchStore, video_ref: str) -> dict:
    video_id = parse_youtube_video_id(video_ref)
    item_uid = f"youtube:{video_id}"
    item = store.load_item(item_uid)
    if item is None:
        raise ValueError(f"unknown item {item_uid}")

    source = store.load_source_state(item["source_id"]) or {}
    snapshots = store.list_snapshots(item_uid)
    latest_snapshot = snapshots[0] if snapshots else {}
    enrichment = MediaEnrichmentStore(store)
    text_state = enrichment.text_status(item_uid)
    text_asset = text_state.get("asset") or {}
    segments = enrichment.list_segments(item_uid)
    appearances = enrichment.list_appearances(item_uid=item_uid)
    channel_id = source.get("channel_id")
    payload = {
        "schema_name": "youtube_video_sidecar.v1",
        "schema_status": "experimental",
        "item_uid": item_uid,
        "video_id": video_id,
        "canonical_url": item["canonical_url"],
        "channel": {
            "source_uid": youtube_source_uid(channel_id) if channel_id else None,
            "source_id": item["source_id"],
            "native_channel_id": channel_id,
            "display_name": source.get("channel_title") or source.get("display_name"),
        },
        "metadata": {
            "state": "available",
            "snapshot_id": latest_snapshot.get("snapshot_id"),
            "observed_at": latest_snapshot.get("observed_at") or item["last_seen"],
            "title": item["title"],
            "description": item["description"],
            "published_at": item["published_at"],
            "duration_seconds": item.get("duration_seconds"),
            "availability": latest_snapshot.get("availability"),
            "statistics": latest_snapshot.get("statistics") or {
                "view_count": None,
                "like_count": None,
                "comment_count": None,
            },
        },
        "summary": _summary_projection(enrichment, item_uid),
        "text": {
            "state": text_state["status"],
            "available": bool(text_state["available"]),
            "preferred_text_asset_id": text_asset.get("text_asset_id"),
            "timing_available": bool(text_asset.get("timing_available", False)),
        },
        "segments": {
            "count": len(segments),
            "segment_ids": [row["segment_id"] for row in segments],
        },
        "appearances": {
            "count": len(appearances),
            "appearance_ids": [row["appearance_id"] for row in appearances],
        },
    }
    _validate("youtube_video_sidecar.v1.json", payload)
    return payload


def ensure_video_sidecar(
    store: MediaWatchStore,
    video_ref: str,
    *,
    metadata_client: YouTubeDataClient | None = None,
    summary_provider: GeminiSummaryProvider | None = None,
    observed_at: str | None = None,
) -> dict:
    item, _ = ensure_video_metadata(
        store,
        video_ref,
        client=metadata_client,
        observed_at=observed_at,
    )
    if summary_provider is not None:
        try:
            ensure_summary(
                store,
                item_uid=item["item_uid"],
                provider=summary_provider,
                generated_at=observed_at,
            )
        except Exception:
            sidecar = build_sidecar(store, item["item_uid"])
            if sidecar["summary"]["state"] not in {"provider_limit", "failed"}:
                raise
            return sidecar
    return build_sidecar(store, item["item_uid"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or ensure a governed YouTube video sidecar")
    parser.add_argument("--store-root", type=Path, default=Path("data/canonical/media_watch"))
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="Read the current sidecar without external calls")
    inspect_parser.add_argument("video")
    ensure_parser = subparsers.add_parser("ensure", help="Ensure metadata and optional explicit derivatives")
    ensure_parser.add_argument("video")
    ensure_parser.add_argument("--summary", action="store_true")
    ensure_parser.add_argument("--model", default=None)
    args = parser.parse_args(argv)
    store = MediaWatchStore(args.store_root)

    if args.command == "inspect":
        payload = build_sidecar(store, args.video)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    existing_id = f"youtube:{parse_youtube_video_id(args.video)}"
    youtube_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    metadata_client = YouTubeDataClient(youtube_key) if youtube_key else None
    if store.load_item(existing_id) is None and metadata_client is None:
        parser.error("YOUTUBE_API_KEY is required to ensure an unknown video")

    summary_provider = None
    if args.summary:
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not gemini_key:
            parser.error("GEMINI_API_KEY is required with --summary")
        model = (args.model or os.environ.get("GEMINI_MODEL", "") or DEFAULT_GEMINI_MODEL).strip()
        summary_provider = GeminiSummaryProvider(api_key=gemini_key, model=model)

    payload = ensure_video_sidecar(
        store,
        args.video,
        metadata_client=metadata_client,
        summary_provider=summary_provider,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if args.summary and payload["summary"]["state"] != "available":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
