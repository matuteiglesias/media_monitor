# PR5 execution runbook: minimal autonomous loop (alive-first)

## Objective

Define a **small autonomous loop** that keeps the system alive with low intervention, while isolating fragile lanes.

## Lanes and cadence

### Lane 1 — Sensing (mandatory, heartbeat)

Cadence: every 60 minutes.

Entrypoint:

- `bin/run_minimal_loop_once.sh --lane sensing`

Actions:

1. `make s01`
2. `make s02`
3. `make s03`
4. `make export-pr3a`

Expected outputs:

- Fresh digest inputs/materialization in `data/`
- Stable contract export surfaces (at least PR3a seams) via `storage/buses/*`

Failure isolation:

- Sensing lane must run independently of editorial/enrich.
- Editorial failure must not block sensing runs.

### Lane 2 — Editorial batch (optional but recommended)

Cadence: every 6 hours.

Entrypoint:

- `bin/run_minimal_loop_once.sh --lane editorial`

Actions:

1. `make s04`
2. `make s06`
3. `make s05`
4. `make build-editorial-access-indexes`

Expected outputs:

- PF outputs + piece brief materialization + draft generation attempts
- Compact editorial observability index at `storage/indexes/editorial_latest.json` (includes `human_handoff` with latest briefs/drafts/yt/fallback + `action_candidates` priorizados)

Failure isolation:

- If PromptFlow/runtime connection fails, lane is marked failed but system stays alive through sensing lane.

### Lane 3 — Enrich selective (optional, queue-driven)

Cadence: every 2–6 hours or on-demand.

Entrypoint:

- `bin/run_minimal_loop_once.sh --lane enrich`

Actions:

1. `python scripts/06_scrape_enrich.py`

Expected outputs:

- Enriched scrape records for queued work items

Failure isolation:

- Enrich must never block sensing lane execution.

## Producer-side observability boundary

This loop emits **producer telemetry** to:

- `storage/observability/run_records.jsonl`
- `storage/observability/manifests/`
- `storage/observability/logs/`
- `storage/observability/status/<lane>_latest.json`

By default, run-record instrumentation is enabled only for `sensing` lane (safe-first rollout), including `export_pr3a` inside that lane.

- To instrument all lanes: `RUN_RECORD_ALL_LANES=1`

Lane snapshots now follow a common shape:

- `lane`
- `updated_at`
- `last_run_id`
- `last_started_at`
- `last_ended_at`
- `last_status`
- `last_error_code`
- `last_success_at`
- `recent_inputs_count`
- `recent_outputs_count`
- `health_state` (`healthy|degraded|down`)

A rolling summary is maintained at `storage/observability/status/summary.json` (24h window).

`storage/indexes/` remains reserved for compacted/indexed outputs managed by a single-writer aggregator.

## Health signals (minimal)

Track these five indicators:

1. Last successful sensing run timestamp.
2. New `news_ref` outputs in last 24h (or closest export proxy).
3. Last digest export timestamp.
4. Last successful editorial batch timestamp.
5. Enrich backlog trend (queued/running/failed) when DB available.

## Degradation policy

- **Sensing down**: system is not alive; page/alert immediately.
- **Editorial down only**: system degraded but alive; continue sensing.
- **Enrich down only**: system degraded but alive; continue sensing + editorial.

## Stop conditions

Pause automation and investigate if:

- No successful sensing run in > 2 cadence windows.
- Export stage repeatedly succeeds with zero outputs for multiple windows (unexpected dry flow).
- Error loop repeats with same error code for > N runs.

## Suggested scheduling examples

- Cron/systemd timers should schedule each lane independently.
- Avoid one monolithic hourly job that runs all heavy stages every tick.

Example cron sketch:

- `0 * * * * bin/run_minimal_loop_once.sh --lane sensing`
- `15 */6 * * * bin/run_minimal_loop_once.sh --lane editorial`
- `30 */3 * * * bin/run_minimal_loop_once.sh --lane enrich`

## Notes

- This runbook intentionally optimizes for continuity over perfect completeness.
- Start with sensing lane reliability; scale editorial/enrich once stable.


## Run it now (heartbeat)

If you want lines to start appearing automatically in the next hours:

```bash
make heartbeat-start INTERVAL_SEC=3600
```

Check status/log quickly:

```bash
make heartbeat-status
```

Stop it:

```bash
make heartbeat-stop
```

The heartbeat appends to:

- `storage/observability/heartbeat.log`
- `storage/observability/run_records.jsonl`
- `storage/observability/status/sensing_latest.json`
- `storage/observability/status/summary.json`
