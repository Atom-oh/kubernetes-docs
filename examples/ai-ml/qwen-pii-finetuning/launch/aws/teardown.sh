#!/usr/bin/env bash
set -euo pipefail

export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker
export AWS_RETRY_MODE=adaptive
export AWS_MAX_ATTEMPTS=10

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
INVENTORY=${1:-"$PACKAGE_ROOT/results/resource-inventory.json"}

if [[ ! -f "$INVENTORY" ]]; then
  printf 'No inventory found at %s; nothing to delete.\n' "$INVENTORY"
  exit 0
fi

EXPERIMENT_ID=$(jq -r '.experiment_id' "$INVENTORY")
REGION=$(jq -r '.region' "$INVENTORY")
BUCKET_NAME=$(jq -r '.bucket_name // empty' "$INVENTORY")
EXECUTION_ROLE_NAME=$(jq -r '.execution_role_name // empty' "$INVENTORY")
MLFLOW_ROLE_NAME=$(jq -r '.mlflow_role_name // empty' "$INVENTORY")
MLFLOW_APP_ARN=$(jq -r '.mlflow_app_arn // empty' "$INVENTORY")
UNIFIED_DOMAIN_ID=$(jq -r '.unified_domain_id // empty' "$INVENTORY")
PROJECT_ID=$(jq -r '.project_id // empty' "$INVENTORY")

if [[ ! "$EXPERIMENT_ID" =~ ^qwen-pii-[0-9A-Za-z-]+$ ]]; then
  printf 'Refusing teardown for unsafe experiment ID: %s\n' "$EXPERIMENT_ID" >&2
  exit 1
fi

if [[ -n "$MLFLOW_APP_ARN" ]]; then
  if APP_STATUS=$(aws sagemaker describe-mlflow-app \
    --region "$REGION" \
    --arn "$MLFLOW_APP_ARN" \
    --query Status \
    --output text 2>/dev/null); then
    if [[ "$APP_STATUS" != "Deleted" ]]; then
      aws sagemaker delete-mlflow-app \
        --region "$REGION" \
        --arn "$MLFLOW_APP_ARN"
      for _attempt in $(seq 1 80); do
        if ! APP_STATUS=$(aws sagemaker describe-mlflow-app \
          --region "$REGION" \
          --arn "$MLFLOW_APP_ARN" \
          --query Status \
          --output text 2>/dev/null); then
          break
        fi
        if [[ "$APP_STATUS" == "Deleted" ]]; then
          break
        fi
        if [[ "$APP_STATUS" == "DeleteFailed" ]]; then
          printf 'MLflow App deletion failed for %s.\n' "$MLFLOW_APP_ARN" >&2
          exit 1
        fi
        sleep 15
      done
    fi
  fi
fi

if [[ -n "$PROJECT_ID" && -n "$UNIFIED_DOMAIN_ID" ]]; then
  if aws datazone get-project \
    --region "$REGION" \
    --domain-identifier "$UNIFIED_DOMAIN_ID" \
    --identifier "$PROJECT_ID" >/dev/null 2>&1; then
    aws datazone delete-project \
      --region "$REGION" \
      --domain-identifier "$UNIFIED_DOMAIN_ID" \
      --identifier "$PROJECT_ID"
    for _attempt in $(seq 1 80); do
      if ! aws datazone get-project \
        --region "$REGION" \
        --domain-identifier "$UNIFIED_DOMAIN_ID" \
        --identifier "$PROJECT_ID" >/dev/null 2>&1; then
        break
      fi
      sleep 15
    done
  fi
fi

LOG_GROUP=/aws/sagemaker/TrainingJobs
if aws logs describe-log-groups \
  --region "$REGION" \
  --log-group-name-prefix "$LOG_GROUP" \
  --query "logGroups[?logGroupName=='$LOG_GROUP'] | length(@)" \
  --output text | grep -qx 1; then
  while IFS= read -r stream; do
    [[ -z "$stream" ]] && continue
    aws logs delete-log-stream \
      --region "$REGION" \
      --log-group-name "$LOG_GROUP" \
      --log-stream-name "$stream"
  done < <(aws logs describe-log-streams \
    --region "$REGION" \
    --log-group-name "$LOG_GROUP" \
    --log-stream-name-prefix "$EXPERIMENT_ID" \
    --query 'logStreams[].logStreamName' \
    --output text | tr '\t' '\n')
fi

if [[ -n "$BUCKET_NAME" ]] && aws s3api head-bucket --bucket "$BUCKET_NAME" >/dev/null 2>&1; then
  while true; do
    VERSIONS=$(aws s3api list-object-versions \
      --bucket "$BUCKET_NAME" \
      --max-keys 1000 \
      --output json)
    DELETE_PAYLOAD=$(jq -c '{
      Objects: (
        [.Versions[]? | {Key: .Key, VersionId: .VersionId}] +
        [.DeleteMarkers[]? | {Key: .Key, VersionId: .VersionId}]
      ),
      Quiet: true
    }' <<<"$VERSIONS")
    OBJECT_COUNT=$(jq '.Objects | length' <<<"$DELETE_PAYLOAD")
    if [[ "$OBJECT_COUNT" == "0" ]]; then
      break
    fi
    aws s3api delete-objects \
      --bucket "$BUCKET_NAME" \
      --delete "$DELETE_PAYLOAD" >/dev/null
  done
  aws s3 rm "s3://${BUCKET_NAME}" --recursive >/dev/null
  aws s3api delete-bucket --bucket "$BUCKET_NAME" --region "$REGION"
fi

delete_role() {
  local role_name=$1
  [[ -z "$role_name" ]] && return
  if ! aws iam get-role --role-name "$role_name" >/dev/null 2>&1; then
    return
  fi
  while IFS= read -r policy_name; do
    [[ -z "$policy_name" ]] && continue
    aws iam delete-role-policy \
      --role-name "$role_name" \
      --policy-name "$policy_name"
  done < <(aws iam list-role-policies \
    --role-name "$role_name" \
    --query 'PolicyNames[]' \
    --output text | tr '\t' '\n')
  aws iam delete-role --role-name "$role_name"
}

delete_role "$EXECUTION_ROLE_NAME"
delete_role "$MLFLOW_ROLE_NAME"

DELETED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
jq --arg deleted_at "$DELETED_AT" '.deleted_at = $deleted_at' \
  "$INVENTORY" > "${INVENTORY}.tmp"
mv "${INVENTORY}.tmp" "$INVENTORY"
printf 'Teardown complete for %s.\n' "$EXPERIMENT_ID"
