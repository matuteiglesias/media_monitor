#!/usr/bin/env python3
"""Build compact published article indexes for the public news site."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUS = ROOT / "storage" / "buses" / "published_article" / "v1"
INDEXES = ROOT / "storage" / "indexes"


def iter_rows(bus_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(bus_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("schema_name") == "published_article.v1" and row.get("status") == "published":
                    rows.append(row)
    return rows


def build_indexes(bus_dir: Path = BUS, indexes_dir: Path = INDEXES) -> tuple[Path, int]:
    rows = iter_rows(bus_dir) if bus_dir.exists() else []
    rows.sort(key=lambda row: (str(row.get("published_at") or ""), str(row.get("article_id") or "")), reverse=True)
    indexes_dir.mkdir(parents=True, exist_ok=True)
    latest = indexes_dir / "published_articles_latest.jsonl"
    latest.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    articles_dir = indexes_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)
    for stale in articles_dir.glob("*.json"):
        stale.unlink()
    for row in rows:
        slug = str(row.get("slug") or "").strip()
        if slug:
            (articles_dir / f"{slug}.json").write_text(json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return latest, len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bus-dir", type=Path, default=BUS)
    parser.add_argument("--indexes-dir", type=Path, default=INDEXES)
    args = parser.parse_args()
    latest, count = build_indexes(args.bus_dir, args.indexes_dir)
    print(json.dumps({"status": "ok", "latest": str(latest), "published_article_count": count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
