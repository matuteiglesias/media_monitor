-- sql/003_work_items.sql
create type work_stage as enum ('scrape','generate','publish');

create table if not exists work_items (
  id           bigserial primary key,
  stage        work_stage not null,
  work_key     text not null,               -- e.g. index_id / digest_id+article_id / article_id+version
  payload      jsonb not null default '{}'::jsonb,
  state        text not null default 'queued', -- queued | running | done | failed
  attempts     int  not null default 0,
  not_before   timestamptz,                 -- backoff / scheduling
  last_error   text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create unique index on work_items (stage, work_key) where state in ('queued','running');
create index on work_items (stage, state, not_before);
create index on work_items (updated_at);

create or replace function work_items_touch() returns trigger as $$
begin
  new.updated_at := now();
  return new;
end $$ language plpgsql;

create trigger trg_work_items_touch
before update on work_items
for each row execute procedure work_items_touch();


-- insert into work_items(stage, work_key, payload, not_before)
-- values ($1, $2, $3::jsonb, coalesce($4, now()))
-- on conflict (stage, work_key)
--   where work_items.state in ('queued','running')
-- do nothing;


with c as (
  select id
  from work_items
  where stage = $1
    and state = 'queued'
    and (not_before is null or not_before <= now())
  order by created_at
  for update skip locked
  limit $2
)
update work_items w
set state='running', attempts = attempts + 1, updated_at = now()
from c
where w.id = c.id
returning w.*;


-- done
update work_items set state='done', last_error=null where id = $1;

-- failed with exponential-ish backoff (min 2m, cap 2h)
update work_items
set state='queued',
    last_error=$2,
    not_before = now() + greatest(interval '2 minutes',
                                  interval '1 minute' * power(2, least(attempts, 7)))
where id = $1;
