# Codex Prompt — PR-A0: Install retrofit governance and characterize sensing mutation

Read `CODEX_START_HERE.md`, embryo plan, starting context, sprint contract, and carry state.

Execute only PR-A0.

## Goal

Install the retrofit control surface and add a trustworthy characterization of the current sensing path, writers, side effects, and failure behavior.

## Required work

1. Add the supplied retrofit documents.
2. Trace `run_minimal_loop_once.sh --lane sensing` through s01–s03, export, indexes, and run/status wrappers.
3. Produce a writer inventory with:
   - path/surface;
   - owner;
   - append/replace/atomic behavior;
   - scope: per-run/cumulative/latest;
   - behavior on retry/failure.
4. Add focused characterization tests for:
   - repeated `DIGEST_AT`;
   - run-record/status writers;
   - DB bookkeeping signature/exception behavior;
   - `DRY_RUN` semantics;
   - failure and partial artifact behavior.
5. Produce `context/closures/PR-A0.md`.
6. Propose `PR-A1`.

## Non-goals

- No fixes.
- No AWS SDK/Terraform/Docker.
- No editorial/enrich/site changes.

## Done

The next PR can repair precise proven defects without repeating pipeline archaeology.
