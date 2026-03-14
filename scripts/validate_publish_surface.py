#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid json: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{lineno}: expected object, got {type(row).__name__}")
            rows.append(row)
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid json: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected object root, got {type(payload).__name__}")
    return payload


def _require_string(obj: dict[str, Any], key: str, *, min_length: int = 0) -> str:
    value = obj.get(key)
    if not isinstance(value, str):
        raise ValueError(f"missing/invalid '{key}' (expected string)")
    if len(value.strip()) < min_length:
        raise ValueError(f"invalid '{key}' (min_length={min_length})")
    return value


def _require_int(obj: dict[str, Any], key: str, *, minimum: int = 0) -> int:
    value = obj.get(key)
    if not isinstance(value, int):
        raise ValueError(f"missing/invalid '{key}' (expected int)")
    if value < minimum:
        raise ValueError(f"invalid '{key}' (minimum={minimum})")
    return value


def _validate_frontpage_item(row: dict[str, Any], idx: int) -> None:
    _require_string(row, "digest_at", min_length=1)
    _require_string(row, "title", min_length=1)
    _require_string(row, "topic", min_length=1)
    _require_string(row, "published_at", min_length=1)
    _require_string(row, "link", min_length=1)

    source = row.get("source")
    if source is not None and not isinstance(source, str):
        raise ValueError(f"row#{idx}: invalid 'source' (expected string)")
    index_id = row.get("index_id")
    if index_id is not None and not isinstance(index_id, str):
        raise ValueError(f"row#{idx}: invalid 'index_id' (expected string)")


def _validate_story(row: dict[str, Any], idx: int) -> None:
    story_id = row.get("index_id") or row.get("link")
    if not isinstance(story_id, str) or not story_id.strip():
        raise ValueError(f"row#{idx}: cannot resolve Story.id from index_id/link")
    _require_string(row, "title", min_length=1)
    _require_string(row, "topic", min_length=1)
    _require_string(row, "link", min_length=1)


def _validate_topic_page(row: dict[str, Any], idx: int) -> None:
    _require_string(row, "digest_at", min_length=1)
    _require_string(row, "topic", min_length=1)
    _require_string(row, "window_type", min_length=1)

    _require_int(row, "group_number", minimum=0)
    _require_int(row, "article_count", minimum=0)

    top_titles = row.get("top_titles")
    if not isinstance(top_titles, list):
        raise ValueError(f"row#{idx}: invalid 'top_titles' (expected list)")
    if any(not isinstance(v, str) for v in top_titles):
        raise ValueError(f"row#{idx}: invalid 'top_titles' (all entries must be string)")


def _validate_editorial_handoff_item(row: dict[str, Any], idx: int) -> None:
    target_format = _require_string(row, "target_format", min_length=1)
    if target_format not in {"article", "yt_script"}:
        raise ValueError(f"item#{idx}: invalid 'target_format' ({target_format!r})")

    _require_string(row, "ready_state", min_length=1)
    _require_string(row, "title", min_length=1)
    _require_string(row, "topic", min_length=1)

    for optional in ("priority", "source", "path"):
        value = row.get(optional)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"item#{idx}: invalid '{optional}' (expected string)")


def validate_publish_surface(storage_dir: Path) -> None:
    refs_path = storage_dir / "indexes" / "news_recent_refs_latest.jsonl"
    groups_path = storage_dir / "indexes" / "news_recent_groups_latest.jsonl"
    editorial_path = storage_dir / "indexes" / "editorial_latest.json"

    for path in (refs_path, groups_path, editorial_path):
        if not path.exists():
            raise ValueError(f"missing required file: {path}")

    refs = _iter_jsonl(refs_path)
    groups = _iter_jsonl(groups_path)
    editorial = _read_json(editorial_path)

    for idx, row in enumerate(refs, start=1):
        try:
            _validate_frontpage_item(row, idx)
            _validate_story(row, idx)
        except ValueError as exc:
            raise ValueError(f"{refs_path}: row#{idx}: {exc}") from exc

    for idx, row in enumerate(groups, start=1):
        try:
            _validate_topic_page(row, idx)
        except ValueError as exc:
            raise ValueError(f"{groups_path}: row#{idx}: {exc}") from exc

    human_handoff = editorial.get("human_handoff")
    if not isinstance(human_handoff, dict):
        raise ValueError(f"{editorial_path}: missing/invalid 'human_handoff' object")

    action_candidates = human_handoff.get("action_candidates")
    if not isinstance(action_candidates, list):
        raise ValueError(f"{editorial_path}: missing/invalid 'human_handoff.action_candidates' list")

    for idx, item in enumerate(action_candidates, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{editorial_path}: item#{idx}: expected object")
        try:
            _validate_editorial_handoff_item(item, idx)
        except ValueError as exc:
            raise ValueError(f"{editorial_path}: {exc}") from exc

    print(f"[validate-publish-surface] frontpage_items={len(refs)}")
    print(f"[validate-publish-surface] stories={len(refs)}")
    print(f"[validate-publish-surface] topic_pages={len(groups)}")
    print(f"[validate-publish-surface] editorial_handoff_items={len(action_candidates)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate publish surface canonical contract against latest indexes")
    parser.add_argument("--storage-dir", default="storage", help="Storage root containing indexes/")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_publish_surface(Path(args.storage_dir))
    except ValueError as exc:
        print(f"[validate-publish-surface] ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
