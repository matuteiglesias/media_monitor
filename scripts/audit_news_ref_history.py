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


def sha256_file(path: Path) -> str:
    """Hash the original file bytes, without newline/blank-line normalization."""
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def legacy_files(bus_dir: Path) -> list[Path]:
    return sorted(p for p in bus_dir.glob("news_ref_*.jsonl") if p.name != "news_ref_current.jsonl")


def iter_rows(path: Path) -> Iterator[tuple[int, bytes]]:
    with path.open("rb") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            yield line_no, raw.rstrip(b"\r\n")


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


def _percentiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {key: None for key in ("p50", "p75", "p90", "p95", "p99", "max")}
    ordered = sorted(values)
    def percentile(p: float) -> float:
        # Nearest-rank keeps the definition reproducible without a statistics dependency.
        return ordered[max(0, min(len(ordered) - 1, int((len(ordered) * p + 0.999999999) - 1)))]
    return {"p50": percentile(.50), "p75": percentile(.75), "p90": percentile(.90), "p95": percentile(.95), "p99": percentile(.99), "max": ordered[-1]}


def current_contract_error(row: dict[str, Any], contract_fields: set[str]) -> str | None:
    """Fast structural equivalent of the v1 schema (format validation is advisory in jsonschema)."""
    if set(row) != contract_fields:
        return "keys differ from current contract"
    if row.get("schema_name") != "news_ref.v1" or row.get("schema_status") != "stable":
        return "schema_name/schema_status differs from current contract"
    if not isinstance(row.get("index_id"), str) or not 8 <= len(row["index_id"]) <= 10 or not row["index_id"].isalnum():
        return "index_id violates current contract"
    if not all(isinstance(row.get(key), str) and row[key] for key in ("source", "link", "first_seen", "last_seen", "digest_file", "article_id", "join_key")):
        return "required string differs from current contract"
    if not isinstance(row.get("topics"), list) or not all(isinstance(x, str) for x in row["topics"]) or not isinstance(row.get("meta"), dict):
        return "topics/meta differs from current contract"
    return None


def audit(bus_dir: Path, output: Path, work_db: Path | None = None, keep_work_db: bool = False) -> dict[str, Any]:
    files = legacy_files(bus_dir)
    # One SHA-256 and its canonical length per distinct logical row version are
    # retained in memory; full payloads and historical snapshots never are.
    known_versions: dict[str, int] = {}
    # Most rows recur verbatim.  Cache raw-line -> canonical content hashes so
    # canonical serialization is paid once per distinct physical row spelling.
    raw_to_content: dict[str, tuple[str, int]] = {}
    parsed_by_raw: dict[str, tuple[dict[str, Any] | None, str | None]] = {}
    versions_per_index_id = collections.Counter()
    snapshots: list[tuple[Any, ...]] = []
    field_snapshots: dict[str, list[int]] = {}
    field_non_null = collections.Counter()
    field_observations = collections.Counter()
    field_value_bytes = collections.Counter()
    field_types: dict[str, collections.Counter[str]] = {}
    schema_signatures = collections.Counter()
    schema_history: dict[str, dict[str, Any]] = {}
    malformed_rows: list[dict[str, Any]] = []
    duplicate_ids: list[dict[str, Any]] = []
    previous: dict[str, str] = {}
    first_semantic: dict[str, str] = {}
    first_source_file: dict[str, str] = {}
    current_invalid_rows: list[dict[str, Any]] = []
    migration_status = collections.Counter()
    schema_path = Path(__file__).parents[1] / "contracts/schemas/news_ref.v1.json"
    current_fields = set(json.loads(schema_path.read_text())["properties"])
    t0 = time.perf_counter()

    for ordinal, path in enumerate(files):
        # This is merely a parser/canonicalization optimization.  Keep it to
        # the immediately preceding state so memory is O(one snapshot), while
        # global logical-version accounting remains exact in known_versions.
        if ordinal and ordinal % 2 == 0:
            raw_to_content.clear()
            parsed_by_raw.clear()
        current: dict[str, str] = {}
        raw_h = hashlib.sha256()
        keyset: set[str] = set()
        rows = 0
        snapshot_new_versions = 0
        for line_no, raw in iter_rows(path):
            rows += 1
            raw_h.update(raw)
            raw_h.update(b"\n")
            raw_hash = digest(raw)
            cached_parse = parsed_by_raw.get(raw_hash)
            if cached_parse is None:
                try:
                    candidate = orjson.loads(raw) if orjson is not None else json.loads(raw)
                    cached_parse = (candidate, None) if isinstance(candidate, dict) else (None, "row is not an object")
                except (json.JSONDecodeError, ValueError) as exc:
                    cached_parse = (None, str(exc))
                parsed_by_raw[raw_hash] = cached_parse
            row, parse_error = cached_parse
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
                migration_status["malformed-quarantined"] += 1
                continue
            contract_error = current_contract_error(row, current_fields)
            if contract_error:
                current_invalid_rows.append({"file": path.name, "line": line_no, "reason": contract_error})
                migration_status["legacy-preserved"] += 1
            else:
                migration_status["current-valid"] += 1
            index_id = row.get("index_id")
            if not isinstance(index_id, str) or not index_id:
                malformed_rows.append({"file": path.name, "line": line_no, "reason": "missing/non-string index_id"})
                index_id = f"__malformed__:{path.name}:{line_no}"
            cached = raw_to_content.get(raw_hash)
            if cached is None:
                canonical = canonical_bytes(row)
                cached = (digest(canonical), len(canonical))
                raw_to_content[raw_hash] = cached
            content_hash, canonical_length = cached
            if index_id in current:
                duplicate_ids.append({"file": path.name, "line": line_no, "index_id": index_id})
            current[index_id] = content_hash
            keyset.update(row)
            for key, value in row.items():
                field_observations[key] += 1
                field_types.setdefault(key, collections.Counter())[type(value).__name__] += 1
                if value is not None:
                    field_non_null[key] += 1
                    field_value_bytes[key] += len(canonical_bytes(value))
                bounds = field_snapshots.setdefault(key, [ordinal, ordinal])
                bounds[0] = min(bounds[0], ordinal)
                bounds[1] = max(bounds[1], ordinal)
            if content_hash not in known_versions:
                known_versions[content_hash] = canonical_length
                versions_per_index_id[index_id] += 1
                snapshot_new_versions += 1
        added = len(current.keys() - previous.keys())
        removed = len(previous.keys() - current.keys())
        common = current.keys() & previous.keys()
        changed = sum(current[key] != previous[key] for key in common)
        unchanged = len(common) - changed
        semantic = _semantic_digest(current)
        source_file = sha256_file(path)
        signature = digest(canonical_bytes(sorted(keyset)))
        schema_signatures[signature] += 1
        history = schema_history.setdefault(signature, {"fields": sorted(keyset), "first_snapshot": path.name, "last_snapshot": path.name})
        history["last_snapshot"] = path.name
        first_semantic.setdefault(semantic, path.name)
        first_source_file.setdefault(source_file, path.name)
        snapshots.append((path.name, path.stat().st_size, rows, len(current), raw_h.hexdigest(), semantic,
                          added, removed, changed, unchanged, signature, source_file, snapshot_new_versions))
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
    byte_identical_nonfirst = sum(1 for row in snapshot_rows if first_source_file[row[11]] != row[0])
    field_report = {}
    for key in sorted(field_observations):
        field_report[key] = {
            "observations": field_observations[key],
            "non_null": field_non_null[key],
            "null_or_absent_observations": total_rows - field_non_null[key],
            "non_null_ratio": round(field_non_null[key] / total_rows, 8) if total_rows else 0,
            "types": _json_dump_counter(field_types[key]),
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
        "integrity": {"malformed_row_count": len(malformed_rows), "duplicate_index_id_row_count": len(duplicate_ids), "current_contract_invalid_parseable_rows": len(current_invalid_rows), "examples": (malformed_rows + duplicate_ids + current_invalid_rows)[:20]},
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
            {"filename": r[0], "source_bytes": r[1], "rows": r[2], "index_ids": r[3], "raw_row_stream_sha256": r[4], "semantic_sha256": r[5], "added": r[6], "removed": r[7], "changed": r[8], "unchanged": r[9], "schema_signature": r[10], "source_file_sha256": r[11], "new_logical_versions": r[12], "same_semantic_state_as": first_semantic[r[5]], "same_source_bytes_as": first_source_file[r[11]]}
            for r in snapshot_rows
        ],
        "snapshot_redundancy": {"semantically_identical_nonfirst_snapshots": exact_duplicate_files, "byte_identical_nonfirst_snapshots": byte_identical_nonfirst, "snapshots_adding_zero_new_logical_versions": sum(1 for r in snapshot_rows if r[12] == 0), "distinct_semantic_states": len(first_semantic), "distinct_schema_signatures": len(schema_signatures)},
        "events": {"adds": sum(r[6] for r in snapshot_rows), "removes": sum(r[7] for r in snapshot_rows), "changes": sum(r[8] for r in snapshot_rows), "consecutive_mutation_rate": _percentiles([(r[6] + r[7] + r[8]) / max(1, (snapshot_rows[i - 1][3] if i else 0), r[3]) for i, r in enumerate(snapshot_rows) if i])},
        "fields": field_report,
        "historical_only_fields": sorted(set(field_report) - current_fields),
        "current_contract_fields_never_seen": sorted(current_fields - set(field_report)),
        "schema_history": [{"schema_signature": signature, "snapshot_count": schema_signatures[signature], **schema_history[signature]} for signature in sorted(schema_history)],
        "migration_status_counts": dict(sorted(migration_status.items())),
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
