#!/usr/bin/env bash
set -euo pipefail

export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker
export AWS_RETRY_MODE=adaptive
export AWS_MAX_ATTEMPTS=10

MODE=${1:-}
if [[ "$MODE" != "smoke" && "$MODE" != "full" ]]; then
  printf 'Usage: %s smoke|full\n' "$0" >&2
  exit 2
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PACKAGE_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd -P)
INVENTORY="$PACKAGE_ROOT/results/resource-inventory.json"
RESULTS_DIR="$PACKAGE_ROOT/results"
REGION=ap-northeast-2
DLC_IMAGE=763104351884.dkr.ecr.ap-northeast-2.amazonaws.com/pytorch-training:2.8.0-gpu-py312-cu129-ubuntu22.04-sagemaker

if [[ ! -f "$INVENTORY" ]]; then
  printf 'Resource inventory is required: %s\n' "$INVENTORY" >&2
  exit 1
fi

BASE_EXPERIMENT_ID=$(jq -r '.experiment_id' "$INVENTORY")
BUCKET_NAME=$(jq -r '.bucket_name' "$INVENTORY")
EXPERIMENT_ID="${BASE_EXPERIMENT_ID}-${MODE}-eks"
STEPS=80
[[ "$MODE" == "smoke" ]] && STEPS=10
RENDER_DIR=$(mktemp -d /tmp/qwen-eks-render.XXXXXX)
CLUSTER_CREATED=0

cleanup() {
  status=$?
  trap - EXIT INT TERM
  if [[ "$CLUSTER_CREATED" == "1" ]]; then
    eksctl delete cluster \
      --name "$EXPERIMENT_ID" \
      --region "$REGION" \
      --wait || true
  fi
  exit "$status"
}
trap cleanup EXIT INT TERM

export EXPERIMENT_ID MODE STEPS
envsubst < "$SCRIPT_DIR/cluster.yaml" > "$RENDER_DIR/cluster.yaml"
CLUSTER_CREATED=1
eksctl create cluster \
  -f "$RENDER_DIR/cluster.yaml" \
  --install-nvidia-plugin=false

jq --arg cluster "$EXPERIMENT_ID" \
  '.eks_clusters = ((.eks_clusters // []) + [$cluster] | unique)' \
  "$INVENTORY" > "${INVENTORY}.tmp"
mv "${INVENTORY}.tmp" "$INVENTORY"

kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin >/dev/null 2>&1 || true
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
kubectl logs --namespace qwen-pii gpu-check
kubectl delete pod --namespace qwen-pii gpu-check --wait=true

kubectl apply -f "$SCRIPT_DIR/mlflow.yaml"
kubectl rollout status deployment/mlflow \
  --namespace qwen-pii \
  --timeout=10m

OBJECT_ROOT="s3://${BUCKET_NAME}/qwen-pii/${BASE_EXPERIMENT_ID}"
SOURCE_URL=$(aws s3 presign "${OBJECT_ROOT}/source/source.tar.gz" --expires-in 14400)
TRAIN_URL=$(aws s3 presign "${OBJECT_ROOT}/dataset/train.jsonl" --expires-in 14400)
VALIDATION_URL=$(aws s3 presign "${OBJECT_ROOT}/dataset/validation.jsonl" --expires-in 14400)
TEST_URL=$(aws s3 presign "${OBJECT_ROOT}/dataset/test.jsonl" --expires-in 14400)
MANIFEST_URL=$(aws s3 presign "${OBJECT_ROOT}/dataset/dataset-manifest.json" --expires-in 14400)
export SOURCE_URL TRAIN_URL VALIDATION_URL TEST_URL MANIFEST_URL

envsubst < "$SCRIPT_DIR/training-job.yaml" > "$RENDER_DIR/training-job.yaml"
kubectl apply -f "$RENDER_DIR/training-job.yaml"
if ! kubectl wait \
  --namespace qwen-pii \
  --for=condition=complete \
  "job/qwen-pii-${MODE}" \
  --timeout=10800s; then
  kubectl logs --namespace qwen-pii "job/qwen-pii-${MODE}" --tail=500
  exit 1
fi
kubectl logs --namespace qwen-pii "job/qwen-pii-${MODE}" --tail=500

MLFLOW_POD=$(kubectl get pods \
  --namespace qwen-pii \
  --selector app=mlflow \
  --output jsonpath='{.items[0].metadata.name}')
kubectl cp \
  "$SCRIPT_DIR/export_mlflow.py" \
  "qwen-pii/${MLFLOW_POD}:/tmp/export_mlflow.py"
kubectl exec --namespace qwen-pii "$MLFLOW_POD" -- \
  python /tmp/export_mlflow.py
mkdir -p "$RESULTS_DIR"
kubectl cp \
  "qwen-pii/${MLFLOW_POD}:/tmp/mlflow-export.json" \
  "$RESULTS_DIR/eks-mlflow-${MODE}.json"

cleanup
