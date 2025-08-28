Good—let’s turn this into a tight, execution-ready sprint. You’ll keep your Python pipeline, drop Sanity from Stablo, stand up a thin read API, add a robust fetcher, and ship a public site. I’ll lay out **scope tiers**, a **workplan**, **infra choices with Apache**, and **acceptance criteria**—plus the sharp edges you’ll hit.

# Sprint goal (and two fallback levels)

* **Target**: automated news site live, with hourly ingestion → synthesis → publish → website render (ISR + revalidation).
* **Plan B (acceptable)**: site live pulling from API, manual/limited publish path; automation runs for a subset of topics.
* **Plan C (still useful)**: static site showing articles ingested from your legacy artifacts; API and fetcher wired; publishing manual.

# Roles (even if it’s you wearing all hats)

* **Pipeline** (Python): ingestion/digest/synthesis, scraper, publisher.
* **API** (FastAPI): read endpoints; internal publish endpoint.
* **Web** (Next.js/Stablo): strip Sanity, connect to API, ISR + revalidation.
* **Infra/Ops**: Postgres + Meilisearch; Apache reverse proxy + TLS; systemd services and logs.

---

## Architecture you’ll ship this sprint

* **DB**: Postgres (Neon or local VM). Tables: `articles`, `citations`.
* **Search**: Meilisearch (or Typesense) for `/search` and fast filters.
* **API**: FastAPI (uvicorn) read endpoints + internal `POST /publish` (calls Next.js revalidate).
* **Web**: Next.js (Stablo UI without Sanity). ISR (e.g., 120s). `POST /api/revalidate`.
* **Pipeline**: your existing stages + (a) canonical URL resolver, (b) extractor (requests→trafilatura→Playwright fallback), (c) QA gates, (d) publisher writing to DB & search, then hitting revalidate.

---

## Workplan (3–5 days of focused work)

### Day 1 — Contracts & storage

1. **IDs & models**

   * Add `stable_index_id(title, source, url)`; unify `digest_id_hour=YYYYMMDDTHH`.
   * Introduce Pydantic models: `ScrapeRecord`, `ArticleDraft`, `Article`.
2. **DB & search**

   * Postgres schema:

     ```sql
     create table articles (
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
     create index on articles (status);
     create index on articles (topic, published_at desc);
     create index on articles using gin (tags);
     ```
   * Meilisearch index `articles` with fields: `id, slug, headline, dek, topic, tags, published_at, lang`.

### Day 2 — API & publisher

3. **FastAPI**

   * Public:

     * `GET /v1/articles?page=&limit=&topic=&tag=&lang=` → teasers + pagination
     * `GET /v1/articles/{slug}` → full article (only `status='published'`)
     * `GET /v1/search?q=&page=&limit=&topic=` → proxy to Meilisearch
   * Internal:

     * `POST /internal/articles` (upsert draft/ready)
     * `POST /internal/articles/{id}/publish` → set `published`, push to search, POST to Next `/api/revalidate` with `["/", "/tema/{topic}", "/articulo/{slug}"]`
4. **Publisher step (Python)**

   * Take validated `ArticleDraft` → `Article` row → push to DB → push to search → call revalidate webhook.
   * Idempotent upsert by `slug`/`article_id`.

### Day 3 — Web (Stablo without Sanity)

5. **Strip Sanity**

   * Remove `lib/sanity/*`, GROQ, Sanity deps.
   * Replace data calls with fetches to your API:

     * `/` → `GET /v1/articles`
     * `/articulo/[slug]` → `GET /v1/articles/{slug}`
     * `/tema/[topic]` → `GET /v1/articles?topic=...`
     * `/search` (basic) → `GET /v1/search?q=...`
   * Add ISR on pages (`export const revalidate = 120;`).
6. **Revalidation endpoint (Next)**

   * `POST /api/revalidate` with `REVALIDATE_SECRET`, call `revalidatePath` for paths in payload.

### Day 4 — Scraper & QA gates

7. **Fetcher**

   * Resolve Google News redirect → `final_url`.
   * `requests` + `trafilatura` (fast path). If `main_text_len < threshold` / odd status → **Playwright** fallback (`page.content()` then extract).
   * Pydantic-validate to `ScrapeRecord`; write JSONL.
8. **QA gates**

   * Input: `main_text_len ≥ 1200`, `lang in {'es','en'}`, domain allow-list, canonical present.
   * Draft: headline length ≤ 90, at least 2 distinct citations, no empty `<p>`.
   * Publish only if gates pass.

### Day 5 — Wiring, deploy, smoke tests

9. **Apache reverse proxy**

   * You can keep Apache. Run Next.js and FastAPI as services, and proxy through Apache:

     ```apache
     # /etc/apache2/sites-available/news.conf
     <VirtualHost *:80>
       ServerName yourdomain.example
       ProxyPreserveHost On
       ProxyPass /api http://127.0.0.1:8000
       ProxyPassReverse /api http://127.0.0.1:8000
       ProxyPass / http://127.0.0.1:3000/
       ProxyPassReverse / http://127.0.0.1:3000/
     </VirtualHost>
     ```

     * Use Let’s Encrypt for TLS; then switch `<VirtualHost *:443>`.
     * If you can, prefer **Vercel** for Next.js and keep Apache for redirects; but Apache proxy works.
10. **Systemd services**

    * FastAPI (uvicorn) and Next.js (production build + `node server.js` or `next start`) supervised by systemd or PM2. Log to journald.
11. **Smoke tests**

    * Publish one article via internal endpoint → verify appears on `/` and `/articulo/slug` within ISR window or after revalidate.
    * Check `/search?q=palabra` returns expected items.

---

## Deliverables & acceptance criteria

* **API**: `GET /v1/articles`, `GET /v1/articles/{slug}`, `GET /v1/search` working against Postgres + search.
* **Website**: Stablo UI, no Sanity, pages render API data; ISR active; `/api/revalidate` secured and functional.
* **Pipeline**: scraper produces validated `ScrapeRecord`; publisher promotes draft → published, upserts DB+search, triggers revalidate.
* **Ops**: Apache proxy in front; TLS; systemd units; `.env` documented; basic runbook.

Pass if:

* Publishing a new article shows up within ≤2 minutes (ISR=120) or instantly after revalidate.
* Search returns that article by headline/keywords.
* At least one topic page paginates correctly.
* QA gate rejects a purposely short or citation-free draft.

---

## Minimal configs/snippets you’ll likely need

**Next.js service (systemd)**

```ini
# /etc/systemd/system/next.service
[Unit]
Description=Next.js
After=network.target

[Service]
WorkingDirectory=/srv/news-web
Environment=NODE_ENV=production
Environment=NEWS_API=https://yourdomain.example/api
Environment=REVALIDATE_SECRET=...
ExecStart=/usr/bin/npm run start -- --port 3000
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

**FastAPI service (systemd)**

```ini
# /etc/systemd/system/news-api.service
[Unit]
Description=News API (FastAPI)
After=network.target

[Service]
WorkingDirectory=/srv/news-api
Environment=DATABASE_URL=postgres://...
Environment=MEILI_URL=http://127.0.0.1:7700
Environment=MEILI_KEY=...
Environment=NEXT_REVALIDATE_URL=https://yourdomain.example/api/revalidate
Environment=REVALIDATE_SECRET=...
ExecStart=/usr/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

**Publisher revalidate call (Python)**

```python
import requests, os
def revalidate(paths: list[str]):
    url = os.getenv("NEXT_REVALIDATE_URL")
    secret = os.getenv("REVALIDATE_SECRET")
    requests.post(url, json={"secret": secret, "paths": paths}, timeout=10)
```

---

## Risks & mitigation

* **Apache only hosting**: Next.js needs Node; proxying through Apache is fine. If constraints bite (memory, PM2 flakiness), move web to Vercel and keep API behind your server.
* **Playwright headless on server**: install dependencies (Chromium). Keep it as fallback only to control CPU/RAM.
* **ISR confusion**: without revalidation you wait for cache to expire. Ensure publisher calls revalidate immediately on publish.
* **Data drift**: enforce Pydantic at write time; refuse invalid JSONL; log quarantined items.

---

## What not to overbuild this sprint

* Full editorial CMS, user auth, comments.
* Fancy personalization or per-user feeds.
* Multi-region deployment.

Get the pipeline publishing, the API serving, the site rendering, and the revalidation firing. That’s the kernel of a durable system.

If you want, I can produce a **file-by-file checklist** for the Stablo fork (which files to delete/edit) and a **Docker Compose** with Postgres + Meilisearch to get local parity fast.
