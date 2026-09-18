from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.compile_outlet import compile_outlet
from scripts.outlet_runtime import resolve_outlet_runtime


DIGEST = "20260918T21"
NOW = "2026-09-18T21:30:00Z"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def policy(policy_id: str) -> dict:
    return {
        "policy_id": policy_id,
        "policy_version": "1",
        "max_age_minutes": 180,
        "future_tolerance_minutes": 5,
        "minimum_items": 1,
        "max_items": 1,
        "high_priority_threshold": 10,
        "default_topic_weight": 0,
        "topic_weights": {},
        "freshness_buckets": [
            {"max_age_minutes": 180, "score": 10, "reason_code": "fresh_under_180m"}
        ],
        "first_source_bonus": 0,
        "first_topic_bonus": 0,
        "repeat_source_penalty": 0,
        "repeat_topic_penalty": 0,
    }


def site(site_id: str, storage_dir: str, policy_path: str) -> dict:
    return {
        "site_id": site_id,
        "name": site_id,
        "tagline": f"{site_id} fixture",
        "locale": "es-AR",
        "runtime": {
            "data_dir": f".runtime/{site_id}/data",
            "storage_dir": storage_dir,
            "selection_policy": policy_path,
        },
        "selection": {
            "topics": ["All Topics"],
            "max_age_hours": 3,
            "minimum_items": 1,
            "max_items": 1,
        },
        "presentation": {"latest_count": 1, "show_sources": True},
    }


def published(article_id: str, title: str, slug: str) -> dict:
    return {
        "schema_name": "published_article.v1",
        "article_id": article_id,
        "draft_id": f"draft-{article_id}",
        "digest_at": DIGEST,
        "story_group_id": f"group-{article_id}",
        "slug": slug,
        "title": title,
        "summary": f"{title} summary",
        "body_md": f"# {title}\n\nBody.",
        "topic": "All Topics",
        "source_links": [f"https://example.test/{slug}"],
        "citations": [
            {
                "citation_id": "c1",
                "claim_text": title,
                "source_ref_id": f"source-{article_id}",
                "url": f"https://example.test/{slug}",
            }
        ],
        "status": "published",
        "review_status": "human_approved",
        "published_at": "2026-09-18T20:00:00Z",
        "updated_at": "2026-09-18T20:00:00Z",
    }


def seed_runtime(root: Path, storage_rel: str, marker: str, article_title: str) -> Path:
    storage = root / storage_rel
    refs = [
        {
            "digest_at": DIGEST,
            "index_id": f"{marker}-signal",
            "title": f"{marker} signal",
            "topic": "All Topics",
            "published_at": "2026-09-18T21:15:00Z",
            "link": f"https://example.test/{marker}/signal",
            "source": marker,
        }
    ]
    groups = [
        {
            "digest_at": DIGEST,
            "topic": "All Topics",
            "article_count": 1,
            "top_titles": [refs[0]["title"]],
            "window_type": "recent",
            "group_number": 1,
        }
    ]
    write_jsonl(storage / "indexes/news_recent_refs_latest.jsonl", refs)
    write_jsonl(storage / "indexes/news_recent_groups_latest.jsonl", groups)
    write_jsonl(
        storage / "buses/published_article/v1" / f"{marker}.jsonl",
        [published(f"{marker}-article", article_title, f"{marker}-article")],
    )
    return storage


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_two_configured_outlets_have_isolated_mutable_state(tmp_path: Path) -> None:
    write_json(tmp_path / "config/argentina-policy.json", policy("argentina-test-v1"))
    write_json(tmp_path / "config/southland-policy.json", policy("southland-test-v1"))
    write_json(
        tmp_path / "sites/argentina-general.json",
        site("argentina-general", "storage", "config/argentina-policy.json"),
    )
    write_json(
        tmp_path / "sites/southland.json",
        site("southland", ".runtime/southland/storage", "config/southland-policy.json"),
    )

    argentina_storage = seed_runtime(tmp_path, "storage", "argentina", "ARGENTINA ARTICLE")
    southland_storage = seed_runtime(
        tmp_path,
        ".runtime/southland/storage",
        "southland",
        "SOUTHLAND ARTICLE",
    )

    argentina = compile_outlet(
        repo_root=tmp_path,
        site_id="argentina-general",
        digest_at=DIGEST,
        now=NOW,
    )
    before_southland = tree_hash(argentina_storage)

    southland = compile_outlet(
        repo_root=tmp_path,
        site_id="southland",
        digest_at=DIGEST,
        now=NOW,
    )
    after_southland = tree_hash(argentina_storage)

    argentina_snapshot = json.loads(Path(argentina["snapshot_path"]).read_text(encoding="utf-8"))
    southland_snapshot = json.loads(Path(southland["snapshot_path"]).read_text(encoding="utf-8"))

    assert argentina["selection_policy_id"] == "argentina-test-v1"
    assert southland["selection_policy_id"] == "southland-test-v1"

    assert argentina_snapshot["site"]["site_id"] == "argentina-general"
    assert southland_snapshot["site"]["site_id"] == "southland"

    assert {row["title"] for row in argentina_snapshot["signals"]["latest"]} == {"argentina signal"}
    assert {row["title"] for row in southland_snapshot["signals"]["latest"]} == {"southland signal"}

    assert set(argentina_snapshot["articles"]) == {"argentina-article"}
    assert set(southland_snapshot["articles"]) == {"southland-article"}
    assert "southland-article" not in argentina_snapshot["articles"]
    assert "argentina-article" not in southland_snapshot["articles"]

    assert before_southland == after_southland
    assert southland_storage != argentina_storage


def test_runtime_paths_must_be_repo_relative_and_cannot_escape(tmp_path: Path) -> None:
    write_json(tmp_path / "config/policy.json", policy("test-v1"))
    cfg = site("southland", "../outside", "config/policy.json")
    write_json(tmp_path / "sites/southland.json", cfg)

    with pytest.raises(ValueError, match="escapes repository root"):
        resolve_outlet_runtime(tmp_path, "southland")
