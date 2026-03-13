-- Flat index of seen sources keyed by index_id
create table if not exists master_ref (
  index_id text primary key,
  source text not null,
  link text not null,
  first_seen timestamptz not null,
  last_seen  timestamptz not null,
  topics text[] not null default '{}',
  meta jsonb not null default '{}'
);

create index if not exists master_ref_last_seen_desc on master_ref (last_seen desc);
