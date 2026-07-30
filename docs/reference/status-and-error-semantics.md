# Status and error semantics

> **Status:** canonical reference · **Verified against:** `7723918`

## Evidence maturity

`designed` → `implemented` → `locally validated` → `deployment-ready` → `deployed` → `operated`. Each transition requires its own evidence; source/IaC cannot prove provider operation.

## Runtime statuses

| Surface | Values/behavior | Meaning |
|---|---|---|
| stage result | `success` / `error`, return code | command outcome only |
| sensing bundle | `success`, `partial_success`, `empty_success`, `error` | output/quarantine/failure classification; only eligible finalized statuses compact |
| compactor | accepted/rejected runs; `empty` or latest status | validation/selection result with rejection reasons |
| schema status | contract-defined enum | lifecycle of a contract record, not process health |
| enrich fetch | `fetch_status`, `error_code`, `error_message` | explicit content acquisition result |
| editorial | draft/fallback/quarantine/index metrics | derived readiness; never human approval |
| published article | `status=published`, review status | valid only after explicit approval gate |
| site snapshot | `status`, metrics, deterministic ID | validated projection identity/content |

## Failure rules

Exit zero is insufficient when state changes: reconcile artifacts, schema, checksums, manifest/finalization, pointer target, counts, and source hashes. Missing or malformed required input fails rather than fabricating state. Quarantine preserves invalid records for diagnosis. Retry must preserve stable logical identity and must not overwrite immutable evidence. Public/UI surfaces cannot upgrade internal status or approve content.
