#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

DIGEST_AT="${DIGEST_AT:-$(date -u +%Y%m%dT%H)}"
DRY_RUN="${DRY_RUN:-0}"
RUN_EXPORTS="${RUN_EXPORTS:-1}"

usage() {
  cat <<USAGE
run_acquire_owner.sh

Acquire owner wrapper (PR4a).
- Keeps canonical runtime intact (delegates to existing make targets).
- Orchestrates acquisition path only: s01 -> s02 -> s03 (+ optional export-pr3a).

Env knobs:
  DIGEST_AT    Hour bucket (YYYYMMDDTHH). Default: current UTC hour.
  DRY_RUN      Passed through to make targets. Default: 0.
  RUN_EXPORTS  1 to run PR3a exports after s03, 0 to skip. Default: 1.

Flags:
  --dry-run    Print commands without executing.
USAGE
}

PRINT_ONLY=0
if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--dry-run" ]]; then
  PRINT_ONLY=1
fi

run_cmd() {
  echo "+ $*"
  if [[ "$PRINT_ONLY" == "1" ]]; then
    return 0
  fi
  "$@"
}

echo "[acquire-owner] digest_at=${DIGEST_AT} dry_run=${DRY_RUN} run_exports=${RUN_EXPORTS}"
run_cmd make s01 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"
run_cmd make s02 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"
run_cmd make s03 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"

if [[ "$RUN_EXPORTS" == "1" ]]; then
  run_cmd make export-pr3a DIGEST_AT="$DIGEST_AT"
else
  echo "[acquire-owner] RUN_EXPORTS=0 -> skipping export-pr3a"
fi

echo "[acquire-owner] done"
