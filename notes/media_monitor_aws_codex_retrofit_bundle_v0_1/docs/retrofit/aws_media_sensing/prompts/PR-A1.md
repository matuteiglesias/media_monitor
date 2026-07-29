# Codex Prompt — PR-A1: Repair sensing bookkeeping, configuration, and side-effect controls

Prerequisite: PR-A0 is accepted.

## Goal

Make the local sensing path internally coherent and explicit before isolating cloud runs.

## Scope

- Correct run start/finish bookkeeping contracts.
- Stop suppressing errors that invalidate run evidence; preserve best-effort only where explicitly accepted.
- Separate controls for network fetch, artifact writes, optional DB bookkeeping, and scrape enqueue.
- Move RSS feed definitions into a validated configuration artifact while preserving defaults.
- Choose one producer-side owner for run record and lane status.
- Keep the current local golden path compatible through documented defaults.

## Tests

- successful, failed, and partial run bookkeeping;
- each side-effect knob independently;
- invalid feed configuration;
- compatibility command;
- no editorial/enrich regression.

No AWS code.

Produce `context/closures/PR-A1.md` and propose `PR-A2`.
