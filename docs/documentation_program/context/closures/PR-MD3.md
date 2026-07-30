# PR-MD3 documentation closure

- **Status:** ACCEPTED
- **Repository commit inspected:** `7723918`
- **Human acceptance required:** received in follow-up instruction

## Goal completed

Created canonical guides for acquire, enrich, editorial, and site ownership plus searchable reference catalogs for commands, configuration, contracts, identities, buses, indexes, snapshots, storage, statuses, and errors. App-local READMEs now link to canonical guides rather than being silently promoted.

## Source truth inspected

Owner source/entrypoints and tests; Makefile/bin/scripts; schemas/fixtures; bus/index/snapshot writers; storage layouts; AWS adapters/IaC; site package/build/validation; canonical architecture and PR-MD0 inventory.

## Documents produced or changed

- four `docs/components/*.md` owner guides;
- five `docs/reference/*.md` catalogs;
- docs-router component/reference links;
- app-local acquire/enrich/editorial links;
- accepted PR-MD2, this closure, and pending PR-MD4 proposal.

## Commands and links verified

```text
python -m pytest contracts/tests/test_contracts.py tests/test_export_pr3a_buses.py tests/test_build_news_access_indexes.py tests/test_build_enrich_access_indexes.py tests/test_news_enrich_service.py tests/test_news_editorial_briefs_pipeline.py tests/test_build_editorial_access_indexes.py tests/test_editorial_handoff_packet.py tests/test_validate_publish_surface.py tests/test_build_site_snapshot.py tests/test_validate_site_snapshot.py tests/test_roll_site.py
npm --prefix apps/news_site run test:refresh-data
node --test apps/news_site/scripts/validate_site_snapshot.test.mjs
python <relative-Markdown-link checker>
git diff --check
```

No operational, artifact-writing, AWS, or Vercel command was run.

## Drift found

The aggregate site publish script/package mismatch, absent minimal-loop enrich wrapper, PR-numbered runbook routing, and stale acquire Terraform statement remain documented. Exact environment defaults are distributed across parsers and will benefit from automated extraction in later maintenance work.

## Decisions made

Component pages own purpose/boundaries/invariants; reference pages own exact identifiers; PR-MD4 will own procedures. Schemas remain field-level authority, and compatibility/archive surfaces are not extension points.

## Known limitations

Operational preflight/recovery/teardown is intentionally deferred to PR-MD4. App-local prose is preserved pending PR-MD6 classification. The catalogs are manually maintained until the documentation quality gate exists.

## Proposed carry update

- `next_pr`: `PR-MD4` after human acceptance
- blockers: none known; acceptance of PR-MD3 is required
- reader-facing change: canonical component ownership and searchable exact-identifier references
- maintenance obligation: owner, command, config, schema, storage, or status changes must update the matching guide/catalog
