# Runtime evidence: 20260101T10

Status: PR1b implementation evidence capture (current container snapshot).

## Commands executed

```bash
make preflight-runtime DIGEST_AT=20260101T10
DIGEST_AT=20260101T10 bash bin/run_hour.sh
make ls DIGEST_AT=20260101T10
```

## Observed outputs

### 1) preflight

Output:

```text
[preflight] repo=/workspace/media_monitor
[preflight] ERROR missing project python: ./.venv/bin/python
make: *** [makefile:40: preflight-runtime] Error 2
```

Interpretation:
- runtime cannot start because project venv is absent at expected path.

### 2) hourly wrapper

Output:

```text
[hourly] start DIGEST_AT=20260101T10
[hourly] ERROR: missing venv activate script: /workspace/media_monitor/.venv/bin/activate
[hourly] Hint: create project venv at /workspace/media_monitor/.venv or set VENV_ACTIVATE
```

Interpretation:
- relocation-safe path logic works (repo-relative), and failure is explicit/preflighted.

### 3) stage artifact listing

Output:

```text
== rss_dumps ==
== digest_map ==
== digest_jsonls ==
== pf_in ==
== pf_out ==
== drafts ==
== quarantine ==
```

Interpretation:
- no stage artifacts produced in this environment due preflight failure before stage execution.

## Root-cause diagnosis (post-relocation)

1. Project venv path was previously hardcoded to `/home/matias/repos/media_monitor/.venv/bin/activate`.
2. After relocation, that hardcoded path is invalid.
3. Runtime also depends on Python deps (`pandas`, `feedparser`) and PF runtime availability.
4. Therefore golden-path break is currently environment/path portability + dependency readiness, not contract logic.

## Minimal fixes implemented in PR1b

- `bin/run_hour.sh`
  - switched to repo-relative root and venv activation (`$REPO_ROOT/.venv/bin/activate` by default),
  - added explicit preflight error messaging and `VENV_ACTIVATE` override,
  - added PF runtime/source logging and configurable `PF_RUNS_DIR`/`PF_CONDA_ENV`.

- `makefile`
  - added `preflight-runtime` target for quick readiness checks,
  - added stage dependency probe messaging,
  - removed duplicate `pf-legacy` / `pf-article` recipes that created noisy warnings.

## Next action to complete full runtime validation

Provision runtime env in this snapshot and rerun:

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt   # or equivalent dependency bootstrap
make preflight-runtime DIGEST_AT=20260101T10
make s01 DIGEST_AT=20260101T10 DRY_RUN=0
make s02 DIGEST_AT=20260101T10 DRY_RUN=0
make s03 DIGEST_AT=20260101T10 DRY_RUN=0
make s04 DIGEST_AT=20260101T10 DRY_RUN=0 PF_MODE=legacy
make s05 DIGEST_AT=20260101T10 DRY_RUN=0
make ls  DIGEST_AT=20260101T10
```
