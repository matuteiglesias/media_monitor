#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
TF_DIR="$ROOT/infra/aws/sensing"
: "${AWS_REGION:?set AWS_REGION}"
: "${SENSING_BUCKET_NAME:?set SENSING_BUCKET_NAME to a globally unique bucket}"
ENVIRONMENT="${ENVIRONMENT:-sprint}"
SOURCE_COMMIT="${SOURCE_COMMIT:-$(git -C "$ROOT" rev-parse HEAD)}"
AWS=(aws --region "$AWS_REGION")
if [[ -n "${AWS_PROFILE:-}" ]]; then AWS+=(--profile "$AWS_PROFILE"); fi

for command in terraform docker aws python; do
  command -v "$command" >/dev/null || { echo "missing required command: $command" >&2; exit 2; }
done

cd "$TF_DIR"
terraform init

# ECR must exist before the first immutable image can be pushed. All other
# resources are still created by the saved full plan below.
placeholder_digest="sha256:$(printf '0%.0s' {1..64})"
terraform apply -auto-approve -target=aws_ecr_repository.sensing \
  -var="aws_region=$AWS_REGION" \
  -var="environment=$ENVIRONMENT" \
  -var="bucket_name=$SENSING_BUCKET_NAME" \
  -var="image_uri=placeholder.invalid/repository@$placeholder_digest" \
  -var="source_commit=$SOURCE_COMMIT"

repository_url="$(terraform output -raw ecr_repository_url)"
registry="${repository_url%%/*}"
"${AWS[@]}" ecr get-login-password | docker login --username AWS --password-stdin "$registry"
tag="source-${SOURCE_COMMIT:0:12}"
digest="$("${AWS[@]}" ecr describe-images --repository-name "${repository_url#*/}" --image-ids imageTag="$tag" --query 'imageDetails[0].imageDigest' --output text 2>/dev/null || true)"
if [[ ! "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]; then
  docker build --file "$ROOT/Dockerfile.sensing" --label "org.opencontainers.image.revision=$SOURCE_COMMIT" --tag "$repository_url:$tag" "$ROOT"
  docker push "$repository_url:$tag"
  digest="$("${AWS[@]}" ecr describe-images --repository-name "${repository_url#*/}" --image-ids imageTag="$tag" --query 'imageDetails[0].imageDigest' --output text)"
else
  echo "reusing immutable ECR image $repository_url@$digest for $SOURCE_COMMIT"
fi
[[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo "invalid pushed image digest: $digest" >&2; exit 3; }

python - "$TF_DIR/deployment.auto.tfvars.json" "$AWS_REGION" "$ENVIRONMENT" "$SENSING_BUCKET_NAME" "$repository_url@$digest" "$SOURCE_COMMIT" <<'PY'
import json, sys
path, region, environment, bucket, image, commit = sys.argv[1:]
with open(path, "w", encoding="utf-8") as fh:
    json.dump({"aws_region": region, "environment": environment, "bucket_name": bucket, "image_uri": image, "source_commit": commit}, fh, indent=2)
    fh.write("\n")
PY

terraform plan -out=a5.tfplan
terraform apply a5.tfplan
terraform plan -detailed-exitcode >/tmp/media-monitor-a5-clean-plan.txt || rc=$?
if [[ "${rc:-0}" != "0" ]]; then
  cat /tmp/media-monitor-a5-clean-plan.txt >&2
  echo "post-apply plan is not clean" >&2
  exit 4
fi

printf 'IMAGE_URI=%s\nSOURCE_COMMIT=%s\n' "$repository_url@$digest" "$SOURCE_COMMIT"
