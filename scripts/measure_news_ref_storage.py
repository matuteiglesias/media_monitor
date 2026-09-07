#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path


def _count_rows(payload: bytes) -> int:
    return sum(1 for line in payload.splitlines() if line.strip())


def _choose_representative(bus_dir: Path) -> Path | None:
    current = bus_dir / "news_ref_current.jsonl"
    if current.exists() and current.is_file():
        return current
    legacy = sorted(
        p for p in bus_dir.glob("news_ref_*.jsonl") if p.name != "news_ref_current.jsonl"
    )
    return legacy[-1] if legacy else None


def measure(bus_dir: Path) -> dict:
    representative = _choose_representative(bus_dir)
    legacy = sorted(
        p for p in bus_dir.glob("news_ref_*.jsonl") if p.name != "news_ref_current.jsonl"
    )
    legacy_bytes = sum(p.stat().st_size for p in legacy)

    result = {
        "schema_name": "news_ref_storage_measurement.v1",
        "bus_dir": str(bus_dir),
        "legacy_payload_count": len(legacy),
        "legacy_payload_bytes": legacy_bytes,
        "representative": None,
    }
    if representative is None:
        return result

    t0 = time.perf_counter()
    payload = representative.read_bytes()
    read_seconds = time.perf_counter() - t0

    t1 = time.perf_counter()
    compressed = gzip.compress(payload, compresslevel=6, mtime=0)
    gzip_seconds = time.perf_counter() - t1

    plain_bytes = len(payload)
    gzip_bytes = len(compressed)
    result["representative"] = {
        "path": str(representative),
        "rows": _count_rows(payload),
        "plain_jsonl_bytes": plain_bytes,
        "gzip_level": 6,
        "gzip_bytes": gzip_bytes,
        "gzip_ratio": (gzip_bytes / plain_bytes) if plain_bytes else None,
        "read_seconds": round(read_seconds, 6),
        "gzip_seconds": round(gzip_seconds, 6),
    }
    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Read-only measurement of news_ref storage and JSONL gzip ratio")
    p.add_argument("--storage-dir", default="storage")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    bus_dir = Path(args.storage_dir) / "buses" / "news_ref" / "v1"
    print(json.dumps(measure(bus_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
