# news_acquire runbook (PR4a owner module)

## Purpose
`apps/news_acquire` is now the explicit **owner module** for acquisition runtime boundaries.

PR4a establishes ownership and entrypoints while preserving backward-compatible legacy wrappers.

## Scope owned by news_acquire

### Raw paths owned
- `data/rss_slices/rss_dumps/*`
- `data/digest_map/*`
- `data/digest_jsonls/*`
- `data/master_ref.csv` (preferred canonical source)
- `data/master_index.csv` (fallback source when `master_ref` is missing/empty)
- `data/quarantine/*` for acquisition stage fallout (`V01`, `V02`, `V03`)

### Buses written
- `storage/buses/news_ref/v1/*` via `scripts/export_pr3a_buses.py`
- `storage/buses/news_digest_group/v1/*` via `scripts/export_pr3a_buses.py`

### Indexes written
- `storage/indexes/pr3a_exports_latest.json`
- `storage/indexes/pr3a_exports_<DIGEST_AT>_<EXPORT_AT>.json`

### Seams consumed
- Owner stage outputs from:
  - `make s01` -> `apps.news_acquire.src.news_acquire.stage01_digests`
  - `make s02` -> `apps.news_acquire.src.news_acquire.stage02_master_index_update`
  - `make s03` -> `apps.news_acquire.src.news_acquire.stage03_headlines_digests`
- Contract schemas:
  - `contracts/schemas/news_ref.v1.json`
  - `contracts/schemas/news_digest_group.v1.json`


## Implementation source of truth (PR4c)
- `apps/news_acquire/src/news_acquire/stage01_digests.py`
- `apps/news_acquire/src/news_acquire/stage02_master_index_update.py`
- `apps/news_acquire/src/news_acquire/stage03_headlines_digests.py`
- `apps/news_acquire/src/news_acquire/{ids,io,db}.py`

Legacy modules remain as thin compatibility wrappers:
- `legacy/stage01_digests.py`
- `legacy/stage02_master_index_update.py`
- `legacy/stage03_headlines_digests.py`

## Operator entrypoint (owner wrapper)
Use:

```bash
apps/news_acquire/entrypoints/run_acquire_owner.sh
```

This wrapper delegates to canonical make targets:

1. `make s01`
2. `make s02`
3. `make s03`
4. `make export-pr3a` (unless `RUN_EXPORTS=0`)

### Useful examples

```bash
# Normal run
DIGEST_AT=20260313T15 apps/news_acquire/entrypoints/run_acquire_owner.sh

# Show commands only
DIGEST_AT=20260313T15 apps/news_acquire/entrypoints/run_acquire_owner.sh --dry-run

# Skip PR3a export phase
DIGEST_AT=20260313T15 RUN_EXPORTS=0 apps/news_acquire/entrypoints/run_acquire_owner.sh
```

## Constraints (explicit)
- Does **not** replace `bin/run_hour.sh`.
- Does **not** replace `make s01..s05`.
- Does **not** delete or move `legacy/*`.
- Does **not** modify PromptFlow logic.

## Failure/no-op behavior
- If legacy inputs are missing, legacy stages keep their current behavior.
- PR3a exporter writes explicit noop statuses in indexes/run records when inputs are missing.
- Schema violations fail fast in exporter validation.
