# GPU 서버 통합

< [이전: 노드 부트스트랩](./04-node-bootstrap.md) | [목차](./README.md) | [다음: 워크로드 배치 전략](./06-workload-placement.md) >

> **지원 버전**: EKS 1.31+, nodeadm 0.1+, Harbor 2.13+
> **마지막 업데이트**: 2025년 2월

이 문서에서는 온프레미스 GPU 서버를 EKS Hybrid Nodes에 통합하는 방법을 다룹니다.

## NVIDIA GPU Operator 배포

GPU Operator는 Kubernetes 클러스터에서 NVIDIA GPU를 관리하기 위한 모든 구성 요소를 자동으로 배포합니다.

```bash
# NVIDIA GPU Operator Helm 저장소 추가
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

# GPU Operator 설치
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --set driver.enabled=false \
  --set toolkit.enabled=true \
  --set devicePlugin.enabled=true \
  --set migManager.enabled=false \
  --set dcgmExporter.enabled=true
```

> **참고**: 온프레미스 노드에 이미 NVIDIA 드라이버가 설치되어 있으므로 `driver.enabled=false`로 설정합니다.

## H100/H200 서버 통합

### Device Plugin 구성 확인

```bash
# GPU 노드에서 Device Plugin 상태 확인
kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset

# GPU 리소스 확인
kubectl describe node hybrid-gpu-node-001 | grep -A 10 "Allocatable:"
# 예상 출력:
# Allocatable:
#   cpu:                128
#   memory:             1024Gi
#   nvidia.com/gpu:     8
```

### GPU 리소스 검증

```bash
# 테스트 Pod으로 GPU 접근 확인
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

Kubernetes 1.31+에서는 DRA를 통해 더 유연한 GPU 리소스 관리가 가능합니다.

### ResourceClass 정의

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

### ResourceClaim 템플릿

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

### DRA를 사용하는 Pod 정의

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

### DRA 모니터링 메트릭

```bash
# ResourceClaim 상태 확인
kubectl get resourceclaims -n ai-workloads

# ResourceClaim 상세 정보
kubectl describe resourceclaim gpu-claim-template-xxxxx -n ai-workloads

# DRA 컨트롤러 로그 확인
kubectl logs -n gpu-operator -l app=nvidia-dra-driver -f
```

---

< [이전: 노드 부트스트랩](./04-node-bootstrap.md) | [목차](./README.md) | [다음: 워크로드 배치 전략](./06-workload-placement.md) >
