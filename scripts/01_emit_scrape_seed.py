#!/usr/bin/env python3
from pathlib import Path
from backend.models import ScrapeRecordV1
from backend.io import append_jsonl
from backend.db import push_work, start_run, finish_run
from datetime import datetime, timezone
import csv, uuid

RUN = f"seed-{uuid.uuid4().hex[:8]}"

def main():
    start_run(RUN, "seed", {"note":"rss seed"})
    ok=fail=0
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = Path(f"data/scrape/{day}.jsonl")

    # example: read one of your rss CSV dumps you already generate
    for row in csv.DictReader(open("data/rss_slices/rss_dumps/some.csv", newline="", encoding="utf-8")):
        rec = ScrapeRecordV1(
            index_id=row["index_id"],
            topic=row["Topic"], title=row["Title"],
            published=row["Published"], source=row["Source"], link=row["Link"]
        )
        err = rec.validate_minimal()
        if err:
            append_jsonl(Path("data/quarantine/scrape_bad.jsonl"), {"run_id":RUN,"err":err,"row":row})
            fail+=1; continue
        append_jsonl(out, rec)
        push_work("scrape", rec.index_id, {"link": rec.link})
        ok+=1
    finish_run(RUN, ok, fail)

if __name__ == "__main__":
    main()
