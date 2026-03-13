# legacy/01_digests.py
# Pull & slice (no heavy work). Deterministic on DIGEST_AT.
# - Reads Google News/RSS feeds (hardcoded here; you can swap to config later)
# - Normalizes items, computes stable index_id
# - Slices into digest windows anchored at DIGEST_AT
# - Writes CSVs under data/rss_slices/rss_dumps/<digest_file>.csv
# - Optional JSONL mirror: data/slices/jsonl/<digest_id_hour>.jsonl
# - If not DRY_RUN, enqueues scrape jobs keyed by index_id

from __future__ import annotations

import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, timezone

import pandas as pd
import feedparser

# Backend layer
from backend import ids, db
from backend import io as bio
from backend import models  # not used directly here, but kept for symmetry/import tests


# ======================= CONFIG =======================

# You can move these to data/config/*.yml later
RSS_FEEDS: Dict[str, str] = {
    "Inflación y Precios": "https://news.google.com/rss/search?q=(%22inflación%22+OR+%22IPC%22+OR+%22canasta+básica%22+OR+INDEC+OR+consultoras)+Argentina&hl=es-419&gl=AR&ceid=AR:es-419",
    "Tipo de Cambio y Reservas": "https://news.google.com/rss/search?q=dólar+OR+blue+OR+oficial+OR+reservas+OR+BCRA+OR+intervención+OR+futuros+OR+planchado&hl=es-419&gl=AR&ceid=AR:es-419",
    "Deuda y Financiamiento": "https://news.google.com/rss/search?q=bono+OR+licitación+OR+vencimientos+OR+Bonte+OR+tasa+OR+rollover&hl=es-419&gl=AR&ceid=AR:es-419",
    "Actividad y Empleo": "https://news.google.com/rss/search?q=subsidios+OR+paritarias+OR+gremios+OR+conciliación+OR+emple+OR+trabaj+OR+informal+OR+desemple+OR+EPH+OR+salarios&hl=es-419&gl=AR&ceid=AR:es-419",
    "Sector Externo": "https://news.google.com/rss/search?q=(comerc+exterior+OR+balanz+argentin+OR+export+OR+import+OR+arancel)+site:infobae.com+OR+site:lanacion.com.ar+OR+site:clarin.com+OR+site:ambito.com.ar+OR+site:telam.com.ar+OR+site:iprofesional.com&hl=es-419&gl=AR&ceid=AR:es-419",
    "Finanzas": "https://news.google.com/rss/search?q=(gasto+public+OR+ajuste+fiscal+OR+deficit+OR+superavit+OR+BCRA+OR+presupuesto+OR+bono+OR+banco+OR+riesgo+pais+OR+tasa+interes+OR+financier)&site:ambito.com.ar+OR+site:infobae.com+OR+site:lanacion.com.ar+OR+site:cronista.com+OR+site:baenegocios.com+OR+site:bna.com.ar&hl=es-419&gl=AR&ceid=AR:es-419",
    "Personajes Políticos y Económicos": "https://news.google.com/rss/search?q=(Milei+OR+Caputo+OR+Bausili+OR+Rubinstein+OR+Prat-Gay+OR+Cavallo+OR+Cristina+OR+Massa+OR+Melconian+OR+Macri+OR+Kicillof)+site:.ar&hl=es-419&gl=AR&ceid=AR:es-419",
}

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
    # All ranges are [start, end) in UTC
    # You can tweak the windows; this mirrors your legacy behavior with clear bounds
    out: List[Tuple[str, datetime, datetime]] = []
    hour = anchor.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

    # Always include the deterministic 1-hour window
    out.append(("1h_window", hour, hour + timedelta(hours=1)))

    # Optional larger windows depending on cadence
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
        if hasattr(v, "isoformat"):
            row[k] = v.isoformat()
        # numpy types, etc.
        elif isinstance(v, (pd.Int64Dtype().type, )):
            row[k] = int(v)
    return row



def run() -> int:
    ensure_dirs()

    # ----- env knobs -----
    digest_at_env = os.getenv("DIGEST_AT")  # YYYYMMDDTHH expected
    dry_run = _env_bool("DRY_RUN", False)
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

    # Run bookkeeping (best-effort; don't crash the stage if runs table is absent)
    try:
        db.start_run(run_id, stage_name, {"digest_id": digest_id})
    except Exception:
        pass

    # ----- fetch (skip network if DRY_RUN) -----
    if dry_run:
        # In DRY_RUN, we don't hit the network. We proceed to slicing using whatever we can fetch now.
        # If you want to read a cached raw CSV here, add that read; for now we keep it simple.
        df_news = pd.DataFrame(columns=["uid", "Topic", "Title", "Link", "Published", "Source"])
    else:
        df_news = fetch_rss_now(RSS_FEEDS, limit=None if limit is None else int(limit))

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
                bio.append_jsonl(
                    quarantine_path("V01", run_id),
                    {
                    "reason": reason,
                    "row": r,
                    "digest_id": digest_id,
                    "window_type": label
                    }
                )
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
            if not dry_run:
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
                    bio.append_jsonl(
                        quarantine_path("V01", run_id),
                        {
                        "reason": f"enqueue_error:{type(e).__name__}",
                        "error": str(e), 
                        "row": r,
                        "digest_id": digest_id,
                        }
                    )

    # Write/replace the JSONL mirror once (atomic)
    if mirror_records:
        write_jsonl_mirror_atomic(mirror_path, mirror_records)

    # Finish run
    try:
        db.finish_run(run_id, stage=stage_name, ok=total_ok, fail=total_bad, meta={"digest_id": digest_id, "slices": len(slices)})
    except Exception:
        pass

    # Console summary
    print(f"[{stage_name}] digest_id={digest_id} ok={total_ok} bad={total_bad} slices={len(slices)} dry_run={dry_run} null_sink={null_sink}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
