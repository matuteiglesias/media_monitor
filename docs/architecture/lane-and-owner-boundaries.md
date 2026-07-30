# Lane and owner boundaries

> **Status:** canonical architecture · **Verified against:** `bf04a74`
> **Scope:** ownership and allowed seams; commands remain in current runbooks until PR-MD4.

| Owner | Owns | May read | Must not own |
|---|---|---|---|
| `apps.news_acquire` | feeds, stages 01–03, sensing run production | feed config, prior input snapshot | editorial approval, canonical compaction pointer |
| sensing compactor | validation/selection of finalized runs, generations, `current.json` | immutable run prefixes | feed acquisition or editorial state |
| `apps.news_enrich` | scrape/replay/requeue and `scraped_article.v1` | scrape requests/DB queue | acquisition grouping, editorial publication |
| `apps.news_editorial` | PromptFlow adapter, briefs, drafts, handoff index | news buses and approved enrichment seams | sensing state or human approval |
| human reviewer + promotion command | approval decision and published article creation | exactly one valid draft | silent/automatic approval |
| index/snapshot builders | deterministic read models/public projections | contract buses and named indexes | upstream facts or approval decisions |
| `apps/news_site` | render generated public snapshot and health routes | `public/data` deployment snapshot | raw workspace, buses, credentials, editorial mutation |
| AWS IaC/adapters | task runtime, roles, logs, bucket/network substrate | immutable image/config | schedules/alarms/deployed compaction not present in IaC |
| Vercel tooling | build/deploy transport and health verification | validated prebuild | source artifact authority |

## Allowed integration direction

New cross-owner integrations use versioned contract buses, compact indexes, or hardened snapshots. `data/*` is an owner-local/transitional workspace. Compatibility wrappers can invoke owners but do not gain authority over their state.

## Human boundary

Draft generation and article publication are different authorities. `promote_draft_to_published.py` requires the explicit `--approve-human` flag, validates one draft, derives a stable article ID, and emits the published contract. UI or automation must not bypass this gate.

## Cloud boundary

The AWS producer and compactor use distinct actors in the S3 adapter. Producer writes are confined to a run prefix and finalized last; compactor writes immutable generation objects then the mutable pointer. The Terraform packet provisions a manual producer task, not an operated schedule or compactor deployment.
