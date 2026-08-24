import json
import subprocess
import sys

from test_build_site_snapshot import (
    ROOT,
    canonical_context_id,
    config,
    inputs,
    published_article,
    run,
    write_jsonl,
)


def validate(tmp_path):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate_site_snapshot.py"),
            "--site-id",
            "test",
            "--digest-at",
            "20260721T18",
            "--sites-dir",
            str(tmp_path / "sites"),
            "--input",
            str(tmp_path / "out.json"),
            "--now",
            "2026-07-21T18:30:00Z",
        ],
        capture_output=True,
        text=True,
    )


def test_validate_snapshot_with_publication_signals_and_context(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    write_jsonl(
        tmp_path / "indexes/published_articles_latest.jsonl", [published_article()]
    )
    run(tmp_path)
    result = validate(tmp_path)
    assert result.returncode == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["published_article_count"] == 1
    assert payload["story_context_count"] == 5


def test_validate_rejects_top_level_tamper(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    run(tmp_path)
    path = tmp_path / "out.json"
    snapshot = json.loads(path.read_text())
    snapshot["status"] = "bad"
    path.write_text(json.dumps(snapshot))
    assert validate(tmp_path).returncode == 1


def test_validate_rejects_publication_ref_tamper(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    write_jsonl(
        tmp_path / "indexes/published_articles_latest.jsonl", [published_article()]
    )
    run(tmp_path)
    path = tmp_path / "out.json"
    snapshot = json.loads(path.read_text())
    snapshot["publication"]["latest"][0]["title"] = "Tampered title"
    path.write_text(json.dumps(snapshot))
    result = validate(tmp_path)
    assert result.returncode == 1


def test_validate_rejects_story_context_projection_tamper(tmp_path):
    config(tmp_path)
    inputs(tmp_path)
    run(tmp_path)
    path = tmp_path / "out.json"
    snapshot = json.loads(path.read_text())
    index_id = snapshot["signals"]["latest"][0]["index_id"]
    context = snapshot["story_contexts"][index_id]
    context["coverage_count"] = 2
    context["context_id"] = canonical_context_id(context)
    path.write_text(json.dumps(snapshot))
    result = validate(tmp_path)
    assert result.returncode == 1
    assert "provenance artifact" in result.stdout or "snapshot_id" in result.stdout
