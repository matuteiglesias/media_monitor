#!/usr/bin/env python3
"""Normalize externally monitored signals into Media Monitor access-index fields.

Input is JSONL where every row satisfies external_monitored_signal.v1. Invalid
rows and conflicting repeated identities are quarantined. The adapter never
mutates canonical runtime storage unless the caller explicitly chooses output
paths there; normal adoption use should write into an isolated workspace first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "schemas" / "external_monitored_signal.v1.json"
DIGEST_RE = re.compile(r"^\d{8}T\d{2}$")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        for row in rows
    ).encode("utf-8")


def _identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row["provider_id"]), str(row["source_id"]), str(row["external_id"]))


def _content_fingerprint(row: dict[str, Any]) -> str:
    semantic = {
        "provider_id": row["provider_id"],
        "source_id": row["source_id"],
        "external_id": row["external_id"],
        "source_name": row["source_name"],
        "title": row["title"],
        "topic": row["topic"],
        "published_at": row["published_at"],
        "link": row["link"],
    }
    encoded = json.dumps(semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256_bytes(encoded)


def _index_id(identity: tuple[str, str, str]) -> str:
    # 10 lowercase hex characters remain compatible with current 8-10
    # alphanumeric index-id assumptions while avoiding provider-native IDs.
    return hashlib.sha256("\x1f".join(identity).encode("utf-8")).hexdigest()[:10]


def _normalized(row: dict[str, Any], digest_at: str, duplicate_observations: int) -> dict[str, Any]:
    identity = _identity(row)
    return {
        "index_id": _index_id(identity),
        "digest_at": digest_at,
        "title": row["title"],
        "topic": row["topic"],
        "published_at": row["published_at"],
        "link": row["link"],
        "source": row["source_name"],
        "external_provenance": {
            "schema_name": row["schema_name"],
            "provider_id": row["provider_id"],
            "source_id": row["source_id"],
            "external_id": row["external_id"],
            "observed_at": row["observed_at"],
            "provenance": row["provenance"],
            "content_sha256": _content_fingerprint(row),
            "duplicate_observations": duplicate_observations,
        },
    }


def import_signals(
    input_path: Path,
    *,
    digest_at: str,
    output_path: Path,
    quarantine_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    if not DIGEST_RE.fullmatch(digest_at):
        raise ValueError("digest_at must match YYYYMMDDTHH")

    schema = _read_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    raw_bytes = input_path.read_bytes()

    valid_by_identity: dict[tuple[str, str, str], list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    quarantine: list[dict[str, Any]] = []
    input_rows = 0

    for line_number, line in enumerate(raw_bytes.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        input_rows += 1
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            quarantine.append(
                {
                    "line_number": line_number,
                    "reason": "invalid_json",
                    "detail": str(exc),
                    "raw": line,
                }
            )
            continue
        if not isinstance(value, dict):
            quarantine.append(
                {
                    "line_number": line_number,
                    "reason": "not_object",
                    "detail": "JSONL row must be an object",
                    "row": value,
                }
            )
            continue
        errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
        if errors:
            quarantine.append(
                {
                    "line_number": line_number,
                    "reason": "schema_invalid",
                    "detail": [
                        {
                            "path": ".".join(str(part) for part in error.absolute_path) or "$",
                            "message": error.message,
                        }
                        for error in errors
                    ],
                    "row": value,
                }
            )
            continue
        valid_by_identity[_identity(value)].append((line_number, value))

    normalized: list[dict[str, Any]] = []
    duplicate_observations = 0
    conflict_identities = 0

    for identity in sorted(valid_by_identity):
        occurrences = valid_by_identity[identity]
        fingerprints = {_content_fingerprint(row) for _, row in occurrences}
        if len(fingerprints) > 1:
            conflict_identities += 1
            for line_number, row in occurrences:
                quarantine.append(
                    {
                        "line_number": line_number,
                        "reason": "identity_conflict",
                        "detail": "same provider/source/external identity carried different semantic content",
                        "identity": {
                            "provider_id": identity[0],
                            "source_id": identity[1],
                            "external_id": identity[2],
                        },
                        "row": row,
                    }
                )
            continue
        duplicate_observations += max(0, len(occurrences) - 1)
        first = min(occurrences, key=lambda pair: pair[0])[1]
        normalized.append(_normalized(first, digest_at, len(occurrences) - 1))

    normalized.sort(key=lambda row: (str(row["published_at"]), str(row["index_id"])), reverse=True)
    quarantine.sort(key=lambda row: int(row.get("line_number") or 0))

    output_bytes = _jsonl_bytes(normalized)
    quarantine_bytes = _jsonl_bytes(quarantine)
    _atomic_write(output_path, output_bytes)
    _atomic_write(quarantine_path, quarantine_bytes)

    manifest = {
        "schema": "external_signal_import_manifest.v1",
        "status": "clean" if not quarantine else "quarantined",
        "contract": "external_monitored_signal.v1",
        "digest_at": digest_at,
        "input_path": str(input_path),
        "input_sha256": _sha256_bytes(raw_bytes),
        "input_rows": input_rows,
        "accepted_rows": len(normalized),
        "quarantined_rows": len(quarantine),
        "duplicate_observations": duplicate_observations,
        "conflict_identities": conflict_identities,
        "output_path": str(output_path),
        "output_sha256": _sha256_bytes(output_bytes),
        "quarantine_path": str(quarantine_path),
        "quarantine_sha256": _sha256_bytes(quarantine_bytes),
        "identity_rule": "sha256(provider_id\\x1fsource_id\\x1fexternal_id)[:10]",
        "downstream_fields": [
            "index_id",
            "digest_at",
            "title",
            "topic",
            "published_at",
            "link",
            "source",
            "external_provenance",
        ],
        "provenance_effect": "provider identity and source record provenance remain attached to each accepted row",
    }
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    _atomic_write(manifest_path, manifest_bytes)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSONL of external_monitored_signal.v1 rows")
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()

    try:
        manifest = import_signals(
            args.input,
            digest_at=args.digest_at,
            output_path=args.output,
            quarantine_path=args.quarantine,
            manifest_path=args.manifest,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")

    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    if args.require_clean and manifest["quarantined_rows"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
