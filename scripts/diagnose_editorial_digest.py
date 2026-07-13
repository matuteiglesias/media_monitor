#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


def _iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any] | None, str | None]]:
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                yield lineno, None, f"invalid_json: {exc.msg}"
                continue
            if not isinstance(row, dict):
                yield lineno, None, f"invalid_row_type: {type(row).__name__}"
                continue
            yield lineno, row, None


def _jsonl_stats(path: Path) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "rows": 0,
        "bad_rows": 0,
        "bad_reasons": {},
    }
    if not path.exists() or not path.is_file():
        return stats

    bad_reasons: Counter[str] = Counter()
    for _, row, error in _iter_jsonl(path):
        if error:
            stats["bad_rows"] += 1
            bad_reasons[error] += 1
            continue
        if row is not None:
            stats["rows"] += 1
    stats["bad_reasons"] = dict(bad_reasons)
    return stats


def _csv_stats(path: Path) -> dict[str, Any]:
    stats = {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "rows": 0,
        "columns": [],
    }
    if not path.exists() or not path.is_file():
        return stats
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        stats["columns"] = reader.fieldnames or []
        stats["rows"] = sum(1 for _ in reader)
    return stats


def _quarantine_files(quarantine_dir: Path, digest_at: str, prefix: str | None = None) -> list[Path]:
    files = sorted(quarantine_dir.glob(f"V*{digest_at}*.jsonl"))
    if prefix:
        files = [path for path in files if path.name.startswith(prefix)]
    return files


def _summarize_quarantine(files: list[Path]) -> dict[str, Any]:
    reason_counts: Counter[str] = Counter()
    rows = 0
    bad_rows = 0
    examples: list[dict[str, Any]] = []

    for path in files:
        for _, row, error in _iter_jsonl(path):
            if error:
                bad_rows += 1
                reason_counts[error] += 1
                continue
            if row is None:
                continue
            rows += 1
            reason = str(row.get("reason") or "unknown")
            reason_counts[reason] += 1
            if len(examples) < 5:
                examples.append(
                    {
                        "file": str(path),
                        "reason": reason,
                        "detail": {
                            key: row.get(key)
                            for key in ("error", "msg", "note", "file", "digest_id", "path")
                            if row.get(key) is not None
                        },
                    }
                )

    return {
        "exists": bool(files),
        "files": [str(path) for path in files],
        "rows": rows,
        "bad_rows": bad_rows,
        "reason_counts": dict(reason_counts),
        "examples": examples,
    }


def _pf_shape_stats(files: list[Path]) -> dict[str, Any]:
    rows = 0
    bad_json_rows = 0
    valid_shape_rows = 0
    invalid_shape: Counter[str] = Counter()
    seed_ideas_count = 0

    for path in files:
        for _, row, error in _iter_jsonl(path):
            if error:
                bad_json_rows += 1
                invalid_shape[error] += 1
                continue
            if row is None:
                continue
            rows += 1

            row_errors: list[str] = []
            if not str(row.get("digest_group_id") or "").strip():
                row_errors.append("missing_digest_group_id")

            seed_obj = row.get("seed_ideas")
            if not isinstance(seed_obj, dict):
                row_errors.append("missing_seed_ideas_object")
            else:
                ideas = seed_obj.get("seed_ideas")
                if not isinstance(ideas, list):
                    row_errors.append("missing_seed_ideas_list")
                else:
                    seed_ideas_count += len([idea for idea in ideas if isinstance(idea, dict)])

            if row_errors:
                for reason in row_errors:
                    invalid_shape[reason] += 1
            else:
                valid_shape_rows += 1

    return {
        "exists": bool(files),
        "files": [str(path) for path in files],
        "rows": rows,
        "bad_json_rows": bad_json_rows,
        "valid_shape_rows": valid_shape_rows,
        "invalid_shape_counts": dict(invalid_shape),
        "seed_ideas_count": seed_ideas_count,
    }


def _count_piece_briefs(storage_dir: Path, digest_at: str) -> dict[str, Any]:
    bus_dir = storage_dir / "buses" / "news_piece_brief" / "v1"
    files = sorted(bus_dir.glob("*.jsonl"))
    rows = 0
    brief_ids: set[str] = set()
    bad_rows = 0
    for path in files:
        for _, row, error in _iter_jsonl(path):
            if error:
                bad_rows += 1
                continue
            if row is None:
                continue
            if str(row.get("schema_name") or "") != "news_piece_brief.v1":
                continue
            if str(row.get("digest_id_hour") or "") != digest_at:
                continue
            rows += 1
            brief_id = str(row.get("brief_id") or "").strip()
            if brief_id:
                brief_ids.add(brief_id)
    return {
        "bus_dir": str(bus_dir),
        "exists": bus_dir.exists(),
        "files_scanned": len(files),
        "rows": rows,
        "bad_rows": bad_rows,
        "brief_ids": sorted(brief_ids),
    }


def _count_drafts(storage_dir: Path, data_dir: Path, digest_at: str, brief_ids: set[str]) -> dict[str, Any]:
    article_dir = storage_dir / "buses" / "news_article_draft" / "v1"
    yt_dir = storage_dir / "buses" / "news_yt_script_draft" / "v1"
    mirror_dir = data_dir / "drafts" / digest_at

    def count_bus(bus_dir: Path, schema_name: str) -> dict[str, Any]:
        files = sorted(bus_dir.glob("*.jsonl"))
        rows = 0
        bad_rows = 0
        for path in files:
            for _, row, error in _iter_jsonl(path):
                if error:
                    bad_rows += 1
                    continue
                if row is None:
                    continue
                if str(row.get("schema_name") or "") != schema_name:
                    continue
                row_brief_id = str(row.get("brief_id") or "").strip()
                if brief_ids and row_brief_id not in brief_ids:
                    continue
                rows += 1
        return {
            "bus_dir": str(bus_dir),
            "exists": bus_dir.exists(),
            "files_scanned": len(files),
            "rows": rows,
            "bad_rows": bad_rows,
        }

    mirror_files = sorted(mirror_dir.glob("*.jsonl")) if mirror_dir.exists() else []
    mirror_rows = 0
    mirror_bad_rows = 0
    for path in mirror_files:
        stats = _jsonl_stats(path)
        mirror_rows += int(stats["rows"])
        mirror_bad_rows += int(stats["bad_rows"])

    return {
        "article": count_bus(article_dir, "news_article_draft.v1"),
        "yt_script": count_bus(yt_dir, "news_yt_script_draft.v1"),
        "legacy_mirror": {
            "dir": str(mirror_dir),
            "exists": mirror_dir.exists(),
            "files_scanned": len(mirror_files),
            "rows": mirror_rows,
            "bad_rows": mirror_bad_rows,
        },
    }


def _read_editorial_latest(storage_dir: Path, public_dir: Path, digest_at: str) -> dict[str, Any]:
    candidates = [
        storage_dir / "indexes" / "editorial_latest.json",
        public_dir / "editorial_latest.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"path": str(path), "exists": True, "error": f"invalid_json: {exc.msg}"}
        if not isinstance(payload, dict):
            return {"path": str(path), "exists": True, "error": "invalid_root"}
        return {
            "path": str(path),
            "exists": True,
            "digest_at": payload.get("digest_at"),
            "matches_requested_digest": payload.get("digest_at") == digest_at,
            "status": payload.get("status"),
            "human_handoff_status": (payload.get("human_handoff") or {}).get("status")
            if isinstance(payload.get("human_handoff"), dict)
            else None,
            "metrics": payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {},
            "quarantine_pointers": (payload.get("pointers") or {}).get("quarantine_files", [])
            if isinstance(payload.get("pointers"), dict)
            else [],
        }
    return {"exists": False, "path": str(candidates[0])}


def _summarize_editorial_quarantine_pointers(editorial_latest: dict[str, Any]) -> dict[str, Any]:
    pointers = editorial_latest.get("quarantine_pointers")
    if not isinstance(pointers, list):
        pointers = []

    pointer_rows: list[dict[str, Any]] = []
    for pointer in pointers:
        path = Path(str(pointer))
        summary = _summarize_quarantine([path] if path.exists() else [])
        pointer_rows.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "rows": summary["rows"],
                "reason_counts": summary["reason_counts"],
                "examples": summary["examples"],
            }
        )

    return {
        "exists": bool(pointer_rows),
        "pointers": pointer_rows,
        "missing_pointer_files": [row["path"] for row in pointer_rows if not row["exists"]],
    }


def _blocking_reason(report: dict[str, Any]) -> str:
    digest_jsonl = report["digest_jsonl"]
    if not digest_jsonl["exists"]:
        return f"missing_digest_jsonl: {digest_jsonl['path']}"
    if digest_jsonl["rows"] == 0:
        return f"empty_digest_jsonl: {digest_jsonl['path']}"
    if digest_jsonl["bad_rows"]:
        return f"invalid_digest_jsonl: {digest_jsonl['bad_reasons']}"

    stage01 = report["quarantine"]["stage01"]
    stage02 = report["quarantine"]["stage02"]
    pointer_quarantine = report["quarantine"].get("editorial_latest_pointers", {})
    if stage01["exists"]:
        return f"stage01_quarantine: {stage01['reason_counts']}"
    if stage02["exists"]:
        return f"stage02_quarantine: {stage02['reason_counts']}"
    missing_pointer_files = pointer_quarantine.get("missing_pointer_files") or []
    if missing_pointer_files:
        return f"editorial_latest_references_missing_quarantine_files: {missing_pointer_files}"

    pf = report["pf_output"]
    if not pf["exists"]:
        return "missing_pf_output: no data/pf_out/pfout_<DIGEST_AT>*.jsonl files"
    if pf["rows"] == 0:
        return "empty_pf_output"
    if pf["valid_shape_rows"] == 0:
        return f"invalid_pf_output_shape: {pf['invalid_shape_counts']}"
    if pf["seed_ideas_count"] == 0:
        return "no_seed_ideas_in_pf_output"

    briefs = report["piece_brief_bus"]
    if briefs["rows"] == 0:
        return "missing_piece_briefs_for_digest"

    drafts = report["draft_bus"]
    draft_count = drafts["article"]["rows"] + drafts["yt_script"]["rows"] + drafts["legacy_mirror"]["rows"]
    if draft_count == 0:
        return "missing_drafts_for_digest"

    editorial = report["editorial_latest"]
    if not editorial["exists"]:
        return "missing_editorial_latest_index"
    if not editorial.get("matches_requested_digest"):
        return f"editorial_latest_digest_mismatch: {editorial.get('digest_at')}"
    if editorial.get("status") != "ok":
        return f"editorial_latest_not_ok: {editorial.get('status')}"

    return "no_blocker_detected"


def diagnose(digest_at: str, data_dir: Path, storage_dir: Path, public_dir: Path) -> dict[str, Any]:
    digest_jsonl = _jsonl_stats(data_dir / "digest_jsonls" / f"{digest_at}.jsonl")
    digest_map = _csv_stats(data_dir / "digest_map" / f"{digest_at}.csv")
    quarantine_dir = data_dir / "quarantine"
    stage01 = _summarize_quarantine(_quarantine_files(quarantine_dir, digest_at, "V01"))
    stage02 = _summarize_quarantine(_quarantine_files(quarantine_dir, digest_at, "V02"))
    pf_output = _pf_shape_stats(sorted((data_dir / "pf_out").glob(f"pfout_{digest_at}*.jsonl")))
    piece_briefs = _count_piece_briefs(storage_dir, digest_at)
    draft_bus = _count_drafts(storage_dir, data_dir, digest_at, set(piece_briefs["brief_ids"]))
    editorial_latest = _read_editorial_latest(storage_dir, public_dir, digest_at)
    all_quarantine = _summarize_quarantine(_quarantine_files(quarantine_dir, digest_at))
    editorial_quarantine_pointers = _summarize_editorial_quarantine_pointers(editorial_latest)

    report = {
        "digest_at": digest_at,
        "digest_jsonl": digest_jsonl,
        "digest_map": digest_map,
        "quarantine": {
            "stage01": stage01,
            "stage02": stage02,
            "all_for_digest": all_quarantine,
            "editorial_latest_pointers": editorial_quarantine_pointers,
        },
        "pf_output": pf_output,
        "piece_brief_bus": piece_briefs,
        "draft_bus": draft_bus,
        "editorial_latest": editorial_latest,
    }
    report["blocking_reason"] = _blocking_reason(report)
    return report


def _print_human(report: dict[str, Any]) -> None:
    print(f"[diagnose-editorial] digest_at={report['digest_at']}")
    print(f"[diagnose-editorial] blocking_reason={report['blocking_reason']}")
    print(
        "[diagnose-editorial] digest_jsonl "
        f"exists={report['digest_jsonl']['exists']} rows={report['digest_jsonl']['rows']} "
        f"bad_rows={report['digest_jsonl']['bad_rows']} path={report['digest_jsonl']['path']}"
    )
    print(
        "[diagnose-editorial] digest_map "
        f"exists={report['digest_map']['exists']} rows={report['digest_map']['rows']} "
        f"path={report['digest_map']['path']}"
    )
    for label in ("stage01", "stage02"):
        q = report["quarantine"][label]
        print(
            f"[diagnose-editorial] quarantine_{label} "
            f"exists={q['exists']} rows={q['rows']} reasons={q['reason_counts']}"
        )
    pointer_quarantine = report["quarantine"]["editorial_latest_pointers"]
    print(
        "[diagnose-editorial] editorial_quarantine_pointers "
        f"exists={pointer_quarantine['exists']} "
        f"missing_files={pointer_quarantine['missing_pointer_files']}"
    )
    pf = report["pf_output"]
    print(
        "[diagnose-editorial] pf_output "
        f"exists={pf['exists']} rows={pf['rows']} valid_shape_rows={pf['valid_shape_rows']} "
        f"seed_ideas={pf['seed_ideas_count']} invalid_shape={pf['invalid_shape_counts']}"
    )
    briefs = report["piece_brief_bus"]
    print(
        "[diagnose-editorial] piece_brief_bus "
        f"exists={briefs['exists']} rows={briefs['rows']} files_scanned={briefs['files_scanned']}"
    )
    drafts = report["draft_bus"]
    print(
        "[diagnose-editorial] draft_bus "
        f"article_rows={drafts['article']['rows']} yt_script_rows={drafts['yt_script']['rows']} "
        f"legacy_mirror_rows={drafts['legacy_mirror']['rows']}"
    )
    editorial = report["editorial_latest"]
    print(
        "[diagnose-editorial] editorial_latest "
        f"exists={editorial['exists']} status={editorial.get('status')} "
        f"human_handoff={editorial.get('human_handoff_status')} path={editorial.get('path')}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose why an editorial digest is degraded or empty")
    parser.add_argument("--digest-at", required=True, help="Digest hour to inspect, e.g. 20260713T19")
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--storage-dir", default="storage")
    parser.add_argument("--public-dir", default="apps/news_site/public/data")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    parser.add_argument("--json-only", action="store_true", help="Print only the JSON report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = diagnose(
        args.digest_at,
        Path(args.data_dir),
        Path(args.storage_dir),
        Path(args.public_dir),
    )
    if not args.json_only:
        _print_human(report)
    if args.json or args.json_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
