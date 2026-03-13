# PR1b Design: Runtime validation and recovery evidence (pre-PR3 gate)

Status: proposed (design-only)

## Goal

Re-center migration on the **current runnable snapshot** before implementing PR3 adapters.

PR1b is a short validation/recovery phase to prove the golden path and produce artifact evidence.

## Scope (strict)

- Validate the current operational path stage-by-stage.
- Identify root-cause(s) of post-relocation failures.
- Apply only minimal patch candidates in these categories:
  - path portability,
  - environment/preflight,
  - logging/evidence.

## Out of scope

- No contract changes (`contracts/*`).
- No monorepo reorg/moves.
- No PromptFlow replacement.
- No runtime logic rewrite.

---

## A) Exact golden path for current snapshot

Primary manual path (from current `Makefile` and `bin/run_hour.sh`):

1. `s01` → `legacy.stage01_digests`
2. `s02` → `legacy.stage02_master_index_update`
3. `s03` → `legacy.stage03_headlines_digests`
4. `s04` → PromptFlow CLI over digest-level input (default `PF_MODE=legacy`)
5. `s05` → `legacy.stage05_explode_pf_outputs`

Canonical all-in-one command:

```bash
make all DIGEST_AT=<YYYYMMDDTHH> DRY_RUN=0
```

Operational cron wrapper:

```bash
bin/run_hour.sh
```

---

## B) Exact manual commands (stage-by-stage)

Use one fixed hour bucket for reproducibility:

```bash
export DIGEST_AT=20260101T10
export DRY_RUN=0
export NULL_SINK=0
```

Preflight snapshot:

```bash
make env
python --version
./.venv/bin/python --version
```

Run stages manually:

```bash
make s01 DIGEST_AT=$DIGEST_AT DRY_RUN=$DRY_RUN NULL_SINK=$NULL_SINK
make s02 DIGEST_AT=$DIGEST_AT DRY_RUN=$DRY_RUN NULL_SINK=$NULL_SINK
make s03 DIGEST_AT=$DIGEST_AT DRY_RUN=$DRY_RUN NULL_SINK=$NULL_SINK
make s04 DIGEST_AT=$DIGEST_AT DRY_RUN=$DRY_RUN NULL_SINK=$NULL_SINK PF_MODE=legacy
make s05 DIGEST_AT=$DIGEST_AT DRY_RUN=$DRY_RUN NULL_SINK=$NULL_SINK
```

Quick artifact listing:

```bash
make ls DIGEST_AT=$DIGEST_AT
```

---

## C) Expected artifacts per stage (evidence contract)

For `DIGEST_AT=<hour>`:

### Stage 01

Expected:
- `data/rss_slices/rss_dumps/*_<hour>00.csv`
- optional mirror: `data/slices/jsonl/<hour>.jsonl`
- quarantine on malformed rows/errors: `data/quarantine/V01_*.jsonl`

### Stage 02

Expected:
- `data/digest_map/<hour>.csv`
- `data/master_ref.csv`
- quarantine: `data/quarantine/V02_*.jsonl`

### Stage 03

Expected:
- `data/digest_jsonls/<hour>.jsonl`
- optional markdown digest output (if enabled by stage config)
- quarantine: `data/quarantine/V03_*.jsonl`

### Stage 04

Expected:
- PromptFlow run under `~/.promptflow/.runs/.../flow_outputs/output.jsonl`
- copied output in project: `data/pf_out/pfout_<hour>_<ts>.jsonl`
- quarantine: `data/quarantine/V04_*.jsonl`

### Stage 05

Expected:
- `data/drafts/<hour>/*.jsonl` when joins/validations pass
- quarantine on misses/validation issues: `data/quarantine/V05_*.jsonl`
- possible no-op with explicit log when no PF outputs or no digest map

---

## D) Root-cause analysis targets for post-relocation break

PR1b must confirm/falsify each with evidence:

1. **Hardcoded repository path in cron wrapper**
   - `bin/run_hour.sh` activates `/home/matias/repos/media_monitor/.venv/bin/activate` and sets `PYTHONPATH` to same absolute path.
   - After relocation, this can break venv activation/imports.

2. **PF environment ambiguity**
   - `Makefile:s04` expects `PF_PYTHON` or working PF module on selected Python.
   - `bin/run_hour.sh` may fall back to `conda run -n new_env`.
   - Mismatch between project venv and PF environment can cause stage04 failures.

3. **PF input-surface drift**
   - `Makefile:s04` default input is digest-level `data/digest_jsonls/<hour>.jsonl` (`PF_MODE=legacy`).
   - `legacy/stage04_promptflow_run.py` header still describes `data/pf_in/pfin_<hour>.jsonl`.
   - Need explicit declaration of currently canonical input path for runtime.

4. **Run-record API drift (known, not solved in PR1b)**
   - `backend.db.finish_run(run_id, ok, fail)` vs stage calls using extra kwargs (`stage=`, `meta=`).
   - PR1b should document drift and avoid pretending telemetry is standardized.

5. **Latest-run selection ambiguity in PF output copy**
   - wrapper picks latest `~/.promptflow/.runs/flow_variant_0_*`; stale run folders may be selected.
   - PR1b should improve evidence logging for selected run folder/file.

---

## E) Minimal patch set (proposal only; implement in PR1b)

Allowed minimal patches:

1. `bin/run_hour.sh`
   - Replace hardcoded venv/PYTHONPATH with repo-relative discovery.
   - Add preflight checks and explicit error messages if PF runtime missing.
   - Log chosen PF input and selected PF output source path.

2. `Makefile` (small)
   - Add explicit preflight target(s) for Python/PF availability and required dirs.
   - Keep stage logic intact.

3. Optional tiny docs update
   - Add runtime runbook section with reproducible manual commands and known caveats.

Not allowed in PR1b:
- schema/contract edits,
- adapter implementation,
- moving runtime modules.

---

## F) Acceptance checklist with evidence files

PR1b completion requires the following evidence bundle for one fixed hour:

- [ ] `docs/runbooks/runtime-evidence-<hour>.md` with command log + outcomes.
- [ ] stage artifacts listed with concrete paths/sizes (`make ls DIGEST_AT=<hour>` output).
- [ ] presence/absence explanation per stage (including no-op cases).
- [ ] root-cause section citing exact failing command/error snippet.
- [ ] explicit statement whether PF foreground run succeeds in current environment.
- [ ] explicit statement that runtime logic was not rewritten.

Recommended evidence captures:

```bash
make env
make s01 DIGEST_AT=<hour> DRY_RUN=0
make s02 DIGEST_AT=<hour> DRY_RUN=0
make s03 DIGEST_AT=<hour> DRY_RUN=0
make s04 DIGEST_AT=<hour> DRY_RUN=0 PF_MODE=legacy
make s05 DIGEST_AT=<hour> DRY_RUN=0
make ls  DIGEST_AT=<hour>
```

---

## PR3 gate after PR1b

Only after PR1b is approved/completed, redesign PR3 adapters from **verified runtime seams**:

- stable buses from validated current outputs,
- experimental buses from validated PF/stage seams,
- with manifests/run-record minimums and explicit source→contract mapping.
