#!/usr/bin/env python3
"""Enrich only the deterministically selected signals for one configured outlet."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.news_enrich.src.news_enrich.bus_writer import (
    default_scraped_article_bus_path,
    write_scraped_article,
)
from apps.news_enrich.src.news_enrich.requests import EnrichRequest
from apps.news_enrich.src.news_enrich.service import FetchResult, enrich_one
from scripts.build_enrich_access_indexes import build_enrich_index
from scripts.outlet_runtime import resolve_outlet_runtime


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    yield value


def _existing_success_hashes(bus_dir: Path) -> set[tuple[str, str]]:
    hashes: set[tuple[str, str]] = set()
    if not bus_dir.exists():
        return hashes
    for path in sorted(bus_dir.glob("*.jsonl")):
        for row in _iter_jsonl(path):
            if row.get("schema_name") != "scraped_article.v1":
                continue
            if row.get("fetch_status") != "success":
                continue
            index_id = str(row.get("index_id") or "").strip()
            text_hash = str(row.get("text_hash") or "").strip()
            if index_id and text_hash:
                hashes.add((index_id, text_hash))
    return hashes


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def enrich_selected(
    *,
    repo_root: Path,
    site_id: str,
    digest_at: str,
    max_items: int = 10,
    minimum_successes: int = 5,
    minimum_text_chars: int = 500,
    timeout: int = 20,
    now: datetime | None = None,
    fetcher: Callable[[str], FetchResult] | None = None,
) -> dict[str, Any]:
    if max_items < 1:
        raise ValueError("max_items must be positive")
    if minimum_successes < 1 or minimum_successes > max_items:
        raise ValueError("minimum_successes must be positive and <= max_items")
    if minimum_text_chars < 1:
        raise ValueError("minimum_text_chars must be positive")

    runtime = resolve_outlet_runtime(repo_root, site_id)
    selection_path = runtime.indexes_dir / "editorial_selection_latest.json"
    if not selection_path.is_file():
        raise ValueError(f"missing editorial selection: {selection_path}")
    selection = _read_json(selection_path)
    if selection.get("schema_name") != "editorial_selection.v1":
        raise ValueError(f"{selection_path}: expected editorial_selection.v1")
    if selection.get("digest_at") != digest_at:
        raise ValueError(
            f"{selection_path}: digest_at={selection.get('digest_at')} does not match {digest_at}"
        )

    selected = list(selection.get("selected") or [])[:max_items]
    if len(selected) < minimum_successes:
        raise ValueError(
            f"selection contains {len(selected)} items; minimum_successes={minimum_successes}"
        )

    now = now or datetime.now(timezone.utc)
    bus_dir = runtime.scraped_article_bus_dir
    bus_path = default_scraped_article_bus_path(now, bus_dir=bus_dir)
    existing_hashes = _existing_success_hashes(bus_dir)

    results: list[dict[str, Any]] = []
    accepted_successes = 0
    written = 0
    skipped_unchanged = 0

    for item in selected:
        request = EnrichRequest(
            index_id=str(item.get("index_id") or ""),
            url=str(item.get("link") or ""),
            title=str(item.get("title") or ""),
            source=str(item.get("source") or ""),
            topic=str(item.get("topic") or ""),
            digest_at=digest_at,
            priority="normal",
            metadata={
                "selection_id": selection.get("selection_id"),
                "selection_rank": item.get("rank"),
                "selection_score": item.get("score"),
            },
        )
        record = enrich_one(request, timeout=timeout, fetcher=fetcher)
        quality_ok = bool(record.ok and record.char_count >= minimum_text_chars)
        unchanged = bool(
            quality_ok
            and record.text_hash
            and (record.index_id, record.text_hash) in existing_hashes
        )

        if quality_ok:
            accepted_successes += 1

        if unchanged:
            skipped_unchanged += 1
        else:
            write_scraped_article(record, path=bus_path)
            written += 1
            if record.ok and record.text_hash:
                existing_hashes.add((record.index_id, record.text_hash))

        results.append(
            {
                "index_id": record.index_id,
                "fetch_status": record.fetch_status,
                "quality_ok": quality_ok,
                "char_count": record.char_count,
                "text_hash": record.text_hash,
                "extractor": record.extractor,
                "source_url": str(record.source_url),
                "final_url": str(record.final_url) if record.final_url else None,
                "written": not unchanged,
                "skipped_unchanged": unchanged,
                "error_code": record.error_code,
            }
        )

    build_enrich_index(runtime.storage_dir, now=now, limit=max_items)
    status = "ok" if accepted_successes >= minimum_successes else "failed"
    report = {
        "schema_name": "selected_enrichment.v1",
        "status": status,
        "site_id": site_id,
        "digest_at": digest_at,
        "selection_id": selection.get("selection_id"),
        "selection_path": str(selection_path),
        "selected_count": len(selected),
        "attempted_count": len(results),
        "minimum_successes": minimum_successes,
        "minimum_text_chars": minimum_text_chars,
        "accepted_success_count": accepted_successes,
        "written_count": written,
        "skipped_unchanged_count": skipped_unchanged,
        "bus_path": str(bus_path),
        "results": results,
    }
    _atomic_json(
        runtime.storage_dir / "observability" / "selected_enrichment_latest.json",
        report,
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--max-items", type=int, default=10)
    parser.add_argument("--minimum-successes", type=int, default=5)
    parser.add_argument("--minimum-text-chars", type=int, default=500)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    try:
        report = enrich_selected(
            repo_root=args.repo_root,
            site_id=args.site_id,
            digest_at=args.digest_at,
            max_items=args.max_items,
            minimum_successes=args.minimum_successes,
            minimum_text_chars=args.minimum_text_chars,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(
            json.dumps(
                {"schema_name": "selected_enrichment.v1", "status": "failed", "error": str(exc)},
                ensure_ascii=False,
            )
        )
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
