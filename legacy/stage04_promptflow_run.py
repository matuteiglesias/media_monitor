# legacy/04_promptflow_run.py
# Execute Promptflow for the fixed hour. Input: data/pf_in/pfin_<DIGEST_AT>.jsonl
# Output: data/pf_out/pfout_<DIGEST_AT>.jsonl (overwrite idempotent)
from __future__ import annotations

import os
import sys
import glob
import json
import subprocess
from pathlib import Path
from typing import Iterable, List, Dict

import pandas as pd

from backend import ids, db
from backend import io as bio

# ---------- Paths / Config ----------
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PF_IN_DIR = DATA_DIR / "pf_in"
PF_OUT_DIR = DATA_DIR / "pf_out"
QUAR_DIR = DATA_DIR / "quarantine"

# Path where PromptFlow drops run artifacts; adjust if yours differs
PF_RUNS_DIR = Path.home() / ".promptflow" / ".runs"
# Your flow root; override with env PF_FLOW_DIR if needed
PF_FLOW_DIR = Path(os.getenv("PF_FLOW_DIR", Path.cwd() / "flow"))

# ---------- Env helpers ----------
def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip() not in ("0", "false", "False", "")

def _env_float(name: str, default: float | None) -> float | None:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default

def ensure_dirs():
    for p in (PF_IN_DIR, PF_OUT_DIR, QUAR_DIR):
        p.mkdir(parents=True, exist_ok=True)

def quarantine_path(stage: str, run_id: str) -> Path:
    return QUAR_DIR / f"{stage}_{run_id}.jsonl"

def atomic_overwrite_jsonl(path: Path, records: Iterable[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        tmp.unlink()
    for rec in records:
        bio.append_jsonl(tmp, rec)
    if path.exists():
        path.unlink()
    tmp.rename(path)

# ---------- PF helpers ----------
def _run_promptflow(flow_dir: Path, data_file: Path) -> int:
    """
    Launch PromptFlow run via CLI, streaming output. Returns subprocess return code.
    """
    cmd = [
        sys.executable, "-m", "promptflow._cli.pf", "run", "create",
        "--flow", str(flow_dir),
        "--data", str(data_file),
    ]
    print("\n[04_promptflow] Running PromptFlow:\n", " ".join(cmd), "\n")
    try:
        return subprocess.run(cmd, check=False).returncode
    except KeyboardInterrupt:
        print("[04_promptflow] Interrupted by user.")
        return 130
    except Exception as e:
        print(f"[04_promptflow] Error launching PromptFlow: {e}")
        return 1

def _latest_pf_output_jsonl(runs_dir: Path) -> Path | None:
    """
    Locate the most recent PF run output.jsonl under ~/.promptflow/.runs/**/flow_outputs/output.jsonl
    """
    candidates = list(runs_dir.glob("flow_variant_0_*/flow_outputs/output.jsonl"))
    if not candidates:
        return None
    latest = max(candidates, key=os.path.getmtime)
    return latest

# ---------- Core ----------
def run() -> int:
    ensure_dirs()

    # Env knobs
    digest_at_env = os.getenv("DIGEST_AT")  # YYYYMMDDTHH
    dry_run = _env_bool("DRY_RUN", False)
    null_sink = _env_bool("NULL_SINK", False)
    run_id = os.getenv("RUN_ID")
    limit = _env_float("LIMIT", None)
    sample = _env_float("SAMPLE", None)

    # Derive hour
    if digest_at_env:
        digest_id, _ = ids.digest_id_hour(digest_at_env)
    else:
        digest_id, _ = ids.digest_id_hour(pd.Timestamp.utcnow().strftime("%Y%m%dT%H"))
    stage_name = "04_promptflow_run"
    run_id = run_id or f"{stage_name}:{digest_id}"

    # Run start
    try:
        db.start_run(run_id, stage_name, {"digest_id": digest_id})
    except Exception:
        pass

    # Input path
    # pfin_path = PF_IN_DIR / f"pfin_{digest_id}.jsonl"
    pfin_path = DATA_DIR / "digest_jsonls" / f"{digest_id}.jsonl"
    if not pfin_path.exists():
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=0, meta={"digest_id": digest_id, "note": "no pfin file"})
        except Exception:
            pass
        print(f"[{stage_name}] digest_id={digest_id} no input at {pfin_path}")
        return 0

    # Load PF input as list of dicts (streaming)
    inputs: List[dict] = []
    try:
        with pfin_path.open("r", encoding="utf-8", errors="strict") as f:
            for ln, line in enumerate(f, start=1):
                s = line.strip()
                if not s:
                    continue
                try:
                    obj = json.loads(s)
                    inputs.append(obj)
                except json.JSONDecodeError as e:
                    bio.append_jsonl(
                        quarantine_path("V04", run_id),
                        {
                            "reason": "bad_jsonl_input",
                            "file": str(pfin_path),
                            "line_no": ln,
                            "col": e.colno,
                            "msg": e.msg,
                            "line_prefix": s[:300]
                        },
                    )
    except Exception as e:
        bio.append_jsonl(quarantine_path("V04", run_id), {
            "reason": "read_error",
            "file": str(pfin_path),
            "error": str(e)
        })
        print(f"[{stage_name}] failed reading {pfin_path}: {e}")
        return 1

    if not inputs:
        # Helpful debug print so you can see path & size
        try:
            size = pfin_path.stat().st_size
        except Exception:
            size = -1
        print(f"[{stage_name}] digest_id={digest_id} empty input (path={pfin_path}, bytes={size})")
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=0,
                        meta={"digest_id": digest_id, "note": "empty input", "path": str(pfin_path), "bytes": size})
        except Exception:
            pass
        return 0

    # Optional sample/limit for speed
    df_in = pd.DataFrame(inputs)
    sample = _env_float("SAMPLE", None)
    limit = _env_float("LIMIT", None)
    if sample is not None and 0 < sample < 1:
        df_in = df_in.sample(frac=float(sample), random_state=17).reset_index(drop=True)
    if limit is not None:
        df_in = df_in.head(int(limit))

    # Write a temp filtered input for PF
    tmp_in = pfin_path.parent / f".tmp_pfin_{digest_id}.jsonl"
    atomic_overwrite_jsonl(tmp_in, df_in.to_dict(orient="records"))

    # ---- DRY_RUN mode: stub output, no PF call ----
    out_dir = (DATA_DIR / "_tmp" / "null" / "pf_out") if null_sink else PF_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"pfout_{digest_id}.jsonl"

    if dry_run:
        # Echo inputs with placeholder PF fields
        stubbed = []
        for rec in df_in.to_dict(orient="records"):
            stub = dict(rec)
            stub.update({
                "cluster_id": f"stub::{rec.get('digest_file','')}::{rec.get('article_id','')}",
                "topic_suggestion": rec.get("title", "")[:80],
                "headline_suggestion": rec.get("title", "")[:80],
                "pf_stub": True,
            })
            stubbed.append(stub)
        atomic_overwrite_jsonl(out_path, stubbed)
        try:
            db.finish_run(run_id, stage=stage_name, ok=len(stubbed), fail=0, meta={"digest_id": digest_id, "mode": "DRY_RUN", "out": str(out_path)})
        except Exception:
            pass
        print(f"[{stage_name}] DRY_RUN -> {out_path} rows={len(stubbed)}")
        return 0

    # ---- Real PF run ----
    rc = _run_promptflow(PF_FLOW_DIR, tmp_in)
    if rc != 0:
        bio.append_jsonl(quarantine_path("V04", run_id), {"reason": "pf_cli_failed", "returncode": rc})
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=len(df_in), meta={"digest_id": digest_id, "pf_rc": rc})
        except Exception:
            pass
        print(f"[{stage_name}] PF CLI failed rc={rc}")
        return rc

    latest = _latest_pf_output_jsonl(PF_RUNS_DIR)
    if latest is None or not latest.exists():
        bio.append_jsonl(quarantine_path("V04", run_id), {"reason": "pf_missing_output"})
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=len(df_in), meta={"digest_id": digest_id, "note": "no pf output"})
        except Exception:
            pass
        print(f"[{stage_name}] PF run produced no output.jsonl")
        return 1

    # Load PF output
    try:
        df_pf = pd.read_json(latest, lines=True)
    except Exception as e:
        bio.append_jsonl(quarantine_path("V04", run_id), {"reason": "pf_output_parse_error", "file": str(latest), "error": str(e)})
        print(f"[{stage_name}] failed parsing PF output: {e}")
        return 1

    # ---- Guardrails & carry-through enrichment ----
    in_n = len(df_in)
    out_n = len(df_pf)

    # Ensure carry-through keys are present; if PF didn’t propagate and counts match,
    # align by position and enrich. If counts differ, we still write but record the delta.
    carry_cols = ["digest_id_hour", "digest_file", "article_id", "index_id", "title", "source", "seed_url", "published"]
    missing = [c for c in carry_cols if c not in df_pf.columns]
    if missing and out_n == in_n:
        # align by index
        for c in carry_cols:
            if c not in df_pf.columns and c in df_in.columns:
                df_pf[c] = df_in[c].values
        # ensure digest_id_hour set at minimum
        df_pf["digest_id_hour"] = digest_id
    else:
        # always set digest_id_hour even if not missing
        df_pf["digest_id_hour"] = digest_id

    # Idempotent overwrite of our canonical per-hour PF output
    atomic_overwrite_jsonl(out_path, df_pf.to_dict(orient="records"))

    # Finish run with meta diagnostics
    meta = {"digest_id": digest_id, "out": str(out_path), "in_rows": in_n, "out_rows": out_n}
    if in_n != out_n:
        meta["row_delta"] = int(out_n - in_n)
    try:
        db.finish_run(run_id, stage=stage_name, ok=out_n, fail=0, meta=meta)
    except Exception:
        pass

    print(f"[{stage_name}] digest_id={digest_id} in={in_n} out={out_n} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
