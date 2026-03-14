import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


def _load_schema() -> dict:
    schema_path = Path(__file__).resolve().parents[1] / "flow" / "02_generate_agenda_and_ideas.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))["parameters"]


def test_seed_ideas_payload_matches_pf_schema_contract() -> None:
    schema = _load_schema()
    payload = {
        "seed_ideas": [
            {
                "idea_id": "EC01",
                "topic": "Economía",
                "idea_title": "Inflación y consumo: señales de enfriamiento",
                "source_ids": [101, 102],
                "draft_editorial_angle": "El consumo muestra señales mixtas pese a una inflación más estable.",
                "key_facts": [
                    "La inflación interanual se desaceleró al 3.2%.",
                    "Las ventas minoristas cayeron 1.1% mensual.",
                ],
                "potential_controversies": [
                    "Debate sobre efecto real de tasas altas en pymes",
                ],
                "relevant_quotes": [
                    "El mercado aún no percibe mejora en ingresos reales.",
                ],
            }
        ]
    }

    validate(instance=payload, schema=schema)


def test_seed_ideas_payload_rejects_legacy_key_data_points() -> None:
    schema = _load_schema()
    payload = {
        "seed_ideas": [
            {
                "idea_id": "EC01",
                "topic": "Economía",
                "idea_title": "Inflación y consumo: señales de enfriamiento",
                "source_ids": [101],
                "draft_editorial_angle": "Ángulo editorial de prueba.",
                "key_data_points": ["dato legacy"],
                "potential_controversies": ["controversia"],
                "relevant_quotes": ["cita"],
            }
        ]
    }

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=schema)
