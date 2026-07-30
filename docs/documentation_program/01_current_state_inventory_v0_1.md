# media_monitor documentation current-state inventory v0.1

## Existing strengths

The root README already states a concise product route—news input to brief,
draft, and human last mile—and explicitly requires a visible canonical path.
Owner modules have local README/runbook pairs. Contracts, buses, indexes,
publication tooling, Vercel paths, and the new AWS sensing substrate all have
substantial documentation or executable evidence.

## Current documentation surfaces

| Surface | Current role | Program treatment |
|---|---|---|
| `README.md` | product front door and local golden path | preserve concise role; verify against current architecture |
| `apps/news_acquire/{README,runbook}.md` | acquisition ownership and operations | split durable owner guide from canonical runbooks/reference |
| `apps/news_enrich/{README,runbook}.md` | enrichment ownership and operations | same |
| `apps/news_editorial/{README,runbook}.md` | editorial ownership and operations | same |
| `docs/runbooks/` | many implementation, migration, publication, and sprint runbooks | inventory; promote capability runbooks; mark PR-era material historical |
| `docs/notes/`, `docs/legacy/`, `legacy/notes/` | working memory and historical records | noncanonical, preserve selectively |
| `infra/aws/sensing/README.md` | current AWS deployment packet | promote/link from canonical operations/deployment docs |
| `notes/media_monitor_aws_codex_retrofit_bundle_v0_1/` | governed retrofit plan and closure record | historical/supporting evidence |
| contracts, schemas, tests, storage layouts, scripts | executable truth | primary verification sources |

## Confirmed drift example

The current acquisition runbook describes the AWS task adapter and then says
Terraform remains future PR-A5 work. Current main now contains the Terraform
deployment packet under `infra/aws/sensing/`. This is exactly the kind of
cross-document drift the program must remove.

## Main gaps

1. Too many potential entrances: root README, app READMEs, app runbooks,
   PR-numbered runbooks, notes, retrofit bundle, and infrastructure README.
2. Capability documentation and historical migration narrative are mixed.
3. The artifact ladder is distributed across many files rather than one
   canonical architecture/reference surface.
4. Writer authority and replay/compaction semantics are not visible from the root.
5. The new AWS sensing architecture is not integrated into the whole-system story.
6. Contract/schema catalog, identity rules, and storage/index semantics lack one
   navigable reference.
7. Local sensing, immutable bundle execution, AWS task execution, compaction,
   site snapshot, human approval, and Vercel deployment need distinct golden paths.
8. No documentation maintenance/validation gate.
9. No root agent contract before this seed.

## Inventory required in PR-MD0

- all Markdown/text documentation;
- all Make targets, scripts, and owner entrypoints;
- all environment variables/config files;
- contract schemas and examples;
- buses, indexes, snapshots, mutable pointers, and writer owners;
- deployment surfaces for AWS and Vercel;
- tests that verify operational/documentation claims;
- duplicated, stale, contradictory, and orphaned instructions;
- historical PR labels embedded in supposedly current docs.

Do not equate recent modification time with canonicality.
