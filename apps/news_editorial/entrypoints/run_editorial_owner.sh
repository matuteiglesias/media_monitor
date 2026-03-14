#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

DIGEST_AT="${DIGEST_AT:-$(date -u +%Y%m%dT%H)}"
DRY_RUN="${DRY_RUN:-0}"
PF_MODE="${PF_MODE:-legacy}"

usage() {
  cat <<USAGE
run_editorial_owner.sh

Editorial owner wrapper (PR4b).
- Keeps canonical runtime intact by delegating to existing make targets.
- Orchestrates editorial layer only: s04 -> s06 -> s05.

Env knobs:
  DIGEST_AT  Hour bucket (YYYYMMDDTHH). Default: current UTC hour.
  DRY_RUN    Passed to make. Default: 0.
  PF_MODE    Passed to make s04 (legacy/new/auto). Default: legacy.

Flags:
  --dry-run  Print commands without executing.
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

echo "[editorial-owner] digest_at=${DIGEST_AT} dry_run=${DRY_RUN} pf_mode=${PF_MODE}"
run_cmd make s04 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN" PF_MODE="$PF_MODE"
run_cmd make s06 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"
run_cmd make s05 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"
echo "[editorial-owner] done"
