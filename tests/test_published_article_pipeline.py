import json

import pytest

import scripts.promote_draft_to_published as promote_module
from scripts.build_published_article_indexes import build_indexes


def _draft():
    return {
        "schema_name": "news_article_draft.v1",
        "draft_id": "draft-123",
        "digest_at": "20260824T12",
        "story_group_id": "group-123",
        "title": "A reviewed article",
        "slug_candidate": "a-reviewed-article",
        "summary": "A concise summary.",
        "body_md": "Article body.",
        "topic": "Economía",
        "source_links": ["https://example.com/source"],
        "citations": [
            {
                "citation_id": "citation-1",
                "claim_text": "A sourced claim.",
                "source_ref_id": "source-1",
                "url": "https://example.com/source",
            }
        ],
        "status": "draft",
    }


def test_promote_and_index_published_article(tmp_path, monkeypatch):
    published_bus = tmp_path / "published"
    indexes = tmp_path / "indexes"
    monkeypatch.setattr(promote_module, "PUBLISHED_BUS", published_bus)

    article, output = promote_module.promote(_draft(), "human_approved")

    assert output.exists()
    assert article["status"] == "published"
    assert article["review_status"] == "human_approved"
    assert article["source_links"] == ["https://example.com/source"]
    assert article["citations"][0]["source_ref_id"] == "source-1"

    latest, count = build_indexes(published_bus, indexes)
    rows = [json.loads(line) for line in latest.read_text(encoding="utf-8").splitlines() if line]

    assert count == 1
    assert rows[0]["article_id"] == article["article_id"]
    assert (indexes / "articles" / f"{article['slug']}.json").exists()


def test_cli_refuses_publication_without_explicit_human_approval(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["promote_draft_to_published.py", "--draft-id", "draft-123"],
    )

    with pytest.raises(SystemExit, match="refusing to publish without --approve-human"):
        promote_module.main()
