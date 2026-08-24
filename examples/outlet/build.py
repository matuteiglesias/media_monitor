#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_editorial_selection import build as build_selection
from build_story_contexts import build as build_contexts
from build_site_snapshot import build as build_snapshot

DIGEST = "20260115T12"
AS_OF = "2026-01-15T12:45:00Z"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def load_list(path: Path) -> list[dict]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"{path}: expected array of objects")
    return value


def build(output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    indexes = output_dir / "storage" / "indexes"
    indexes.mkdir(parents=True, exist_ok=True)

    refs_path = indexes / "news_recent_refs_latest.jsonl"
    groups_path = indexes / "news_recent_groups_latest.jsonl"
    published_path = indexes / "published_articles_latest.jsonl"
    selection_path = indexes / "editorial_selection_latest.json"
    contexts_path = indexes / "story_contexts_latest.jsonl"
    snapshot_path = output_dir / "site_snapshot.json"

    write_jsonl(refs_path, load_list(HERE / "fixtures" / "signals.json"))
    write_jsonl(groups_path, load_list(HERE / "fixtures" / "groups.json"))
    published_path.write_text("", encoding="utf-8")

    selection = build_selection(
        refs_path=refs_path,
        policy_path=HERE / "editorial_selection.example.json",
        digest_at=DIGEST,
        as_of=AS_OF,
        output=selection_path,
    )
    contexts = build_contexts(output_dir / "storage", DIGEST, contexts_path)
    snapshot = build_snapshot(
        SimpleNamespace(
            site_id="example-general",
            digest_at=DIGEST,
            sites_dir=str(HERE),
            indexes_dir=str(indexes),
            editorial_selection=str(selection_path),
            story_contexts=str(contexts_path),
            output=str(snapshot_path),
            now=AS_OF,
        )
    )
    result = {
        "schema_name": "example_outlet_build.v1",
        "status": "ok",
        "site_id": snapshot["site"]["site_id"],
        "name": snapshot["site"]["name"],
        "snapshot_id": snapshot["snapshot_id"],
        "signal_count": snapshot["metrics"]["item_count"],
        "curated_signal_count": snapshot["metrics"]["curated_signal_count"],
        "story_context_count": snapshot["metrics"]["story_context_count"],
        "selection_policy_id": selection["policy"]["policy_id"],
        "output": str(snapshot_path),
    }
    (output_dir / "build_manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    result = build(ROOT / ".demo" / "example-outlet")
    print(json.dumps(result, indent=2))
