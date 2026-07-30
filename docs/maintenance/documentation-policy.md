# Documentation maintenance policy

> **Status:** canonical policy · **Owner:** repository maintainers · **Verified against:** `65e8c0d`

## Change obligations

A PR changing commands/entrypoints, ownership, configuration, schema/identity, bus/index/snapshot layout, writer authority, AWS/Vercel infrastructure, approval/publication, or maturity status must name and update the affected canonical page. `N/A` requires a reason.

Canonical pages live in `docs/architecture`, `components`, `operations`, `reference`, `case-studies`, and `maintenance`. They require a visible `Status`, working relative links, capability-oriented names, source/test evidence, and honest maturity language. Procedures have one canonical owner; supporting pages link rather than copy.

## Review and validation

Run `make docs-check`. Review claims against executable source, schemas, tests, artifacts, IaC, or provider evidence. Commands must be executed or labeled unverified. Mermaid diagrams require adjacent prose. Provider status may advance to deployed/operated only with retained provider evidence.

## Migration/deprecation

Classify first; create and verify replacement; link old to new; preserve unique decisions/incidents; check inbound links; delete only with human confirmation. PR-numbered documents cannot become permanent canonical owners.
