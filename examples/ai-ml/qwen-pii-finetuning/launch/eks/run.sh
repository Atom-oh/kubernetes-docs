#!/usr/bin/env bash
set -euo pipefail

export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker
export AWS_RETRY_MODE=adaptive
export AWS_MAX_ATTEMPTS=10

umask 077
PYTHON=${PYTHON:-python3}
MODE=${1:-}
if [[ "$MODE" != "smoke" && "$MODE" != "full" ]]; then
  printf 'Usage: %s smoke|full\n' "$0" >&2
  exit 2
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
# This pinned cohort is executable only while its upstream patch support is current.
"${PYTHON:-python3}" "$PACKAGE_ROOT/src/runtime_contract.py" --check-execution
INVENTORY="$PACKAGE_ROOT/results/resource-inventory.json"
RESULTS_DIR="$PACKAGE_ROOT/results"
REGION=ap-northeast-2
HELPER="$SCRIPT_DIR/../aws/lifecycle.py"
DLC_IMAGE=763104351884.dkr.ecr.ap-northeast-2.amazonaws.com/pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker

if [[ ! -f "$INVENTORY" ]]; then
  printf 'Resource inventory is required: %s\n' "$INVENTORY" >&2
  exit 1
fi

"$PYTHON" "$HELPER" check "$INVENTORY"
BASE_EXPERIMENT_ID=$(jq -er '.experiment_id' "$INVENTORY")
BUCKET_NAME=$(jq -er '.bucket_name' "$INVENTORY")
OWNERSHIP_TOKEN=$(jq -er '.ownership_token' "$INVENTORY")
ACCOUNT_ID=$(jq -er '.account_id' "$INVENTORY")
EXPERIMENT_ID="${BASE_EXPERIMENT_ID}-${MODE}-eks"
STEPS=80
[[ "$MODE" == "smoke" ]] && STEPS=10
mkdir -p "$RESULTS_DIR"
RENDER_DIR=$(mktemp -d "$RESULTS_DIR/eks-${MODE}.XXXXXX")
export KUBECONFIG="$RENDER_DIR/kubeconfig"
CLUSTER_DELETED=0
finalize() {
  status=$?
  trap - EXIT INT TERM
  if [[ "$CLUSTER_DELETED" != 1 ]]; then
    printf 'EKS was not confirmed deleted. Inspect %s and %s. Partial/unknown creation requires manual recovery; retained resources continue to incur costs. No workload logs were dumped.\n' "$INVENTORY" "$RENDER_DIR" >&2
    ((status != 0)) || status=1
  fi
  exit "$status"
}
trap finalize EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Validate the private hash receipt and bootstrap code before allocating resources.
test -f "$SCRIPT_DIR/download_inputs.py"
"$PYTHON" "$HELPER" input-manifest "$INVENTORY" --output "$RENDER_DIR/input-manifest.json"
for key in source/source.tar.gz dataset/train.jsonl dataset/validation.jsonl dataset/test.jsonl dataset/dataset-manifest.json; do
  aws s3api head-object --region "$REGION" --bucket "$BUCKET_NAME" \
    --expected-bucket-owner "$ACCOUNT_ID" --key "qwen-pii/${BASE_EXPERIMENT_ID}/${key}" >/dev/null
done
export EXPERIMENT_ID BASE_EXPERIMENT_ID OWNERSHIP_TOKEN MODE STEPS BUCKET_NAME ACCOUNT_ID
"$PYTHON" "$HELPER" eks-plan "$INVENTORY" "$EXPERIMENT_ID" --kubeconfig "$KUBECONFIG"
jq -e --arg key "eks:$EXPERIMENT_ID" '.resources[$key].expected_export' \
  "$INVENTORY" > "$RENDER_DIR/expected-export.json"
EXECUTION_ID=$(jq -er '.execution_id' "$RENDER_DIR/expected-export.json")
INPUT_ROLE_NAME=$(jq -er --arg key "eks:$EXPERIMENT_ID" '.resources[$key].workload_identity.role_name' "$INVENTORY")
export EXECUTION_ID INPUT_ROLE_NAME
envsubst '${EXPERIMENT_ID} ${BASE_EXPERIMENT_ID} ${OWNERSHIP_TOKEN} ${BUCKET_NAME} ${ACCOUNT_ID} ${INPUT_ROLE_NAME}' \
  < "$SCRIPT_DIR/cluster.yaml" > "$RENDER_DIR/cluster.yaml"
# Failure never grants cleanup ownership. The creating journal survives host loss.
eksctl create cluster -f "$RENDER_DIR/cluster.yaml" \
  --install-nvidia-plugin=false --write-kubeconfig=false --timeout 45m
"$PYTHON" "$HELPER" eks-confirm "$INVENTORY" "$EXPERIMENT_ID"
aws eks update-kubeconfig --name "$EXPERIMENT_ID" --region "$REGION" \
  --kubeconfig "$KUBECONFIG" --alias "$EXPERIMENT_ID" >/dev/null

kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
kubectl rollout status daemonset/eks-pod-identity-agent --namespace kube-system --timeout=5m
kubectl create configmap qwen-pii-input-loader --namespace qwen-pii \
  --from-file=download_inputs.py="$SCRIPT_DIR/download_inputs.py" \
  --from-file=input-manifest.json="$RENDER_DIR/input-manifest.json" \
  --dry-run=client -o yaml | kubectl apply -f -
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin --force-update >/dev/null
helm repo update nvdp >/dev/null
helm upgrade --install nvidia-device-plugin nvdp/nvidia-device-plugin \
  --version 0.20.0 \
  --namespace nvidia-device-plugin \
  --create-namespace \
  --wait \
  --timeout 10m

GPU_READY=0
for _attempt in $(seq 1 60); do
  if kubectl get nodes -o json | jq -e \
    'any(.items[]; (.status.allocatable["nvidia.com/gpu"] // "0") != "0")' \
    >/dev/null; then
    GPU_READY=1
    break
  fi
  sleep 10
done
if [[ "$GPU_READY" != "1" ]]; then
  printf 'GPU resource did not become allocatable.\n' >&2
  exit 1
fi

kubectl run gpu-check \
  --namespace qwen-pii \
  --image "$DLC_IMAGE" \
  --restart Never \
  --overrides "{
    \"spec\": {
      \"nodeSelector\": {\"workload\": \"qwen-pii-training\"},
      \"containers\": [{
        \"name\": \"gpu-check\",
        \"image\": \"$DLC_IMAGE\",
        \"command\": [\"nvidia-smi\"],
        \"resources\": {\"limits\": {\"nvidia.com/gpu\": 1}}
      }]
    }
  }"
kubectl wait --namespace qwen-pii --for=jsonpath='{.status.phase}'=Succeeded \
  pod/gpu-check --timeout=10m
kubectl delete pod --namespace qwen-pii gpu-check --wait=true

kubectl apply -f "$SCRIPT_DIR/mlflow.yaml"
kubectl rollout status deployment/mlflow \
  --namespace qwen-pii \
  --timeout=10m

envsubst '${MODE} ${STEPS} ${EXPERIMENT_ID} ${BASE_EXPERIMENT_ID} ${BUCKET_NAME} ${ACCOUNT_ID} ${EXECUTION_ID}' \
  < "$SCRIPT_DIR/training-job.yaml" > "$RENDER_DIR/training-job.yaml"
kubectl apply -f "$RENDER_DIR/training-job.yaml"
if ! kubectl wait \
  --namespace qwen-pii \
  --for=condition=complete \
  "job/qwen-pii-${MODE}" \
  --timeout=10800s; then
  printf 'Training did not complete; retain the cluster for private diagnosis/export.\n' >&2
  exit 1
fi

MLFLOW_POD=$(kubectl get pods \
  --namespace qwen-pii \
  --selector app=mlflow \
  --output jsonpath='{.items[0].metadata.name}')
kubectl cp \
  "$SCRIPT_DIR/export_mlflow.py" \
  "qwen-pii/${MLFLOW_POD}:/tmp/export_mlflow.py"
kubectl exec --namespace qwen-pii "$MLFLOW_POD" -- \
  python /tmp/export_mlflow.py --mode "$MODE" \
    --experiment-id "$BASE_EXPERIMENT_ID" --cluster-name "$EXPERIMENT_ID" \
    --execution-id "$EXECUTION_ID"
ARCHIVE="$RENDER_DIR/mlflow-export-${MODE}.tar.gz"
kubectl cp "qwen-pii/${MLFLOW_POD}:/tmp/mlflow-export-${MODE}.tar.gz" "$ARCHIVE"
"$PYTHON" "$SCRIPT_DIR/verify_export.py" "$ARCHIVE" --mode "$MODE" \
  --expected-provenance "$RENDER_DIR/expected-export.json" > "$RENDER_DIR/export-receipt.json"
# Rechecks local hashes and owned cluster/stack identities; failures stay nonzero.
"$PYTHON" "$HELPER" eks-delete "$INVENTORY" "$EXPERIMENT_ID" --archive "$ARCHIVE" --mode "$MODE"
CLUSTER_DELETED=1
printf 'Export verified and EKS deletion confirmed. Private artifacts: %s\n' "$ARCHIVE"
