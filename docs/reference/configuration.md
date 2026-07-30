# Configuration

> **Status:** canonical identifier reference · **Verified against:** `7723918`

| Area | Identifiers | Source/default boundary |
|---|---|---|
| run selection | `DIGEST_AT`, `RUN_ID`, `ATTEMPT` | hour/logical/physical identity in source |
| local controls | `DRY_RUN`, `LIMIT`, `SAMPLE`, `NULL_SINK`, `PF_MODE` | Makefile/owner parsers |
| paths | `DATA_DIR`, `STORAGE_DIR`, `SENSING_RUN_ROOT`, `SENSING_STATE_ROOT`, `PF_FLOW_DIR`, `PF_RUNS` | local filesystem roots |
| acquire | `SENSING_FEED_CONFIG`, `ACQUIRE_NETWORK`, `WRITE_ARTIFACTS`, `ENQUEUE_SCRAPE`, `DB_RUN_BOOKKEEPING`, `GROUP_MIN_ROWS`, `GROUP_MAX_ROWS` | acquire runtime; feed file defaults to `config/sensing_feeds.v1.yaml` |
| database/enrich | `PG_DSN`, `BATCH` | secret DSN and worker batch size |
| editorial/site | `CONTRACTS_SCHEMAS_DIR`, `LEGACY_EDITORIAL_FALLBACK`, `ALLOW_EDITORIAL_FALLBACK`, `SITE_ID`, `SITE_SNAPSHOT_NOW` | schema/fallback/site selection |
| AWS task | `SENSING_S3_BUCKET`, `SENSING_S3_PREFIX`, `SENSING_TASK_TIMEOUT_SECONDS`, `RUN_IAM_DENIAL_PROBE` | ECS task/adapters |
| AWS deploy | `AWS_REGION`, `AWS_PROFILE`, `SENSING_BUCKET_NAME`, `ENVIRONMENT`, Terraform variables | deployment scripts/IaC |

Values in `.env.local`, `PG_DSN`, AWS credentials, and provider tokens are secrets/local state and must not be documented or committed. Configuration presence does not prove provider deployment. Consult the parser/IaC for exact validation and default values before operation.
