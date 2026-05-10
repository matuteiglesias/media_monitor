from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_enrich_access_indexes.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _row(index_id: str, status: str, fetched_at: str, *, source: str = "Example", char_count: int = 100) -> dict:
    return {
        "schema_name": "scraped_article.v1",
        "schema_status": "experimental",
        "index_id": index_id,
        "source_url": f"https://example.com/{index_id}",
        "final_url": f"https://example.com/{index_id}",
        "fetched_at": fetched_at,
        "fetch_status": status,
        "title": f"Story {index_id}",
        "source": source,
        "topic": "Economy",
        "text": "hello world" if status == "success" else "",
        "text_hash": "abc" if status == "success" else "",
        "byte_size": 42,
        "char_count": char_count if status == "success" else 0,
        "language": None,
        "error_code": "" if status == "success" else status,
        "error_message": "" if status == "success" else f"{status} happened",
        "extractor": "requests_basic",
        "meta": {"http_status": 200 if status == "success" else 403},
    }


def test_build_enrich_access_indexes_with_bus_rows(tmp_path: Path):
    storage = tmp_path / "storage"
    _write_jsonl(
        storage / "buses" / "scraped_article" / "v1" / "scraped_article_2026-05-10.jsonl",
        [
            _row("OK1", "success", "2026-05-10T10:00:00Z", char_count=120),
            _row("FAIL1", "failed", "2026-05-10T11:00:00Z", source="Reuters"),
            _row("BLOCK1", "blocked", "2026-05-10T12:00:00Z", source="Reuters"),
        ],
    )

    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--storage-dir", str(storage), "--now", "2026-05-10T13:00:00Z"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "status=degraded" in out.stdout
    latest = storage / "indexes" / "enrich_latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["status"] == "degraded"
    assert payload["metrics"]["total_records"] == 3
    assert payload["metrics"]["requests_24h"] == 3
    assert payload["metrics"]["success_24h"] == 1
    assert payload["metrics"]["failed_24h"] == 1
    assert payload["metrics"]["blocked_24h"] == 1
    assert payload["metrics"]["median_text_chars"] == 120
    assert payload["latest_successes"][0]["index_id"] == "OK1"
    assert [row["index_id"] for row in payload["latest_failures"]] == ["BLOCK1", "FAIL1"]
    assert payload["retry_candidates"][0]["fetch_status"] == "blocked"
    assert payload["top_sources_by_failure"] == [{"source": "Reuters", "failures_24h": 2}]


def test_build_enrich_access_indexes_no_data(tmp_path: Path):
    storage = tmp_path / "storage"

    subprocess.run(
        [sys.executable, str(SCRIPT), "--storage-dir", str(storage), "--now", "2026-05-10T13:00:00Z"],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads((storage / "indexes" / "enrich_latest.json").read_text(encoding="utf-8"))
    assert payload["status"] == "no-data"
    assert payload["metrics"]["total_records"] == 0
    assert payload["latest_successes"] == []
    assert payload["latest_failures"] == []
