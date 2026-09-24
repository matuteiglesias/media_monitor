#!/usr/bin/env python3
"""Read-only, bounded-memory census for legacy ``news_ref`` JSONL snapshots.

The script deliberately treats a snapshot as a mapping of ``index_id`` to a
canonical JSON value.  The canonical representation is UTF-8 JSON with sorted
object keys, compact separators, and the original array order.  Thus cosmetic
whitespace/object-key ordering does not create a false record version, while a
changed array order remains a change (arrays are contract data).

It never writes below --bus-dir.  Its working set is a current snapshot map
and one SHA-256/length entry per distinct logical row version; it never loads
the corpus or payload versions into memory.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterator

try:
    import orjson
except ImportError:  # pragma: no cover - kept runnable in the base environment
    orjson = None


CANONICAL_SEPARATORS = (",", ":")


def canonical_bytes(value: Any) -> bytes:
    if orjson is not None:
        return orjson.dumps(value, option=orjson.OPT_SORT_KEYS)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=CANONICAL_SEPARATORS).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def legacy_files(bus_dir: Path) -> list[Path]:
    return sorted(p for p in bus_dir.glob("news_ref_*.jsonl") if p.name != "news_ref_current.jsonl")


def iter_rows(path: Path) -> Iterator[tuple[int, bytes, dict[str, Any] | None, str | None]]:
    with path.open("rb") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                row = orjson.loads(raw) if orjson is not None else json.loads(raw)
            except json.JSONDecodeError as exc:
                yield line_no, raw.rstrip(b"\r\n"), None, str(exc)
                continue
            if not isinstance(row, dict):
                yield line_no, raw.rstrip(b"\r\n"), None, "row is not an object"
                continue
            yield line_no, raw.rstrip(b"\r\n"), row, None


def _semantic_digest(current: dict[str, str]) -> str:
    h = hashlib.sha256()
    for index_id in sorted(current):
        h.update(index_id.encode("utf-8"))
        h.update(b"\0")
        h.update(current[index_id].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def _json_dump_counter(counter: collections.Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def audit(bus_dir: Path, output: Path, work_db: Path | None = None, keep_work_db: bool = False) -> dict[str, Any]:
    files = legacy_files(bus_dir)
    # One SHA-256 and its canonical length per distinct logical row version are
    # retained in memory; full payloads and historical snapshots never are.
    known_versions: dict[str, int] = {}
    versions_per_index_id = collections.Counter()
    snapshots: list[tuple[Any, ...]] = []
    field_snapshots: dict[str, list[int]] = {}
    field_non_null = collections.Counter()
    field_observations = collections.Counter()
    field_value_bytes = collections.Counter()
    schema_signatures = collections.Counter()
    malformed_rows: list[dict[str, Any]] = []
    duplicate_ids: list[dict[str, Any]] = []
    previous: dict[str, str] = {}
    first_semantic: dict[str, str] = {}
    t0 = time.perf_counter()

    for ordinal, path in enumerate(files):
        current: dict[str, str] = {}
        raw_h = hashlib.sha256()
        keyset: set[str] = set()
        rows = 0
        for line_no, raw, row, parse_error in iter_rows(path):
            rows += 1
            raw_h.update(raw)
            raw_h.update(b"\n")
            if row is None:
                malformed_rows.append({"file": path.name, "line": line_no, "reason": parse_error})
                # Preserve its unique raw identity in the semantic accounting;
                # an archive must retain this quarantined raw line verbatim.
                index_id = f"__malformed__:{path.name}:{line_no}"
                content_hash = digest(raw)
                current[index_id] = content_hash
                if content_hash not in known_versions:
                    known_versions[content_hash] = len(raw)
                    versions_per_index_id[index_id] += 1
                continue
            index_id = row.get("index_id")
            if not isinstance(index_id, str) or not index_id:
                malformed_rows.append({"file": path.name, "line": line_no, "reason": "missing/non-string index_id"})
                index_id = f"__malformed__:{path.name}:{line_no}"
            canonical = canonical_bytes(row)
            content_hash = digest(canonical)
            if index_id in current:
                duplicate_ids.append({"file": path.name, "line": line_no, "index_id": index_id})
            current[index_id] = content_hash
            keyset.update(row)
            for key, value in row.items():
                field_observations[key] += 1
                if value is not None:
                    field_non_null[key] += 1
                    field_value_bytes[key] += len(canonical_bytes(value))
                bounds = field_snapshots.setdefault(key, [ordinal, ordinal])
                bounds[0] = min(bounds[0], ordinal)
                bounds[1] = max(bounds[1], ordinal)
            if content_hash not in known_versions:
                known_versions[content_hash] = len(canonical)
                versions_per_index_id[index_id] += 1
        added = len(current.keys() - previous.keys())
        removed = len(previous.keys() - current.keys())
        common = current.keys() & previous.keys()
        changed = sum(current[key] != previous[key] for key in common)
        unchanged = len(common) - changed
        semantic = _semantic_digest(current)
        signature = digest(canonical_bytes(sorted(keyset)))
        schema_signatures[signature] += 1
        first_semantic.setdefault(semantic, path.name)
        snapshots.append((path.name, path.stat().st_size, rows, len(current), raw_h.hexdigest(), semantic,
                          added, removed, changed, unchanged, signature))
        previous = current
        if (ordinal + 1) % 100 == 0:
            print(f"[news-ref-audit] snapshots={ordinal + 1}/{len(files)} elapsed={time.perf_counter() - t0:.1f}s", flush=True)

    snapshot_rows = snapshots
    unique_versions = len(known_versions)
    unique_version_bytes = sum(known_versions.values())
    unique_contents = unique_versions
    unique_ids = len(versions_per_index_id)
    version_distribution = collections.Counter(versions_per_index_id.values()).items()
    total_source = sum(row[1] for row in snapshot_rows)
    total_rows = sum(row[2] for row in snapshot_rows)
    exact_duplicate_files = sum(1 for row in snapshot_rows if first_semantic[row[5]] != row[0])
    current_fields = set(json.loads((Path(__file__).parents[1] / "contracts/schemas/news_ref.v1.json").read_text())["properties"])
    field_report = {}
    for key in sorted(field_observations):
        field_report[key] = {
            "observations": field_observations[key],
            "non_null": field_non_null[key],
            "null_or_absent_observations": total_rows - field_non_null[key],
            "non_null_ratio": round(field_non_null[key] / total_rows, 8) if total_rows else 0,
            "serialized_value_bytes": field_value_bytes[key],
            "first_snapshot_ordinal": field_snapshots[key][0],
            "last_snapshot_ordinal": field_snapshots[key][1],
            "in_current_contract": key in current_fields,
        }
    report = {
        "schema_name": "news_ref_historical_audit.v1",
        "canonicalization": {
            "algorithm": "UTF-8 JSON, sort_keys=true, separators=(',', ':'), ensure_ascii=false; arrays retain source order",
            "content_hash": "sha256(canonical row bytes)",
            "snapshot_hash": "sha256 of lexicographically sorted index_id + NUL + row content hash pairs",
            "effect": "ignores JSON whitespace/object-key order; preserves all keys, values, types, and array order",
        },
        "input": {"bus_dir": str(bus_dir), "snapshot_count": len(files), "source_bytes": total_source, "rows": total_rows},
        "integrity": {"malformed_row_count": len(malformed_rows), "duplicate_index_id_row_count": len(duplicate_ids), "examples": (malformed_rows + duplicate_ids)[:20]},
        "deduplication": {
            "unique_index_ids": unique_ids,
            "unique_index_id_content_versions": unique_versions,
            "unique_canonical_row_contents": unique_contents,
            "unique_canonical_row_bytes": unique_version_bytes,
            "logical_row_reuse_ratio": round(1 - unique_versions / total_rows, 8) if total_rows else 0,
            "canonical_unique_to_source_ratio": round(unique_version_bytes / total_source, 8) if total_source else 0,
            "versions_per_index_id_distribution": [{"versions": versions, "index_ids": count} for versions, count in version_distribution],
        },
        "snapshots": [
            {"filename": r[0], "source_bytes": r[1], "rows": r[2], "index_ids": r[3], "raw_row_sha256": r[4], "semantic_sha256": r[5], "added": r[6], "removed": r[7], "changed": r[8], "unchanged": r[9], "schema_signature": r[10], "same_semantic_state_as": first_semantic[r[5]]}
            for r in snapshot_rows
        ],
        "snapshot_redundancy": {"semantically_identical_nonfirst_snapshots": exact_duplicate_files, "distinct_semantic_states": len(first_semantic), "distinct_schema_signatures": len(schema_signatures)},
        "fields": field_report,
        "historical_only_fields": sorted(set(field_report) - current_fields),
        "current_contract_fields_never_seen": sorted(current_fields - set(field_report)),
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only streaming census of historical news_ref snapshots")
    parser.add_argument("--bus-dir", default="storage/buses/news_ref/v1", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--work-db", type=Path, help="deprecated compatibility option; no database is created")
    parser.add_argument("--keep-work-db", action="store_true", help="deprecated compatibility option")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit(args.bus_dir, args.output, args.work_db, args.keep_work_db)
    print(json.dumps({"snapshots": report["input"]["snapshot_count"], "source_bytes": report["input"]["source_bytes"], "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
