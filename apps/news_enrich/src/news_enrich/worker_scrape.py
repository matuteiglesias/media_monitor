#!/usr/bin/env python3
"""PostgreSQL scrape worker backed by the shared enrich service."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sys
from typing import Callable

from .bus_writer import write_scraped_article
from .io import append_jsonl
from .records import ScrapedArticle
from .requests import EnrichRequest
from .service import FetchResult, enrich_one

PG_DSN = os.environ.get("PG_DSN")
BATCH = int(os.environ.get("BATCH", "5"))


def default_scrape_output(now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    return Path("data/scrape") / f"{now:%Y-%m-%d}.enriched.jsonl"


def pop_jobs(conn, stage, n):
    from psycopg.rows import dict_row

    sql = """
    with c as (
      select id
      from work_items
      where stage = %s and state='queued' and (not_before is null or not_before <= now())
      order by created_at
      for update skip locked
      limit %s
    )
    update work_items w
    set state='running', attempts = attempts + 1, updated_at = now()
    from c
    where w.id = c.id
    returning w.id, w.work_key, w.payload;
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, (stage, n))
        return cur.fetchall()


def mark_done(conn, wid):
    with conn.cursor() as cur:
        cur.execute("update work_items set state='done', last_error=null where id=%s", (wid,))


def mark_fail(conn, wid, err):
    with conn.cursor() as cur:
        cur.execute(
            """
            update work_items
            set state='queued',
                last_error=%s,
                not_before = now() + greatest(interval '2 minutes',
                                              interval '1 minute' * power(2, least(attempts, 7)))
            where id=%s
        """,
            (str(err)[:500], wid),
        )


def service_error(record: ScrapedArticle) -> str:
    """Return a retry-safe worker error string for non-success enrich results."""
    detail = record.error_message or record.error_code or f"fetch_status={record.fetch_status}"
    return f"enrich_one returned {record.fetch_status}: {detail}"


def handle_one(
    job,
    *,
    fetcher: Callable[[str], FetchResult] | None = None,
    bus_path: Path | None = None,
    scrape_mirror_path: Path | None = None,
) -> ScrapedArticle:
    """Enrich one queued scrape job and write bus + Level-0 mirror records."""
    request = EnrichRequest.from_queue_payload(job["work_key"], job.get("payload") or {})
    record = enrich_one(request, fetcher=fetcher)
    write_scraped_article(record, path=bus_path)
    append_jsonl(scrape_mirror_path or default_scrape_output(), record)
    return record


def main():
    import psycopg

    if not PG_DSN:
        print("PG_DSN not set", file=sys.stderr)
        sys.exit(2)
    ok = fail = 0
    with psycopg.connect(PG_DSN, autocommit=False) as conn:
        jobs = pop_jobs(conn, "scrape", BATCH)
        for j in jobs:
            try:
                record = handle_one(j)
                if record.ok:
                    mark_done(conn, j["id"])
                    conn.commit()
                    ok += 1
                else:
                    mark_fail(conn, j["id"], service_error(record))
                    conn.commit()
                    fail += 1
            except Exception as e:
                conn.rollback()
                mark_fail(conn, j["id"], e)
                conn.commit()
                fail += 1
    print(f"scrape worker exit: ok={ok} fail={fail}")


if __name__ == "__main__":
    main()
