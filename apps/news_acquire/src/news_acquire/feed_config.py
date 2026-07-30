"""Validated, versioned sensing feed configuration."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


DEFAULT_FEED_CONFIG = Path(__file__).resolve().parents[4] / "config" / "sensing_feeds.v1.yaml"


def load_feed_config(path: str | Path | None = None) -> dict[str, str]:
    config_path = Path(path or os.getenv("SENSING_FEED_CONFIG", DEFAULT_FEED_CONFIG))
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"invalid sensing feed config {config_path}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("schema_version") != "sensing_feeds.v1":
        raise ValueError(f"invalid sensing feed config {config_path}: expected schema_version sensing_feeds.v1")
    entries = payload.get("feeds")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"invalid sensing feed config {config_path}: feeds must be a non-empty list")

    feeds: dict[str, str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"invalid sensing feed config {config_path}: feeds[{index}] must be an object")
        topic = entry.get("topic")
        url = entry.get("url")
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError(f"invalid sensing feed config {config_path}: feeds[{index}].topic is required")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            raise ValueError(f"invalid sensing feed config {config_path}: feeds[{index}].url must be http(s)")
        if topic in feeds:
            raise ValueError(f"invalid sensing feed config {config_path}: duplicate topic {topic!r}")
        feeds[topic] = url
    return feeds
