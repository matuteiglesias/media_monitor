import json
import subprocess
import sys

from test_build_site_snapshot import (
    ROOT,
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


def test_validate_snapshot_with_publication_and_signals(tmp_path):
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
