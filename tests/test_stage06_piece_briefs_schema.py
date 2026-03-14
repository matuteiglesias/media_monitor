import importlib
import json
import sys
import types
from pathlib import Path

from jsonschema import Draft202012Validator


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_stage06_module(monkeypatch):
    if "psycopg" not in sys.modules:
        sys.modules["psycopg"] = types.SimpleNamespace(connect=lambda *args, **kwargs: None)
    mod = importlib.import_module("apps.news_editorial.src.news_editorial.stage06_build_piece_briefs")
    mod = importlib.reload(mod)
    monkeypatch.setattr(mod.db, "start_run", lambda *a, **k: None)
    monkeypatch.setattr(mod.db, "finish_run", lambda *a, **k: None)
    return mod



def test_stage06_emits_schema_valid_piece_brief(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    storage_dir = tmp_path / "storage"
    digest_id = "20260314T17"

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("DIGEST_AT", digest_id)
    monkeypatch.setenv("DRY_RUN", "0")

    digest_map = data_dir / "digest_map" / f"{digest_id}.csv"
    digest_map.parent.mkdir(parents=True, exist_ok=True)
    digest_map.write_text(
        "digest_file,article_id,index_id,Title,Source,Link,Published\n"
        "A_20260314T1700,1,abc12345,Inflacion baja,Fuente A,https://example.com/a,2026-03-14T17:10:00Z\n",
        encoding="utf-8",
    )

    mod = _load_stage06_module(monkeypatch)

    _write_jsonl(
        data_dir / "pf_out" / f"pfout_{digest_id}.jsonl",
        [
            {
                "digest_group_id": "20260314T17::A::Economia::01",
                "seed_ideas": {
                    "seed_ideas": [
                        {
                            "idea_id": "EC01",
                            "topic": "Economia",
                            "idea_title": "Inflación y consumo",
                            "draft_editorial_angle": "Explicar impacto inmediato en consumo.",
                            "source_ids": [1],
                            "key_facts": ["Dato 1"],
                            "potential_controversies": ["Controversia 1"],
                            "relevant_quotes": ["Cita 1"],
                        }
                    ]
                },
            }
        ],
    )

    rc = mod.run()
    assert rc == 0

    out_files = sorted((storage_dir / "buses" / "news_piece_brief" / "v1").glob("*.jsonl"))
    assert len(out_files) == 1

    payload = json.loads(out_files[0].read_text(encoding="utf-8").splitlines()[0])
    schema = json.loads((Path("contracts/schemas/news_piece_brief.v1.json")).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    assert not errors


def test_stage06_quarantines_schema_validation_error(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    storage_dir = tmp_path / "storage"
    digest_id = "20260314T18"

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("DIGEST_AT", digest_id)
    monkeypatch.setenv("DRY_RUN", "0")

    digest_map = data_dir / "digest_map" / f"{digest_id}.csv"
    digest_map.parent.mkdir(parents=True, exist_ok=True)
    # Empty Link produces source_refs.url="" and should fail schema minLength validation.
    digest_map.write_text(
        "digest_file,article_id,index_id,Title,Source,Link,Published\n"
        "A_20260314T1800,1,abc12345,Inflacion baja,Fuente A,,2026-03-14T18:10:00Z\n",
        encoding="utf-8",
    )

    mod = _load_stage06_module(monkeypatch)

    _write_jsonl(
        data_dir / "pf_out" / f"pfout_{digest_id}.jsonl",
        [
            {
                "digest_group_id": "20260314T18::A::Economia::01",
                "seed_ideas": {
                    "seed_ideas": [
                        {
                            "idea_id": "EC02",
                            "topic": "Economia",
                            "idea_title": "Inflación y ahorro",
                            "draft_editorial_angle": "Analizar efectos en ahorro.",
                            "source_ids": [2],
                            "key_facts": ["Dato 1"],
                            "potential_controversies": ["Controversia 1"],
                            "relevant_quotes": ["Cita 1"],
                        }
                    ]
                },
            }
        ],
    )

    rc = mod.run()
    assert rc == 0

    out_files = sorted((storage_dir / "buses" / "news_piece_brief" / "v1").glob("*.jsonl"))
    assert out_files == []

    quarantine = sorted((data_dir / "quarantine").glob("V06_*.jsonl"))
    assert quarantine, "expected quarantine file"
    lines = [json.loads(line) for line in quarantine[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    reasons = {row.get("reason") for row in lines}
    assert "schema_validation_error" in reasons
