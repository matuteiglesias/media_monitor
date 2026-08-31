from __future__ import annotations

import argparse
from pathlib import Path

from .store import MediaObservation, MediaWatchStore


def seed(root: Path) -> None:
    store = MediaWatchStore(root)
    sources = [("el-destape-youtube", "El Destape", "UC5wAqJ9NF0fpGH9dVf3h6HA", "UU5wAqJ9NF0fpGH9dVf3h6HA"), ("futurock-youtube", "Futurock", "UCgn6r0aGRBnEQm02tE_jzbw", "UUgn6r0aGRBnEQm02tE_jzbw")]
    rows = [MediaObservation("el-destape-youtube", "fixtureA01", "Economía y actualidad — entrevista", "Descripción del video de prueba.", "2026-08-30T19:00:00Z", 1260, 1200, 90, 14, "public", "2026-08-30T20:00:00Z"), MediaObservation("el-destape-youtube", "fixtureA02", "Programa completo de la tarde", "Emisión completa.", "2026-08-30T17:00:00Z", 7200, 2400, 110, 20, "public", "2026-08-30T20:00:00Z"), MediaObservation("futurock-youtube", "fixtureB01", "Análisis económico del día", "Clip editorial.", "2026-08-30T18:30:00Z", 980, 1800, 130, 30, "public", "2026-08-30T20:00:00Z"), MediaObservation("futurock-youtube", "fixtureB02", "Mañana de radio — programa", "Programa completo.", "2026-08-30T14:00:00Z", 6400, 3000, 155, 41, "public", "2026-08-30T20:00:00Z")]
    store.materialize(rows)
    for source_id, display_name, channel_id, uploads_id in sources:
        latest = max(row.published_at for row in rows if row.source_id == source_id)
        store.update_source_state(source_id=source_id, display_name=display_name, channel_id=channel_id, channel_title=display_name, uploads_playlist_id=uploads_id, observed_at="2026-08-30T20:00:00Z", latest_published_at=latest, health="healthy", error=None, item_count=sum(row.source_id == source_id for row in rows), api_calls=3, quota_units_estimated=3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--store-root", type=Path, required=True); args = parser.parse_args(argv); seed(args.store_root); return 0


if __name__ == "__main__": raise SystemExit(main())
