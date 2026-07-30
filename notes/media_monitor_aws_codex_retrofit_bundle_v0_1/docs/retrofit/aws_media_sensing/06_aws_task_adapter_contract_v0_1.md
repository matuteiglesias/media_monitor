# AWS Task and Storage Adapter Contract v0.1

## S3 layout and ownership

```text
<prefix>/
  runs/<run_id>/...                    # producer; immutable PutObject only
  compacted/<generation>/...           # compactor; immutable PutObject only
  latest/current.json                  # compactor only; replace after generation
```

The producer API accepts one finalized local bundle and derives its prefix from
the manifest `run_id`. Every object uses `If-None-Match: *`; an identical retry is
a no-op, while different bytes at an existing key fail. `FINALIZED` uploads last.
The producer cannot list runs or write compacted/latest keys.

The compactor API may list/download finalized runs, upload one immutable
generation, and replace `latest/current.json` last. It cannot use the producer
upload API. No adapter appends JSONL or exposes a shared task-owned key.

## Application task role expectations

Producer application role:

- `s3:PutObject` on `<prefix>/runs/<task-run-id>/*`;
- `s3:GetObject` on the same prefix only, solely for idempotent retry comparison;
- optional secret/parameter reads only if a future accepted configuration needs
  them; none are required by this image.

Compactor application role:

- `s3:ListBucket` restricted by `s3:prefix` to `<prefix>/runs/*`;
- `s3:GetObject` on `<prefix>/runs/*`;
- `s3:PutObject` on `<prefix>/compacted/*` and `<prefix>/latest/current.json`.

The ECS task execution role is separate and should contain only image-pull and
CloudWatch Logs delivery permissions. IAM resources and policies are PR-A5 work.

## Task contract

`scripts/run_sensing_task.py` requires:

- `DIGEST_AT`;
- `SENSING_S3_BUCKET`;
- `SOURCE_COMMIT`;
- `IMAGE_DIGEST`.

Optional values are `SENSING_S3_PREFIX`, `RUN_ID`, `ATTEMPT`, and
`SENSING_TASK_TIMEOUT_SECONDS`. Timeout defaults to and may not exceed 900
seconds. The intended task size is 0.25 vCPU and 0.5–1 GiB memory with at most two
attempts; infrastructure enforcement belongs to PR-A5.

The entrypoint emits JSON lines for task start, every stage result, bundle
finalization, upload completion, and error. Each applicable event carries
`lane`, `run_id`, `digest_at`, `stage`, and `status`. The producer manifest binds
`run_id`, `source_commit`, and `image_digest`.

The task always uses `ENQUEUE_SCRAPE=0` and `DB_RUN_BOOKKEEPING=0` image defaults.
It invokes only acquisition s01–s03, contract export, and sensing index candidate
construction. Editorial, enrich, site, `.env`, and credentials are absent from
the image context and Docker copy list.

## Container

`Dockerfile.sensing` uses Python 3.12, exact Python dependency pins, a non-root
UID, unbuffered output, and the sensing task entrypoint. The image digest is
supplied by deployment as `IMAGE_DIGEST`; the task refuses to run without it.
The source commit is likewise required rather than inferred from an image that
does not contain `.git`.
