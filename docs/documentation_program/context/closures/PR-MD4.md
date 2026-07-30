# PR-MD4 documentation closure

- **Status:** ACCEPTED
- **Repository commit inspected:** `e068f5a`
- **Human acceptance required:** received in follow-up instruction

## Goal completed

Created six separate canonical operational golden paths for local lanes, immutable sensing bundles, compaction/recovery, AWS deployment/first task, editorial human publication, and site snapshot/Vercel publication. Each includes preflight, execution, independent reconciliation, failure/stop behavior, retry identity, and rollback/teardown where applicable.

## Source truth inspected

Make targets and lane entrypoints; owner source/runbooks; run-bundle/compactor/S3 code and tests; AWS scripts/Terraform/IAM; editorial handoff/promotion/index validation; site snapshot/roll/build code and tests.

## Verification

Focused tests for sensing, AWS packet, editorial publication, and site roll passed. CLI help/dry-run surfaces, relative links, and whitespace were checked. Artifact-writing and provider-mutating examples are explicitly labeled unverified and were not run.

## Drift and decisions

The missing minimal-loop enrich wrapper and missing aggregate-site npm scripts are denied in canonical paths rather than hidden. PR-era runbooks remain preserved but no longer own the procedures linked from the docs router. AWS/Vercel provider operation is not claimed.

## Proposed carry update

- `next_pr`: `PR-MD5` after human acceptance
- blockers: none known; acceptance of PR-MD4 required
- reader-facing change: six executable/reconcilable golden paths with explicit stop rules
- maintenance obligation: command, recovery, denial, teardown, or evidence changes update the owning operation page
