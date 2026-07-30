#!/usr/bin/env python3
"""Mirror the compactor-selected generation into legacy local paths.

This is not the governed compactor.  It exists only to keep legacy local
consumers usable while immutable bundle production is introduced.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def copy_if_present(source: Path, destination: Path) -> None:
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        shutil.copy2(source, temporary)
        temporary.replace(destination)


def promote_current_compaction(state_root: Path, repo_root: Path) -> None:
    pointer_path = state_root / "current.json"
    if not pointer_path.is_file():
        raise ValueError(f"compactor current pointer is missing: {pointer_path}")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    generation = state_root / "generations" / str(pointer.get("generation") or "")
    manifest_path = generation / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"compactor generation is missing: {generation}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("generation") != pointer.get("generation"):
        raise ValueError("compactor pointer/generation mismatch")
    copy_if_present(generation / "master_ref.csv", repo_root / "data" / "master_ref.csv")
    copy_if_present(
        generation / "news_recent_refs.jsonl",
        repo_root / "storage" / "indexes" / "news_recent_refs_latest.jsonl",
    )
    copy_if_present(
        generation / "news_recent_groups.jsonl",
        repo_root / "storage" / "indexes" / "news_recent_groups_latest.jsonl",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", default="storage/sensing_compacted")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    promote_current_compaction(Path(args.state_root), Path(args.repo_root))
    print(f"[sensing-compatibility-mirror] state_root={args.state_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
