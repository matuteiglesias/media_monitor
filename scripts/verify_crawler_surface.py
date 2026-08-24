#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen


@dataclass
class Response:
    body: str
    content_type: str = ""


def http_get(url: str, timeout: float = 20.0) -> Response:
    request = Request(url, headers={"User-Agent": "media-monitor-crawler-acceptance/1", "Accept": "*/*"})
    with urlopen(request, timeout=timeout) as response:
        return Response(response.read().decode("utf-8"), response.headers.get("Content-Type", ""))


def first_rss_link(xml_text: str) -> str | None:
    root = ET.fromstring(xml_text)
    item = root.find("./channel/item")
    if item is None:
        return None
    link = item.findtext("link")
    return link.strip() if link else None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(base_url: str, fetch: Callable[[str], Response] = http_get) -> dict:
    base = base_url.rstrip("/") + "/"
    robots_url = urljoin(base, "robots.txt")
    sitemap_url = urljoin(base, "sitemap.xml")
    feed_url = urljoin(base, "feed.xml")
    signals_url = urljoin(base, "signals.xml")
    author_url = urljoin(base, "authors/matias-iglesias")

    robots = fetch(robots_url).body
    require(f"Sitemap: {sitemap_url}" in robots, "robots.txt does not advertise canonical sitemap")

    sitemap = fetch(sitemap_url).body
    require(base.rstrip("/") in sitemap, "sitemap is missing canonical root")
    require(author_url in sitemap, "sitemap is missing canonical author page")

    editorial_feed = fetch(feed_url)
    require("rss" in editorial_feed.content_type.lower() or editorial_feed.body.startswith("<?xml"), "editorial feed is not XML/RSS")
    require("Análisis editorial human-approved" in editorial_feed.body, "editorial feed does not state approval semantics")
    require("Señal monitoreada de fuente externa" not in editorial_feed.body, "editorial feed is contaminated by monitored-signal copy")

    signal_feed = fetch(signals_url)
    require("rss" in signal_feed.content_type.lower() or signal_feed.body.startswith("<?xml"), "signal feed is not XML/RSS")
    require("no representa análisis editorial propio" in signal_feed.body, "signal feed does not state external-monitoring semantics")

    article_url = first_rss_link(editorial_feed.body)
    article_status = "no_approved_public_article"
    if article_url:
        html = fetch(article_url).body
        require("Análisis editorial · aprobado" in html, "approved article page lacks publication label")
        require('rel="canonical"' in html or "rel='canonical'" in html, "article is missing canonical link")
        require(f'href="{article_url}"' in html or f"href='{article_url}'" in html, "article canonical URL mismatch")
        require('property="og:title"' in html, "article is missing og:title")
        require('name="twitter:card"' in html and "summary_large_image" in html, "article is missing large Twitter card")
        require('application/ld+json' in html and "Article" in html, "article is missing Article JSON-LD")
        require(article_url in sitemap, "approved article is missing from sitemap")
        article_status = "verified"

    story_url = first_rss_link(signal_feed.body)
    story_status = "no_current_signal"
    if story_url:
        story_html = fetch(story_url).body
        require("Señal monitoreada · fuente externa" in story_html, "story page lost external-source label")
        require("no es" in story_html and "análisis editorial" in story_html, "story page no longer distinguishes monitoring from editorial")
        story_status = "verified"

    return {
        "schema_name": "crawler_surface_check.v1",
        "status": "ok",
        "base_url": base.rstrip("/"),
        "article_status": article_status,
        "story_status": story_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    try:
        report = verify(args.base_url)
    except Exception as exc:
        print(json.dumps({"schema_name": "crawler_surface_check.v1", "status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
