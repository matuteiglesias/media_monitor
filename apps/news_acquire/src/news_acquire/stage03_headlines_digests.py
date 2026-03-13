# legacy/03_headlines_digests.py
# Build group-level digest text (markdown) + JSONL for PromptFlow (legacy schema).
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

import pandas as pd
from pydantic import BaseModel, ValidationError

from . import ids, db
from . import io as bio  # for append_jsonl and JSON helpers

# ---------- Paths ----------
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DIGEST_MAP_DIR = DATA_DIR / "digest_map"                 # input from stage 02
OUT_JSONL_DIR = DATA_DIR / "digest_jsonls"               # PF input (legacy)
OUT_MD_DIR = DATA_DIR / "output_digests"                 # optional mirrors (human)
QUAR_DIR = DATA_DIR / "quarantine"

REQUIRED_MAP_COLS = [
    "digest_file", "window_type", "article_id",
    "Title", "Source", "Link", "Published"
]  # Topic optional

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
    for p in (OUT_JSONL_DIR, OUT_MD_DIR, QUAR_DIR):
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

# ---------- Contract for PF legacy input ----------
class PFGroupInputV1(BaseModel):
    id_digest: str           # e.g., 20250830T16_000
    digest_group_id: str     # e.g., 20250830T16::4h_window::Actividad_y_Empleo::01
    window_type: str
    topic: str
    group_number: str        # "01", "02", ...
    content: str             # markdown block with the group’s headlines

# ---------- Helpers ----------
def _safe_topic(topic: str | None) -> str:
    t = (topic or "").strip()
    return t if t else "All Topics"

def _topic_slug(topic: str) -> str:
    t = _safe_topic(topic)
    return re.sub(r"[^\w\-]+", "_", t)

def _split_topic_group(df_topic: pd.DataFrame, min_rows: int, max_rows: int) -> List[pd.DataFrame]:
    n = len(df_topic)
    if n <= max_rows:
        return [df_topic.reset_index(drop=True)]
    # ceil split into near-equal parts not below min_rows
    k = (n + max_rows - 1) // max_rows
    parts = []
    step = (n + k - 1) // k
    for start in range(0, n, step):
        parts.append(df_topic.iloc[start:start+step].reset_index(drop=True))
    # merge tail if too small
    if len(parts) > 1 and len(parts[-1]) < min_rows:
        parts[-2] = pd.concat([parts[-2], parts[-1]], ignore_index=True)
        parts.pop()
    return parts

def _render_markdown(window_type: str, topic: str, group_no: str, rows: pd.DataFrame) -> str:
    lines = [f"# {topic} — {window_type} (Grupo {group_no})", ""]
    for _, r in rows.iterrows():
        aid = r.get("article_id")
        title = str(r.get("Title") or "").strip()
        src = str(r.get("Source") or "").strip()
        # url = str(r.get("Link") or "").strip()
        pub = r.get("Published")
        pub_s = ""
        if pd.notna(pub):
            try:
                pub_s = pd.to_datetime(pub, utc=True).strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                pub_s = str(pub)
        line = f"- **ID {aid}** — {title} — _{src}_"
        if pub_s:
            line += f" — _{pub_s}_"
        # if url:
        #     line += f"\n  <{url}>"
        lines.append(line)
    lines.append("")  # final newline
    return "\n".join(lines)

def _write_md_mirror(dir_: Path, digest_id: str, window_type: str, topic: str, group_no: str, content: str) -> Path:
    dir_.mkdir(parents=True, exist_ok=True)
    fname = f"headlines_{window_type}_{digest_id}_{_topic_slug(topic)}_{group_no}.md"
    p = dir_ / fname
    p.write_text(content, encoding="utf-8")
    return p

# ---------- Core ----------
def run() -> int:
    ensure_dirs()

    # Env knobs
    digest_at_env = os.getenv("DIGEST_AT")  # YYYYMMDDTHH
    dry_run = _env_bool("DRY_RUN", False)   # no effect on file writes; only skip DB
    null_sink = _env_bool("NULL_SINK", False)
    run_id = os.getenv("RUN_ID")
    limit = _env_float("LIMIT", None)       # caps rows before grouping
    sample = _env_float("SAMPLE", None)     # 0<sample<1 downsample before grouping

    # Derive hour (deterministic)
    if digest_at_env:
        digest_id, _ = ids.digest_id_hour(digest_at_env)
    else:
        digest_id, _ = ids.digest_id_hour(pd.Timestamp.utcnow().strftime("%Y%m%dT%H"))
    stage_name = "03_headlines_digests"
    run_id = run_id or f"{stage_name}:{digest_id}"

    # Run start
    try:
        db.start_run(run_id, stage=stage_name, meta={"digest_id": digest_id})
    except Exception:
        pass

    # Load digest_map for the hour
    map_csv = DIGEST_MAP_DIR / f"{digest_id}.csv"
    if not map_csv.exists():
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=0, meta={"note": "no digest_map", "digest_id": digest_id})
        except Exception:
            pass
        print(f"[{stage_name}] no digest_map for {digest_id}: {map_csv}")
        return 0

    try:
        df = pd.read_csv(map_csv)
    except Exception as e:
        bio.append_jsonl(quarantine_path("V03", run_id), {"reason": "read_error", "file": str(map_csv), "error": str(e)})
        print(f"[{stage_name}] failed reading {map_csv}: {e}")
        return 1

    # Validate columns
    missing = [c for c in REQUIRED_MAP_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"{stage_name}: missing required columns in {map_csv}: {missing}")

    # Normalize types/fields
    df["Published"] = pd.to_datetime(df["Published"], errors="coerce", utc=True)
    df = df.dropna(subset=["Published"]).copy()
    if "Topic" not in df.columns:
        df["Topic"] = "All Topics"

    # Optional sample/limit **before** grouping
    df = df.sort_values(["window_type", "Topic", "Published", "Title"]).reset_index(drop=True)
    if sample is not None and 0 < sample < 1:
        df = df.sample(frac=float(sample), random_state=17).sort_values(["window_type", "Topic", "Published", "Title"])
    if limit is not None:
        df = df.head(int(limit))

    # Build groups → content
    out_records: List[dict] = []
    md_written = 0
    bad = 0
    min_rows = int(os.getenv("GROUP_MIN_ROWS", "5"))
    max_rows = int(os.getenv("GROUP_MAX_ROWS", "25"))

    # Determine output dirs
    jsonl_dir = (DATA_DIR / "_tmp" / "null" / "digest_jsonls") if null_sink else OUT_JSONL_DIR
    md_dir = (DATA_DIR / "_tmp" / "null" / "output_digests") if null_sink else OUT_MD_DIR
    jsonl_dir.mkdir(parents=True, exist_ok=True); md_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = jsonl_dir / f"{digest_id}.jsonl"

    # Group by window_type then Topic for human sense
    idx_counter = 0
    for window_type, df_w in df.groupby("window_type", sort=False):
        for topic, df_t in df_w.groupby("Topic", sort=False):
            chunks = _split_topic_group(df_t, min_rows=min_rows, max_rows=max_rows)
            for i, chunk in enumerate(chunks, start=1):
                group_no = f"{i:02d}"
                content = _render_markdown(window_type, _safe_topic(topic), group_no, chunk)
                digest_group_id = f"{digest_id}::{window_type}::{_topic_slug(topic)}::{group_no}"
                rec = {
                    "id_digest": f"{digest_id}_{idx_counter:03d}",
                    "digest_group_id": digest_group_id,
                    "window_type": window_type,
                    "topic": _safe_topic(topic),
                    "group_number": group_no,
                    "content": content,
                }
                # Validate with Pydantic
                try:
                    PFGroupInputV1(**rec)
                except ValidationError as ve:
                    bad += 1
                    bio.append_jsonl(quarantine_path("V03", run_id), {"reason": "validation_error", "error": str(ve), "record": rec})
                    continue

                # Optional MD mirror (kept for legacy ergonomics)
                _write_md_mirror(md_dir, digest_id, window_type, _safe_topic(topic), group_no, content)
                md_written += 1

                out_records.append(rec)
                idx_counter += 1

    # Write JSONL atomically (idempotent)
    if out_records:
        atomic_overwrite_jsonl(out_jsonl, out_records)

    ok = len(out_records)
    try:
        db.finish_run(
            run_id,
            stage=stage_name,
            ok=ok,
            fail=bad,
            meta={
                "digest_id": digest_id,
                "out_jsonl": str(out_jsonl),
                "md_files": md_written,
                "groups": ok,
                "min_rows": min_rows,
                "max_rows": max_rows,
            },
        )
    except Exception:
        pass

    print(f"[{stage_name}] digest_id={digest_id} groups={ok} bad={bad} -> {out_jsonl}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
