# PR5 design memo: observability-first prep (KB-compatible)

## Goal

Prepare `media_monitor` to emit stable producer-side execution telemetry that can be compacted by a **single writer** into UI-facing indexes, without making UI/indexes the source-of-truth.

## Operating model

- Producers emit run records + pointers (manifest/log).
- Aggregator compacts producer outputs into canonical UI indexes.
- UI stays read-only over compact indexes only.
- Rebuild remains possible from ground truth (bus + run records + manifests).


## Producer emission location (explicit boundary)

Producer artifacts should live under `storage/observability/` (not final-looking index paths):

- `storage/observability/run_records.jsonl`
- `storage/observability/manifests/`
- `storage/observability/logs/`
- `storage/observability/status/<lane>_latest.json`

`storage/indexes/` is reserved for compacted/indexed views produced by a dedicated single-writer aggregator.

## Canonical UI-facing index target (v0.1)

- `projects.csv`
- `runs.jsonl`
- `corpora_daily.jsonl`
- `refresh.json`

This repo should **prepare producer-side emissions**, not implement a full UI platform.

## Minimal run telemetry contract for this repo

Each relevant execution should emit a run record with at least:

- `run_id`
- `project_id`
- `operator`
- `started_at`
- `ended_at`
- `status`
- `error_code`
- `inputs_count`
- `outputs_count`
- `manifest_path`
- `log_path`

## Emission points in media_monitor

Recommended emission points (incremental):

1. Stage-level wrapper execution (`make s01..s05` via wrapper script).
2. Owner entrypoints in `apps/*/entrypoints/`.
3. Export jobs (`scripts/export_pr3a_buses.py`) as first-class observable runs.

## Internal-only vs public surfaces

Public/contract candidate outputs:

- versioned buses under `storage/buses/*`
- compacted indexes (aggregator-managed)

Internal-only outputs (not public contracts):

- `data/pf_out/*`
- quarantine folders
- queue internals / work items tables
- ad-hoc draft intermediates not promoted to a contract

## Corpus deltas stance

Near-term recommendation:

- Support both ingestion modes at aggregator boundary (if needed):
  1) dedicated `corpus_deltas` stream, or
  2) deltas embedded in run records.
- Freeze one canonical mode once producers are stable.

For this repo now: postpone mandatory `corpus_deltas` emission until run records are consistently emitted.

## Refresh marker

Proposed `refresh.json` producer/aggregator fields:

- `refreshed_at` (UTC ISO8601)
- `sources` (array of producer names/paths)
- `runs_count`
- `corpora_rows`


## Minimal health semantics (producer-side)

Lane health states are computed from `last_success_at` age with conservative defaults:

- `sensing`: healthy <= 2h, degraded <= 6h, else down
- `editorial`: healthy <= 12h, degraded <= 24h, else down
- `enrich`: healthy <= 12h, degraded <= 48h, else down

Producer status snapshots should share one shape across lanes and feed a small rolling summary at
`storage/observability/status/summary.json` for quick operational checks.

## Guardrails

- No multi-writer append to shared compact indexes.
- No UI reads over repo trees or raw BUS directories.
- No conversion of indexes into source-of-truth.
- No exposure of PF raw output as public bus.

## Minimal implementation path

1. Add small shared wrapper that runs commands and always appends run records in `finally` semantics.
2. Write per-run manifest/log pointers.
3. Keep compaction to UI indexes outside producer runtime (single writer).
