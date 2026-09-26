#!/usr/bin/env python3
"""Copy-verify-retire legacy news_ref snapshots; never bypass a failed gate.

This command deliberately has no ``--force``.  It removes local originals only
after a separately built compact archive has a passing verification report and
every copied destination file agrees with the census SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--bus-dir",type=Path,required=True)
    p.add_argument("--archive-root",type=Path,required=True,help="validated compact archive")
    p.add_argument("--destination-mount",type=Path,required=True,help="mounted durable filesystem, not a subdirectory")
    p.add_argument("--archive-name",required=True)
    p.add_argument("--retire-local",action="store_true",help="perform final local removal after copy verification")
    args=p.parse_args(); compact=args.archive_root.resolve(); mount=args.destination_mount
    verify=json.loads((compact/"verification.json").read_text())
    if not verify.get("passed"): raise SystemExit("REFUSING: compact-archive verification did not pass")
    if not mount.is_dir() or not os.path.ismount(mount): raise SystemExit(f"REFUSING: destination is not a mounted filesystem: {mount}")
    if not os.access(mount,os.W_OK): raise SystemExit(f"REFUSING: destination is not writable: {mount}")
    audit=json.loads((compact/"source_census.json").read_text()); rows=audit["snapshots"]
    dest=mount/"MATIAS_ESTATE"/"DURABLE_ARCHIVE"/"project-data"/"media_monitor"/args.archive_name
    if dest.exists(): raise SystemExit(f"REFUSING: destination already exists: {dest}")
    snapshots=dest/"source_snapshots"; snapshots.mkdir(parents=True)
    # shutil.copy2 uses a distinct destination filesystem and preserves source
    # metadata.  Each copy is immediately SHA-256 checked; no cross-FS rename.
    copied_bytes=0
    for n,row in enumerate(rows,1):
        source=args.bus_dir/row["filename"]; target=snapshots/row["filename"]
        if not source.is_file() or source.stat().st_size != row["source_bytes"] or sha(source)!=row["source_file_sha256"]:
            raise SystemExit(f"REFUSING: source changed before copy: {source}")
        shutil.copy2(source,target)
        if target.stat().st_size != row["source_bytes"] or sha(target)!=row["source_file_sha256"]:
            raise SystemExit(f"FAILED destination checksum: {target}")
        copied_bytes += target.stat().st_size
        if n%100==0: print(f"[news-ref-retire] copied/verified {n}/{len(rows)}",flush=True)
    reports=dest/"reports"; reports.mkdir()
    for name in ("source_census.json","manifest.json","verification.json"):
        shutil.copy2(compact/name,reports/name)
    (dest/"README.md").write_text(f"""# Retired `news_ref` full snapshots

Migration date: 2026-09-26

This safety copy contains {len(rows)} historical source snapshots ({copied_bytes} bytes),
retired after the compact archive passed its hash and replay verification.

The compact replacement is `{compact}`.  `reports/` contains the source census,
compact manifest, and verification report.  Malformed rows are retained by the
compact archive quarantine and are accounted for by the census.

This Elements copy may be considered for deletion only in a separate reviewed
decision after the compact archive remains independently available, its manifests
and replay verification are revalidated, and no retention/legal/consumer need
for original byte-for-byte snapshots remains.
""")
    # Recheck aggregate count/bytes, then hashes a second time independently of
    # the copying loop, before removal becomes possible.
    found=list(snapshots.iterdir())
    if len(found)!=len(rows) or sum(x.stat().st_size for x in found)!=copied_bytes: raise SystemExit("FAILED destination count/byte verification")
    for row in rows:
        if sha(snapshots/row["filename"]) != row["source_file_sha256"]: raise SystemExit("FAILED destination final hash verification")
    result={"destination":str(dest),"files":len(rows),"bytes":copied_bytes,"sha256_verified":True,"local_retired":False}
    if args.retire_local:
        # Check compact artifact still present and passing immediately before the
        # irreversible local phase, then unlink only census-declared history.
        if not (compact/"verification.json").is_file() or not json.loads((compact/"verification.json").read_text()).get("passed"):
            raise SystemExit("REFUSING: compact archive no longer validates")
        for row in rows: (args.bus_dir/row["filename"]).unlink()
        result["local_retired"]=True
    print(json.dumps(result,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
