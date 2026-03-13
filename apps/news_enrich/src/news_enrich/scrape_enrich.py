#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import hashlib, uuid
from backend.models import ScrapeRecordV1, ScrapedData
from .io import append_jsonl
from .db import pop_work, complete_work, fail_work, start_run, finish_run

RUN = f"scrape-{uuid.uuid4().hex[:8]}"

def normalize_text(html:str)->str:
    # TODO: replace with your Playwright + cleaner; placeholder below:
    import re
    return re.sub(r'\s+',' ', html).strip()

def fetch_html(url:str)->str:
    # placeholder; wire to Playwright runner you already have
    import requests
    return requests.get(url, timeout=20).text

def main():
    start_run(RUN, "scrape", {})
    ok=fail=0
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = Path(f"data/scrape/{day}.enriched.jsonl")

    for job in pop_work("scrape", limit=10) or []:
        url = job["payload"]["link"]
        try:
            html = fetch_html(url)
            text = normalize_text(html)
            rec = ScrapeRecordV1(
                index_id=job["work_key"],
                title="", source="", link=url, topic="", published=None,   # minimal fields; enrichers can merge on index_id
                scraped_data=ScrapedData(
                    final_url=url,
                    text=text,
                    text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    byte_size=len(html.encode("utf-8")),
                    fetched_at=datetime.now(timezone.utc).isoformat()
                )
            )
            append_jsonl(out, rec)
            complete_work("scrape", job["work_key"])
            ok+=1
        except Exception as e:
            fail_work("scrape", job["work_key"], str(e))
            fail+=1

    finish_run(RUN, ok, fail)

if __name__ == "__main__":
    main()
