-- Observability: one row per execution
create table if not exists runs (
  run_id text primary key,
  stage text not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  ok_count int not null default 0,
  fail_count int not null default 0,
  meta jsonb not null default '{}'
);

create index if not exists runs_stage_time_idx on runs (stage, started_at desc);


