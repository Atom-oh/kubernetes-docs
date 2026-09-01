#!/usr/bin/env bash
set -euo pipefail

export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker
export AWS_RETRY_MODE=adaptive
export AWS_MAX_ATTEMPTS=10

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
INVENTORY="$PACKAGE_ROOT/results/resource-inventory.json"
REGION=ap-northeast-2
DLC_ACCOUNT=763104351884
DLC_REPOSITORY=pytorch-training
DLC_TAG=2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker

for command in aws kubectl eksctl helm docker jq python3; do
  command -v "$command" >/dev/null || {
    printf 'Missing required command: %s\n' "$command" >&2
    exit 1
  }
done

if [[ -e "$INVENTORY" ]]; then
  printf 'Existing resource inventory must be resolved first: %s\n' "$INVENTORY" >&2
  exit 1
fi

aws sts get-caller-identity >/dev/null

RESOLVED_REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region 2>/dev/null || true)}}
if [[ "$RESOLVED_REGION" != "$REGION" ]]; then
  printf 'AWS region must resolve to %s, got %s\n' "$REGION" "${RESOLVED_REGION:-unset}" >&2
  exit 1
fi

SM_QUOTA=$(aws service-quotas list-service-quotas \
  --service-code sagemaker \
  --region "$REGION" \
  --output json | jq -r \
  '[.Quotas[] | select(.QuotaName=="ml.g6e.4xlarge for training job usage") | .Value][0] // 0')
awk -v value="$SM_QUOTA" 'BEGIN { exit !(value >= 1) }' || {
  printf 'SageMaker ml.g6e.4xlarge training quota is below 1: %s\n' "$SM_QUOTA" >&2
  exit 1
}

EC2_QUOTA=$(aws service-quotas list-service-quotas \
  --service-code ec2 \
  --region "$REGION" \
  --output json | jq -r \
  '[.Quotas[] | select(.QuotaName=="Running On-Demand G and VT instances") | .Value][0] // 0')
awk -v value="$EC2_QUOTA" 'BEGIN { exit !(value >= 16) }' || {
  printf 'EC2 On-Demand G/VT quota is below 16 vCPUs: %s\n' "$EC2_QUOTA" >&2
  exit 1
}

aws ecr describe-images \
  --region "$REGION" \
  --registry-id "$DLC_ACCOUNT" \
  --repository-name "$DLC_REPOSITORY" \
  --image-ids "imageTag=$DLC_TAG" >/dev/null

APP_COUNT=$(aws sagemaker list-mlflow-apps \
  --region "$REGION" \
  --output json | jq \
  '[.Summaries[]? | select((.Name | startswith("qwen-pii-")) and .Status != "Deleted")] | length')
if [[ "$APP_COUNT" != "0" ]]; then
  printf 'Found %s active qwen-pii MLflow App resources; clean them before continuing.\n' "$APP_COUNT" >&2
  exit 1
fi

CLUSTER_COUNT=$(aws eks list-clusters \
  --region "$REGION" \
  --query "length(clusters[?starts_with(@, 'qwen-pii-')])" \
  --output text)
if [[ "$CLUSTER_COUNT" != "0" ]]; then
  printf 'Found %s qwen-pii EKS clusters; clean them before continuing.\n' "$CLUSTER_COUNT" >&2
  exit 1
fi

BUCKET_COUNT=$(aws s3api list-buckets \
  --query "length(Buckets[?starts_with(Name, 'sagemaker-qwen-pii-')])" \
  --output text)
if [[ "$BUCKET_COUNT" != "0" ]]; then
  printf 'Found %s sagemaker-qwen-pii buckets; clean them before continuing.\n' "$BUCKET_COUNT" >&2
  exit 1
fi

ROLE_COUNT=$(aws iam list-roles \
  --output json | jq \
  '[.Roles[]? | select(.RoleName | startswith("qwen-pii-"))] | length')
if [[ "$ROLE_COUNT" != "0" ]]; then
  printf 'Found %s qwen-pii IAM roles; clean them before continuing.\n' "$ROLE_COUNT" >&2
  exit 1
fi

printf 'Preflight passed: region=%s, SageMaker quota=%s, EC2 GPU vCPU quota=%s\n' \
  "$REGION" "$SM_QUOTA" "$EC2_QUOTA"
