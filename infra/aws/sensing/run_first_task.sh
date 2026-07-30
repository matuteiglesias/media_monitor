#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TF_DIR="$ROOT/infra/aws/sensing"
: "${DIGEST_AT:?set DIGEST_AT as YYYYMMDDTHH}"
: "${AWS_REGION:?set AWS_REGION}"
AWS=(aws --region "$AWS_REGION")
if [[ -n "${AWS_PROFILE:-}" ]]; then AWS+=(--profile "$AWS_PROFILE"); fi
for command in terraform aws python; do command -v "$command" >/dev/null || { echo "missing $command" >&2; exit 2; }; done

cluster="$(terraform -chdir="$TF_DIR" output -raw ecs_cluster_name)"
task_definition="$(terraform -chdir="$TF_DIR" output -raw task_definition_arn)"
security_group="$(terraform -chdir="$TF_DIR" output -raw security_group_id)"
bucket="$(terraform -chdir="$TF_DIR" output -raw bucket_name)"
prefix="$(terraform -chdir="$TF_DIR" output -raw s3_prefix)"
log_group="$(terraform -chdir="$TF_DIR" output -raw log_group_name)"
mapfile -t subnets < <(terraform -chdir="$TF_DIR" output -json subnet_ids | python -c 'import json,sys; print("\n".join(json.load(sys.stdin)))')
run_id="${RUN_ID:-sensing:${DIGEST_AT}:attempt:1:manual-$(date -u +%Y%m%dT%H%M%SZ)}"
subnet_csv="$(IFS=,; echo "${subnets[*]}")"
overrides="$(python - "$DIGEST_AT" "$run_id" <<'PY'
import json,sys
digest, run_id = sys.argv[1:]
print(json.dumps({"containerOverrides":[{"name":"sensing","environment":[{"name":"DIGEST_AT","value":digest},{"name":"RUN_ID","value":run_id},{"name":"ATTEMPT","value":"1"},{"name":"RUN_IAM_DENIAL_PROBE","value":"1"}]}]}))
PY
)"

task_arn="$("${AWS[@]}" ecs run-task \
  --cluster "$cluster" --task-definition "$task_definition" --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$subnet_csv],securityGroups=[$security_group],assignPublicIp=ENABLED}" \
  --overrides "$overrides" --query 'tasks[0].taskArn' --output text)"
[[ "$task_arn" != "None" ]] || { echo "ECS did not return a task ARN" >&2; exit 3; }
"${AWS[@]}" ecs wait tasks-stopped --cluster "$cluster" --tasks "$task_arn"
description="$("${AWS[@]}" ecs describe-tasks --cluster "$cluster" --tasks "$task_arn")"
exit_code="$(python -c 'import json,sys; d=json.load(sys.stdin); print(d["tasks"][0]["containers"][0].get("exitCode",-1))' <<<"$description")"
[[ "$exit_code" == "0" ]] || { echo "$description" >&2; exit 4; }

evidence_dir="$ROOT/artifacts/aws-a5/${run_id//:/_}"
mkdir -p "$evidence_dir"
printf '%s\n' "$description" >"$evidence_dir/ecs_task.json"
"${AWS[@]}" s3api list-objects-v2 --bucket "$bucket" --prefix "$prefix/runs/$run_id/" >"$evidence_dir/s3_run_objects.json"
for _attempt in {1..12}; do
  "${AWS[@]}" logs filter-log-events --log-group-name "$log_group" --filter-pattern "\"$run_id\"" >"$evidence_dir/cloudwatch_logs.json"
  if python -c 'import json,sys; raise SystemExit(0 if json.load(open(sys.argv[1])).get("events") else 1)' "$evidence_dir/cloudwatch_logs.json"; then
    break
  fi
  sleep 5
done
python - "$evidence_dir" "$prefix" "$run_id" <<'PY'
import json,sys
from pathlib import Path
root,prefix,run_id=Path(sys.argv[1]),sys.argv[2],sys.argv[3]
objects=json.loads((root/'s3_run_objects.json').read_text()).get('Contents',[])
keys=[item['Key'] for item in objects]
assert f'{prefix}/runs/{run_id}/FINALIZED' in keys
assert all(key.startswith(f'{prefix}/runs/{run_id}/') for key in keys)
logs=json.loads((root/'cloudwatch_logs.json').read_text()).get('events',[])
messages=[event.get('message','') for event in logs]
assert any('bundle_uploaded' in message and run_id in message for message in messages)
assert any('iam_denial_confirmed' in message and run_id in message for message in messages)
print(f'A5 evidence verified at {root}')
PY

printf 'TASK_ARN=%s\nRUN_ID=%s\nEVIDENCE_DIR=%s\n' "$task_arn" "$run_id" "$evidence_dir"
