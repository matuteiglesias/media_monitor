"""Producer-owned projection from governed media summaries to generic evidence JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .enrichment import MediaEnrichmentStore
from .store import MediaWatchStore, canonical_json, sha256_text

CONTRACT = "producer-local:media-monitor.evidence-jsonl@1"


def _record(store: MediaWatchStore, summary: dict) -> dict:
    item = store.load_item(summary["item_uid"])
    if item is None:
        raise ValueError(f"summary references missing item {summary['item_uid']}")
    source = store.load_source_state(item["source_id"]) or {}
    key_points = list(summary.get("key_points") or [])
    body_parts = [summary["summary"]]
    if key_points:
        body_parts.extend(["", "Key points:", *[f"- {point}" for point in key_points]])
    text = "\n".join(body_parts).strip()
    return {
        "title": item["title"],
        "summary": summary["summary"],
        "text": text,
        "tags": [
            "media-monitor",
            "youtube",
            "governed-summary",
            item["source_id"],
        ],
        "timestamp": item["published_at"],
        "source_ref": summary["summary_id"],
        "text_sha256": sha256_text(text),
        "meta": {
            "producer": "media-monitor",
            "domain": "media",
            "stage": "governed_summary",
            "artifact_family": "media_summary",
            "item_uid": item["item_uid"],
            "source_id": item["source_id"],
            "channel_name": source.get("channel_title") or source.get("display_name"),
            "canonical_url": item["canonical_url"],
            "published_at": item["published_at"],
            "summary_id": summary["summary_id"],
            "key_points": key_points,
            "summary_generated_at": summary["generated_at"],
            "provider": summary["provider"],
            "model": summary["model"],
            "prompt_version": summary["prompt_version"],
            "adapter_version": summary["adapter_version"],
            "processing_mode": summary["processing_mode"],
            "provenance": {"source_ref": summary["summary_id"]},
        },
    }


def export_evidence(store_root: Path, output: Path) -> dict:
    store = MediaWatchStore(store_root)
    enrichment = MediaEnrichmentStore(store)
    records = [_record(store, summary) for summary in enrichment.list_summaries()]
    records.sort(key=lambda row: (row["timestamp"], row["source_ref"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_json(record) + "\n" for record in records)
    output.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    receipt = {
        "contract": CONTRACT,
        "records": len(records),
        "output_sha256": digest,
        "source_refs": [record["source_ref"] for record in records],
    }
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export governed Media Monitor summaries as generic JSONL evidence")
    parser.add_argument("--store-root", type=Path, default=Path("data/canonical/media_watch"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = export_evidence(args.store_root, args.output)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
