# ADR 0001: Immutable runs and single-writer canonical state

- **Status:** accepted from implemented source
- **Decision owners:** sensing producer and compactor maintainers
- **Verified against:** `bf04a74`

## Context

Sensing retries, local/cloud execution, and mutable “latest” files can lose evidence or make replay order-dependent when every producer may update shared state.

## Decision

Producers create immutable, uniquely identified run bundles and finalize them last. A separate compactor validates evidence, deterministically selects one attempt per logical digest, writes an immutable content-derived generation, and alone updates the mutable current pointer. Local filesystem and S3 adapters preserve the same authority split.

## Consequences

- retries preserve evidence and idempotent uploads require byte equality;
- canonical state is reproducible from run evidence;
- readers see a complete generation through one pointer;
- producer IAM must deny out-of-prefix/canonical writes;
- compactor availability is required for promotion, but producer execution cannot corrupt shared latest state.

## Rejected alternatives

- Producers directly overwrite cumulative/latest state: unsafe under concurrency and replay.
- Timestamp-only “latest”: insufficient identity and nondeterministic under retry.
- Treat process exit zero as finalization: does not reconcile artifacts/checksums.
