#!/usr/bin/env bash
set -euo pipefail

: "${HOME:=/home/matias}"

CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}"
LOCKFILE="${CACHE_DIR}/media_monitor_hourly.lock"
mkdir -p "$(dirname "$LOCKFILE")"
exec 9>"$LOCKFILE"
flock -n 9 || { echo "[hourly] another run is active, exiting."; exit 0; }

cd "$(dirname "$0")/.."

HOUR_UTC="$(date -u +%Y%m%dT%H)"
export DIGEST_AT="${DIGEST_AT:-$HOUR_UTC}"

echo "[hourly] start DIGEST_AT=${DIGEST_AT}"

# --- Stages 01/02/03 in project venv
. /home/matias/repos/media_monitor/.venv/bin/activate
export PYTHONPATH="/home/matias/repos/media_monitor"

make s01 DIGEST_AT="$DIGEST_AT" DRY_RUN=0
make s02 DIGEST_AT="$DIGEST_AT" DRY_RUN=0
make s03 DIGEST_AT="$DIGEST_AT" DRY_RUN=0

# --- Stage 04: PromptFlow only if a digest_jsonl exists
PF_IN="data/digest_jsonls/${DIGEST_AT}.jsonl"

pick_pf_data_file() {
  local wanted="${PF_IN}"
  if [[ -s "${wanted}" ]]; then
    echo "${wanted}"
    return 0
  fi
  # fallback: most recent digest_jsonls file
  local latest
  latest=$(ls -t data/digest_jsonls/*.jsonl 2>/dev/null | head -n1 || true)
  if [[ -n "${latest}" && -s "${latest}" ]]; then
    echo "${latest}"
    return 0
  fi
  echo ""
  return 1
}

DATA_FILE="$(pick_pf_data_file)"
if [[ -z "${DATA_FILE}" ]]; then
  echo "[hourly] no digest_jsonls available (wanted ${PF_IN}); skipping PF and 05"
  echo "[hourly] done DIGEST_AT=${DIGEST_AT}"
  exit 0
fi

echo "[hourly] PF input: ${DATA_FILE}"

# Prefer explicit PF_PYTHON (python that has promptflow), else conda run
if [[ -n "${PF_PYTHON:-}" && -x "${PF_PYTHON}" ]]; then
  "${PF_PYTHON}" -m promptflow._cli.pf run create \
     --flow ./flow \
     --data "${DATA_FILE}"
elif command -v conda >/dev/null 2>&1; then
  conda run -n new_env python -m promptflow._cli.pf run create \
     --flow ./flow \
     --data "${DATA_FILE}"
else
  echo "[hourly] ERROR: Neither PF_PYTHON set nor 'conda' on PATH; cannot run PF." >&2
  exit 127
fi

# Copy most recent PF output into data/pf_out/
latest=$(ls -td -- ~/.promptflow/.runs/flow_variant_0_* 2>/dev/null | head -n1 || true)
if [[ -n "$latest" && -f "$latest/flow_outputs/output.jsonl" ]]; then
  ts=$(date +%H%M%S)
  mkdir -p data/pf_out
  cp "$latest/flow_outputs/output.jsonl" "data/pf_out/pfout_${DIGEST_AT}_${ts}.jsonl"
  echo "[hourly] PF output copied → data/pf_out/pfout_${DIGEST_AT}_${ts}.jsonl"
else
  echo "[hourly] WARN: no PF output.jsonl found under ~/.promptflow/.runs"
fi


# --- Stage 05 back in project venv (we're already in it)
make s05 DIGEST_AT="$DIGEST_AT" DRY_RUN=0

echo "[hourly] done DIGEST_AT=${DIGEST_AT}"
