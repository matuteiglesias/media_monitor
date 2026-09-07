import copy
import json
from pathlib import Path

from scripts.import_external_signals import import_signals


REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "contracts" / "tests" / "fixtures" / "external_monitored_signal.example.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _run(tmp_path: Path, rows: list[dict]):
    source = tmp_path / "external.jsonl"
    output = tmp_path / "normalized.jsonl"
    quarantine = tmp_path / "quarantine.jsonl"
    manifest = tmp_path / "manifest.json"
    _write_jsonl(source, rows)
    result = import_signals(
        source,
        digest_at="20260115T12",
        output_path=output,
        quarantine_path=quarantine,
        manifest_path=manifest,
    )
    normalized = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line]
    quarantined = [json.loads(line) for line in quarantine.read_text(encoding="utf-8").splitlines() if line]
    return result, normalized, quarantined


def test_external_signal_import_normalizes_provider_rows(tmp_path: Path) -> None:
    first = _fixture()
    second = copy.deepcopy(first)
    second["external_id"] = "item-002"
    second["provenance"]["record_id"] = "row-002"
    second["title"] = "Second representative external signal"
    second["topic"] = "infrastructure"
    second["published_at"] = "2026-01-15T12:25:00Z"
    second["link"] = "https://example.com/provider/item-002"

    manifest, normalized, quarantine = _run(tmp_path, [first, second])

    assert manifest["status"] == "clean"
    assert manifest["accepted_rows"] == 2
    assert manifest["quarantined_rows"] == 0
    assert quarantine == []
    assert len({row["index_id"] for row in normalized}) == 2
    assert all(len(row["index_id"]) == 10 for row in normalized)
    assert all(row["digest_at"] == "20260115T12" for row in normalized)
    assert all(row["external_provenance"]["provider_id"] == "example-provider" for row in normalized)


def test_identical_external_observations_dedupe_without_losing_count(tmp_path: Path) -> None:
    row = _fixture()
    manifest, normalized, quarantine = _run(tmp_path, [row, copy.deepcopy(row)])

    assert manifest["accepted_rows"] == 1
    assert manifest["duplicate_observations"] == 1
    assert manifest["quarantined_rows"] == 0
    assert quarantine == []
    assert normalized[0]["external_provenance"]["duplicate_observations"] == 1


def test_conflicting_external_identity_is_fully_quarantined(tmp_path: Path) -> None:
    first = _fixture()
    conflicting = copy.deepcopy(first)
    conflicting["title"] = "Conflicting title for same provider identity"

    manifest, normalized, quarantine = _run(tmp_path, [first, conflicting])

    assert manifest["status"] == "quarantined"
    assert manifest["accepted_rows"] == 0
    assert manifest["conflict_identities"] == 1
    assert len(quarantine) == 2
    assert {row["reason"] for row in quarantine} == {"identity_conflict"}
    assert normalized == []


def test_schema_invalid_external_row_is_quarantined(tmp_path: Path) -> None:
    bad = _fixture()
    del bad["link"]

    manifest, normalized, quarantine = _run(tmp_path, [bad])

    assert manifest["accepted_rows"] == 0
    assert manifest["quarantined_rows"] == 1
    assert normalized == []
    assert quarantine[0]["reason"] == "schema_invalid"
    assert any(item["path"] == "$" or "link" in item["message"] for item in quarantine[0]["detail"])


def test_external_identity_is_deterministic_across_imports(tmp_path: Path) -> None:
    row = _fixture()
    first_manifest, first_rows, _ = _run(tmp_path / "a", [row])
    second_manifest, second_rows, _ = _run(tmp_path / "b", [row])

    assert first_rows[0]["index_id"] == second_rows[0]["index_id"]
    assert first_manifest["output_sha256"] == second_manifest["output_sha256"]
