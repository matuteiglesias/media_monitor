from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_story_contexts.py"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def setup_inputs(tmp_path: Path, with_groups: bool = True) -> Path:
    storage = tmp_path / "storage"
    digest = "20260824T20"
    refs = [
        {
            "digest_at": digest,
            "index_id": "signal-a",
            "title": "Inflación: nuevo dato oficial",
            "source": "Fuente A",
            "published_at": "2026-08-24T19:45:00Z",
            "topic": "Inflación y Precios",
            "link": "https://example.com/a",
        },
        {
            "digest_at": digest,
            "index_id": "signal-b",
            "title": "Otra mirada sobre la inflación",
            "source": "Fuente B",
            "published_at": "2026-08-24T19:10:00Z",
            "topic": "Inflación y Precios",
            "link": "https://example.com/b",
        },
    ]
    write_jsonl(storage / "indexes/news_recent_refs_latest.jsonl", refs)
    write_json(
        storage / "indexes/editorial_selection_latest.json",
        {
            "schema_name": "editorial_selection.v1",
            "selection_id": "d" * 64,
            "digest_at": digest,
            "selected": [
                {
                    "index_id": "signal-a",
                    "rank": 1,
                    "score": 88,
                    "reason_codes": ["fresh_under_120m", "high_topic_priority"],
                }
            ],
        },
    )

    if with_groups:
        group_path = storage / "buses/news_digest_group/v1/news_digest_group_20260824T20.jsonl"
        write_jsonl(
            group_path,
            [
                {
                    "schema_name": "news_digest_group.v1",
                    "schema_status": "experimental_structured",
                    "digest_group_id": "20260824T20:4h_window:Inflación y Precios:1",
                    "digest_id_hour": digest,
                    "window_type": "4h_window",
                    "topic": "Inflación y Precios",
                    "group_number": 1,
                    "content": [
                        {
                            "article_id": "a",
                            "title": refs[0]["title"],
                            "source": refs[0]["source"],
                            "link": refs[0]["link"],
                            "published": refs[0]["published_at"],
                        },
                        {
                            "article_id": "b",
                            "title": refs[1]["title"],
                            "source": refs[1]["source"],
                            "link": refs[1]["link"],
                            "published": refs[1]["published_at"],
                        },
                    ],
                }
            ],
        )
        write_json(
            storage / "indexes/pr3a_exports_latest.json",
            {
                "digest_at": digest,
                "status": "exported",
                "results": [
                    {
                        "name": "news_digest_group.v1",
                        "status": "exported",
                        "output_path": str(group_path),
                    }
                ],
            },
        )
    return storage


def run(storage: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--storage-dir",
            str(storage),
            "--digest-at",
            "20260824T20",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def read_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_cluster_context_is_deterministic_and_carries_coverage_and_curation(tmp_path: Path) -> None:
    storage = setup_inputs(tmp_path)
    output = storage / "indexes/story_contexts_latest.jsonl"
    result = run(storage, output)
    assert result.returncode == 0, result.stdout + result.stderr
    first = output.read_bytes()
    result2 = run(storage, output)
    assert result2.returncode == 0, result2.stdout + result2.stderr
    assert output.read_bytes() == first

    rows = {row["index_id"]: row for row in read_rows(output)}
    context = rows["signal-a"]
    assert context["schema_name"] == "story_context.v1"
    assert context["coverage_count"] == 2
    assert context["source_count"] == 2
    assert context["sources"] == ["Fuente A", "Fuente B"]
    assert context["group_ids"] == ["20260824T20:4h_window:Inflación y Precios:1"]
    assert context["window_types"] == ["4h_window"]
    assert context["related_signals"][0]["index_id"] == "signal-b"
    assert context["curation"] == {
        "selected": True,
        "rank": 1,
        "score": 88,
        "reason_codes": ["fresh_under_120m", "high_topic_priority"],
    }
    assert len(context["context_id"]) == 64


def test_missing_group_bus_degrades_to_truthful_singleton_context(tmp_path: Path) -> None:
    storage = setup_inputs(tmp_path, with_groups=False)
    output = storage / "indexes/story_contexts_latest.jsonl"
    result = run(storage, output)
    assert result.returncode == 0, result.stdout + result.stderr
    rows = read_rows(output)
    assert all(row["coverage_count"] == 1 for row in rows)
    assert all(row["group_ids"] == [] for row in rows)
    assert all(row["related_signals"] == [] for row in rows)
    assert all(row["provenance"]["groups_path"] is None for row in rows)


def test_selection_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    storage = setup_inputs(tmp_path)
    path = storage / "indexes/editorial_selection_latest.json"
    selection = json.loads(path.read_text(encoding="utf-8"))
    selection["digest_at"] = "20260824T19"
    write_json(path, selection)
    result = run(storage, storage / "indexes/story_contexts_latest.jsonl")
    assert result.returncode == 1
    assert "another digest" in result.stdout


def test_context_builder_has_no_draft_or_promptflow_dependency() -> None:
    source = SCRIPT.read_text(encoding="utf-8").lower()
    for forbidden in ("promptflow", "news_article_draft", "editorial_latest"):
        assert forbidden not in source
