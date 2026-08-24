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
    publisher = (REPO_ROOT / "scripts" / "publish_news_site.sh").read_text(encoding="utf-8")

    invoked = {"refresh-data", "smoke:public-data"}
    for name in invoked:
        assert f"run {name}" in publisher or f"run --silent {name}" in publisher
        assert name in scripts


def test_freshness_notice_is_global_and_request_time() -> None:
    layout = (NEWS_SITE_ROOT / "app" / "layout.tsx").read_text(encoding="utf-8")
    route = (NEWS_SITE_ROOT / "app" / "api" / "health" / "route.ts").read_text(encoding="utf-8")

    assert 'export const dynamic = "force-dynamic"' in layout
    assert "<FreshnessNotice />" in layout
    assert "buildPublicationHealth" in route
    assert "published_article_count" in route
    assert "curated_signal_count" in route
    assert "story_context_count" in route
    assert '"Cache-Control": "no-store"' in route


def test_public_identity_is_single_sourced_across_runtime_and_public_docs() -> None:
    identity = json.loads((NEWS_SITE_ROOT / "config" / "public_identity.json").read_text(encoding="utf-8"))
    site = json.loads((REPO_ROOT / "sites" / "argentina-general.json").read_text(encoding="utf-8"))
    layout = (NEWS_SITE_ROOT / "app" / "layout.tsx").read_text(encoding="utf-8")
    mapper = (NEWS_SITE_ROOT / "lib" / "adapter" / "mappers.ts").read_text(encoding="utf-8")
    health = (NEWS_SITE_ROOT / "app" / "api" / "health" / "route.ts").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert identity["schema_name"] == "public_identity.v1"
    assert identity["public_outlet_url"] == "https://mediamonitor-psi.vercel.app"
    assert site["name"] == identity["outlet_name"]
    assert site["tagline"] == identity["outlet_tagline"]
    assert "PUBLIC_IDENTITY.public_outlet_url" in layout
    assert "alternates" in layout and "canonical" in layout
    assert "PUBLIC_IDENTITY.outlet_name" in mapper
    assert "canonical_url: PUBLIC_IDENTITY.public_outlet_url" in health
    for value in (identity["public_outlet_url"], identity["docs_url"], identity["repository_url"], identity["owner_url"]):
        assert value in readme
        assert value in docs


def test_prominent_public_claims_are_calibrated_to_evidence() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")

    assert "sistema desplegado y gobernado de inteligencia de noticias y publicación editorial" in readme
    assert "deployed governed news-intelligence and editorial" in docs
    assert "Working internal/prototype" not in readme
    assert "backend editorial semiautónomo" not in readme
    for text in (readme, docs):
        assert "freshness_status=FRESH" in text
        assert "is_current=true" in text
        assert "within_target=true" in text
    assert "no se enlaza todavía" in readme.lower()
    assert "actual publication approval remains intentionally human" in docs


def test_v4_outlet_adapter_separates_publication_curation_wire_and_story_context() -> None:
    mapper = (NEWS_SITE_ROOT / "lib" / "adapter" / "mappers.ts").read_text(encoding="utf-8")
    health = (NEWS_SITE_ROOT / "lib" / "publication_health.mjs").read_text(encoding="utf-8")
    assert "site_snapshot.v4" in mapper
    assert "publication: snapshot.publication" in mapper
    assert "articles: snapshot.articles" in mapper
    assert "story_contexts:" in mapper
    assert "curated:" in mapper
    assert "publication: { featured: null, latest: [] }" in mapper
    assert "findArticle" in mapper
    assert "findStoryContext" in mapper
    assert "site_snapshot.v4" in health
    assert "chronological wire" in health
    assert "context" in health


def test_homepage_makes_editorial_curated_and_chronological_layers_distinct() -> None:
    home = (NEWS_SITE_ROOT / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "Análisis editorial · aprobado" in home
    assert "Qué importa ahora" in home
    assert "Shortlist determinística de señales externas" in home
    assert "Estar seleccionado no convierte" in home
    assert "Cable cronológico de fuentes" in home
    assert "No hay análisis editorial aprobado publicado" in home
    assert "href={`/articles/${featured.slug}`}" in home
    assert "href={`/story/${item.index_id}`}" in home
    assert "curationReasonLabel" in home


def test_article_route_only_reads_published_article_projection() -> None:
    article_route = (NEWS_SITE_ROOT / "app" / "articles" / "[slug]" / "page.tsx").read_text(encoding="utf-8")
    assert "findArticle(params.slug)" in article_route
    assert "Análisis editorial · aprobado" in article_route
    assert "article.summary" in article_route
    assert "article.body_md" in article_route
    assert "article.citations" in article_route
    assert "article.source_links" in article_route
    assert "article.review_status" in article_route


def test_rich_story_page_uses_context_without_masquerading_as_editorial() -> None:
    story = (NEWS_SITE_ROOT / "app" / "story" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    assert "findStoryContext(params.id)" in story
    assert "Contexto de cobertura" in story
    assert "coverage_count" in story
    assert "source_count" in story
    assert "Cobertura relacionada" in story
    assert "curationReasonLabel" in story
    assert "Análisis aprobado relacionado" in story
    assert "relatedApprovedArticles" in story
    assert "No hay análisis editorial humanamente aprobado" in story
    assert "Señal monitoreada · fuente externa" in story
    assert "no es" in story and "análisis editorial" in story
    assert "no constituye aprobación" in story.lower()


def test_related_analysis_helper_only_accepts_human_approved_publication() -> None:
    helper = (NEWS_SITE_ROOT / "lib" / "story_relations.ts").read_text(encoding="utf-8")
    assert 'article?.schema_name === "published_article.v1"' in helper
    assert 'article?.status === "published"' in helper
    assert 'article?.review_status === "human_approved"' in helper
    assert "source_links.includes(story?.link)" in helper
    assert "context.group_ids.includes(article?.story_group_id)" in helper
    assert "article.topic === story?.topic" in helper
    for forbidden in ("news_article_draft", "editorial_latest", "promptflow"):
        assert forbidden not in helper.lower()


def test_discovery_surfaces_keep_analysis_and_monitored_signals_separate() -> None:
    sitemap = (NEWS_SITE_ROOT / "app" / "sitemap.ts").read_text(encoding="utf-8")
    robots = (NEWS_SITE_ROOT / "app" / "robots.ts").read_text(encoding="utf-8")
    feeds = (NEWS_SITE_ROOT / "lib" / "feeds.ts").read_text(encoding="utf-8")
    editorial_feed = (NEWS_SITE_ROOT / "app" / "feed.xml" / "route.ts").read_text(encoding="utf-8")
    signal_feed = (NEWS_SITE_ROOT / "app" / "signals.xml" / "route.ts").read_text(encoding="utf-8")
    layout = (NEWS_SITE_ROOT / "app" / "layout.tsx").read_text(encoding="utf-8")

    assert "MetadataRoute.Sitemap" in sitemap
    assert "outlet.articles" in sitemap and "outlet.signals?.latest" in sitemap
    assert "MetadataRoute.Robots" in robots and 'disallow: ["/api/"]' in robots
    assert 'article?.schema_name === "published_article.v1"' in feeds
    assert 'article?.review_status === "human_approved"' in feeds
    assert "No incluye titulares monitoreados de terceros" in feeds
    assert "no representa análisis editorial propio" in feeds.lower()
    assert "approvedAnalysisRss" in editorial_feed
    assert "monitoredSignalsRss" in signal_feed
    assert '"/feed.xml"' in layout and '"/signals.xml"' in layout


def test_other_signal_routes_remain_explicit_external_monitoring() -> None:
    latest = (NEWS_SITE_ROOT / "app" / "latest" / "page.tsx").read_text(encoding="utf-8")
    topic = (NEWS_SITE_ROOT / "app" / "topic" / "[topic]" / "page.tsx").read_text(encoding="utf-8")
    assert "Señales monitoreadas · fuentes externas" in latest
    assert "no análisis editorial propio" in latest
    assert "Señales monitoreadas · fuentes externas" in topic
