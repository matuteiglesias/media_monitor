# PR6 wrapper surface inventory (runtime-guided pruning)

Objetivo: reducir entrypoints que compiten con la ruta real sin romper continuidad.

## Canonical operational shortlist (run this first)

- `bin/run_minimal_loop_once.sh --lane sensing`
- `bin/run_minimal_loop_once.sh --lane editorial`
- `bin/run_minimal_loop_once.sh --lane enrich`
- `make s01|s02|s03|s04|s06|s05`
- `make export-pr3a`
- `make build-news-access-indexes`
- `make build-editorial-access-indexes`

## Wrapper and helper classification

### Keep active (compatibility or runtime support)

- `legacy/stage01_digests.py` (compat)
- `legacy/stage02_master_index_update.py` (compat)
- `legacy/stage03_headlines_digests.py` (compat)
- `legacy/stage04_promptflow_run.py` (compat)
- `legacy/stage05_explode_pf_outputs.py` (compat)
- `legacy/stage06_build_piece_briefs.py` (compat)
- `scripts/06_scrape_enrich.py` (compat wrapper)
- `scripts/worker_scrape.py` (compat wrapper)
- `scripts/requeue_failed.py` (compat wrapper)
- `scripts/replay.job.py` (compat wrapper)
- `scripts/export_pr3a_buses.py` (runtime-support)
- `scripts/build_news_access_indexes.py` (runtime-support)
- `scripts/build_editorial_access_indexes.py` (runtime-support)

### Archived historical (preserved, not canonical)

- `scripts/archive/historical/03_headlines_digests.py`
- `scripts/archive/historical/04_promptflow_run.py`
- `scripts/archive/historical/05_explode_pf_outputs.py`

### Safe to unplug candidate (needs explicit runtime evidence window)

- `scripts/01_emit_scrape_seed.py` (ad-hoc seed helper; no canonical references)
- `scripts/generator.py` (ad-hoc generation helper; no canonical references)
- `scripts/meili_bootstrap.py` (future integration helper)

## Policy

- No deletions without runtime evidence (`cron/systemd/make/bin` refs + recent execution evidence).
- Canonical commands above are the only ones expected in day-to-day operation.
- Historical scripts stay archived to keep migration traceability.
