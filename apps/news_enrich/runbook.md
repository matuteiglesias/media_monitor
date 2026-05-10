# news_enrich runbook

## Purpose

`news_enrich` fetches article text on demand for known article references. It consumes an `EnrichRequest`, calls the shared `enrich_one` service, and writes a schema-valid `scraped_article.v1` record.

It does not own acquisition, editorial decisions, publication, or site rendering.

## PR-E4 operating contract

Input shape:

```text
index_id + url + optional title/source/topic/digest_at/priority metadata
```

Service boundary:

```python
from news_enrich.requests import EnrichRequest
from news_enrich.service import enrich_one

record = enrich_one(EnrichRequest(index_id="X", url="https://example.com/article"))
```

Output shape:

```text
schema_name: scraped_article.v1
schema_status: experimental
fetch_status: success|failed|blocked|empty|timeout
text/text_hash/byte_size/char_count/fetched_at/error evidence
```

Primary bus output location:

```text
storage/buses/scraped_article/v1/scraped_article_<UTC-day>.jsonl
```

This is the Level 1 contract bus. The previous `data/scrape/<UTC-day>.enriched.jsonl` path remains available as an optional Level-0 mirror.

## Manual enrich-one

Write to the default bus and Level-0 mirror:

```bash
python -m news_enrich.cli enrich-one --index-id TEST123 --url https://example.com
```

Write to test-specific bus and mirror files:

```bash
python -m news_enrich.cli enrich-one \
  --index-id TEST123 \
  --url https://example.com \
  --title "Example" \
  --source "Example.com" \
  --bus-output data/_tmp/scraped_article_smoke.jsonl \
  --scrape-output data/_tmp/enrich_smoke.jsonl
```

The command validates the record against `contracts/schemas/scraped_article.v1.json`, prints the same record it appends, and prints the bus path for quick inspection.

## Batch mode

The batch runner still consumes existing `scrape` work items and keeps the current queue completion/failure behavior:

```bash
python -m apps.news_enrich.src.news_enrich.scrape_enrich
```

For each job, it builds an `EnrichRequest` from queue payload conventions (`url`, `link`, or `original_link`) and delegates fetching/normalization to `enrich_one`, validates the result, writes the bus record, and then writes the optional `data/scrape` mirror.


## Worker mode

The PostgreSQL worker is still one execution mode over the existing `work_items` table. It now delegates each queued `scrape` job to the same service path as the CLI and batch runner:

```text
work_items(stage=scrape) -> EnrichRequest -> enrich_one -> scraped_article.v1 bus + data/scrape mirror
```

`fetch_status=success` marks the work item `done`. Non-success service results and exceptions keep the existing retry/backoff behavior by requeueing through `mark_fail`.

Dry-run the owner wrapper command selection without requiring PostgreSQL or network access:

```bash
MODE=worker apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
```

This should print:

```text
+ python -m apps.news_enrich.src.news_enrich.worker_scrape
```

## Enrich access/status index

Build the compact status index from the `scraped_article.v1` bus:

```bash
make build-enrich-access-indexes
```

The target writes:

```text
storage/indexes/enrich_latest.json
```

The index includes total/24h metrics, latest successes, latest failures, retry candidates, and top failing sources. It is intended as the quick health/read model for other operators and consumers.

## Operator wrapper

The owner wrapper remains the operational front door:

```bash
apps/news_enrich/entrypoints/run_enrich_owner.sh
```

Examples:

```bash
MODE=batch apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
MODE=worker apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
MODE=requeue ARGS='--stage scrape --key ABC' apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
```

## Non-goals in PR-E4

- No PostgreSQL queue semantics redesign.
- No Playwright/Selenium promotion.
- No direct editorial coupling to fetchers.
