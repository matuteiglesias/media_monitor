# Documentation inventory and canonicality map v0.1

- **Scope:** PR-MD0 inventory only; no procedure is promoted or rewritten here.
- **Repository inspected:** `58ec15c94f7a21fbf47587967518a64649835129`
- **Status:** reviewable inventory; proposed ownership is not canonical until human acceptance.
- **Evidence:** tracked files, source, schemas, tests, Make targets, shell entrypoints, and infrastructure at the commit above.

## Method and classification

The inventory used `git ls-files`, not modification time, then compared prose with executable source. “Canonical” means current reader truth, “supporting” means useful detail or evidence, and “historical” means it cannot own current commands. Generated dependency metadata and local secrets are excluded as documentation. Commands in this page are inventory references, not newly verified operating procedures.

## Complete documentation inventory

| Surface | Files | Current classification | Proposed disposition / owner |
|---|---|---|---|
| Repository front door | `README.md` | canonical but overloaded | keep concise; route through proposed `docs/README.md` in PR-MD1 |
| Owner modules | `apps/news_{acquire,enrich,editorial}/{README.md,runbook.md}` | supporting; some current commands, some drift | concise component summaries linking to component and capability pages in PR-MD3/4 |
| Contract front door | `contracts/README.md` | supporting/current | `docs/reference/contracts-and-schemas.md` in PR-MD3; retain implementation-local link |
| Architecture/product | `docs/architecture/{artifact_ladder,utility_inventory}.md`, `docs/product/product_maps.md` | mixed supporting/current | reconcile into architecture pages in PR-MD2 |
| Current capability runbooks | `docs/runbooks/{README,news-site-publishing,newspaper_skin_guide,site-roll}.md` | mixed, potentially canonical | map to publication and site capability pages in PR-MD4 |
| PR/sprint runbooks | `docs/runbooks/pr1b-*`, `pr4a-*` through `pr9-*` (15 files) | historical/supporting | classify and banner in PR-MD6; never own current commands |
| Runtime records | `docs/runbooks/runtime-evidence-20260101T10.md`, `runtime-evidence-20260313T15.md` | historical evidence | retain as evidence; do not use as current status without revalidation |
| Notes | `docs/notes/{dev_next_pointer,dev_sprint,handoff-memo-monorepo-news}.md` | historical/working memory | classify in PR-MD6 |
| Legacy docs | `docs/legacy/*` (5 files), `legacy/Readme_JOURNAL.md`, `legacy/notes/{hist,sql}.txt`, `legacy/test.mdd` | historical | preserve; add historical router in PR-MD6 |
| AWS implementation | `infra/aws/sensing/README.md` | supporting, deployment-ready | link from `docs/operations/aws-sensing-deployment.md` in PR-MD4 |
| AWS retrofit bundle | `notes/media_monitor_aws_codex_retrofit_bundle_v0_1/INSTALL.md` and 25 plan, prompt, contract, template, and closure Markdown files | historical/supporting evidence | preserve as governed evidence; canonical pages must cite source/IaC instead |
| Documentation seed bundle | `notes/media-monitor-documentation-seed-v0_1/AGENTS.md`, `BUNDLE_MANIFEST.md`, and 18 program files | historical seed after overlay | root `AGENTS.md` and `docs/documentation_program/` now own program execution |
| Dependency lists | `requirements-sensing.txt`, `flow/requirements.txt` | executable configuration, not prose docs | configuration reference in PR-MD3 |

This accounts for all 92 tracked Markdown, text, README/AGENTS, and dependency-list surfaces returned by the inventory command. The two bundles are retained; PR-MD0 only overlays the documentation-program seed at its intended root locations.

## Command and entrypoint matrix

| Reader task | Executable owner | Primary entrypoint(s) | Proposed canonical page |
|---|---|---|---|
| Inspect runtime | root Makefile | `make help`, `make env`, `make preflight-runtime`, `make ls` | `docs/reference/command-matrix.md` |
| Local acquire | `apps.news_acquire` | `make s01 s02 s03`; `apps/news_acquire/entrypoints/run_acquire_owner.sh` | `docs/operations/local-lane-operation.md` |
| Immutable sensing run | acquire run-bundle code | `make sensing-bundle`; `scripts/run_sensing_bundle.py` | `docs/operations/sensing-run-bundles.md` |
| Compact/promote sensing | compactor scripts | `make compact-sensing-bundles`; `make promote-sensing-bundle-local` | `docs/operations/sensing-compaction-and-recovery.md` |
| Editorial generation | `apps.news_editorial` | `make s04 s06 s05`; `apps/news_editorial/entrypoints/run_editorial_owner.sh` | `docs/operations/local-lane-operation.md` |
| Enrichment | `apps.news_enrich` | `apps/news_enrich/entrypoints/run_enrich_owner.sh`; compatibility worker/replay wrappers | component guide plus local operation page |
| Export and access indexes | root scripts | `make export-pr3a build-news-access-indexes build-enrich-access-indexes build-editorial-access-indexes` | command and buses/indexes references |
| Diagnose/handoff | editorial scripts | `make diagnose-editorial materialize-editorial-handoff` | `docs/operations/editorial-human-last-mile.md` |
| Human publication | publication scripts | `make promote-draft`, `make build-published-article-indexes`, `make publish-article` | `docs/operations/editorial-human-last-mile.md` |
| Public/site snapshot | site scripts | `make validate-publish-surface publish-news-site publish-last-mile-snapshot build-site-snapshot validate-site-snapshot build-source-site roll-site` | `docs/operations/site-snapshot-and-vercel.md` |
| Whole/periodic loops | `bin/` | `bin/run_hour.sh`, `run_minimal_loop_once.sh`, `run_sensing_heartbeat.sh`; heartbeat Make targets | local lane operation page; status limitations explicit |
| AWS sensing | `infra/aws/sensing` and task adapters | `deploy.sh`, `run_first_task.sh`, `scripts/run_sensing_task.py`, `run_sensing_compactor_task.py` | `docs/operations/aws-sensing-deployment.md` |
| Contract tests | contract test suite | `python -m pytest contracts/tests/test_contracts.py` | contracts reference |
| Site tests/build | `apps/news_site/package.json` | `npm --prefix apps/news_site run test:refresh-data`; `node --test apps/news_site/scripts/validate_site_snapshot.test.mjs`; `npm --prefix apps/news_site run build` | site component/operation pages |

Compatibility wrappers under `scripts/compat_wrappers/` and archived scripts under `scripts/archive/` are not proposed as golden-path owners.

## Environment and configuration inventory

| Area | Identifiers / files | Authority and caution |
|---|---|---|
| Time/run controls | `DIGEST_AT`, `RUN_ID`, `ATTEMPT`, `DRY_RUN`, `LIMIT`, `SAMPLE`, `NULL_SINK`, `PF_MODE` | Makefile, lane scripts, and source parsers; exact accepted values must be documented from source |
| Local storage/runtime | `DATA_DIR`, `STORAGE_DIR`, `SENSING_RUN_ROOT`, `SENSING_STATE_ROOT`, `PF_FLOW_DIR`, `PF_RUNS` | source defaults; changing roots changes artifact location |
| Acquisition | `SENSING_FEED_CONFIG` and `config/sensing_feeds.v1.yaml`, `ACQUIRE_NETWORK`, `ENQUEUE_SCRAPE`, `DB_RUN_BOOKKEEPING`, `GROUP_MIN_ROWS`, `GROUP_MAX_ROWS` | acquire source and run-bundle environment |
| Database/enrich | `PG_DSN`, `BATCH` | DB adapters and scrape worker; secret value must never enter docs |
| Editorial/site | `CONTRACTS_SCHEMAS_DIR`, `LEGACY_EDITORIAL_FALLBACK`, `ALLOW_EDITORIAL_FALLBACK`, `SITE_ID`, `SITE_SNAPSHOT_NOW` | source and Node validators; fallbacks need explicit risk/status treatment |
| AWS task | `SENSING_S3_BUCKET`, `SENSING_S3_PREFIX`, `SENSING_TASK_TIMEOUT_SECONDS`, `RUN_IAM_DENIAL_PROBE` | ECS task definition and adapters; bucket is required, timeout is bounded in source |
| AWS deployment | `AWS_REGION`, `AWS_PROFILE`, `SENSING_BUCKET_NAME`, `ENVIRONMENT`, Terraform variables and `terraform.tfvars.example` | deploy scripts/IaC; `.env.local` is untracked-secret material and not documentation |
| Feed/dependencies | `.env` inclusion in Makefile, `.env.example`, `requirements-sensing.txt`, `flow/requirements.txt`, `apps/news_site/package.json` | reference inputs; local `.env.local` values excluded |

## Contract/schema catalog

`contracts/tests/test_contracts.py` and `contracts/tests/fixtures/` provide executable examples for the JSON schemas.

| Schema | Role | Principal producer / consumer |
|---|---|---|
| `news_ref.v1` | normalized sensed reference | export → news indexes/site |
| `news_digest_group.v1` | grouped sensed news | export → draft generation/site |
| `scrape_request.v1` | enrichment request | acquire/export → enrich worker |
| `scraped_article.v1` | enriched content | enrich → enrich index/downstream |
| `news_topic_cluster.v1` | clustered article group | PromptFlow → editorial |
| `news_seed_idea.v1` | candidate editorial idea | PromptFlow → seed compilation |
| `news_seed_card.v1` | developed seed | editorial → brief/draft path |
| `news_piece_brief.v1` | editorial handoff brief | stage 06 → editorial indexes |
| `news_article_draft.v1` | reviewable article | draft generator → human promotion |
| `news_yt_script_draft.v1` | reviewable video-script draft | editorial producer → review tooling |
| `published_article.v1` | human-approved article | promotion script → public indexes/site |
| `publish_surface_v1` | reconciled publish surface | validator/indexes → publication checks |
| `site_snapshot.v1` | deterministic source-site snapshot | snapshot builder → validator/news site |

## Artifact writer/reader and mutation matrix

| Artifact/state | Authoritative writer | Readers | Mutation semantics |
|---|---|---|---|
| `data/rss_slices/rss_dumps`, `data/digest_map`, `data/digest_jsonls` | acquire stages 01–03 | export, PromptFlow, diagnostics | hour-scoped local working artifacts |
| `artifacts/sensing_runs/<run_id>` manifest/payloads | `run_sensing_bundle.py` / acquire run-bundle | compactor, AWS uploader, evidence inspection | finalized immutable run bundle |
| S3 run prefix | `run_sensing_task.py` | compactor task/operator | producer has run-prefix authority, not canonical-state authority |
| `storage/sensing_compacted` generations/current pointer | `compact_sensing_bundles.py` (or AWS compactor adapter) | local promotion, operators, downstream | deterministic generation; compactor is sole canonical writer |
| `storage/buses/*.jsonl` | `export_pr3a_buses.py`, editorial/enrich producers by contract | index builders and downstream lanes | append/materialize by bus owner; stable identities required |
| `storage/indexes/news_*` | `build_news_access_indexes.py` | publish validator/site | derived mutable access indexes |
| `storage/indexes/enrich_*` | `build_enrich_access_indexes.py` | diagnostics/downstream | derived mutable access index |
| `storage/indexes/editorial_latest.json` | `build_editorial_access_indexes.py` | handoff, publish snapshot/site | derived mutable pointer/status view |
| published-article indexes | `build_published_article_indexes.py` | public snapshot/site | only human-approved promotion supplies articles |
| `artifacts/editorial_handoff/latest` | editorial handoff module | human reviewer | materialized handoff pointer/packet |
| publish/site snapshots | `publish_last_mile_snapshot.py`, `build_site_snapshot.py` | validators and Next.js build | generated snapshot; validators independently check contract |
| `apps/news_site/public/data` | refresh scripts | static web application | deploy input mirror, never primary editorial authority |
| `storage/observability` run records/heartbeat | run-record and heartbeat scripts | operator/diagnostics | operational evidence, not product-state authority |

## Drift, duplication, and orphan register

| Finding | Evidence | Risk | Planned treatment |
|---|---|---|---|
| Acquisition AWS statement is stale | `apps/news_acquire/runbook.md` says Terraform remains PR-A5 work; `infra/aws/sensing/*.tf` and deployment scripts exist | understates implementation and sends operators to a past plan | correct only when canonical AWS page is created in PR-MD4; preserve deployment-ready/not deployed boundary |
| AWS README title is PR-numbered | `infra/aws/sensing/README.md` calls itself the PR-A5 packet | capability is discoverable only through migration vocabulary | retain infrastructure detail but route from capability page |
| Many PR-numbered runbooks compete with current docs | 15 `docs/runbooks/pr*.md` files | obsolete commands can appear authoritative | classify/banner after replacements in PR-MD6 |
| Multiple loop and publication entrances overlap | Makefile, `bin/`, app entrypoints, and several runbooks | unclear golden path and recovery owner | select one owner per task in PR-MD4; reference alternatives explicitly |
| Runtime evidence is time-bound | two dated evidence pages | past success may be mistaken for current operation | label historical; new status claims require current evidence |
| Notes bundles are unusually visible | two large `notes/` bundles contain prompts and contracts | search results can outrank current source | preserve as supporting/historical and add canonical routing |
| Compatibility and archive scripts remain discoverable | `scripts/compat_wrappers/`, `scripts/archive/` | contributors may extend the wrong surface | component guides must name owner modules and compatibility boundary |
| No docs router or automated link/canonicality gate | no `docs/README.md`; no documentation check target | orphaning and drift recur | PR-MD1 router; PR-MD6 quality gate |

No files are deleted or broadly rewritten in PR-MD0. Potentially orphaned content remains preserved until inbound-link checking and human review in PR-MD6.

## Proposed canonical owner by common reader task

| Reader need | Proposed page | Planned PR |
|---|---|---|
| Choose a route by audience/task/status | `docs/README.md` | PR-MD1 |
| Understand end-to-end system and maturity | `docs/architecture/system-overview.md` | PR-MD2 |
| Resolve lane and owner boundaries | `docs/architecture/lane-and-owner-boundaries.md` | PR-MD2 |
| Resolve artifacts, writers, identities, replay, trust | architecture pages named in the target stack | PR-MD2 |
| Change acquire, enrich, editorial, or site | `docs/components/<component>.md` | PR-MD3 |
| Find exact command/config/schema/path/status | `docs/reference/*.md` | PR-MD3 |
| Run local lanes or an immutable sensing bundle | matching `docs/operations/*.md` | PR-MD4 |
| Compact/replay/recover sensing | `docs/operations/sensing-compaction-and-recovery.md` | PR-MD4 |
| Deploy/verify/tear down AWS sensing | `docs/operations/aws-sensing-deployment.md` | PR-MD4 |
| Approve/publish editorial output | `docs/operations/editorial-human-last-mile.md` | PR-MD4 |
| Build/deploy site snapshot | `docs/operations/site-snapshot-and-vercel.md` | PR-MD4 |
| Evaluate retrofit/publication decisions | `docs/case-studies/*.md` | PR-MD5 |
| Interpret old PR plans and notes | `docs/historical/README.md` | PR-MD6 |

## Status boundary

At the inspected commit, AWS sensing has source, image definition, task adapters, Terraform, deployment scripts, and local test evidence described in the repository. It is **deployment-ready**, not evidenced here as **deployed** or **operated**. PR-MD0 performs no AWS or Vercel operation and makes no provider-state claim.
