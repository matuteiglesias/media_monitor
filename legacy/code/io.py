# backend/io.py
from pathlib import Path
from pydantic import BaseModel
import os, tempfile, json

def append_jsonl(path: Path, obj: BaseModel | dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = obj.model_dump_json() if isinstance(obj, BaseModel) else json.dumps(obj, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def atomic_write_jsonl(path: Path, rows: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        for line in rows:
            tmp.write(line.rstrip("\n") + "\n")
        temp_name = tmp.name
    os.replace(temp_name, path)
