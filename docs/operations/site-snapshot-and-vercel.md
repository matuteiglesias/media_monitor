# Site snapshot and Vercel publication

> **Status:** canonical runbook; tooling locally validated, provider operation unverified · **Owner:** snapshot/site operator · **Verified against:** `e068f5a`

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
