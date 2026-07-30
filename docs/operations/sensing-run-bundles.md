# Immutable sensing run bundles

> **Status:** canonical runbook · **Owner:** news_acquire producer · **Verified against:** `e068f5a`

## Preflight

Run `make preflight-runtime`; validate `SENSING_FEED_CONFIG`; choose fixed `DIGEST_AT`, `ATTEMPT`, and optional unique `RUN_ID`. Ensure the run root has space and the run ID does not already exist.

## Execute

```bash
DIGEST_AT=YYYYMMDDTHH ATTEMPT=1 make sensing-bundle
# explicit isolation/identity:
python scripts/run_sensing_bundle.py --digest-at YYYYMMDDTHH --run-root artifacts/sensing_runs --run-id sensing:YYYYMMDDTHH:attempt:1:manual
```

The second command is illustrative and writes artifacts; the `--help` surface was verified in PR-MD4.

## Reconcile independently

Require `runs/<run_id>/manifest.json`, `evidence/checksums.json`, candidates, and `FINALIZED`. Confirm manifest/run-directory identity, digest, stage results, status, counts, source commit/config digest, every checksum, and quarantine. `FINALIZED` must be last; exit zero alone is insufficient.

## Failure/retry

Never edit/finalize a failed bundle. Preserve staging/evidence, diagnose the failed stage, increment attempt, and use a new physical run ID for the same logical digest. A collision is a stop condition, not permission to overwrite. Producer writes to generations or `current.json` are denied.
