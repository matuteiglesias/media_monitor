# Sensing Writer and Side-Effect Inventory v0.1

**Scope:** current `bin/run_minimal_loop_once.sh --lane sensing` behavior at PR-A0.  This is characterization, not a desired cloud design.

## Execution order and controls

The shell fixes one `DIGEST_AT`, then runs `s01`, `s02`, `s03`, `export_pr3a`, and `build_news_access_indexes` serially under `set -e`. Each command is independently wrapped by `run_with_run_record.py`. The exit trap writes lane status after success or the first failed command.

| Knob | Present behavior |
|---|---|
| `DIGEST_AT` | Selects deterministic stage filenames/windows and is forwarded to all five commands. It is not a unique attempt ID. |
| `DRY_RUN` | In s01 it disables both RSS network acquisition and scrape enqueue. In s02/s03 it disables DB data writes but not local artifact writes or best-effort run bookkeeping. Export/index commands do not receive it. |
| `NULL_SINK` | Redirects major s01-s03 outputs beneath `data/_tmp/null`; quarantine remains under the normal data root. The minimal-loop shell does not explicitly forward it, but Make inherits exported/environment values. |
| `DATA_DIR` | Parameterizes acquisition stage roots. Export defaults independently to `data`; access indexes default independently to `storage`. |
| `RUN_ID` | Optional per-stage DB bookkeeping identity. Without it, each stage derives `<stage>:<digest_at>`, so a retry reuses the same ID. |

## Writer map

| Path or surface | Owner | Mutation | Scope | Retry and failure behavior |
|---|---|---|---|---|
| `data/rss_slices/rss_dumps/<window>_<digest>00.csv` | s01 | direct overwrite (`to_csv`) | digest/window | Same digest replaces files that are produced, but stale files for windows no longer produced are not removed. A mid-loop failure can leave a subset. |
| `data/slices/jsonl/<digest>.jsonl` | s01 | temp file then unlink/rename | digest | Same digest replaces content when at least one valid row exists. Empty retries leave an older mirror untouched. |
| `data/quarantine/V01_<run_id>.jsonl` | s01 | append | stage/run identity | Reusing the derived run ID appends retry failures to the same file. Enqueue errors are quarantined and do not fail s01. |
| Postgres `work_items` (`stage=scrape`) | s01 | insert, conflict no-op | cumulative queue | Only attempted when `DRY_RUN=0`; coupled to network acquisition. Errors are quarantined and suppressed. |
| Postgres `runs` | s01-s03 | insert/update intended | stage/run identity | `start_run` errors are suppressed. Every `finish_run` call passes unsupported `stage`/`meta` keywords, raises `TypeError`, and is suppressed, so finalization does not execute. Derived IDs also collide on same-digest retry. |
| `data/digest_map/<digest>.csv` | s02 | direct overwrite (`to_csv`) | digest | Deterministically replaces the digest map after valid input. Read/validation failure may leave the prior map. |
| `data/master_ref.csv` | s02 | direct overwrite (`to_csv`) | cumulative | Read/merge/write is not atomic. Same-digest replay deduplicates by stable `index_id`, but can rewrite the cumulative file; interruption can corrupt it. |
| `data/quarantine/V02_<run_id>.jsonl` | s02 | append | stage/run identity | Read, validation, and optional DB-upsert errors accumulate; DB-upsert errors do not fail the stage. |
| Postgres `master_ref` | s02 | upsert | cumulative | Skipped by `DRY_RUN`; errors are quarantined and suppressed after local files have already changed. |
| `data/digest_jsonls/<digest>.jsonl` | s03 | temp file then unlink/rename | digest | Same digest replaces only when groups exist; an empty retry leaves old output. |
| `data/output_digests/headlines_<window>_<digest>_<topic>_<group>.md` | s03 | direct overwrite | digest/group | Produced groups overwrite matching names; obsolete group mirrors are not removed. Partial sets can remain on failure. |
| `data/quarantine/V03_<run_id>.jsonl` | s03 | append | stage/run identity | Read/validation failures append. Missing map is reported as successful no-op; missing required columns raise and fail. |
| `storage/buses/news_ref.v1/<digest>_<export_at>.jsonl` and `news_digest_group.v1/...` | exporter | direct overwrite of timestamped name | export invocation | Normally new timestamped artifacts; a same-second retry can overwrite. Contract validation fails fast. |
| Adjacent bus manifest JSON files | exporter | direct overwrite | export invocation | Written with each successful bus export; a failure can leave one bus/manifest without the other. |
| `storage/runs/pr3a_export_<digest>_<export_at>.json` | exporter | direct overwrite | export invocation | Written only after both export functions return. A prior partial bus can remain when absent. |
| `storage/indexes/pr3a_exports_latest.json` | exporter | direct overwrite | latest | Replaced on successful export after run record; no atomic replace. |
| `storage/indexes/pr3a_exports_<digest>_<export_at>.json` | exporter | direct overwrite | export invocation | Timestamped audit record, with same-second collision possibility. |
| `storage/indexes/pr3a_export_compact_latest.json` | exporter | read/modify/direct overwrite | latest | Written on both success and caught failure. Failure retains previous success counts/time but changes failure status. |
| `storage/indexes/pr3a_export_compact_<digest>_<export_at>.json` | exporter | direct overwrite | export invocation | Records success or caught failure; same-second collision possible. |
| `storage/indexes/news_recent_refs_latest.jsonl`, `news_recent_groups_latest.jsonl` | access-index builder | direct overwrite | latest | Both are written sequentially, not atomically as a pair. Failure between writes yields a mixed generation. |
| Timestamped `news_recent_{refs,groups}_<digest>_<built_at>.jsonl` | access-index builder | direct overwrite | build invocation | Written only after both latest files; same-second retries collide. |
| `storage/observability/logs/<uuid>.log` | per-command wrapper | direct create/overwrite | wrapper run | UUID makes collisions unlikely; child stdout/stderr survives failure. |
| `storage/observability/manifests/<uuid>.json` | per-command wrapper | direct create/overwrite | wrapper run | Written after the child exits, including failures; wrapper interruption before emission leaves no manifest. |
| `storage/observability/run_records.jsonl` | per-command wrapper | append | cumulative | One record per stage command, not one sensing execution. Concurrent append has no lock. |
| `storage/observability/status/sensing_latest.json` | per-command wrapper | direct overwrite | latest | Replaced after every stage, so it represents the last child command. |
| `storage/observability/status/summary.json` | per-command wrapper | read/recompute/direct overwrite | cumulative/latest | Rewritten after every stage from run records and lane latest files; malformed records are skipped. |
| Same lane-latest and summary paths | outer shell exit trap | direct overwrite/read-modify-overwrite | latest | Competes with wrapper. It preserves some wrapper fields but sets `last_run_id` from the previous payload and rewrites final lane status from the shell exit code. |
| `storage/observability/heartbeat.log` and `.pid` | heartbeat/Make helpers | shell append/truncate and overwrite | latest/process | Outside one run, but launches this sensing lane repeatedly and adds another operational status surface. |

## Proven characterization and repair targets

1. **Same digest is replace-in-place, not immutable replay.** Stable IDs reduce row duplication, while digest artifacts and mutable cumulative/latest files are overwritten. Empty or early-failed retries can leave stale outputs from an earlier attempt.
2. **Bookkeeping success is not trustworthy.** The DB finish helper accepts `(run_id, ok, fail)`, but stages pass `stage` and `meta`; broad exception handling hides the mismatch.
3. **`DRY_RUN` has multiple meanings.** It prevents the only RSS fetch and enqueue in s01, prevents the s02 master upsert, and prevents s03 DB intent, while local filesystem creation/writes remain enabled.
4. **Failure evidence is partial but not transactionally grouped.** The wrapper records a failed command and its captured logs, while stage/export/index files already written remain. Latest status is mutated by both the wrapper and outer trap.
5. **There is no single run owner.** Five wrapper UUIDs describe one shell invocation, each stage attempts a separate DB run, exporter writes another run record, and two layers claim lane-latest ownership.

These facts validate the embryo sequence: PR-A1 should repair local control and ownership semantics before PR-A2 introduces immutable per-run roots.
