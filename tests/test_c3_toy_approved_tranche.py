from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import promote_draft_to_published as promote_module
from materialize_toy_approved_tranche import materialize


def test_toy_approval_exercises_real_human_approved_path_without_touching_production(tmp_path):
    production_bus = promote_module.PUBLISHED_BUS
    before = sorted(production_bus.glob("*.jsonl")) if production_bus.exists() else []

    manifest = materialize(output_dir=tmp_path)

    assert manifest["scope"] == "SIMULATED_TOY_HUMAN_APPROVAL_NOT_PUBLICATION"
    assert manifest["not_for_publication"] is True
    assert manifest["production_bus_touched"] is False
    assert manifest["candidate_count"] == 3
    assert manifest["approved_count"] == 2
    assert manifest["held_or_revise_count"] == 1
    assert {row["draft_id"] for row in manifest["articles"]} == {
        "c3-cpi-july-2026",
        "c3-trade-july-2026",
    }
    assert all(row["review_status"] == "human_approved" for row in manifest["articles"])

    latest = Path(manifest["published_index_path"])
    rows = [json.loads(line) for line in latest.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2
    assert all(row["schema_name"] == "published_article.v1" for row in rows)
    assert all(row["review_status"] == "human_approved" for row in rows)

    after = sorted(production_bus.glob("*.jsonl")) if production_bus.exists() else []
    assert before == after
    assert promote_module.PUBLISHED_BUS == production_bus


def test_toy_manifest_is_explicitly_not_publication_authority(tmp_path):
    manifest = materialize(output_dir=tmp_path)
    text = json.dumps(manifest)
    assert "NOT_PUBLICATION" in text
    assert manifest["not_for_publication"] is True
