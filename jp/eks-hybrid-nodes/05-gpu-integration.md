# GPU Server Integration

< [前へ: Node Bootstrap](./04-node-bootstrap.md) | [目次](./README.md) | [次へ: Workload Placement](./06-workload-placement.md) >

> **サポート対象バージョン**: EKS 1.31+, NVIDIA GPU Operator 24.x+
> **最終更新**: February 21, 2026

このドキュメントでは、AI/ML workloads 向けに NVIDIA GPU servers（H100、H200、A100、L40S）を EKS Hybrid Nodes と統合する方法について説明します。

## NVIDIA GPU Operator Deployment

GPU Operator は、Kubernetes cluster 内の NVIDIA GPUs を管理するために必要なすべての components を自動的にデプロイします。

```bash
# Add NVIDIA GPU Operator Helm repository
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# Install GPU Operator
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --set driver.enabled=false \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true \
  --set migManager.enabled=false \
  --set dcgmExporter.enabled=true
```

> **注記**: NVIDIA drivers はオンプレミス nodes にすでにインストールされているため、`driver.enabled=false` を設定します。

## H100/H200 Server Integration

### Verify Device Plugin Configuration

```bash
# Check Device Plugin status on GPU nodes
kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset

# Check GPU resources
kubectl describe node hybrid-gpu-node-001 | grep -A 10 "Allocatable:"
# Expected output:
# Allocatable:
#   cpu:                128
#   memory:             1024Gi
#   nvidia.com/gpu:     8
```

### GPU Resource Verification

```bash
# Verify GPU access with test Pod
kubectl run gpu-test --rm -it \
  --image=nvidia/cuda:12.3.1-base-ubuntu22.04 \
  --restart=Never \
  --overrides='
{
  "spec": {
    "nodeSelector": {"topology.kubernetes.io/zone": "on-premises"},
    "tolerations": [{"key": "location", "operator": "Equal", "value": "on-premises", "effect": "NoSchedule"}],
    "containers": [{
      "name": "gpu-test",
      "image": "nvidia/cuda:12.3.1-base-ubuntu22.04",
      "command": ["nvidia-smi"],
      "resources": {"limits": {"nvidia.com/gpu": "1"}}
    }]
  }
}' \
  -- nvidia-smi
```

## Dynamic Resource Allocation (DRA)

Kubernetes 1.31+ では、DRA を通じてより柔軟な GPU resource management が可能になります。

### DeviceClass Definition

```yaml
# gpu-device-class.yaml
apiVersion: resource.k8s.io/v1alpha3
kind: DeviceClass
metadata:
  name: nvidia-gpu
spec:
  selectors:
  - cel:
      expression: "device.driver == 'gpu.nvidia.com'"
---
apiVersion: resource.k8s.io/v1alpha3
kind: DeviceClass
metadata:
  name: high-memory-gpu
spec:
  selectors:
  - cel:
      expression: "device.driver == 'gpu.nvidia.com' && device.attributes['gpu.nvidia.com'].productName in ['NVIDIA-H100-80GB-HBM3', 'NVIDIA-H200']"
```

### ResourceClaim Template

```yaml
# gpu-resource-claim-template.yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClaimTemplate
metadata:
  name: gpu-claim-template
  namespace: ai-workloads
spec:
  spec:
    devices:
      requests:
      - name: gpu
        deviceClassName: nvidia-gpu
        count: 1
```

### Pod Definition Using DRA

```yaml
# pod-with-dra.yaml
apiVersion: v1
kind: Pod
metadata:
  name: llm-inference-pod
  namespace: ai-workloads
spec:
  nodeSelector:
    topology.kubernetes.io/zone: on-premises
  tolerations:
  - key: location
    operator: Equal
    value: on-premises
    effect: NoSchedule
  containers:
  - name: llm-server
    image: <REGISTRY>/ai/vllm-server:v0.4.0
    resources:
      claims:
      - name: gpu-resource
    env:
    - name: CUDA_VISIBLE_DEVICES
      value: "0,1,2,3"
  resourceClaims:
  - name: gpu-resource
    source:
      resourceClaimTemplateName: gpu-claim-template
```

### DRA Monitoring Metrics

```bash
# Check ResourceClaim status
kubectl get resourceclaims -n ai-workloads

# ResourceClaim details
kubectl describe resourceclaim gpu-claim-template-xxxxx -n ai-workloads

# Check DRA controller logs
kubectl logs -n gpu-operator -l app=nvidia-dra-driver -f
```

---

< [前へ: Node Bootstrap](./04-node-bootstrap.md) | [目次](./README.md) | [次へ: Workload Placement](./06-workload-placement.md) >
