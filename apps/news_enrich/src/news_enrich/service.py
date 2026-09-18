"""On-demand article enrichment service boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html as html_lib
import json
import re
from typing import Any, Callable, Iterable

import requests

from .records import ScrapedArticle
from .requests import EnrichRequest

USER_AGENT = "media-monitor-news-enrich/0.1 (+https://media-monitor.local)"
ARTICLE_TYPES = {
    "Article",
    "NewsArticle",
    "ReportageNewsArticle",
    "AnalysisNewsArticle",
    "OpinionNewsArticle",
}


@dataclass(frozen=True)
class FetchResult:
    """Raw fetch evidence captured before text normalization."""

    status_code: int | None
    final_url: str | None
    html: str
    byte_size: int
    fetched_at: datetime
    error_code: str = ""
    error_message: str = ""


def _plain_text(fragment: str) -> str:
    """Strip non-content markup and normalize a HTML fragment to compact text."""
    text = re.sub(r"(?is)<!--.*?-->", " ", fragment)
    text = re.sub(
        r"(?is)<(script|style|noscript|svg|nav|aside|footer|form|button).*?>.*?</\1>",
        " ",
        text,
    )
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    text = re.sub(r"(?i)</(?:p|div|li|h[1-6]|section)>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(html: str) -> str:
    """Backward-compatible generic HTML-to-text fallback."""
    return _plain_text(html)


def _walk_json(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def _article_jsonld_text(document: str) -> str:
    blocks = re.findall(
        r"(?is)<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        document,
    )
    for raw in blocks:
        try:
            parsed = json.loads(html_lib.unescape(raw).strip())
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _walk_json(parsed):
            node_type = node.get("@type")
            types = {node_type} if isinstance(node_type, str) else set(node_type or [])
            if not (types & ARTICLE_TYPES):
                continue
            article_body = node.get("articleBody")
            if isinstance(article_body, str):
                text = _plain_text(article_body)
                if text:
                    return text
    return ""


def extract_text(document: str) -> tuple[str, str]:
    """Prefer publisher article semantics before falling back to whole-page text."""
    jsonld = _article_jsonld_text(document)
    if jsonld:
        return jsonld, "jsonld_article"

    article_fragments = re.findall(r"(?is)<article\b[^>]*>(.*?)</article>", document)
    if article_fragments:
        candidates = [_plain_text(fragment) for fragment in article_fragments]
        best = max(candidates, key=len, default="")
        if best:
            return best, "html_article"

    main_fragments = re.findall(r"(?is)<main\b[^>]*>(.*?)</main>", document)
    if main_fragments:
        candidates = [_plain_text(fragment) for fragment in main_fragments]
        best = max(candidates, key=len, default="")
        if best:
            return best, "html_main"

    return normalize_text(document), "requests_basic"


def fetch_article(url: str, *, timeout: int = 20) -> FetchResult:
    """Fetch a URL with requests and return structured fetch evidence."""
    fetched_at = datetime.now(timezone.utc)
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    )
    html = response.text or ""
    return FetchResult(
        status_code=response.status_code,
        final_url=response.url,
        html=html,
        byte_size=len(response.content or html.encode("utf-8")),
        fetched_at=fetched_at,
    )


def _status_from_fetch(result: FetchResult, text: str) -> str:
    if result.error_code:
        return "timeout" if result.error_code == "timeout" else "failed"
    if result.status_code in {401, 403, 429, 451}:
        return "blocked"
    if result.status_code is not None and result.status_code >= 400:
        return "failed"
    if not text:
        return "empty"
    return "success"


def _fetch_error(exc: requests.RequestException, url: str) -> FetchResult:
    code = "timeout" if isinstance(exc, requests.Timeout) else exc.__class__.__name__
    return FetchResult(
        status_code=None,
        final_url=url,
        html="",
        byte_size=0,
        fetched_at=datetime.now(timezone.utc),
        error_code=code,
        error_message=str(exc),
    )


def enrich_one(
    request: EnrichRequest,
    *,
    timeout: int = 20,
    fetcher: Callable[[str], FetchResult] | None = None,
) -> ScrapedArticle:
    """Fetch and normalize one article reference into a structured draft record."""
    fetch = fetcher or (lambda url: fetch_article(url, timeout=timeout))
    try:
        result = fetch(str(request.url))
    except requests.RequestException as exc:
        result = _fetch_error(exc, str(request.url))

    text, extractor = extract_text(result.html) if result.html else ("", "requests_basic")
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
    fetch_status = _status_from_fetch(result, text)

    return ScrapedArticle(
        index_id=request.index_id,
        source_url=request.url,
        final_url=result.final_url or str(request.url),
        fetched_at=result.fetched_at,
        fetch_status=fetch_status,
        title=request.title,
        source=request.source,
        topic=request.topic,
        text=text,
        text_hash=text_hash,
        byte_size=result.byte_size,
        char_count=len(text),
        error_code=result.error_code,
        error_message=result.error_message,
        extractor=extractor,
        meta={
            "http_status": result.status_code,
            "digest_at": request.digest_at,
            "priority": request.priority,
            "request_metadata": request.metadata,
        },
    )
