#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

INTERVAL_SEC="${INTERVAL_SEC:-3600}"
MAX_RUNS="${MAX_RUNS:-0}"
DIGEST_AT_MODE="${DIGEST_AT_MODE:-now}"  # now|fixed
FIXED_DIGEST_AT="${FIXED_DIGEST_AT:-}"

usage() {
  cat <<USAGE
Usage: $0 [--interval-sec N] [--max-runs N] [--digest-at-mode now|fixed] [--fixed-digest-at YYYYMMDDTHH]

Env passthrough to lane runner:
  DRY_RUN, PROJECT_ID, OPERATOR, TRIGGER_TYPE, ATTEMPT, RUN_RECORD_ALL_LANES

Notes:
  - MAX_RUNS=0 means run forever.
  - Writes heartbeat log to storage/observability/heartbeat.log.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval-sec)
      INTERVAL_SEC="${2:-}"
      shift 2
      ;;
    --max-runs)
      MAX_RUNS="${2:-}"
      shift 2
      ;;
    --digest-at-mode)
      DIGEST_AT_MODE="${2:-}"
      shift 2
      ;;
    --fixed-digest-at)
      FIXED_DIGEST_AT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if ! [[ "$INTERVAL_SEC" =~ ^[0-9]+$ ]] || [[ "$INTERVAL_SEC" -lt 1 ]]; then
  echo "INTERVAL_SEC must be a positive integer" >&2
  exit 2
fi
if ! [[ "$MAX_RUNS" =~ ^[0-9]+$ ]]; then
  echo "MAX_RUNS must be a non-negative integer" >&2
  exit 2
fi
if [[ "$DIGEST_AT_MODE" != "now" && "$DIGEST_AT_MODE" != "fixed" ]]; then
  echo "DIGEST_AT_MODE must be now|fixed" >&2
  exit 2
fi
if [[ "$DIGEST_AT_MODE" == "fixed" && -z "$FIXED_DIGEST_AT" ]]; then
  echo "--fixed-digest-at is required when --digest-at-mode fixed" >&2
  exit 2
fi

mkdir -p storage/observability
HEARTBEAT_LOG="storage/observability/heartbeat.log"
LOCKFILE="storage/observability/heartbeat.lock"

exec 9>"$LOCKFILE"
if ! flock -n 9; then
  echo "[heartbeat] another heartbeat process is already running" | tee -a "$HEARTBEAT_LOG"
  exit 0
fi

run_count=0
while true; do
  run_count=$((run_count + 1))
  started_epoch="$(date +%s)"
  started_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  if [[ "$DIGEST_AT_MODE" == "fixed" ]]; then
    DIGEST_AT="$FIXED_DIGEST_AT"
  else
    DIGEST_AT="$(date -u +%Y%m%dT%H)"
  fi

  echo "[heartbeat] run=${run_count} start=${started_iso} digest_at=${DIGEST_AT}" | tee -a "$HEARTBEAT_LOG"

  set +e
  DIGEST_AT="$DIGEST_AT" \
  TRIGGER_TYPE="${TRIGGER_TYPE:-timer}" \
  OPERATOR="${OPERATOR:-heartbeat}" \
  ATTEMPT="${ATTEMPT:-1}" \
  PROJECT_ID="${PROJECT_ID:-media_monitor}" \
  DRY_RUN="${DRY_RUN:-0}" \
  RUN_RECORD_ALL_LANES="${RUN_RECORD_ALL_LANES:-0}" \
  bin/run_minimal_loop_once.sh --lane sensing >> "$HEARTBEAT_LOG" 2>&1
  rc=$?
  set -e

  ended_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "[heartbeat] run=${run_count} end=${ended_iso} rc=${rc}" | tee -a "$HEARTBEAT_LOG"

  if [[ "$MAX_RUNS" -gt 0 && "$run_count" -ge "$MAX_RUNS" ]]; then
    echo "[heartbeat] reached max runs (${MAX_RUNS}), exiting" | tee -a "$HEARTBEAT_LOG"
    break
  fi

  ended_epoch="$(date +%s)"
  elapsed=$((ended_epoch - started_epoch))
  sleep_for=$((INTERVAL_SEC - elapsed))
  if [[ "$sleep_for" -lt 1 ]]; then
    sleep_for=1
  fi
  sleep "$sleep_for"
done
