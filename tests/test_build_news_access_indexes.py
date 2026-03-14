from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_news_access_indexes.py"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_build_news_access_indexes_creates_latest_readable_files(tmp_path: Path):
    storage = tmp_path / "storage"
    digest_at = "20260313T20"
    ref_path = storage / "buses" / "news_ref" / "v1" / "news_ref_20260313T200000Z.jsonl"
    group_path = storage / "buses" / "news_digest_group" / "v1" / "news_digest_group_20260313T20_20260313T200000Z.jsonl"

    _write_jsonl(
        ref_path,
        [
            {
                "schema_name": "news_ref.v1",
                "schema_status": "stable",
                "index_id": "15ef8990d6",
                "source": "EL PAIS",
                "link": "https://elpais.com/economia/example",
                "first_seen": "2026-03-13T15:00:00Z",
                "last_seen": "2026-03-13T15:00:00Z",
                "topics": ["Economia"],
                "meta": {},
                "digest_file": "digest_A_20260313T20.csv",
                "article_id": "42",
                "join_key": "digest_A_20260313T20.csv::42",
            }
        ],
    )

    _write_jsonl(
        group_path,
        [
            {
                "schema_name": "news_digest_group.v1",
                "schema_status": "experimental_structured",
                "digest_group_id": "20260313T20:4h_window:Economia:1",
                "digest_id_hour": digest_at,
                "window_type": "4h_window",
                "topic": "Economia",
                "group_number": 1,
                "content": [
                    {
                        "article_id": "42",
                        "title": "Inflación baja",
                        "source": "EL PAIS",
                        "link": "https://elpais.com/economia/example",
                        "published": "2026-03-13T15:00:00Z",
                    }
                ],
            }
        ],
    )

    _write_json(
        storage / "indexes" / "pr3a_exports_latest.json",
        {
            "digest_at": digest_at,
            "export_at": "20260313T200000Z",
            "status": "exported",
            "results": [
                {
                    "name": "news_ref.v1",
                    "status": "exported",
                    "count": 1,
                    "source": "data/master_ref.csv",
                    "output_path": str(ref_path),
                    "manifest_path": str(storage / "buses" / "news_ref" / "v1" / "manifest_20260313T200000Z.json"),
                    "reason": None,
                },
                {
                    "name": "news_digest_group.v1",
                    "status": "exported",
                    "count": 1,
                    "source": "data/digest_jsonls/20260313T20.jsonl",
                    "output_path": str(group_path),
                    "manifest_path": str(storage / "buses" / "news_digest_group" / "v1" / "manifest_20260313T200000Z.json"),
                    "reason": None,
                },
            ],
        },
    )

    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--storage-dir", str(storage)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "refs=1 groups=1" in out.stdout

    refs_latest = storage / "indexes" / "news_recent_refs_latest.jsonl"
    groups_latest = storage / "indexes" / "news_recent_groups_latest.jsonl"
    assert refs_latest.exists()
    assert groups_latest.exists()

    ref_rows = [json.loads(line) for line in refs_latest.read_text(encoding="utf-8").splitlines() if line.strip()]
    group_rows = [json.loads(line) for line in groups_latest.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert ref_rows == [
        {
            "digest_at": "20260313T20",
            "index_id": "15ef8990d6",
            "title": "Inflación baja",
            "source": "EL PAIS",
            "published_at": "2026-03-13T15:00:00Z",
            "topic": "Economia",
            "link": "https://elpais.com/economia/example",
        }
    ]
    assert group_rows == [
        {
            "digest_at": "20260313T20",
            "window_type": "4h_window",
            "topic": "Economia",
            "group_number": 1,
            "article_count": 1,
            "top_titles": ["Inflación baja"],
        }
    ]


def test_build_news_access_indexes_falls_back_when_latest_group_is_noop(tmp_path: Path):
    storage = tmp_path / "storage"

    ref_path_latest = storage / "buses" / "news_ref" / "v1" / "news_ref_20260313T210000Z.jsonl"
    _write_jsonl(
        ref_path_latest,
        [
            {
                "schema_name": "news_ref.v1",
                "schema_status": "stable",
                "index_id": "abc12345",
                "source": "Reuters",
                "link": "https://example.com/n1",
                "first_seen": "2026-03-13T21:00:00Z",
                "last_seen": "2026-03-13T21:00:00Z",
                "topics": ["Economy"],
                "meta": {},
                "digest_file": "digest_A_20260313T21.csv",
                "article_id": "1",
                "join_key": "digest_A_20260313T21.csv::1",
            }
        ],
    )

    old_group_path = storage / "buses" / "news_digest_group" / "v1" / "news_digest_group_20260313T20_20260313T200000Z.jsonl"
    _write_jsonl(
        old_group_path,
        [
            {
                "schema_name": "news_digest_group.v1",
                "schema_status": "experimental_structured",
                "digest_group_id": "20260313T20:4h_window:Economy:1",
                "digest_id_hour": "20260313T20",
                "window_type": "4h_window",
                "topic": "Economy",
                "group_number": 1,
                "content": [
                    {
                        "article_id": "1",
                        "title": "Markets steady",
                        "source": "Reuters",
                        "link": "https://example.com/n1",
                        "published": "2026-03-13T21:00:00Z",
                    }
                ],
            }
        ],
    )

    _write_json(
        storage / "indexes" / "pr3a_exports_20260313T20_20260313T200000Z.json",
        {
            "digest_at": "20260313T20",
            "export_at": "20260313T200000Z",
            "status": "exported",
            "results": [
                {
                    "name": "news_digest_group.v1",
                    "status": "exported",
                    "count": 1,
                    "source": "data/digest_jsonls/20260313T20.jsonl",
                    "output_path": str(old_group_path),
                    "manifest_path": "",
                    "reason": None,
                }
            ],
        },
    )

    _write_json(
        storage / "indexes" / "pr3a_exports_latest.json",
        {
            "digest_at": "20260313T21",
            "export_at": "20260313T210000Z",
            "status": "exported",
            "results": [
                {
                    "name": "news_ref.v1",
                    "status": "exported",
                    "count": 1,
                    "source": "data/master_ref.csv",
                    "output_path": str(ref_path_latest),
                    "manifest_path": "",
                    "reason": None,
                },
                {
                    "name": "news_digest_group.v1",
                    "status": "noop",
                    "count": 0,
                    "source": None,
                    "output_path": None,
                    "manifest_path": None,
                    "reason": "no digest rows",
                },
            ],
        },
    )

    subprocess.run(
        [sys.executable, str(SCRIPT), "--storage-dir", str(storage)],
        capture_output=True,
        text=True,
        check=True,
    )

    refs_latest = storage / "indexes" / "news_recent_refs_latest.jsonl"
    rows = [json.loads(line) for line in refs_latest.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows[0]["title"] == "Markets steady"
    assert rows[0]["topic"] == "Economy"


def test_build_news_access_indexes_succeeds_without_digest_groups(tmp_path: Path):
    storage = tmp_path / "storage"

    ref_path = storage / "buses" / "news_ref" / "v1" / "news_ref_20260313T220000Z.jsonl"
    _write_jsonl(
        ref_path,
        [
            {
                "schema_name": "news_ref.v1",
                "schema_status": "stable",
                "index_id": "xyz98765",
                "source": "AP",
                "link": "https://example.com/n2",
                "first_seen": "2026-03-13T22:00:00Z",
                "last_seen": "2026-03-13T22:00:00Z",
                "topics": ["Politics"],
                "meta": {"title": "Election update"},
                "digest_file": "unknown.csv",
                "article_id": "xyz98765",
                "join_key": "unknown.csv::xyz98765",
            }
        ],
    )

    _write_json(
        storage / "indexes" / "pr3a_exports_latest.json",
        {
            "digest_at": "20260313T22",
            "export_at": "20260313T220000Z",
            "status": "exported",
            "results": [
                {
                    "name": "news_ref.v1",
                    "status": "exported",
                    "count": 1,
                    "source": "data/master_ref.csv",
                    "output_path": str(ref_path),
                    "manifest_path": "",
                    "reason": None,
                },
                {
                    "name": "news_digest_group.v1",
                    "status": "noop",
                    "count": 0,
                    "source": None,
                    "output_path": None,
                    "manifest_path": None,
                    "reason": "no digest rows",
                },
            ],
        },
    )

    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--storage-dir", str(storage)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "refs=1 groups=0" in out.stdout

    refs_latest = storage / "indexes" / "news_recent_refs_latest.jsonl"
    groups_latest = storage / "indexes" / "news_recent_groups_latest.jsonl"
    ref_rows = [json.loads(line) for line in refs_latest.read_text(encoding="utf-8").splitlines() if line.strip()]
    group_rows = [json.loads(line) for line in groups_latest.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert ref_rows[0]["title"] == "Election update"
    assert ref_rows[0]["topic"] == "Politics"
    assert group_rows == []
