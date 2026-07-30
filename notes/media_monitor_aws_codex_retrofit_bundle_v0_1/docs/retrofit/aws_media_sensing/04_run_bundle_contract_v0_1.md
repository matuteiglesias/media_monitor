# Immutable Sensing Run Bundle Contract v0.1

## Identity and replay

- `logical_run_id` is `sensing:<DIGEST_AT>`.
- `run_id` is `sensing:<DIGEST_AT>:attempt:<n>:<uuid>` unless explicitly supplied.
- Attempts for one logical digest always use different directories.
- A finalized `run_id` is never overwritten; reuse fails closed.

## Layout

```text
runs/<run_id>/
  inputs/
    sensing_feeds.v1.yaml
    master_ref.csv                 # when local input state exists
  stage_outputs/
    rss_slices/
    digest_map/
    digest_jsonls/
    output_digests/
  contracts/buses/
  candidates/
    master_ref.csv
    news_recent_refs.jsonl
    news_recent_groups.jsonl
  evidence/
    quarantine/
    export_runs/
    logs/<stage>.{stdout,stderr}.log
    stage_results.jsonl
    exception.json                 # error runs only
    checksums.json
  run_record.json
  manifest.json
  FINALIZED
```

The bundle never contains a mutable `latest` name. Candidate promotion is not
part of finalization.

## Finalization

The producer assembles a private staging directory, calculates SHA-256 values,
writes the run record and manifest, writes `FINALIZED` last, and atomically
renames staging into `runs/<run_id>`. A failed pipeline is finalized with its
partial outputs, logs, stage results, and exception evidence. A staging failure
never appears beneath `runs/`.

Contractual statuses are:

- `success`: stages succeeded and candidate outputs are non-empty;
- `partial_success`: stages succeeded with quarantine evidence;
- `empty_success`: stages succeeded with zero reference and group candidates;
- `error`: a stage exited non-zero.

The CLI exits non-zero for `error` while retaining the finalized evidence bundle.

## Compatibility boundary

As completed by PR-A3, `promote_sensing_bundle_local.py` is only a mirror for the
generation already selected by the compactor. It cannot accept or select a run
bundle. Ordering, duplicate, replay, and out-of-order decisions belong exclusively
to the compactor.
