# Source-site roll

## Prerequisites

- Authenticate the Vercel CLI (`vercel login`) and link this repository root to the existing project.
- Ensure the project Root Directory remains `apps/news_site`.
- Have current canonical source indexes for the requested digest. The roll builds only the generated snapshot; it does not ingest or generate editorial data.

## Commands

Preview:

```bash
make roll-site SITE_ID=argentina-general DIGEST_AT=20260721T18 TARGET=preview
```

Production:

```bash
make roll-site SITE_ID=argentina-general DIGEST_AT=20260721T18 TARGET=production
```

A PASS means the locally compiled and validated snapshot was included in `.vercel/output`, deployed using `vercel deploy --prebuilt`, and the deployment's `/api/health` returned the exact snapshot ID, digest, and item/section counts.

Inspect the latest record at:

```text
storage/observability/site_roll_latest_argentina-general.json
```

After a successful production roll, manually open the production URL and inspect the homepage, latest page, a story link, and a topic link. The health check is the machine gate; browser review remains the human presentation check.
