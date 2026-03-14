#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:  # pragma: no cover - runtime fallback when dependency is absent
    Draft202012Validator = None



@dataclass
class ExportResult:
    name: str
    status: str
    count: int
    source: str | None
    output_path: str | None
    manifest_path: str | None
    reason: str | None = None


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _compact_to_rfc3339(value: str) -> str:
    try:
        dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except ValueError:
        return _to_rfc3339(value)


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
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_previous_export_output(storage_dir: Path, digest_at: str, export_name: str) -> str | None:
    idx_dir = storage_dir / "indexes"
    latest = idx_dir / "pr3a_exports_latest.json"
    candidates: list[Path] = []
    if latest.exists():
        candidates.append(latest)
    candidates.extend(sorted(idx_dir.glob(f"pr3a_exports_{digest_at}_*.json"), reverse=True))

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            payload = _read_json(candidate)
        except Exception:
            continue
        if str(payload.get("digest_at") or "") != digest_at:
            continue
        for result in payload.get("results") or []:
            if str(result.get("name") or "") != export_name:
                continue
            if str(result.get("status") or "") not in {"exported", "skipped_duplicate"}:
                continue
            output = str(result.get("output_path") or "").strip()
            if output and Path(output).exists():
                return output

    manifest_glob: str
    if export_name == "news_ref.v1":
        manifest_glob = "buses/news_ref/v1/manifest_*.json"
    elif export_name == "news_digest_group.v1":
        manifest_glob = "buses/news_digest_group/v1/manifest_*.json"
    else:
        return None

    for manifest in sorted(storage_dir.glob(manifest_glob), reverse=True):
        try:
            payload = _read_json(manifest)
        except Exception:
            continue
        if str(payload.get("digest_at") or "") != digest_at:
            continue
        if str(payload.get("status") or "exported") not in {"exported", "skipped_duplicate"}:
            continue
        output = str(payload.get("output_file") or payload.get("duplicate_of") or "").strip()
        if output and Path(output).exists():
            return output
    return None


def _rows_match_previous_output(rows: list[dict[str, Any]], previous_output: str | None) -> bool:
    if not previous_output:
        return False
    prev_path = Path(previous_output)
    if not prev_path.exists() or prev_path.stat().st_size == 0:
        return False
    prev_rows = list(_iter_jsonl(prev_path))
    return prev_rows == rows


def _run_status(results: list[ExportResult]) -> str:
    if any(r.status == "exported" for r in results):
        return "exported"
    if any(r.status == "skipped_duplicate" for r in results):
        return "skipped_duplicate"
    return "noop"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _parse_maybe_struct(value: Any, default: Any):
    if isinstance(value, (list, dict)):
        return value
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(s)
            if isinstance(parsed, type(default)):
                return parsed
        except Exception:
            pass
    return default


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


def _validate_rows(rows: list[dict[str, Any]], schema_path: Path) -> None:
    if Draft202012Validator is None:
        print(
            f"[pr3a-export] WARN validation skipped for {schema_path.name}: missing jsonschema dependency",
            flush=True,
        )
        return
    validator = Draft202012Validator(_read_json(schema_path))
    for idx, row in enumerate(rows):
        errors = sorted(validator.iter_errors(row), key=lambda e: e.path)
        if errors:
            raise ValueError(f"{schema_path.name} row {idx} invalid: {[e.message for e in errors]}")


def _select_ref_source(data_dir: Path) -> tuple[str | None, list[dict[str, str]]]:
    master_ref = data_dir / "master_ref.csv"
    master_index = data_dir / "master_index.csv"
    if master_ref.exists() and master_ref.stat().st_size > 0:
        rows = _read_csv(master_ref)
        if rows:
            return str(master_ref), rows
    if master_index.exists() and master_index.stat().st_size > 0:
        rows = _read_csv(master_index)
        if rows:
            return str(master_index), rows
    return None, []


def _latest_digest_map_by_index(data_dir: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    digest_map_dir = data_dir / "digest_map"
    if not digest_map_dir.exists():
        return out
    for csv_file in sorted(digest_map_dir.glob("*.csv")):
        for row in _read_csv(csv_file):
            idx = str(row.get("index_id") or "").strip()
            if idx:
                out[idx] = row
    return out


def export_news_ref(data_dir: Path, storage_dir: Path, contracts_dir: Path, digest_at: str, export_at: str) -> ExportResult:
    source_path, source_rows = _select_ref_source(data_dir)
    if not source_rows:
        return ExportResult("news_ref.v1", "noop", 0, None, None, None, "missing master_ref/master_index input")

    digest_map_latest = _latest_digest_map_by_index(data_dir)
    out_rows: list[dict[str, Any]] = []

    for row in source_rows:
        index_id = str(row.get("index_id") or row.get("IndexID") or "").strip()
        if not index_id:
            continue
        source = str(row.get("source") or row.get("Source") or "").strip()
        link = str(row.get("link") or row.get("Link") or "").strip()
        first_seen = _to_rfc3339(row.get("first_seen") or row.get("FirstSeen") or row.get("Published"))
        last_seen = _to_rfc3339(row.get("last_seen") or row.get("LastSeen") or row.get("Published"))

        dmap = digest_map_latest.get(index_id, {})
        digest_file = str(row.get("digest_file") or dmap.get("digest_file") or "unknown.csv")
        article_id = str(row.get("article_id") or dmap.get("article_id") or index_id)

        out_rows.append(
            {
                "schema_name": "news_ref.v1",
                "schema_status": "stable",
                "index_id": index_id,
                "source": source or "unknown",
                "link": link or "https://example.invalid",
                "first_seen": first_seen,
                "last_seen": last_seen,
                "topics": _parse_maybe_struct(row.get("topics"), []),
                "meta": _parse_maybe_struct(row.get("meta"), {}),
                "digest_file": digest_file,
                "article_id": article_id,
                "join_key": f"{digest_file}::{article_id}",
            }
        )

    if not out_rows:
        return ExportResult("news_ref.v1", "noop", 0, source_path, None, None, "source rows missing index_id")

    schema = contracts_dir / "schemas" / "news_ref.v1.json"
    _validate_rows(out_rows, schema)

    out_dir = storage_dir / "buses" / "news_ref" / "v1"
    out_file = out_dir / f"news_ref_{export_at}.jsonl"
    manifest = out_dir / f"manifest_{export_at}.json"
    previous_output = _load_previous_export_output(storage_dir, digest_at, "news_ref.v1")
    if _rows_match_previous_output(out_rows, previous_output):
        _write_json(
            manifest,
            {
                "schema": "news_ref.v1",
                "status": "skipped_duplicate",
                "export_at": export_at,
                "digest_at": digest_at,
                "row_count": len(out_rows),
                "source_file": source_path,
                "duplicate_of": previous_output,
            },
        )
        return ExportResult(
            "news_ref.v1",
            "skipped_duplicate",
            len(out_rows),
            source_path,
            previous_output,
            str(manifest),
            "content identical to latest successful export for digest_at",
        )

    _write_jsonl(out_file, out_rows)
    _write_json(
        manifest,
        {
            "schema": "news_ref.v1",
            "status": "exported",
            "export_at": export_at,
            "digest_at": digest_at,
            "row_count": len(out_rows),
            "source_file": source_path,
            "source_fields": ["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"],
            "contract_fields": [
                "schema_name",
                "schema_status",
                "index_id",
                "source",
                "link",
                "first_seen",
                "last_seen",
                "topics",
                "meta",
                "digest_file",
                "article_id",
                "join_key",
            ],
            "transforms": [
                "master_ref/master_index => canonical fields",
                "digest_map by index_id => digest_file/article_id fallback",
                "topics/meta parse from csv serialized values",
            ],
            "fallback_behavior": "use master_index when master_ref is missing/empty",
            "no_op_behavior": "noop when neither master_ref nor master_index has rows",
            "quarantine_behavior": "fail-fast on schema validation errors",
            "output_file": str(out_file),
        },
    )
    return ExportResult("news_ref.v1", "exported", len(out_rows), source_path, str(out_file), str(manifest))


def _digest_rows_from_digest_jsonl(digest_jsonl: Path) -> list[dict[str, Any]]:
    rows = list(_iter_jsonl(digest_jsonl))
    out: list[dict[str, Any]] = []
    for row in rows:
        if {
            "schema_name",
            "schema_status",
            "digest_group_id",
            "digest_id_hour",
            "window_type",
            "topic",
            "group_number",
            "content",
        }.issubset(row.keys()):
            out.append(row)
    return out


def _digest_rows_from_digest_map(data_dir: Path, digest_at: str) -> list[dict[str, Any]]:
    digest_map = data_dir / "digest_map" / f"{digest_at}.csv"
    if not digest_map.exists() or digest_map.stat().st_size == 0:
        return []
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in _read_csv(digest_map):
        w = str(row.get("window_type") or "A").strip() or "A"
        topic = str(row.get("Topic") or "All Topics").strip() or "All Topics"
        grouped.setdefault((w, topic), []).append(row)

    out: list[dict[str, Any]] = []
    for (window_type, topic), rows in sorted(grouped.items()):
        content = []
        for r in rows:
            content.append(
                {
                    "article_id": str(r.get("article_id") or ""),
                    "title": str(r.get("Title") or "").strip() or "(untitled)",
                    "source": str(r.get("Source") or "").strip() or "unknown",
                    "link": str(r.get("Link") or "").strip() or "https://example.invalid",
                    "published": _to_rfc3339(r.get("Published")),
                }
            )
        out.append(
            {
                "schema_name": "news_digest_group.v1",
                "schema_status": "experimental_structured",
                "digest_group_id": f"{digest_at}:{window_type}:{topic}:1",
                "digest_id_hour": digest_at,
                "window_type": window_type,
                "topic": topic,
                "group_number": 1,
                "content": content,
            }
        )
    return out


def export_news_digest_group(
    data_dir: Path, storage_dir: Path, contracts_dir: Path, digest_at: str, export_at: str
) -> ExportResult:
    digest_jsonl = data_dir / "digest_jsonls" / f"{digest_at}.jsonl"
    out_rows: list[dict[str, Any]] = []
    source: str | None = None

    if digest_jsonl.exists() and digest_jsonl.stat().st_size > 0:
        from_jsonl = _digest_rows_from_digest_jsonl(digest_jsonl)
        if from_jsonl:
            out_rows = from_jsonl
            source = str(digest_jsonl)

    if not out_rows:
        from_map = _digest_rows_from_digest_map(data_dir, digest_at)
        if from_map:
            out_rows = from_map
            source = str(data_dir / "digest_map" / f"{digest_at}.csv")

    if not out_rows:
        return ExportResult(
            "news_digest_group.v1",
            "noop",
            0,
            None,
            None,
            None,
            "missing digest_jsonls structured rows and digest_map fallback",
        )

    schema = contracts_dir / "schemas" / "news_digest_group.v1.json"
    _validate_rows(out_rows, schema)

    out_dir = storage_dir / "buses" / "news_digest_group" / "v1"
    out_file = out_dir / f"news_digest_group_{digest_at}_{export_at}.jsonl"
    manifest = out_dir / f"manifest_{digest_at}_{export_at}.json"
    previous_output = _load_previous_export_output(storage_dir, digest_at, "news_digest_group.v1")
    if _rows_match_previous_output(out_rows, previous_output):
        _write_json(
            manifest,
            {
                "schema": "news_digest_group.v1",
                "status": "skipped_duplicate",
                "export_at": export_at,
                "digest_at": digest_at,
                "row_count": len(out_rows),
                "source_file": source,
                "duplicate_of": previous_output,
            },
        )
        return ExportResult(
            "news_digest_group.v1",
            "skipped_duplicate",
            len(out_rows),
            source,
            previous_output,
            str(manifest),
            "content identical to latest successful export for digest_at",
        )

    _write_jsonl(out_file, out_rows)
    _write_json(
        manifest,
        {
            "schema": "news_digest_group.v1",
            "status": "exported",
            "export_at": export_at,
            "digest_at": digest_at,
            "row_count": len(out_rows),
            "source_file": source,
            "source_fields": ["digest_group_id", "digest_id_hour", "window_type", "topic", "group_number", "content"],
            "contract_fields": ["schema_name", "schema_status", "digest_group_id", "digest_id_hour", "window_type", "topic", "group_number", "content"],
            "transforms": [
                "pass-through when digest_jsonls already structured",
                "fallback build from digest_map grouped by window_type/topic",
            ],
            "fallback_behavior": "use digest_map/<DIGEST_AT>.csv when digest_jsonls is missing or legacy-only",
            "no_op_behavior": "noop when both digest_jsonls and digest_map are unavailable/empty",
            "quarantine_behavior": "fail-fast on schema validation errors",
            "output_file": str(out_file),
        },
    )
    return ExportResult("news_digest_group.v1", "exported", len(out_rows), source, str(out_file), str(manifest))


def write_indexes(storage_dir: Path, digest_at: str, export_at: str, results: list[ExportResult]) -> Path:
    idx_dir = storage_dir / "indexes"
    idx_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "digest_at": digest_at,
        "export_at": export_at,
        "status": _run_status(results),
        "results": [r.__dict__ for r in results],
    }
    latest = idx_dir / "pr3a_exports_latest.json"
    run_file = idx_dir / f"pr3a_exports_{digest_at}_{export_at}.json"
    _write_json(latest, payload)
    _write_json(run_file, payload)
    return run_file


def write_run_record(storage_dir: Path, digest_at: str, export_at: str, results: list[ExportResult]) -> Path:
    runs_dir = storage_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = runs_dir / f"pr3a_export_{digest_at}_{export_at}.json"
    _write_json(
        run_path,
        {
            "job": "export_pr3a_buses",
            "digest_at": digest_at,
            "export_at": export_at,
            "status": _run_status(results),
            "results": [r.__dict__ for r in results],
        },
    )
    return run_path




def _build_compact_summary(
    previous: dict[str, Any],
    digest_at: str,
    export_at: str,
    results: list[ExportResult],
    export_status: str,
    failure_reason: str | None,
) -> dict[str, Any]:
    news_ref = next((r for r in results if r.name == "news_ref.v1"), None)
    news_digest = next((r for r in results if r.name == "news_digest_group.v1"), None)

    summary = {
        "last_successful_export_at": previous.get("last_successful_export_at"),
        "last_exported_digest_at": previous.get("last_exported_digest_at"),
        "news_ref_count": int(previous.get("news_ref_count") or 0),
        "news_digest_group_count": int(previous.get("news_digest_group_count") or 0),
        "export_status": export_status,
        "failure_reason": failure_reason,
    }

    if export_status == "success":
        summary.update(
            {
                "last_successful_export_at": _compact_to_rfc3339(export_at),
                "last_exported_digest_at": digest_at,
                "news_ref_count": news_ref.count if news_ref else 0,
                "news_digest_group_count": news_digest.count if news_digest else 0,
                "failure_reason": None,
            }
        )
    return summary


def write_compact_summary(
    storage_dir: Path,
    digest_at: str,
    export_at: str,
    results: list[ExportResult],
    export_status: str,
    failure_reason: str | None,
) -> Path:
    idx_dir = storage_dir / "indexes"
    idx_dir.mkdir(parents=True, exist_ok=True)
    latest = idx_dir / "pr3a_export_compact_latest.json"

    previous: dict[str, Any] = {}
    if latest.exists():
        try:
            previous = _read_json(latest)
        except Exception:
            previous = {}

    payload = _build_compact_summary(previous, digest_at, export_at, results, export_status, failure_reason)
    _write_json(latest, payload)

    run_file = idx_dir / f"pr3a_export_compact_{digest_at}_{export_at}.json"
    _write_json(run_file, payload)
    return latest

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PR3a real exports from legacy outputs to storage buses/indexes")
    p.add_argument("--digest-at", required=True, help="Hour bucket YYYYMMDDTHH")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--storage-dir", default="storage")
    p.add_argument("--contracts-dir", default="contracts")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    digest_at = args.digest_at
    export_at = _utc_now_compact()
    data_dir = Path(args.data_dir)
    storage_dir = Path(args.storage_dir)
    contracts_dir = Path(args.contracts_dir)

    try:
        results = [
            export_news_ref(data_dir, storage_dir, contracts_dir, export_at),
            export_news_digest_group(data_dir, storage_dir, contracts_dir, digest_at, export_at),
        ]

        run_record = write_run_record(storage_dir, digest_at, export_at, results)
        index_record = write_indexes(storage_dir, digest_at, export_at, results)
        compact_summary = write_compact_summary(
            storage_dir, digest_at, export_at, results, export_status="success", failure_reason=None
        )

        print(f"[pr3a-export] digest_at={digest_at} export_at={export_at}")
        for r in results:
            print(f"[pr3a-export] {r.name} status={r.status} count={r.count} source={r.source} output={r.output_path}")
        print(f"[pr3a-export] run_record={run_record}")
        print(f"[pr3a-export] index_record={index_record}")
        print(f"[pr3a-export] compact_summary={compact_summary}")
        return 0
    except Exception as exc:
        reason = f"{exc.__class__.__name__}: {exc}"
        compact_summary = write_compact_summary(
            storage_dir,
            digest_at,
            export_at,
            results=[],
            export_status="failed",
            failure_reason=reason,
        )
        print(f"[pr3a-export] ERROR export failed: {reason}", flush=True)
        print(f"[pr3a-export] compact_summary={compact_summary}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
