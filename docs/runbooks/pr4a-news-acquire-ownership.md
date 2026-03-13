# PR4a runbook: news_acquire ownership established

## Decision
`apps/news_acquire` becomes the explicit owner module for acquisition boundaries and PR3a stable export surfaces.

## Why now
PR3a already materializes real buses and indexes. PR4a makes ownership and operator entrypoints explicit without changing runtime architecture.

## What changed
- `apps/news_acquire/README.md` now documents real ownership.
- `apps/news_acquire/runbook.md` defines owned raw paths, buses, indexes, consumed seams, and constraints.
- `apps/news_acquire/entrypoints/run_acquire_owner.sh` provides an additive owner wrapper:
  - `make s01`
  - `make s02`
  - `make s03`
  - `make export-pr3a` (optional)

## Runtime safety
- `bin/run_hour.sh` unchanged.
- `make s01..s05` unchanged.
- `legacy/*` unchanged.
- PromptFlow logic unchanged.

## Operator quick checks

```bash
bash -n apps/news_acquire/entrypoints/run_acquire_owner.sh
apps/news_acquire/entrypoints/run_acquire_owner.sh --dry-run
```

