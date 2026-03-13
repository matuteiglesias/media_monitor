# legacy/05_explode_pf_outputs.py
# Explode PF clusters -> ArticleDraftV1, validate, and enqueue "generate".
from __future__ import annotations

import os
import re
import sys
import json
from pathlib import Path
from typing import Iterable, List, Dict, Tuple, Optional

import pandas as pd

from backend import ids, db, slugs
from backend import io as bio
try:
    # Optional strict validation if your models are wired
    from backend.models import ArticleDraftV1  # type: ignore
except Exception:
    ArticleDraftV1 = None  # fallback to dicts

# -------- Paths --------
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PF_OUT_DIR = DATA_DIR / "pf_out"
DIGEST_MAP_DIR = DATA_DIR / "digest_map"
DRAFTS_BASE = DATA_DIR / "drafts"
QUAR_DIR = DATA_DIR / "quarantine"

# -------- Env helpers --------
def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip() not in ("0", "false", "False", "")

def _env_float(name: str, default: float | None = None) -> float | None:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(v)
    except Exception:
        return default

def ensure_dirs():
    for p in (PF_OUT_DIR, DIGEST_MAP_DIR, DRAFTS_BASE, QUAR_DIR):
        p.mkdir(parents=True, exist_ok=True)

def quarantine_path(stage: str, run_id: str) -> Path:
    return QUAR_DIR / f"{stage}_{run_id}.jsonl"

def atomic_write_one_jsonl(path: Path, record: dict) -> None:
    """Idempotent write of a single-record JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    bio.atomic_write_jsonl(path, [line])

# -------- Parsing helpers --------
_GROUP_ID_RE = re.compile(r"^(?P<ts>\d{8}T\d{2})::(?P<win>[A-Za-z0-9_]+)::(?P<topic>.+?)::(?P<grp>\d{2})$")

def parse_digest_group_id(digest_group_id: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Returns (digest_ts, window_type, topic_slug_or_name, group_no) or None.
    """
    m = _GROUP_ID_RE.match(digest_group_id or "")
    if not m:
        return None
    return m.group("ts"), m.group("win"), m.group("topic"), m.group("grp")

def derive_digest_file(digest_ts: str, window_type: str) -> str:
    # 02 produced digest_file names like "<window>_<YYYYMMDDTHH>00"
    return f"{window_type}_{digest_ts}00"

def load_pf_outputs_for_hour(digest_id: str) -> List[Path]:
    # support both pfout_<HOUR>.jsonl and pfout_<HOUR>_*.jsonl
    paths = sorted(PF_OUT_DIR.glob(f"pfout_{digest_id}*.jsonl"))
    return paths

def iter_jsonl_records(path: Path) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                yield json.loads(s)
            except Exception as e:
                yield {"__bad__": True, "error": str(e), "line_no": ln, "line": s[:400]}

# -------- Draft construction --------
def build_citation(link: str, title: str, source: str) -> dict:
    # minimal citation contract; validator will enforce stricter if available
    return {"url": link, "title": title, "source": source}

def make_draft_obj(digest_id: str,
                   digest_file: str,
                   article_id: str,
                   index_id: str,
                   cluster_topic: str | None,
                   mapped_row: dict,
                   headline: str | None) -> dict:
    # Conservative, minimal draft; ArticleDraftV1 (if present) will validate/transform.
    title = headline or str(mapped_row.get("Title") or "").strip()
    source = str(mapped_row.get("Source") or "").strip()
    link = str(mapped_row.get("Link") or "").strip()

    # Stable identities
    cluster_id = f"{digest_id}:{index_id}"      # per-hour × per-entity
    slug = slugs.slugify(title) or index_id.lower()

    draft = {
        "digest_id_hour": digest_id,
        "digest_file": digest_file,
        "article_id": str(article_id),
        "index_id": index_id,

        "topic": (cluster_topic or str(mapped_row.get("Topic") or "All Topics")).strip(),
        "headline": title,
        "dek": None,  # could be filled from PF "seed_ideas" if you prefer

        "citations": [build_citation(link, title, source)] if link else [],

        "cluster_id": cluster_id,
        "slug": slug,

        # allow downstream generator to fill these:
        "body_html": "",
        "tags": [],
        "related_ids": [],
        "meta": {
            "source": source,
            "first_seen": str(mapped_row.get("Published", "")),
        },
    }
    return draft

# -------- Core --------
def run() -> int:
    ensure_dirs()

    # Env knobs
    digest_at_env = os.getenv("DIGEST_AT")  # YYYYMMDDTHH
    dry_run = _env_bool("DRY_RUN", False)
    null_sink = _env_bool("NULL_SINK", False)  # drafts path supports null sink at directory level
    run_id = os.getenv("RUN_ID")
    limit = _env_float("LIMIT", None)   # cap PF groups processed
    sample = _env_float("SAMPLE", None) # frac of PF groups

    # Derive hour
    if digest_at_env:
        digest_id, _ = ids.digest_id_hour(digest_at_env)
    else:
        digest_id, _ = ids.digest_id_hour(pd.Timestamp.utcnow().strftime("%Y%m%dT%H"))
    stage_name = "05_explode_pf_outputs"
    run_id = run_id or f"{stage_name}:{digest_id}"

    # Start run
    try:
        db.start_run(run_id, stage_name, {"digest_id": digest_id})
    except Exception:
        pass

    # Load mapping for the hour
    map_csv = DIGEST_MAP_DIR / f"{digest_id}.csv"
    if not map_csv.exists():
        msg = {"note": "no digest_map", "digest_id": digest_id}
        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "missing_digest_map", **msg})
        try:
            db.finish_run(run_id, ok=0, fail=1)
        except Exception:
            pass
        print(f"[{stage_name}] missing {map_csv}")
        return 1

    try:
        df_map = pd.read_csv(map_csv, dtype={"article_id": str})
    except Exception as e:
        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "map_read_error", "file": str(map_csv), "error": str(e)})
        try:
            db.finish_run(run_id, ok=0, fail=1)
        except Exception:
            pass
        return 1

    # Build key->row map: key = digest_file::article_id
    required_cols = ["digest_file", "article_id", "index_id", "Title", "Source", "Link", "Published"]
    missing = [c for c in required_cols if c not in df_map.columns]
    if missing:
        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "map_missing_cols", "missing": missing})
        try:
            db.finish_run(run_id, ok=0, fail=1)
        except Exception:
            pass
        return 1

    df_map["article_id"] = df_map["article_id"].astype(str)
    kseries = df_map["digest_file"].astype(str) + "::" + df_map["article_id"].astype(str)
    map_rows = df_map.assign(_key=kseries).set_index("_key").to_dict(orient="index")

    # PF outputs
    pf_files = load_pf_outputs_for_hour(digest_id)
    if not pf_files:
        print(f"[{stage_name}] no PF outputs for {digest_id} in {PF_OUT_DIR}")
        try:
            db.finish_run(run_id, ok=0, fail=0)
        except Exception:
            pass
        return 0

    # Read, optionally sample/limit at the GROUP (line) level
    group_records: List[dict] = []
    for pf in pf_files:
        for rec in iter_jsonl_records(pf):
            if rec.get("__bad__"):
                bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "pf_bad_jsonl", "file": pf.name, **rec})
                continue
            group_records.append(rec)

    if not group_records:
        print(f"[{stage_name}] PF outputs empty after filtering")
        try:
            db.finish_run(run_id, ok=0, fail=0)
        except Exception:
            pass
        return 0

    df_groups = pd.DataFrame(group_records)
    if sample is not None and 0 < sample < 1:
        df_groups = df_groups.sample(frac=float(sample), random_state=17).reset_index(drop=True)
    if limit is not None:
        df_groups = df_groups.head(int(limit))

    # Output drafts directory
    drafts_dir = (DATA_DIR / "_tmp" / "null" / "drafts" / digest_id) if null_sink else (DRAFTS_BASE / digest_id)
    drafts_dir.mkdir(parents=True, exist_ok=True)

    # Explode clusters
    total_refs = 0  # how many (digest_file, article_id) refs PF tried to produce
    joined_refs = 0
    ok_drafts = 0
    bad_drafts = 0

    for _, row in df_groups.iterrows():
        digest_group_id = str(row.get("digest_group_id", "") or "").strip()
        parsed = parse_digest_group_id(digest_group_id)
        if not parsed:
            bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "bad_digest_group_id", "value": digest_group_id})
            bad_drafts += 1
            continue
        digest_ts, window_type, topic_str, group_no = parsed
        digest_file = derive_digest_file(digest_ts, window_type)

        # clusters structure: legacy: {"clustered_agenda_table": [{"topic": "...", "article_ids":[...], "deduplicated_titles":[...]}]}
        clusters_obj = row.get("clustered_agenda_table", {})
        if isinstance(clusters_obj, dict) and "clustered_agenda_table" in clusters_obj:
            clusters = clusters_obj.get("clustered_agenda_table") or []
        elif isinstance(clusters_obj, list):
            clusters = clusters_obj
        else:
            clusters = []

        if not clusters:
            # still allow seed ideas path below; but note no article refs here
            pass

        for cl in clusters:
            cl_topic = cl.get("topic") if isinstance(cl, dict) else None
            a_ids = (cl.get("article_ids") or []) if isinstance(cl, dict) else []
            titles = (cl.get("deduplicated_titles") or []) if isinstance(cl, dict) else []

            n = min(len(a_ids), len(titles)) if titles else len(a_ids)
            for i in range(n):
                article_id = str(a_ids[i])
                headline = titles[i] if i < len(titles) else None

                total_refs += 1
                key = f"{digest_file}::{article_id}"
                mapped = map_rows.get(key)
                if not mapped:
                    bio.append_jsonl(quarantine_path("V05", run_id), {
                        "reason": "map_miss",
                        "digest_file": digest_file,
                        "article_id": article_id,
                        "key": key
                    })
                    bad_drafts += 1
                    continue

                index_id = str(mapped.get("index_id"))
                draft_obj = make_draft_obj(digest_ts, digest_file, article_id, index_id, cl_topic, mapped, headline)

                # Validation (V05): topic && (headline||dek) && >=1 citation.url
                has_headline = bool(draft_obj.get("headline"))
                has_dek = bool(draft_obj.get("dek"))
                cits = draft_obj.get("citations") or []
                ok_min = bool(draft_obj.get("topic")) and (has_headline or has_dek) and any(c.get("url") for c in cits)

                if not ok_min:
                    bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "validation_min_fail", "draft": draft_obj})
                    bad_drafts += 1
                    continue

                # Optional strict Pydantic validation
                if ArticleDraftV1 is not None:
                    try:
                        draft_model = ArticleDraftV1(**draft_obj)
                        draft_record = json.loads(draft_model.model_dump_json())
                    except Exception as e:
                        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "pydantic_validation_error", "error": str(e), "draft": draft_obj})
                        bad_drafts += 1
                        continue
                else:
                    draft_record = draft_obj

                # Idempotent write per index_id
                out_path = drafts_dir / f"{index_id}.jsonl"
                atomic_write_one_jsonl(out_path, draft_record)
                ok_drafts += 1
                joined_refs += 1

                # Enqueue next stage
                if not dry_run:
                    # Try a few possible enqueue APIs depending on your backend
                    payload = {"digest_id_hour": digest_ts, "index_id": index_id, "draft_path": str(out_path)}
                    enqueued = False
                    for fn in ("push_work", "push_job", "enqueue_work", "enqueue_job"):
                        try:
                            getattr(db, fn)("generate", index_id, json.dumps(payload))
                            enqueued = True
                            break
                        except Exception:
                            continue
                    if not enqueued:
                        # best-effort log; pipeline still proceeds
                        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "enqueue_not_available", "stage": "generate", "work_key": index_id, "payload": payload})

        # You can also process seed_ideas here if you want to persist them:
        # ideas = row.get("seed_ideas", {}).get("seed_ideas", []) if isinstance(row.get("seed_ideas"), dict) else []
        # (Persist to a separate ideas/ path if helpful.)

    # Join success threshold
    if total_refs > 0:
        join_ratio = joined_refs / total_refs
        if join_ratio < 0.99:
            # fail hard per spec
            bio.append_jsonl(quarantine_path("V05", run_id), {
                "reason": "join_ratio_below_threshold",
                "joined": joined_refs,
                "total": total_refs,
                "ratio": round(join_ratio, 4),
                "threshold": 0.99
            })
            try:
                db.finish_run(run_id, ok=ok_drafts, fail=bad_drafts + 1)
            except Exception:
                pass
            print(f"[{stage_name}] join ratio {join_ratio:.3%} < 99% — fail")
            return 2

    # Finish run
    try:
        db.finish_run(run_id, ok=ok_drafts, fail=bad_drafts)
    except Exception:
        pass

    print(f"[{stage_name}] digest_id={digest_id} drafts_ok={ok_drafts} bad={bad_drafts} joined={joined_refs}/{total_refs} -> {drafts_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
