# Site snapshot and Vercel publication

> **Status:** canonical runbook; tooling locally validated, provider operation unverified · **Owner:** snapshot/site operator · **Verified against:** `6f39d25`

## Repository connections

Vercel currently reports two repository status contexts. Treat only
`Vercel – media-monitor` as the active news-site connection. The underscore-named
`Vercel – media_monitor` project is a legacy duplicate and should be disconnected
from this repository in Vercel rather than repaired or made required.

This classification was checked on 2026-08-17: the active context succeeded and
the legacy context failed on PR #56 and on `main`. The same pair of results was
present on merged PR #55, and GitHub reported `main` as unprotected with no
required status checks. A legacy failure is therefore provider cleanup, not a
code or merge blocker. This status evidence does not by itself prove a successful
production health reconciliation; retain the deployment verification below.

## Preflight/build

Choose fixed `SITE_ID` and `DIGEST_AT`; require coherent, current news indexes and site config. Build and validate before any provider call:

```bash
make build-site-snapshot SITE_ID=argentina-general DIGEST_AT=YYYYMMDDTHH
make validate-site-snapshot SITE_ID=argentina-general DIGEST_AT=YYYYMMDDTHH
SITE_ID=argentina-general DIGEST_AT=YYYYMMDDTHH npm --prefix apps/news_site run build
```

The aggregate `make publish-news-site` is denied until its missing npm `refresh-data`/`smoke:public-data` scripts are reconciled.

## Deploy/reconcile

After `vercel login` and confirming project root `apps/news_site`:

```bash
make roll-site SITE_ID=argentina-general DIGEST_AT=YYYYMMDDTHH TARGET=preview
# production only after preview/human review:
make roll-site SITE_ID=argentina-general DIGEST_AT=YYYYMMDDTHH TARGET=production
```

Provider commands are **unverified here**. Require local schema/digest/source-hash checks, prebuilt snapshot inclusion, deployment URL, and `/api/health` exact snapshot ID/digest/item/section counts. Then manually inspect home/latest/story/topic. Save `storage/observability/site_roll_latest_<site>.json` and provider output.

## Failure/rollback

Stop on stale/mixed digest, invalid/empty source, fallback, build failure, health mismatch, or wrong project root. Do not deploy around validation. Roll back through Vercel to the prior known-good deployment, verify its health identity, and retain both roll records; rebuild source truth rather than editing public JSON by hand.
