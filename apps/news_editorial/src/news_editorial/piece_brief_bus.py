"""Validation and atomic writing for news_piece_brief.v1."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from . import io as bio

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "contracts" / "schemas" / "news_piece_brief.v1.json"
DEFAULT_BUS_DIR = REPO_ROOT / "storage" / "buses" / "news_piece_brief" / "v1"


class PieceBriefValidationError(ValueError):
    pass


def validate_piece_brief(
    record: dict[str, Any], *, schema_path: Path = SCHEMA_PATH
) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(record),
        key=lambda error: list(error.path),
    )
    if errors:
        raise PieceBriefValidationError("; ".join(error.message for error in errors))
    return record


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]+", "_", value).strip("_")
    return cleaned or "piece_brief"


def write_piece_brief(
    record: dict[str, Any], *, bus_dir: Path = DEFAULT_BUS_DIR
) -> Path:
    validated = validate_piece_brief(record)
    destination = bus_dir / f"{_safe_id(str(validated['brief_id']))}.jsonl"
    bio.atomic_write_jsonl(
        destination,
        [json.dumps(validated, ensure_ascii=False)],
    )
    return destination
