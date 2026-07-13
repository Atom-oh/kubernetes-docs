# GPU 服务器集成

< [上一页：Node Bootstrap](./04-node-bootstrap.md) | [目录](./README.md) | [下一页：Workload Placement](./06-workload-placement.md) >

> **支持的版本**：EKS 1.31+、NVIDIA GPU Operator 24.x+
> **最后更新**：February 21, 2026

本文档介绍如何将 NVIDIA GPU 服务器（H100、H200、A100、L40S）与 EKS Hybrid Nodes 集成，用于 AI/ML 工作负载。

## NVIDIA GPU Operator 部署

GPU Operator 会自动部署在 Kubernetes 集群中管理 NVIDIA GPU 所需的所有组件。

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

> **注意**：由于 NVIDIA drivers 已安装在本地 Node 上，请设置 `driver.enabled=false`。

## H100/H200 服务器集成

### 验证 Device Plugin 配置

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

### GPU 资源验证

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

Kubernetes 1.31+ 可通过 DRA 实现更灵活的 GPU 资源管理。

### DeviceClass 定义

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

### ResourceClaim 模板

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

### 使用 DRA 的 Pod 定义

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

### DRA 监控指标

```bash
# Check ResourceClaim status
kubectl get resourceclaims -n ai-workloads

# ResourceClaim details
kubectl describe resourceclaim gpu-claim-template-xxxxx -n ai-workloads

# Check DRA controller logs
kubectl logs -n gpu-operator -l app=nvidia-dra-driver -f
```

---

< [上一页：Node Bootstrap](./04-node-bootstrap.md) | [目录](./README.md) | [下一页：Workload Placement](./06-workload-placement.md) >
