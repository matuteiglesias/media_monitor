# news_editorial runbook

## Purpose

`apps/news_editorial` owns the editorial lane from digest runtime input through human/operator handoff. The lane keeps the current PromptFlow runtime intact, but the subsystem boundary is now described as an artifact ladder:

```text
Level 0 runtime evidence -> Level 1 contract buses -> Level 2 decision index -> Level 3 public snapshot
```

The most important operating rule is:

```text
PromptFlow output is runtime evidence, not the editorial contract.
news_piece_brief.v1 is the primary editorial contract.
editorial_latest.json is the human/operator decision surface.
```

## Artifact ladder

| Level | Path(s) | Operator meaning |
| --- | --- | --- |
| Level 0 runtime | `data/digest_jsonls/*`, `data/pf_out/*`, editorial `data/quarantine/*` rows | Evidence and emergency diagnostics. These paths are allowed to be ugly and runtime-specific. |
| Level 1 contracts | `storage/buses/news_piece_brief/v1/*`, `storage/buses/news_article_draft/v1/*`, `storage/buses/news_yt_script_draft/v1/*` | Schema-valid editorial artifacts that downstream code should prefer. |
| Level 2 handoff | `storage/indexes/editorial_latest.json` | Compact decision/status surface for humans and agents. |
| Level 3 snapshot | `apps/news_site/public/data/editorial_latest.json` when published | Hardened public/static handoff copy. |

## Four named components

### 1. promptflow_runner

Implementation: `apps/news_editorial/src/news_editorial/stage04_promptflow_run.py`

```text
data/digest_jsonls/<DIGEST_AT>.jsonl
  -> PromptFlow CLI/runtime
  -> data/pf_out/pfout_<DIGEST_AT>*.jsonl
```

Responsibilities:

- Locate current digest JSONL input.
- Run the existing PromptFlow CLI flow.
- Copy/normalize the raw PromptFlow output into `data/pf_out/*`.

Boundary rule: `data/pf_out/*` is Level 0 runtime output. Do not treat it as the stable editorial contract.

### 2. piece_brief_builder

Implementation: `apps/news_editorial/src/news_editorial/stage06_build_piece_briefs.py`

```text
data/pf_out/*
  -> normalized seed ideas
  -> storage/buses/news_piece_brief/v1/*.jsonl
```

Responsibilities:

- Read PromptFlow runtime output.
- Normalize seed ideas and editorial decision fields.
- Emit schema-valid `news_piece_brief.v1` rows.
- Quarantine schema failures with enough evidence to debug the run.

Boundary rule: `news_piece_brief.v1` is the primary editorial Level 1 contract today.

### 3. draft_builder

Implementation: `apps/news_editorial/src/news_editorial/stage05_explode_pf_outputs.py` with bus validation/writes in `apps/news_editorial/src/news_editorial/draft_bus_writer.py`

```text
storage/buses/news_piece_brief/v1/* preferred
  -> storage/buses/news_article_draft/v1/*.jsonl
  -> storage/buses/news_yt_script_draft/v1/*.jsonl when format candidates request video
  -> data/drafts/<DIGEST_AT>/*.jsonl optional transitional mirror
```

Responsibilities:

- Prefer `news_piece_brief.v1` inputs when present.
- Build schema-valid draft bus records before writing the transitional mirror.
- Keep `data/drafts/*` as an optional mirror controlled by `WRITE_DRAFT_MIRROR`; it is not the canonical draft contract.
- Use legacy PF cluster packaging only when the configured fallback policy allows it.
- Emit metrics/quarantine evidence when fallback activates.

Boundary rule: `news_article_draft.v1` and `news_yt_script_draft.v1` are the Level 1 draft contracts. `data/drafts/*` is a transitional Level 0 mirror.

### 4. handoff_index_builder

Implementation: `scripts/build_editorial_access_indexes.py`

```text
editorial buses + transitional draft/fallback evidence
  -> storage/indexes/editorial_latest.json
```

Responsibilities:

- Build the compact handoff/status document for operators and agents.
- Read `news_piece_brief.v1`, `news_article_draft.v1`, and `news_yt_script_draft.v1` buses first.
- Fall back to `data/drafts/*` only when draft bus rows are absent.
- Surface brief/draft/fallback counts, latest artifact pointers, and explicit input provenance.
- Keep fallback visible instead of requiring operators to inspect random Level 0 folders.

Boundary rule: `editorial_latest.json` is the Level 2 human/operator decision surface. Its `contract_inputs` fields show Level 1 bus use, and its `fallback_inputs` fields show Level 0 transitional sources such as `pf_out`, `data_drafts`, or `quarantine`.

## Operator entrypoint

```bash
apps/news_editorial/entrypoints/run_editorial_owner.sh
```

Wrapper behavior:

1. Executes `make s04 DIGEST_AT=<...> DRY_RUN=<...> PF_MODE=<...>`.
2. Executes `make s06 DIGEST_AT=<...> DRY_RUN=<...>`.
3. Executes `make s05 DIGEST_AT=<...> DRY_RUN=<...>`.
4. Executes `make build-editorial-access-indexes DIGEST_AT=<...>` unless `RUN_EXPORTS=0`.

### Examples

```bash
# Standard editorial run
DIGEST_AT=20260313T15 apps/news_editorial/entrypoints/run_editorial_owner.sh

# Inspect commands only
DIGEST_AT=20260313T15 apps/news_editorial/entrypoints/run_editorial_owner.sh --dry-run

# Force PF article mode passthrough
DIGEST_AT=20260313T15 PF_MODE=new apps/news_editorial/entrypoints/run_editorial_owner.sh

# Skip handoff index/export step for local debugging
DIGEST_AT=20260313T15 RUN_EXPORTS=0 apps/news_editorial/entrypoints/run_editorial_owner.sh
```

## Handoff input provenance

`storage/indexes/editorial_latest.json` includes explicit input provenance:

```json
{
  "contract_inputs": {
    "piece_brief_bus": true,
    "article_draft_bus": true,
    "yt_script_draft_bus": true
  },
  "fallback_inputs": {
    "pf_out": false,
    "data_drafts": false,
    "quarantine": true
  }
}
```

Expected ED3 behavior:

- If draft bus rows exist, the handoff index reads them instead of `data/drafts/*`.
- If draft bus rows are absent, the handoff index may fall back to `data/drafts/*` and sets `fallback_inputs.data_drafts=true`.
- If raw PF output is missing but buses exist, the handoff index still builds; `seed_ideas_emitted` may be `0`, but bus-backed briefs/drafts keep the handoff usable.

## Fallback and no-op behavior

- `make s04` performs no-op when suitable digest input is missing.
- `make s06` may emit zero briefs when PF outputs or seed ideas are missing/invalid.
- `make s05` consumes briefs when available, writes validated draft buses first, mirrors to `data/drafts/*` when enabled, and falls back to legacy cluster packaging when briefs are absent and fallback policy allows it.
- Default fallback mode is `LEGACY_EDITORIAL_FALLBACK=emergency`.
- Set `LEGACY_EDITORIAL_FALLBACK=off` to fail fast when `news_piece_brief.v1` is missing.
- Every fallback activation must remain visible in metrics/quarantine evidence; fallback is migration telemetry, not normal success.

## Updated editorial contract (`news_seed_idea.v1`)

- The same `v1` version is preserved for compatibility with current producers and consumers.
- Optional editorial decision fields may be populated:
  - `format_candidates`: `article` | `yt_script` | `both`
  - `working_title`
  - `angle`
  - `why_now`
  - `supporting_refs`
  - `risk_notes`
- For new editorial flows, populate these fields where possible to enable format decisions and prioritization.

## External dependency boundary

- PromptFlow runtime (`PF_PYTHON`/conda env and run dir resolution) remains an external dependency.
- Failures in PromptFlow availability or connectivity are runtime/environment issues, not ownership-definition issues.

## Constraints respected

- No replacement of `bin/run_hour.sh`.
- No replacement of `make s04`/`make s06`/`make s05`.
- No refactor of PromptFlow internals.
- No schema definition changes.
- No file moves/deletes in legacy.
