from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]
NEWS_SITE_ROOT = REPO_ROOT / "apps" / "news_site"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_editorial_identity_v1_is_schema_valid_and_matches_public_identity() -> None:
    identity = read_json(NEWS_SITE_ROOT / "config" / "editorial_identity.json")
    public = read_json(NEWS_SITE_ROOT / "config" / "public_identity.json")
    schema = read_json(REPO_ROOT / "contracts" / "schemas" / "editorial_identity.v1.json")

    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(identity),
        key=lambda error: list(error.path),
    )
    assert not errors, "; ".join(error.message for error in errors)
    assert identity["schema_name"] == "editorial_identity.v1"
    assert identity["outlet_name"] == public["outlet_name"]
    assert identity["editor"]["name"] == "Matías Iglesias"
    assert identity["editor"]["contact"]["website"] == public["owner_url"]
    assert identity["endorsement_line"].endswith("por Matías Iglesias")
    assert identity["routes"] == {
        "about": "/about",
        "methodology": "/methodology",
        "journalists": "/journalists",
    }


def test_default_editor_attribution_does_not_mutate_published_article_v1() -> None:
    article_schema = read_json(REPO_ROOT / "contracts" / "schemas" / "published_article.v1.json")
    article_route = (
        NEWS_SITE_ROOT / "app" / "articles" / "[slug]" / "page.tsx"
    ).read_text(encoding="utf-8")
    homepage = (NEWS_SITE_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")

    assert "author" not in article_schema["properties"]
    assert "EDITORIAL_IDENTITY" in article_route
    assert "Por <Link" in article_route
    assert "editor.name" in article_route
    assert "article.author" not in article_route
    assert "EDITORIAL_IDENTITY.endorsement_line" in homepage
