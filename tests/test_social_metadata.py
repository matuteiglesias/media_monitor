from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps" / "news_site"


def test_article_social_metadata_and_image_are_article_specific_and_edge_safe():
    seo = (SITE / "lib" / "seo.ts").read_text(encoding="utf-8")
    image = (SITE / "app" / "articles" / "[slug]" / "opengraph-image.tsx").read_text(encoding="utf-8")
    materializer = (SITE / "scripts" / "materialize_article_social_cards.mjs").read_text(encoding="utf-8")
    package = (SITE / "package.json").read_text(encoding="utf-8")

    assert 'card: "summary_large_image"' in seo
    assert "opengraph-image" in seo
    assert "width: 1200" in seo and "height: 630" in seo
    assert "ImageResponse" in image
    assert 'runtime = "edge"' in image
    assert "article_social_cards.json" in image
    assert "SOCIAL_CARDS.articles[params.slug]" in image
    assert "article?.title" in image
    assert "EDITORIAL_IDENTITY.editor.name" in image
    assert "análisis aprobado" in image.lower()
    assert "adapter/mappers" not in image
    assert "node:fs" not in image and "node:path" not in image

    assert "site_snapshot.v4" in materializer
    assert 'article.status !== "published"' in materializer
    assert 'article.review_status !== "human_approved"' in materializer
    assert "article_social_cards.v1" in materializer
    assert "materialize_article_social_cards.mjs" in package


def test_runtime_ci_executes_real_next_production_build():
    workflow = (ROOT / ".github" / "workflows" / "runtime-ci.yml").read_text(encoding="utf-8")
    assert "site_snapshot.v4.example.json" in workflow
    assert "DIGEST_AT=20260824T18 npm run build" in workflow


def test_scheduled_production_runs_black_box_crawler_acceptance():
    workflow = (ROOT / ".github" / "workflows" / "scheduled-publication.yml").read_text(encoding="utf-8")
    verifier = (ROOT / "scripts" / "verify_crawler_surface.py").read_text(encoding="utf-8")

    assert "Verify crawler, feed and social-card surface" in workflow
    assert "verify_crawler_surface.py" in workflow
    assert "crawler_surface_check_latest.json" in workflow
    assert "robots.txt" in verifier
    assert "sitemap.xml" in verifier
    assert "feed.xml" in verifier and "signals.xml" in verifier
    assert "twitter:card" in verifier and "og:title" in verifier
    assert "Señal monitoreada · fuente externa" in verifier
