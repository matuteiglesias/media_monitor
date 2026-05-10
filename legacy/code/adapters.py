# adapters.py
from pathlib import Path
from backend import db, ids, io
from models import ScrapeRecordV1, ArticleDraftV1

def stable_index_id_from_row(row: dict) -> str:
    # prefer final_url if known, else original link
    url = (row.get("final_url") or row.get("original_link") or "").strip()
    return ids.stable_index_id(row.get("Title") or row.get("title",""),
                               row.get("Source") or row.get("source",""),
                               url)

def append_jsonl(path: Path, obj) -> None:
    io.append_jsonl(path, obj)

def upsert_master(rows: list[dict]) -> None:
    db.upsert_master_ref(rows)

def push_job(stage: str, work_key: str, payload: dict) -> None:
    db.push_work(stage, work_key, payload)
