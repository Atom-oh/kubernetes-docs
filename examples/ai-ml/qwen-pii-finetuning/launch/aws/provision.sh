#!/usr/bin/env bash
set -euo pipefail

export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker
export AWS_RETRY_MODE=adaptive
export AWS_MAX_ATTEMPTS=10

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
# This pinned cohort is executable only while its upstream patch support is current.
"${PYTHON:-python3}" "$PACKAGE_ROOT/src/runtime_contract.py" --check-execution
RESULTS_DIR="$PACKAGE_ROOT/results"
INVENTORY="$RESULTS_DIR/resource-inventory.json"
TEARDOWN="$SCRIPT_DIR/teardown.sh"
REGION=ap-northeast-2
umask 077
PYTHON=${PYTHON:-python3}
HELPER="$SCRIPT_DIR/lifecycle.py"
# All supplied DataZone IDs and the caller account are validated before mutation.
ACCOUNT_ID=$("$PYTHON" "$HELPER" inputs)
TIMESTAMP=$(date -u +%Y%m%d%H%M%S)
SUFFIX=$("$PYTHON" -c 'import uuid; print(uuid.uuid4().hex[:12])')
EXPERIMENT_ID=${EXPERIMENT_ID:-qwen-pii-$TIMESTAMP-$SUFFIX}
if [[ ! "$EXPERIMENT_ID" =~ ^qwen-pii-[0-9A-Za-z-]+$ || ${#EXPERIMENT_ID} -gt 50 ]]; then
  printf 'Experiment ID must be qwen-pii-* and at most 50 characters.\n' >&2
  exit 1
fi
BUCKET_NAME="sagemaker-qwen-pii-${ACCOUNT_ID}-${SUFFIX}"
EXECUTION_ROLE_NAME="${EXPERIMENT_ID}-exec"
MLFLOW_ROLE_NAME="${EXPERIMENT_ID}-mlflow"
UNIFIED_DOMAIN_ID=$DATAZONE_DOMAIN_ID
PROJECT_PROFILE_ID=$DATAZONE_PROJECT_PROFILE_ID
PROJECT_OWNER_GROUP_ID=$DATAZONE_OWNER_GROUP_ID
export EXPERIMENT_ID BUCKET_NAME EXECUTION_ROLE_NAME MLFLOW_ROLE_NAME
mkdir -p "$RESULTS_DIR"
# Keep a run lock separate from the helper's short inventory-update lock.
exec 9>"$RESULTS_DIR/provision.lock"
flock -n 9 || { printf 'Another provisioning process is active.\n' >&2; exit 1; }
"$PYTHON" "$HELPER" init "$INVENTORY"
finalize() {
  status=$?
  trap - EXIT INT TERM
  if ((status != 0)); then
    printf 'Provisioning interrupted; checking confirmed ownership for cleanup.\n' >&2
    if ! "$TEARDOWN" "$INVENTORY"; then
      printf 'Cleanup incomplete. Preserve %s; reconcile partial/unknown creation manually. Costs may continue.\n' "$INVENTORY" >&2
    fi
  fi
  exit "$status"
}
trap finalize EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
jq -nc --arg bucket "$BUCKET_NAME" --arg region "$REGION" \
  '{Bucket:$bucket,CreateBucketConfiguration:{LocationConstraint:$region}}' |
  "$PYTHON" "$HELPER" create "$INVENTORY" bucket >/dev/null
aws s3api put-public-access-block --bucket "$BUCKET_NAME" --expected-bucket-owner "$ACCOUNT_ID" \
  --public-access-block-configuration \
  'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
aws s3api put-bucket-encryption --bucket "$BUCKET_NAME" --expected-bucket-owner "$ACCOUNT_ID" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-versioning --bucket "$BUCKET_NAME" --expected-bucket-owner "$ACCOUNT_ID" \
  --versioning-configuration Status=Enabled

TRUST_POLICY=$(jq -nc \
  --arg account "$ACCOUNT_ID" \
  --arg source_arn "arn:aws:sagemaker:${REGION}:${ACCOUNT_ID}:*" \
  '{
    Version: "2012-10-17",
    Statement: [{
      Effect: "Allow",
      Principal: {Service: "sagemaker.amazonaws.com"},
      Action: "sts:AssumeRole",
      Condition: {
        StringEquals: {"aws:SourceAccount": $account},
        ArnLike: {"aws:SourceArn": $source_arn}
      }
    }]
  }')

EXECUTION_ROLE_ARN=$(jq -nc --arg name "$EXECUTION_ROLE_NAME" --arg policy "$TRUST_POLICY" \
  '{RoleName:$name,AssumeRolePolicyDocument:$policy}' |
  "$PYTHON" "$HELPER" create "$INVENTORY" execution_role | jq -er '.Role.Arn')
MLFLOW_ROLE_ARN=$(jq -nc --arg name "$MLFLOW_ROLE_NAME" --arg policy "$TRUST_POLICY" \
  '{RoleName:$name,AssumeRolePolicyDocument:$policy}' |
  "$PYTHON" "$HELPER" create "$INVENTORY" mlflow_role | jq -er '.Role.Arn')
aws iam wait role-exists --role-name "$EXECUTION_ROLE_NAME"
aws iam wait role-exists --role-name "$MLFLOW_ROLE_NAME"

MLFLOW_S3_POLICY=$(jq -nc \
  --arg bucket "arn:aws:s3:::${BUCKET_NAME}" \
  --arg objects "arn:aws:s3:::${BUCKET_NAME}/mlflow-artifacts/*" \
  '{
    Version: "2012-10-17",
    Statement: [
      {
        Sid: "ReadBucketLocation",
        Effect: "Allow",
        Action: "s3:GetBucketLocation",
        Resource: $bucket
      },
      {
        Sid: "ListArtifactPrefix",
        Effect: "Allow",
        Action: "s3:ListBucket",
        Resource: $bucket,
        Condition: {StringLike: {"s3:prefix": ["mlflow-artifacts", "mlflow-artifacts/*"]}}
      },
      {
        Sid: "ManageArtifacts",
        Effect: "Allow",
        Action: ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"],
        Resource: $objects
      }
    ]
  }')
POLICY_FINDINGS=$(aws accessanalyzer validate-policy \
  --region "$REGION" \
  --policy-document "$MLFLOW_S3_POLICY" \
  --policy-type IDENTITY_POLICY \
  --query "findings[?findingType=='ERROR' || findingType=='SECURITY_WARNING']" \
  --output json)
if [[ "$(jq length <<<"$POLICY_FINDINGS")" != "0" ]]; then
  jq . <<<"$POLICY_FINDINGS" >&2
  exit 1
fi
aws iam put-role-policy \
  --role-name "$MLFLOW_ROLE_NAME" \
  --policy-name "${EXPERIMENT_ID}-mlflow-s3" \
  --policy-document "$MLFLOW_S3_POLICY"

sleep 10
APP_RESPONSE=$(jq -nc --arg name "$EXPERIMENT_ID" \
  --arg store "s3://${BUCKET_NAME}/mlflow-artifacts" --arg role "$MLFLOW_ROLE_ARN" \
  '{Name:$name,ArtifactStoreUri:$store,RoleArn:$role,
    ModelRegistrationMode:"AutoModelRegistrationDisabled",AccountDefaultStatus:"DISABLED"}' |
  "$PYTHON" "$HELPER" create "$INVENTORY" mlflow_app)
MLFLOW_APP_ARN=$(jq -er '.Arn' <<<"$APP_RESPONSE")

for _attempt in $(seq 1 40); do
  APP_STATUS=$(aws sagemaker describe-mlflow-app \
    --region "$REGION" \
    --arn "$MLFLOW_APP_ARN" \
    --query Status \
    --output text)
  if [[ "$APP_STATUS" == "Created" || "$APP_STATUS" == "Updated" ]]; then
    break
  fi
  if [[ "$APP_STATUS" == "CreateFailed" || "$APP_STATUS" == "UpdateFailed" || "$APP_STATUS" == "DeleteFailed" ]]; then
    printf 'MLflow App creation failed.\n' >&2
    exit 1
  fi
  sleep 15
done
if [[ "${APP_STATUS:-}" != "Created" && "${APP_STATUS:-}" != "Updated" ]]; then
  printf 'Timed out waiting for MLflow App ready status.\n' >&2
  exit 1
fi

EXECUTION_POLICY=$(jq -nc \
  --arg bucket "arn:aws:s3:::${BUCKET_NAME}" \
  --arg objects "arn:aws:s3:::${BUCKET_NAME}/*" \
  --arg app "$MLFLOW_APP_ARN" \
  --arg log_group "arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:/aws/sagemaker/TrainingJobs:*" \
  '{
    Version: "2012-10-17",
    Statement: [
      {
        Sid: "ListExperimentBucket",
        Effect: "Allow",
        Action: ["s3:GetBucketLocation", "s3:ListBucket", "s3:ListBucketMultipartUploads"],
        Resource: $bucket
      },
      {
        Sid: "ReadWriteExperimentObjects",
        Effect: "Allow",
        Action: [
          "s3:GetObject", "s3:GetObjectVersion", "s3:PutObject",
          "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"
        ],
        Resource: $objects
      },
      {
        Sid: "WriteTrainingLogs",
        Effect: "Allow",
        Action: ["logs:CreateLogStream", "logs:PutLogEvents"],
        Resource: $log_group
      },
      {
        Sid: "UseMlflowApp",
        Effect: "Allow",
        Action: ["sagemaker:CallMlflowAppApi", "sagemaker:DescribeMlflowApp"],
        Resource: $app
      }
    ]
  }')
POLICY_FINDINGS=$(aws accessanalyzer validate-policy \
  --region "$REGION" \
  --policy-document "$EXECUTION_POLICY" \
  --policy-type IDENTITY_POLICY \
  --query "findings[?findingType=='ERROR' || findingType=='SECURITY_WARNING']" \
  --output json)
if [[ "$(jq length <<<"$POLICY_FINDINGS")" != "0" ]]; then
  jq . <<<"$POLICY_FINDINGS" >&2
  exit 1
fi
aws iam put-role-policy \
  --role-name "$EXECUTION_ROLE_NAME" \
  --policy-name "${EXPERIMENT_ID}-execution" \
  --policy-document "$EXECUTION_POLICY"

PROJECT_ID=$(jq -nc --arg domain "$UNIFIED_DOMAIN_ID" --arg name "$EXPERIMENT_ID" \
  --arg profile "$PROJECT_PROFILE_ID" --arg group "$PROJECT_OWNER_GROUP_ID" \
  '{domainIdentifier:$domain,name:$name,projectProfileId:$profile,
    description:"Ephemeral Qwen PII fine-tuning validation project",
    membershipAssignments:[{member:{groupIdentifier:$group},designation:"PROJECT_OWNER"}]}' |
  "$PYTHON" "$HELPER" create "$INVENTORY" project | jq -er '.id')

for _attempt in $(seq 1 60); do
  PROJECT_STATUS=$(aws datazone get-project \
    --region "$REGION" \
    --domain-identifier "$UNIFIED_DOMAIN_ID" \
    --identifier "$PROJECT_ID" \
    --query projectStatus \
    --output text)
  if [[ "$PROJECT_STATUS" == "ACTIVE" ]]; then
    break
  fi
  if [[ "$PROJECT_STATUS" == "DELETE_FAILED" ]]; then
    printf 'Unified Studio project creation failed.\n' >&2
    exit 1
  fi
  sleep 15
done
if [[ "${PROJECT_STATUS:-}" != "ACTIVE" ]]; then
  printf 'Timed out waiting for Unified Studio project ACTIVE status.\n' >&2
  exit 1
fi

trap - EXIT INT TERM
printf 'Provisioned experiment %s; inventory: %s\n' "$EXPERIMENT_ID" "$INVENTORY"
