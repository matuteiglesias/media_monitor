# Runtime evidence: 20260313T15 (PR1c)

Status: verified stage execution on provisioned environment for snapshot runtime path.

## Environment provisioning used

```bash
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install pandas feedparser pydantic psycopg[binary]
```

PromptFlow runtime candidate:
- `python` (global) with `promptflow==1.18.3` available.

## Preflight

Command:

```bash
make preflight-runtime DIGEST_AT=20260313T15
```

Result:

```text
[preflight] repo=/workspace/media_monitor
[preflight] project python: Python 3.12.12
[preflight] stage01 deps import: OK (pandas, feedparser)
[preflight] WARN postgres unreachable (stages continue with quarantine fallbacks)
[preflight] PF python candidate: python
[preflight] promptflow import: OK via PF_PYTHON
[preflight] required data dirs ensured
```

## Golden path execution (manual)

Commands:

```bash
make s01 DIGEST_AT=20260313T15 DRY_RUN=0 LIMIT=20
make s02 DIGEST_AT=20260313T15 DRY_RUN=0
make s03 DIGEST_AT=20260313T15 DRY_RUN=0
make s04 DIGEST_AT=20260313T15 DRY_RUN=0 PF_MODE=legacy PF_PYTHON=python
make s05 DIGEST_AT=20260313T15 DRY_RUN=0
make ls  DIGEST_AT=20260313T15
```

Exit codes observed:

- `s01=0`
- `s02=0`
- `s03=0`
- `s04=2`
- `s05=0`

### Stage-by-stage results

### s01

Output:

```text
[01_digests] digest_id=20260313T15 ok=1 bad=0 slices=1 dry_run=False null_sink=False
```

Produced:
- `data/rss_slices/rss_dumps/1h_window_20260313T1500.csv`

### s02

Output:

```text
[02_master_index_update] digest_id=20260313T15 ok=1 bad=0 files=1 dry_run=False null_sink=False
```

Produced:
- `data/digest_map/20260313T15.csv`
- `data/master_ref.csv`

### s03

Output:

```text
[03_headlines_digests] digest_id=20260313T15 groups=1 bad=0 -> data/digest_jsonls/20260313T15.jsonl
```

Produced:
- `data/digest_jsonls/20260313T15.jsonl`

### s04

Output:

```text
[s04] PF input: data/digest_jsonls/20260313T15.jsonl
...Submitting run flow_variant_0_20260313_151338_076810...
pf.run.create failed with ConnectionNotFoundError: Connection 'open_ai_connection' is not found.
make: *** [makefile:92: s04] Error 1
```

Result:
- PF orchestration starts but fails due missing PromptFlow connection config (`open_ai_connection`).
- No `data/pf_out/pfout_20260313T15*` generated in this environment.

### s05

Output:

```text
[05_explode_pf_outputs] no PF outputs for 20260313T15 in data/pf_out
```

Result:
- consumption path verified (clean no-op when `pf_out` absent).
- no drafts generated for this run.

## Artifact snapshot

`make ls DIGEST_AT=20260313T15`:

```text
== rss_dumps ==
data/rss_slices/rss_dumps/1h_window_20260313T1500.csv
== digest_map ==
data/digest_map/20260313T15.csv
== digest_jsonls ==
-rw-r--r-- 1 root root 410 Mar 13 15:13 data/digest_jsonls/20260313T15.jsonl
== pf_in ==
== pf_out ==
== drafts ==
== quarantine ==
 - V01_01_digests:20260313T15.jsonl
 - V02_02_master_index_update:20260313T15.jsonl
```

## Runtime-path conclusion (PR1c)

- Effective runtime path remains `legacy.stage01..05` via Make targets.
- Stable upstream seams are now empirically confirmed in this snapshot:
  - Stage02: `data/digest_map/<hour>.csv`, `data/master_ref.csv`
  - Stage03: `data/digest_jsonls/<hour>.jsonl`
- Current blocker for full end-to-end completion is PF connection setup (`open_ai_connection`) rather than stage wiring.
- DB telemetry path still exhibits operational drift tolerance (stages continue with quarantine records when Postgres is unavailable).

## Actionable blocker fix for next run

Configure PromptFlow connection before rerunning `s04`:

```bash
pf connection create --file <connection.yaml-with-name-open_ai_connection>
```

Then rerun:

```bash
make s04 DIGEST_AT=20260313T15 DRY_RUN=0 PF_MODE=legacy PF_PYTHON=python
make s05 DIGEST_AT=20260313T15 DRY_RUN=0
make ls DIGEST_AT=20260313T15
```
