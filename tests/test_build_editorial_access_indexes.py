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
    assert payload["status"] == "degraded"
    assert payload["human_handoff"]["status"] == "needs-attention"
    assert len(payload["human_handoff"]["latest_briefs"]) == 1
    assert len(payload["human_handoff"]["latest_article_drafts"]) == 1
    assert payload["human_handoff"]["latest_yt_script_drafts"] == []
    assert len(payload["human_handoff"]["fallback_events"]) >= 1


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
