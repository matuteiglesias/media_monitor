#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$REPO_ROOT"

MODE="${MODE:-worker}" # worker|batch|requeue|replay
PRINT_ONLY=0

usage(){
  cat <<USAGE
run_enrich_owner.sh

Enrich owner wrapper for compatibility-safe invocation.

Env knobs:
  MODE=worker|batch|requeue|replay (default: worker)
  ARGS="..." additional args passed to selected command

Modes:
  worker -> python -m apps.news_enrich.src.news_enrich.worker_scrape
  batch  -> python -m apps.news_enrich.src.news_enrich.scrape_enrich
  requeue-> python -m apps.news_enrich.src.news_enrich.requeue_failed
  replay -> python -m apps.news_enrich.src.news_enrich.replay_job

Flags:
  --dry-run  print command only
USAGE
}

if [[ "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ "${1:-}" == "--dry-run" ]]; then PRINT_ONLY=1; fi

ARGS="${ARGS:-}"
case "$MODE" in
  worker) CMD=(python -m apps.news_enrich.src.news_enrich.worker_scrape) ;;
  batch)  CMD=(python -m apps.news_enrich.src.news_enrich.scrape_enrich) ;;
  requeue) CMD=(python -m apps.news_enrich.src.news_enrich.requeue_failed) ;;
  replay) CMD=(python -m apps.news_enrich.src.news_enrich.replay_job) ;;
  *) echo "unknown MODE=$MODE"; exit 2 ;;
esac

echo "+ ${CMD[*]} ${ARGS}"
if [[ "$PRINT_ONLY" == "1" ]]; then exit 0; fi
# shellcheck disable=SC2086
${CMD[@]} $ARGS
