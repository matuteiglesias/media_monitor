# PR4d runbook: editorial implementation migrated under apps/news_editorial

## Decision
Editorial implementation source-of-truth is moved to `apps/news_editorial/src/news_editorial/*`.

## What changed
- Migrated stage implementations:
  - `stage04_promptflow_run.py`
  - `stage05_explode_pf_outputs.py`
- Migrated editorial helpers required by these stages:
  - `ids.py`, `io.py`, `db.py`, `slugs.py`
- Rewired migrated stage imports to local package modules.
- Kept runtime compatibility by converting legacy stage modules into thin wrappers:
  - `legacy/stage04_promptflow_run.py`
  - `legacy/stage05_explode_pf_outputs.py`

## Flow path handling
- `flow/` remains at repository root in this PR to avoid runtime risk.
- Ownership is editorial; physical move is deferred until a dedicated low-risk change.

## Runtime safety
- `make s04/s05` unchanged.
- `bin/run_hour.sh` unchanged.
- PromptFlow behavior unchanged (no connection/runtime provisioning changes).
- No contract/schema changes.

## Validation checks
```bash
python -m py_compile apps/news_editorial/src/news_editorial/*.py legacy/stage04_promptflow_run.py legacy/stage05_explode_pf_outputs.py
python -m pytest -q tests/test_export_pr3a_buses.py contracts/tests/test_contracts.py
```
