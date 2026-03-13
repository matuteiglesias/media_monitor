#!/usr/bin/env python3
from pathlib import Path
import json, uuid
from backend.models import ArticleDraftV1
from backend.io import append_jsonl
from backend.db import pop_work, complete_work, fail_work, start_run, finish_run

RUN = f"gen-{uuid.uuid4().hex[:8]}"

def synthesize(draft: ArticleDraftV1) -> ArticleDraftV1:
    # placeholder: call your Promptflow or LLM
    body = f"<p>{draft.headline}</p>"
    draft.body_html = body
    draft.dek = draft.dek or draft.headline[:140]
    draft.citations = draft.citations or []
    return draft

def main():
    start_run(RUN, "generate", {})
    ok=fail=0
    jobs = pop_work("generate", limit=10) or []
    for job in jobs:
        try:
            digest_id, article_id = job["work_key"].split("::",1)
            drafts_path = Path(f"data/drafts/{digest_id}.ready.jsonl")
            # minimal: reconstruct a draft; in practice read original draft row if you need more fields
            d = ArticleDraftV1(article_id=article_id, slug=None, lang="es", headline=job["payload"].get("headline",""), topic="General", body_html=None, tags=[], citations=[], source_index_id=None)
            d = synthesize(d)
            append_jsonl(drafts_path, d)
            complete_work("generate", job["work_key"])
            ok+=1
        except Exception as e:
            fail_work("generate", job["work_key"], str(e))
            fail+=1
    finish_run(RUN, ok, fail)

if __name__ == "__main__":
    main()
