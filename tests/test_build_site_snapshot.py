import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_site_snapshot.py"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def config(tmp, **selection):
    value = {
        "site_id": "test",
        "name": "Test news",
        "tagline": "Test tagline",
        "locale": "es-AR",
        "selection": {
            "topics": ["All Topics"],
            "max_age_hours": 3,
            "minimum_items": 5,
            "max_items": 40,
        }
        | selection,
        "presentation": {"latest_count": 12, "show_sources": True},
    }
    write_json(tmp / "sites/test.json", value)


def inputs(tmp, digest="20260721T18", n=5, topic="All Topics"):
    refs = [
        {
            "digest_at": digest,
            "index_id": f"id{i}",
            "title": f"Title {i}",
            "topic": topic,
            "published_at": f"2026-07-21T{18 - i % 2:02}:00:00Z",
            "link": f"https://e.test/{i}",
            "source": "E",
        }
        for i in range(n)
    ]
    groups = [
        {
            "digest_at": digest,
            "topic": topic,
            "article_count": n,
            "top_titles": ["Title 0"],
            "window_type": "A",
            "group_number": 1,
        }
    ]
    write_jsonl(tmp / "indexes/news_recent_refs_latest.jsonl", refs)
    write_jsonl(tmp / "indexes/news_recent_groups_latest.jsonl", groups)
    write_jsonl(tmp / "indexes/published_articles_latest.jsonl", [])


def published_article(
    *,
    article_id="article-1",
    slug="approved-analysis",
    topic="All Topics",
    published_at="2026-07-20T12:00:00Z",
):
    return {
        "schema_name": "published_article.v1",
        "article_id": article_id,
        "draft_id": f"draft-{article_id}",
        "digest_at": "20260720T12",
        "story_group_id": "group-1",
        "slug": slug,
        "title": "Approved analysis",
        "summary": "Reviewed summary",
        "body_md": "# Approved analysis\n\nReviewed body.",
        "topic": topic,
        "source_links": ["https://source.test/report"],
        "citations": [
            {
                "citation_id": "c1",
                "claim_text": "Reviewed claim",
                "source_ref_id": "source-1",
                "url": "https://source.test/report",
            }
        ],
        "status": "published",
        "review_status": "human_approved",
        "published_at": published_at,
        "updated_at": published_at,
    }


def run(tmp, expect=True):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--site-id",
            "test",
            "--digest-at",
            "20260721T18",
            "--sites-dir",
            str(tmp / "sites"),
            "--indexes-dir",
            str(tmp / "indexes"),
            "--output",
            str(tmp / "out.json"),
            "--now",
            "2026-07-21T18:30:00Z",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == (0 if expect else 1), result.stdout + result.stderr
    return result


def test_valid_snapshot_and_deterministic_id_with_empty_publication(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    run(tmp_path)
    one = json.loads((tmp_path / "out.json").read_text())
    run(tmp_path)
    two = json.loads((tmp_path / "out.json").read_text())
    assert one["schema_name"] == "site_snapshot.v2"
    assert one["snapshot_id"] == two["snapshot_id"]
    assert one["metrics"] == {
        "item_count": 5,
        "section_count": 1,
        "published_article_count": 0,
    }
    assert one["publication"] == {"featured": None, "latest": []}
    assert one["articles"] == {}
    assert one["signals"]["hero"] == one["signals"]["latest"][0]


def test_approved_article_enters_snapshot_with_evidence_intact(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    article = published_article()
    write_jsonl(tmp_path / "indexes/published_articles_latest.jsonl", [article])
    run(tmp_path)
    snapshot = json.loads((tmp_path / "out.json").read_text())
    assert snapshot["metrics"]["published_article_count"] == 1
    assert snapshot["publication"]["featured"]["slug"] == article["slug"]
    public = snapshot["articles"][article["slug"]]
    assert public["source_links"] == article["source_links"]
    assert public["citations"] == article["citations"]
    assert public["body_md"] == article["body_md"]


def test_draft_contamination_of_published_index_fails_closed(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    draft = {
        "schema_name": "news_article_draft.v1",
        "draft_id": "draft-sneak",
        "status": "draft",
        "title": "This must never become public",
    }
    write_jsonl(tmp_path / "indexes/published_articles_latest.jsonl", [draft])
    result = run(tmp_path, False)
    assert "not a valid published_article.v1" in result.stdout


def test_draft_elsewhere_is_not_a_snapshot_input(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    write_json(
        tmp_path / "indexes/editorial_latest.json",
        {
            "schema_name": "editorial_status.v1",
            "drafts": [{"draft_id": "private-draft", "title": "Private draft"}],
        },
    )
    run(tmp_path)
    snapshot_text = (tmp_path / "out.json").read_text()
    assert "private-draft" not in snapshot_text
    assert "Private draft" not in snapshot_text


def test_old_approved_article_does_not_inherit_signal_freshness_sla(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    write_jsonl(
        tmp_path / "indexes/published_articles_latest.jsonl",
        [published_article(published_at="2026-06-01T12:00:00Z")],
    )
    run(tmp_path)
    snapshot = json.loads((tmp_path / "out.json").read_text())
    assert snapshot["metrics"]["published_article_count"] == 1


def test_mixed_signal_digests_fail(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    path = tmp_path / "indexes/news_recent_refs_latest.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[-1]["digest_at"] = "20260721T17"
    write_jsonl(path, rows)
    run(tmp_path, False)


def test_requested_signal_digest_mismatch_fails(tmp_path):
    config(tmp_path)
    inputs(tmp_path, "20260721T17")
    run(tmp_path, False)


def test_stale_signal_input_fails(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    path = tmp_path / "indexes/news_recent_refs_latest.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        row["published_at"] = "2026-07-21T10:00:00Z"
    write_jsonl(path, rows)
    run(tmp_path, False)


def test_minimum_signal_items_fails(tmp_path):
    config(tmp_path)
    inputs(tmp_path, n=4)
    run(tmp_path, False)


def test_topic_max_items_and_branding(tmp_path):
    config(tmp_path, topics=["Sports"], max_items=2, minimum_items=1)
    inputs(tmp_path, n=3, topic="Sports")
    run(tmp_path)
    snapshot = json.loads((tmp_path / "out.json").read_text())
    assert len(snapshot["signals"]["latest"]) == 2
    assert snapshot["site"]["name"] == "Test news"


def test_all_topics_is_wildcard_for_concrete_signal_and_publication_topics(tmp_path):
    config(tmp_path, topics=["All Topics"], minimum_items=1)
    inputs(tmp_path, n=2, topic="Inflación y Precios")
    write_jsonl(
        tmp_path / "indexes/published_articles_latest.jsonl",
        [published_article(topic="Inflación y Precios")],
    )
    run(tmp_path)
    snapshot = json.loads((tmp_path / "out.json").read_text())
    assert snapshot["signals"]["hero"]["topic"] == "Inflación y Precios"
    assert snapshot["publication"]["featured"]["topic"] == "Inflación y Precios"


def test_second_configuration_changes_branding_without_renderer_change(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    run(tmp_path)
    first = json.loads((tmp_path / "out.json").read_text())
    second = {
        "site_id": "second",
        "name": "Otra portada",
        "tagline": "Otra voz",
        "locale": "es-AR",
        "selection": {
            "topics": ["All Topics"],
            "max_age_hours": 3,
            "minimum_items": 5,
            "max_items": 40,
        },
        "presentation": {"latest_count": 12, "show_sources": False},
    }
    write_json(tmp_path / "sites/second.json", second)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--site-id",
            "second",
            "--digest-at",
            "20260721T18",
            "--sites-dir",
            str(tmp_path / "sites"),
            "--indexes-dir",
            str(tmp_path / "indexes"),
            "--output",
            str(tmp_path / "second.json"),
            "--now",
            "2026-07-21T18:30:00Z",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout
    assert json.loads((tmp_path / "second.json").read_text())["site"]["name"] != first["site"]["name"]
