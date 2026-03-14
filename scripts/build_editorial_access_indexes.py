#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _extract_digest_from_name(path: Path) -> str | None:
    m = re.search(r"pfout_(\d{8}T\d{2})", path.name)
    return m.group(1) if m else None


def _resolve_digest_id(data_dir: Path, digest_at: str | None) -> str | None:
    if digest_at:
        return digest_at.strip()

    pf_out = data_dir / "pf_out"
    candidates = sorted(pf_out.glob("pfout_*.jsonl"), reverse=True)
    for p in candidates:
        did = _extract_digest_from_name(p)
        if did:
            return did
    return None


def _count_seed_ideas(pf_files: list[Path]) -> int:
    total = 0
    for pf in pf_files:
        for row in _iter_jsonl(pf):
            seed_obj = row.get("seed_ideas")
            if not isinstance(seed_obj, dict):
                continue
            ideas = seed_obj.get("seed_ideas")
            if isinstance(ideas, list):
                total += len([x for x in ideas if isinstance(x, dict)])
    return total


def _count_briefs(brief_files: list[Path], digest_id: str) -> int:
    count = 0
    for bf in brief_files:
        for row in _iter_jsonl(bf):
            if str(row.get("schema_name") or "") != "news_piece_brief.v1":
                continue
            if str(row.get("digest_id_hour") or "") != digest_id:
                continue
            count += 1
    return count


def _count_drafts(drafts_dir: Path) -> int:
    if not drafts_dir.exists():
        return 0
    return len(list(drafts_dir.glob("*.jsonl")))


def _quarantine_metrics(quarantine_dir: Path, digest_id: str) -> tuple[int, int]:
    fallback_legacy_count = 0
    schema_failures = 0
    for qf in sorted(quarantine_dir.glob(f"V*{digest_id}*.jsonl")):
        for row in _iter_jsonl(qf):
            reason = str(row.get("reason") or "")
            if reason in {"missing_piece_briefs_fallback_legacy", "legacy_fallback_emergency_activated"}:
                fallback_legacy_count += 1
            if reason == "schema_validation_error":
                schema_failures += 1
    return fallback_legacy_count, schema_failures


def _status_for(metrics: dict[str, int]) -> str:
    if metrics["schema_failures"] > 0:
        return "degraded"
    if metrics["fallback_legacy_count"] > 0:
        return "fallback-heavy"
    if metrics["seed_ideas_emitted"] == 0:
        return "degraded"
    return "ok"




def _latest_briefs(brief_files: list[Path], digest_id: str, limit: int = 10) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for bf in brief_files:
        for row in _iter_jsonl(bf):
            if str(row.get("schema_name") or "") != "news_piece_brief.v1":
                continue
            if str(row.get("digest_id_hour") or "") != digest_id:
                continue
            out.append(
                {
                    "brief_id": str(row.get("brief_id") or ""),
                    "topic": str(row.get("topic") or ""),
                    "working_title": str(row.get("working_title") or ""),
                    "angle": str(row.get("angle") or ""),
                    "source_index_ids": [str(v) for v in (row.get("source_index_ids") or []) if str(v).strip()],
                }
            )
    return out[-limit:]


def _latest_draft_records(drafts_dir: Path, limit: int = 10) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    article: list[dict[str, Any]] = []
    yt: list[dict[str, Any]] = []
    if not drafts_dir.exists():
        return article, yt

    files = sorted(drafts_dir.glob("*.jsonl"))
    for df in files:
        try:
            rows = list(_iter_jsonl(df))
        except Exception:
            continue
        if not rows:
            continue
        row = rows[-1]
        schema_name = str(row.get("schema_name") or "")
        record = {
            "path": str(df),
            "index_id": str(row.get("index_id") or ""),
            "topic": str(row.get("topic") or ""),
            "headline": str(row.get("headline") or ""),
            "dek": str(row.get("dek") or ""),
            "cluster_id": str(row.get("cluster_id") or ""),
            "schema_name": schema_name,
        }
        if schema_name == "news_yt_script_draft.v1":
            yt.append(record)
        else:
            article.append(record)

    return article[-limit:], yt[-limit:]


def _fallback_summary(quarantine_dir: Path, digest_id: str, limit: int = 20) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for qf in sorted(quarantine_dir.glob(f"V*{digest_id}*.jsonl")):
        for row in _iter_jsonl(qf):
            reason = str(row.get("reason") or "")
            if "fallback" not in reason:
                continue
            out.append({"file": str(qf), "reason": reason, "digest_id": str(row.get("digest_id") or digest_id)})
    return out[-limit:]


def _human_status(metrics: dict[str, int]) -> str:
    if metrics["schema_failures"] > 0:
        return "needs-attention"
    if metrics["fallback_legacy_count"] > 0:
        return "fallback-emergency"
    if metrics["briefs_emitted"] == 0 and metrics["seed_ideas_emitted"] > 0:
        return "brief-gap"
    if metrics["drafts_emitted"] == 0 and metrics["briefs_emitted"] > 0:
        return "draft-gap"
    if metrics["seed_ideas_emitted"] == 0:
        return "no-seed-ideas"
    return "ready"

def build_editorial_index(storage_dir: Path, data_dir: Path, digest_at: str | None = None) -> Path:
    digest_id = _resolve_digest_id(data_dir, digest_at)
    built_at = _utc_now_compact()
    idx_dir = storage_dir / "indexes"

    if not digest_id:
        payload = {
            "digest_at": None,
            "built_at": built_at,
            "status": "no-data",
            "metrics": {
                "seed_ideas_emitted": 0,
                "briefs_emitted": 0,
                "drafts_emitted": 0,
                "fallback_legacy_count": 0,
                "schema_failures": 0,
            },
            "pointers": {
                "pf_outputs": [],
                "brief_files": [],
                "draft_files": [],
                "quarantine_files": [],
            },
            "human_handoff": {
                "status": "no-data",
                "latest_briefs": [],
                "latest_article_drafts": [],
                "latest_yt_script_drafts": [],
                "fallback_events": [],
            },
        }
        latest = idx_dir / "editorial_latest.json"
        _write_json(latest, payload)
        _write_json(idx_dir / f"editorial_unknown_{built_at}.json", payload)
        return latest

    pf_files = sorted((data_dir / "pf_out").glob(f"pfout_{digest_id}*.jsonl"))
    brief_files = sorted((storage_dir / "buses" / "news_piece_brief" / "v1").glob("*.jsonl"))
    drafts_dir = data_dir / "drafts" / digest_id
    quarantine_files = sorted((data_dir / "quarantine").glob(f"V*{digest_id}*.jsonl"))

    metrics = {
        "seed_ideas_emitted": _count_seed_ideas(pf_files),
        "briefs_emitted": _count_briefs(brief_files, digest_id),
        "drafts_emitted": _count_drafts(drafts_dir),
        "fallback_legacy_count": 0,
        "schema_failures": 0,
    }
    fallback_count, schema_fails = _quarantine_metrics(data_dir / "quarantine", digest_id)
    metrics["fallback_legacy_count"] = fallback_count
    metrics["schema_failures"] = schema_fails

    latest_briefs = _latest_briefs(brief_files, digest_id)
    latest_article_drafts, latest_yt_script_drafts = _latest_draft_records(drafts_dir)
    fallback_events = _fallback_summary(data_dir / "quarantine", digest_id)

    payload = {
        "digest_at": digest_id,
        "built_at": built_at,
        "status": _status_for(metrics),
        "metrics": metrics,
        "pointers": {
            "pf_outputs": [str(p) for p in pf_files[-5:]],
            "brief_files": [str(p) for p in brief_files[-10:]],
            "draft_files": [str(p) for p in sorted(drafts_dir.glob("*.jsonl"))[-10:]] if drafts_dir.exists() else [],
            "quarantine_files": [str(p) for p in quarantine_files[-10:]],
        },
        "human_handoff": {
            "status": _human_status(metrics),
            "latest_briefs": latest_briefs,
            "latest_article_drafts": latest_article_drafts,
            "latest_yt_script_drafts": latest_yt_script_drafts,
            "fallback_events": fallback_events,
        },
    }

    latest = idx_dir / "editorial_latest.json"
    snap = idx_dir / f"editorial_{digest_id}_{built_at}.json"
    _write_json(latest, payload)
    _write_json(snap, payload)
    return latest


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build compact editorial status index")
    p.add_argument("--storage-dir", default="storage")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--digest-at", default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    latest = build_editorial_index(Path(args.storage_dir), Path(args.data_dir), args.digest_at)
    payload = json.loads(latest.read_text(encoding="utf-8"))
    print(
        "[editorial-index] "
        f"digest_at={payload.get('digest_at')} status={payload.get('status')} "
        f"seed_ideas={payload.get('metrics', {}).get('seed_ideas_emitted', 0)} "
        f"briefs={payload.get('metrics', {}).get('briefs_emitted', 0)} "
        f"drafts={payload.get('metrics', {}).get('drafts_emitted', 0)} "
        f"fallback={payload.get('metrics', {}).get('fallback_legacy_count', 0)} "
        f"schema_failures={payload.get('metrics', {}).get('schema_failures', 0)}"
    )
    print(f"[editorial-index] latest={latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
