# PR4b runbook: news_editorial ownership established

## Decision
`apps/news_editorial` is now the explicit owner module for editorial structuring and generation boundaries.

## What this PR changes
- Upgrades `apps/news_editorial/README.md` from placeholder to explicit ownership documentation.
- Adds `apps/news_editorial/runbook.md` with owned paths, consumed seams, intended buses, fallback/no-op behavior and dependency boundaries.
- Adds additive entrypoint wrapper `apps/news_editorial/entrypoints/run_editorial_owner.sh` delegating to canonical runtime:
  - `make s04`
  - `make s05`

## Ownership clarified
- Owns `flow/`, `data/digest_jsonls/*`, `data/pf_out/*`, `data/drafts/*` editorial path.
- Consumes `news_digest_group.v1` seam when available while retaining legacy digest seam.
- Targets future editorial adapter outputs:
  - `news_topic_cluster.v1`
  - `news_seed_idea.v1`
  - `news_seed_card.v1`

## External dependency boundary
PromptFlow runtime remains an external dependency and known boundary. This PR documents that dependency but intentionally does not refactor or replace PromptFlow runtime wiring.

## Runtime safety (explicit)
- `bin/run_hour.sh` unchanged.
- `make s04/s05` unchanged.
- `legacy/stage04_promptflow_run.py` and `legacy/stage05_explode_pf_outputs.py` remain intact.
- No schema changes.

## Quick checks

```bash
bash -n apps/news_editorial/entrypoints/run_editorial_owner.sh
apps/news_editorial/entrypoints/run_editorial_owner.sh --dry-run
```
