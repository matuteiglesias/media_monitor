from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NEWS_SITE_ROOT = REPO_ROOT / "apps" / "news_site"


def test_publish_script_npm_commands_are_owned_by_news_site() -> None:
    package = json.loads((NEWS_SITE_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    expected = {
        "refresh-data": "node scripts/refresh_public_data.mjs",
        "smoke:public-data": "node scripts/validate_public_data.mjs",
    }

    for name, command in expected.items():
        assert scripts.get(name) == command
        script_path = NEWS_SITE_ROOT / command.removeprefix("node ")
        assert script_path.is_file(), f"{name} points to missing file: {script_path}"


def test_shell_publisher_only_invokes_declared_news_site_scripts() -> None:
    package = json.loads((NEWS_SITE_ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]
    publisher = (REPO_ROOT / "scripts" / "publish_news_site.sh").read_text(
        encoding="utf-8"
    )

    invoked = {"refresh-data", "smoke:public-data"}
    for name in invoked:
        assert f"run {name}" in publisher or f"run --silent {name}" in publisher
        assert name in scripts


def test_freshness_notice_is_global_and_request_time() -> None:
    layout = (NEWS_SITE_ROOT / "app" / "layout.tsx").read_text(encoding="utf-8")
    route = (NEWS_SITE_ROOT / "app" / "api" / "health" / "route.ts").read_text(
        encoding="utf-8"
    )

    assert 'export const dynamic = "force-dynamic"' in layout
    assert "<FreshnessNotice />" in layout
    assert "buildPublicationHealth" in route
    assert "published_article_count" in route
    assert '"Cache-Control": "no-store"' in route


def test_public_identity_is_single_sourced_across_runtime_and_root_readme() -> None:
    identity = json.loads(
        (NEWS_SITE_ROOT / "config" / "public_identity.json").read_text(encoding="utf-8")
    )
    site = json.loads((REPO_ROOT / "sites" / "argentina-general.json").read_text(encoding="utf-8"))
    layout = (NEWS_SITE_ROOT / "app" / "layout.tsx").read_text(encoding="utf-8")
    mapper = (NEWS_SITE_ROOT / "lib" / "adapter" / "mappers.ts").read_text(encoding="utf-8")
    health = (NEWS_SITE_ROOT / "app" / "api" / "health" / "route.ts").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert identity["schema_name"] == "public_identity.v1"
    assert identity["public_outlet_url"] == "https://mediamonitor-psi.vercel.app"
    assert site["name"] == identity["outlet_name"]
    assert site["tagline"] == identity["outlet_tagline"]
    assert "PUBLIC_IDENTITY.public_outlet_url" in layout
    assert "alternates" in layout and "canonical" in layout
    assert "PUBLIC_IDENTITY.outlet_name" in mapper
    assert "canonical_url: PUBLIC_IDENTITY.public_outlet_url" in health
    for value in (
        identity["public_outlet_url"],
        identity["docs_url"],
        identity["repository_url"],
        identity["owner_url"],
    ):
        assert value in readme


def test_v2_outlet_adapter_separates_publication_from_signals() -> None:
    mapper = (NEWS_SITE_ROOT / "lib" / "adapter" / "mappers.ts").read_text(
        encoding="utf-8"
    )
    health = (NEWS_SITE_ROOT / "lib" / "publication_health.mjs").read_text(
        encoding="utf-8"
    )
    assert 'snapshot?.schema_name === "site_snapshot.v2"' in mapper
    assert "publication: snapshot.publication" in mapper
    assert "articles: snapshot.articles" in mapper
    assert "signals: snapshot.signals" in mapper
    assert "publication: { featured: null, latest: [] }" in mapper
    assert "findArticle" in mapper
    assert 'snapshot?.schema_name === "site_snapshot.v2"' in health
    assert "snapshot?.signals" in health


def test_homepage_makes_editorial_and_external_layers_visibly_distinct() -> None:
    home = (NEWS_SITE_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "Análisis editorial · aprobado" in home
    assert "Señal monitoreada · fuente externa" in home
    assert "No hay análisis editorial aprobado publicado" in home
    assert "no se presentan" in home and "contenido propio" in home
    assert "href={`/articles/${featured.slug}`}" in home
    assert "href={`/story/${signals.hero.index_id}`}" in home


def test_article_route_only_reads_published_article_projection() -> None:
    article_route = (
        NEWS_SITE_ROOT / "app" / "articles" / "[slug]" / "page.tsx"
    ).read_text(encoding="utf-8")
    assert "findArticle(params.slug)" in article_route
    assert "Análisis editorial · aprobado" in article_route
    assert "article.summary" in article_route
    assert "article.body_md" in article_route
    assert "article.citations" in article_route
    assert "article.source_links" in article_route
    assert "article.review_status" in article_route


def test_signal_routes_do_not_masquerade_as_editorial_articles() -> None:
    story = (NEWS_SITE_ROOT / "app" / "story" / "[id]" / "page.tsx").read_text(
        encoding="utf-8"
    )
    latest = (NEWS_SITE_ROOT / "app" / "latest" / "page.tsx").read_text(
        encoding="utf-8"
    )
    topic = (
        NEWS_SITE_ROOT / "app" / "topic" / "[topic]" / "page.tsx"
    ).read_text(encoding="utf-8")
    assert "Señal monitoreada · fuente externa" in story
    assert "no es" in story and "análisis editorial" in story
    assert "Señales monitoreadas · fuentes externas" in latest
    assert "no análisis editorial propio" in latest
    assert "Señales monitoreadas · fuentes externas" in topic
