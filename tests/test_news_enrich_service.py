import json
from datetime import datetime, timezone
from pathlib import Path

from news_enrich.bus_writer import validate_scraped_article, write_scraped_article
from news_enrich.requests import EnrichRequest
from news_enrich.service import FetchResult, enrich_one


def _fake_fetcher(url: str) -> FetchResult:
    return FetchResult(
        status_code=200,
        final_url=url,
        html="<html><head><style>.x{}</style></head><body><h1>Hello</h1><script>x()</script><p>World</p></body></html>",
        byte_size=100,
        fetched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
    )


def test_enrich_one_returns_schema_valid_scraped_article():
    request = EnrichRequest(index_id="TEST123", url="https://example.com/story", title="Story")

    record = enrich_one(request, fetcher=_fake_fetcher)

    assert record.schema_name == "scraped_article.v1"
    assert record.schema_status == "experimental"
    assert record.fetch_status == "success"
    assert record.index_id == "TEST123"
    assert record.title == "Story"
    assert record.text == "Hello World"
    assert record.char_count == len("Hello World")
    assert record.text_hash
    assert record.meta["http_status"] == 200
    validate_scraped_article(record)


def test_write_scraped_article_validates_and_appends_bus_record(tmp_path: Path):
    record = enrich_one(
        EnrichRequest(index_id="TEST123", url="https://example.com/story", title="Story"),
        fetcher=_fake_fetcher,
    )
    bus_path = tmp_path / "scraped_article.v1.jsonl"

    written_path = write_scraped_article(record, path=bus_path)

    assert written_path == bus_path
    rows = [json.loads(line) for line in bus_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["schema_name"] == "scraped_article.v1"
    assert rows[0]["schema_status"] == "experimental"
    validate_scraped_article(rows[0])


def test_worker_handle_one_delegates_to_service_without_external_fetch(tmp_path: Path):
    from news_enrich.worker_scrape import handle_one

    job = {
        "work_key": "WORK123",
        "payload": {
            "link": "https://example.com/story",
            "title": "Worker story",
            "source": "Example",
        },
    }
    bus_path = tmp_path / "bus.jsonl"
    mirror_path = tmp_path / "mirror.jsonl"

    record = handle_one(
        job,
        fetcher=_fake_fetcher,
        bus_path=bus_path,
        scrape_mirror_path=mirror_path,
    )

    assert record.ok
    assert record.index_id == "WORK123"
    assert record.title == "Worker story"
    assert bus_path.exists()
    assert mirror_path.exists()
    bus_rows = [json.loads(line) for line in bus_path.read_text(encoding="utf-8").splitlines()]
    mirror_rows = [json.loads(line) for line in mirror_path.read_text(encoding="utf-8").splitlines()]
    assert bus_rows == mirror_rows
    validate_scraped_article(bus_rows[0])


def test_worker_service_error_describes_retry_reason():
    from news_enrich.worker_scrape import service_error

    record = enrich_one(
        EnrichRequest(index_id="TEST123", url="https://example.com/story"),
        fetcher=lambda url: FetchResult(
            status_code=403,
            final_url=url,
            html="blocked",
            byte_size=7,
            fetched_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        ),
    )

    assert not record.ok
    assert "blocked" in service_error(record)
