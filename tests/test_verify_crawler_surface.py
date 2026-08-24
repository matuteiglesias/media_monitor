from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_crawler_surface import Response, verify


BASE = "https://media.example.test"
ARTICLE = f"{BASE}/articles/approved-analysis"
STORY = f"{BASE}/story/signal-1"


def rss(title: str, description: str, link: str | None = None) -> str:
    item = f"<item><title>Item</title><link>{link}</link></item>" if link else ""
    return f'<?xml version="1.0"?><rss><channel><title>{title}</title><description>{description}</description>{item}</channel></rss>'


def fetcher(mapping):
    def fetch(url: str) -> Response:
        return mapping[url]
    return fetch


def base_mapping(article: bool = True):
    editorial = rss("Analysis", "Análisis editorial human-approved de Media Monitor.", ARTICLE if article else None)
    signals = rss("Signals", "Esta fuente no representa análisis editorial propio.", STORY)
    mapping = {
        f"{BASE}/robots.txt": Response(f"User-agent: *\nSitemap: {BASE}/sitemap.xml\n"),
        f"{BASE}/sitemap.xml": Response(f"<urlset><loc>{BASE}</loc><loc>{BASE}/authors/matias-iglesias</loc>{f'<loc>{ARTICLE}</loc>' if article else ''}</urlset>", "application/xml"),
        f"{BASE}/feed.xml": Response(editorial, "application/rss+xml"),
        f"{BASE}/signals.xml": Response(signals, "application/rss+xml"),
        STORY: Response("<html>Señal monitoreada · fuente externa — este registro no es análisis editorial.</html>", "text/html"),
    }
    if article:
        mapping[ARTICLE] = Response(
            f'<html><head><link rel="canonical" href="{ARTICLE}"/><meta property="og:title" content="Approved"/><meta name="twitter:card" content="summary_large_image"/><script type="application/ld+json">{{"@type":"Article"}}</script></head><body>Análisis editorial · aprobado</body></html>',
            "text/html",
        )
    return mapping


def test_crawler_surface_verifies_article_and_story_semantics():
    report = verify(BASE, fetcher(base_mapping()))
    assert report["status"] == "ok"
    assert report["article_status"] == "verified"
    assert report["story_status"] == "verified"


def test_crawler_surface_allows_truthful_zero_article_state():
    report = verify(BASE, fetcher(base_mapping(article=False)))
    assert report["article_status"] == "no_approved_public_article"
    assert report["story_status"] == "verified"


def test_editorial_feed_contamination_fails():
    mapping = base_mapping()
    mapping[f"{BASE}/feed.xml"] = Response(
        rss("Analysis", "Análisis editorial human-approved de Media Monitor. Señal monitoreada de fuente externa", ARTICLE),
        "application/rss+xml",
    )
    try:
        verify(BASE, fetcher(mapping))
    except ValueError as exc:
        assert "contaminated" in str(exc)
    else:
        assert False
