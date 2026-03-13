#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

MODE="${MODE:-worker}" # worker|batch|requeue|replay
PRINT_ONLY=0

usage(){
  cat <<USAGE
run_enrich_owner.sh

Enrich owner wrapper (PR4e) for compatibility-safe invocation.

Env knobs:
  MODE=worker|batch|requeue|replay (default: worker)
  ARGS="..." additional args passed to selected command

Modes:
  worker -> python scripts/worker_scrape.py
  batch  -> python scripts/06_scrape_enrich.py
  requeue-> python scripts/requeue_failed.py
  replay -> python scripts/replay.job.py

Flags:
  --dry-run  print command only
USAGE
}

if [[ "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ "${1:-}" == "--dry-run" ]]; then PRINT_ONLY=1; fi

ARGS="${ARGS:-}"
case "$MODE" in
  worker) CMD=(python scripts/worker_scrape.py) ;;
  batch)  CMD=(python scripts/06_scrape_enrich.py) ;;
  requeue) CMD=(python scripts/requeue_failed.py) ;;
  replay) CMD=(python scripts/replay.job.py) ;;
  *) echo "unknown MODE=$MODE"; exit 2 ;;
esac

echo "+ ${CMD[*]} ${ARGS}"
if [[ "$PRINT_ONLY" == "1" ]]; then exit 0; fi
# shellcheck disable=SC2086
${CMD[@]} $ARGS
