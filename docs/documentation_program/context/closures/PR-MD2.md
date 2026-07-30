# PR-MD2 documentation closure

- **Status:** ACCEPTED
- **Repository commit inspected:** `bf04a74506d28634c3076f835da472d3b4e04a1e`
- **Documentation paths changed:** canonical architecture pages, docs router, carry state, and closure records
- **Human acceptance required:** received in the follow-up instruction

## Goal completed

Created the bounded architecture set: system overview, lane/owner boundaries, artifact/state authority map, identity/provenance/replay semantics, trust boundaries, and one necessary ADR for immutable runs plus single-writer canonical state. Every mutable pointer named by this PR has one writer.

## Source truth inspected

- acquire stages, run-bundle finalization, compactor, local promotion, S3 adapter, and AWS task adapters;
- bus exporters, index builders, schemas, fixtures, and focused tests;
- enrich owner/service/worker and PostgreSQL boundary;
- editorial stages, draft generation, handoff/index builders, and tests;
- human-gated promotion, published indexes, public snapshot builders/validators, site roll, and tests;
- Dockerfile, Terraform/IAM/network/storage/compute, deployment/first-task/teardown scripts;
- root/docs front doors and existing architecture/product prose.

## Documents produced or changed

- `docs/architecture/system-overview.md`
- `docs/architecture/lane-and-owner-boundaries.md`
- `docs/architecture/artifact-ladder-and-state.md`
- `docs/architecture/identity-provenance-and-replay.md`
- `docs/architecture/trust-boundaries.md`
- `docs/architecture/decisions/0001-immutable-runs-single-writer-state.md`
- architecture route in `docs/README.md`
- accepted PR-MD1 and proposed PR-MD3 in carry state

## Commands and links verified

```text
python -m pytest tests/test_sensing_run_bundle.py tests/test_sensing_compactor.py tests/test_sensing_s3_store.py tests/test_sensing_container_task.py tests/test_sensing_terraform_packet.py tests/test_news_enrich_service.py tests/test_news_editorial_briefs_pipeline.py tests/test_build_editorial_access_indexes.py tests/test_validate_publish_surface.py tests/test_build_site_snapshot.py tests/test_roll_site.py
python <local relative-Markdown-link checker>
python <Mermaid fence/text explanation checker>
git diff --check
```

No artifact-writing, AWS, or Vercel command was run. Architecture claims are source/test inspection, not provider operation evidence.

## Drift found

- The old `docs/architecture/artifact_ladder.md` labels some currently implemented buses as targets and does not model immutable runs/generations or published articles.
- Existing product prose describes reusable/product ideas alongside current architecture and should remain supporting rather than operational truth.
- Previously recorded enrich, aggregate publication, runbook-router, and acquire/AWS drift remains open outside PR-MD2 scope.

## Decisions made

- Make artifact boundaries—not Python call structure—the primary architecture seams.
- Separate immutable run/generation facts from mutable access pointers.
- Assign sensing `current.json` exclusively to the compactor and publication exclusively to the explicit human gate.
- Treat AWS and Vercel as trust/execution boundaries without inferring provider operation.
- Add only one ADR because the producer/compactor authority split is the cross-cutting decision requiring durable rationale.

## Known limitations

- Component/reference catalogs remain PR-MD3; operational commands and recovery steps remain PR-MD4.
- Existing architecture pages are preserved and not yet bannered/migrated; that classification work remains PR-MD6.
- Provider-side state was neither inspected nor changed.

## Proposed carry update

- `next_pr`: `PR-MD3` after human acceptance
- blockers: none known; acceptance of PR-MD2 is required
- reader-facing change: source-backed end-to-end architecture with explicit authority and trust boundaries
- maintenance obligation: changes to identity, writer authority, run finalization, compaction, approval, or snapshot provenance must update these pages
