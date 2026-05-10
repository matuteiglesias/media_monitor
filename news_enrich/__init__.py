"""Import shim for running `python -m news_enrich.*` from the repo root."""

from __future__ import annotations

from pathlib import Path

_source_package = Path(__file__).resolve().parents[1] / "apps" / "news_enrich" / "src" / "news_enrich"
__path__.append(str(_source_package))
