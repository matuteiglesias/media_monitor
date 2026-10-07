"""Sanitized two-channel governed-summary fixture for evidence consumers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .enrichment import MediaEnrichmentStore
from .enrichment_fixture import seed_enriched
from .store import MediaWatchStore


def seed_evidence_fixture(root: Path) -> dict:
    seed_enriched(root)
    store = MediaWatchStore(root)
    enrichment = MediaEnrichmentStore(store)
    first = enrichment.put_summary(
        item_uid="youtube:fixtureA01",
        summary="El canal describe una desaceleración de la inflación y debate sobre actividad económica.",
        key_points=["Inflación desacelera", "Actividad débil", "Política económica en debate"],
        provider="google-gemini",
        model="gemini-fixture",
        prompt_version="youtube-summary.v1",
        adapter_version="gemini-youtube-url.v1",
        processing_mode="static",
        generated_at="2026-08-30T21:00:00Z",
    )
    second = enrichment.put_summary(
        item_uid="youtube:fixtureB01",
        summary="El segundo canal también discute inflación, salarios, consumo y nivel de actividad.",
        key_points=["Inflación desacelera", "Salarios rezagados", "Consumo débil"],
        provider="google-gemini",
        model="gemini-fixture",
        prompt_version="youtube-summary.v1",
        adapter_version="gemini-youtube-url.v1",
        processing_mode="static",
        generated_at="2026-08-30T21:05:00Z",
    )
    return {
        "contract": "media-monitor.evidence-fixture@1",
        "items": [first["item_uid"], second["item_uid"]],
        "summaries": [first["summary_id"], second["summary_id"]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-root", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(seed_evidence_fixture(args.store_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
