from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_pr3a_buses.py"


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _schema(name: str) -> dict:
    return json.loads((ROOT / "contracts" / "schemas" / name).read_text(encoding="utf-8"))


def test_export_pr3a_generates_non_empty_buses_and_valid_contracts(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"

    _write_csv(
        data / "master_ref.csv",
        [
            {
                "index_id": "ABCDEFGHJK",
                "source": "EL PAIS",
                "link": "https://elpais.com/economia/example",
                "first_seen": "2026-03-13T15:00:00Z",
                "last_seen": "2026-03-13T15:00:00Z",
                "topics": '["Economia"]',
                "meta": '{"ingest": "rss"}',
            }
        ],
    )

    _write_csv(
        data / "digest_map" / "20260313T15.csv",
        [
            {
                "digest_file": "digest_A_20260313T15.csv",
                "article_id": "42",
                "index_id": "ABCDEFGHJK",
                "Title": "Inflación baja",
                "Source": "EL PAIS",
                "Link": "https://elpais.com/economia/example",
                "Published": "2026-03-13T15:00:00Z",
                "window_type": "A",
                "Topic": "Economia",
            }
        ],
    )

    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--digest-at",
            "20260313T15",
            "--data-dir",
            str(data),
            "--storage-dir",
            str(storage),
            "--contracts-dir",
            str(ROOT / "contracts"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "status=exported" in out.stdout

    ref_files = sorted((storage / "buses" / "news_ref" / "v1").glob("news_ref_*.jsonl"))
    dg_files = sorted((storage / "buses" / "news_digest_group" / "v1").glob("news_digest_group_*.jsonl"))
    assert ref_files and dg_files

    ref_rows = [json.loads(x) for x in ref_files[-1].read_text(encoding="utf-8").splitlines() if x.strip()]
    dg_rows = [json.loads(x) for x in dg_files[-1].read_text(encoding="utf-8").splitlines() if x.strip()]
    assert ref_rows and dg_rows

    ref_validator = Draft202012Validator(_schema("news_ref.v1.json"))
    dg_validator = Draft202012Validator(_schema("news_digest_group.v1.json"))
    assert not list(ref_validator.iter_errors(ref_rows[0]))
    assert not list(dg_validator.iter_errors(dg_rows[0]))


def test_export_pr3a_noop_when_missing_input(tmp_path: Path):
    storage = tmp_path / "storage"
    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--digest-at",
            "20260313T15",
            "--data-dir",
            str(tmp_path / "data"),
            "--storage-dir",
            str(storage),
            "--contracts-dir",
            str(ROOT / "contracts"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "status=noop" in out.stdout

    latest_index = storage / "indexes" / "pr3a_exports_latest.json"
    payload = json.loads(latest_index.read_text(encoding="utf-8"))
    assert all(r["status"] == "noop" for r in payload["results"])
