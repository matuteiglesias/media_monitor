# legacy/05_explode_pf_outputs.py
# Explode PF clusters or briefs -> ArticleDraftV1, validate, and enqueue "generate".
from __future__ import annotations

import os
import re
import sys
import json
from pathlib import Path
from typing import Iterable, List, Tuple, Optional

import pandas as pd

from . import ids, db, slugs
from . import io as bio

try:
    # Optional strict validation if your models are wired
    from backend.models import ArticleDraftV1  # type: ignore
except Exception:
    ArticleDraftV1 = None  # fallback to dicts

# -------- Paths --------
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
PF_OUT_DIR = DATA_DIR / "pf_out"
DIGEST_MAP_DIR = DATA_DIR / "digest_map"
DRAFTS_BASE = DATA_DIR / "drafts"
QUAR_DIR = DATA_DIR / "quarantine"
BRIEFS_DIR = STORAGE_DIR / "buses" / "news_piece_brief" / "v1"


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
    for p in (PF_OUT_DIR, DIGEST_MAP_DIR, DRAFTS_BASE, QUAR_DIR, BRIEFS_DIR):
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
    m = _GROUP_ID_RE.match(digest_group_id or "")
    if not m:
        return None
    return m.group("ts"), m.group("win"), m.group("topic"), m.group("grp")


def derive_digest_file(digest_ts: str, window_type: str) -> str:
    return f"{window_type}_{digest_ts}00"


def load_pf_outputs_for_hour(digest_id: str) -> List[Path]:
    return sorted(PF_OUT_DIR.glob(f"pfout_{digest_id}*.jsonl"))


def load_piece_briefs_for_hour(digest_id: str) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(BRIEFS_DIR.glob("*.jsonl")):
        for rec in iter_jsonl_records(path):
            if rec.get("__bad__"):
                continue
            if str(rec.get("schema_name") or "").strip() != "news_piece_brief.v1":
                continue
            if str(rec.get("digest_id_hour") or "").strip() != digest_id:
                continue
            rows.append(rec)
    return rows


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
def normalize_seed_idea(idea: dict) -> dict:
    normalized = dict(idea or {})
    if "key_facts" not in normalized and "key_data_points" in normalized:
        normalized["key_facts"] = normalized.get("key_data_points")
    return normalized


def extract_seed_ideas(row: dict) -> list[dict]:
    seed_ideas_obj = row.get("seed_ideas")
    if not isinstance(seed_ideas_obj, dict):
        return []
    ideas = seed_ideas_obj.get("seed_ideas")
    if not isinstance(ideas, list):
        return []
    return [normalize_seed_idea(idea) for idea in ideas if isinstance(idea, dict)]


def build_citation(link: str, title: str, source: str) -> dict:
    return {"url": link, "title": title, "source": source}


def make_draft_obj(
    digest_id: str,
    digest_file: str,
    article_id: str,
    index_id: str,
    cluster_topic: str | None,
    mapped_row: dict,
    headline: str | None,
) -> dict:
    title = headline or str(mapped_row.get("Title") or "").strip()
    source = str(mapped_row.get("Source") or "").strip()
    link = str(mapped_row.get("Link") or "").strip()
    cluster_id = f"{digest_id}:{index_id}"
    slug = slugs.slugify(title) or index_id.lower()

    return {
        "digest_id_hour": digest_id,
        "digest_file": digest_file,
        "article_id": str(article_id),
        "index_id": index_id,
        "topic": (cluster_topic or str(mapped_row.get("Topic") or "All Topics")).strip(),
        "headline": title,
        "dek": None,
        "citations": [build_citation(link, title, source)] if link else [],
        "cluster_id": cluster_id,
        "slug": slug,
        "body_html": "",
        "tags": [],
        "related_ids": [],
        "meta": {
            "source": source,
            "first_seen": str(mapped_row.get("Published", "")),
        },
    }


def make_draft_obj_from_brief(brief: dict, mapped_by_index: dict[str, dict]) -> tuple[dict | None, str | None]:
    index_ids = [str(v).strip() for v in (brief.get("source_index_ids") or []) if str(v).strip()]
    if not index_ids:
        index_ids = [str(r.get("index_id") or "").strip() for r in (brief.get("source_refs") or []) if isinstance(r, dict)]
        index_ids = [v for v in index_ids if v]
    if not index_ids:
        return None, "brief_without_sources"

    primary_index_id = index_ids[0]
    primary = mapped_by_index.get(primary_index_id)
    if not primary:
        return None, "brief_primary_index_missing"

    citations = []
    for idx in index_ids:
        row = mapped_by_index.get(idx)
        if not row:
            continue
        link = str(row.get("Link") or "").strip()
        if not link:
            continue
        title = str(row.get("Title") or "").strip()
        source = str(row.get("Source") or "").strip()
        citations.append(build_citation(link, title, source))

    digest_file = str(brief.get("digest_file") or primary.get("digest_file") or "").strip()
    digest_id_hour = str(brief.get("digest_id_hour") or "").strip()

    return {
        "digest_id_hour": digest_id_hour,
        "digest_file": digest_file,
        "article_id": str(primary.get("article_id") or "").strip(),
        "index_id": primary_index_id,
        "topic": str(brief.get("topic") or primary.get("Topic") or "All Topics").strip(),
        "headline": str(brief.get("working_title") or primary.get("Title") or "").strip(),
        "dek": str(brief.get("angle") or "").strip() or None,
        "citations": citations,
        "cluster_id": str(brief.get("brief_id") or f"brief:{primary_index_id}"),
        "slug": slugs.slugify(str(brief.get("working_title") or primary.get("Title") or "")) or primary_index_id.lower(),
        "body_html": "",
        "tags": [],
        "related_ids": index_ids[1:],
        "meta": {
            "source": str(primary.get("Source") or "").strip(),
            "first_seen": str(primary.get("Published") or ""),
            "brief_id": str(brief.get("brief_id") or "").strip(),
            "brief_schema": str(brief.get("schema_name") or "").strip(),
        },
    }, None


def _validate_and_package_draft(draft_obj: dict, run_id: str, source_reason: str) -> tuple[dict | None, str | None]:
    has_headline = bool(draft_obj.get("headline"))
    has_dek = bool(draft_obj.get("dek"))
    cits = draft_obj.get("citations") or []
    ok_min = bool(draft_obj.get("topic")) and (has_headline or has_dek) and any(c.get("url") for c in cits)
    if not ok_min:
        return None, "validation_min_fail"

    if ArticleDraftV1 is not None:
        try:
            draft_model = ArticleDraftV1(**draft_obj)
            return json.loads(draft_model.model_dump_json()), None
        except Exception as e:
            bio.append_jsonl(quarantine_path("V05", run_id), {
                "reason": "pydantic_validation_error",
                "error": str(e),
                "source_reason": source_reason,
                "draft": draft_obj,
            })
            return None, "pydantic_validation_error"
    return draft_obj, None


# -------- Core --------
def run() -> int:
    ensure_dirs()

    digest_at_env = os.getenv("DIGEST_AT")
    dry_run = _env_bool("DRY_RUN", False)
    null_sink = _env_bool("NULL_SINK", False)
    run_id = os.getenv("RUN_ID")
    limit = _env_float("LIMIT", None)
    sample = _env_float("SAMPLE", None)
    fallback_mode = (os.getenv("LEGACY_EDITORIAL_FALLBACK", "emergency") or "emergency").strip().lower()

    if digest_at_env:
        digest_id, _ = ids.digest_id_hour(digest_at_env)
    else:
        digest_id, _ = ids.digest_id_hour(pd.Timestamp.utcnow().strftime("%Y%m%dT%H"))
    stage_name = "05_explode_pf_outputs"
    run_id = run_id or f"{stage_name}:{digest_id}"

    try:
        db.start_run(run_id, stage_name, {"digest_id": digest_id})
    except Exception:
        pass

    map_csv = DIGEST_MAP_DIR / f"{digest_id}.csv"
    if not map_csv.exists():
        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "missing_digest_map", "digest_id": digest_id})
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
    map_rows = df_map.assign(_key=df_map["digest_file"].astype(str) + "::" + df_map["article_id"].astype(str)).set_index("_key").to_dict(orient="index")
    mapped_by_index = df_map.assign(index_id=df_map["index_id"].astype(str)).set_index("index_id").to_dict(orient="index")

    pf_files = load_pf_outputs_for_hour(digest_id)
    if not pf_files:
        print(f"[{stage_name}] no PF outputs for {digest_id} in {PF_OUT_DIR}")
        try:
            db.finish_run(run_id, ok=0, fail=0)
        except Exception:
            pass
        return 0

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

    drafts_dir = (DATA_DIR / "_tmp" / "null" / "drafts" / digest_id) if null_sink else (DRAFTS_BASE / digest_id)
    drafts_dir.mkdir(parents=True, exist_ok=True)

    total_refs = 0
    joined_refs = 0
    ok_drafts = 0
    bad_drafts = 0

    briefs = load_piece_briefs_for_hour(digest_id)
    use_briefs = len(briefs) > 0

    if use_briefs:
        for brief in briefs:
            total_refs += 1
            draft_obj, err = make_draft_obj_from_brief(brief, mapped_by_index)
            if err or draft_obj is None:
                bio.append_jsonl(quarantine_path("V05", run_id), {"reason": err or "brief_packaging_error", "brief_id": brief.get("brief_id")})
                bad_drafts += 1
                continue

            draft_record, validation_err = _validate_and_package_draft(draft_obj, run_id, "brief")
            if validation_err or draft_record is None:
                bad_drafts += 1
                continue

            index_id = str(draft_record.get("index_id") or "").strip()
            out_path = drafts_dir / f"{index_id}.jsonl"
            atomic_write_one_jsonl(out_path, draft_record)
            ok_drafts += 1
            joined_refs += 1

            if not dry_run:
                payload = {"digest_id_hour": draft_record.get("digest_id_hour"), "index_id": index_id, "draft_path": str(out_path)}
                enqueued = False
                for fn in ("push_work", "push_job", "enqueue_work", "enqueue_job"):
                    try:
                        getattr(db, fn)("generate", index_id, json.dumps(payload))
                        enqueued = True
                        break
                    except Exception:
                        continue
                if not enqueued:
                    bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "enqueue_not_available", "stage": "generate", "work_key": index_id, "payload": payload})
    else:
        if fallback_mode == "off":
            msg = (
                f"[{stage_name}] ERROR no news_piece_brief.v1 found for digest_id={digest_id}; "
                "legacy editorial fallback is disabled (LEGACY_EDITORIAL_FALLBACK=off)"
            )
            print(msg)
            bio.append_jsonl(
                quarantine_path("V05", run_id),
                {"reason": "fallback_disabled_no_piece_briefs", "digest_id": digest_id, "fallback_mode": fallback_mode},
            )
            try:
                db.finish_run(run_id, ok=0, fail=1)
            except Exception:
                pass
            return 1

        warning = (
            f"[{stage_name}] WARNING EMERGENCY FALLBACK ACTIVATED for digest_id={digest_id}; "
            "no news_piece_brief.v1 found, using legacy cluster packaging path"
        )
        print(warning)
        bio.append_jsonl(
            quarantine_path("V05", run_id),
            {
                "reason": "legacy_fallback_emergency_activated",
                "digest_id": digest_id,
                "fallback_mode": fallback_mode,
            },
        )
        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "missing_piece_briefs_fallback_legacy", "digest_id": digest_id})

        for _, row in df_groups.iterrows():
            digest_group_id = str(row.get("digest_group_id", "") or "").strip()
            parsed = parse_digest_group_id(digest_group_id)
            if not parsed:
                bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "bad_digest_group_id", "value": digest_group_id})
                bad_drafts += 1
                continue

            digest_ts, window_type, _, _ = parsed
            digest_file = derive_digest_file(digest_ts, window_type)
            clusters_obj = row.get("clustered_agenda_table", {})
            if isinstance(clusters_obj, dict) and "clustered_agenda_table" in clusters_obj:
                clusters = clusters_obj.get("clustered_agenda_table") or []
            elif isinstance(clusters_obj, list):
                clusters = clusters_obj
            else:
                clusters = []

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
                        bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "map_miss", "digest_file": digest_file, "article_id": article_id, "key": key})
                        bad_drafts += 1
                        continue

                    index_id = str(mapped.get("index_id"))
                    draft_obj = make_draft_obj(digest_ts, digest_file, article_id, index_id, cl_topic, mapped, headline)
                    draft_record, validation_err = _validate_and_package_draft(draft_obj, run_id, "cluster")
                    if validation_err or draft_record is None:
                        bad_drafts += 1
                        continue

                    out_path = drafts_dir / f"{index_id}.jsonl"
                    atomic_write_one_jsonl(out_path, draft_record)
                    ok_drafts += 1
                    joined_refs += 1

                    if not dry_run:
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
                            bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "enqueue_not_available", "stage": "generate", "work_key": index_id, "payload": payload})

            _ = extract_seed_ideas(row)

    if total_refs > 0:
        join_ratio = joined_refs / total_refs
        if join_ratio < 0.99:
            bio.append_jsonl(quarantine_path("V05", run_id), {"reason": "join_ratio_below_threshold", "joined": joined_refs, "total": total_refs, "ratio": round(join_ratio, 4), "threshold": 0.99})
            try:
                db.finish_run(run_id, ok=ok_drafts, fail=bad_drafts + 1)
            except Exception:
                pass
            print(f"[{stage_name}] join ratio {join_ratio:.3%} < 99% — fail")
            return 2

    try:
        db.finish_run(run_id, ok=ok_drafts, fail=bad_drafts)
    except Exception:
        pass

    print(f"[{stage_name}] digest_id={digest_id} drafts_ok={ok_drafts} bad={bad_drafts} joined={joined_refs}/{total_refs} -> {drafts_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
