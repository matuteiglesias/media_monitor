# WP01 — Media Publication → Cloud Logging

**Contract:** `evidence:producer-run-receipt@1`
**Producer:** `producer.github.media-publication`
**GCP project:** `estate-observability-510700`
**Log:** `estate-producer-run` (routed to dedicated bucket `estate-producer-runs`)

## Producer-owned semantics

The existing `scripts/emit_media_publication_receipt.py` emits the canonical
receipt *before* any GCP operation and runs under `if: always()`. This captures
failed and partial publication cycles. It derives artifact/terminal acceptance
from the publication guard, site roll, anonymous deployment verification,
crawler verification, and workflow state—not from GitHub's job conclusion alone.

The new `scripts/export_media_publication_gcp.py` is a **transport adapter**,
not a second semantic emitter or a replacement receipt schema. It enforces the
published receipt's fixed producer, stage names, output kinds and durability,
scheduler run/attempt, metadata-only refs, and privacy boundary. It constructs
the same G2 `receipt_sha256`, deterministic `insertId`, JSON projection,
labels and severity as the central estate exporter.

The estate `projects` repository is private. A public Media Monitor workflow
must not clone it using a personal token or publish its contents. Hence the
small source-local transport adapter, with compatibility tests.

## Keyless IAM

GitHub Actions workload identity pool `estate-producer-github`, provider
`media-publication-main-oidc`:

- Issuer: GitHub Actions OIDC.
- Repo: `matuteiglesias/media_monitor`, immutable repo ID `992285444`.
- Branch: `refs/heads/main`.
- Workflow identity: `matuteiglesias/media_monitor/.github/workflows/scheduled-publication.yml@refs/heads/main`.
- Allowed events: `schedule` or `workflow_dispatch`.
- Dedicated service account: `estate-media-receipt-writer@estate-observability-510700.iam.gserviceaccount.com`.
- GCP project role: `roles/logging.logWriter` **only**.
- Service-account WIF role: `roles/iam.workloadIdentityUser` for the Media Monitor repository principal set.

No service-account private keys, human ADC refresh tokens, or broad log-reading
permissions are introduced. The GitHub workflow has `contents:read` and
`id-token:write`, not repository write permission.

## Publication must never depend on telemetry transport

The workflow orders operations:

1. Normal sensing, guards, deploy and public verification.
2. **Always emit** the canonical publication receipt; failure outcomes remain failure.
3. Authenticate with keyless OIDC, only when receipt emission succeeded.
4. Export one validated receipt; the adapter performs a Cloud Logging dry-run
   before a real `entries.write`.
5. Summarize authentication/export outcome independently.
6. **Always upload** publication-cycle evidence containing the original receipt
   (14-day retention).

Steps 3–4 use GitHub `continue-on-error: true`. If GCP authentication or
networking fails, the publication's own success/failure status is unchanged,
and the receipt is retained for a later authorized backfill. The GitHub job
summary and warning annotation signal the degraded *transport* without
fabricating a failed publication.

## Idempotence / replay

A canonical receipt is identified by
`(producer_id, run_id, sha256(canonical receipt JSON))`. Its SHA-256
`insertId` matches the central G2 exporter. Retries therefore retain one
**logical** event under the existing G3 SQL deduplication, even if Cloud Logging
accepts an occasional physically duplicated record (the API's `insertId`
deduplication is best effort). Different run attempts have distinct IDs.

## Acceptance evidence to collect

- Unit tests cover healthy, failed and missing/unsafe metadata, run identity,
  deterministic payload and HTTP success/failure.
- Validate against the known October 24 real producer-owned receipt; its
  `insertId` must match the central exporter.
- Review a normal scheduled workflow run after merge; check `gcp_auth`,
  `gcp_export`, and uploaded evidence.
- Query `estate-producer-runs/_AllLogs` by exact `insertId` and verify
  the semantic dimensions and physical destination. `_Default` should contain
  zero matches.
- Repeat on a second real cycle; failure-only cycles are valid evidence
  of error observability but not substitutes for two successful publications.

## Reproduction / recovery

```bash
python3 scripts/export_media_publication_gcp.py \
  --receipt storage/runs/producer_receipts/media-publication-<RUN_ID>-<ATTEMPT>.json \
  --scheduler-run-id <RUN_ID> --run-attempt <ATTEMPT> --validate-only

# Only with appropriate (keyless or operator) credentials:
python3 scripts/export_media_publication_gcp.py \
  --receipt storage/runs/producer_receipts/media-publication-<RUN_ID>-<ATTEMPT>.json \
  --scheduler-run-id <RUN_ID> --run-attempt <ATTEMPT> --write
```

Rollback: revert the `scheduled-publication.yml` transport steps and
remove the Media provider/WIF grant and dedicated service account, leaving
the original producer-owned emitter and publication schedule intact.
