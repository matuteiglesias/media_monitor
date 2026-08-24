from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.promote_draft_to_published as promote_module
from scripts.rehearse_c3_editorial_tranche import (
    DEFAULT_CANDIDATES,
    DEFAULT_LEDGER,
    SIMULATED_REVIEW_STATUS,
    read_jsonl,
    rehearse,
    validate_ledger,
)


def test_rehearsal_promotes_only_simulated_approvals_to_isolated_bus(tmp_path, monkeypatch):
    production_sentinel = tmp_path / "production-published-bus"
    monkeypatch.setattr(promote_module, "PUBLISHED_BUS", production_sentinel)

    out = tmp_path / "rehearsal"
    report = rehearse(DEFAULT_CANDIDATES, DEFAULT_LEDGER, out)

    assert report["status"] == "ready_for_real_human_gate"
    assert report["candidate_count"] == 3
    assert report["decision_counts"]["SIMULATED_APPROVE"] == 2
    assert report["decision_counts"]["SIMULATED_REVISE"] == 1
    assert report["simulated_promoted_count"] == 2
    assert report["real_publication_performed"] is False
    assert report["production_bus_touched"] is False
    assert not production_sentinel.exists()

    rows = []
    for path in sorted((out / "simulated_published").glob("*.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)
    assert len(rows) == 2
    assert all(row["schema_name"] == "published_article.v1" for row in rows)
    assert all(row["review_status"] == SIMULATED_REVIEW_STATUS for row in rows)
    assert all(row["review_status"] != "human_approved" for row in rows)
    assert {row["draft_id"] for row in rows} == {"c3-cpi-july-2026", "c3-trade-july-2026"}

    index_rows = [
        json.loads(line)
        for line in (out / "indexes/published_articles_latest.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(index_rows) == 2


def test_rehearsal_candidates_are_real_schema_valid_drafts():
    candidates = read_jsonl(DEFAULT_CANDIDATES)
    assert {candidate["topic"] for candidate in candidates} == {
        "Inflación y Precios",
        "Sector Externo",
        "Actividad y Consumo",
    }
    assert all(candidate["source_links"] for candidate in candidates)
    assert all(candidate["citations"] for candidate in candidates)


def test_rehearsal_ledger_cannot_smuggle_real_approval():
    candidates = read_jsonl(DEFAULT_CANDIDATES)
    ledger = json.loads(DEFAULT_LEDGER.read_text(encoding="utf-8"))
    ledger["reviews"][0]["decision"] = "human_approved"
    with pytest.raises(ValueError, match="invalid simulated review entry"):
        validate_ledger(ledger, candidates)


def test_real_cli_gate_still_refuses_without_explicit_human_approval(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        ["promote_draft_to_published.py", "--draft-id", "c3-trade-july-2026"],
    )
    with pytest.raises(SystemExit, match="refusing to publish without --approve-human"):
        promote_module.main()
