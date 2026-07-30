# media_monitor target documentation stack v0.1

## Target tree

```text
README.md
AGENTS.md
docs/
  README.md
  getting-started/
    local-sensing.md
    first-editorial-handoff.md
    first-approved-publication.md
  architecture/
    system-overview.md
    lane-and-owner-boundaries.md
    artifact-ladder-and-state.md
    identity-provenance-and-replay.md
    trust-boundaries.md
    decisions/
  components/
    news-acquire.md
    news-enrich.md
    news-editorial.md
    news-site.md
  operations/
    local-lane-operation.md
    sensing-run-bundles.md
    sensing-compaction-and-recovery.md
    aws-sensing-deployment.md
    editorial-human-last-mile.md
    site-snapshot-and-vercel.md
  reference/
    command-matrix.md
    configuration.md
    contracts-and-schemas.md
    buses-indexes-and-snapshots.md
    status-and-error-semantics.md
    storage-layout.md
  case-studies/
    aws-immutable-sensing-retrofit.md
    deterministic-site-publication.md
  historical/
    README.md
  documentation_program/
    ...
```

## Stack contracts

### Root README

Keep the existing concise product identity and one golden-path promise. Add only
the minimum architecture/status and reader routing needed to reach canonical
docs. Do not duplicate runbooks.

### Documentation router

`docs/README.md` owns navigation by audience, task, component, and maturity
status. It is the canonical map for current vs historical material.

### Architecture

Architecture pages explain:

- sensing, enrich, editorial, publication, and site boundaries;
- owner modules and compatibility wrappers;
- artifact levels and state writers;
- stable identities and provenance;
- immutable run bundles, compaction, snapshots, and mutable pointers;
- local, AWS, and Vercel trust boundaries.

### Component guides

Each owner guide describes purpose, ownership, inputs, outputs, contracts,
commands, invariants, dependencies, tests, failure behavior, and extension
points. App-local READMEs may link to these pages or remain concise mirrors.

### Operations

Each repeated task has one canonical runbook. Distinct tasks stay distinct:

- legacy/local lane run;
- immutable sensing bundle;
- compaction/replay/recovery;
- AWS deployment and first task;
- editorial approval/publication;
- site snapshot and Vercel deployment.

### Reference

Reference pages catalog commands, configuration, contracts, buses, indexes,
snapshots, storage paths, state/status values, and ownership. They should be
searchable by exact identifier.

### Case studies

Case studies explain engineering decisions and evidence without becoming
operational instructions. The AWS case must show producer/compactor authority,
idempotency, replay safety, IAM denial proof, infrastructure, and current status.

### Historical layer

PR-numbered runbooks, migration plans, old sprint documents, and retrofit
bundles remain traceable but do not own current commands.
