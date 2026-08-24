from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_demo_outlet import build_demo


def test_demo_is_deterministic_offline_and_does_not_touch_production(tmp_path: Path) -> None:
    production_snapshot = ROOT / "apps/news_site/public/data/site_snapshot.json"
    before = production_snapshot.read_bytes() if production_snapshot.exists() else None

    first = build_demo(tmp_path / "demo")
    first_snapshot = json.loads((tmp_path / "demo/site_snapshot.json").read_text(encoding="utf-8"))
    second = build_demo(tmp_path / "demo")
    second_snapshot = json.loads((tmp_path / "demo/site_snapshot.json").read_text(encoding="utf-8"))

    assert first["snapshot_id"] == second["snapshot_id"]
    assert first_snapshot["snapshot_id"] == second_snapshot["snapshot_id"]
    assert first["scope"] == "DETERMINISTIC_FIXTURE_NOT_LIVE_NEWS"
    assert first["network_used"] is False
    assert first["llm_used"] is False
    assert first["database_used"] is False
    assert first["deployment_credentials_used"] is False
    assert first["signal_count"] >= 5
    assert first["curated_signal_count"] >= 5
    assert first["story_context_count"] >= 5
    assert first["published_article_count"] == 0
    assert first_snapshot["schema_name"] == "site_snapshot.v4"
    assert first_snapshot["signals"]["curated"]
    assert first_snapshot["story_contexts"]

    after = production_snapshot.read_bytes() if production_snapshot.exists() else None
    assert after == before


def test_bin_media_exposes_demo_before_operational_cli() -> None:
    wrapper = (ROOT / "bin/media").read_text(encoding="utf-8")
    assert 'if [ "${1:-}" = "demo" ]' in wrapper
    assert "scripts/build_demo_outlet.py" in wrapper
    assert wrapper.index("scripts/build_demo_outlet.py") < wrapper.index("scripts/media_ops.py")
