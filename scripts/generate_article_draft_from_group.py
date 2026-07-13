#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                row = json.loads(stripped)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}: expected JSON object rows")
                yield row


def _write_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return normalized or "draft"


def _story_group_id(group: dict[str, Any]) -> str:
    digest_at = str(group.get("digest_at") or "").strip()
    window = str(group.get("window_type") or "window").strip()
    topic = _slugify(str(group.get("topic") or "topic"))
    group_number = int(group.get("group_number") or 0)
    return f"{digest_at}::{window}::{topic}::{group_number:02d}"


def _draft_id(story_group_id: str, title: str) -> str:
    digest = hashlib.sha1(f"{story_group_id}|{title}".encode("utf-8")).hexdigest()[:12]
    return f"draft_article_{digest}"


def _select_refs(group: dict[str, Any], refs: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    digest_at = str(group.get("digest_at") or "").strip()
    topic = str(group.get("topic") or "").strip()
    top_titles = {str(title).strip() for title in (group.get("top_titles") or []) if str(title).strip()}

    candidates = [
        ref
        for ref in refs
        if str(ref.get("digest_at") or "").strip() == digest_at
        and (not topic or str(ref.get("topic") or "").strip() == topic)
    ]
    exact_title_matches = [ref for ref in candidates if str(ref.get("title") or "").strip() in top_titles]
    selected = exact_title_matches or candidates
    return selected[:limit]


def _source_id(ref: dict[str, Any], ordinal: int) -> str:
    return str(ref.get("index_id") or "").strip() or f"source_{ordinal}"


def _source_url(ref: dict[str, Any]) -> str:
    return str(ref.get("link") or "").strip()


def build_draft(group: dict[str, Any], refs: list[dict[str, Any]], created_at: str) -> dict[str, Any]:
    source_refs = _select_refs(group, refs, limit=5)
    if not source_refs:
        raise ValueError("no source refs match the selected group digest/topic")

    digest_at = str(group.get("digest_at") or "").strip()
    topic = str(group.get("topic") or "All Topics").strip()
    titles = [str(title).strip() for title in (group.get("top_titles") or []) if str(title).strip()]
    primary_title = titles[0] if titles else str(source_refs[0].get("title") or "Draft article").strip()
    title = f"Qué se sabe de {primary_title}"
    slug_candidate = _slugify(title)
    story_group_id = _story_group_id(group)
    summary = (
        f"Este borrador reúne {len(source_refs)} fuentes recientes sobre {topic} "
        f"para convertir un grupo de noticias en una pieza original revisable."
    )
    source_ids = [_source_id(ref, idx) for idx, ref in enumerate(source_refs, start=1)]
    source_links = [_source_url(ref) for ref in source_refs if _source_url(ref)]
    if not source_links:
        raise ValueError("selected refs do not include source links")

    bullet_lines = "\n".join(
        f"- {ref.get('title')} ({ref.get('source') or 'fuente'})"
        for ref in source_refs
    )
    body_md = (
        f"# {title}\n\n"
        f"{summary}\n\n"
        "## Por qué importa\n\n"
        "El grupo concentra señales recientes que un editor puede transformar en una cobertura propia, "
        "manteniendo atribución explícita a las fuentes utilizadas.\n\n"
        "## Fuentes revisadas\n\n"
        f"{bullet_lines}\n\n"
        "## Nota editorial\n\n"
        "Borrador inicial generado para revisión humana. Verificar datos, contexto y atribuciones antes de publicar."
    )

    citations = [
        {
            "citation_id": f"c{idx}",
            "claim_text": str(ref.get("title") or title).strip(),
            "source_ref_id": _source_id(ref, idx),
            "url": _source_url(ref),
        }
        for idx, ref in enumerate(source_refs, start=1)
        if _source_url(ref)
    ]

    draft_id = _draft_id(story_group_id, title)
    return {
        "schema_name": "news_article_draft.v1",
        "schema_status": "experimental_structured",
        "draft_id": draft_id,
        "digest_at": digest_at,
        "story_group_id": story_group_id,
        "brief_id": f"auto_brief_{story_group_id}",
        "title": title,
        "slug_candidate": slug_candidate,
        "summary": summary,
        "dek": summary,
        "lede": summary,
        "sections": [
            {
                "section_id": "sec_1",
                "heading": "Por qué importa",
                "summary": "El grupo puede convertirse en una cobertura propia con atribución explícita.",
            },
            {
                "section_id": "sec_2",
                "heading": "Fuentes revisadas",
                "summary": f"Se usaron {len(source_refs)} referencias recientes como punto de partida.",
            },
        ],
        "body_md": body_md,
        "body_markdown": body_md,
        "source_links": source_links,
        "source_ids": source_ids,
        "topic": topic,
        "status": "draft",
        "created_at": created_at,
        "citations": citations,
        "fact_check_flags": [
            {
                "flag": "Revisión humana requerida",
                "severity": "medium",
                "note": "Confirmar hechos, contexto y atribución antes de publicar.",
            }
        ],
        "revision_notes": [
            "Agregar reportería o contexto propio antes de promoción a published_article.v1.",
            "Verificar si hay actualizaciones posteriores al digest usado.",
        ],
    }


def _load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _validate(schema_path: Path, draft: dict[str, Any]) -> None:
    validator = Draft202012Validator(_load_schema(schema_path))
    errors = sorted(validator.iter_errors(draft), key=lambda error: list(error.path))
    if errors:
        messages = "; ".join(error.message for error in errors)
        raise ValueError(f"draft failed news_article_draft.v1 validation: {messages}")


def generate(
    digest_at: str,
    group_index: int,
    public_dir: Path,
    storage_dir: Path,
    schema_path: Path,
    created_at: str,
) -> Path:
    groups = [
        row
        for row in _iter_jsonl(public_dir / "news_recent_groups_latest.jsonl")
        if str(row.get("digest_at") or "").strip() == digest_at
    ]
    if not groups:
        raise ValueError(f"no public groups found for digest_at={digest_at}")
    if group_index < 0 or group_index >= len(groups):
        raise ValueError(f"group_index={group_index} outside available range 0..{len(groups) - 1}")

    refs = list(_iter_jsonl(public_dir / "news_recent_refs_latest.jsonl"))
    draft = build_draft(groups[group_index], refs, created_at)
    _validate(schema_path, draft)
    out_path = storage_dir / "buses" / "news_article_draft" / "v1" / f"{draft['draft_id']}.jsonl"
    _write_jsonl(out_path, draft)
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate one minimal news_article_draft.v1 from a current news group")
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--group-index", type=int, default=0, help="Zero-based group index within the digest")
    parser.add_argument("--public-dir", default="apps/news_site/public/data")
    parser.add_argument("--storage-dir", default="storage")
    parser.add_argument("--schema-path", default="contracts/schemas/news_article_draft.v1.json")
    parser.add_argument("--created-at", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    created_at = args.created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        out_path = generate(
            args.digest_at,
            args.group_index,
            Path(args.public_dir),
            Path(args.storage_dir),
            Path(args.schema_path),
            created_at,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[article-draft] ERROR {exc}")
        return 1

    print(f"[article-draft] wrote={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
