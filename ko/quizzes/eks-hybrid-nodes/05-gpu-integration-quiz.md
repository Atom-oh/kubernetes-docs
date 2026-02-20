# EKS Hybrid Nodes GPU 통합 퀴즈

> **관련 문서**: [GPU 통합](../../eks-hybrid-nodes/05-gpu-integration.md)

## 객관식 문제

### 1. NVIDIA GPU의 Multi-Instance GPU (MIG) 기술의 주요 특징은?

A. 여러 GPU를 하나로 통합
B. 단일 GPU를 물리적으로 격리된 여러 인스턴스로 분할
C. GPU 메모리만 공유
D. 소프트웨어 레벨의 시분할

<details>
<summary>정답 보기</summary>

**정답: B. 단일 GPU를 물리적으로 격리된 여러 인스턴스로 분할**

**설명:**
MIG(Multi-Instance GPU)는 NVIDIA A100, H100 등의 GPU를 최대 7개의 물리적으로 격리된 인스턴스로 분할합니다. 각 인스턴스는 독립적인 메모리, 캐시, 컴퓨팅 리소스를 가집니다.

**MIG vs Time-Slicing 비교:**

| 특성 | MIG | Time-Slicing |
|-----|-----|--------------|
| 격리 수준 | 물리적 (완전 격리) | 시간 기반 (소프트웨어) |
| 메모리 격리 | 완전 격리 | 공유 |
| 지원 GPU | A100, H100 | 모든 NVIDIA GPU |
| QoS 보장 | 예 | 아니오 |

```yaml
# MIG 리소스 요청
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  containers:
  - name: cuda-app
    image: nvidia/cuda:12.0-runtime
    resources:
      limits:
        nvidia.com/mig-1g.5gb: 1
```

</details>

### 2. NVIDIA GPU MIG 구성에서 "1g.5gb"의 의미는 무엇인가요?

A. 1GB 메모리, 5개 GPU 코어
B. 1 GPU Instance (컴퓨팅 슬라이스 1개), 5GB GPU 메모리
C. 1개 GPU, 5GB 시스템 메모리
D. 1초당 5GB 처리량

<details>
<summary>정답 보기</summary>

**정답: B. 1 GPU Instance (컴퓨팅 슬라이스 1개), 5GB GPU 메모리**

**설명:**
MIG 인스턴스 이름 형식: `<compute-slices>g.<memory-size>gb`

- **1g**: 1 컴퓨팅 슬라이스
- **5gb**: 5GB GPU 메모리

**A100 MIG 프로파일 예시:**
- `1g.5gb`: 1 컴퓨팅 슬라이스, 5GB 메모리 (최대 7개)
- `2g.10gb`: 2 컴퓨팅 슬라이스, 10GB 메모리 (최대 3개)
- `3g.20gb`: 3 컴퓨팅 슬라이스, 20GB 메모리 (최대 2개)
- `4g.40gb`: 4 컴퓨팅 슬라이스, 40GB 메모리 (최대 1개)
- `7g.40gb`: 7 컴퓨팅 슬라이스, 40GB 메모리 (전체 GPU)

```bash
# MIG 인스턴스 확인
nvidia-smi mig -lgi
```

</details>

### 3. GPU Time-Slicing에서 oversubscription이 발생할 때 예상되는 현상은?

A. GPU 작업 완전 실패
B. 컨텍스트 스위칭으로 인한 성능 저하
C. 자동 GPU 추가
D. 메모리 자동 확장

<details>
<summary>정답 보기</summary>

**정답: B. 컨텍스트 스위칭으로 인한 성능 저하**

**설명:**
Time-Slicing은 하나의 GPU를 시간 단위로 여러 워크로드가 공유합니다. Oversubscription(초과 할당) 시 컨텍스트 스위칭이 빈번해져 성능이 저하됩니다.

```yaml
# GPU Time-Slicing 설정
apiVersion: v1
kind: ConfigMap
metadata:
  name: device-plugin-config
  namespace: nvidia-device-plugin
data:
  config.yaml: |
    version: v1
    sharing:
      timeSlicing:
        resources:
        - name: nvidia.com/gpu
          replicas: 4  # 1 GPU를 4개로 분할
```

**Time-Slicing 고려사항:**
- 메모리는 공유되므로 OOM 발생 가능
- 추론(inference) 워크로드에 적합
- 학습(training)에는 MIG 또는 전용 GPU 권장
- 적절한 replicas 수 설정 중요

</details>

### 4. Dynamic Resource Allocation (DRA)의 주요 장점은?

A. 정적 리소스 할당만 지원
B. 벤더별 플러그인 없이 모든 디바이스 지원
C. 사용자 정의 리소스에 대한 유연한 요청/할당 메커니즘
D. CPU와 메모리만 관리

<details>
<summary>정답 보기</summary>

**정답: C. 사용자 정의 리소스에 대한 유연한 요청/할당 메커니즘**

**설명:**
DRA(Dynamic Resource Allocation)는 Kubernetes 1.26에서 도입된 기능으로, GPU, FPGA, 네트워크 디바이스 등 사용자 정의 리소스에 대해 더 유연한 요청 및 할당 메커니즘을 제공합니다.

**DRA의 핵심 구성 요소:**
- **ResourceClass**: 드라이버가 제공하는 리소스 유형 정의
- **ResourceClaim**: 리소스에 대한 요청
- **ResourceClaimTemplate**: 재사용 가능한 클레임 템플릿

```yaml
# Pod에서 DRA 사용
apiVersion: v1
kind: Pod
metadata:
  name: gpu-workload
spec:
  containers:
  - name: cuda-app
    resources:
      claims:
      - name: gpu
  resourceClaims:
  - name: gpu
    source:
      resourceClaimTemplateName: gpu-claim-template
```

</details>

### 5. DRA(Dynamic Resource Allocation)에서 ResourceClaim의 상태가 "Bound"가 되려면 어떤 조건이 충족되어야 하나요?

A. 클레임 생성만 완료
B. 드라이버가 리소스를 할당하고 Pod가 스케줄링됨
C. Pod가 종료됨
D. 클레임이 삭제됨

<details>
<summary>정답 보기</summary>

**정답: B. 드라이버가 리소스를 할당하고 Pod가 스케줄링됨**

**설명:**
ResourceClaim 상태 흐름:

1. **Pending**: 클레임 생성됨, 아직 할당 안됨
2. **Allocated**: 드라이버가 리소스 할당 완료
3. **Bound**: Pod에 바인딩되어 사용 중

```yaml
# ResourceClaim 상태 확인
kubectl get resourceclaim gpu-claim -o yaml

# 예상 출력
status:
  allocation:
    resourceHandles:
    - driverName: gpu.nvidia.com
      data: '{"gpu":"GPU-abc123"}'
  reservedFor:
  - name: gpu-workload
    uid: xxx-xxx-xxx
```

</details>

### 6. NVIDIA GPU Operator의 주요 역할은?

A. GPU 하드웨어 제조
B. Kubernetes에서 GPU 드라이버, 런타임, 플러그인 자동 관리
C. GPU 성능 테스트만 수행
D. GPU 구매 및 배송 관리

<details>
<summary>정답 보기</summary>

**정답: B. Kubernetes에서 GPU 드라이버, 런타임, 플러그인 자동 관리**

**설명:**
NVIDIA GPU Operator는 Kubernetes에서 GPU 인프라를 자동으로 관리합니다:

- NVIDIA 드라이버 설치/업데이트
- NVIDIA Container Toolkit 설치
- NVIDIA Device Plugin 배포
- GPU 모니터링 (DCGM Exporter)
- MIG 관리

```bash
# GPU Operator 설치 (Helm)
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

```yaml
# GPU Operator 커스텀 설정
apiVersion: nvidia.com/v1
kind: ClusterPolicy
metadata:
  name: cluster-policy
spec:
  driver:
    enabled: true
    version: "535.104.12"
  toolkit:
    enabled: true
  devicePlugin:
    enabled: true
  mig:
    strategy: mixed
```

</details>

### 7. H100과 H200 GPU의 주요 차이점은?

A. H200은 H100보다 메모리 용량이 작음
B. H200은 H100보다 HBM3e 메모리와 더 높은 대역폭 제공
C. H200은 MIG를 지원하지 않음
D. H200은 데이터센터용이 아님

<details>
<summary>정답 보기</summary>

**정답: B. H200은 H100보다 HBM3e 메모리와 더 높은 대역폭 제공**

**설명:**
H200은 H100의 후속 모델로, 향상된 메모리 시스템을 제공합니다:

| 특성 | H100 | H200 |
|-----|------|------|
| 메모리 유형 | HBM3 | HBM3e |
| 메모리 용량 | 80GB | 141GB |
| 메모리 대역폭 | 3.35TB/s | 4.8TB/s |
| MIG 지원 | 예 (최대 7개) | 예 (최대 7개) |
| LLM 추론 | 우수 | 최적화 |

```yaml
# H200 노드 선택
apiVersion: v1
kind: Pod
spec:
  nodeSelector:
    nvidia.com/gpu.product: "NVIDIA-H200"
  containers:
  - name: llm
    resources:
      limits:
        nvidia.com/gpu: 1
```

H200은 특히 대규모 언어 모델(LLM) 추론에서 메모리 용량과 대역폭 덕분에 우수한 성능을 보입니다.

</details>

