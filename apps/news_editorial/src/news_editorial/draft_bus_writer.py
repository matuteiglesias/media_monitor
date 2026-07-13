"""Schema validation and bus writing for editorial draft contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Literal

from jsonschema import Draft202012Validator

from . import io as bio

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_DIR = REPO_ROOT / "contracts" / "schemas"
STORAGE_DIR = REPO_ROOT / "storage"
ARTICLE_BUS_DIR = STORAGE_DIR / "buses" / "news_article_draft" / "v1"
YT_SCRIPT_BUS_DIR = STORAGE_DIR / "buses" / "news_yt_script_draft" / "v1"

DraftKind = Literal["article", "yt_script"]


class DraftBusValidationError(ValueError):
    """Raised when an editorial draft bus record fails JSON Schema validation."""


def _safe_id(value: str, fallback: str) -> str:
    raw = value.strip() or fallback
    safe = re.sub(r"[^A-Za-z0-9_.:-]+", "_", raw).strip("_")
    return safe or fallback


def _load_schema(schema_name: str, *, schema_dir: Path = SCHEMA_DIR) -> dict[str, Any]:
    with (schema_dir / schema_name).open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate(record: dict[str, Any], schema_name: str, *, schema_dir: Path = SCHEMA_DIR) -> dict[str, Any]:
    validator = Draft202012Validator(_load_schema(schema_name, schema_dir=schema_dir))
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise DraftBusValidationError(messages)
    return record


def validate_article_draft(record: dict[str, Any], *, schema_dir: Path = SCHEMA_DIR) -> dict[str, Any]:
    """Validate a record against contracts/schemas/news_article_draft.v1.json."""
    return _validate(record, "news_article_draft.v1.json", schema_dir=schema_dir)


def validate_yt_script_draft(record: dict[str, Any], *, schema_dir: Path = SCHEMA_DIR) -> dict[str, Any]:
    """Validate a record against contracts/schemas/news_yt_script_draft.v1.json."""
    return _validate(record, "news_yt_script_draft.v1.json", schema_dir=schema_dir)


def article_bus_path(record: dict[str, Any], *, bus_dir: Path = ARTICLE_BUS_DIR) -> Path:
    draft_id = _safe_id(str(record.get("draft_id") or ""), "article_draft")
    return bus_dir / f"{draft_id}.jsonl"


def yt_script_bus_path(record: dict[str, Any], *, bus_dir: Path = YT_SCRIPT_BUS_DIR) -> Path:
    script_id = _safe_id(str(record.get("script_id") or ""), "yt_script_draft")
    return bus_dir / f"{script_id}.jsonl"


def _citation_url(citation: dict[str, Any]) -> str:
    return str(citation.get("url") or "").strip()


def _source_ref_id(citation: dict[str, Any], ordinal: int, fallback: str) -> str:
    return _safe_id(
        str(citation.get("source_ref_id") or citation.get("index_id") or citation.get("source") or ""),
        f"{fallback}_ref_{ordinal}",
    )


def article_draft_from_stage05(draft: dict[str, Any]) -> dict[str, Any]:
    """Promote the stage05 draft mirror shape into news_article_draft.v1."""
    meta = draft.get("meta") if isinstance(draft.get("meta"), dict) else {}
    brief_id = _safe_id(str(meta.get("brief_id") or draft.get("cluster_id") or draft.get("index_id") or ""), "legacy_brief")
    index_id = _safe_id(str(draft.get("index_id") or brief_id), brief_id)
    title = str(draft.get("headline") or draft.get("topic") or index_id).strip()
    dek = str(draft.get("dek") or draft.get("topic") or title).strip()
    lede = dek or title
    section_heading = str(draft.get("topic") or "What matters").strip() or "What matters"
    digest_at = str(draft.get("digest_id_hour") or "").strip()
    story_group_id = str(draft.get("cluster_id") or brief_id).strip()
    slug_candidate = _safe_id(str(draft.get("slug") or title).lower(), index_id.lower())
    body_markdown = f"# {title}\n\n{lede}"

    citations = []
    source_links = []
    source_ids = []
    for ordinal, citation in enumerate([c for c in (draft.get("citations") or []) if isinstance(c, dict)], start=1):
        url = _citation_url(citation)
        if not url:
            continue
        source_ref_id = _source_ref_id(citation, ordinal, index_id)
        source_links.append(url)
        source_ids.append(source_ref_id)
        citations.append(
            {
                "citation_id": f"c{ordinal}",
                "claim_text": title,
                "source_ref_id": source_ref_id,
                "url": url,
            }
        )

    return {
        "schema_name": "news_article_draft.v1",
        "schema_status": "experimental_structured",
        "draft_id": _safe_id(f"article_{brief_id}_{index_id}", f"article_{index_id}"),
        "digest_at": digest_at,
        "story_group_id": story_group_id,
        "brief_id": brief_id,
        "title": title,
        "slug_candidate": slug_candidate,
        "summary": dek,
        "dek": dek,
        "lede": lede,
        "sections": [
            {
                "section_id": "sec_1",
                "heading": section_heading,
                "summary": lede,
            }
        ],
        "body_md": body_markdown,
        "body_markdown": body_markdown,
        "source_links": source_links,
        "source_ids": source_ids,
        "topic": section_heading,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "citations": citations,
        "fact_check_flags": [],
        "revision_notes": [],
    }


def yt_script_draft_from_stage05(draft: dict[str, Any]) -> dict[str, Any]:
    """Promote the stage05 draft mirror shape into news_yt_script_draft.v1."""
    meta = draft.get("meta") if isinstance(draft.get("meta"), dict) else {}
    brief_id = _safe_id(str(meta.get("brief_id") or draft.get("cluster_id") or draft.get("index_id") or ""), "legacy_brief")
    index_id = _safe_id(str(draft.get("index_id") or brief_id), brief_id)
    title = str(draft.get("headline") or draft.get("topic") or index_id).strip()
    hook = str(draft.get("dek") or title).strip()
    topic = str(draft.get("topic") or "What matters").strip() or "What matters"

    citations = []
    for ordinal, citation in enumerate([c for c in (draft.get("citations") or []) if isinstance(c, dict)], start=1):
        url = _citation_url(citation)
        if not url:
            continue
        citations.append(
            {
                "source_ref_id": _source_ref_id(citation, ordinal, index_id),
                "url": url,
                "usage_note": title,
            }
        )

    return {
        "schema_name": "news_yt_script_draft.v1",
        "schema_status": "experimental_structured",
        "script_id": _safe_id(f"yt_{brief_id}_{index_id}", f"yt_{index_id}"),
        "brief_id": brief_id,
        "title": title,
        "thumbnail_hook": hook,
        "cold_open": hook,
        "segment_outline": [
            {
                "segment_id": "seg_1",
                "heading": topic,
                "beat": hook,
                "estimated_seconds": 45,
            }
        ],
        "full_script": f"[COLD OPEN]\n{hook}\n\n[SEGMENT 1]\n{title}",
        "voice_notes": [],
        "visual_notes": [],
        "citations": citations,
    }


def write_article_draft(record: dict[str, Any], *, path: Path | None = None, bus_dir: Path = ARTICLE_BUS_DIR) -> Path:
    """Validate and write one news_article_draft.v1 row to its bus."""
    validated = validate_article_draft(record)
    destination = path or article_bus_path(validated, bus_dir=bus_dir)
    bio.atomic_write_jsonl(destination, [json.dumps(validated, ensure_ascii=False)])
    return destination


def write_yt_script_draft(record: dict[str, Any], *, path: Path | None = None, bus_dir: Path = YT_SCRIPT_BUS_DIR) -> Path:
    """Validate and write one news_yt_script_draft.v1 row to its bus."""
    validated = validate_yt_script_draft(record)
    destination = path or yt_script_bus_path(validated, bus_dir=bus_dir)
    bio.atomic_write_jsonl(destination, [json.dumps(validated, ensure_ascii=False)])
    return destination
