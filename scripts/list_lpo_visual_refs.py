#!/usr/bin/env python3
"""Inspect a local LPO visual reference corpus for Southland curation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("visuals/references"))
    parser.add_argument("--only-downloaded", action="store_true")
    parser.add_argument("--only-credited", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    articles = {
        row["article_id"]: row
        for row in load_rows(args.root / "manifests/lpo_articles.jsonl")
    }
    images = load_rows(args.root / "manifests/lpo_images.jsonl")

    rows = []
    for image in images:
        if args.only_downloaded and image.get("download_status") != "ok":
            continue
        if args.only_credited and not image.get("credit_as_published"):
            continue
        article_id = (image.get("article_ids") or [""])[0]
        article = articles.get(article_id, {})
        rows.append(
            {
                "image_id": image.get("image_id", ""),
                "role": image.get("role", ""),
                "dimensions": (
                    f"{image.get('width')}x{image.get('height')}"
                    if image.get("width") and image.get("height")
                    else ""
                ),
                "credit": image.get("credit_as_published", ""),
                "headline": article.get("headline", ""),
                "article_url": article.get("canonical_url", ""),
                "local_reference_path": image.get("local_reference_path", ""),
            }
        )
    rows.sort(key=lambda row: (row["headline"], row["role"], row["image_id"]))
    if args.limit is not None:
        rows = rows[: args.limit]

    print("image_id\trole\tdimensions\tcredit\theadline\tarticle_url\tlocal_reference_path")
    for row in rows:
        print(
            "\t".join(
                str(row[key]).replace("\t", " ").replace("\n", " ")
                for key in (
                    "image_id",
                    "role",
                    "dimensions",
                    "credit",
                    "headline",
                    "article_url",
                    "local_reference_path",
                )
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
