#!/usr/bin/env python3
"""Build and verify a restartable, lossless semantic archive of legacy news_ref.

The input census is an immutable contract: every legacy file must have its
recorded size and SHA-256 before it can enter the archive.  The builder stages
state in SQLite (outside the source tree), then emits independently hashed
Parquet/Zstd tables.  It never deletes or changes a source snapshot.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import zstandard as zstd

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None


def canonical(value: Any) -> bytes:
    if orjson:
        return orjson.dumps(value, option=orjson.OPT_SORT_KEYS)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def semantic(state: dict[str, str]) -> str:
    h = hashlib.sha256()
    for key in sorted(state):
        h.update(key.encode()); h.update(b"\0"); h.update(state[key].encode()); h.update(b"\n")
    return h.hexdigest()


def source_rows(path: Path):
    with path.open("rb") as f:
        for line_no, raw in enumerate(f, 1):
            raw = raw.rstrip(b"\r\n")
            if raw.strip():
                yield line_no, raw


def open_db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.executescript("""
      PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
      CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS current_state (index_id TEXT PRIMARY KEY, content_sha256 TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS source_files (ordinal INTEGER PRIMARY KEY, filename TEXT UNIQUE NOT NULL, source_sha256 TEXT NOT NULL, source_bytes INTEGER NOT NULL, semantic_sha256 TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS versions (content_sha256 TEXT PRIMARY KEY, index_id TEXT NOT NULL, canonical_payload BLOB, migration_status TEXT NOT NULL, first_ordinal INTEGER NOT NULL);
      CREATE TABLE IF NOT EXISTS events (ordinal INTEGER NOT NULL, sequence INTEGER NOT NULL, operation TEXT NOT NULL, index_id TEXT NOT NULL, content_sha256 TEXT, PRIMARY KEY(ordinal, sequence));
      CREATE TABLE IF NOT EXISTS quarantined (ordinal INTEGER NOT NULL, filename TEXT NOT NULL, line_number INTEGER NOT NULL, synthetic_index_id TEXT NOT NULL, raw_sha256 TEXT NOT NULL, raw_b64 TEXT NOT NULL, PRIMARY KEY(ordinal, line_number));
    """)
    return db


def meta(db: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def set_meta(db: sqlite3.Connection, key: str, value: str) -> None:
    db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, value))


def write_parquet(db: sqlite3.Connection, root: Path) -> list[Path]:
    out = root / "parquet"; out.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    specs = [
        ("record_versions.parquet", "SELECT content_sha256,index_id,canonical_payload,migration_status,first_ordinal FROM versions ORDER BY content_sha256", ["content_sha256","index_id","canonical_payload","migration_status","first_ordinal"]),
        ("snapshot_events.parquet", "SELECT ordinal,sequence,operation,index_id,content_sha256 FROM events ORDER BY ordinal,sequence", ["ordinal","sequence","operation","index_id","content_sha256"]),
        ("source_files.parquet", "SELECT ordinal,filename,source_sha256,source_bytes,semantic_sha256 FROM source_files ORDER BY ordinal", ["ordinal","filename","source_sha256","source_bytes","semantic_sha256"]),
    ]
    types = {"content_sha256": pa.string(), "index_id": pa.string(), "canonical_payload": pa.binary(), "migration_status": pa.string(), "ordinal": pa.int64(), "sequence": pa.int64(), "operation": pa.string(), "filename": pa.string(), "source_sha256": pa.string(), "source_bytes": pa.int64(), "semantic_sha256": pa.string(), "first_ordinal": pa.int64()}
    for name, query, names in specs:
        target = out / name
        # PyArrow treats unknown extensions inconsistently across writers; a
        # temporary name which still ends in .parquet gives rename its exact
        # promised source path.
        tmp = target.with_name(target.stem + ".part.parquet")
        if target.exists(): target.unlink()
        writer = None; cur = db.execute(query)
        while rows := cur.fetchmany(10000):
            cols = list(zip(*rows))
            table = pa.table({name: pa.array(value, type=types[name]) for name, value in zip(names, cols)})
            if writer is None: writer = pq.ParquetWriter(tmp, table.schema, compression="zstd", compression_level=9)
            writer.write_table(table)
        if writer is None:
            raise RuntimeError(f"empty required table: {name}")
        writer.close(); os.replace(tmp, target); files.append(target)
    qtarget = root / "quarantine" / "malformed.jsonl.zst"; qtarget.parent.mkdir(exist_ok=True)
    with qtarget.open("wb") as raw, zstd.ZstdCompressor(level=9).stream_writer(raw) as z:
        for row in db.execute("SELECT ordinal,filename,line_number,synthetic_index_id,raw_sha256,raw_b64 FROM quarantined ORDER BY ordinal,line_number"):
            z.write((json.dumps(dict(zip(["ordinal","filename","line_number","synthetic_index_id","raw_sha256","raw_b64"], row)), separators=(",", ":")) + "\n").encode())
    files.append(qtarget)
    return files


def checkpoint(db: sqlite3.Connection, root: Path, ordinal: int, state: dict[str, str]) -> Path:
    target = root / "checkpoints" / f"{ordinal:05d}.parquet"; target.parent.mkdir(exist_ok=True)
    tmp = target.with_suffix(".tmp")
    pq.write_table(pa.table({"index_id": list(sorted(state)), "content_sha256": [state[k] for k in sorted(state)]}), tmp, compression="zstd", compression_level=9)
    os.replace(tmp, target)
    return target


def build(args: argparse.Namespace) -> int:
    audit_path, root = args.audit.resolve(), args.archive_root.resolve()
    audit = json.loads(audit_path.read_text())
    if audit.get("schema_name") != "news_ref_historical_audit.v1": raise SystemExit("unsupported audit")
    snapshots = audit["snapshots"]
    if len(snapshots) != audit["input"]["snapshot_count"]: raise SystemExit("audit snapshot count mismatch")
    root.mkdir(parents=True, exist_ok=True)
    db = open_db(root / "build.sqlite")
    audit_hash = sha_file(audit_path)
    prior = meta(db, "audit_sha256")
    if prior and prior != audit_hash: raise SystemExit("archive root belongs to a different audit")
    set_meta(db, "audit_sha256", audit_hash); set_meta(db, "format", "news_ref_compact_archive.v1")
    current = dict(db.execute("SELECT index_id,content_sha256 FROM current_state"))
    # A compact set avoids issuing a SQLite INSERT OR IGNORE for each of the
    # ~50M historical row observations; only novel logical versions are rows
    # in the immutable version store.
    known_versions = {row[0] for row in db.execute("SELECT content_sha256 FROM versions")}
    done = int(meta(db, "next_ordinal", "0") or 0)
    if done and not current: raise SystemExit("restart state missing")
    start = time.monotonic()
    for ordinal in range(done, len(snapshots)):
        entry = snapshots[ordinal]; path = args.bus_dir / entry["filename"]
        if not path.is_file() or path.stat().st_size != entry["source_bytes"]: raise SystemExit(f"source identity changed: {path}")
        source_hash = sha_file(path)
        if source_hash != entry["source_file_sha256"]: raise SystemExit(f"source SHA-256 changed: {path}")
        new: dict[str, str] = {}; versions=[]; quarantined=[]
        for line_no, raw in source_rows(path):
            try:
                obj = orjson.loads(raw) if orjson else json.loads(raw)
                if not isinstance(obj, dict): raise ValueError("row is not an object")
                index = obj.get("index_id")
                if not isinstance(index, str) or not index: raise ValueError("missing/non-string index_id")
                payload = canonical(obj); digest = sha_bytes(payload)
                new[index] = digest
                if digest not in known_versions:
                    known_versions.add(digest); versions.append((digest,index,payload,"current-valid",ordinal))
            except Exception:
                digest = sha_bytes(raw); index = f"__malformed__:{entry['filename']}:{line_no}"
                new[index] = digest
                if digest not in known_versions:
                    known_versions.add(digest); versions.append((digest,index,raw,"malformed-quarantined",ordinal))
                quarantined.append((ordinal,entry["filename"],line_no,index,digest,base64.b64encode(raw).decode()))
        if semantic(new) != entry["semantic_sha256"]: raise SystemExit(f"semantic mismatch while building {path}")
        removed = sorted(set(current) - set(new)); changed = sorted(k for k in set(current)&set(new) if current[k] != new[k]); added = sorted(set(new)-set(current))
        events = [(ordinal,n,"remove",k,None) for n,k in enumerate(removed)]
        seq=len(events); events += [(ordinal,seq+i,"change",k,new[k]) for i,k in enumerate(changed)]; seq=len(events)
        events += [(ordinal,seq+i,"add",k,new[k]) for i,k in enumerate(added)]
        with db:
            db.executemany("INSERT OR IGNORE INTO versions VALUES (?,?,?,?,?)", versions)
            db.executemany("INSERT INTO quarantined VALUES (?,?,?,?,?,?)", quarantined)
            db.executemany("INSERT INTO events VALUES (?,?,?,?,?)", events)
            db.execute("DELETE FROM current_state")
            db.executemany("INSERT INTO current_state VALUES (?,?)", new.items())
            db.execute("INSERT INTO source_files VALUES (?,?,?,?,?)", (ordinal,entry["filename"],source_hash,entry["source_bytes"],entry["semantic_sha256"]))
            set_meta(db,"next_ordinal",str(ordinal+1))
        current = new
        if ordinal % args.checkpoint_every == 0 or ordinal == len(snapshots)-1: checkpoint(db, root, ordinal, current)
        if (ordinal+1) % 25 == 0: print(f"[news-ref-archive] {ordinal+1}/{len(snapshots)} elapsed={time.monotonic()-start:.0f}s", flush=True)
    outputs = write_parquet(db, root)
    outputs += sorted((root / "checkpoints").glob("*.parquet"))
    manifest = {"schema_name":"news_ref_compact_archive.v1","audit_sha256":audit_hash,"source":{"file_count":len(snapshots),"bytes":audit["input"]["source_bytes"],"rows":audit["input"]["rows"],"first":snapshots[0]["filename"],"last":snapshots[-1]["filename"]},"format":{"record_versions":"Parquet/Zstd canonical JSON payloads","events":"Parquet/Zstd add/change/remove event log","checkpoints_every":args.checkpoint_every,"quarantine":"Zstd JSONL raw bytes base64"},"counts":{"versions":db.execute("SELECT count(*) FROM versions").fetchone()[0],"events":db.execute("SELECT count(*) FROM events").fetchone()[0],"quarantined":db.execute("SELECT count(*) FROM quarantined").fetchone()[0]},"files":[{"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha_file(p)} for p in sorted(outputs)]}
    (root / "manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    shutil.copy2(audit_path, root / "source_census.json")
    print(json.dumps({"archive_root":str(root),"manifest":str(root/'manifest.json'),"counts":manifest["counts"]},indent=2))
    return 0


def verify(args: argparse.Namespace) -> int:
    root=args.archive_root.resolve(); audit=json.loads((root/"source_census.json").read_text()); manifest=json.loads((root/"manifest.json").read_text())
    problems=[]
    consumer = None
    if args.consumer_audit and args.consumer_audit.is_file():
        consumer=json.loads(args.consumer_audit.read_text())
        if not consumer.get("passed"): problems.append("consumer audit did not pass")
    else:
        problems.append("missing consumer audit")
    for row in manifest["files"]:
        p=root/row["path"]
        if not p.is_file() or p.stat().st_size != row["bytes"] or sha_file(p) != row["sha256"]: problems.append("archive file hash: "+row["path"])
    # Reconstruct entirely from the final archived event table and compare every source-audited state hash.
    event=pq.read_table(root/"parquet/snapshot_events.parquet").to_pylist(); state={}; expected={i:s["semantic_sha256"] for i,s in enumerate(audit["snapshots"])}; replay=[]; at=0
    for ordinal in range(len(audit["snapshots"])):
        while at < len(event) and event[at]["ordinal"] == ordinal:
            e=event[at]
            if e["operation"] == "remove": state.pop(e["index_id"],None)
            else: state[e["index_id"]]=e["content_sha256"]
            at += 1
        got=semantic(state)
        if got != expected[ordinal]: problems.append(f"replay semantic mismatch ordinal={ordinal}")
        if ordinal in {0,len(expected)-1,len(expected)//4,len(expected)//2,(3*len(expected))//4}: replay.append({"ordinal":ordinal,"filename":audit["snapshots"][ordinal]["filename"],"semantic_sha256":got})
    # Verify deterministic checkpoint boundaries against an event replay, not merely their parquet checksums.
    for p in sorted((root/"checkpoints").glob("*.parquet")):
        ordinal=int(p.stem); table=pq.read_table(p).to_pydict(); cp=dict(zip(table["index_id"],table["content_sha256"]))
        # Rebuild only this state from events to keep checkpoint validation independent.
        x={}
        for e in event:
            if e["ordinal"]>ordinal: break
            if e["operation"]=="remove": x.pop(e["index_id"],None)
            else: x[e["index_id"]]=e["content_sha256"]
        if x != cp: problems.append(f"checkpoint mismatch ordinal={ordinal}")
    # Source identity is rechecked here; this is intentionally expensive and is a hard gate.
    source_problems=[]
    for s in audit["snapshots"]:
        p=args.bus_dir/s["filename"]
        if not p.is_file() or p.stat().st_size != s["source_bytes"] or sha_file(p) != s["source_file_sha256"]: source_problems.append(s["filename"])
    problems += ["source identity: "+x for x in source_problems]
    current_hash=sha_file(args.bus_dir/"news_ref_current.jsonl") if (args.bus_dir/"news_ref_current.jsonl").is_file() else None
    report={"schema_name":"news_ref_compact_archive_verification.v1","passed":not problems,"checked_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_census":{"files":len(audit["snapshots"]),"bytes":audit["input"]["source_bytes"],"malformed_quarantined":audit["integrity"]["malformed_row_count"]},"consumer_audit":consumer,"archive_manifest_sha256":sha_file(root/"manifest.json"),"replay":{"all_snapshot_states_checked":len(audit["snapshots"]),"deterministic_points":replay,"checkpoint_files_checked":len(list((root/"checkpoints").glob("*.parquet")))},"current_state":{"current_file_sha256":current_hash,"last_historical_semantic_sha256":audit["snapshots"][-1]["semantic_sha256"],"status":"intentional temporal boundary: current state is retained hot and postdates the final legacy snapshot; it is not an archival input"},"problems":problems}
    (root/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2)); return 0 if not problems else 2


def main() -> int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="action",required=True)
    for name in ("build","verify"):
        x=sub.add_parser(name); x.add_argument("--bus-dir",type=Path,required=True); x.add_argument("--archive-root",type=Path,required=True)
        if name=="verify": x.add_argument("--consumer-audit",type=Path,required=True)
        if name=="build": x.add_argument("--audit",type=Path,required=True); x.add_argument("--checkpoint-every",type=int,default=100)
    args=p.parse_args(); return build(args) if args.action=="build" else verify(args)

if __name__ == "__main__": raise SystemExit(main())
