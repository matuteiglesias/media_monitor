#!/usr/bin/env python3
"""Build a deterministic Media Monitor demo without network, LLMs, DBs or deploy credentials."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_editorial_selection import build as build_selection
from build_story_contexts import build as build_contexts
from build_site_snapshot import build as build_snapshot

DIGEST = "20260824T19"
AS_OF = "2026-08-24T19:45:00Z"

SIGNALS = [
    ("demo-cpi", "Inflación y Precios", "INDEC", "2026-08-24T19:35:00Z", "IPC: nueva observación mensual disponible"),
    ("demo-fx", "Tipo de Cambio y Reservas", "BCRA", "2026-08-24T19:30:00Z", "Reservas: nueva observación del balance cambiario"),
    ("demo-jobs", "Actividad y Empleo", "INDEC", "2026-08-24T19:25:00Z", "Mercado de trabajo: actualización de indicadores"),
    ("demo-trade", "Sector Externo", "INDEC Comercio Exterior", "2026-08-24T19:20:00Z", "Comercio exterior: actualización del intercambio"),
    ("demo-debt", "Deuda y Financiamiento", "Ministerio de Economía", "2026-08-24T19:15:00Z", "Financiamiento: nueva información oficial"),
    ("demo-finance", "Finanzas", "BYMA", "2026-08-24T19:10:00Z", "Mercados: nueva rueda y referencias financieras"),
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def fixture_refs() -> list[dict]:
    return [
        {
            "index_id": index_id,
            "digest_at": DIGEST,
            "title": title,
            "topic": topic,
            "published_at": published_at,
            "link": f"https://example.com/media-monitor-demo/{index_id}",
            "source": source,
        }
        for index_id, topic, source, published_at, title in SIGNALS
    ]


def fixture_groups() -> list[dict]:
    by_topic: dict[str, list[str]] = {}
    for _, topic, _, _, title in SIGNALS:
        by_topic.setdefault(topic, []).append(title)
    return [
        {
            "digest_at": DIGEST,
            "topic": topic,
            "article_count": len(titles),
            "top_titles": titles,
        }
        for topic, titles in sorted(by_topic.items())
    ]


def build_demo(output_dir: Path, *, clean: bool = True) -> dict:
    output_dir = output_dir.resolve()
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    indexes = output_dir / "storage" / "indexes"
    indexes.mkdir(parents=True, exist_ok=True)

    refs_path = indexes / "news_recent_refs_latest.jsonl"
    groups_path = indexes / "news_recent_groups_latest.jsonl"
    published_path = indexes / "published_articles_latest.jsonl"
    selection_path = indexes / "editorial_selection_latest.json"
    contexts_path = indexes / "story_contexts_latest.jsonl"
    snapshot_path = output_dir / "site_snapshot.json"

    write_jsonl(refs_path, fixture_refs())
    write_jsonl(groups_path, fixture_groups())
    published_path.write_text("", encoding="utf-8")

    selection = build_selection(
        refs_path=refs_path,
        policy_path=ROOT / "config" / "editorial_selection.argentina.json",
        digest_at=DIGEST,
        as_of=AS_OF,
        output=selection_path,
    )
    contexts = build_contexts(output_dir / "storage", DIGEST, contexts_path)
    snapshot = build_snapshot(
        SimpleNamespace(
            site_id="argentina-general",
            digest_at=DIGEST,
            sites_dir=str(ROOT / "sites"),
            indexes_dir=str(indexes),
            editorial_selection=str(selection_path),
            story_contexts=str(contexts_path),
            output=str(snapshot_path),
            now=AS_OF,
        )
    )

    manifest = {
        "schema_name": "media_monitor_demo.v1",
        "scope": "DETERMINISTIC_FIXTURE_NOT_LIVE_NEWS",
        "network_used": False,
        "llm_used": False,
        "database_used": False,
        "deployment_credentials_used": False,
        "digest_at": DIGEST,
        "as_of": AS_OF,
        "snapshot_id": snapshot["snapshot_id"],
        "signal_count": snapshot["metrics"]["item_count"],
        "curated_signal_count": snapshot["metrics"]["curated_signal_count"],
        "story_context_count": snapshot["metrics"]["story_context_count"],
        "published_article_count": snapshot["metrics"]["published_article_count"],
        "selection_id": selection["selection_id"],
        "context_count": len(contexts),
        "snapshot_path": str(snapshot_path),
    }
    (output_dir / "demo_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "README.txt").write_text(
        "Media Monitor deterministic demo\n"
        "This directory contains fixture data, not live news and not public editorial approval.\n"
        "Inspect site_snapshot.json and demo_manifest.json.\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".demo" / "media-monitor")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()
    try:
        first = build_demo(args.output_dir, clean=not args.no_clean)
        expected = first["snapshot_id"]
        second = build_demo(args.output_dir, clean=True)
        if second["snapshot_id"] != expected:
            raise AssertionError("demo snapshot is not deterministic across repeated builds")
    except Exception as exc:
        print(json.dumps({"schema_name": "media_monitor_demo.v1", "status": "failed", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(second | {"status": "ok"}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
