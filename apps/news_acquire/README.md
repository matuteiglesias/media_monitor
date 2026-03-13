# news_acquire (PR4a owner module)

`apps/news_acquire` is the **first operational owner module** in the monorepo transition.

It owns acquisition-related raw boundaries and stable export surfaces, while keeping the legacy runtime path intact.

## Ownership declaration

### Owns raw acquisition boundaries
- `data/rss_slices/rss_dumps/*`
- `data/digest_map/*`
- `data/digest_jsonls/*`
- `data/master_ref.csv` (preferred seam)
- `data/master_index.csv` (fallback seam)
- `data/quarantine/*` for acquisition-stage fallout

### Owns buses/indexes publication for PR3a surfaces
- `news_ref.v1` -> `storage/buses/news_ref/v1/*`
- `news_digest_group.v1` -> `storage/buses/news_digest_group/v1/*`
- summarized index -> `storage/indexes/pr3a_exports_*.json`

### Consumes
- Legacy acquisition stages (`s01`, `s02`, `s03`) via existing make targets.
- Contract schemas under `contracts/schemas/` for validation.


## Implementation location (PR4c)
Acquire primary implementation now lives under:
- `apps/news_acquire/src/news_acquire/stage01_digests.py`
- `apps/news_acquire/src/news_acquire/stage02_master_index_update.py`
- `apps/news_acquire/src/news_acquire/stage03_headlines_digests.py`
- `apps/news_acquire/src/news_acquire/{ids,io,db}.py`

`legacy/stage01..03` are kept as thin wrappers for runtime compatibility.

## Entrypoint

Use the owner wrapper:

```bash
apps/news_acquire/entrypoints/run_acquire_owner.sh
```

The wrapper orchestrates:
1. `make s01`
2. `make s02`
3. `make s03`
4. `make export-pr3a` (optional via `RUN_EXPORTS=0`)

See operational details in [`runbook.md`](./runbook.md).

## Non-goals in PR4a
- No replacement of `bin/run_hour.sh`.
- No replacement of canonical `make s01..s05` flow.
- No PromptFlow refactor.
- No ownership migration for `news_editorial` or `news_enrich` (handled in future PR4b/PR4c).
