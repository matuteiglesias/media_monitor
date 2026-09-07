from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from scripts import bounded_storage


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


def _run_export(data: Path, storage: Path, digest_at: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--digest-at",
            digest_at,
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


def test_export_pr3a_generates_non_empty_buses_and_valid_contracts(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"

    _write_csv(
        data / "master_ref.csv",
        [
            {
                "index_id": "15ef8990d6",
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
                "index_id": "15ef8990d6",
                "Title": "Inflación baja",
                "Source": "EL PAIS",
                "Link": "https://elpais.com/economia/example",
                "Published": "2026-03-13T15:00:00Z",
                "window_type": "4h_window",
                "Topic": "Economia",
            }
        ],
    )

    out = _run_export(data, storage, "20260313T15")
    assert "status=exported" in out.stdout

    ref_files = sorted((storage / "buses" / "news_ref" / "v1").glob("news_ref_*.jsonl"))
    dg_files = sorted((storage / "buses" / "news_digest_group" / "v1").glob("news_digest_group_*.jsonl"))
    assert ref_files and dg_files

    ref_rows = [json.loads(x) for x in ref_files[-1].read_text(encoding="utf-8").splitlines() if x.strip()]
    dg_rows = [json.loads(x) for x in dg_files[-1].read_text(encoding="utf-8").splitlines() if x.strip()]
    assert ref_rows and dg_rows
    assert dg_rows[0]["window_type"] == "4h_window"

    ref_validator = Draft202012Validator(_schema("news_ref.v1.json"))
    dg_validator = Draft202012Validator(_schema("news_digest_group.v1.json"))
    assert not list(ref_validator.iter_errors(ref_rows[0]))
    assert not list(dg_validator.iter_errors(dg_rows[0]))


def test_export_pr3a_accepts_8_char_index_id_and_validates_schema(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"

    _write_csv(
        data / "master_ref.csv",
        [
            {
                "index_id": "15ef8990",
                "source": "EL PAIS",
                "link": "https://elpais.com/economia/example-8",
                "first_seen": "2026-03-13T16:00:00Z",
                "last_seen": "2026-03-13T16:00:00Z",
                "topics": '["Economia"]',
                "meta": '{"ingest": "rss"}',
            }
        ],
    )

    _write_csv(
        data / "digest_map" / "20260313T16.csv",
        [
            {
                "digest_file": "digest_A_20260313T16.csv",
                "article_id": "43",
                "index_id": "15ef8990",
                "Title": "Mercado se estabiliza",
                "Source": "EL PAIS",
                "Link": "https://elpais.com/economia/example-8",
                "Published": "2026-03-13T16:00:00Z",
                "window_type": "4h_window",
                "Topic": "Economia",
            }
        ],
    )

    out = _run_export(data, storage, "20260313T16")
    assert "status=exported" in out.stdout

    ref_files = sorted((storage / "buses" / "news_ref" / "v1").glob("news_ref_*.jsonl"))
    assert ref_files
    ref_rows = [json.loads(x) for x in ref_files[-1].read_text(encoding="utf-8").splitlines() if x.strip()]
    assert ref_rows
    assert ref_rows[0]["index_id"] == "15ef8990"

    ref_validator = Draft202012Validator(_schema("news_ref.v1.json"))
    assert not list(ref_validator.iter_errors(ref_rows[0]))


def test_export_pr3a_noop_when_missing_input(tmp_path: Path):
    storage = tmp_path / "storage"
    out = _run_export(tmp_path / "data", storage, "20260313T15")
    assert "status=noop" in out.stdout

    latest_index = storage / "indexes" / "pr3a_exports_latest.json"
    payload = json.loads(latest_index.read_text(encoding="utf-8"))
    assert all(r["status"] == "noop" for r in payload["results"])


def test_news_ref_identical_cross_digest_cycle_keeps_one_payload(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"
    rows = [
        {
            "index_id": "same1234",
            "source": "Reuters",
            "link": "https://example.com/same",
            "first_seen": "2026-03-13T15:00:00Z",
            "last_seen": "2026-03-13T15:00:00Z",
            "topics": '["Economy"]',
            "meta": '{"title": "Same story"}',
            "digest_file": "stable.csv",
            "article_id": "stable-1",
        }
    ]
    _write_csv(data / "master_ref.csv", rows)

    first = _run_export(data, storage, "20260313T15")
    second = _run_export(data, storage, "20260313T16")
    assert "news_ref.v1 status=exported" in first.stdout
    assert "news_ref.v1 status=skipped_duplicate" in second.stdout

    bus_dir = storage / "buses" / "news_ref" / "v1"
    payloads = sorted(bus_dir.glob("news_ref_*.jsonl"))
    assert payloads == [bus_dir / "news_ref_current.jsonl"]

    manifests = sorted(bus_dir.glob("manifest_*.json"))
    assert manifests
    latest_manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert latest_manifest["status"] == "unchanged"
    assert latest_manifest["content_sha256"] == latest_manifest["previous_content_sha256"]
    assert latest_manifest["added_count"] == 0
    assert latest_manifest["changed_count"] == 0
    assert latest_manifest["removed_count"] == 0


def test_news_ref_small_change_replaces_current_without_snapshot_growth(tmp_path: Path):
    data = tmp_path / "data"
    storage = tmp_path / "storage"
    base = {
        "index_id": "change12",
        "source": "Reuters",
        "link": "https://example.com/change",
        "first_seen": "2026-03-13T15:00:00Z",
        "last_seen": "2026-03-13T15:00:00Z",
        "topics": '["Economy"]',
        "meta": '{"title": "Changing story"}',
        "digest_file": "stable.csv",
        "article_id": "stable-2",
    }
    _write_csv(data / "master_ref.csv", [base])
    _run_export(data, storage, "20260313T15")

    changed = dict(base)
    changed["source"] = "AP"
    _write_csv(data / "master_ref.csv", [changed])
    _run_export(data, storage, "20260313T16")

    bus_dir = storage / "buses" / "news_ref" / "v1"
    payloads = sorted(bus_dir.glob("news_ref_*.jsonl"))
    assert payloads == [bus_dir / "news_ref_current.jsonl"]
    current_rows = [json.loads(line) for line in payloads[0].read_text(encoding="utf-8").splitlines() if line]
    assert current_rows[0]["source"] == "AP"

    manifests = sorted(bus_dir.glob("manifest_*.json"))
    assert manifests
    latest_manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert latest_manifest["status"] == "changed"
    assert latest_manifest["previous_content_sha256"] != latest_manifest["content_sha256"]
    assert latest_manifest["added_count"] == 0
    assert latest_manifest["changed_count"] == 1
    assert latest_manifest["removed_count"] == 0


def test_atomic_write_failure_preserves_authoritative_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target = tmp_path / "news_ref_current.jsonl"
    target.write_bytes(b"old-authoritative-bytes\n")

    def fail_replace(_src, _dst):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(bounded_storage.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        bounded_storage.atomic_write_bytes(target, b"new-partial-bytes\n")

    assert target.read_bytes() == b"old-authoritative-bytes\n"
    assert list(tmp_path.glob(".news_ref_current.jsonl.*.tmp")) == []
