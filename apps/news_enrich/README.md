# news_enrich

`apps/news_enrich` owns article-text enrichment for known news references.

## Doctrine

`news_enrich` is responsible for fetching, normalizing, and recording full article text for known article references. It consumes article references and enrich requests, then emits structured scraped-article records and status evidence for downstream systems.

The module does **not** own acquisition, topic grouping, editorial generation, publication, or site rendering.

## Current PR-E4 boundary

PR-E4 keeps the validated bus seam and adds a compact enrich status index without redesigning the queue:

```text
input: EnrichRequest(index_id + url + optional source metadata)
runtime: fetch URL with requests, normalize text/plain, record fetch evidence
output: schema-valid scraped_article.v1 record appended to storage/buses/scraped_article/v1, with data/scrape as an optional Level-0 mirror
```

The public service boundary is:

- `apps/news_enrich/src/news_enrich/requests.py` — `EnrichRequest`
- `apps/news_enrich/src/news_enrich/records.py` — `ScrapedArticle`
- `apps/news_enrich/src/news_enrich/service.py` — `enrich_one(request)`
- `apps/news_enrich/src/news_enrich/bus_writer.py` — schema validation + `scraped_article.v1` bus append
- `apps/news_enrich/src/news_enrich/cli.py` — `enrich-one` command

The canonical manual command is:

```bash
python -m news_enrich.cli enrich-one --index-id X --url URL
```

By default, the command appends exactly one schema-valid bus record to:

```text
storage/buses/scraped_article/v1/scraped_article_YYYY-MM-DD.jsonl
```

It also preserves the previous Level-0 runtime output as a mirror at:

```text
data/scrape/YYYY-MM-DD.enriched.jsonl
```

Use `--bus-output <path>` for smoke tests or targeted bus paths, `--scrape-output <path>` for a targeted mirror, or `--no-scrape-mirror` to disable the mirror.

## Runtime modes

`news_enrich` can run as:

- manual/on-demand CLI (`python -m news_enrich.cli enrich-one ...`)
- batch queue consumer (`apps/news_enrich/src/news_enrich/scrape_enrich.py`)
- PostgreSQL worker (`apps/news_enrich/src/news_enrich/worker_scrape.py`)
- recovery helpers (`requeue_failed.py`, `replay_job.py`)

PR-E3 makes the PostgreSQL worker delegate to the same `enrich_one` service and write schema-validated `scraped_article.v1` bus records while preserving existing retry/backoff semantics. Recovery commands remain unchanged.

## Existing compatibility entrypoints

Compatibility wrappers remain available and delegate to app-owned implementation:

- `scripts/compat_wrappers/06_scrape_enrich.py`
- `scripts/compat_wrappers/worker_scrape.py`
- `scripts/compat_wrappers/requeue_failed.py`
- `scripts/compat_wrappers/replay.job.py`
- `legacy/code/06_scrape_contents.py`

## Future target shape

The current PR promotes enrich output into the Level 1 contract bus:

```text
storage/buses/scraped_article/v1/*.jsonl
```

The current PR also builds the Level 2 enrich access/status index:

```text
storage/indexes/enrich_latest.json
```

Build it with:

```bash
make build-enrich-access-indexes
```

Downstream consumers should prefer `enrich_latest.json` for health/status and the `scraped_article.v1` bus for full records. Treat `data/scrape/*.enriched.jsonl` as an optional Level-0 mirror rather than a public artifact.
