# news_enrich runbook (PR4e owner module)

## Purpose
Establish `apps/news_enrich` as source-of-truth for scrape/enrich implementation with compatibility-safe wrappers.

## Source-of-truth modules
- `src/news_enrich/scrape_enrich.py`
- `src/news_enrich/worker_scrape.py`
- `src/news_enrich/requeue_failed.py`
- `src/news_enrich/replay_job.py`
- `src/news_enrich/scrape_contents_legacy.py`
- `src/news_enrich/db.py`
- `src/news_enrich/io.py`

## Compatibility wrappers
- `scripts/06_scrape_enrich.py` -> `news_enrich.scrape_enrich.main`
- `scripts/worker_scrape.py` -> `news_enrich.worker_scrape.main`
- `scripts/requeue_failed.py` -> `news_enrich.requeue_failed.main`
- `scripts/replay.job.py` -> `news_enrich.replay_job.main`
- `legacy/06_scrape_contents.py` -> `news_enrich.scrape_contents_legacy.main`

## Operator entrypoint

```bash
apps/news_enrich/entrypoints/run_enrich_owner.sh
```

Examples:

```bash
MODE=worker apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
MODE=batch apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
MODE=requeue ARGS='--stage scrape --key ABC' apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
```

## Constraints respected
- No behavior redesign; import/path rewiring only.
- No PromptFlow changes.
- No contract changes.
- No deletion of compatibility entrypoints.
