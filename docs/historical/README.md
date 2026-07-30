# Historical and supporting documentation

> **Status:** canonical classification index · **Verified against:** `65e8c0d`

These files preserve decisions, migrations, incidents, runtime evidence, and working memory but do **not** own current commands. Start at the [documentation router](../README.md) for current architecture, components, references, and operations.

| Surface | Classification | Preserved value | Canonical replacement |
|---|---|---|---|
| `docs/runbooks/pr*.md` | historical PR/migration plans | sequencing, rationale, migration evidence | [operations](../operations/) and [components](../components/) |
| dated `docs/runbooks/runtime-evidence-*` | historical runtime evidence | past environment/failure observations | current operation page plus new evidence packet |
| `docs/notes/*` | working memory/historical | handoffs and sprint context | router/carry state |
| `docs/legacy/*`, `legacy/*` | historical implementation/context | original design and compatibility evidence | architecture/components/reference |
| `docs/architecture/artifact_ladder.md`, `utility_inventory.md`, `docs/product/*` | supporting precursor/ideas | earlier ladder and product exploration | [canonical architecture](../architecture/system-overview.md) |
| `notes/media_monitor_aws_codex_retrofit_bundle_v0_1` | historical governed retrofit | contracts and accepted PR-A closure evidence | AWS case study/runbook |
| `notes/media-monitor-documentation-seed-v0_1` | historical seed bundle | program origin | root `AGENTS.md` and `docs/documentation_program` |
| app-local runbooks/READMEs | supporting implementation context | module-local detail | canonical component/operation pages |
| `infra/aws/sensing/README.md` | supporting infrastructure detail | IaC-adjacent prerequisites | canonical AWS operation page |

Nothing in these surfaces is deleted by PR-MD6. Unique evidence remains addressable. A historical command may be reproduced only in an isolated investigation and must be revalidated against current source.
