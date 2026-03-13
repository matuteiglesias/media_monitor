from backend.models import ScrapeRecordV1, CitationV1, ArticleDraftV1, ArticleV1
from datetime import datetime, timezone

def _now(): return datetime.now(timezone.utc)

def test_scrape_record_ok():
    s = ScrapeRecordV1(
        index_id="ABCDEFGHIJ",
        digest_id_hour="20250624T16",
        topic="Economia",
        source="EL PAIS",
        title="Titulo",
        published=_now(),
        original_link="https://news.google.com/abc",
        final_url="https://elpais.com/x",
        redirects=[],
        status=200,
        fetch_latency_ms=123,
        raw_html_len=10000,
        main_text="hola"*400,
        main_text_len=1600,
        lang="es",
        canonical_url="https://elpais.com/x",
        extraction_engine="trafilatura",
        quality={},
        fetched_at=_now(),
    )
    assert s.index_id

def test_article_roundtrip():
    c = CitationV1(title="t", source="s", url="https://x")
    a = ArticleV1(
        article_id="ART-1",
        slug="nota-1",
        lang="es",
        headline="h",
        body_html="<p>ok</p>",
        topic="Economia",
        tags=["x"],
        citations=[c],
        published_at=_now(),
        first_seen_at=_now(),
        cluster_id="clu-1"
    )
    j = a.model_dump_json()
    assert '"schema_version":"ArticleV1"' in j
