# news_editorial

`apps/news_editorial` owns the editorial generation and handoff lane. The lane is being kept compatible with the current PromptFlow runtime while its contracts are made explicit in the same artifact ladder used elsewhere in Media Monitor.

## Editorial doctrine

The editorial lane is a subsystem boundary, not a collection of PromptFlow output folders.

```text
digest runtime input
  -> promptflow_runner
  -> piece_brief_builder
  -> draft_builder
  -> handoff_index_builder
```

Artifact levels:

| Level | Editorial artifacts | Role |
| --- | --- | --- |
| Level 0 runtime evidence | `data/digest_jsonls/*`, `data/pf_out/*`, editorial rows in `data/quarantine/*` | Operational inputs, raw generation output, and failure evidence. These are not the editorial contract. |
| Level 1 contract buses | `storage/buses/news_piece_brief/v1/*`, `storage/buses/news_article_draft/v1/*`, `storage/buses/news_yt_script_draft/v1/*` | Schema-valid editorial contracts for downstream tooling. |
| Level 2 access/decision index | `storage/indexes/editorial_latest.json` | Human/operator handoff surface and compact status index. |
| Level 3 public snapshot | `apps/news_site/public/data/editorial_latest.json` when exported | Hardened snapshot for static/public consumers. |

Current doctrine:

- Raw PromptFlow output in `data/pf_out/*` is Level 0 runtime evidence only.
- `news_piece_brief.v1` is the primary editorial contract today.
- `data/drafts/*` is an optional transitional Level 0 mirror; draft buses are the canonical downstream draft surface.
- `editorial_latest.json` is the operator/human decision surface.
- Legacy fallback is emergency/support behavior and must remain visible through metrics and quarantine evidence.

## Named components

1. **promptflow_runner** — `stage04_promptflow_run.py`
   - Reads `data/digest_jsonls/<DIGEST_AT>.jsonl`.
   - Runs PromptFlow through the existing CLI/runtime.
   - Writes raw generation output to `data/pf_out/pfout_<DIGEST_AT>*.jsonl`.
2. **piece_brief_builder** — `stage06_build_piece_briefs.py`
   - Reads PromptFlow runtime output.
   - Normalizes editorial seed ideas.
   - Writes schema-valid `news_piece_brief.v1` rows to `storage/buses/news_piece_brief/v1/*`.
3. **draft_builder** — `stage05_explode_pf_outputs.py`
   - Prefers `news_piece_brief.v1` as canonical input.
   - Writes schema-valid draft rows to `storage/buses/news_article_draft/v1/*` and, when requested by format candidates, `storage/buses/news_yt_script_draft/v1/*`.
   - Writes current draft mirrors under `data/drafts/<DIGEST_AT>/*` when `WRITE_DRAFT_MIRROR` is enabled.
   - May use legacy PF cluster packaging only as emergency fallback.
4. **handoff_index_builder** — `scripts/build_editorial_access_indexes.py`
   - Builds `storage/indexes/editorial_latest.json` as the compact operator view over briefs, drafts, and fallback status.
   - Reads draft buses first and uses `data/drafts/*` only as an explicit transition fallback.
   - Emits `contract_inputs` and `fallback_inputs` so operators can see which Level 1 buses or Level 0 fallbacks contributed to the handoff.

## Ownership declaration

### Owned runtime/raw boundaries

- `flow/` (PromptFlow definition and editorial generation logic)
- `data/digest_jsonls/*` (current operational editorial input seam)
- `data/pf_out/*` (Level 0 PromptFlow runtime output)
- `data/drafts/*` (transitional draft mirror/output surface)
- `data/quarantine/*` entries produced by editorial stages (`V03`, `V05`, and related editorial fallbacks)

### Buses consumed

- `storage/buses/news_digest_group/v1/*` when available
- Current runtime seam: `data/digest_jsonls/<DIGEST_AT>.jsonl`

### Buses written today

- `storage/buses/news_piece_brief/v1/*`
- `storage/buses/news_article_draft/v1/*`
- `storage/buses/news_yt_script_draft/v1/*`

### Buses planned for later PRs

- `editorial_event.v1` or equivalent fallback/event stream

## Implementation source of truth

Editorial primary implementation lives under:

- `apps/news_editorial/src/news_editorial/stage04_promptflow_run.py`
- `apps/news_editorial/src/news_editorial/stage06_build_piece_briefs.py`
- `apps/news_editorial/src/news_editorial/stage05_explode_pf_outputs.py`
- `apps/news_editorial/src/news_editorial/draft_bus_writer.py`
- `apps/news_editorial/src/news_editorial/{ids,io,db,slugs}.py`

Compatibility wrappers remain at:

- `legacy/stage04_promptflow_run.py`
- `legacy/stage05_explode_pf_outputs.py`

`flow/` remains at the repo root for runtime safety and is treated as an editorial-owned transitional seam.

## Operator entrypoint

Use owner wrapper:

```bash
apps/news_editorial/entrypoints/run_editorial_owner.sh
```

Wrapper delegates to canonical runtime targets:

1. `make s04` — PromptFlow runner
2. `make s06` — piece brief builder
3. `make s05` — draft builder with legacy fallback
4. `make build-editorial-access-indexes` — handoff index builder, unless `RUN_EXPORTS=0`

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

- PromptFlow runtime/env/connectivity is an external dependency boundary for this module.
- Current runtime keeps PromptFlow invocation in canonical make target logic.
- This documentation clarifies ownership but does not replace PromptFlow or solve runtime connectivity.

See operational details in [`runbook.md`](./runbook.md).

## Non-goals for this closure

- No PromptFlow replacement.
- No file moves.
- No UI work.
- No fallback deletion.
