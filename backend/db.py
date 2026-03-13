# backend/db.py
import os, json, psycopg
from typing import Iterable

def get_conn():
    dsn = os.getenv("PG_DSN", "dbname=newsdb")
    return psycopg.connect(dsn)

def upsert_master_ref(rows: Iterable[dict]):
    sql = """
    insert into master_ref (index_id, source, link, first_seen, last_seen, topics, meta)
    values (%(index_id)s, %(source)s, %(link)s, %(first_seen)s, %(last_seen)s, %(topics)s, %(meta)s::jsonb)
    on conflict (index_id) do update set
      last_seen = excluded.last_seen,
      topics    = (select array(select distinct unnest(master_ref.topics || excluded.topics))),
      meta      = master_ref.meta || excluded.meta;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()

def push_work(stage: str, work_key: str, payload: dict):
    sql = """
    insert into work_items(stage, work_key, state, payload)
    values (%s,%s,'queued',%s)
    on conflict (stage, work_key) do nothing;
    """
    with get_conn() as c, c.cursor() as cur:
        cur.execute(sql, (stage, work_key, json.dumps(payload)))

def pop_work(stage: str, limit: int = 10):
    sql = """
    update work_items wi set state='running', attempts=wi.attempts+1, updated_at=now()
    where (stage,state)=(%s,'queued')
    returning stage, work_key, payload;
    """
    with get_conn() as c, c.cursor() as cur:
        cur.execute(sql, (stage,))
        rows = cur.fetchmany(limit)
        return [{"stage": r[0], "work_key": r[1], "payload": r[2]} for r in rows]

def complete_work(stage: str, work_key: str):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("update work_items set state='done', updated_at=now() where stage=%s and work_key=%s",
                    (stage, work_key))

def fail_work(stage: str, work_key: str, err: str):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("update work_items set state='failed', last_error=%s, updated_at=now() where stage=%s and work_key=%s",
                    (err, stage, work_key))

def start_run(run_id: str, stage: str, meta: dict):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("insert into runs(run_id,stage,started_at,meta) values (%s,%s,now(),%s::jsonb)",
                    (run_id, stage, json.dumps(meta)))

def finish_run(run_id: str, ok: int, fail: int):
    with get_conn() as c, c.cursor() as cur:
        cur.execute("update runs set finished_at=now(), ok_count=%s, fail_count=%s where run_id=%s",
                    (ok, fail, run_id))
