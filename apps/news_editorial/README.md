# news_editorial (PR4b owner module)

`apps/news_editorial` is the explicit owner module for the editorial structuring layer in the migration plan.

This PR is additive: it clarifies ownership and operator entrypoints while preserving the current runtime path.

## Ownership declaration

### Owned runtime/raw boundaries
- `flow/` (PromptFlow definition and editorial generation logic)
- `data/digest_jsonls/*` (operational editorial input seam today)
- `data/pf_out/*` (PromptFlow output seam today)
- `data/drafts/*` (downstream editorial-derived drafts after stage05)
- `data/quarantine/*` entries produced by editorial stages (`V03`, `V05`)

### Buses consumed
- `storage/buses/news_digest_group/v1/*` (structured digest groups when available)
- legacy digest input seam `data/digest_jsonls/<DIGEST_AT>.jsonl` remains active source of truth for current runtime

### Buses intended to be written by editorial adapters
- `news_topic_cluster.v1`
- `news_seed_idea.v1` (expandido de forma backward-compatible con campos editoriales: `format_candidates`, `working_title`, `angle`, `why_now`, `supporting_refs`, `risk_notes`)
- `news_seed_card.v1`

(These remain planned adapter outputs; this PR does not change contract shapes nor replace runtime.)


## Implementation location (PR4d)
Editorial primary implementation now lives under:
- `apps/news_editorial/src/news_editorial/stage04_promptflow_run.py`
- `apps/news_editorial/src/news_editorial/stage06_build_piece_briefs.py`
- `apps/news_editorial/src/news_editorial/stage05_explode_pf_outputs.py`
- `apps/news_editorial/src/news_editorial/{ids,io,db,slugs}.py`

Compatibility wrappers remain at:
- `legacy/stage04_promptflow_run.py`
- `legacy/stage05_explode_pf_outputs.py`

`flow/` remains in its current top-level location for runtime safety and is treated as an editorial-owned transitional seam in this PR.

## Entrypoint

Use owner wrapper:

```bash
apps/news_editorial/entrypoints/run_editorial_owner.sh
```

Wrapper delegates to canonical runtime targets:
1. `make s04`
2. `make s06`
3. `make s05`


## Contrato editorial actualizado (`news_seed_idea.v1`)
- Se mantiene **la misma versión `v1`** para preservar compatibilidad con productores/consumidores actuales.
- Los nuevos campos editoriales de decisión se agregan como opcionales en el esquema:
  - `format_candidates`: `article` | `yt_script` | `both`
  - `working_title`
  - `angle`
  - `why_now`
  - `supporting_refs`
  - `risk_notes`
- Recomendación operativa: para nuevos flujos editoriales, poblar estos campos como mínimo para habilitar decisión de formato y priorización.

## External dependency boundary (explicit)
- PromptFlow runtime/env/connectivity is an external dependency boundary for this module.
- Current runtime keeps PF invocation in canonical make target logic.
- This PR documents dependency ownership but does not solve PF runtime connectivity.

See operational details in [`runbook.md`](./runbook.md).

## Non-goals in PR4b
- No replacement of `bin/run_hour.sh`.
- No replacement of `make s04` / `make s05`.
- No PromptFlow refactor.
- No schema edits under `contracts/schemas`.
- No ownership migration for `news_enrich` (reserved for PR4c).
