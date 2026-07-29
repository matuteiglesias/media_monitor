# Codex Prompt — PR-A3: Deterministic single-writer compactor

Prerequisite: PR-A2 is accepted.

## Goal

Build the sole owner of cumulative and latest sensing state from immutable run bundles.

## Scope

- pure/near-pure compaction API;
- canonical master reference;
- recent refs/groups access indexes;
- accepted/latest run pointer and lane status;
- deterministic ordering;
- duplicate and out-of-order input handling;
- atomic local publication;
- fixtures and property/regression tests.

## Non-goals

- No S3.
- No editorial/enrich outputs.
- No scheduler.

The sensing task must no longer be conceptually responsible for cumulative/latest state.

Produce `context/closures/PR-A3.md` and propose `PR-A4`.
