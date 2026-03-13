# news_enrich (PR4e owner module)

`apps/news_enrich` is the explicit owner module for scrape/enrich runtime implementation.

This PR migrates enrich source-of-truth into `apps/news_enrich/src/news_enrich` while preserving compatibility entrypoints.

## Ownership declaration

### Owned implementation (source of truth)
- `apps/news_enrich/src/news_enrich/scrape_enrich.py`
- `apps/news_enrich/src/news_enrich/worker_scrape.py`
- `apps/news_enrich/src/news_enrich/requeue_failed.py`
- `apps/news_enrich/src/news_enrich/replay_job.py`
- `apps/news_enrich/src/news_enrich/scrape_contents_legacy.py`
- `apps/news_enrich/src/news_enrich/{db,io}.py`

### Compatibility entrypoints kept
- `scripts/06_scrape_enrich.py`
- `scripts/worker_scrape.py`
- `scripts/requeue_failed.py`
- `scripts/replay.job.py`
- `legacy/06_scrape_contents.py`

All compatibility files are thin wrappers delegating to app-owned implementation.

## Entrypoint
Use owner wrapper:

```bash
apps/news_enrich/entrypoints/run_enrich_owner.sh
```

Supports modes: `worker`, `batch`, `requeue`, `replay`.

## Non-goals in PR4e
- No queue semantics redesign.
- No PromptFlow changes.
- No contract/schema changes.
- No orchestration rewiring in `bin/run_hour.sh`.
