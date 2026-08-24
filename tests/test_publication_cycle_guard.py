from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publication_cycle_guard import resolve_production_digest, validate_predeploy


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def fixture(root: Path, *, digest="20260824T18", age_minutes=30, mixed=False, count=5):
    write_json(
        root / "sites/argentina-general.json",
        {
            "site_id": "argentina-general",
            "name": "Actualidad Argentina",
            "tagline": "Noticias recientes de Argentina",
            "locale": "es-AR",
            "selection": {
                "topics": ["All Topics"],
                "max_age_hours": 3,
                "minimum_items": 5,
                "max_items": 40,
            },
            "presentation": {"latest_count": 12, "show_sources": True},
        },
    )
    now = datetime(2026, 8, 24, 18, 45, tzinfo=timezone.utc)
    published = (now.timestamp() - age_minutes * 60)
    published_text = datetime.fromtimestamp(published, timezone.utc).isoformat().replace("+00:00", "Z")
    refs = [
        {
            "digest_at": digest if not (mixed and i == count - 1) else "20260824T17",
            "index_id": f"id-{i}",
            "title": f"Title {i}",
            "topic": "Inflación y Precios",
            "published_at": published_text,
            "link": f"https://example.test/{i}",
            "source": "Example",
        }
        for i in range(count)
    ]
    groups = [
        {
            "digest_at": digest,
            "topic": "Inflación y Precios",
            "article_count": count,
            "top_titles": ["Title 0"],
            "window_type": "1h_window",
            "group_number": 1,
        }
    ]
    write_jsonl(root / "storage/indexes/news_recent_refs_latest.jsonl", refs)
    write_jsonl(root / "storage/indexes/news_recent_groups_latest.jsonl", groups)
    return now


def test_three_consecutive_scheduled_resolutions_are_monotonic_and_new():
    times = [
        datetime(2026, 8, 24, hour, 45, tzinfo=timezone.utc)
        for hour in (16, 17, 18)
    ]
    digests = [resolve_production_digest(now) for now in times]
    assert digests == ["20260824T16", "20260824T17", "20260824T18"]
    assert digests == sorted(digests)
    assert len(set(digests)) == 3


def test_production_replay_or_future_digest_is_refused():
    now = datetime(2026, 8, 24, 18, 45, tzinfo=timezone.utc)
    for requested in ("20260824T17", "20260824T19"):
        with pytest.raises(ValueError, match="current UTC hour"):
            resolve_production_digest(now, requested)


def test_good_current_inputs_pass_target_guard(tmp_path):
    now = fixture(tmp_path, age_minutes=30)
    report = validate_predeploy(
        site_id="argentina-general",
        digest_at="20260824T18",
        repo_root=tmp_path,
        now=now,
        target_minutes=120,
    )
    assert report["status"] == "ok"
    assert report["eligible_item_count"] == 5
    assert report["newest_item_age_minutes"] == 30


def test_mixed_digest_is_blocked_before_deploy(tmp_path):
    now = fixture(tmp_path, mixed=True)
    with pytest.raises(ValueError, match="refs digest mismatch"):
        validate_predeploy(
            site_id="argentina-general",
            digest_at="20260824T18",
            repo_root=tmp_path,
            now=now,
            target_minutes=120,
        )


def test_target_miss_is_blocked_before_deploy(tmp_path):
    now = fixture(tmp_path, age_minutes=150)
    with pytest.raises(ValueError, match="target missed before deploy"):
        validate_predeploy(
            site_id="argentina-general",
            digest_at="20260824T18",
            repo_root=tmp_path,
            now=now,
            target_minutes=120,
        )


def test_minimum_items_is_enforced(tmp_path):
    now = fixture(tmp_path, count=4)
    with pytest.raises(ValueError, match="below minimum"):
        validate_predeploy(
            site_id="argentina-general",
            digest_at="20260824T18",
            repo_root=tmp_path,
            now=now,
            target_minutes=120,
        )


def test_digest_regression_guard(tmp_path):
    now = fixture(tmp_path)
    with pytest.raises(ValueError, match="digest regression"):
        validate_predeploy(
            site_id="argentina-general",
            digest_at="20260824T18",
            repo_root=tmp_path,
            now=now,
            target_minutes=120,
            previous_digest_at="20260824T19",
        )


def test_workflow_orders_guard_before_deploy_and_external_check_after():
    workflow = (ROOT / ".github/workflows/scheduled-publication.yml").read_text(encoding="utf-8")
    assert 'cron: "45 * * * *"' in workflow
    assert "bin/run_minimal_loop_once.sh --lane sensing" in workflow
    assert 'ENQUEUE_SCRAPE: "0"' in workflow
    assert 'DB_RUN_BOOKKEEPING: "0"' in workflow
    guard_at = workflow.index("publication_cycle_guard.py validate")
    deploy_at = workflow.index("scripts/roll_site.py")
    verify_at = workflow.index("scripts/verify_public_deployment.py")
    assert guard_at < deploy_at < verify_at
    assert "if: always()" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "promote_draft_to_published" not in workflow
    assert "--lane editorial" not in workflow
