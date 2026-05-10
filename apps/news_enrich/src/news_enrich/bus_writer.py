"""Schema validation and bus writing for scraped_article.v1 records."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .io import append_jsonl
from .records import ScrapedArticle

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "contracts" / "schemas" / "scraped_article.v1.json"
BUS_DIR = REPO_ROOT / "storage" / "buses" / "scraped_article" / "v1"


class ScrapedArticleValidationError(ValueError):
    """Raised when a scraped_article.v1 record fails JSON Schema validation."""


def _load_schema(schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_scraped_article(record: ScrapedArticle | dict[str, Any], *, schema_path: Path = SCHEMA_PATH) -> dict[str, Any]:
    """Validate a record against contracts/schemas/scraped_article.v1.json."""
    data = record.model_dump(mode="json") if isinstance(record, ScrapedArticle) else record
    validator = Draft202012Validator(_load_schema(schema_path))
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise ScrapedArticleValidationError(messages)
    return data


def default_scraped_article_bus_path(now: datetime | None = None, *, bus_dir: Path = BUS_DIR) -> Path:
    """Return the append-only daily scraped_article.v1 bus path."""
    now = now or datetime.now(timezone.utc)
    return bus_dir / f"scraped_article_{now:%Y-%m-%d}.jsonl"


def write_scraped_article(record: ScrapedArticle, *, path: Path | None = None) -> Path:
    """Validate and append one scraped_article.v1 record to the bus."""
    destination = path or default_scraped_article_bus_path()
    validated = validate_scraped_article(record)
    append_jsonl(destination, validated)
    return destination
