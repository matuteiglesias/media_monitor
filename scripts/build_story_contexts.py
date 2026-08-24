#!/usr/bin/env python3
"""Build deterministic source-side context for monitored signals.

The output is a read model over sensing/digest-group artifacts plus the deterministic
editorial shortlist. It does not read drafts or confer authorship/publication status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from build_news_access_indexes import _iter_jsonl, _resolve_output, _to_rfc3339

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"missing required index: {path}")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{path}: expected non-empty JSONL objects")
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_id(payload: dict[str, Any]) -> str:
    value = {key: item for key, item in payload.items() if key != "context_id"}
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validator() -> Draft202012Validator:
    schema = read_json(ROOT / "contracts/schemas/story_context.v1.json")
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_context(payload: dict[str, Any], contract: Draft202012Validator) -> None:
    errors = sorted(contract.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        raise ValueError("story context schema validation failed: " + "; ".join(error.message for error in errors))
    if payload["context_id"] != canonical_id(payload):
        raise ValueError(f"story context {payload['index_id']} has non-canonical context_id")


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        temp = Path(handle.name)
    temp.replace(path)


def build(storage_dir: Path, digest_at: str, output: Path) -> list[dict[str, Any]]:
    refs_path = storage_dir / "indexes/news_recent_refs_latest.jsonl"
    selection_path = storage_dir / "indexes/editorial_selection_latest.json"
    refs = read_jsonl(refs_path)
    selection = read_json(selection_path)

    ref_digests = {str(row.get("digest_at") or "") for row in refs}
    if ref_digests != {digest_at}:
        raise ValueError(f"refs digest mismatch: {sorted(ref_digests)} requested={digest_at}")
    if selection.get("schema_name") != "editorial_selection.v1" or selection.get("digest_at") != digest_at:
        raise ValueError("editorial selection is missing or belongs to another digest")
    selection_id = str(selection.get("selection_id") or "")
    if len(selection_id) != 64:
        raise ValueError("editorial selection_id is missing")

    _, group_output = _resolve_output(storage_dir, "news_digest_group.v1", digest_at, False)
    groups_path = Path(group_output) if group_output else None
    groups = list(_iter_jsonl(groups_path)) if groups_path else []
    groups = [row for row in groups if str(row.get("digest_id_hour") or "") == digest_at]

    refs_by_link = {str(row.get("link") or "").strip(): row for row in refs if str(row.get("link") or "").strip()}
    curation_by_id = {str(row.get("index_id") or ""): row for row in selection.get("selected") or []}

    groups_by_member_link: dict[str, list[dict[str, Any]]] = {}
    for group in groups:
        for member in group.get("content") or []:
            if not isinstance(member, dict):
                continue
            link = str(member.get("link") or "").strip()
            if link:
                groups_by_member_link.setdefault(link, []).append(group)

    contract = validator()
    contexts: list[dict[str, Any]] = []
    for ref in refs:
        index_id = str(ref.get("index_id") or "").strip()
        link = str(ref.get("link") or "").strip()
        if not index_id or not link:
            continue

        matching_groups = groups_by_member_link.get(link, [])
        coverage_by_link: dict[str, dict[str, Any]] = {
            link: {
                "index_id": index_id,
                "title": str(ref.get("title") or "(untitled)"),
                "source": str(ref.get("source") or "unknown"),
                "published_at": _to_rfc3339(ref.get("published_at")),
                "link": link,
            }
        }
        group_ids: set[str] = set()
        window_types: set[str] = set()

        for group in matching_groups:
            group_id = str(group.get("digest_group_id") or "").strip()
            if group_id:
                group_ids.add(group_id)
            window_type = str(group.get("window_type") or "").strip()
            if window_type:
                window_types.add(window_type)
            for member in group.get("content") or []:
                if not isinstance(member, dict):
                    continue
                member_link = str(member.get("link") or "").strip()
                if not member_link or member_link in coverage_by_link:
                    continue
                public_ref = refs_by_link.get(member_link)
                coverage_by_link[member_link] = {
                    "index_id": str(public_ref.get("index_id") or "").strip() if public_ref else None,
                    "title": str(member.get("title") or "(untitled)"),
                    "source": str(member.get("source") or "unknown"),
                    "published_at": _to_rfc3339(member.get("published")),
                    "link": member_link,
                }

        coverage = list(coverage_by_link.values())
        coverage.sort(key=lambda item: (item["published_at"], item["link"]), reverse=True)
        published_times = [item["published_at"] for item in coverage]
        sources = sorted({str(item["source"]) for item in coverage})
        related = [item for item in coverage if item["link"] != link]

        curated = curation_by_id.get(index_id)
        curation = {
            "selected": curated is not None,
            "rank": int(curated["rank"]) if curated is not None else None,
            "score": int(curated["score"]) if curated is not None else None,
            "reason_codes": list(curated.get("reason_codes") or []) if curated is not None else [],
        }

        payload: dict[str, Any] = {
            "schema_name": "story_context.v1",
            "context_id": "",
            "digest_at": digest_at,
            "index_id": index_id,
            "topic": str(ref.get("topic") or "unknown"),
            "coverage_first_published_at": min(published_times),
            "coverage_latest_published_at": max(published_times),
            "coverage_count": len(coverage),
            "source_count": len(sources),
            "sources": sources,
            "group_ids": sorted(group_ids),
            "window_types": sorted(window_types),
            "related_signals": related,
            "curation": curation,
            "provenance": {
                "refs_path": str(refs_path),
                "refs_sha256": sha256(refs_path),
                "groups_path": str(groups_path) if groups_path else None,
                "groups_sha256": sha256(groups_path) if groups_path else None,
                "editorial_selection_id": selection_id,
            },
        }
        payload["context_id"] = canonical_id(payload)
        validate_context(payload, contract)
        contexts.append(payload)

    contexts.sort(key=lambda row: row["index_id"])
    if not contexts:
        raise ValueError("no story contexts could be built from current monitored refs")
    write_jsonl_atomic(output, contexts)

    archive = output.parent / f"story_contexts_{digest_at}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    write_jsonl_atomic(archive, contexts)
    return contexts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-dir", default="storage")
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--output", default="storage/indexes/story_contexts_latest.jsonl")
    args = parser.parse_args()
    try:
        contexts = build(Path(args.storage_dir), args.digest_at, Path(args.output))
        print(json.dumps({"status": "ok", "digest_at": args.digest_at, "story_context_count": len(contexts)}))
        return 0
    except Exception as exc:
        print(f"[story-contexts] ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
