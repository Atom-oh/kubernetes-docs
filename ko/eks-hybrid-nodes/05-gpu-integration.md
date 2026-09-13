# GPU 서버 통합

< [이전: 노드 부트스트랩](./04-node-bootstrap.md) | [목차](./README.md) | [다음: 워크로드 배치 전략](./06-workload-placement.md) >

> **지원 버전**: DRA GPU 예제는 지원되는 EKS 버전의 Kubernetes 1.34.2 이상 필요. 확인한 인터페이스: GPU Operator 26.7.0, DRA driver 0.5.0, device plugin 0.20.0.
> **마지막 업데이트**: 2026년 9월 12일

이 문서는 준비한 NVIDIA GPU 호스트를 EKS Hybrid Nodes에 통합하며 할당, GPU Operator 소유권, MIG와 time-slicing을 다룹니다. **이번 감사에서 GPU 실행, 드라이버 설치, 모델 다운로드, 추론 벤치마크를 수행하지 않았습니다.** 예제에는 승인한 OS·커널·드라이버·toolkit·런타임·이미지 조합과 실제 하드웨어 시험이 필요합니다.

## GPU마다 할당 관리자 하나 선택

| 경로 | 사전 요구 사항과 할당 |
|---|---|
| 독립 NVIDIA device plugin | 준비한 호스트 드라이버, NVIDIA Container Toolkit·런타임. `nvidia.com/gpu` 등의 확장 리소스 게시 |
| 독립 DRA driver | 준비한 드라이버·CDI 런타임. ResourceSlice 게시 후 DeviceClass/ResourceClaim으로 할당 |
| `ClusterPolicy`를 사용하는 GPU Operator | Operator가 관리하는 device-plugin 방식. 기존 드라이버·toolkit·MIG 구성과 소유권을 맞춤 |
| `GPUCluster`를 사용하는 GPU Operator 26.7 | 신규 설치용 Operator 관리 DRA 방식. 같은 클러스터의 `ClusterPolicy`와 상호 배타적 |

AWS는 지원되는 정적 용량 프로비저닝을 사용하는 신규 EKS 1.34 이상 배포에 DRA를 권고합니다. **EKS Auto Mode는 현재 DRA를 지원하지 않으며** GPU device plugin을 자체 관리합니다. 아래 독립 설치 예제는 식별한 Hybrid GPU 노드만 대상으로 하며 Auto Mode나 다른 GPU 노드에 중복 할당 관리자를 설치하지 않습니다.

`workload.example.com/gpu-allocation=device-plugin` 또는 `dra`처럼 소유자가 관리하는 배타적인 label을 사용합니다. 이는 스케줄링 입력이며 보안 경계나 GPU 정상 상태의 증거가 아닙니다. 어느 경로든 활성화 전에 같은 물리 장치를 게시하는 다른 plugin·Operator가 없는지 확인합니다.

## 호스트 구성 조합 준비와 확인

- Hybrid 신원, CNI와 시각 동기화를 포함한 [노드 부트스트랩](./04-node-bootstrap.md)을 완료합니다.
- GPU 모델·form factor, firmware, 드라이버 branch, OS·커널·런타임을 NVIDIA 행렬 및 AWS Hybrid OS 지원과 대조합니다. 새 NVIDIA 행렬에 나오는 모든 Kubernetes 버전을 EKS가 제공한다는 뜻은 아닙니다.
- 실제 NVIDIA 드라이버와 toolkit 설치를 확인합니다. 온프레미스라는 이유만으로 드라이버가 설치되어 있다고 가정하지 않습니다.
- 기존 device-plugin 예제에는 containerd의 NVIDIA runtime handler에 연결된 `nvidia` 이름의 `RuntimeClass`가 필요합니다. Class 이름만으로 handler를 구성하지 못합니다.
- DRA 0.5.0 GPU 할당의 릴리스 사전 요구 사항은 Kubernetes **1.34.2 이상**, 독립 설치 드라이버 **565 이상**, Toolkit **1.18 이상**, CDI 활성 런타임입니다. GPU Operator DRA 방식은 드라이버 **580 이상**을 요구합니다. 이는 호환성 하한이며 현재 패치·branch 권고값이 아닙니다.
- 승인한 NFD/GFD 설치나 호스트 인벤토리 절차로 discovery label을 준비합니다. 예제에 활성화 옵션이 있다고 두 번째 discovery 컨트롤러를 배포하지 않습니다.

다음은 운영자가 실행하는 호스트 GPU 메타데이터 읽기이며 CUDA·LLM 벤치마크가 아닙니다.

```bash
nvidia-smi --query-gpu=name,driver_version,uuid,memory.total --format=csv,noheader
```

이전 예제의 `cpu: 128`, `memory: 1024Gi`, `nvidia.com/gpu: 8`은 **미검증 예시 출력**이며 이번 감사 실측이 아닙니다. Kubernetes GPU capacity는 구성에 따라 물리 GPU, MIG 인스턴스 또는 time-slicing replica를 나타낼 수 있습니다.

## 선택한 Hybrid Node의 독립 device plugin

다음 값은 드라이버·런타임 사전 설치와 기존 호환 discovery 구성을 요구합니다. 두 node-selector label은 차트의 GPU-discovery affinity와 함께 적용됩니다. 선택되는 노드가 없다면 인벤토리·label을 고치며 Pod를 실행시키기 위해 affinity를 제거하지 않습니다.

```yaml
nodeSelector:
  eks.amazonaws.com/compute-type: hybrid
  workload.example.com/gpu-allocation: device-plugin
runtimeClassName: nvidia
migStrategy: none
failOnInitError: true
deviceListStrategy: envvar
gfd:
  enabled: false
nfd:
  enabled: false
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
```

`device-plugin-values.yaml`로 저장합니다. 확인한 차트는 **0.20.0**이며 배포 전 업그레이드 경로와 이미지 호환성을 확인합니다.

```bash
# Cluster write; installs a privileged infrastructure component.
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" get nodes \
  -l 'eks.amazonaws.com/compute-type=hybrid,workload.example.com/gpu-allocation=device-plugin' \
  -o json > plugin-nodes.json
jq -e '.items | length > 0 and
  all(.[]; .metadata.labels["nvidia.com/mps.capable"] != "true")' plugin-nodes.json
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update nvdp
helm install hybrid-gpu-plugin nvdp/nvidia-device-plugin \
  --version 0.20.0 --namespace gpu-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values device-plugin-values.yaml --wait --timeout 10m
```

GPU 인프라 운영자가 소유한 namespace·release를 사용합니다. 렌더링된 RBAC, host path, privilege, 레지스트리 접근과 toleration을 검토합니다. Helm `--wait` 성공은 CUDA 호환성이나 워크로드 성능의 증거가 아닙니다.

게시된 0.20.0 차트는 선택한 Hybrid 집합과 `nvidia.com/mps.capable=true`로 한정한 MPS control DaemonSet도 렌더링합니다. 이 전용 GPU 예제는 해당 label이 이미 있으면 중단합니다. Label을 무조건 지우지 말고 기존 MPS 소유권을 조사하며, 차트에 DaemonSet 하나만 있다고 가정하지 않습니다.

## 별도 Hybrid GPU 집합의 독립 DRA

현재 드라이버 프로젝트는 **`kubernetes-sigs/dra-driver-nvidia-gpu`**입니다. DRA API 안정성, EKS 지원과 개별 공급자 기능 성숙도는 별도 확인합니다. 현재 NVIDIA 26.7 문서는 전체 GPU·기존 MIG 할당을 GA로 명시하며 동적 MIG, MPS, 일부 공유·NVML 할당 상태 기능에는 별도 Alpha gate가 있습니다. 데모를 시작하려고 모든 feature gate를 활성화하지 않습니다.

태그된 저장소 README의 이전 설명에는 GPU 할당 미지원 문구가 있습니다. 릴리스된 사전 요구 사항·설치 문서와 현재 NVIDIA 기능 표는 더 새로운 기능별 안내를 제공합니다. 운영 배포에는 정확한 버전과 지원 계약을 기록합니다.

일반 H100/H200 할당에는 Multi-Node NVLink 오케스트레이션이 필요하지 않아 이 예제는 ComputeDomains를 끕니다. ComputeDomains에는 Grace Blackwell/MNNVL, IMEX와 discovery 추가 요구 사항이 있습니다.

```yaml
gpuResourcesEnabledOverride: true
nvidiaDriverRoot: /
resources:
  gpus:
    enabled: true
  computeDomains:
    enabled: false
featureGates: {}
kubeletPlugin:
  nodeSelector:
    eks.amazonaws.com/compute-type: hybrid
    workload.example.com/gpu-allocation: dra
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  containers:
    gpus:
      resources:
        requests:
          cpu: 50m
          memory: 128Mi
        limits:
          cpu: "1"
          memory: 512Mi
webhook:
  enabled: false
```

`dra-values.yaml`로 저장합니다. 호스트 드라이버 root가 `/`이고 CDI가 구성되었다고 가정합니다. Operator가 설치한 드라이버는 일반적으로 다른 root를 사용하므로 이 값을 그대로 복사하지 않습니다.

```bash
# Alternative cluster write, only for the separately selected DRA cohort.
set -euo pipefail
: "${KUBECONFIG:?}" "${CONTEXT:?}"
helm install hybrid-gpu-dra \
  oci://registry.k8s.io/dra-driver-nvidia/charts/dra-driver-nvidia-gpu \
  --version 0.5.0 --namespace gpu-dra-system --create-namespace \
  --kubeconfig "$KUBECONFIG" --kube-context "$CONTEXT" \
  --values dra-values.yaml --wait --timeout 10m
```

이 차트는 GPU 리소스에 여전히 `gpuResourcesEnabledOverride=true`를 요구합니다. 옵션 존재가 모든 GPU 기능이 Alpha라는 뜻은 아닙니다. 최소 예제에서는 선택적 admission webhook을 끕니다. 이를 켜려면 접근 가능한 webhook 엔드포인트와 검증된 TLS/cert-manager 또는 기존 Secret 구성이 필요합니다.

### GPU Operator 대안과 소유권

Operator의 구성 요소 관리 방식이 의도한 설치와 맞을 때 사용합니다. `driver.enabled=false`는 **호스트 드라이버를 검증한 경우에만** 적절합니다. Toolkit 관리도 필요한 런타임 구성을 준비한 뒤에만 비활성화합니다. Operator 업그레이드는 드라이버, validator, 리소스 게시와 노드 가용성을 바꿀 수 있습니다.

**신규 Operator 관리 DRA**의 문서화된 값 예제:

```yaml
clusterPolicy:
  deployCR: false
gpuCluster:
  deployCR: true
driver:
  enabled: false
nfd:
  enabled: false
draDriver:
  computeDomains:
    enabled: false
```

승인한 드라이버·CDI 런타임·discovery의 사전 설치를 가정합니다. GPUCluster가 ClusterPolicy의 toolkit·MIG 관리 기능을 자동으로 제공하는 것은 아닙니다. **26.7.0**의 전체 차트 값을 검토한 뒤 클러스터 GPU 소유자를 통해 배포합니다.

`GPUCluster`는 이름이 `gpu-cluster`인 cluster-scoped singleton이며 `ClusterPolicy`와 공존할 수 없습니다. 이 방식은 ClusterPolicy 또는 독립 DRA Helm release에서 GPUCluster로의 제자리 마이그레이션을 지원하지 않습니다. 문서화된 신규 설치 경로를 사용하고 Operator 관리 배포에 독립 DRA release를 추가하지 않습니다.

Operator 컨트롤러의 `nodeSelector`는 **모든 operand를 한정하지 않습니다**. Operand 배치는 GPU discovery와 `nvidia.com/gpu.deploy.*` label을 사용합니다. 제외해야 할 클라우드·Auto Mode GPU와 새로 생길 노드까지 검토합니다. 경계를 유지할 수 없다면 분리된 클러스터 또는 적절히 한정한 독립 경로를 사용합니다.

GPUCluster 조정 과정은 GPU validator를 실행하고 claim을 할당할 수 있습니다. Readiness와 DCGM telemetry는 DRA 장치 할당 상태와 같지 않습니다. 이 릴리스의 `NVMLDeviceHealthCheck`는 Alpha이며 기본 비활성입니다.

## 현재 DRA manifest

다음 예제는 **`resource.k8s.io/v1`**을 사용합니다. Kubernetes 1.31의 이전 alpha 형태를 현재 클러스터에 그대로 적용하지 않습니다. DRA에는 동작하는 공급자 드라이버, ResourceSlice, 호환 kubelet·런타임과 활성 API가 필요합니다. DeviceClass만으로 GPU가 발견되지 않습니다.

```yaml
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-full-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu"
---
apiVersion: resource.k8s.io/v1
kind: DeviceClass
metadata:
  name: hybrid-large-gpu
spec:
  selectors:
    - cel:
        expression: >-
          device.driver == "gpu.nvidia.com" &&
          device.attributes["gpu.nvidia.com"].type == "gpu" &&
          device.capacity["gpu.nvidia.com"].memory.isGreaterThan(quantity("40Gi"))
---
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: single-large-gpu
  namespace: ai-workloads
spec:
  spec:
    devices:
      requests:
        - name: gpu
          exactly:
            deviceClassName: hybrid-large-gpu
            allocationMode: ExactCount
            count: 1
```

`type == "gpu"`는 같은 `gpu.nvidia.com` 드라이버가 게시하는 MIG·VFIO 장치를 제외합니다. 두 번째 class는 게시된 메모리가 **40 GiB보다 큰** 장치를 선택하며 H100/H200 전용 선택자가 아닙니다. 실제 capacity와 NVML `productName`은 ResourceSlice에서 확인합니다. `NVIDIA-H200` 같은 GFD node label과 DRA 제품명 속성이 같다고 가정하지 않습니다.

이 API의 DeviceClass에는 `suitableNodes` 필드가 없습니다. 워크로드 node selector·affinity와 DRA 장치·노드 가용성 매칭을 사용합니다. 요청은 `requests[].exactly`를 사용하며 Pod claim은 이전 `source` wrapper 없이 `resourceClaimTemplateName`을 직접 참조합니다.

## 제한된 GPU smoke Job

승인한 namespace(예: `ai-workloads`)와 선택한 드라이버·런타임, non-root UID, 읽기 전용 root filesystem에서 검증한 **다이제스트 고정 이미지**를 사용합니다. 아래 placeholder 이미지는 의도적으로 사용할 수 없는 값입니다. 두 Job은 **기본 정지 상태**이므로 적용만으로 GPU 작업을 시작하지 않습니다.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-plugin-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      runtimeClassName: nvidia
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: device-plugin
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
              nvidia.com/gpu: 1
            limits:
              cpu: 500m
              memory: 256Mi
              nvidia.com/gpu: 1
---
apiVersion: batch/v1
kind: Job
metadata:
  name: hybrid-gpu-dra-smoke
  namespace: ai-workloads
spec:
  suspend: true
  completions: 1
  parallelism: 1
  backoffLimit: 0
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      nodeSelector:
        eks.amazonaws.com/compute-type: hybrid
        workload.example.com/gpu-allocation: dra
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: gpu-check
          image: registry.example.invalid/approved/gpu-smoke:replace-with-approved-digest
          command: ["nvidia-smi", "-L"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
            claims:
              - name: gpu-resource
      resourceClaims:
        - name: gpu-resource
          resourceClaimTemplateName: single-large-gpu
```

첫 Job은 전용 GPU를 쓰는 기존 device-plugin 예제이며 두 번째는 별도 DRA 집합용입니다. 같은 GPU를 두 방식으로 요청하지 않습니다. 여러 컨테이너가 같은 DRA claim을 참조해도 할당은 하나입니다.

소유자가 이미지를 교체하고 배치·런타임·보안을 확인한 뒤 GPU 시험을 승인하면 일반 배포 절차로 의도한 Job 하나만 재개합니다. TTL 정리 전 결과를 보존합니다. 120초 deadline은 시작된 Job을 제한하며 이미지 준비나 외부 유지보수 작업 시간을 제한하는 값이 아닙니다.

장치 하나를 요청한 claim에 `CUDA_VISIBLE_DEVICES=0,1,2,3`을 설정하지 않습니다. 장치 관리자·런타임이 할당 장치를 제공하며 CUDA의 프로세스 내부 index와 물리 GPU index는 다를 수 있습니다. 수동 override는 할당을 숨기거나 잘못 식별할 수 있으며 추가 GPU를 허용하지 않습니다.

`nvidia-smi -L`은 장치 가시성만 확인합니다. 승인한 하드웨어에서 제한된 CUDA 연산과 실제 애플리케이션을 별도로 검증합니다. 여기서는 그 실행이나 성능 결과를 주장하지 않습니다.

## MIG와 time-slicing

MIG는 지원 GPU를 하드웨어 기반 compute·memory 인스턴스로 나눕니다. Time-slicing보다 강한 리소스·메모리·장애 격리를 제공하지만 공유 호스트·드라이버를 완전한 보안 경계로 바꾸거나 애플리케이션 지연 SLO를 보장하지 않습니다. 지원 profile·instance 한도는 GPU SKU와 드라이버에 따라 다릅니다.

일반적인 **A100 40 GB** profile:

| Profile | 명목상 profile 메모리 | 해당 profile 최대 인스턴스 |
|---|---|---|
| `1g.5gb` | 5 GB | 7 |
| `2g.10gb` | 10 GB | 3 |
| `3g.20gb` | 20 GB | 2 |
| `4g.20gb` | 20 GB | 1 |
| `7g.40gb` | 40 GB | 1 |

`4g.40gb`는 **A100 80 GB** profile 집합에 해당하며 이전 퀴즈는 두 SKU 표를 섞었습니다. `1g`는 profile의 GPU compute slice 수이며 물리 GPU 수가 아닙니다. 명목 메모리 label은 정확한 사용 가능 메모리 보장이 아닙니다. 혼합 profile 배치에는 추가 geometry 제약이 있습니다.

MIG 활성화·재구성은 GPU 워크로드를 중단할 수 있는 소유자 통제 유지보수 작업입니다. 위 독립 plugin 기본값은 `migStrategy: none`입니다. Pod 요청만 `nvidia.com/mig-1g.5gb`로 바꿔도 MIG 인스턴스가 생성되지는 않습니다. 실제 MIG geometry와 적절한 plugin strategy를 먼저 준비합니다.

Time-slicing은 물리적으로 분리된 GPU나 메모리 partition이 아닌 여러 **논리적 접근 슬롯**을 게시합니다. 별도 검토한 device-plugin 설정 예제:

```yaml
# Fragment of device-plugin configuration, not a Kubernetes resource.
version: v1
sharing:
  timeSlicing:
    renameByDefault: true
    failRequestsGreaterThanOne: true
    resources:
      - name: nvidia.com/gpu
        replicas: 4
```

이 구성을 이름 있는 ConfigMap/config 선택으로 plugin과 대상 노드에 연결합니다. 연결되지 않은 ConfigMap만으로 동작은 바뀌지 않습니다. `renameByDefault: true`이면 게시되는 리소스는 `nvidia.com/gpu.shared`입니다. 전용 GPU smoke 요청을 그대로 공유 리소스에 사용하지 않습니다.

Replica 4개는 독립적인 메모리 영역 4개를 예약하지 않으며 더 많은 슬롯 요청이 비례하는 compute를 보장하지 않습니다. 경합, context switch와 워크로드 동작이 지연·처리량에 영향을 줄 수 있으므로 원인을 하나로 단정하지 않고 측정합니다. Time-slicing replica 사이에는 메모리·장애 격리가 없습니다. 추론이라고 초과 할당이 자동으로 안전하거나 학습이 항상 공유와 호환되지 않는 것은 아닙니다.

## H100/H200 사양의 범위

| NVIDIA 사양 | H100 **SXM** | H200 **SXM** |
|---|---|---|
| GPU 메모리 | 80 GB HBM3 | 141 GB HBM3e |
| 게시된 메모리 대역폭 | 3.35 TB/s | 4.8 TB/s |
| MIG | 최대 7개, 모델별 profile | 최대 7개, 모델별 profile |

공급자 하드웨어 사양이며 이 Kubernetes 환경의 실측값이 아닙니다. H100 NVL/PCIe variant의 용량·대역폭은 다르므로 SXM 행을 모든 H100에 일반화하지 않습니다. 메모리 증가가 워크로드 수용에 도움이 될 수 있지만 실제 추론·학습 성능은 모델, 정밀도, batch, 소프트웨어, interconnect와 경합에도 영향을 받습니다.

## 할당 조사와 안전한 정리

명시적인 관리자 kubeconfig·context를 사용하고 하드웨어·Pod 진단은 비공개로 보관합니다.

```bash
set -euo pipefail
umask 077
: "${KUBECONFIG:?}" "${CONTEXT:?}"
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceslices -o json > gpu-slices.json
jq '[.items[] | select(.spec.driver == "gpu.nvidia.com") |
  {name: .metadata.name, node: .spec.nodeName,
   devices: [.spec.devices[] | {name, attributes, capacity}]}]' gpu-slices.json
kubectl --kubeconfig "$KUBECONFIG" --context "$CONTEXT" \
  get resourceclaims -n ai-workloads -o json > gpu-claims.json
jq '[.items[] | {name: .metadata.name,
  allocation: .status.allocation.devices.results,
  reservedFor: .status.reservedFor}]' gpu-claims.json
```

현재 ResourceClaim에는 일반적인 저장 필드로 `Pending → Allocated → Bound` phase enum이 없습니다. 할당 결과, 예약, Pod 스케줄링·이벤트와 드라이버 준비 상태를 확인합니다. 예약만으로 컨테이너의 GPU 사용 성공을 증명하지 못합니다. 이전 `resourceHandles` 예제는 현재 structured allocation 형태가 아닙니다.

로그를 조사할 때 선택한 드라이버 릴리스가 실제 렌더링하는 워크로드 이름·label을 사용합니다. Operator 관리 DRA와 독립 DRA release가 이전 `app=nvidia-dra-driver` selector를 공통 사용한다고 가정하지 않습니다.

결과를 보존한 뒤 소유한 시험 Job·Pod만 삭제하고 생성된 claim이 해제되고 장치가 unprepare되었는지 확인합니다. 보존된 claim·finalizer는 중지된 컨테이너보다 오래 남을 수 있습니다. 워크로드가 claim unprepare에 사용해야 하는 DRA kubelet plugin을 먼저 제거하지 않습니다.

Operator 관리 DRA는 문서화된 Helm hook·finalizer의 순서 있는 제거 절차를 사용합니다. `helm uninstall --no-hooks`나 공유 claim의 무조건적인 finalizer 제거·강제 삭제를 사용하지 않습니다. 실패한 정리를 리소스 소유자와 확인한 뒤 하드웨어를 재사용합니다.

## 공식 참고 자료

- [AWS NVIDIA 장치 관리](https://docs.aws.amazon.com/eks/latest/userguide/device-management-nvidia.html)
- [AWS Hybrid 추론: 범위를 제한한 device plugin](https://aws.amazon.com/blogs/containers/run-genai-inference-across-environments-with-amazon-eks-hybrid-nodes/)
- [GPU Operator 플랫폼·구성 요소 행렬](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html)
- [GPU Operator DRA/GPUCluster 절차](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/dra-intro-install.html)
- [DRA driver 0.5.0 사전 요구 사항](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/prerequisites.md)
- [DRA ResourceSlice 속성](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/v0.5.0/site/content/docs/reference/resourceslice-attributes.md)
- [Kubernetes DRA](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/)
- [NVIDIA device plugin 0.20.0](https://github.com/NVIDIA/k8s-device-plugin/tree/v0.20.0)
- [MIG profile](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-mig-profiles.html), [time-slicing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)
- [H100 사양](https://www.nvidia.com/en-us/data-center/h100/), [H200 사양](https://www.nvidia.com/en-us/data-center/h200/)

< [이전: 노드 부트스트랩](./04-node-bootstrap.md) | [목차](./README.md) | [다음: 워크로드 배치 전략](./06-workload-placement.md) >
