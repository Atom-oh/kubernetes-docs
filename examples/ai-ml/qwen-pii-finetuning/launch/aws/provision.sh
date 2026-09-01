#!/usr/bin/env bash
set -euo pipefail

export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
RESULTS_DIR="$PACKAGE_ROOT/results"
INVENTORY="$RESULTS_DIR/resource-inventory.json"
TEARDOWN="$SCRIPT_DIR/teardown.sh"
REGION=ap-northeast-2
TIMESTAMP=$(date -u +%Y%m%d%H%M%S)
EXPERIMENT_ID=${EXPERIMENT_ID:-qwen-pii-$TIMESTAMP}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="sagemaker-qwen-pii-${ACCOUNT_ID}-${TIMESTAMP}"
EXECUTION_ROLE_NAME="${EXPERIMENT_ID}-exec"
MLFLOW_ROLE_NAME="${EXPERIMENT_ID}-mlflow"
EXECUTION_ROLE_ARN=""
MLFLOW_ROLE_ARN=""
MLFLOW_APP_ARN=""
UNIFIED_DOMAIN_ID=""
PROJECT_PROFILE_ID=""
PROJECT_ID=""
CREATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

mkdir -p "$RESULTS_DIR"
if [[ -e "$INVENTORY" ]]; then
  printf 'Refusing to overwrite existing inventory: %s\n' "$INVENTORY" >&2
  exit 1
fi
if [[ ! "$EXPERIMENT_ID" =~ ^qwen-pii-[0-9A-Za-z-]+$ ]]; then
  printf 'Unsafe experiment ID: %s\n' "$EXPERIMENT_ID" >&2
  exit 1
fi

write_inventory() {
  jq -n \
    --arg experiment_id "$EXPERIMENT_ID" \
    --arg region "$REGION" \
    --arg bucket_name "$BUCKET_NAME" \
    --arg execution_role_name "$EXECUTION_ROLE_NAME" \
    --arg execution_role_arn "$EXECUTION_ROLE_ARN" \
    --arg mlflow_role_name "$MLFLOW_ROLE_NAME" \
    --arg mlflow_role_arn "$MLFLOW_ROLE_ARN" \
    --arg mlflow_app_arn "$MLFLOW_APP_ARN" \
    --arg unified_domain_id "$UNIFIED_DOMAIN_ID" \
    --arg project_profile_id "$PROJECT_PROFILE_ID" \
    --arg project_id "$PROJECT_ID" \
    --arg source_s3_uri "s3://${BUCKET_NAME}/qwen-pii/${EXPERIMENT_ID}/source/source.tar.gz" \
    --arg created_at "$CREATED_AT" \
    '{
      experiment_id: $experiment_id,
      region: $region,
      bucket_name: $bucket_name,
      execution_role_name: $execution_role_name,
      execution_role_arn: $execution_role_arn,
      mlflow_role_name: $mlflow_role_name,
      mlflow_role_arn: $mlflow_role_arn,
      mlflow_app_arn: $mlflow_app_arn,
      unified_domain_id: $unified_domain_id,
      project_profile_id: $project_profile_id,
      project_id: $project_id,
      source_s3_uri: $source_s3_uri,
      created_at: $created_at
    }' > "${INVENTORY}.tmp"
  mv "${INVENTORY}.tmp" "$INVENTORY"
}

cleanup_on_error() {
  status=$?
  trap - ERR INT TERM
  write_inventory
  if [[ -x "$TEARDOWN" ]]; then
    "$TEARDOWN" "$INVENTORY" || true
  fi
  exit "$status"
}
trap cleanup_on_error ERR INT TERM

aws s3api create-bucket \
  --bucket "$BUCKET_NAME" \
  --region "$REGION" \
  --create-bucket-configuration "LocationConstraint=$REGION" >/dev/null
aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-versioning \
  --bucket "$BUCKET_NAME" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-tagging \
  --bucket "$BUCKET_NAME" \
  --tagging "TagSet=[{Key=Experiment,Value=qwen-pii-finetuning},{Key=ExperimentId,Value=$EXPERIMENT_ID}]"
write_inventory

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

EXECUTION_ROLE_ARN=$(aws iam create-role \
  --role-name "$EXECUTION_ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --tags Key=Experiment,Value=qwen-pii-finetuning Key=ExperimentId,Value="$EXPERIMENT_ID" \
  --query Role.Arn \
  --output text)
MLFLOW_ROLE_ARN=$(aws iam create-role \
  --role-name "$MLFLOW_ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --tags Key=Experiment,Value=qwen-pii-finetuning Key=ExperimentId,Value="$EXPERIMENT_ID" \
  --query Role.Arn \
  --output text)
aws iam wait role-exists --role-name "$EXECUTION_ROLE_NAME"
aws iam wait role-exists --role-name "$MLFLOW_ROLE_NAME"
write_inventory

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
APP_RESPONSE=$(aws sagemaker create-mlflow-app \
  --region "$REGION" \
  --name "$EXPERIMENT_ID" \
  --artifact-store-uri "s3://${BUCKET_NAME}/mlflow-artifacts" \
  --role-arn "$MLFLOW_ROLE_ARN" \
  --model-registration-mode AutoModelRegistrationDisabled \
  --account-default-status DISABLED \
  --tags Key=Experiment,Value=qwen-pii-finetuning Key=ExperimentId,Value="$EXPERIMENT_ID" \
  --output json)
MLFLOW_APP_ARN=$(jq -r '.Arn' <<<"$APP_RESPONSE")
write_inventory

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

UNIFIED_DOMAIN_ID=$(aws datazone list-domains \
  --region "$REGION" \
  --query "items[?name=='sagemaker_hyper'].id | [0]" \
  --output text)
if [[ -z "$UNIFIED_DOMAIN_ID" || "$UNIFIED_DOMAIN_ID" == "None" ]]; then
  printf 'Unified Studio domain sagemaker_hyper not found.\n' >&2
  exit 1
fi
PROJECT_PROFILE_ID=$(aws datazone list-project-profiles \
  --region "$REGION" \
  --domain-identifier "$UNIFIED_DOMAIN_ID" \
  --query "items[?name=='All capabilities' && status=='ENABLED'].id | [0]" \
  --output text)
if [[ -z "$PROJECT_PROFILE_ID" || "$PROJECT_PROFILE_ID" == "None" ]]; then
  printf 'Enabled All capabilities project profile not found.\n' >&2
  exit 1
fi
PROJECT_ID=$(aws datazone create-project \
  --region "$REGION" \
  --domain-identifier "$UNIFIED_DOMAIN_ID" \
  --name "$EXPERIMENT_ID" \
  --description "Ephemeral Qwen PII fine-tuning validation project" \
  --project-profile-id "$PROJECT_PROFILE_ID" \
  --resource-tags Experiment=qwen-pii-finetuning,ExperimentId="$EXPERIMENT_ID" \
  --query id \
  --output text)
write_inventory

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

write_inventory
trap - ERR INT TERM
printf 'Provisioned experiment %s; inventory: %s\n' "$EXPERIMENT_ID" "$INVENTORY"
