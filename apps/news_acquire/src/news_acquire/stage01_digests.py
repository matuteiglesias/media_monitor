# legacy/01_digests.py
# Pull & slice (no heavy work). Deterministic on DIGEST_AT.
# - Reads Google News/RSS feeds from a validated, versioned configuration
# - Normalizes items, computes stable index_id
# - Slices into digest windows anchored at DIGEST_AT
# - Writes CSVs under data/rss_slices/rss_dumps/<digest_file>.csv
# - Optional JSONL mirror: data/slices/jsonl/<digest_id_hour>.jsonl
# - Independently controls acquisition, artifact writes, enqueue, and DB bookkeeping

from __future__ import annotations

import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone

import pandas as pd
import feedparser

# Acquisition-local backend helpers. Keep this stage independent of the removed legacy `backend` package.
from . import ids, db
from . import io as bio
from .feed_config import load_feed_config
from .runtime import SensingControls


# ======================= CONFIG =======================

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
SLICE_DIR = DATA_DIR / "rss_slices"
RSS_DUMPS_DIR = SLICE_DIR / "rss_dumps"
JSONL_DIR = DATA_DIR / "slices" / "jsonl"
QUAR_DIR = DATA_DIR / "quarantine"

# ======================= ENV/UTILS =======================

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

def compute_uid(title: str, source: str) -> str:
    raw = f"{title}::{source}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]

def stable_index_id_from_row(title: str, source: str, url: str) -> str:
    # Prefer URL + title + source hashing rule from backend.ids
    return ids.stable_index_id(title or "", source or "", url or "")

def clean_title(title: str) -> str:
    # Google News often appends " - Source" to the headline
    return title.rsplit(" - ", 1)[0].strip()

def ensure_dirs() -> None:
    for p in (SLICE_DIR, RSS_DUMPS_DIR, JSONL_DIR, QUAR_DIR):
        p.mkdir(parents=True, exist_ok=True)

def quarantine_path(stage: str, run_id: str) -> Path:
    return QUAR_DIR / f"{stage}_{run_id}.jsonl"

# Slice plan anchored at the hour bucket
def compute_slices(anchor: datetime) -> List[Tuple[str, datetime, datetime]]:
    # All ranges are [start, end) in UTC.
    out: List[Tuple[str, datetime, datetime]] = []
    hour = anchor.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

    # Always include the deterministic 1-hour window.
    out.append(("1h_window", hour, hour + timedelta(hours=1)))

    # The public selector admits signals up to 180 minutes old. A current-hour-only
    # sensing run can therefore be publication-starved early in the hour even when
    # good recent coverage exists. This four-hour bucket guarantees the full
    # selector horizon is materialized at every minute of the current UTC hour;
    # downstream deterministic selection still applies the exact age cutoff.
    out.append(
        (
            "recent_4h_window",
            hour - timedelta(hours=3),
            hour + timedelta(hours=1),
        )
    )

    # Optional larger historical windows depending on cadence.
    if hour.hour % 4 == 0:
        out.append(("4h_window", hour - timedelta(hours=8), hour - timedelta(hours=2)))
    if hour.hour % 8 == 0:
        out.append(("8h_window", hour - timedelta(hours=16), hour - timedelta(hours=4)))
    if hour.hour == 12:
        out.append(("2day_window", hour - timedelta(hours=60), hour - timedelta(hours=12)))
        if hour.day % 3 == 0:
            out.append(("3day_window", hour - timedelta(hours=168), hour - timedelta(hours=72)))
        if hour.day % 7 == 0:
            out.append(("weekly_window", hour - timedelta(days=14), hour - timedelta(days=7)))
        if hour.day % 14 == 0:
            out.append(("fortnight_window", hour - timedelta(days=45), hour - timedelta(days=15)))

    return out

# ======================= CORE =======================

def fetch_rss_now(feeds: Dict[str, str], limit: int | None) -> pd.DataFrame:
    rows: List[dict] = []
    for topic, url in feeds.items():
        feed = feedparser.parse(url)
        entries = feed.entries if limit is None else feed.entries[: int(limit)]
        for e in entries:
            title = clean_title(getattr(e, "title", "") or "")
            link = getattr(e, "link", "") or ""
            # published string; pandas will normalize to UTC later
            published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
            # Google News may embed 'source'
            src_title = getattr(getattr(e, "source", None), "title", None)
            source = (src_title or "").strip() or "N/A"

            uid = compute_uid(title, source)

            rows.append(
                {
                    "uid": uid,
                    "Topic": topic,
                    "Title": title,
                    "Link": link,
                    "Published": published,
                    "Source": source,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Normalize datetime to UTC and drop unparsable
    df["Published"] = pd.to_datetime(df["Published"], errors="coerce", utc=True)
    df = df.dropna(subset=["Published"]).copy()
    # Sort for stable assignment
    df = df.sort_values(["Published", "Title", "Source"]).reset_index(drop=True)
    # Dedup within this fetch by (Title, Source, Link)
    df = df.drop_duplicates(subset=["Title", "Source", "Link"], keep="first")
    return df

def validate_row_v01(r: pd.Series) -> Tuple[bool, str | None]:
    if not (str(r.get("Title") or "").strip()):
        return False, "missing_title"
    if not (str(r.get("Source") or "").strip()):
        return False, "missing_source"
    if not (str(r.get("Link") or "").strip()):
        return False, "missing_link"
    if pd.isna(r.get("Published")):
        return False, "bad_published"
    return True, None

def write_jsonl_mirror_atomic(path: Path, records: List[dict]) -> None:
    # replace-on-write to avoid duplication across reruns
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    if tmp.exists():
        tmp.unlink()
    with tmp.open("wb") as f:
        for rec in records:
            bio.append_jsonl(path=tmp, obj=rec)
    if path.exists():
        path.unlink()
    tmp.rename(path)


def _serializable_row(r):
    row = r.to_dict()
    for k, v in row.items():
        # pandas Timestamp or datetime
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
        # numpy types, etc.
        elif isinstance(v, (pd.Int64Dtype().type, )):
            row[k] = int(v)
    return row



def run() -> int:
    # ----- env knobs -----
    digest_at_env = os.getenv("DIGEST_AT")  # YYYYMMDDTHH expected
    controls = SensingControls.from_env()
    limit = _env_float("LIMIT", None)
    sample = _env_float("SAMPLE", None)
    null_sink = _env_bool("NULL_SINK", False)
    run_id = os.getenv("RUN_ID")

    # Anchor hour (deterministic)
    if digest_at_env:
        digest_id, anchor_dt = ids.digest_id_hour(digest_at_env)
    else:
        # fallback to current UTC hour for convenience (still deterministic over that hour)
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        digest_id, anchor_dt = ids.digest_id_hour(now.strftime("%Y%m%dT%H"))

    stage_name = "01_digests"
    run_id = run_id or f"{stage_name}:{digest_id}"

    feeds = load_feed_config()
    if controls.write_artifacts:
        ensure_dirs()

    if controls.db_run_bookkeeping:
        db.start_run(run_id, stage_name, {"digest_id": digest_id})

    # Acquisition and downstream side effects are deliberately independent.
    try:
        df_news = (
            fetch_rss_now(feeds, limit=None if limit is None else int(limit))
            if controls.acquire_network
            else pd.DataFrame(columns=["uid", "Topic", "Title", "Link", "Published", "Source"])
        )
    except Exception as exc:
        if controls.db_run_bookkeeping:
            db.finish_run(
                run_id,
                stage=stage_name,
                ok=0,
                fail=1,
                meta={"digest_id": digest_id, "error": f"{type(exc).__name__}: {exc}"},
            )
        raise

    # Optional downsample for iteration
    if sample is not None and 0 < sample < 1 and not df_news.empty:
        df_news = df_news.sample(frac=float(sample), random_state=17).sort_values("Published")

    # Normalize to UTC (idempotent)
    if not df_news.empty:
        df_news["Published"] = pd.to_datetime(df_news["Published"], errors="coerce", utc=True)
        df_news = df_news.dropna(subset=["Published"]).copy()

    # ----- slice plan -----
    slices = compute_slices(anchor_dt)

    total_ok = 0
    total_bad = 0
    mirror_records: List[dict] = []

    # Where to write
    out_dir = RSS_DUMPS_DIR if not null_sink else (DATA_DIR / "_tmp" / "null" / "rss_dumps")
    if controls.write_artifacts:
        out_dir.mkdir(parents=True, exist_ok=True)
    mirror_path = (JSONL_DIR / f"{digest_id}.jsonl") if not null_sink else (DATA_DIR / "_tmp" / "null" / "slices" / "jsonl" / f"{digest_id}.jsonl")

    # ----- per-slice processing -----
    for (label, start, end) in slices:
        # filter by window [start, end)
        if df_news.empty:
            df_slice = df_news.copy()
        else:
            df_slice = df_news[(df_news["Published"] >= start) & (df_news["Published"] < end)].copy()

        if df_slice.empty:
            continue

        # Assign within-slice fields
        df_slice = df_slice.sort_values(["Published", "Title", "Source"]).reset_index(drop=True)
        df_slice.insert(0, "article_id", df_slice.index + 1)
        df_slice["window_type"] = label
        digest_file = f"{label}_{digest_id}00"
        df_slice["digest_file"] = digest_file

        # Compute stable index_id (Title, Source, Link)
        df_slice["index_id"] = df_slice.apply(
            lambda r: stable_index_id_from_row(str(r.get("Title") or ""), str(r.get("Source") or ""), str(r.get("Link") or "")),
            axis=1,
        )

        # Validate rows, quarantine failures
        good_rows: List[dict] = []
        for _, r in df_slice.iterrows():
            ok, reason = validate_row_v01(r)
            if not ok:
                total_bad += 1

                r = _serializable_row(r)
                if controls.write_artifacts:
                    bio.append_jsonl(quarantine_path("V01", run_id), {
                    "reason": reason,
                    "row": r,
                    "digest_id": digest_id,
                    "window_type": label
                    })
                continue
            good_rows.append(r.to_dict())

        if not good_rows:
            continue

        # Collapse duplicates within slice by index_id (keep earliest Published)
        gdf = pd.DataFrame(good_rows)
        gdf = gdf.sort_values(["index_id", "Published"]).drop_duplicates(subset=["index_id"], keep="first")
        # Re-number article_id after dedup to maintain 1..N
        gdf = gdf.sort_values(["Published", "Title", "Source"]).reset_index(drop=True)
        gdf["article_id"] = gdf.index + 1

        # Column order for CSV contract
        cols = [
            "digest_file",
            "window_type",
            "article_id",
            "Title",
            "Source",
            "Link",
            "Published",
            "uid",
            "index_id",
            "Topic",
        ]
        for c in cols:
            if c not in gdf.columns:
                gdf[c] = "" if c not in ("Published", "article_id") else (pd.NaT if c == "Published" else 0)
        gdf = gdf[cols]

        # Write slice CSV (overwrite)
        out_path = out_dir / f"{digest_file}.csv"
        if controls.write_artifacts:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            gdf.to_csv(out_path, index=False)
        total_ok += len(gdf)

        # Mirror JSONL (per-row)
        for _, r in gdf.iterrows():
            rec = {
                "digest_id_hour": digest_id,
                "digest_file": r["digest_file"],
                "window_type": r["window_type"],
                "article_id": int(r["article_id"]),
                "index_id": r["index_id"],
                "title": r["Title"],
                "source": r["Source"],
                "seed_url": r["Link"],
                "published": pd.to_datetime(r["Published"]).isoformat() if pd.notna(r["Published"]) else None,
                "topic": r.get("Topic", ""),
            }
            mirror_records.append(rec)

            # Enqueue scrape jobs (side effect)
            if controls.enqueue_scrape:
                try:
                    db.push_work(
                        "scrape",
                        r["index_id"],
                        {
                            "index_id": r["index_id"],
                            "digest_id_hour": digest_id,
                            "source": r["Source"],
                            "title": r["Title"],
                            "url": r["Link"],
                        },
                    )
                except Exception as e:
                    # Don't break the whole slice on queue errors; send to quarantine
                    r = _serializable_row(r)
                    if controls.write_artifacts:
                        bio.append_jsonl(quarantine_path("V01", run_id), {
                        "reason": f"enqueue_error:{type(e).__name__}",
                        "error": str(e), 
                        "row": r,
                        "digest_id": digest_id,
                        })

    # Write/replace the JSONL mirror once (atomic)
    if controls.write_artifacts and mirror_records:
        write_jsonl_mirror_atomic(mirror_path, mirror_records)

    if controls.db_run_bookkeeping:
        db.finish_run(run_id, stage=stage_name, ok=total_ok, fail=total_bad, meta={"digest_id": digest_id, "slices": len(slices)})

    # Console summary
    print(
        f"[{stage_name}] digest_id={digest_id} ok={total_ok} bad={total_bad} slices={len(slices)} "
        f"acquire_network={controls.acquire_network} write_artifacts={controls.write_artifacts} "
        f"enqueue_scrape={controls.enqueue_scrape} db_run_bookkeeping={controls.db_run_bookkeeping} "
        f"null_sink={null_sink}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
