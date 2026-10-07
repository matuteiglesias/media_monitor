from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .digest import build_digest_input, render_digest, validate_watch_config, annotate
from .enrichment import MediaEnrichmentStore
from .store import MediaWatchStore, utc_now
from .summary import DEFAULT_GEMINI_MODEL, GeminiSummaryProvider, ensure_summary


def _round_robin_candidates(store: MediaWatchStore, source_ids: list[str], limit_per_source: int) -> list[dict]:
    buckets = {
        source_id: [item for item in store.list_items() if item["source_id"] == source_id][:limit_per_source]
        for source_id in source_ids
    }
    rows: list[dict] = []
    for index in range(limit_per_source):
        for source_id in source_ids:
            bucket = buckets[source_id]
            if index < len(bucket):
                rows.append(bucket[index])
    return rows


def run(*, store_root: Path, config_path: Path, output_root: Path, model: str, min_successes: int, limit_per_source: int) -> dict:
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is required")
    config = validate_watch_config(config_path)
    store = MediaWatchStore(store_root)
    enrichment = MediaEnrichmentStore(store)
    source_ids = sorted(source["source_id"] for source in config["sources"])
    candidates = _round_robin_candidates(store, source_ids, limit_per_source)
    if not candidates:
        raise RuntimeError("no live media candidates are available")

    provider = GeminiSummaryProvider(api_key=gemini_key, model=model)
    attempts: list[dict] = []
    successes: list[dict] = []
    for item in candidates:
        if len(successes) >= min_successes:
            break
        before_attempts = len(enrichment.list_summary_attempts(item["item_uid"]))
        try:
            artifact, state = ensure_summary(
                store,
                item_uid=item["item_uid"],
                provider=provider,
            )
        except Exception as exc:
            after = enrichment.list_summary_attempts(item["item_uid"])
            attempts.append({
                "item_uid": item["item_uid"],
                "source_id": item["source_id"],
                "outcome": "failed",
                "error_class": type(exc).__name__,
                "summary_count": len(enrichment.list_summaries(item["item_uid"])),
                "new_attempt_count": len(after) - before_attempts,
                "latest_state": after[0]["state"] if after else None,
                "retryable": after[0]["retryable"] if after else None,
            })
            continue
        attempts.append({
            "item_uid": item["item_uid"],
            "source_id": item["source_id"],
            "outcome": state,
            "summary_id": artifact["summary_id"],
        })
        successes.append({
            "item_uid": item["item_uid"],
            "source_id": item["source_id"],
            "summary_id": artifact["summary_id"],
        })

    if len(successes) < min_successes:
        raise RuntimeError(f"serial live summary acceptance produced {len(successes)} successes; need {min_successes}")

    cache_replays = []
    for success in successes:
        artifact, state = ensure_summary(
            store,
            item_uid=success["item_uid"],
            provider=provider,
        )
        if state != "existing" or artifact["summary_id"] != success["summary_id"]:
            raise RuntimeError("summary replay did not reuse the governed cache")
        cache_replays.append({"item_uid": success["item_uid"], "state": state})

    rows = build_digest_input(config, store, limit_per_channel=max(limit_per_source, 5))
    by_id = {row["item_uid"]: row for row in rows}
    for success in successes:
        row = by_id.get(success["item_uid"])
        if not row or row.get("summary_id") != success["summary_id"] or not row.get("summary"):
            raise RuntimeError("successful summary is not visible in deterministic digest input")

    output_root.mkdir(parents=True, exist_ok=True)
    annotations = [annotate(row) for row in rows]
    digest_id = "live-summary-acceptance"
    digest_root = output_root / "digest"
    if digest_root.exists():
        raise RuntimeError(f"digest output already exists: {digest_root}")
    manifest = render_digest(
        config,
        rows,
        annotations,
        output_root=digest_root,
        digest_id=digest_id,
        since=None,
    )
    digest_text = (digest_root / digest_id / "digest.md").read_text(encoding="utf-8")
    for success in successes:
        summary = enrichment.list_summaries(success["item_uid"])[0]["summary"]
        if summary not in digest_text:
            raise RuntimeError("governed summary text is absent from rendered deterministic digest")

    receipt = {
        "contract": "media-monitor.live-summary-acceptance@1",
        "observed_at": utc_now(),
        "model": model,
        "serialized": True,
        "requested_min_successes": min_successes,
        "successes": successes,
        "attempts": attempts,
        "cache_replays": cache_replays,
        "digest_manifest": manifest,
        "acceptance_green": True,
    }
    (output_root / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serial live Gemini summary acceptance over governed Media Monitor state")
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("config/media_watch/watches/matias-knowledge-channels.yaml"))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model", default=os.environ.get("GEMINI_MODEL", "") or DEFAULT_GEMINI_MODEL)
    parser.add_argument("--min-successes", type=int, default=2)
    parser.add_argument("--limit-per-source", type=int, default=3)
    args = parser.parse_args(argv)
    receipt = run(
        store_root=args.store_root,
        config_path=args.config,
        output_root=args.output_root,
        model=args.model,
        min_successes=args.min_successes,
        limit_per_source=args.limit_per_source,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
