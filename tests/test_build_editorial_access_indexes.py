import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_editorial_access_indexes.py"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_editorial_access_indexes_with_partial_data(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"
    digest = "20260314T20"

    _write_jsonl(
        data / "pf_out" / f"pfout_{digest}.jsonl",
        [
            {
                "digest_group_id": "20260314T20::A::Economia::01",
                "seed_ideas": {
                    "seed_ideas": [
                        {"idea_id": "EC01"},
                        {"idea_id": "EC02"},
                    ]
                },
            }
        ],
    )

    _write_jsonl(
        storage / "buses" / "news_piece_brief" / "v1" / "npb_1.jsonl",
        [
            {
                "schema_name": "news_piece_brief.v1",
                "digest_id_hour": digest,
                "brief_id": "npb_1",
                "format_candidates": ["yt_script", "article"],
            }
        ],
    )

    _write_jsonl(data / "drafts" / digest / "abc123.jsonl", [{"index_id": "abc123"}])

    _write_jsonl(
        data / "quarantine" / f"V05_05_explode_pf_outputs:{digest}.jsonl",
        [{"reason": "missing_piece_briefs_fallback_legacy", "digest_id": digest}],
    )
    _write_jsonl(
        data / "quarantine" / f"V06_06_build_piece_briefs:{digest}.jsonl",
        [{"reason": "schema_validation_error", "brief_id": "npb_bad"}],
    )

    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--storage-dir",
            str(storage),
            "--data-dir",
            str(data),
            "--digest-at",
            digest,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "status=degraded" in out.stdout

    latest = storage / "indexes" / "editorial_latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["digest_at"] == digest
    assert payload["metrics"]["seed_ideas_emitted"] == 2
    assert payload["metrics"]["briefs_emitted"] == 1
    assert payload["metrics"]["drafts_emitted"] == 1
    assert payload["metrics"]["fallback_legacy_count"] == 1
    assert payload["metrics"]["schema_failures"] == 1
    assert payload["contract_inputs"] == {"piece_brief_bus": True, "article_draft_bus": False, "yt_script_draft_bus": False}
    assert payload["fallback_inputs"] == {"pf_out": False, "data_drafts": True, "quarantine": True}
    assert payload["status"] == "degraded"
    assert payload["human_handoff"]["status"] == "needs-attention"
    assert len(payload["human_handoff"]["latest_briefs"]) == 1
    assert len(payload["human_handoff"]["latest_article_drafts"]) == 1
    assert payload["human_handoff"]["latest_yt_script_drafts"] == []
    assert payload["human_handoff"]["latest_briefs"][0]["target_format"] == "yt_script"
    assert len(payload["human_handoff"]["fallback_events"]) >= 1
    assert payload["human_handoff"]["action_candidates"][0]["target_format"] in {"article", "yt_script"}


def test_build_editorial_access_indexes_no_data(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--storage-dir",
            str(storage),
            "--data-dir",
            str(data),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    latest = storage / "indexes" / "editorial_latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    assert payload["digest_at"] is None
    assert payload["status"] == "no-data"
    assert payload["metrics"]["seed_ideas_emitted"] == 0
    assert payload["human_handoff"]["status"] == "no-data"
    assert payload["contract_inputs"] == {"piece_brief_bus": False, "article_draft_bus": False, "yt_script_draft_bus": False}
    assert payload["fallback_inputs"] == {"pf_out": False, "data_drafts": False, "quarantine": False}
    assert payload["human_handoff"]["latest_briefs"] == []


def test_build_editorial_access_indexes_separates_yt_drafts(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"
    digest = "20260315T01"

    _write_jsonl(
        data / "pf_out" / f"pfout_{digest}.jsonl",
        [{"digest_group_id": f"{digest}::A::Economia::01", "seed_ideas": {"seed_ideas": [{"idea_id": "I1"}]}}],
    )
    _write_jsonl(
        storage / "buses" / "news_piece_brief" / "v1" / "npb_1.jsonl",
        [{"schema_name": "news_piece_brief.v1", "digest_id_hour": digest, "brief_id": "npb_1", "topic": "Economia"}],
    )
    _write_jsonl(
        data / "drafts" / digest / "article_1.jsonl",
        [{"schema_name": "news_article_draft.v1", "index_id": "A1", "topic": "Economia", "headline": "H1"}],
    )
    _write_jsonl(
        data / "drafts" / digest / "yt_1.jsonl",
        [{"schema_name": "news_yt_script_draft.v1", "index_id": "Y1", "topic": "Economia", "headline": "YT1"}],
    )

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--storage-dir",
            str(storage),
            "--data-dir",
            str(data),
            "--digest-at",
            digest,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads((storage / "indexes" / "editorial_latest.json").read_text(encoding="utf-8"))
    assert len(payload["human_handoff"]["latest_article_drafts"]) == 1
    assert len(payload["human_handoff"]["latest_yt_script_drafts"]) == 1
    assert payload["human_handoff"]["action_candidates"][0]["target_format"] == "yt_script"
    assert payload["human_handoff"]["action_candidates"][0]["ready_state"] == "draft-ready"


def test_build_editorial_access_indexes_prefers_draft_buses_without_pf_or_data_drafts(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"
    digest = "20260316T02"

    _write_jsonl(
        storage / "buses" / "news_piece_brief" / "v1" / "npb_bus.jsonl",
        [
            {
                "schema_name": "news_piece_brief.v1",
                "digest_id_hour": digest,
                "brief_id": "npb_bus",
                "topic": "Economia",
                "working_title": "Brief bus title",
                "format_candidates": ["both"],
            }
        ],
    )
    _write_jsonl(
        storage / "buses" / "news_article_draft" / "v1" / "article_npb_bus.jsonl",
        [
            {
                "schema_name": "news_article_draft.v1",
                "schema_status": "experimental_structured",
                "draft_id": "article_npb_bus",
                "brief_id": "npb_bus",
                "title": "Article draft title",
                "dek": "Article dek",
                "lede": "Article lede",
                "sections": [{"section_id": "sec_1", "heading": "Heading", "summary": "Summary"}],
                "body_markdown": "# Article draft title",
                "citations": [],
                "fact_check_flags": [],
                "revision_notes": [],
            }
        ],
    )
    _write_jsonl(
        storage / "buses" / "news_yt_script_draft" / "v1" / "yt_npb_bus.jsonl",
        [
            {
                "schema_name": "news_yt_script_draft.v1",
                "schema_status": "experimental_structured",
                "script_id": "yt_npb_bus",
                "brief_id": "npb_bus",
                "title": "YT draft title",
                "thumbnail_hook": "Hook",
                "cold_open": "Cold open",
                "segment_outline": [{"segment_id": "seg_1", "heading": "Heading", "beat": "Beat", "estimated_seconds": 30}],
                "full_script": "Full script",
                "voice_notes": [],
                "visual_notes": [],
                "citations": [],
            }
        ],
    )

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--storage-dir",
            str(storage),
            "--data-dir",
            str(data),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads((storage / "indexes" / "editorial_latest.json").read_text(encoding="utf-8"))
    assert payload["digest_at"] == digest
    assert payload["status"] == "ok"
    assert payload["human_handoff"]["status"] == "ready"
    assert payload["metrics"]["seed_ideas_emitted"] == 0
    assert payload["metrics"]["briefs_emitted"] == 1
    assert payload["metrics"]["drafts_emitted"] == 2
    assert payload["contract_inputs"] == {"piece_brief_bus": True, "article_draft_bus": True, "yt_script_draft_bus": True}
    assert payload["fallback_inputs"] == {"pf_out": False, "data_drafts": False, "quarantine": False}
    assert payload["pointers"]["pf_outputs"] == []
    assert payload["pointers"]["draft_files"] == []
    assert len(payload["human_handoff"]["latest_article_drafts"]) == 1
    assert len(payload["human_handoff"]["latest_yt_script_drafts"]) == 1
    assert payload["human_handoff"]["action_candidates"][0]["target_format"] == "yt_script"


def test_build_editorial_access_indexes_normalizes_missing_draft_bus_topics(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"
    digest = "20260713T21"
    digest_group_id = f"{digest}::A::Science::01"

    _write_jsonl(
        storage / "buses" / "news_digest_group" / "v1" / "groups.jsonl",
        [
            {
                "schema_name": "news_digest_group.v1",
                "schema_status": "experimental_structured",
                "digest_group_id": digest_group_id,
                "digest_id_hour": digest,
                "window_type": "A",
                "topic": "Science",
                "group_number": 1,
                "content": [],
            }
        ],
    )
    _write_jsonl(
        storage / "buses" / "news_piece_brief" / "v1" / "briefs.jsonl",
        [
            {
                "schema_name": "news_piece_brief.v1",
                "digest_id_hour": digest,
                "digest_group_id": digest_group_id,
                "brief_id": "npb_science",
                "topic": "",
                "working_title": "Brief title",
                "format_candidates": ["article"],
            }
        ],
    )
    _write_jsonl(
        storage / "buses" / "news_article_draft" / "v1" / "article.jsonl",
        [
            {
                "schema_name": "news_article_draft.v1",
                "schema_status": "experimental_structured",
                "draft_id": "article_npb_science",
                "brief_id": "npb_science",
                "topic": "",
                "title": "Article draft title",
                "dek": "Article dek",
            }
        ],
    )
    _write_jsonl(
        storage / "buses" / "news_yt_script_draft" / "v1" / "yt.jsonl",
        [
            {
                "schema_name": "news_yt_script_draft.v1",
                "schema_status": "experimental_structured",
                "script_id": "yt_npb_science",
                "brief_id": "npb_science",
                "title": "YT draft title",
                "thumbnail_hook": "Hook",
                "cold_open": "Cold open",
            }
        ],
    )

    subprocess.run(
        [sys.executable, str(SCRIPT), "--storage-dir", str(storage), "--data-dir", str(data), "--digest-at", digest],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads((storage / "indexes" / "editorial_latest.json").read_text(encoding="utf-8"))
    handoff = payload["human_handoff"]
    records = (
        handoff["latest_briefs"]
        + handoff["latest_article_drafts"]
        + handoff["latest_yt_script_drafts"]
        + handoff["action_candidates"]
    )
    assert records
    assert all(record["topic"] == "Science" for record in records)
