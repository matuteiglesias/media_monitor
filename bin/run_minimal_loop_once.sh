#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

LANE=""
DIGEST_AT="${DIGEST_AT:-$(date -u +%Y%m%dT%H)}"
PROJECT_ID="${PROJECT_ID:-media_monitor}"
OPERATOR="${OPERATOR:-autonomous-loop}"
TRIGGER_TYPE="${TRIGGER_TYPE:-timer}"
ATTEMPT="${ATTEMPT:-1}"
DRY_RUN="${DRY_RUN:-0}"
ACQUIRE_NETWORK="${ACQUIRE_NETWORK:-}"
WRITE_ARTIFACTS="${WRITE_ARTIFACTS:-}"
ENQUEUE_SCRAPE="${ENQUEUE_SCRAPE:-}"
DB_RUN_BOOKKEEPING="${DB_RUN_BOOKKEEPING:-}"
RUN_RECORD_ALL_LANES="${RUN_RECORD_ALL_LANES:-0}"

PYTHON_CMD="${PYTHON_CMD:-}"
if [[ -z "$PYTHON_CMD" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
  else
    echo "Neither python3 nor python found on PATH" >&2
    exit 127
  fi
fi

usage() {
  cat <<USAGE
Usage: $0 --lane {sensing|editorial|enrich}

Optional env:
  DIGEST_AT=YYYYMMDDTHH
  DRY_RUN=0|1
  ACQUIRE_NETWORK=0|1       # default: inverse of DRY_RUN
  WRITE_ARTIFACTS=0|1       # default: 1
  ENQUEUE_SCRAPE=0|1        # default: inverse of DRY_RUN
  DB_RUN_BOOKKEEPING=0|1    # default: 0 (strict when enabled)
  SENSING_FEED_CONFIG=path  # default: config/sensing_feeds.v1.yaml
  PROJECT_ID=media_monitor
  OPERATOR=autonomous-loop
  TRIGGER_TYPE=timer|manual|batch|replay
  ATTEMPT=1
  RUN_RECORD_ALL_LANES=0|1   # default 0 instruments only sensing lane
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lane)
      LANE="${2:-}"
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

if [[ -z "$LANE" ]]; then
  echo "Missing --lane" >&2
  usage
  exit 2
fi

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

write_lane_status() {
  local exit_code="$1"
  local status_file="storage/observability/status/${LANE}_latest.json"
  local summary_file="storage/observability/status/summary.json"
  local ended_at
  ended_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  "$PYTHON_CMD" - "$status_file" "$summary_file" "$LANE" "$DIGEST_AT" "$STARTED_AT" "$ended_at" "$TRIGGER_TYPE" "$ATTEMPT" "$exit_code" "$PROJECT_ID" "$OPERATOR" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

HEALTH_THRESHOLDS_HOURS = {
    "sensing": {"healthy": 2, "degraded": 6},
    "editorial": {"healthy": 12, "degraded": 24},
    "enrich": {"healthy": 12, "degraded": 48},
}

status_file = Path(sys.argv[1])
summary_file = Path(sys.argv[2])
lane = sys.argv[3]
digest_at = sys.argv[4]
started_at = sys.argv[5]
ended_at = sys.argv[6]
trigger_type = sys.argv[7]
attempt = int(sys.argv[8])
exit_code = int(sys.argv[9])
project_id = sys.argv[10]
operator = sys.argv[11]

status = "success" if exit_code == 0 else "failed"
error_code = None if exit_code == 0 else f"exit_{exit_code}"
run_id = f"{lane}:{digest_at}:attempt:{attempt}"
record_path = Path("storage/observability/run_records.jsonl")
record_path.parent.mkdir(parents=True, exist_ok=True)
run_record = {
    "run_id": run_id,
    "project_id": project_id,
    "lane": lane,
    "stage": "lane",
    "digest_at": digest_at,
    "trigger_type": trigger_type,
    "attempt": attempt,
    "operator": operator,
    "started_at": started_at,
    "ended_at": ended_at,
    "status": status,
    "error_code": error_code or "",
}
with record_path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(run_record, ensure_ascii=False) + "\n")

if status_file.exists():
    try:
        prev = json.loads(status_file.read_text(encoding="utf-8"))
    except Exception:
        prev = {}
else:
    prev = {}

last_success_at = ended_at if status == "success" else prev.get("last_success_at")

threshold = HEALTH_THRESHOLDS_HOURS.get(lane, {"healthy": 6, "degraded": 24})
if last_success_at:
    last_success_dt = datetime.fromisoformat(last_success_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    now_dt = datetime.fromisoformat(ended_at.replace("Z", "+00:00")).astimezone(timezone.utc)
    age_h = (now_dt - last_success_dt).total_seconds() / 3600
    if age_h <= threshold["healthy"]:
        health_state = "healthy"
    elif age_h <= threshold["degraded"]:
        health_state = "degraded"
    else:
        health_state = "down"
else:
    health_state = "down"

payload = {
    "lane": lane,
    "updated_at": ended_at,
    "last_run_id": run_id,
    "last_started_at": started_at,
    "last_ended_at": ended_at,
    "last_status": status,
    "last_error_code": error_code,
    "last_success_at": last_success_at,
    "trigger_type": trigger_type,
    "attempt": attempt,
    "recent_inputs_count": prev.get("recent_inputs_count"),
    "recent_outputs_count": prev.get("recent_outputs_count"),
    "record_path": str(record_path),
    "health_state": health_state,
}
for key in (
    "last_successful_export_at",
    "last_exported_digest_at",
    "news_ref_count",
    "news_digest_group_count",
    "export_status",
    "failure_reason",
):
    if key in prev:
        payload[key] = prev.get(key)
status_file.parent.mkdir(parents=True, exist_ok=True)
status_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if summary_file.exists():
    try:
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
    except Exception:
        summary = {}
else:
    summary = {}
summary.setdefault("lanes", {})[lane] = {
    "runs_24h": summary.get("lanes", {}).get(lane, {}).get("runs_24h", 0) + 1,
    "success_24h": summary.get("lanes", {}).get(lane, {}).get("success_24h", 0) + (status == "success"),
    "failed_24h": summary.get("lanes", {}).get(lane, {}).get("failed_24h", 0) + (status == "failed"),
    "inputs_count_24h": summary.get("lanes", {}).get(lane, {}).get("inputs_count_24h", 0),
    "outputs_count_24h": summary.get("lanes", {}).get(lane, {}).get("outputs_count_24h", 0),
    "latest": payload,
}
summary["updated_at"] = ended_at
summary.setdefault("window", "24h")
summary.setdefault("source", {"run_records_path": "storage/observability/run_records.jsonl", "status_dir": "storage/observability/status"})
summary_file.parent.mkdir(parents=True, exist_ok=True)
summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

on_exit() {
  local exit_code=$?
  write_lane_status "$exit_code"
  exit "$exit_code"
}
trap on_exit EXIT

run_cmd() {
  local stage="$1"; shift
  local cmd=("$@")

  local use_wrapper="0"
  if [[ "$LANE" == "sensing" || "$RUN_RECORD_ALL_LANES" == "1" ]]; then
    use_wrapper="1"
  fi

  if [[ "$use_wrapper" == "1" && -x "scripts/run_with_run_record.py" ]]; then
    "$PYTHON_CMD" scripts/run_with_run_record.py \
      --project-id "$PROJECT_ID" \
      --operator "$OPERATOR" \
      --lane "$LANE" \
      --stage "$stage" \
      --trigger-type "$TRIGGER_TYPE" \
      --attempt "$ATTEMPT" \
      --telemetry-root "storage/observability" \
      --no-lane-status \
      --no-run-record \
      -- "${cmd[@]}"
  else
    "${cmd[@]}"
  fi
}

echo "[minimal-loop] lane=${LANE} digest_at=${DIGEST_AT} dry_run=${DRY_RUN}"

case "$LANE" in
  sensing)
    controls=(DRY_RUN="$DRY_RUN")
    [[ -n "$ACQUIRE_NETWORK" ]] && controls+=(ACQUIRE_NETWORK="$ACQUIRE_NETWORK")
    [[ -n "$WRITE_ARTIFACTS" ]] && controls+=(WRITE_ARTIFACTS="$WRITE_ARTIFACTS")
    [[ -n "$ENQUEUE_SCRAPE" ]] && controls+=(ENQUEUE_SCRAPE="$ENQUEUE_SCRAPE")
    [[ -n "$DB_RUN_BOOKKEEPING" ]] && controls+=(DB_RUN_BOOKKEEPING="$DB_RUN_BOOKKEEPING")
    run_cmd "s01" make s01 DIGEST_AT="$DIGEST_AT" "${controls[@]}"
    run_cmd "s02" make s02 DIGEST_AT="$DIGEST_AT" "${controls[@]}"
    run_cmd "s03" make s03 DIGEST_AT="$DIGEST_AT" "${controls[@]}"
    run_cmd "export_pr3a" make export-pr3a DIGEST_AT="$DIGEST_AT"
    run_cmd "build_news_access_indexes" make build-news-access-indexes DIGEST_AT="$DIGEST_AT"
    ;;
  editorial)
    run_cmd "s04" make s04 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"
    run_cmd "s06" make s06 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"
    run_cmd "s05" make s05 DIGEST_AT="$DIGEST_AT" DRY_RUN="$DRY_RUN"
    run_cmd "build_editorial_access_indexes" make build-editorial-access-indexes DIGEST_AT="$DIGEST_AT"
    ;;
  enrich)
    run_cmd "scrape_enrich" "$PYTHON_CMD" scripts/06_scrape_enrich.py
    ;;
  *)
    echo "Unsupported lane: $LANE" >&2
    usage
    exit 2
    ;;
esac

echo "[minimal-loop] lane=${LANE} completed"
