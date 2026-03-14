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


def _resolve_export_outputs(storage_dir: Path) -> tuple[str, str, str]:
    latest = storage_dir / "indexes" / "pr3a_exports_latest.json"
    if not latest.exists():
        raise FileNotFoundError(f"missing export index: {latest}")

    payload = _read_json(latest)
    digest_at = str(payload.get("digest_at") or "").strip()
    results = payload.get("results") or []
    if not digest_at:
        raise ValueError("pr3a_exports_latest.json missing digest_at")

    outputs: dict[str, str] = {}
    for result in results:
        name = str(result.get("name") or "").strip()
        status = str(result.get("status") or "").strip()
        if status not in {"exported", "skipped_duplicate"}:
            continue
        out = str(result.get("output_path") or "").strip()
        if out:
            outputs[name] = out

    ref_out = outputs.get("news_ref.v1")
    group_out = outputs.get("news_digest_group.v1")
    if not ref_out or not group_out:
        raise ValueError("missing output_path for news_ref.v1 or news_digest_group.v1 in pr3a_exports_latest.json")
    return digest_at, ref_out, group_out


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
    digest_at, ref_output, group_output = _resolve_export_outputs(storage_dir)
    ref_rows = list(_iter_jsonl(Path(ref_output)))
    group_rows = list(_iter_jsonl(Path(group_output)))

    by_link, groups = _build_group_index(group_rows)

    refs: list[dict[str, Any]] = []
    for row in ref_rows:
        link = str(row.get("link") or "").strip()
        if not link:
            continue
        group_match = by_link.get(link, {})
        topics = row.get("topics") if isinstance(row.get("topics"), list) else []
        topic = str(group_match.get("topic") or (topics[0] if topics else "")).strip()
        title = str(group_match.get("title") or _title_from_meta(row.get("meta")) or "(untitled)").strip()

        refs.append(
            {
                "digest_at": str(group_match.get("digest_at") or digest_at),
                "index_id": str(row.get("index_id") or "").strip(),
                "title": title,
                "source": str(row.get("source") or group_match.get("source") or "unknown").strip(),
                "published_at": _to_rfc3339(group_match.get("published_at") or row.get("first_seen")),
                "topic": topic or "unknown",
                "link": link,
            }
        )

    refs = [r for r in refs if r["index_id"]]
    refs.sort(key=lambda r: (r["published_at"], r["index_id"]), reverse=True)

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
