# Integración de servidores GPU

< [Anterior: Bootstrap del nodo](./04-node-bootstrap.md) | [Tabla de contenidos](./README.md) | [Siguiente: Ubicación de workloads](./06-workload-placement.md) >

> **Versiones compatibles**: EKS 1.31+, NVIDIA GPU Operator 24.x+
> **Última actualización**: February 21, 2026

Este documento cubre la integración de servidores NVIDIA GPU (H100, H200, A100, L40S) con EKS Hybrid Nodes para workloads (cargas de trabajo) de AI/ML.

## Despliegue de NVIDIA GPU Operator

El GPU Operator despliega automáticamente todos los componentes necesarios para gestionar GPUs NVIDIA en un cluster Kubernetes.

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

> **Nota**: Dado que los drivers NVIDIA ya están instalados en los nodos on-premises, establezca `driver.enabled=false`.

## Integración de servidores H100/H200

### Verificar la configuración de Device Plugin

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

### Verificación de recursos GPU

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

Kubernetes 1.31+ permite una gestión más flexible de recursos GPU mediante DRA.

### Definición de DeviceClass

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

### Plantilla de ResourceClaim

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

### Definición de Pod usando DRA

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

### Métricas de monitoreo de DRA

```bash
# Check ResourceClaim status
kubectl get resourceclaims -n ai-workloads

# ResourceClaim details
kubectl describe resourceclaim gpu-claim-template-xxxxx -n ai-workloads

# Check DRA controller logs
kubectl logs -n gpu-operator -l app=nvidia-dra-driver -f
```

---

< [Anterior: Bootstrap del nodo](./04-node-bootstrap.md) | [Tabla de contenidos](./README.md) | [Siguiente: Ubicación de workloads](./06-workload-placement.md) >
