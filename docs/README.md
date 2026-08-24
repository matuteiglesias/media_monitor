# Documentation map

This page is the current front door to `media_monitor` documentation. It routes
readers to the best available source without turning plans, dated evidence, or
PR-era migration records into canonical operating instructions.

## Canonical public surfaces

- **Public outlet:** https://mediamonitor-psi.vercel.app
- **Public health:** https://mediamonitor-psi.vercel.app/api/health
- **Documentation:** https://github.com/matuteiglesias/media_monitor/tree/main/docs
- **Repository:** https://github.com/matuteiglesias/media_monitor
- **Owner / portfolio:** https://main.matuteiglesias.link

These surfaces are the public identity boundary for Media Monitor. Preview,
branch, or older deployment URLs are deployment artifacts rather than alternate
public identities. Machine-readable ownership lives in
[`apps/news_site/config/public_identity.json`](../apps/news_site/config/public_identity.json).

The calibrated external claim is **deployed governed news-intelligence and editorial
publishing system**. “Live/current” is stronger than “deployed”: it should be asserted
only when `/api/health` reports `freshness_status=FRESH`, `is_current=true`, and
`within_target=true`.

The short local path remains in the [root README](../README.md). The repository
does not yet have all of the capability-oriented pages planned by the
[documentation program](documentation_program/02_target_docs_stack_v0_1.md), so
the links below name the current supporting source and the known status honestly.

## Choose a route

| Reader | Start here | Then use |
|---|---|---|
| Evaluator | [Product route and quickstart](../README.md) | [artifact ladder](architecture/artifact_ladder.md), [product maps](product/product_maps.md), and the status matrix below |
| Operator | [Local lane route](../README.md#-ruta-canónica-operativa) | [owner runbooks](#components-and-owners), [site publication](runbooks/news-site-publishing.md), or [AWS sensing packet](../infra/aws/sensing/README.md) |
| Contributor | [Components and owners](#components-and-owners) | [contracts](../contracts/README.md), [utility inventory](architecture/utility_inventory.md), and tests adjacent to the changed source |
| Agent | [root operating contract](../AGENTS.md) | [canonicality inventory](documentation_program/06_inventory_and_canonicality_map_v0_1.md) and executable source before prose |
| Maintainer | [canonicality inventory](documentation_program/06_inventory_and_canonicality_map_v0_1.md) | [documentation program](documentation_program/CODEX_START_HERE.md) and its closure records |

## Architecture

Start with the [system overview](architecture/system-overview.md), then use
[lane and owner boundaries](architecture/lane-and-owner-boundaries.md),
[artifact ladder and state](architecture/artifact-ladder-and-state.md),
[identity, provenance, and replay](architecture/identity-provenance-and-replay.md),
and [trust boundaries](architecture/trust-boundaries.md). The governing sensing
decision is [ADR 0001](architecture/decisions/0001-immutable-runs-single-writer-state.md).

## Capability and evidence status

Status terms follow the program evidence ladder: **implemented** means source
exists; **locally validated** means focused local checks exist and pass;
**deployment-ready** additionally requires the deployment adapter/IaC/runbook;
**deployed** requires provider-side evidence; **operated repeatedly** requires run/health
evidence rather than merely a schedule declaration. A later state is never inferred
from an earlier one.

| Capability | Current status | Evidence and current route | Boundary / known gap |
|---|---|---|---|
| Local sensing stages and access indexes | implemented; focused tests locally validated | root `Makefile`, `apps/news_acquire`, `bin/run_minimal_loop_once.sh`; [acquire runbook](../apps/news_acquire/runbook.md) | network, PostgreSQL, and PromptFlow-dependent execution is environment-specific |
| Immutable sensing run bundles | implemented; locally validated | `scripts/run_sensing_bundle.py`, bundle/compactor tests; [acquire runbook](../apps/news_acquire/runbook.md) | local validation is not AWS operation |
| Deterministic sensing compaction | implemented; locally validated | `scripts/compact_sensing_bundles.py` and compactor tests | AWS compaction is not deployed by the current Terraform packet |
| AWS manual sensing task substrate | deployment-ready | `Dockerfile.sensing`, task adapters, Terraform, deploy/first-task/teardown scripts; [AWS packet](../infra/aws/sensing/README.md) | no provider evidence in this repository establishes deployed or operated AWS status; no AWS schedule, alarms, Lambda, or deployed compaction |
| Enrichment owner module | implemented; focused tests locally validated | `apps/news_enrich`; canonical minimal-loop compatibility wrapper delegates to the owner entrypoint; [owner README](../apps/news_enrich/README.md) and [runbook](../apps/news_enrich/runbook.md) | live fetch/queue execution remains environment-specific |
| Editorial brief/draft/index path | implemented; focused tests locally validated | `apps/news_editorial`, editorial/index tests; [owner README](../apps/news_editorial/README.md) and [runbook](../apps/news_editorial/runbook.md) | PromptFlow and live-data execution require external runtime inputs |
| Human-approved article promotion | implemented; focused tests locally validated; C3 rehearsal exercised real promotion/index code in isolation | `scripts/promote_draft_to_published.py`, `scripts/build_published_article_indexes.py`, promotion/index tests; [C3 rehearsal PR](https://github.com/matuteiglesias/media_monitor/pull/64) | actual publication approval remains intentionally human; no representative article is claimed before that decision |
| Publication-aware snapshot and roll | implemented; focused tests locally validated; canonical Vercel deployment evidenced | `site_snapshot.v2`, snapshot builder/validator, `scripts/roll_site.py`, site-roll tests; [source-site roll](runbooks/site-roll.md) | repeated scheduled production success remains a separate operational-evidence claim |
| Scheduled public refresh | implemented; contract-tested; production workflow registered | [scheduled workflow](../.github/workflows/scheduled-publication.yml), pre-deploy freshness guard, anonymous post-deploy verifier | schedule presence is not itself proof of repeated successful operation; use Actions evidence and public health |
| Next.js news site | **deployed**; focused Node tests green; canonical public identity and request-time freshness health defined | `apps/news_site`, `apps/news_site/config/public_identity.json`, `/api/health`; [runtime CI reference](https://github.com/matuteiglesias/media_monitor/actions/runs/32770941754) | current/live status is conditional on the health invariant, not merely URL reachability |

## Current task routes

These are links, not duplicated runbooks. Run commands only after reading the
linked page's prerequisites and current-source caveats.

| Task | Current best route | Planned canonical owner |
|---|---|---|
| Run sensing/editorial locally | [root golden path](../README.md#-ruta-canónica-operativa) | [local lane operation](operations/local-lane-operation.md) |
| Run an immutable sensing bundle | [acquire runbook](../apps/news_acquire/runbook.md) plus current scripts | [sensing run bundles](operations/sensing-run-bundles.md) |
| Compact or recover sensing state | current compactor source and [AWS packet](../infra/aws/sensing/README.md) | [compaction and recovery](operations/sensing-compaction-and-recovery.md) |
| Deploy a manual AWS sensing task | [AWS sensing packet](../infra/aws/sensing/README.md) | [AWS sensing deployment](operations/aws-sensing-deployment.md) |
| Review and publish editorial output | [root last mile](../README.md#-last-mile-página-simple-de-publicación) and [editorial runbook](../apps/news_editorial/runbook.md) | [editorial human last mile](operations/editorial-human-last-mile.md) |
| Build or roll a site snapshot | [source-site roll](runbooks/site-roll.md) and [publishing audit](runbooks/news-site-publishing.md) | [site snapshot and Vercel](operations/site-snapshot-and-vercel.md) |
| Look up contracts | [contracts README](../contracts/README.md) and `contracts/schemas/` | `reference/contracts-and-schemas.md` (PR-MD3) |

## Reference catalogs

- [Commands](reference/command-matrix.md)
- [Configuration](reference/configuration.md)
- [Contracts and schemas](reference/contracts-and-schemas.md)
- [Buses, indexes, snapshots, and storage](reference/buses-indexes-and-storage.md)
- [Status and error semantics](reference/status-and-error-semantics.md)

## Components and owners

| Component | Owns | Current guide |
|---|---|---|
| `news_acquire` | feed acquisition, grouping, sensing bundle production | [canonical guide](components/news-acquire.md) |
| `news_enrich` | scraping/enrichment behind contract seams | [canonical guide](components/news-enrich.md) |
| `news_editorial` | PromptFlow handoff, briefs, drafts, editorial indexes | [canonical guide](components/news-editorial.md) |
| `news_site` | generated public snapshot rendering and health surface | [canonical guide](components/news-site.md) |

Compatibility wrappers and `legacy/` remain discoverable but are not preferred
extension points. PR-numbered runbooks, `docs/notes/`, `docs/legacy/`, and both
bundles under `notes/` are supporting or historical unless a canonical page
explicitly promotes a claim from them.

## Case studies

- [AWS immutable sensing retrofit](case-studies/aws-immutable-sensing-retrofit.md)
- [Deterministic site and publication snapshots](case-studies/deterministic-site-publication.md)

## Known documentation drift

- The [acquire runbook](../apps/news_acquire/runbook.md) still says Terraform is
  future PR-A5 work, while [`infra/aws/sensing`](../infra/aws/sensing/) contains
  the deployment packet. Trust the infrastructure/source and retain the exact
  deployment-ready—not deployed or operated—AWS status.
- [`docs/runbooks/README.md`](runbooks/README.md) routes through PR-numbered plans
  and links a missing `docs/current_state.md`; use this page as the reader front
  door instead.

See the [PR-MD0 inventory](documentation_program/06_inventory_and_canonicality_map_v0_1.md)
for the complete drift register and proposed ownership map. No historical file
has been moved or deleted.

## Documentation maintenance

Use the [historical classification](historical/README.md), [maintenance policy](maintenance/documentation-policy.md), and [coverage/known-gaps report](maintenance/coverage-and-known-gaps.md). Run `make docs-check` before review.
