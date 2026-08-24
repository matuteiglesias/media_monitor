from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_editorial_selection.py"
SCHEMA = ROOT / "contracts" / "schemas" / "editorial_selection.v1.json"
FIXTURE = ROOT / "contracts" / "tests" / "fixtures" / "editorial_selection.example.json"
POLICY = ROOT / "config" / "editorial_selection.argentina.json"


def write_refs(path: Path) -> None:
    rows = [
        {
            "digest_at": "20260824T20",
            "index_id": "inflation-1",
            "title": "Inflación: nuevo dato oficial",
            "source": "Fuente A",
            "published_at": "2026-08-24T19:55:00Z",
            "topic": "Inflación y Precios",
            "link": "https://example.com/inflation-new",
        },
        {
            "digest_at": "20260824T20",
            "index_id": "inflation-duplicate",
            "title": "Inflación — nuevo dato oficial",
            "source": "Fuente Z",
            "published_at": "2026-08-24T19:20:00Z",
            "topic": "Inflación y Precios",
            "link": "https://example.com/inflation-old",
        },
        {
            "digest_at": "20260824T20",
            "index_id": "fx-1",
            "title": "Reservas y tipo de cambio en la rueda",
            "source": "Fuente A",
            "published_at": "2026-08-24T19:54:00Z",
            "topic": "Tipo de Cambio y Reservas",
            "link": "https://example.com/fx",
        },
        {
            "digest_at": "20260824T20",
            "index_id": "activity-1",
            "title": "Actividad industrial muestra nuevas señales",
            "source": "Fuente B",
            "published_at": "2026-08-24T19:50:00Z",
            "topic": "Actividad y Empleo",
            "link": "https://example.com/activity",
        },
        {
            "digest_at": "20260824T20",
            "index_id": "debt-1",
            "title": "Financiamiento soberano bajo seguimiento",
            "source": "Fuente C",
            "published_at": "2026-08-24T19:30:00Z",
            "topic": "Deuda y Financiamiento",
            "link": "https://example.com/debt",
        },
        {
            "digest_at": "20260824T20",
            "index_id": "external-1",
            "title": "Comercio exterior y saldo mensual",
            "source": "Fuente D",
            "published_at": "2026-08-24T19:25:00Z",
            "topic": "Sector Externo",
            "link": "https://example.com/external",
        },
        {
            "digest_at": "20260824T20",
            "index_id": "finance-1",
            "title": "Mercados locales cierran la jornada",
            "source": "Fuente E",
            "published_at": "2026-08-24T19:10:00Z",
            "topic": "Finanzas",
            "link": "https://example.com/finance",
        },
        {
            "digest_at": "20260824T20",
            "index_id": "stale-1",
            "title": "Señal vieja fuera de ventana",
            "source": "Fuente F",
            "published_at": "2026-08-24T16:00:00Z",
            "topic": "Finanzas",
            "link": "https://example.com/stale",
        },
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def run_selection(refs: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--refs",
            str(refs),
            "--policy",
            str(POLICY),
            "--digest-at",
            "20260824T20",
            "--as-of",
            "2026-08-24T20:00:00Z",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_contract_fixture_is_valid() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(fixture),
        key=lambda error: list(error.path),
    )
    assert not errors, "; ".join(error.message for error in errors)


def test_selection_is_deterministic_deduplicated_and_reasoned(tmp_path: Path) -> None:
    refs = tmp_path / "refs.jsonl"
    first = tmp_path / "selection-1.json"
    second = tmp_path / "selection-2.json"
    write_refs(refs)

    result = run_selection(refs, first)
    assert result.returncode == 0, result.stderr + result.stdout
    result2 = run_selection(refs, second)
    assert result2.returncode == 0, result2.stderr + result2.stdout
    assert first.read_bytes() == second.read_bytes()

    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["schema_name"] == "editorial_selection.v1"
    assert payload["metrics"] == {
        "candidate_count": 8,
        "eligible_count": 6,
        "deduplicated_count": 1,
        "discarded_stale_count": 1,
        "discarded_missing_identity_count": 0,
        "selected_count": 6,
    }
    assert payload["selected"][0]["index_id"] == "inflation-1"
    assert "high_topic_priority" in payload["selected"][0]["reason_codes"]
    assert "new_source_bonus" in payload["selected"][0]["reason_codes"]
    assert all(item["index_id"] != "inflation-duplicate" for item in payload["selected"])
    assert all(item["index_id"] != "stale-1" for item in payload["selected"])
    assert [item["rank"] for item in payload["selected"]] == list(range(1, 7))


def test_diversity_penalty_is_explicit_and_selection_is_not_publication_authority(tmp_path: Path) -> None:
    refs = tmp_path / "refs.jsonl"
    output = tmp_path / "selection.json"
    write_refs(refs)
    result = run_selection(refs, output)
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))

    repeated_source = next(item for item in payload["selected"] if item["index_id"] == "fx-1")
    assert repeated_source["score_components"]["repeat_source_penalty"] < 0
    assert "repeat_source_penalty" in repeated_source["reason_codes"]

    source = SCRIPT.read_text(encoding="utf-8").lower()
    for forbidden_dependency in ("promptflow", "editorial_latest", "news_article_draft"):
        assert forbidden_dependency not in source
    assert "published_article.v1.json" not in source
    assert "it never implies authorship" in source


def test_minimum_items_fails_closed(tmp_path: Path) -> None:
    refs = tmp_path / "refs.jsonl"
    output = tmp_path / "selection.json"
    row = {
        "digest_at": "20260824T20",
        "index_id": "only-one",
        "title": "Única señal",
        "source": "Fuente A",
        "published_at": "2026-08-24T19:59:00Z",
        "topic": "Inflación y Precios",
        "link": "https://example.com/one",
    }
    refs.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    result = run_selection(refs, output)
    assert result.returncode != 0
    assert "minimum_items=5" in result.stdout
    assert not output.exists()
