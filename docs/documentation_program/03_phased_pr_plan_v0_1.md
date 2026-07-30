# media_monitor documentation production plan v0.1

| PR | Outcome | Reader value | Stop condition |
|---|---|---|---|
| PR-MD0 | full inventory and canonicality map | resolves competing documentation sources | reviewed inventory; no broad rewrite |
| PR-MD1 | root/docs front doors and status map | one coherent entrance | routes accepted; root remains concise |
| PR-MD2 | architecture, artifact ladder, identities | system becomes explainable end-to-end | diagrams and writer matrix reconcile |
| PR-MD3 | owner guides and contract/reference catalog | contributors/agents can work safely | four components and contract catalog complete |
| PR-MD4 | canonical operational golden paths | operators can execute, verify, and recover | commands verified; one owner per procedure |
| PR-MD5 | AWS sensing and publication case studies | cloud/reliability maturity becomes legible | evidence/status boundaries reviewed |
| PR-MD6 | migration, pruning, and docs quality gate | docs remain trustworthy | old docs classified; checks automated |

## PR-MD0 — inventory and canonicality

Deliver file-level documentation inventory, command/entrypoint matrix, artifact
writer/reader matrix, drift register, and proposed canonical owner page per task.
Explicitly compare current source to PR-era runbooks.

## PR-MD1 — front doors

Update the root README minimally and add `docs/README.md`. Preserve the promise
that the basic path is visible without archaeology. Add audience routes, a
current capability/status matrix, and links to current local and cloud paths.

## PR-MD2 — system architecture

Create:

- system overview;
- lane/owner boundaries;
- artifact ladder and state-writer map;
- identity/provenance/replay semantics;
- trust boundaries;
- selected ADRs.

Diagram the route from feeds to public snapshot/article, including immutable
sensing bundles and deterministic compaction.

## PR-MD3 — component and contract documentation

Create canonical guides for acquire, enrich, editorial, and news site.
Consolidate reference catalogs for schemas, buses, indexes, snapshots, storage
layout, status/error semantics, configuration, and commands.

## PR-MD4 — operational golden paths

Create/verify separate runbooks for:

1. local lane operation;
2. immutable sensing bundle;
3. compaction/replay/recovery;
4. AWS sensing deploy and first task;
5. editorial human last mile;
6. site snapshot and Vercel deployment.

Each runbook requires preflight, execution, independent verification, failure
handling, and evidence. AWS runbooks also require denied-access and teardown.

## PR-MD5 — evidence-based case studies

Create:

- AWS immutable sensing retrofit;
- deterministic site/publication snapshot case.

Show before/after architecture, decisions, constraints, rejected alternatives,
tests/evidence, and honest maturity status. Do not duplicate runbook commands.

## PR-MD6 — migration and quality gate

- classify PR-era runbooks and notes;
- add historical/superseded banners and canonical links;
- remove duplicate commands from supporting pages;
- add link/metadata validation;
- wire docs validation into repository quality checks;
- publish coverage and known-gaps report;
- define documentation obligations for code/contract/infra PRs.

## Optional later work

A generated site, visual screenshots, or automated schema/CLI extraction may
follow only after canonical Markdown ownership is stable.
