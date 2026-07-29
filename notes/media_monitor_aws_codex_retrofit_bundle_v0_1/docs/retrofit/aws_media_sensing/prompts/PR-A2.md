# Codex Prompt — PR-A2: Per-run working root and immutable sensing bundle

Prerequisite: PR-A1 is accepted.

## Goal

Make one sensing execution self-contained, immutable after finalization, and replayable.

## Scope

- configurable run root;
- run/digest identity;
- input configuration snapshot;
- s01–s03 outputs;
- exported buses and compact-index candidates;
- run record, manifest, checksums, exception inventory;
- explicit successful/partial/failed finalization;
- compatibility promotion kept separate.

## Required behavior

- no mutable `latest` output inside the run bundle;
- repeated same-digest semantics documented and tested;
- failure still yields a valid evidence bundle;
- stable IDs and schema validation preserved.

Produce `context/closures/PR-A2.md` and propose `PR-A3`.
