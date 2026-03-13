create table if not exists articles (
  article_id text primary key,
  slug text unique not null,
  status text not null check (status in ('draft','ready','published','archived')),
  lang text not null,
  headline text not null,
  dek text,
  body_html text not null,
  topic text not null,
  tags text[] not null default '{}',
  citations jsonb not null default '[]',
  first_seen_at timestamptz not null,
  published_at timestamptz,
  cluster_id text,
  version int not null default 1,
  meta jsonb not null default '{}'
);

create index if not exists idx_articles_status on articles (status);
create index if not exists idx_articles_topic_pub on articles (topic, published_at desc);
create index if not exists idx_articles_pub on articles (published_at desc);
create index if not exists idx_articles_tags on articles using gin (tags);
