from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple

import pandas as pd

from . import db, ids
from . import io as bio

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
PF_OUT_DIR = DATA_DIR / "pf_out"
DIGEST_MAP_DIR = DATA_DIR / "digest_map"
QUAR_DIR = DATA_DIR / "quarantine"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "storage"))
BRIEFS_DIR = STORAGE_DIR / "buses" / "news_piece_brief" / "v1"

_GROUP_ID_RE = re.compile(r"^(?P<ts>\d{8}T\d{2})::(?P<win>[A-Za-z0-9_]+)::(?P<topic>.+?)::(?P<grp>\d{2})$")


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip() not in ("0", "false", "False", "")


def ensure_dirs() -> None:
    for p in (PF_OUT_DIR, DIGEST_MAP_DIR, QUAR_DIR, BRIEFS_DIR):
        p.mkdir(parents=True, exist_ok=True)


def quarantine_path(stage: str, run_id: str) -> Path:
    return QUAR_DIR / f"{stage}_{run_id}.jsonl"


def atomic_write_one_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    bio.atomic_write_jsonl(path, [line])


def parse_digest_group_id(digest_group_id: str) -> Optional[Tuple[str, str, str, str]]:
    m = _GROUP_ID_RE.match(digest_group_id or "")
    if not m:
        return None
    return m.group("ts"), m.group("win"), m.group("topic"), m.group("grp")


def derive_digest_file(digest_ts: str, window_type: str) -> str:
    return f"{window_type}_{digest_ts}00"


def load_pf_outputs_for_hour(digest_id: str) -> list[Path]:
    return sorted(PF_OUT_DIR.glob(f"pfout_{digest_id}*.jsonl"))


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


def _brief_id(digest_id: str, digest_group_id: str, idea: dict, ordinal: int) -> str:
    idea_id = str(idea.get("idea_id") or "").strip() or f"{ordinal:02d}"
    raw = f"{digest_id}|{digest_group_id}|{idea_id}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"npb_{digest}"


def run() -> int:
    ensure_dirs()

    digest_at_env = os.getenv("DIGEST_AT")
    dry_run = _env_bool("DRY_RUN", False)
    run_id = os.getenv("RUN_ID")

    if digest_at_env:
        digest_id, _ = ids.digest_id_hour(digest_at_env)
    else:
        digest_id, _ = ids.digest_id_hour(pd.Timestamp.utcnow().strftime("%Y%m%dT%H"))

    stage_name = "06_build_piece_briefs"
    run_id = run_id or f"{stage_name}:{digest_id}"

    try:
        db.start_run(run_id, stage_name, {"digest_id": digest_id})
    except Exception:
        pass

    map_csv = DIGEST_MAP_DIR / f"{digest_id}.csv"
    if not map_csv.exists():
        bio.append_jsonl(quarantine_path("V06", run_id), {"reason": "missing_digest_map", "digest_id": digest_id})
        try:
            db.finish_run(run_id, ok=0, fail=1)
        except Exception:
            pass
        return 1

    try:
        df_map = pd.read_csv(map_csv, dtype={"article_id": str})
    except Exception as e:
        bio.append_jsonl(quarantine_path("V06", run_id), {"reason": "map_read_error", "error": str(e), "file": str(map_csv)})
        try:
            db.finish_run(run_id, ok=0, fail=1)
        except Exception:
            pass
        return 1

    required_cols = ["digest_file", "article_id", "index_id", "Title", "Source", "Link", "Published"]
    missing = [c for c in required_cols if c not in df_map.columns]
    if missing:
        bio.append_jsonl(quarantine_path("V06", run_id), {"reason": "map_missing_cols", "missing": missing})
        try:
            db.finish_run(run_id, ok=0, fail=1)
        except Exception:
            pass
        return 1

    df_map["article_id"] = df_map["article_id"].astype(str)
    key_series = df_map["digest_file"].astype(str) + "::" + df_map["article_id"].astype(str)
    map_rows = df_map.assign(_key=key_series).set_index("_key").to_dict(orient="index")

    pf_files = load_pf_outputs_for_hour(digest_id)
    if not pf_files:
        print(f"[{stage_name}] no PF outputs for {digest_id}")
        try:
            db.finish_run(run_id, ok=0, fail=0)
        except Exception:
            pass
        return 0

    ok_briefs = 0
    bad_briefs = 0

    for pf in pf_files:
        for row in iter_jsonl_records(pf):
            if row.get("__bad__"):
                bio.append_jsonl(quarantine_path("V06", run_id), {"reason": "pf_bad_jsonl", "file": pf.name, **row})
                bad_briefs += 1
                continue

            digest_group_id = str(row.get("digest_group_id", "") or "").strip()
            parsed = parse_digest_group_id(digest_group_id)
            if not parsed:
                bio.append_jsonl(quarantine_path("V06", run_id), {"reason": "bad_digest_group_id", "value": digest_group_id})
                bad_briefs += 1
                continue

            digest_ts, window_type, topic_str, group_no = parsed
            digest_file = derive_digest_file(digest_ts, window_type)

            for ordinal, idea in enumerate(extract_seed_ideas(row), start=1):
                source_ids = [str(v) for v in (idea.get("source_ids") or [])]
                source_refs: list[dict] = []
                index_ids: list[str] = []
                for article_id in source_ids:
                    map_key = f"{digest_file}::{article_id}"
                    mapped = map_rows.get(map_key)
                    if not mapped:
                        continue
                    index_id = str(mapped.get("index_id") or "").strip()
                    if not index_id:
                        continue
                    index_ids.append(index_id)
                    source_refs.append(
                        {
                            "index_id": index_id,
                            "article_id": article_id,
                            "title": str(mapped.get("Title") or "").strip(),
                            "source": str(mapped.get("Source") or "").strip(),
                            "url": str(mapped.get("Link") or "").strip(),
                        }
                    )

                brief_id = _brief_id(digest_id, digest_group_id, idea, ordinal)
                piece_brief = {
                    "schema_name": "news_piece_brief.v1",
                    "brief_id": brief_id,
                    "digest_id_hour": digest_id,
                    "digest_group_id": digest_group_id,
                    "digest_file": digest_file,
                    "topic": str(idea.get("topic") or topic_str or "All Topics").strip(),
                    "working_title": str(idea.get("working_title") or idea.get("idea_title") or "").strip(),
                    "angle": str(idea.get("angle") or idea.get("draft_editorial_angle") or "").strip(),
                    "key_facts": [str(x).strip() for x in (idea.get("key_facts") or []) if str(x).strip()],
                    "potential_controversies": [
                        str(x).strip() for x in (idea.get("potential_controversies") or []) if str(x).strip()
                    ],
                    "relevant_quotes": [str(x).strip() for x in (idea.get("relevant_quotes") or []) if str(x).strip()],
                    "source_index_ids": index_ids,
                    "source_refs": source_refs,
                    "meta": {
                        "idea_id": str(idea.get("idea_id") or "").strip(),
                        "group_no": group_no,
                    },
                }

                if not piece_brief["working_title"]:
                    bio.append_jsonl(quarantine_path("V06", run_id), {"reason": "missing_working_title", "brief_id": brief_id})
                    bad_briefs += 1
                    continue

                if not dry_run:
                    out_path = BRIEFS_DIR / f"{brief_id}.jsonl"
                    atomic_write_one_jsonl(out_path, piece_brief)
                ok_briefs += 1

    try:
        db.finish_run(run_id, ok=ok_briefs, fail=bad_briefs)
    except Exception:
        pass

    print(f"[{stage_name}] digest_id={digest_id} briefs_ok={ok_briefs} bad={bad_briefs} -> {BRIEFS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
