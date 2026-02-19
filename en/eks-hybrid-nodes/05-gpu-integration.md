# GPU Server Integration

< [Previous: Node Bootstrap](./04-node-bootstrap.md) | [Table of Contents](./README.md) | [Next: Workload Placement](./06-workload-placement.md) >

> **Supported Versions**: EKS 1.31+, NVIDIA GPU Operator 24.x+
> **Last Updated**: February 2025

This document covers integrating NVIDIA GPU servers (H100, H200, A100, L40S) with EKS Hybrid Nodes for AI/ML workloads.

## NVIDIA GPU Operator Deployment

The GPU Operator automatically deploys all components needed to manage NVIDIA GPUs in a Kubernetes cluster.

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

> **Note**: Since NVIDIA drivers are already installed on on-premises nodes, set `driver.enabled=false`.

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

Kubernetes 1.31+ enables more flexible GPU resource management through DRA.

### ResourceClass Definition

```yaml
# gpu-resource-class.yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClass
metadata:
  name: nvidia-gpu
driverName: gpu.nvidia.com
suitableNodes:
  nodeSelectorTerms:
  - matchExpressions:
    - key: nvidia.com/gpu.present
      operator: In
      values: ["true"]
---
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceClass
metadata:
  name: high-memory-gpu
driverName: gpu.nvidia.com
suitableNodes:
  nodeSelectorTerms:
  - matchExpressions:
    - key: nvidia.com/gpu.product
      operator: In
      values: ["NVIDIA-H100-80GB-HBM3", "NVIDIA-H200"]
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
    resourceClassName: nvidia-gpu
    allocationMode: WaitForFirstConsumer
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
    image: harbor.internal.company.io/ai/vllm-server:v0.4.0
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

< [Previous: Node Bootstrap](./04-node-bootstrap.md) | [Table of Contents](./README.md) | [Next: Workload Placement](./06-workload-placement.md) >
