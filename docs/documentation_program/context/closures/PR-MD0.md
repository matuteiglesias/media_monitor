# PR-MD0 documentation closure

- **Status:** ACCEPTED
- **Repository commit inspected:** `58ec15c94f7a21fbf47587967518a64649835129`
- **Documentation paths changed:** root program overlay and `docs/documentation_program/06_inventory_and_canonicality_map_v0_1.md`
- **Human acceptance required:** received in the follow-up instruction

## Goal completed

Produced the bounded file-level inventory, command/entrypoint and configuration matrices, schema catalog, artifact authority matrix, drift register, and proposed canonical owner map required by PR-MD0. No pipeline semantics or operational procedures changed.

## Source truth inspected

- tracked documentation and repository tree;
- root Makefile, lane entrypoints, `bin/`, operational scripts, and compatibility/archive surfaces;
- owner-module source and environment access;
- contract schemas, fixtures, and tests;
- storage/index/snapshot builders and validators;
- AWS Terraform, Dockerfile, deploy/first-task scripts, task adapters, and retrofit closure evidence;
- site package scripts and validators.

## Documents produced or changed

- Installed the documentation program seed at its intended root paths.
- Added the reviewable inventory and canonicality map.
- Added this closure note.
- Added a non-accepting carry-state proposal for PR-MD1.

## Commands and links verified

```text
git ls-files
find . -maxdepth 4 -type f | sort
rg -n <targeted source/config/storage patterns> <scoped paths>
python -m pytest contracts/tests/test_contracts.py
python -m pytest  # collection blocked by removed legacy `backend` package in two tests
npm --prefix apps/news_site run test:refresh-data
node --test apps/news_site/scripts/validate_site_snapshot.test.mjs
terraform -chdir=infra/aws/sensing fmt -check  # unverified: Terraform is unavailable in this environment
python scripts/run_sensing_bundle.py --help
python scripts/compact_sensing_bundles.py --help
```

Relative links in the program files were checked programmatically. Commands that mutate pipeline or provider state were intentionally not run.

## Drift found

- `apps/news_acquire/runbook.md` says Terraform remains PR-A5 work, while current main contains the Terraform deployment packet.
- PR-numbered runbooks, overlapping loop/publication entrances, dated runtime evidence, historical bundles, and compatibility scripts compete in search with current owner surfaces.
- No documentation router or automated documentation gate currently exists.

## Decisions made

- Inventory rather than rewrite, move, delete, or silently promote.
- Classify notes and PR-era documents as supporting/historical proposals pending human review.
- Keep AWS status at deployment-ready, with no deployed/operated claim.
- Propose capability-oriented owners from the accepted target stack.

## Known limitations

- Classification and proposed ownership require human acceptance.
- Provider-side AWS/Vercel state was not inspected or changed.
- Runtime commands that write artifacts were inventoried but not executed because PR-MD0 is documentation-only.
- The full Python suite cannot collect `tests/test_ids.py` and `tests/test_models.py` because both import the absent legacy `backend` package; the focused contract test passes.

## Proposed carry update

- `next_pr`: `PR-MD1` after human acceptance
- blockers: none known; acceptance of PR-MD0 is required
- reader-facing change: one reviewed inventory of competing sources and proposed owners
- maintenance obligation: keep inventory claims tied to source and record new drift until the quality gate exists
