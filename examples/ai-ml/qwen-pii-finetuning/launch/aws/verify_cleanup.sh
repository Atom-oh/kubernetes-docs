#!/usr/bin/env bash
set -euo pipefail

export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
INVENTORY=${1:-"$PACKAGE_ROOT/results/resource-inventory.json"}
REPORT="$PACKAGE_ROOT/results/teardown-report.json"

if [[ ! -f "$INVENTORY" ]]; then
  printf 'Inventory not found: %s\n' "$INVENTORY" >&2
  exit 1
fi

EXPERIMENT_ID=$(jq -r '.experiment_id' "$INVENTORY")
REGION=$(jq -r '.region' "$INVENTORY")
BUCKET_NAME=$(jq -r '.bucket_name // empty' "$INVENTORY")
EXECUTION_ROLE_NAME=$(jq -r '.execution_role_name // empty' "$INVENTORY")
MLFLOW_ROLE_NAME=$(jq -r '.mlflow_role_name // empty' "$INVENTORY")
MLFLOW_APP_ARN=$(jq -r '.mlflow_app_arn // empty' "$INVENTORY")
UNIFIED_DOMAIN_ID=$(jq -r '.unified_domain_id // empty' "$INVENTORY")
PROJECT_ID=$(jq -r '.project_id // empty' "$INVENTORY")
REMAINING=()

if [[ -n "$MLFLOW_APP_ARN" ]] && APP_STATUS=$(aws sagemaker describe-mlflow-app \
  --region "$REGION" --arn "$MLFLOW_APP_ARN" --query Status --output text 2>/dev/null); then
  if [[ "$APP_STATUS" != "Deleted" ]]; then
    REMAINING+=("mlflow-app:$MLFLOW_APP_ARN")
  fi
fi
if [[ -n "$PROJECT_ID" ]] && aws datazone get-project \
  --region "$REGION" \
  --domain-identifier "$UNIFIED_DOMAIN_ID" \
  --identifier "$PROJECT_ID" >/dev/null 2>&1; then
  REMAINING+=("unified-studio-project:$PROJECT_ID")
fi
if [[ -n "$BUCKET_NAME" ]] && aws s3api head-bucket \
  --bucket "$BUCKET_NAME" >/dev/null 2>&1; then
  REMAINING+=("s3:$BUCKET_NAME")
fi
if [[ -n "$EXECUTION_ROLE_NAME" ]] && aws iam get-role \
  --role-name "$EXECUTION_ROLE_NAME" >/dev/null 2>&1; then
  REMAINING+=("iam-role:$EXECUTION_ROLE_NAME")
fi
if [[ -n "$MLFLOW_ROLE_NAME" ]] && aws iam get-role \
  --role-name "$MLFLOW_ROLE_NAME" >/dev/null 2>&1; then
  REMAINING+=("iam-role:$MLFLOW_ROLE_NAME")
fi

while IFS= read -r cluster; do
  [[ -z "$cluster" ]] && continue
  REMAINING+=("eks:$cluster")
done < <(aws eks list-clusters \
  --region "$REGION" \
  --query "clusters[?starts_with(@, '$EXPERIMENT_ID')]" \
  --output text | tr '\t' '\n')

while IFS= read -r instance_id; do
  [[ -z "$instance_id" ]] && continue
  REMAINING+=("ec2:$instance_id")
done < <(aws ec2 describe-instances \
  --region "$REGION" \
  --filters \
    "Name=tag:ExperimentId,Values=$EXPERIMENT_ID" \
    "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' \
  --output text | tr '\t' '\n')

while IFS= read -r resource_arn; do
  [[ -z "$resource_arn" ]] && continue
  if [[ "$resource_arn" == "$MLFLOW_APP_ARN" && "${APP_STATUS:-}" == "Deleted" ]]; then
    continue
  fi
  REMAINING+=("tagged:$resource_arn")
done < <(aws resourcegroupstaggingapi get-resources \
  --region "$REGION" \
  --tag-filters "Key=ExperimentId,Values=$EXPERIMENT_ID" \
  --query 'ResourceTagMappingList[].ResourceARN' \
  --output text | tr '\t' '\n')

mkdir -p "$(dirname "$REPORT")"
if ((${#REMAINING[@]})); then
  printf '%s\n' "${REMAINING[@]}" | jq -R . | jq -s \
    --arg experiment_id "$EXPERIMENT_ID" \
    --arg checked_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{
      experimentId: $experiment_id,
      checkedAt: $checked_at,
      remainingResources: .,
      remainingResourceCount: length
    }' > "$REPORT"
else
  jq -n \
    --arg experiment_id "$EXPERIMENT_ID" \
    --arg checked_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{
      experimentId: $experiment_id,
      checkedAt: $checked_at,
      remainingResources: [],
      remainingResourceCount: 0
    }' > "$REPORT"
fi

COUNT=$(jq -r '.remainingResourceCount' "$REPORT")
printf 'Cleanup verification: %s resource(s) remain.\n' "$COUNT"
[[ "$COUNT" == "0" ]]
