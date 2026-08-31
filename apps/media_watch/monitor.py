from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

import yaml

from .store import MediaObservation, MediaWatchStore, utc_now
from .youtube_api import YouTubeDataClient

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "media_watch" / "sources.yaml"


def load_config(path: Path) -> dict:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("media-watch config must have schema_version: 1")
    sources = [row for row in (config.get("sources") or []) if row.get("active", True)]
    if len(sources) < 1:
        raise ValueError("media-watch config has no active sources")
    config["sources"] = sources
    return config


def acquire_source(client: YouTubeDataClient, source: dict, *, limit: int, observed_at: str) -> tuple[list[MediaObservation], dict]:
    channel = client.fetch_channel(source["native_source_id"])
    expected = str(source["display_name"]).casefold()
    returned = channel.title.casefold()
    if expected not in returned and returned not in expected:
        raise ValueError(f"configured source {source['display_name']!r} resolved to unexpected channel title {channel.title!r}")
    refs = client.fetch_upload_refs(channel.uploads_playlist_id, limit=limit)
    videos = client.fetch_videos(refs)
    observations = [MediaObservation(source_id=source["source_id"], video_id=video.video_id, title=video.title, description=video.description, published_at=video.published_at, duration_seconds=video.duration_seconds, view_count=video.view_count, like_count=video.like_count, comment_count=video.comment_count, availability=video.availability, observed_at=observed_at) for video in videos]
    meta = {"source_id": source["source_id"], "display_name": source["display_name"], "channel_id": channel.channel_id, "channel_title": channel.title, "uploads_playlist_id": channel.uploads_playlist_id, "latest_published_at": max((row.published_at for row in observations), default=None), "observations": len(observations)}
    return observations, meta


def run_live(*, config_path: Path, store_root: Path, evidence_root: Path, limit: int, api_key: str) -> dict:
    config = load_config(config_path)
    store = MediaWatchStore(store_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    observed_at = utc_now()
    all_observations: list[MediaObservation] = []
    source_results: dict[str, dict] = {}
    source_failures: list[dict] = []
    for source in config["sources"]:
        client = YouTubeDataClient(api_key)
        try:
            observations, meta = acquire_source(client, source, limit=limit, observed_at=observed_at)
            all_observations.extend(observations)
            source_results[source["source_id"]] = meta
            store.update_source_state(source_id=source["source_id"], display_name=source["display_name"], channel_id=meta["channel_id"], channel_title=meta["channel_title"], uploads_playlist_id=meta["uploads_playlist_id"], observed_at=observed_at, latest_published_at=meta["latest_published_at"], health="healthy", error=None, item_count=meta["observations"], api_calls=client.api_calls, quota_units_estimated=client.quota_units_estimated)
            (evidence_root / f"{source['source_id']}.json").write_text(json.dumps({"source": meta, "observations": [asdict(row) for row in observations]}, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        except Exception as exc:
            failure = {"source_id": source["source_id"], "error_type": type(exc).__name__, "message": str(exc)}
            source_failures.append(failure)
            store.update_source_state(source_id=source["source_id"], display_name=source["display_name"], channel_id=source["native_source_id"], channel_title=source["display_name"], uploads_playlist_id="unknown", observed_at=observed_at, latest_published_at=None, health="failed", error=f"{type(exc).__name__}: {exc}", item_count=0, api_calls=client.api_calls, quota_units_estimated=client.quota_units_estimated)
    first, materialization_failures, first_run_id = store.materialize(all_observations)
    item_count_after_first = len(store.list_items())
    snapshots_after_first = store.snapshot_count()
    replay, replay_failures, replay_run_id = store.materialize(all_observations)
    item_count_after_replay = len(store.list_items())
    snapshots_after_replay = store.snapshot_count()
    if replay.new_items != 0 or replay.new_snapshots != 0:
        raise RuntimeError("unchanged observation replay created new item/snapshot")
    if item_count_after_first != item_count_after_replay or snapshots_after_first != snapshots_after_replay:
        raise RuntimeError("unchanged replay changed store cardinality")
    expected_sources = {row["source_id"] for row in config["sources"]}
    acceptance_green = not source_failures and not materialization_failures and not replay_failures and set(source_results) == expected_sources and all(row["observations"] >= limit for row in source_results.values())
    manifest = {"schema_name": "media_watch_m1_live_proof.v1", "observed_at": observed_at, "requested_per_source": limit, "sources": source_results, "source_failures": source_failures, "first_materialization": asdict(first), "replay_materialization": asdict(replay), "first_run_id": first_run_id, "replay_run_id": replay_run_id, "item_count_after_first": item_count_after_first, "item_count_after_replay": item_count_after_replay, "snapshot_count_after_first": snapshots_after_first, "snapshot_count_after_replay": snapshots_after_replay, "acceptance_green": acceptance_green}
    (evidence_root / "m1_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile configured YouTube channels into governed media-item/snapshot state")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--store-root", type=Path, default=Path("data/canonical/media_watch"))
    parser.add_argument("--evidence-root", type=Path, default=Path("artifacts/runs/media-watch-m1"))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        parser.error("YOUTUBE_API_KEY is required for official YouTube Data API reconciliation")
    manifest = run_live(config_path=args.config, store_root=args.store_root, evidence_root=args.evidence_root, limit=args.limit, api_key=api_key)
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if manifest["acceptance_green"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
