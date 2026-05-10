#!/usr/bin/env python3
from pathlib import Path
import json, uuid
from backend.models import ArticleDraftV1
from backend.io import append_jsonl
from backend.db import push_work, start_run, finish_run

RUN = f"draft-{uuid.uuid4().hex[:8]}"

def main(digest_id: str):
    start_run(RUN, "draft", {"digest_id":digest_id})
    ok=fail=0
    out = Path(f"data/drafts/{digest_id}.jsonl")

    # Assume you already produced an exploded JSONL per digest hour (from 05)
    for line in open(f"data/article_quotes/articles_exploded.jsonl", encoding="utf-8"):
        row = json.loads(line)
        if row.get("id_digest","").startswith(digest_id):
            d = ArticleDraftV1(
                article_id=f"ART-{row['index_id']}",
                slug=None, lang="es",
                headline=row.get("Title",""),
                topic=row.get("Topic") or row.get("cluster_topic") or "General",
                body_html=None, tags=[], citations=[],
                source_index_id=row["index_id"],
                source_link=row.get("Link"), source_title=row.get("Title"),
                meta={"digest_file": row.get("digest_file")}
            )
            err = d.validate_minimal()
            if err:
                append_jsonl(Path("data/quarantine/draft_bad.jsonl"), {"run_id":RUN,"err":err,"row":row})
                fail+=1; continue
            append_jsonl(out, d)
            key = f"{digest_id}::{d.article_id}"
            push_work("generate", key, {"digest_id":digest_id, "article_id":d.article_id})
            ok+=1

    finish_run(RUN, ok, fail)

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
