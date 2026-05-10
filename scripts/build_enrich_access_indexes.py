#!/usr/bin/env python3
"""Build compact access/status indexes for news_enrich outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any

FETCH_FAILURE_STATUSES = {"failed", "blocked", "empty", "timeout"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_rfc3339(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                yield {
                    "schema_name": "scraped_article.v1",
                    "schema_status": "invalid",
                    "index_id": "",
                    "source_url": "",
                    "final_url": "",
                    "fetched_at": None,
                    "fetch_status": "failed",
                    "title": "",
                    "source": "",
                    "topic": "",
                    "text": "",
                    "text_hash": "",
                    "byte_size": 0,
                    "char_count": 0,
                    "language": None,
                    "error_code": "json_decode_error",
                    "error_message": f"{path}:{line_no}: {exc}",
                    "extractor": "unknown",
                    "meta": {"path": str(path), "line_no": line_no},
                }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_scraped_articles(bus_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not bus_dir.exists():
        return rows
    for path in sorted(bus_dir.glob("*.jsonl")):
        for row in _iter_jsonl(path):
            if str(row.get("schema_name") or "") != "scraped_article.v1":
                continue
            row = dict(row)
            row["_path"] = str(path)
            row["_fetched_dt"] = _parse_dt(row.get("fetched_at"))
            rows.append(row)
    rows.sort(key=lambda r: r.get("_fetched_dt") or datetime.min.replace(tzinfo=timezone.utc))
    return rows


def _compact_article(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    return {
        "index_id": str(row.get("index_id") or ""),
        "fetch_status": str(row.get("fetch_status") or ""),
        "title": str(row.get("title") or ""),
        "source": str(row.get("source") or ""),
        "topic": str(row.get("topic") or ""),
        "source_url": str(row.get("source_url") or ""),
        "final_url": str(row.get("final_url") or ""),
        "fetched_at": str(row.get("fetched_at") or ""),
        "char_count": int(row.get("char_count") or 0),
        "error_code": str(row.get("error_code") or ""),
        "error_message": str(row.get("error_message") or "")[:240],
        "http_status": meta.get("http_status"),
    }


def _status_for(metrics: dict[str, int]) -> str:
    if metrics["total_records"] == 0:
        return "no-data"
    if metrics["requests_24h"] == 0:
        return "stale"
    if metrics["success_24h"] == 0:
        return "degraded"
    if metrics["failed_24h"] or metrics["blocked_24h"] or metrics["empty_text_24h"] or metrics["timeout_24h"]:
        return "degraded"
    return "ok"


def build_enrich_index(storage_dir: Path, *, now: datetime | None = None, limit: int = 10) -> Path:
    now = now or _utc_now()
    bus_dir = storage_dir / "buses" / "scraped_article" / "v1"
    rows = _load_scraped_articles(bus_dir)
    cutoff = now - timedelta(hours=24)
    rows_24h = [r for r in rows if (r.get("_fetched_dt") is not None and r["_fetched_dt"] >= cutoff)]

    status_counts_24h = Counter(str(r.get("fetch_status") or "") for r in rows_24h)
    failures = [r for r in rows if str(r.get("fetch_status") or "") in FETCH_FAILURE_STATUSES]
    successes = [r for r in rows if str(r.get("fetch_status") or "") == "success"]
    successes_24h = [r for r in rows_24h if str(r.get("fetch_status") or "") == "success"]
    char_counts = [int(r.get("char_count") or 0) for r in successes_24h if int(r.get("char_count") or 0) > 0]

    source_failures = Counter(str(r.get("source") or "unknown") or "unknown" for r in rows_24h if str(r.get("fetch_status") or "") in FETCH_FAILURE_STATUSES)
    metrics = {
        "total_records": len(rows),
        "requests_24h": len(rows_24h),
        "success_24h": status_counts_24h.get("success", 0),
        "failed_24h": status_counts_24h.get("failed", 0),
        "blocked_24h": status_counts_24h.get("blocked", 0),
        "empty_text_24h": status_counts_24h.get("empty", 0),
        "timeout_24h": status_counts_24h.get("timeout", 0),
        "median_text_chars": int(median(char_counts)) if char_counts else 0,
    }

    payload = {
        "schema_name": "enrich_latest.v1",
        "schema_status": "experimental",
        "built_at": _to_rfc3339(now),
        "status": _status_for(metrics),
        "bus_dir": str(bus_dir),
        "metrics": metrics,
        "latest_successes": [_compact_article(r) for r in successes[-limit:]][::-1],
        "latest_failures": [_compact_article(r) for r in failures[-limit:]][::-1],
        "retry_candidates": [_compact_article(r) for r in failures[-limit:]][::-1],
        "top_sources_by_failure": [
            {"source": source, "failures_24h": count}
            for source, count in source_failures.most_common(limit)
        ],
    }

    out = storage_dir / "indexes" / "enrich_latest.json"
    _write_json(out, payload)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build news_enrich latest status/access index")
    parser.add_argument("--storage-dir", default="storage", help="Storage root containing buses/ and indexes/")
    parser.add_argument("--now", default=None, help="Override current time for tests, RFC3339/ISO format")
    parser.add_argument("--limit", type=int, default=10, help="Number of latest successes/failures to expose")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    now = _parse_dt(args.now) if args.now else None
    out = build_enrich_index(Path(args.storage_dir), now=now, limit=args.limit)
    payload = json.loads(out.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    print(
        f"wrote {out} status={payload['status']} total={metrics['total_records']} "
        f"requests_24h={metrics['requests_24h']} failures_24h={metrics['failed_24h'] + metrics['blocked_24h'] + metrics['empty_text_24h'] + metrics['timeout_24h']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
