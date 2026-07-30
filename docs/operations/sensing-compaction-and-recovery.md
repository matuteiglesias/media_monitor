# Sensing compaction, replay, and recovery

> **Status:** canonical runbook · **Owner:** sensing compactor · **Verified against:** `e068f5a`

## Preflight and execute

List finalized run directories; preserve the existing pointer; use explicit roots:

```bash
python scripts/compact_sensing_bundles.py --run-root artifacts/sensing_runs --state-root storage/sensing_compacted
```

## Reconcile

Verify the selected generation exists and its manifest/checksums match; `accepted_runs.json` contains one deterministic attempt per digest; rejected runs have reasons; `lane_status.json` agrees; `current.json` names the complete generation. Re-run the command over unchanged inputs and require the same generation identity.

## Replay/recovery

Restore truth from immutable runs, never by editing a generation. Add/recover finalized bundles, rerun compaction, then optionally mirror the selected generation with `make promote-sensing-bundle-local`. If the pointer is corrupt, retain it as evidence and rerun the sole writer; never point manually to an incomplete generation. Lock contention means another writer exists: stop and investigate. Checksum mismatch, unsafe path, missing candidate, error status, or unfinalized run must remain rejected.
