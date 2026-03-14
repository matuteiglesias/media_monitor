#!/usr/bin/env python3
"""Publish a hardened last-mile snapshot for static hosting.

Copies `storage/indexes/editorial_latest.json` into `web/data/editorial_latest.json`
with a constrained public shape so the static UI can be deployed safely.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_ROOT_KEYS = {"digest_at", "built_at", "status", "metrics", "human_handoff"}
ALLOWED_METRICS_KEYS = {
    "seed_ideas_emitted",
    "briefs_emitted",
    "drafts_emitted",
    "fallback_legacy_count",
    "schema_failures",
}
ALLOWED_HANDOFF_KEYS = {
    "status",
    "action_candidates",
    "latest_article_drafts",
    "latest_yt_script_drafts",
}


def _safe_text(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    return default


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _normalize_candidate(candidate: Any) -> dict[str, Any] | str:
    if isinstance(candidate, str):
        return _safe_text(candidate, "sin título")
    if not isinstance(candidate, dict):
        return "sin título"
    return {
        "priority": _safe_int(candidate.get("priority"), 999),
        "kind": _safe_text(candidate.get("kind") or candidate.get("target_format"), "n/a"),
        "title": _safe_text(candidate.get("title") or candidate.get("index_id"), "sin título"),
    }


def _normalize_draft(draft: Any) -> dict[str, str]:
    if not isinstance(draft, dict):
        return {"title": "sin título", "index_id": ""}
    return {
        "title": _safe_text(draft.get("title"), "sin título"),
        "index_id": _safe_text(draft.get("index_id"), ""),
    }


def build_public_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    public_data: dict[str, Any] = {k: data[k] for k in ALLOWED_ROOT_KEYS if k in data}

    metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
    public_data["metrics"] = {
        key: _safe_int(metrics.get(key), 0)
        for key in ALLOWED_METRICS_KEYS
    }

    handoff = data.get("human_handoff") if isinstance(data.get("human_handoff"), dict) else {}
    public_handoff: dict[str, Any] = {
        "status": _safe_text(handoff.get("status"), "unknown"),
        "action_candidates": [
            _normalize_candidate(item)
            for item in (handoff.get("action_candidates") or [])
        ],
        "latest_article_drafts": [
            _normalize_draft(item)
            for item in (handoff.get("latest_article_drafts") or [])
        ],
        "latest_yt_script_drafts": [
            _normalize_draft(item)
            for item in (handoff.get("latest_yt_script_drafts") or [])
        ],
    }
    public_data["human_handoff"] = {
        key: public_handoff[key]
        for key in ALLOWED_HANDOFF_KEYS
    }

    public_data["digest_at"] = _safe_text(public_data.get("digest_at"), "")
    public_data["built_at"] = _safe_text(public_data.get("built_at"), "")
    public_data["status"] = _safe_text(public_data.get("status"), "unknown")
    return public_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish last-mile snapshot for web deployment")
    parser.add_argument(
        "--source",
        default="storage/indexes/editorial_latest.json",
        help="Input editorial latest JSON",
    )
    parser.add_argument(
        "--dest",
        default="web/data/editorial_latest.json",
        help="Output public snapshot JSON",
    )
    args = parser.parse_args()

    source = Path(args.source)
    dest = Path(args.dest)

    if not source.exists():
        raise SystemExit(f"[publish-last-mile] source file not found: {source}")

    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("[publish-last-mile] expected JSON object at root")

    snapshot = build_public_snapshot(data)
    dest.parent.mkdir(parents=True, exist_ok=True)

    temp_dest = dest.with_suffix(dest.suffix + ".tmp")
    temp_dest.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_dest.replace(dest)

    print(f"[publish-last-mile] source={source} -> dest={dest}")
    print(
        "[publish-last-mile] "
        f"status={snapshot.get('status')} "
        f"digest_at={snapshot.get('digest_at')} "
        f"actions={len(snapshot['human_handoff']['action_candidates'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
