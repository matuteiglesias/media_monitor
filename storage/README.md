# Storage runbook (PR2 scaffolding)

This directory defines **storage boundaries** for the 3-component monorepo migration.

## Boundary model

- `storage/raw/*` = private component internals (not a public contract surface).
- `storage/buses/*` = versioned contract seams between producers and consumers.
- `storage/indexes/*` = compact read models for consumers/UI.
- `storage/snapshots/*` = publication/export artifacts with reproducible manifests.

## Governance notes

- Consumers should read **contracts + indexes**, not private raw trees.
- Any new producer/consumer integration should publish/consume via bus contracts and pass contract tests.
- Adapter policy: until migration completes, adapters may map legacy runtime outputs into bus/index/snapshot forms without replacing the runtime path.

## Status in PR2

- This is scaffolding and governance only.
- Legacy runtime (`legacy/stage01..05` + PromptFlow path) remains the operational path.
