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

## Sensing side-effect controls

The minimal sensing loop and acquisition stages expose independent controls:

| Environment variable | Default | Effect |
|---|---:|---|
| `ACQUIRE_NETWORK` | `1` unless `DRY_RUN=1` | Fetch configured RSS sources. |
| `WRITE_ARTIFACTS` | `1` | Write acquisition CSV/JSONL/Markdown and quarantine artifacts. |
| `ENQUEUE_SCRAPE` | `1` unless `DRY_RUN=1` | Enqueue scrape work for acquired valid rows. |
| `DB_RUN_BOOKKEEPING` | `0` | Start/finish Postgres stage runs and upsert stage-02 master state. When enabled, DB errors fail the stage instead of being silently suppressed. |
| `SENSING_FEED_CONFIG` | `config/sensing_feeds.v1.yaml` | Select the validated `sensing_feeds.v1` configuration. |

`DRY_RUN=1` remains a compatibility shortcut for `ACQUIRE_NETWORK=0` and
`ENQUEUE_SCRAPE=0`; explicit controls override it. Artifact writes remain enabled
for compatibility. The outer minimal-loop orchestrator is the authoritative
writer of the consolidated sensing run record, lane-latest, and summary status;
child wrappers retain per-command logs and manifests only.

## Immutable local run bundle

Run one isolated sensing attempt with:

```bash
make sensing-bundle DIGEST_AT=20260729T00 RUN_ROOT=artifacts/sensing_runs
```

Each attempt gets a unique `run_id` and finalizes under
`<run-root>/runs/<run-id>/`. The finalized bundle contains the feed and input
state snapshot, stage outputs, exported contract buses, candidate state/indexes,
stage logs/results, checksums, a run record, and a manifest. Failed attempts are
also finalized as diagnostic bundles and the command exits non-zero. Finalized
run IDs cannot be overwritten, including retries for the same `DIGEST_AT`.

No filename containing `latest` is published inside a bundle. Run the sole
compactor to validate bundles, select attempts, and publish canonical state:

```bash
make compact-sensing-bundles RUN_ROOT=artifacts/sensing_runs STATE_ROOT=storage/sensing_compacted
```

Canonical generations are immutable beneath `STATE_ROOT/generations/`; consumers
select the complete generation through the atomically replaced
`STATE_ROOT/current.json` pointer. If legacy local consumers still need the old
paths, mirror only the compactor-selected generation afterward:

```bash
make promote-sensing-bundle-local SENSING_STATE_ROOT=storage/sensing_compacted
```

The compatibility command cannot select a run bundle and is not a compactor.

## AWS task adapter (no infrastructure)

Build the sensing-only image with `Dockerfile.sensing`. Its entrypoint requires
`DIGEST_AT`, `SENSING_S3_BUCKET`, `SOURCE_COMMIT`, and `IMAGE_DIGEST`; optional
settings include `SENSING_S3_PREFIX`, `RUN_ID`, `ATTEMPT`, and a timeout no larger
than 900 seconds. The producer uploads only
`<prefix>/runs/<run_id>/` and writes `FINALIZED` last.

The separately invoked `scripts/run_sensing_compactor_task.py` lists finalized
run prefixes, executes the accepted deterministic compactor, uploads immutable
`<prefix>/compacted/<generation>/` objects, and replaces
`<prefix>/latest/current.json` last. Role and resource expectations are frozen in
`06_aws_task_adapter_contract_v0_1.md`; Terraform remains PR-A5 work.

## Constraints (explicit)
- Does **not** replace `bin/run_hour.sh`.
- Does **not** replace `make s01..s05`.
- Does **not** delete or move `legacy/*`.
- Does **not** modify PromptFlow logic.

## Failure/no-op behavior
- If legacy inputs are missing, legacy stages keep their current behavior.
- PR3a exporter writes explicit noop statuses in indexes/run records when inputs are missing.
- Schema violations fail fast in exporter validation.
