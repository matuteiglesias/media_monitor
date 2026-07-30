# Command matrix

> **Status:** canonical reference, not an operational procedure · **Verified against:** `7723918`

| Capability | Stable entrypoint | Owner | Required selectors |
|---|---|---|---|
| inspect/preflight | `make help`, `make env`, `make preflight-runtime`, `make ls` | root wiring | optional hour controls |
| acquire stages | `make s01`, `s02`, `s03` | news_acquire | `DIGEST_AT`; runtime controls |
| sensing bundle/compaction | `make sensing-bundle`, `make compact-sensing-bundles`, `make promote-sensing-bundle-local` | producer / compactor | digest, roots, attempt/run ID as applicable |
| editorial stages | `make s04`, `s06`, `s05` | news_editorial | digest, PF/runtime controls |
| enrich | `apps/news_enrich/entrypoints/run_enrich_owner.sh` | news_enrich | `MODE`, optional `ARGS` |
| export/index | `make export-pr3a`, `build-*-access-indexes` | named builders | digest where required |
| handoff/diagnose | `make diagnose-editorial`, `materialize-editorial-handoff` | news_editorial | digest/index paths |
| approve/publish | `make promote-draft`, `build-published-article-indexes`, `publish-article` | human gate / builder | `DRAFT_ID` |
| site snapshot/roll | `make build-site-snapshot`, `validate-site-snapshot`, `build-source-site`, `roll-site` | snapshot/site tooling | `SITE_ID`, `DIGEST_AT`; roll also `TARGET` |
| AWS manual substrate | `infra/aws/sensing/deploy.sh`, `run_first_task.sh`, `teardown.sh` | infrastructure/operators | AWS/provider inputs |

Exact preflight, recovery, verification, and teardown sequences belong to PR-MD4 operation pages. `scripts/archive` is historical; `scripts/compat_wrappers` is compatibility-only. Known broken aggregate/minimal-loop routes remain listed in [docs status](../README.md#capability-and-evidence-status), not silently recommended here.
