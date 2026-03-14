#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _to_rfc3339(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return "1970-01-01T00:00:00Z"
    if s.endswith("Z"):
        return s
    if " " in s and "T" not in s:
        s = s.replace(" ", "T")
    if "+00:00" in s:
        return s.replace("+00:00", "Z")
    if len(s) == 19 and "T" in s:
        return s + "Z"
    return s


def _safe_exists_jsonl(path_str: str) -> bool:
    if not path_str:
        return False
    p = Path(path_str)
    return p.exists() and p.is_file() and p.stat().st_size > 0


def _latest_payload(storage_dir: Path) -> dict[str, Any]:
    latest = storage_dir / "indexes" / "pr3a_exports_latest.json"
    if not latest.exists():
        return {}
    try:
        return _read_json(latest)
    except Exception:
        return {}


def _resolve_from_indexes(storage_dir: Path, export_name: str) -> tuple[str | None, str | None]:
    idx_dir = storage_dir / "indexes"
    run_files = sorted(idx_dir.glob("pr3a_exports_*.json"), reverse=True)
    for idx in run_files:
        try:
            payload = _read_json(idx)
        except Exception:
            continue
        digest_at = str(payload.get("digest_at") or "").strip() or None
        for result in payload.get("results") or []:
            if str(result.get("name") or "") != export_name:
                continue
            status = str(result.get("status") or "")
            if status not in {"exported", "skipped_duplicate"}:
                continue
            out = str(result.get("output_path") or "").strip()
            if _safe_exists_jsonl(out):
                return digest_at, out
    return None, None


def _resolve_from_manifests(storage_dir: Path, export_name: str) -> tuple[str | None, str | None]:
    if export_name == "news_ref.v1":
        manifest_glob = "buses/news_ref/v1/manifest_*.json"
    elif export_name == "news_digest_group.v1":
        manifest_glob = "buses/news_digest_group/v1/manifest_*.json"
    else:
        return None, None

    for manifest in sorted(storage_dir.glob(manifest_glob), reverse=True):
        try:
            payload = _read_json(manifest)
        except Exception:
            continue
        status = str(payload.get("status") or "")
        if status not in {"exported", "skipped_duplicate"}:
            continue
        out = str(payload.get("output_file") or payload.get("duplicate_of") or "").strip()
        if _safe_exists_jsonl(out):
            return str(payload.get("digest_at") or "").strip() or None, out
    return None, None


def _resolve_output(storage_dir: Path, export_name: str) -> tuple[str | None, str | None]:
    latest = _latest_payload(storage_dir)
    digest_at_latest = str(latest.get("digest_at") or "").strip() or None
    for result in latest.get("results") or []:
        if str(result.get("name") or "") != export_name:
            continue
        out = str(result.get("output_path") or "").strip()
        if _safe_exists_jsonl(out):
            return digest_at_latest, out

    digest_at, out = _resolve_from_indexes(storage_dir, export_name)
    if out:
        return digest_at or digest_at_latest, out

    digest_at, out = _resolve_from_manifests(storage_dir, export_name)
    if out:
        return digest_at or digest_at_latest, out

    return digest_at_latest, None


def _title_from_meta(meta: Any) -> str:
    if not isinstance(meta, dict):
        return ""
    for key in ("title", "headline", "article_title"):
        val = str(meta.get(key) or "").strip()
        if val:
            return val
    return ""


def _build_group_index(group_rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    by_link: dict[str, dict[str, Any]] = {}
    groups: list[dict[str, Any]] = []

    for row in group_rows:
        digest_at = str(row.get("digest_id_hour") or "").strip()
        window_type = str(row.get("window_type") or "").strip() or "unknown"
        topic = str(row.get("topic") or "").strip() or "unknown"
        group_number = int(row.get("group_number") or 0)

        content = row.get("content")
        if not isinstance(content, list):
            content = []

        titles: list[str] = []
        for article in content:
            if not isinstance(article, dict):
                continue
            link = str(article.get("link") or "").strip()
            title = str(article.get("title") or "").strip()
            published_at = _to_rfc3339(article.get("published"))
            source = str(article.get("source") or "").strip()

            if title:
                titles.append(title)
            if link and link not in by_link:
                by_link[link] = {
                    "digest_at": digest_at,
                    "title": title,
                    "published_at": published_at,
                    "topic": topic,
                    "source": source,
                }

        groups.append(
            {
                "digest_at": digest_at,
                "window_type": window_type,
                "topic": topic,
                "group_number": group_number,
                "article_count": len(content),
                "top_titles": titles[:3],
            }
        )

    groups.sort(key=lambda g: (g["digest_at"], g["window_type"], g["topic"], g["group_number"]))
    return by_link, groups


def build_access_indexes(storage_dir: Path) -> tuple[Path, Path, int, int]:
    digest_ref, ref_output = _resolve_output(storage_dir, "news_ref.v1")
    digest_group, group_output = _resolve_output(storage_dir, "news_digest_group.v1")

    ref_rows = list(_iter_jsonl(Path(ref_output))) if ref_output else []
    group_rows = list(_iter_jsonl(Path(group_output))) if group_output else []

    # Prefer semantic article content from digest groups.
    # Use refs only to enrich index_id by link when available.
    index_id_by_link: dict[str, str] = {}
    refs_fallback: list[dict[str, Any]] = []

    for row in ref_rows:
        link = str(row.get("link") or "").strip()
        if not link:
            continue
        index_id = str(row.get("index_id") or "").strip()
        if index_id and link not in index_id_by_link:
            index_id_by_link[link] = index_id
        topics = row.get("topics") if isinstance(row.get("topics"), list) else []
        refs_fallback.append(
            {
                "digest_at": str(digest_ref or digest_group or "unknown"),
                "index_id": index_id,
                "title": str(_title_from_meta(row.get("meta")) or "(untitled)").strip(),
                "source": str(row.get("source") or "unknown").strip(),
                "published_at": _to_rfc3339(row.get("first_seen")),
                "topic": str((topics[0] if topics else "unknown") or "unknown").strip(),
                "link": link,
            }
        )

    groups: list[dict[str, Any]] = []
    refs_from_groups: list[dict[str, Any]] = []
    for row in group_rows:
        digest_at = str(row.get("digest_id_hour") or digest_group or digest_ref or "unknown").strip() or "unknown"
        window_type = str(row.get("window_type") or "").strip() or "unknown"
        topic = str(row.get("topic") or "").strip() or "unknown"
        group_number = int(row.get("group_number") or 0)

        content = row.get("content") if isinstance(row.get("content"), list) else []
        titles: list[str] = []
        for article in content:
            if not isinstance(article, dict):
                continue
            title = str(article.get("title") or "").strip() or "(untitled)"
            source = str(article.get("source") or "").strip() or "unknown"
            link = str(article.get("link") or "").strip()
            published = _to_rfc3339(article.get("published"))
            if title:
                titles.append(title)
            if not link:
                continue
            refs_from_groups.append(
                {
                    "digest_at": digest_at,
                    "index_id": index_id_by_link.get(link, ""),
                    "title": title,
                    "source": source,
                    "published_at": published,
                    "topic": topic,
                    "link": link,
                }
            )

        groups.append(
            {
                "digest_at": digest_at,
                "window_type": window_type,
                "topic": topic,
                "group_number": group_number,
                "article_count": len(content),
                "top_titles": titles[:3],
            }
        )

    refs = refs_from_groups if refs_from_groups else refs_fallback
    refs.sort(key=lambda r: (r.get("published_at") or "", r.get("link") or ""), reverse=True)
    groups.sort(key=lambda g: (g["digest_at"], g["window_type"], g["topic"], g["group_number"]))

    digest_at = digest_group or digest_ref or "unknown"
    built_at = _utc_now_compact()
    idx_dir = storage_dir / "indexes"
    latest_refs = idx_dir / "news_recent_refs_latest.jsonl"
    latest_groups = idx_dir / "news_recent_groups_latest.jsonl"
    _write_jsonl(latest_refs, refs)
    _write_jsonl(latest_groups, groups)

    _write_jsonl(idx_dir / f"news_recent_refs_{digest_at}_{built_at}.jsonl", refs)
    _write_jsonl(idx_dir / f"news_recent_groups_{digest_at}_{built_at}.jsonl", groups)
    return latest_refs, latest_groups, len(refs), len(groups)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build compact, human-readable latest news indexes from exported seams")
    p.add_argument("--storage-dir", default="storage")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    latest_refs, latest_groups, ref_count, group_count = build_access_indexes(Path(args.storage_dir))
    print(f"[news-access] refs={ref_count} groups={group_count}")
    print(f"[news-access] latest_refs={latest_refs}")
    print(f"[news-access] latest_groups={latest_groups}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
