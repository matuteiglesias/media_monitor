# Runbooks index

## Read first

1. `../current_state.md`
2. `../architecture/artifact_ladder.md`
3. `pr5-minimal-autonomous-loop.md`
4. `pr6-wrapper-surface-inventory.md`
5. `pr9-newspaper-skin-implementation-prs.md`

## Active operations

| Runbook | Status | Use for |
|---|---|---|
| `pr5-minimal-autonomous-loop.md` | active | lane-based operation |
| `pr6-wrapper-surface-inventory.md` | active | allowed commands and wrapper classification |
| `pr9-newspaper-skin-implementation-prs.md` | active | public site implementation |
| `newspaper_skin_guide.md` | active guide | constraints for site/Codex work |

## Active consolidation

| Runbook | Status | Use for |
|---|---|---|
| `pr5-observability-indexes-prep.md` | active design | observability boundary |
| `pr5-pruning-diagnostic-and-phased-plan.md` | active design | pruning with guardrails |
| `pr7-editorial-handoff-5day-sprint-plan.md` | active/near-term | editorial handoff dominance |
| `pr8-wrap-up-and-next-prs.md` | planning | next PR sequence |

## Migration records

| Runbook | Status | Use for |
|---|---|---|
| `pr4a-*` | historical/current ownership record | acquire ownership |
| `pr4b-*` | historical/current ownership record | editorial ownership |
| `pr4c-*` | migration record | acquire code migration |
| `pr4d-*` | migration record | editorial code migration |
| `pr4e-*` | migration record | enrich code migration |

## Historical runtime evidence

| Runbook | Status | Use for |
|---|---|---|
| `pr1b-runtime-validation-recovery-plan.md` | superseded recovery baseline | old golden path and preflight logic |
| `runtime-evidence-20260101T10.md` | historical evidence | relocation/env failure |
| `runtime-evidence-20260313T15.md` | historical evidence | stage execution and PF connection failure |




If a runbook mentions `legacy`, `data/*`, or `bin/run_hour.sh`, interpret it through the artifact ladder:

- `data/*` is Level 0 runtime workspace.
- `legacy/*` is compatibility unless the current command contract says otherwise.
- new integrations should consume `storage/buses/*` or `storage/indexes/*`.
- public surfaces should consume hardened snapshots or compact indexes, not raw runtime files.


