#!/usr/bin/env python3
"""Compile one configured outlet from its isolated mutable runtime state."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_editorial_selection import build as build_selection
from build_published_article_indexes import build_indexes as build_published_indexes
from build_site_snapshot import build as build_snapshot
from build_story_contexts import build as build_story_contexts
from outlet_runtime import resolve_outlet_runtime


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compile_outlet(
    *,
    repo_root: Path,
    site_id: str,
    digest_at: str,
    now: str | None = None,
) -> dict[str, Any]:
    runtime = resolve_outlet_runtime(repo_root, site_id)
    as_of = now or _utc_now()
    indexes = runtime.indexes_dir
    indexes.mkdir(parents=True, exist_ok=True)

    published_index, published_count = build_published_indexes(
        bus_dir=runtime.published_bus_dir,
        indexes_dir=indexes,
    )

    selection_path = indexes / "editorial_selection_latest.json"
    selection = build_selection(
        refs_path=indexes / "news_recent_refs_latest.jsonl",
        policy_path=runtime.selection_policy,
        digest_at=digest_at,
        as_of=as_of,
        output=selection_path,
    )

    contexts_path = indexes / "story_contexts_latest.jsonl"
    contexts = build_story_contexts(
        runtime.storage_dir,
        digest_at,
        contexts_path,
    )

    snapshot = build_snapshot(
        SimpleNamespace(
            site_id=site_id,
            digest_at=digest_at,
            sites_dir=str(runtime.repo_root / "sites"),
            indexes_dir=str(indexes),
            editorial_selection=str(selection_path),
            story_contexts=str(contexts_path),
            output=str(runtime.snapshot_path),
            now=as_of,
        )
    )

    return {
        "schema_name": "outlet_compile.v1",
        "status": "ok",
        "site_id": site_id,
        "digest_at": digest_at,
        "storage_dir": str(runtime.storage_dir),
        "snapshot_path": str(runtime.snapshot_path),
        "snapshot_id": snapshot["snapshot_id"],
        "selection_policy_id": selection["policy"]["policy_id"],
        "selected_count": selection["metrics"]["selected_count"],
        "story_context_count": len(contexts),
        "published_article_count": published_count,
        "published_index": str(published_index),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--now", default=None)
    args = parser.parse_args()
    try:
        result = compile_outlet(
            repo_root=args.repo_root,
            site_id=args.site_id,
            digest_at=args.digest_at,
            now=args.now,
        )
    except Exception as exc:
        print(json.dumps({"schema_name": "outlet_compile.v1", "status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
