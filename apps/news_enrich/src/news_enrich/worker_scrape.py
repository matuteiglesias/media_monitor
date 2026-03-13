# scripts/worker_scrape.py
import os, sys, time, json
import psycopg
from psycopg.rows import dict_row

PG_DSN = os.environ.get("PG_DSN")
BATCH  = int(os.environ.get("BATCH", "5"))

def pop_jobs(conn, stage, n):
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
        cur.execute("""
            update work_items
            set state='queued',
                last_error=%s,
                not_before = now() + greatest(interval '2 minutes',
                                              interval '1 minute' * power(2, least(attempts, 7)))
            where id=%s
        """, (str(err)[:500], wid))

def handle_one(job):
    # TODO: call your scrape/enrich function by index_id
    index_id = job["work_key"]
    payload  = job["payload"] or {}
    # scrape_and_enrich(index_id, payload)
    return True

def main():
    if not PG_DSN:
        print("PG_DSN not set", file=sys.stderr); sys.exit(2)
    ok = fail = 0
    with psycopg.connect(PG_DSN, autocommit=False) as conn:
        jobs = pop_jobs(conn, "scrape", BATCH)
        for j in jobs:
            try:
                if handle_one(j):
                    mark_done(conn, j["id"])
                    conn.commit(); ok += 1
                else:
                    mark_fail(conn, j["id"], "returned False")
                    conn.commit(); fail += 1
            except Exception as e:
                conn.rollback()
                mark_fail(conn, j["id"], e)
                conn.commit(); fail += 1
    print(f"scrape worker exit: ok={ok} fail={fail}")

if __name__ == "__main__":
    main()




# from backend import db
# from models import ScrapeRecordV1
# from adapters import append_jsonl, upsert_master
# from pathlib import Path

# jobs = db.pop_work("scrape", limit=25)   # returns stage, key, payload  :contentReference[oaicite:19]{index=19}
# ok = fail = 0
# for j in jobs:
#     try:
#         rec = run_playwright(j["payload"]["url"])  # your scraper
#         sr = ScrapeRecordV1(
#             index_id=j["payload"]["index_id"],     # pre-id, may be title|source|seed-url
#             digest_id_hour=j["payload"]["digest_id_hour"],
#             # ... fill the rest, including final_url, main_text, fetched_at ...
#         )                                          # contract check here  :contentReference[oaicite:20]{index=20}
#         append_jsonl(Path("data/scrape")/f"{sr.digest_id_hour}.jsonl", sr)
#         # update catalog last_seen + stash final_url in meta
#         upsert_master([{
#             "index_id": sr.index_id,
#             "source": sr.source,
#             "link": str(sr.final_url or sr.original_link),
#             "first_seen": sr.published,
#             "last_seen": sr.fetched_at,
#             "topics": [],
#             "meta": {"final_url": str(sr.final_url or "")}
#         }])                                        # :contentReference[oaicite:21]{index=21}
#         db.complete_work("scrape", j["work_key"])  # :contentReference[oaicite:22]{index=22}
#         ok += 1
#     except Exception as e:
#         db.fail_work("scrape", j["work_key"], str(e))  # :contentReference[oaicite:23]{index=23}
#         fail += 1
# # optionally log run stats
