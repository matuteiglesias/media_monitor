import json
import subprocess
import sys
from pathlib import Path


MODULE = "apps.news_editorial.src.news_editorial.handoff_packet"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(index_path: Path, out_dir: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", MODULE, "--index", str(index_path), "--out", str(out_dir)],
        check=True,
        capture_output=True,
        text=True,
    )


def test_materialize_editorial_handoff_packet_writes_required_files(tmp_path: Path):
    index_path = tmp_path / "storage" / "indexes" / "editorial_latest.json"
    out_dir = tmp_path / "artifacts" / "editorial_handoff" / "latest"

    _write_json(
        index_path,
        {
            "digest_at": "20260523T11",
            "status": "ok",
            "contract_inputs": {"piece_brief_bus": True, "article_draft_bus": True, "yt_script_draft_bus": False},
            "fallback_inputs": {"pf_out": False, "data_drafts": False, "quarantine": False},
            "pointers": {"brief_files": ["storage/buses/news_piece_brief/v1/npb_1.jsonl"]},
            "human_handoff": {
                "action_candidates": [
                    {
                        "title": "Candidate title",
                        "topic": "Economy",
                        "target_format": "article",
                        "ready_state": "draft-ready",
                        "source": "draft",
                        "path": "storage/buses/news_article_draft/v1/article_1.jsonl",
                    }
                ]
            },
        },
    )

    _run(index_path, out_dir)

    assert (out_dir / "README.md").exists()
    assert (out_dir / "publication_candidates.md").exists()
    assert (out_dir / "fallback_status.md").exists()
    assert (out_dir / "editorial_latest.copy.json").exists()
    assert (out_dir / "provenance.json").exists()

    provenance = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert "candidate_count" in provenance
    assert provenance["candidate_count"] == 1


def test_materialize_editorial_handoff_packet_no_data_input(tmp_path: Path):
    index_path = tmp_path / "storage" / "indexes" / "editorial_latest.json"
    out_dir = tmp_path / "artifacts" / "editorial_handoff" / "latest"
    _write_json(index_path, {})

    _run(index_path, out_dir)

    publication_md = (out_dir / "publication_candidates.md").read_text(encoding="utf-8")
    assert "No candidates available" in publication_md

    provenance = json.loads((out_dir / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["candidate_count"] == 0

    source_pointers = json.loads((out_dir / "source_pointers.json").read_text(encoding="utf-8"))
    assert source_pointers["pointers"] == {}
