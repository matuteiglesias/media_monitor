import json
from pathlib import Path

import pytest

from scripts.adopter_review import materialize_queue, read_decisions, record_decision


REPO = Path(__file__).resolve().parents[1]
DRAFT_FIXTURE = REPO / "contracts" / "tests" / "fixtures" / "news_article_draft.example.json"


def _draft_file(tmp_path: Path) -> Path:
    draft = json.loads(DRAFT_FIXTURE.read_text(encoding="utf-8"))
    path = tmp_path / "draft.jsonl"
    path.write_text(json.dumps(draft, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def test_materialize_review_queue_exposes_draft_evidence_and_no_publish_effect(tmp_path: Path) -> None:
    draft_path = _draft_file(tmp_path)
    out = tmp_path / "review"
    decisions = tmp_path / "review_decisions.jsonl"
    published_bus = tmp_path / "published"

    queue = materialize_queue(
        [draft_path],
        out_dir=out,
        decisions_path=decisions,
        published_bus_dir=published_bus,
    )

    assert queue["status"] == "ready_for_human_review"
    assert queue["draft_count"] == 1
    assert queue["publication_authority"] == "explicit_human_approval_required"
    item = queue["items"][0]
    assert item["draft_id"] == "draft_article_2026_03_14_01"
    assert item["source_links"] == ["https://example.com/official-announcement"]
    assert item["citations"]
    assert item["fact_check_flags"]
    assert item["revision_notes"]

    markdown = (out / "review_queue.md").read_text(encoding="utf-8")
    assert "Verificar cifra de crecimiento interanual" in markdown
    assert "--decision approve --approve-human" in markdown
    assert str(published_bus) in markdown
    assert not decisions.exists()
    assert not published_bus.exists()


def test_hold_decision_is_audited_without_publication(tmp_path: Path) -> None:
    draft_path = _draft_file(tmp_path)
    decisions = tmp_path / "decisions.jsonl"
    published_bus = tmp_path / "published"

    record = record_decision(
        draft_path=draft_path,
        decisions_path=decisions,
        decision="hold",
        reviewer="pilot-analyst",
        note="Need a second source before approval.",
    )

    assert record["decision"] == "hold"
    assert record["publication_effect"] == "none"
    assert record["article_id"] is None
    assert record["published_path"] is None
    assert not published_bus.exists()
    rows = read_decisions(decisions)
    assert rows == [record]


def test_approve_refuses_without_explicit_human_gate(tmp_path: Path) -> None:
    draft_path = _draft_file(tmp_path)
    with pytest.raises(ValueError, match="--approve-human"):
        record_decision(
            draft_path=draft_path,
            decisions_path=tmp_path / "decisions.jsonl",
            decision="approve",
            reviewer="pilot-editor",
            note="Reviewed against attached sources.",
            published_bus_dir=tmp_path / "published",
        )


def test_approve_requires_explicit_isolated_published_bus(tmp_path: Path) -> None:
    draft_path = _draft_file(tmp_path)
    with pytest.raises(ValueError, match="published-bus-dir"):
        record_decision(
            draft_path=draft_path,
            decisions_path=tmp_path / "decisions.jsonl",
            decision="approve",
            reviewer="pilot-editor",
            note="Reviewed against attached sources.",
            approve_human=True,
        )


def test_explicit_human_approval_publishes_only_to_selected_bus_and_journals_decision(tmp_path: Path) -> None:
    draft_path = _draft_file(tmp_path)
    decisions = tmp_path / "decisions.jsonl"
    published_bus = tmp_path / "isolated" / "published_article" / "v1"

    record = record_decision(
        draft_path=draft_path,
        decisions_path=decisions,
        decision="approve",
        reviewer="pilot-editor",
        note="Sources and claims reviewed; approve for isolated pilot publication.",
        approve_human=True,
        published_bus_dir=published_bus,
    )

    assert record["decision"] == "approve"
    assert record["publication_effect"] == "published"
    assert record["article_id"].startswith("article_")
    published_path = Path(record["published_path"])
    assert published_path.parent == published_bus
    assert published_path.exists()
    article = json.loads(published_path.read_text(encoding="utf-8"))
    assert article["draft_id"] == "draft_article_2026_03_14_01"
    assert article["review_status"] == "human_approved"
    assert read_decisions(decisions)[0]["article_id"] == article["article_id"]


def test_second_approve_of_same_draft_is_refused_by_decision_journal(tmp_path: Path) -> None:
    draft_path = _draft_file(tmp_path)
    decisions = tmp_path / "decisions.jsonl"
    published_bus = tmp_path / "published"

    record_decision(
        draft_path=draft_path,
        decisions_path=decisions,
        decision="approve",
        reviewer="pilot-editor",
        note="First explicit approval.",
        approve_human=True,
        published_bus_dir=published_bus,
    )

    with pytest.raises(ValueError, match="already has an approve decision"):
        record_decision(
            draft_path=draft_path,
            decisions_path=decisions,
            decision="approve",
            reviewer="pilot-editor",
            note="Second approval should be denied.",
            approve_human=True,
            published_bus_dir=published_bus,
        )
