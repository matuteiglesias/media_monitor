# PR5 diagnostic: controlled pruning + continuity guardrails

## Scope and objective

This document proposes **tree shaking with operational continuity** for `media_monitor`.
It does **not** propose a runtime rewrite.

Hard constraints:

- Keep canonical runtime path: `bin/run_hour.sh` + `make s01..s05`.
- Keep domain ownership in `apps/*/src/*`.
- Keep compatibility wrappers where still needed (`legacy/`, selected `scripts/`).

## Repository classification (current state)

| Zone | Classification | Why | Action stance |
|---|---|---|---|
| `bin/run_hour.sh`, `makefile` | canonical runtime | Current global orchestration entrypoint and stage wiring. | Must keep. |
| `apps/news_acquire/src/news_acquire` | owner source-of-truth | Acquire implementation moved under owner module. | Must keep. |
| `apps/news_editorial/src/news_editorial` | owner source-of-truth | Editorial implementation moved under owner module. | Must keep. |
| `apps/news_enrich/src/news_enrich` | owner source-of-truth | Enrich implementation moved under owner module. | Must keep. |
| `legacy/*.py` stage modules | compatibility wrapper | Backward-compatible module entrypoints for old calls; canonical Make now calls owner modules directly. | Keep; avoid runtime dependency on wrappers. |
| `backend/` | transitional/internal modules | Useful for migration history and internal reuse. | Keep; avoid promoting as public seam. |
| `scripts/export_pr3a_buses.py` | runtime-support utility | Material export seam to buses/indexes. | Keep and harden. |
| `scripts/04_promptflow_run.py`, `scripts/05_explode_pf_outputs.py`, `scripts/06_scrape_enrich.py` | compatibility/ops wrappers | Useful as aditive entrypoints; overlap with staged path. | Keep with explicit ownership labels. |
| `flow/` | must keep for continuity | PromptFlow remains active editorial seam. | Must keep; postpone invasive changes. |
| `contracts/schemas` | must keep for continuity | Contract boundaries for interoperability. | Must keep. |
| `storage/buses`, `storage/indexes` | must keep for continuity | Target public surfaces. | Keep and populate consistently. |
| `storage/raw` | internal intermediate artifact | Private module storage. | Keep internal-only. |
| `notes/` | mixed: historical/dev + live context | Contains useful handoff and diagnostics but also noise accumulation risk. | Phase 1 archive/indexing pass. |
| `docs/runbooks/` | historical + operational | Runbooks are useful but can become hard to navigate. | Keep; add index + archive older evidence snapshots. |
| local artifacts (`data/pf_out`, quarantine, local logs, drafts) | internal intermediate artifact | Operational scratch and stage internals. | Keep private; do not treat as public bus. |

## Hot spots of structural noise

1. **Ambiguous wrapper vs owner script intent** across `legacy/`, `backend/`, and `scripts/`.
2. **Documentation sprawl** between `notes/` and `docs/runbooks/` without simple “current vs historical” marker.
3. **Operational intermediates** (PF outputs/quarantine/drafts/logs) that are useful locally but should not be consumed as contracts.

## Phased pruning plan

### Phase 1 — safe now (very low risk)

- Add/normalize wrapper headers in `legacy/` and wrapper scripts (“compatibility entrypoint; source-of-truth in apps/*”).
- Add runbook index file grouping docs as: active runbook / historical evidence / migration record.
- Move purely historical ad-hoc notes to `notes/archive/` (no deletions).
- Add explicit “internal-only artifacts” section in storage/readme docs.

### Phase 2 — safe with smoke checks

- Consolidate duplicated helper scripts that wrap the same stage behavior.
- Normalize operational artifact paths for logs/manifests under `storage/indexes/` (or another explicit internal path).
- Introduce a lightweight run-record wrapper for command execution (single append target) and validate with stage smoke checks.

Smoke checks:

- `make preflight-runtime`
- `make s01 DRY_RUN=1`
- `make s02 DRY_RUN=1`
- `make s03 DRY_RUN=1`

### Phase 3 — postpone

- PromptFlow runtime/connection rewiring (`open_ai_connection`, keyring backend assumptions).
- Removing legacy wrappers still referenced by external scripts/cron paths.
- Structural collapse of `backend/` until runtime ownership usage is fully verified.
- Any migration that changes canonical orchestration order.

## Stop rules

Stop and postpone if any of these occur:

- A candidate deletion path is still referenced by `make`, `bin/run_hour.sh`, or cron/systemd wrappers.
- PromptFlow behavior changes are required to complete the cleanup.
- A cleanup proposal mixes documentation pruning with runtime behavior changes.
- A path cannot be classified confidently as wrapper/internal/historical.

## Success criteria for pruning

- Lower ambiguity: each path is clearly tagged as canonical, owner, wrapper, internal, or historical.
- Lower noise: historical materials are archived but preserved.
- No runtime breakage on canonical stage path.
- Better readiness for observability compaction inputs.
