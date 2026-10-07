from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .enrichment import MediaEnrichmentStore
from .monitor import load_config
from .store import MediaWatchStore, canonical_json, sha256_text, utc_now

DECISIONS = {"WATCH", "TRANSCRIPT_ENOUGH", "SKIP"}
LOW_VALUE_HINTS = (
    "programa completo", "música", "horóscopo", "clima", "trailer", "shorts", "viral",
    "playlist", "repetición", "replay",
)
VISUAL_HINTS = ("en vivo", "live", "reacción", "reaccion", "tutorial", "receta", "video", "documental")
TOPIC_TERMS = {
    "economy": ("economía", "economia", "inflación", "inflacion", "dólar", "dolar", "mercado", "empleo"),
    "politics": ("gobierno", "presidente", "congreso", "elecciones", "política", "politica", "ley", "ministro"),
    "culture": ("música", "musica", "cine", "libro", "cultura", "arte"),
    "technology": ("tecnología", "tecnologia", "internet", "software", "inteligencia artificial", "datos"),
    "science": ("ciencia", "investigación", "investigacion", "salud", "clima"),
}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _excerpt(value: str, limit: int = 900) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def validate_watch_config(config_path: Path) -> dict:
    config = load_config(config_path)
    watch = config.get("watch") or {}
    sources = config.get("sources") or []
    ids = [row.get("source_id") for row in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("watch source IDs must be unique")
    requested = watch.get("source_ids") or []
    if len(requested) != len(set(requested)):
        raise ValueError("watch source_ids must be unique")
    if set(requested) != set(ids):
        raise ValueError("watch source registry resolution did not produce exactly the configured source IDs")
    for source in sources:
        if source.get("platform") != "youtube" or source.get("source_kind") != "channel":
            raise ValueError(f"unsupported watch source {source.get('source_id')}")
        if not source.get("native_source_id") or not source.get("display_name") or not source.get("canonical_url"):
            raise ValueError(f"incomplete source identity {source.get('source_id')}")
        discovery = source.get("discovery") or {}
        if discovery.get("adapter") != "youtube_uploads":
            raise ValueError(f"source {source['source_id']} is not using youtube_uploads")
    return config


def materialize_channels(config: dict, store: MediaWatchStore, output_root: Path) -> dict:
    states = {row["source_id"]: row for row in store.list_source_states()}
    rows = []
    for source in config["sources"]:
        state = states.get(source["source_id"], {})
        groups = [name for name, members in (config.get("groups") or {}).items() if source["source_id"] in members]
        rows.append({
            "source_id": source["source_id"],
            "display_name": source["display_name"],
            "native_channel_id": source["native_source_id"],
            "canonical_url": source["canonical_url"],
            "groups": groups,
            "active": bool(source.get("active", True)),
            "last_observation": state.get("last_success_at") or state.get("last_attempt_at"),
            "latest_observed_video": next((item["item_uid"] for item in store.list_items() if item["source_id"] == source["source_id"]), None),
            "health": state.get("health", "not_observed"),
        })
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "channels.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# CHANNELS", "", f"Watch: `{config['watch']['monitor_id']}`", ""]
    for row in rows:
        lines.extend([f"## {row['display_name']}", "", f"- source_id: `{row['source_id']}`", f"- native channel ID: `{row['native_channel_id']}`", f"- URL: {row['canonical_url']}", f"- groups: {', '.join(row['groups']) or 'none'}", f"- active: `{row['active']}`", f"- last observation: `{row['last_observation'] or 'not observed'}`", f"- latest observed video: `{row['latest_observed_video'] or 'not observed'}`", f"- health: `{row['health']}`", ""])
    (output_root / "CHANNELS.md").write_text("\n".join(lines), encoding="utf-8")
    return {"channels": rows}


def _summary_state(enrichment: MediaEnrichmentStore, item_uid: str) -> dict:
    summaries = enrichment.list_summaries(item_uid)
    if not summaries:
        return {
            "state": "unavailable",
            "summary_id": None,
            "summary": None,
            "key_points": [],
            "provider": None,
            "model": None,
            "generated_at": None,
        }
    summary = summaries[0]
    return {
        "state": "available",
        "summary_id": summary["summary_id"],
        "summary": summary["summary"],
        "key_points": summary["key_points"],
        "provider": summary["provider"],
        "model": summary["model"],
        "generated_at": summary["generated_at"],
    }


def _text_state(enrichment: MediaEnrichmentStore, item_uid: str) -> dict:
    state = enrichment.text_status(item_uid)
    asset = state.get("asset") or {}
    return {
        "status": state.get("status", "not_attempted"),
        "available": bool(state.get("available")),
        "text_asset_id": asset.get("text_asset_id"),
        "timing_available": bool(asset.get("timing_available", False)),
        "text": asset.get("text"),
    }


def build_digest_input(config: dict, store: MediaWatchStore, *, limit_per_channel: int, since: str | None = None) -> list[dict]:
    enrichment = MediaEnrichmentStore(store)
    allowed = {source["source_id"] for source in config["sources"]}
    source_names = {source["source_id"]: source["display_name"] for source in config["sources"]}
    rows = [item for item in store.list_items() if item["source_id"] in allowed]
    if since:
        watermark = _parse_time(since)
        rows = [item for item in rows if _parse_time(item["published_at"]) > watermark]
    selected: list[dict] = []
    for source_id in sorted(allowed):
        source_rows = [item for item in rows if item["source_id"] == source_id][:limit_per_channel]
        for item in source_rows:
            snapshots = store.list_snapshots(item["item_uid"])
            text = _text_state(enrichment, item["item_uid"])
            summary = _summary_state(enrichment, item["item_uid"])
            selected.append({
                "item_uid": item["item_uid"],
                "source_id": source_id,
                "channel_name": source_names[source_id],
                "title": item["title"],
                "published_at": item["published_at"],
                "duration_seconds": item.get("duration_seconds"),
                "canonical_url": item["canonical_url"],
                "description_excerpt": _excerpt(item.get("description", "")),
                "text_status": text["status"],
                "text_available": text["available"],
                "text_asset_id": text["text_asset_id"],
                "timing_available": text["timing_available"],
                "text_excerpt": _excerpt(text.get("text") or "", 1400) if text["available"] else None,
                "summary_state": summary["state"],
                "summary_id": summary["summary_id"],
                "summary": summary["summary"],
                "summary_key_points": summary["key_points"],
                "summary_provider": summary["provider"],
                "summary_model": summary["model"],
                "summary_generated_at": summary["generated_at"],
                "segment_ids": [row["segment_id"] for row in enrichment.list_segments(item["item_uid"])],
                "observed_at": item["last_seen"],
                "snapshot_id": snapshots[0]["snapshot_id"] if snapshots else None,
            })
    return sorted(selected, key=lambda row: (row["published_at"], row["item_uid"]), reverse=True)


def annotate(row: dict) -> dict:
    hay = (row["title"] + " " + row["description_excerpt"] + " " + (row.get("text_excerpt") or "")).casefold()
    topics = [topic for topic, terms in TOPIC_TERMS.items() if any(term in hay for term in terms)] or ["other"]
    text_available = row["text_available"]
    if text_available and not any(term in hay for term in VISUAL_HINTS):
        decision = "TRANSCRIPT_ENOUGH"
        reason = "Governed text is available and the metadata does not signal that direct visual inspection is central."
        quality = "governed_text"
    elif any(term in hay for term in LOW_VALUE_HINTS):
        decision = "SKIP"
        reason = "The title/description identifies a low-priority or repeat-format item for this watch."
        quality = "metadata_only"
    else:
        decision = "WATCH"
        reason = "Governed text is unavailable or the item may depend on live/visual context; metadata is insufficient to clear it."
        quality = "governed_text_plus_metadata" if text_available else "metadata_only"
    evidence = [{"kind": "metadata", "ref": f"snapshot:{row['snapshot_id']}"}] if row.get("snapshot_id") else []
    if row.get("text_asset_id"):
        evidence.append({"kind": "text_asset", "ref": row["text_asset_id"]})
    if row.get("summary_id"):
        evidence.append({"kind": "summary", "ref": row["summary_id"]})
    source_text = row.get("summary") or row.get("text_excerpt") or row.get("description_excerpt") or row["title"]
    source_label = (
        "the governed summary"
        if row.get("summary")
        else "the governed text"
        if row.get("text_excerpt")
        else "the published metadata"
    )
    abstract = f"{row['title']}. {source_label.capitalize()} presents this item as: {source_text}"
    if len(abstract) > 900:
        abstract = abstract[:899].rstrip() + "…"
    return {
        "item_uid": row["item_uid"],
        "abstract": abstract,
        "abstract_source_quality": quality,
        "topics": topics,
        "decision": decision,
        "decision_reason": reason,
        "interesting_because": "; ".join(topics),
        "evidence": evidence,
        "confidence": "medium" if text_available else "low",
    }


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "duration unavailable"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m {secs}s"


def render_digest(config: dict, rows: list[dict], annotations: list[dict], *, output_root: Path, digest_id: str, since: str | None) -> dict:
    if len({row["item_uid"] for row in rows}) != len(rows):
        raise ValueError("duplicate video in digest input")
    by_id = {row["item_uid"]: row for row in rows}
    if any(annotation["item_uid"] not in by_id for annotation in annotations):
        raise ValueError("annotation references unknown item")
    if any(annotation["decision"] not in DECISIONS for annotation in annotations):
        raise ValueError("invalid editorial decision")
    digest_dir = output_root / digest_id
    digest_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_name": "media_channel_digest.v1",
        "digest_id": digest_id,
        "generated_at": utc_now(),
        "monitor_id": config["watch"]["monitor_id"],
        "since": since,
        "channels": sorted({row["source_id"] for row in rows}),
        "item_count": len(rows),
        "new_item_count": len(rows),
        "watermark": max((row["published_at"] for row in rows), default=since),
        "text_counts": dict(Counter(row["text_status"] for row in rows)),
        "decision_counts": dict(Counter(annotation["decision"] for annotation in annotations)),
        "input_sha256": sha256_text(canonical_json(rows)),
        "annotation_sha256": sha256_text(canonical_json(annotations)),
    }
    (digest_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (digest_dir / "items.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (digest_dir / "digest_annotations.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in annotations), encoding="utf-8")
    groups = {decision: [annotation for annotation in annotations if annotation["decision"] == decision] for decision in ("WATCH", "TRANSCRIPT_ENOUGH", "SKIP")}
    lines = ["# Custom YouTube Watch", "", f"Generated: {manifest['generated_at']}", f"Channels: {', '.join(manifest['channels'])}", f"Items considered: {len(rows)}", "", f"Text coverage: {sum(row['text_available'] for row in rows)} with governed text; {sum(not row['text_available'] and row['text_status'] != 'not_attempted' for row in rows)} explicit unavailable/blocked; {sum(row['text_status'] == 'not_attempted' for row in rows)} not attempted", ""]
    for decision, label in (("WATCH", "MUST WATCH"), ("TRANSCRIPT_ENOUGH", "TRANSCRIPT ENOUGH"), ("SKIP", "SKIP")):
        lines.extend([f"## {label}", ""])
        for annotation in groups[decision]:
            row = by_id[annotation["item_uid"]]
            lines.extend([f"### {row['channel_name']} — {row['title']}", "", f"- Published: {row['published_at']}", f"- Duration: {_fmt_duration(row.get('duration_seconds'))}", f"- Text: `{row['text_status']}`", f"- Summary: `{row['summary_state']}`" + (f" via {row['summary_model']}" if row.get("summary_model") else ""), f"- Topics: {', '.join(annotation['topics'])}", f"- Decision: **{decision}** — {annotation['decision_reason']}"])
            if row.get("summary"):
                lines.extend([f"- Governed summary: {row['summary']}"])
                if row.get("summary_key_points"):
                    lines.extend(["- Key points: " + " | ".join(row["summary_key_points"])])
            lines.extend([f"- Abstract ({annotation['abstract_source_quality']}): {annotation['abstract']}", f"- URL: {row['canonical_url']}", ""])
    lines.extend(["## BY CHANNEL", ""])
    for source_id in sorted({row["source_id"] for row in rows}):
        lines.append(f"- `{source_id}`: {sum(row['source_id'] == source_id for row in rows)} items")
    (digest_dir / "digest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    cards = []
    for annotation in annotations:
        row = by_id[annotation["item_uid"]]
        summary_html = ""
        if row.get("summary"):
            points = "".join(f"<li>{html.escape(point)}</li>" for point in row.get("summary_key_points", []))
            summary_html = f"<h3>Governed summary</h3><p>{html.escape(row['summary'])}</p>" + (f"<ul>{points}</ul>" if points else "")
        cards.append(f"<article><h2>{html.escape(row['channel_name'])} — {html.escape(row['title'])}</h2><p>{html.escape(row['published_at'])} · {html.escape(_fmt_duration(row.get('duration_seconds')))} · text: <code>{html.escape(row['text_status'])}</code> · summary: <code>{html.escape(row['summary_state'])}</code></p><p><strong>{annotation['decision']}</strong> — {html.escape(annotation['decision_reason'])}</p>{summary_html}<p>{html.escape(annotation['abstract'])}</p><p>{', '.join(html.escape(t) for t in annotation['topics'])} · <a href='{html.escape(row['canonical_url'])}'>Open on YouTube</a></p></article>")
    page = "<!doctype html><meta charset='utf-8'><title>Custom YouTube Watch</title><style>body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}article{border-top:1px solid #ccc;padding:1rem 0}code{color:#555}</style><h1>Custom YouTube Watch</h1>" + f"<p>{len(rows)} items · {html.escape(str(manifest['generated_at']))}</p>" + "".join(cards)
    (digest_dir / "digest.html").write_text(page, encoding="utf-8")
    index_path = output_root / "index.json"
    history = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    history = [entry for entry in history if entry.get("digest_id") != digest_id]
    history.append({"digest_id": digest_id, "generated_at": manifest["generated_at"], "item_count": len(rows), "new_item_count": len(rows), "watermark": manifest["watermark"], "channels": manifest["channels"], "manifest_path": f"{digest_id}/manifest.json"})
    index_path.write_text(json.dumps(sorted(history, key=lambda item: item["generated_at"], reverse=True), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def run(config_path: Path, store_root: Path, output_root: Path, *, limit_per_channel: int, since: str | None, digest_id: str | None) -> dict:
    config = validate_watch_config(config_path)
    store = MediaWatchStore(store_root)
    if since == "last_successful":
        index_path = output_root / "index.json"
        if index_path.exists():
            history = json.loads(index_path.read_text(encoding="utf-8"))
            since = history[0].get("watermark") if history else None
        else:
            since = None
    materialize_channels(config, store, output_root)
    rows = build_digest_input(config, store, limit_per_channel=limit_per_channel, since=since)
    annotations = [annotate(row) for row in rows]
    digest_id = digest_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return render_digest(config, rows, annotations, output_root=output_root, digest_id=digest_id, since=since)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic Custom YouTube Channel Watch digest")
    parser.add_argument("--config", type=Path, default=Path("config/media_watch/watches/matias-knowledge-channels.yaml"))
    parser.add_argument("--store-root", type=Path, default=Path("data/canonical/media_watch"))
    parser.add_argument("--output-root", type=Path, default=Path("artifacts/channel-watch/matias-knowledge-channels/digests"))
    parser.add_argument("--limit-per-channel", type=int, default=5)
    parser.add_argument("--since", help="ISO timestamp or last_successful")
    parser.add_argument("--digest-id")
    args = parser.parse_args(argv)
    if not 1 <= args.limit_per_channel <= 50:
        parser.error("--limit-per-channel must be between 1 and 50")
    print(json.dumps(run(args.config, args.store_root, args.output_root, limit_per_channel=args.limit_per_channel, since=args.since, digest_id=args.digest_id), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
