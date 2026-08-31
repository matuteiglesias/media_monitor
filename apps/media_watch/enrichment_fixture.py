from __future__ import annotations

import argparse
from pathlib import Path

from .enrichment import MediaEnrichmentStore, detect_appearances, load_watch_config, materialize_segments
from .fixture import seed
from .store import MediaWatchStore


def seed_enriched(root: Path) -> dict:
    seed(root)
    store = MediaWatchStore(root)
    enrichment = MediaEnrichmentStore(store)
    items = {row["native_id"]: row for row in store.list_items()}

    enrichment.put_text_asset(
        item_uid=items["fixtureA01"]["item_uid"],
        status="publisher_article_text",
        acquisition_method="publisher_page",
        observed_at="2026-08-30T20:05:00Z",
        language="es",
        text="Texto editorial compañero del publisher sobre la entrevista económica a Carlos Melconian.",
    )
    enrichment.put_text_asset(
        item_uid=items["fixtureA02"]["item_uid"],
        status="unavailable",
        acquisition_method="none",
        observed_at="2026-08-30T20:05:00Z",
    )
    enrichment.put_text_asset(
        item_uid=items["fixtureB01"]["item_uid"],
        status="authorized_asr",
        acquisition_method="authorized_asr",
        observed_at="2026-08-30T20:05:00Z",
        language="es",
        text="Fixture de ASR autorizado: Marina Dal Poggetto analiza actividad, inflación y producción.",
        generator={"provider": "deterministic-fixture", "model": "authorized-asr-proof-v1"},
    )
    enrichment.put_text_asset(
        item_uid=items["fixtureB02"]["item_uid"],
        status="blocked_by_policy",
        acquisition_method="none",
        observed_at="2026-08-30T20:05:00Z",
    )

    materialize_segments(enrichment)
    config = load_watch_config(Path(__file__).resolve().parents[2] / "config" / "media_watch" / "sources.yaml")
    people = config["watch"]["people"]
    detect_appearances(enrichment, people)
    indexes = enrichment.write_indexes(people)
    return indexes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed deterministic governed media enrichment fixture")
    parser.add_argument("--store-root", type=Path, required=True)
    args = parser.parse_args(argv)
    print(seed_enriched(args.store_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
