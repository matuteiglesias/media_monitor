# news_editorial runbook (PR4b owner module)

## Purpose
`apps/news_editorial` is now the explicit owner for editorial structuring and generation boundaries.

PR4b establishes module ownership and a stable operator entrypoint while keeping legacy runtime behavior unchanged.

## Scope owned by news_editorial

### Owned paths
- `flow/`
- `data/digest_jsonls/*`
- `data/pf_out/*`
- `data/drafts/*`
- editorial-related quarantine entries under `data/quarantine/*`

### Seams consumed
- Canonical runtime seam: `data/digest_jsonls/<DIGEST_AT>.jsonl`
- Optional structured seam: `storage/buses/news_digest_group/v1/*`

### Seams/exports targeted (future adapters)
- `news_topic_cluster.v1`
- `news_seed_idea.v1` (expandido de forma backward-compatible con campos editoriales: `format_candidates`, `working_title`, `angle`, `why_now`, `supporting_refs`, `risk_notes`)
- `news_seed_card.v1`


## Implementation source of truth (PR4d)
- `apps/news_editorial/src/news_editorial/stage04_promptflow_run.py`
- `apps/news_editorial/src/news_editorial/stage05_explode_pf_outputs.py`
- `apps/news_editorial/src/news_editorial/{ids,io,db,slugs}.py`

Legacy modules are thin compatibility wrappers:
- `legacy/stage04_promptflow_run.py`
- `legacy/stage05_explode_pf_outputs.py`

`flow/` is intentionally left at repo root in PR4d for runtime safety and documented as editorial-owned transitional seam.

## Operator entrypoint

```bash
apps/news_editorial/entrypoints/run_editorial_owner.sh
```

Wrapper behavior:
1. Executes `make s04 DIGEST_AT=<...> DRY_RUN=<...> PF_MODE=<...>`
2. Executes `make s05 DIGEST_AT=<...> DRY_RUN=<...>`

### Examples

```bash
# Standard editorial run
DIGEST_AT=20260313T15 apps/news_editorial/entrypoints/run_editorial_owner.sh

# Inspect commands only
DIGEST_AT=20260313T15 apps/news_editorial/entrypoints/run_editorial_owner.sh --dry-run

# Force PF article mode passthrough
DIGEST_AT=20260313T15 PF_MODE=new apps/news_editorial/entrypoints/run_editorial_owner.sh
```

## Fallback and no-op behavior
- `make s04` already performs no-op when suitable PF input is missing.
- `make s05` continues with existing legacy behavior over available PF outputs.
- This wrapper does not alter stage semantics; it only centralizes editorial ownership at module level.


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

## External dependency boundary
- PromptFlow runtime (`PF_PYTHON`/conda env and run dir resolution) remains external dependency.
- Failures in PromptFlow availability or connectivity are runtime/environment issues, not ownership-definition issues.

## Constraints respected
- No replacement of `bin/run_hour.sh`.
- No replacement of `make s04`/`make s05`.
- No refactor of PromptFlow internals.
- No changes to schema definitions.
- No file moves/deletes in legacy.
