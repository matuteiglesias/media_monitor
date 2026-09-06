from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def serialize_jsonl(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(
        (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        finally:
            raise


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> bytes:
    payload = serialize_jsonl(rows)
    atomic_write_bytes(path, payload)
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write_bytes(path, data)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def identity_change_counts(
    previous_rows: list[dict[str, Any]],
    current_rows: list[dict[str, Any]],
    identity_field: str,
) -> tuple[int, int, int]:
    previous = {
        str(row.get(identity_field) or ""): row
        for row in previous_rows
        if str(row.get(identity_field) or "")
    }
    current = {
        str(row.get(identity_field) or ""): row
        for row in current_rows
        if str(row.get(identity_field) or "")
    }
    previous_keys = set(previous)
    current_keys = set(current)
    added = len(current_keys - previous_keys)
    removed = len(previous_keys - current_keys)
    changed = sum(previous[key] != current[key] for key in previous_keys & current_keys)
    return added, changed, removed
