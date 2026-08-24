#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from build_site_snapshot import (
    canonical_id,
    parse_time,
    published_validator,
    read_json,
    sha,
    validate_config,
    validate_editorial_selection,
    validate_published_article,
    validate_schema,
)


def validate_publication(snapshot: dict, latest_count: int) -> None:
    publication = snapshot["publication"]
    articles = snapshot["articles"]
    expected_count = snapshot["metrics"]["published_article_count"]
    if expected_count != len(articles):
        raise ValueError("published_article_count/articles mismatch")

    validator = published_validator()
    seen_ids: set[str] = set()
    for slug, article in articles.items():
        validate_published_article(article, f"articles.{slug}", validator)
        if article["slug"] != slug:
            raise ValueError(f"articles.{slug}: key does not match article slug")
        if article["article_id"] in seen_ids:
            raise ValueError(f"duplicate article_id {article['article_id']}")
        seen_ids.add(article["article_id"])

    latest = publication["latest"]
    if len(latest) != min(expected_count, latest_count):
        raise ValueError("publication.latest length mismatch")
    if expected_count == 0:
        if publication["featured"] is not None or latest:
            raise ValueError("empty publication must not expose featured/latest entries")
        return
    if not latest or publication["featured"] != latest[0]:
        raise ValueError("publication.featured must equal first publication.latest entry")

    previous_key: tuple[str, str] | None = None
    for ref in latest:
        slug = ref["slug"]
        article = articles.get(slug)
        if article is None:
            raise ValueError(f"publication.latest references missing article slug {slug}")
        expected = {
            key: article[key]
            for key in (
                "article_id",
                "slug",
                "title",
                "summary",
                "topic",
                "published_at",
                "updated_at",
            )
        }
        if ref != expected:
            raise ValueError(f"publication ref does not match articles.{slug}")
        key = (ref["published_at"], ref["article_id"])
        if previous_key is not None and key > previous_key:
            raise ValueError("publication.latest is not deterministically newest-first")
        previous_key = key


def validate_curated(snapshot: dict, *, now: datetime, max_age_hours: int) -> None:
    curated = snapshot["signals"]["curated"]
    expected_count = snapshot["metrics"]["curated_signal_count"]
    if len(curated) != expected_count:
        raise ValueError("curated_signal_count/signals.curated mismatch")
    if [item["rank"] for item in curated] != list(range(1, len(curated) + 1)):
        raise ValueError("signals.curated ranks must be contiguous and ordered")

    provenance = snapshot["provenance"]
    selection_path = Path(provenance["editorial_selection_path"])
    if not selection_path.exists():
        raise ValueError("editorial selection provenance path does not exist")
    if sha(selection_path) != provenance["editorial_selection_sha256"]:
        raise ValueError("editorial selection provenance hash mismatch")
    selection = read_json(selection_path)
    validate_editorial_selection(
        selection,
        path=selection_path,
        digest_at=snapshot["digest_at"],
        now=now,
        max_age_hours=max_age_hours,
    )
    if selection["selection_id"] != provenance["editorial_selection_id"]:
        raise ValueError("editorial selection id/provenance mismatch")
    if selection["policy"]["policy_sha256"] != provenance["editorial_selection_policy_sha256"]:
        raise ValueError("editorial selection policy hash/provenance mismatch")

    public_fields = ("rank", "index_id", "title", "topic", "published_at", "link", "source", "score", "score_components", "reason_codes")
    expected = [{key: item[key] for key in public_fields} for item in selection["selected"]]
    if curated != expected:
        raise ValueError("signals.curated does not match editorial_selection.v1 ordered projection")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--sites-dir", default="sites")
    parser.add_argument("--input", default="apps/news_site/public/data/site_snapshot.json")
    parser.add_argument("--now")
    args = parser.parse_args()

    try:
        config = read_json(Path(args.sites_dir) / f"{args.site_id}.json")
        validate_config(config)
        snapshot = read_json(Path(args.input))
        validate_schema(snapshot)
        if snapshot["schema_name"] != "site_snapshot.v3":
            raise ValueError("expected site_snapshot.v3")
        if snapshot["site"]["site_id"] != args.site_id or snapshot["digest_at"] != args.digest_at:
            raise ValueError("snapshot site_id or digest_at does not match requested values")
        if snapshot["snapshot_id"] != canonical_id(snapshot):
            raise ValueError("snapshot_id is not deterministic canonical payload hash")

        signals = snapshot["signals"]
        signal_latest = signals["latest"]
        signal_sections = signals["sections"]
        item_count = snapshot["metrics"]["item_count"]
        section_count = snapshot["metrics"]["section_count"]
        if len(signal_latest) != min(item_count, config["presentation"]["latest_count"]):
            raise ValueError("item_count/signals.latest mismatch")
        if section_count != len(signal_sections):
            raise ValueError("section_count/signals.sections mismatch")
        if item_count < config["selection"]["minimum_items"]:
            raise ValueError("snapshot below configured minimum_items")
        if signals["hero"] != signal_latest[0]:
            raise ValueError("signals.hero must be first signals.latest item")

        now = parse_time(args.now, "--now") if args.now else datetime.now(timezone.utc)
        if now - parse_time(snapshot["generated_at"], "generated_at") > timedelta(hours=config["selection"]["max_age_hours"]):
            raise ValueError("snapshot age exceeds configured max_age_hours")
        for item in [signals["hero"], *signal_latest, *signals["curated"]]:
            if parse_time(item["published_at"], item["index_id"]) < now - timedelta(hours=config["selection"]["max_age_hours"]):
                raise ValueError("snapshot contains stale monitored signal")

        validate_curated(snapshot, now=now, max_age_hours=config["selection"]["max_age_hours"])
        validate_publication(snapshot, config["presentation"]["latest_count"])

        print(json.dumps({
            "status": "ok",
            "snapshot_id": snapshot["snapshot_id"],
            "digest_at": snapshot["digest_at"],
            "item_count": item_count,
            "section_count": section_count,
            "published_article_count": snapshot["metrics"]["published_article_count"],
            "curated_signal_count": snapshot["metrics"]["curated_signal_count"],
        }))
        return 0
    except Exception as exc:
        print(f"[validate-site-snapshot] ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
