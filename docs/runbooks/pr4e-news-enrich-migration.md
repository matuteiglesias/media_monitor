# PR4e runbook: enrich implementation migrated under apps/news_enrich

## Decision
Enrich implementation source-of-truth is moved to `apps/news_enrich/src/news_enrich/*`.

## What changed
- Migrated enrich/scrape implementations from script/legacy paths into app-owned module paths.
- Added app-owned copies of required helper modules (`db.py`, `io.py`) for local imports.
- Converted previous script/legacy entrypoints into thin compatibility wrappers.

## Compatibility preserved
- Existing commands still resolve through wrappers:
  - `python scripts/06_scrape_enrich.py`
  - `python scripts/worker_scrape.py`
  - `python scripts/requeue_failed.py`
  - `python scripts/replay.job.py`
  - `python legacy/06_scrape_contents.py`

## Runtime safety
- No queue/worker semantics redesign.
- No PromptFlow changes.
- No schema/contract changes.
- No canonical orchestration rewiring.

## Validation checks
```bash
python -m py_compile apps/news_enrich/src/news_enrich/*.py scripts/06_scrape_enrich.py scripts/worker_scrape.py scripts/requeue_failed.py scripts/replay.job.py legacy/06_scrape_contents.py
python -m pytest -q tests/test_export_pr3a_buses.py contracts/tests/test_contracts.py
```
