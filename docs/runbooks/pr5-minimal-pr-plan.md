# PR5 minimal plan (small, low-risk PRs)

## PR-A: clarify ownership and wrapper intent

- Add explicit header notes in wrapper scripts/modules.
- Add concise map in docs: canonical runtime vs owner source-of-truth vs compatibility wrappers.
- No behavior change.

## PR-B: archive historical noise safely

- Create `notes/archive/` (and optionally `docs/runbooks/archive/`) for historical-only artifacts.
- Move low-signal historical notes/evidence snapshots without deleting content.
- Add index/readme to point to active docs.

## PR-C: add run-record wrapper utility

- Add lightweight command wrapper emitting run record + log + manifest pointer.
- Keep it optional first; no forced integration into canonical pipeline yet.

## PR-D: wire minimal telemetry pointers

- Adopt wrapper in one safe path first (e.g., export job or non-critical stage wrapper).
- Verify append behavior and failure capture.

## PR-E: aggregator-facing bootstrap

- Provide sample producer output mapping for downstream single-writer compactor:
  - projects source rows
  - runs source JSONL
  - optional corpus delta inputs
- Keep compaction/index-writing out of multi-writer runtime paths.

## Done criteria

- Runtime continuity preserved.
- Clearer ownership taxonomy.
- At least one reliable run-record emission path available.
- Clean handoff to external single-writer index compaction.
