"""On-demand article enrichment service boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Callable

import requests

from .records import ScrapedArticle
from .requests import EnrichRequest

USER_AGENT = "media-monitor-news-enrich/0.1 (+https://media-monitor.local)"


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


def normalize_text(html: str) -> str:
    """Convert fetched HTML/text into a compact text/plain draft extraction."""
    without_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return re.sub(r"\s+", " ", without_tags).strip()


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

    text = normalize_text(result.html) if result.html else ""
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
        meta={
            "http_status": result.status_code,
            "digest_at": request.digest_at,
            "priority": request.priority,
            "request_metadata": request.metadata,
        },
    )
