#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TF_DIR="$ROOT/infra/aws/sensing"
: "${CONFIRM_DESTROY:?set CONFIRM_DESTROY=media-monitor-sensing}"
[[ "$CONFIRM_DESTROY" == "media-monitor-sensing" ]] || { echo "confirmation mismatch" >&2; exit 2; }
terraform -chdir="$TF_DIR" destroy -var="allow_destroy=true"
echo "Terraform destroy completed; retain the terminal output as teardown evidence."
