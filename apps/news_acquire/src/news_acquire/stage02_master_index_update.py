# 02_master_index_update.py
# Catalog + mapping for a fixed hour bucket.
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict

import pandas as pd
from pandas.errors import EmptyDataError

from . import ids, db
from . import io as bio

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
RSS_DUMPS_DIR = DATA_DIR / "rss_slices" / "rss_dumps"
MASTER_REF_CSV = DATA_DIR / "master_ref.csv"
DIGEST_MAP_DIR = DATA_DIR / "digest_map"
QUAR_DIR = DATA_DIR / "quarantine"

# -------------------- utils/env --------------------

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip() not in ("0", "false", "False", "")


def ensure_dirs():
    for p in (RSS_DUMPS_DIR, DIGEST_MAP_DIR, QUAR_DIR, DATA_DIR):
        p.mkdir(parents=True, exist_ok=True)


def quarantine_path(stage: str, run_id: str) -> Path:
    return QUAR_DIR / f"{stage}_{run_id}.jsonl"

REQUIRED_COLS = ["digest_file", "window_type", "article_id", "Title", "Source", "Link", "Published", "index_id"]


def validate_input_df(df: pd.DataFrame, run_id: str) -> Tuple[pd.DataFrame, int]:
    """Ensure required columns and sane values; quarantine bad rows."""
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"02_master_index_update: missing required columns: {missing}")

    df["Published"] = pd.to_datetime(df["Published"], errors="coerce", utc=True)

    bad_mask = (
        df["Published"].isna()
        | (df["Title"].astype(str).str.strip() == "")
        | (df["Source"].astype(str).str.strip() == "")
        | (df["Link"].astype(str).str.strip() == "")
        | (df["digest_file"].astype(str).str.strip() == "")
        | (df["article_id"].astype(str).str.strip() == "")
    )

    bad = df[bad_mask]
    for _, r in bad.iterrows():
        bio.append_jsonl(
            quarantine_path("V02", run_id),
            {"reason": "bad_row", "row": _serializable_row(r)},
        )

    good = df[~bad_mask].copy()
    good["article_id"] = good["article_id"].astype(str)
    good["index_id"] = good["index_id"].astype(str)
    return good, len(bad)


def _serializable_row(r: pd.Series) -> Dict:
    row = r.to_dict()
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
        elif pd.isna(v):
            row[k] = None
    return row


def load_hour_slice_files(digest_id: str) -> List[Path]:
    pattern = f"*_{digest_id}00.csv"
    return sorted(RSS_DUMPS_DIR.glob(pattern))


def load_master_ref_csv() -> pd.DataFrame:
    if MASTER_REF_CSV.exists():
        try:
            df = pd.read_csv(MASTER_REF_CSV)
        except EmptyDataError:
            return pd.DataFrame(columns=["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"])
        for col in ("first_seen", "last_seen"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        return df
    return pd.DataFrame(columns=["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"])


def write_master_ref_csv(df: pd.DataFrame, null_sink: bool) -> None:
    out = (DATA_DIR / "_tmp" / "null" / "master_ref.csv") if null_sink else MASTER_REF_CSV
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].drop_duplicates(subset=["index_id"], keep="last").sort_values("index_id")
    df["topics"] = df["topics"].apply(lambda v: v if isinstance(v, list) else [])
    df["meta"] = df["meta"].apply(lambda v: v if isinstance(v, dict) else {})
    df.to_csv(out, index=False)


def write_digest_map_csv(df_map: pd.DataFrame, digest_id: str, null_sink: bool) -> Path:
    out_dir = (DATA_DIR / "_tmp" / "null" / "digest_map") if null_sink else DIGEST_MAP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{digest_id}.csv"
    cols = ["digest_file", "article_id", "index_id", "Title", "Source", "Link", "Published", "window_type"]
    for c in cols:
        if c not in df_map.columns:
            df_map[c] = None
    df_map = df_map[cols].drop_duplicates(subset=["digest_file", "article_id"], keep="last").sort_values(["digest_file", "article_id"])
    df_map.to_csv(out, index=False)
    return out

# -------------------- core --------------------

def run() -> int:
    ensure_dirs()

    digest_at_env = os.getenv("DIGEST_AT")
    dry_run = _env_bool("DRY_RUN", False)
    null_sink = _env_bool("NULL_SINK", False)
    run_id = os.getenv("RUN_ID")

    if digest_at_env:
        digest_id, _ = ids.digest_id_hour(digest_at_env)
    else:
        digest_id, _ = ids.digest_id_hour(pd.Timestamp.utcnow().strftime("%Y%m%dT%H"))

    stage_name = "02_master_index_update"
    run_id = run_id or f"{stage_name}:{digest_id}"

    try:
        db.start_run(run_id, stage_name, {"digest_id": digest_id})
    except Exception:
        pass

    files = load_hour_slice_files(digest_id)
    if not files:
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=0, meta={"digest_id": digest_id, "note": "no slice files"})
        except Exception:
            pass
        print(f"[{stage_name}] digest_id={digest_id} no slice files")
        return 0

    dfs: List[pd.DataFrame] = []
    for p in files:
        try:
            dfs.append(pd.read_csv(p))
        except Exception as e:
            bio.append_jsonl(quarantine_path("V02", run_id), {"reason": "read_error", "file": str(p), "error": str(e)})

    if not dfs:
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=0, meta={"digest_id": digest_id, "note": "read failures"})
        except Exception:
            pass
        print(f"[{stage_name}] digest_id={digest_id} failed to read slice files")
        return 1

    raw = pd.concat(dfs, ignore_index=True)
    good, n_bad = validate_input_df(raw, run_id)
    if good.empty:
        try:
            db.finish_run(run_id, stage=stage_name, ok=0, fail=n_bad, meta={"digest_id": digest_id})
        except Exception:
            pass
        print(f"[{stage_name}] digest_id={digest_id} all rows invalid")
        return 1

    digest_map = (
        good[["digest_file", "article_id", "index_id", "Title", "Source", "Link", "Published", "window_type"]]
        .copy()
    )
    digest_map = digest_map.sort_values(["digest_file", "article_id", "Published"]).drop_duplicates(
        subset=["digest_file", "article_id"], keep="last"
    )
    map_path = write_digest_map_csv(digest_map, digest_id, null_sink)

    hour_stats = good.groupby("index_id").agg(
        source=("Source", "last"),
        link=("Link", "last"),
        first_seen=("Published", "min"),
        last_seen=("Published", "max"),
    ).reset_index()

    master_prev = load_master_ref_csv()
    if not master_prev.empty:
        merged = pd.merge(
            master_prev,
            hour_stats,
            on="index_id",
            how="outer",
            suffixes=("_prev", "_new"),
        )
        # ensure suffix columns exist before time computations
        for col in ("first_seen_prev", "first_seen_new", "last_seen_prev", "last_seen_new"):
            if col not in merged.columns:
                merged[col] = pd.NaT

        def _coalesce(src_prev, src_new):
            return src_new if pd.notna(src_new) and src_new != "" else src_prev

        merged["source"] = merged.apply(lambda r: _coalesce(r.get("source_prev"), r.get("source_new")), axis=1)
        merged["link"] = merged.apply(lambda r: _coalesce(r.get("link_prev"), r.get("link_new")), axis=1)

        # Ensure time columns exist before computing mins/maxs
        for col in ("first_seen_prev", "first_seen_new", "last_seen_prev", "last_seen_new"):
            if col not in merged.columns:
                merged[col] = pd.NaT

        merged["first_seen"] = merged[["first_seen_prev", "first_seen_new"]].min(axis=1)
        merged["last_seen"] = merged[["last_seen_prev", "last_seen_new"]].max(axis=1)

        if "topics_prev" in merged.columns:
            merged["topics"] = merged["topics_prev"]
        else:
            merged["topics"] = [[] for _ in range(len(merged))]
        if "meta_prev" in merged.columns:
            merged["meta"] = merged["meta_prev"]
        else:
            merged["meta"] = [{} for _ in range(len(merged))]

        master_final = merged[["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"]].copy()
    else:
        master_final = hour_stats.copy()
        master_final["topics"] = [[] for _ in range(len(master_final))]
        master_final["meta"] = [{} for _ in range(len(master_final))]

    write_master_ref_csv(master_final, null_sink)

    ok_rows = len(hour_stats)
    if not _env_bool("DRY_RUN", False):
        try:
            payload = []
            for _, r in hour_stats.iterrows():
                payload.append(
                    {
                        "index_id": str(r["index_id"]),
                        "source": str(r.get("source") or ""),
                        "link": str(r.get("link") or ""),
                        "first_seen": pd.to_datetime(r["first_seen"]).to_pydatetime(),
                        "last_seen": pd.to_datetime(r["last_seen"]).to_pydatetime(),
                        "topics": [],
                        "meta": {"last_digest_id": digest_id},
                    }
                )
            if payload:
                db.upsert_master_ref(payload)
        except Exception as e:
            bio.append_jsonl(quarantine_path("V02", run_id), {"reason": "db_upsert_error", "error": str(e)})

    try:
        db.finish_run(
            run_id,
            stage="02_master_index_update",
            ok=ok_rows,
            fail=n_bad,
            meta={"digest_id": digest_id, "digest_map": str(map_path), "files": len(files)},
        )
    except Exception:
        pass

    print(
        f"[02_master_index_update] digest_id={digest_id} ok={ok_rows} bad={n_bad} "
        f"files={len(files)} dry_run={_env_bool('DRY_RUN', False)} null_sink={_env_bool('NULL_SINK', False)}"
    )
    return 0

if __name__ == "__main__":
    sys.exit(run())
