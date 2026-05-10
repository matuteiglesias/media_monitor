#!/usr/bin/env python3
"""Batch scrape/enrich runner backed by the shared enrich service."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import uuid

from .bus_writer import write_scraped_article
from .db import pop_work, complete_work, fail_work, start_run, finish_run
from .io import append_jsonl
from .requests import EnrichRequest
from .service import enrich_one

RUN = f"scrape-{uuid.uuid4().hex[:8]}"


def output_path(now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    return Path("data/scrape") / f"{now:%Y-%m-%d}.enriched.jsonl"


def main():
    start_run(RUN, "scrape", {})
    ok = fail = 0
    out = output_path()

    for job in pop_work("scrape", limit=10) or []:
        try:
            request = EnrichRequest.from_queue_payload(job["work_key"], job.get("payload") or {})
            record = enrich_one(request)
            write_scraped_article(record)
            append_jsonl(out, record)
            complete_work("scrape", job["work_key"])
            ok += 1
        except Exception as e:
            fail_work("scrape", job["work_key"], str(e))
            fail += 1

    finish_run(RUN, ok, fail)


if __name__ == "__main__":
    main()
