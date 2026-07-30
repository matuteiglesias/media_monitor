# Local lane operation

> **Status:** canonical runbook · **Owner:** lane owner modules · **Verified against:** `e068f5a`

## Preflight

Run `make preflight-runtime` and `make env`; choose a fixed UTC `DIGEST_AT=YYYYMMDDTHH`. Resolve warnings for the lane you will run. PromptFlow and PostgreSQL are external dependencies; dry-run does not prove them.

## Execute

```bash
DIGEST_AT=YYYYMMDDTHH bin/run_minimal_loop_once.sh --lane sensing
DIGEST_AT=YYYYMMDDTHH bin/run_minimal_loop_once.sh --lane editorial
MODE=batch apps/news_enrich/entrypoints/run_enrich_owner.sh
```

Run lanes independently and in dependency order. The generic `--lane enrich` path is denied because it names absent `scripts/06_scrape_enrich.py`.

## Reconcile

Use `make ls DIGEST_AT=...`; validate expected buses/indexes rather than exit code alone. Sensing requires news refs/groups and export evidence; editorial requires brief/draft state plus `editorial_latest.json`; enrich requires schema-valid scraped bus/status. Inspect `data/quarantine` and `storage/observability`.

## Failure/retry/stop

Retry the same logical digest only after preserving evidence and correcting the dependency. Do not hand-edit indexes or promote partial artifacts. Stop if schema validation fails, required inputs are missing, or fallback is unexplained. Local generated paths can be rebuilt; contract facts and run evidence must not be silently deleted.
