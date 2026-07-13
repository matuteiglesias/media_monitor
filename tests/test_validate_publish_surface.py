import json
from pathlib import Path

import pytest

from scripts.validate_publish_surface import validate_publish_surface


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_validate_publish_surface_reports_editorial_handoff_json_path(tmp_path):
    storage = tmp_path / "storage"
    digest = "20260713T21"
    _write_jsonl(
        storage / "indexes" / "news_recent_refs_latest.jsonl",
        [
            {
                "digest_at": digest,
                "title": "Story",
                "topic": "Science",
                "published_at": "2026-07-13T21:00:00Z",
                "link": "https://example.com/story",
            }
        ],
    )
    _write_jsonl(
        storage / "indexes" / "news_recent_groups_latest.jsonl",
        [
            {
                "digest_at": digest,
                "topic": "Science",
                "window_type": "A",
                "group_number": 1,
                "article_count": 1,
                "top_titles": ["Story"],
            }
        ],
    )
    _write_json(
        storage / "indexes" / "editorial_latest.json",
        {
            "digest_at": digest,
            "human_handoff": {
                "action_candidates": [
                    {
                        "target_format": "article",
                        "ready_state": "draft-ready",
                        "title": "Draft",
                        "topic": "",
                    }
                ]
            },
        },
    )

    with pytest.raises(ValueError, match=r"human_handoff\.action_candidates\[0\]\.topic"):
        validate_publish_surface(storage, digest)
