# PR4c runbook: acquire implementation migrated under apps/news_acquire

## Decision
Acquire implementation source-of-truth is moved to `apps/news_acquire/src/news_acquire/*`.

## What changed
- Migrated stage implementations:
  - `stage01_digests.py`
  - `stage02_master_index_update.py`
  - `stage03_headlines_digests.py`
- Migrated acquire helpers:
  - `ids.py`, `io.py`, `db.py`
- Kept runtime compatibility by turning legacy stage modules into thin wrappers delegating to the new module paths.

## Runtime safety
- `make s01/s02/s03` unchanged.
- `bin/run_hour.sh` unchanged.
- No business-logic redesign; migration focused on physical ownership and import rewiring.

## Validation checks
```bash
python -m py_compile apps/news_acquire/src/news_acquire/*.py legacy/stage01_digests.py legacy/stage02_master_index_update.py legacy/stage03_headlines_digests.py
python -m pytest -q tests/test_export_pr3a_buses.py contracts/tests/test_contracts.py
```
