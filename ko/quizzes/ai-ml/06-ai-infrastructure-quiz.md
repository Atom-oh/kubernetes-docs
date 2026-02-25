# EKS 기반 AI 인프라 퀴즈

이 퀴즈는 Amazon EKS의 AI/ML 인프라 패턴에 대한 이해를 테스트합니다. JARK 스택, 동적 리소스 할당, AI 워크로드를 위한 프로덕션 플랫폼을 포함합니다.

## 퀴즈 문제

### 1. EKS의 AI/ML 인프라 맥락에서 JARK 스택은 무엇을 의미하나요?

A) Java, Ansible, Redis, Kafka
B) JupyterHub, Argo Workflows, Ray, Karpenter
C) Jenkins, Airflow, RabbitMQ, Kubernetes
D) JupyterLab, Apache Spark, Ray, Kubeflow

<details>
<summary>정답 보기</summary>

**정답: B) JupyterHub, Argo Workflows, Ray, Karpenter**

**설명:**
JARK 스택은 EKS에서 완전한 AI/ML 개발 환경을 구성하는 요소들입니다:

- **JupyterHub**: GPU 지원 노트북 프로필을 갖춘 다중 사용자 대화형 개발 환경
- **Argo Workflows**: DAG 기반 워크플로우를 통한 ML 파이프라인 오케스트레이션
- **Ray (KubeRay)**: 훈련, 튜닝, 서빙을 위한 통합 분산 컴퓨팅
- **Karpenter**: GPU 및 Neuron 지원이 포함된 빠르고 비용 효율적인 노드 프로비저닝

이 스택은 데이터 과학자와 ML 엔지니어가 Kubernetes에서 ML 모델을 개발, 훈련, 배포하는 데 필요한 모든 것을 제공합니다.

</details>

### 2. 엔터프라이즈 환경에서 EKS의 JupyterHub에 일반적으로 사용되는 인증 방법은 무엇인가요?

A) ConfigMap에 저장된 기본 사용자명/비밀번호
B) SSH 키 기반 인증
C) OAuth를 사용한 Amazon Cognito
D) Kubernetes ServiceAccount 토큰

<details>
<summary>정답 보기</summary>

**정답: C) OAuth를 사용한 Amazon Cognito**

**설명:**
엔터프라이즈 환경에서 EKS의 JupyterHub에는 OAuth를 사용한 Amazon Cognito가 권장되는 인증 방법입니다:

1. **Single Sign-On (SSO)**: 기업 ID 제공자와 통합 (SAML, OIDC)
2. **다중 인증(MFA)**: 향상된 보안을 위한 MFA 지원
3. **사용자 관리**: 중앙 집중식 사용자 관리 및 접근 제어
4. **확장성**: 사용자 기반에 따라 확장되는 관리형 서비스
5. **규정 준수**: 보안 규정 준수 요구사항 충족에 도움

구성 예시:
```python
c.JupyterHub.authenticator_class = 'oauthenticator.generic.GenericOAuthenticator'
c.GenericOAuthenticator.oauth_callback_url = 'https://jupyter.example.com/hub/oauth_callback'
c.GenericOAuthenticator.authorize_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize'
```

</details>

### 3. Kubernetes의 Ray에서 Ray 헤드 노드의 목적은 무엇인가요?

A) 모든 훈련 데이터와 모델 가중치를 저장
B) 클러스터를 조정하고, 대시보드를 실행하며, 워커 스케줄링을 관리
C) 모든 GPU 계산을 독점적으로 수행
D) 외부 API 요청만 처리

<details>
<summary>정답 보기</summary>

**정답: B) 클러스터를 조정하고, 대시보드를 실행하며, 워커 스케줄링을 관리**

**설명:**
Ray 헤드 노드는 Ray 클러스터의 중앙 코디네이터 역할을 합니다:

1. **글로벌 컨트롤 스토어(GCS)**: 클러스터 메타데이터 및 상태 관리
2. **대시보드**: 모니터링 및 디버깅을 위한 Ray 대시보드 실행 (포트 8265)
3. **클라이언트 연결**: Ray 클라이언트로부터의 연결 수락 (포트 10001)
4. **스케줄링**: 워커 간 태스크 및 액터 스케줄링 조정
5. **오토스케일링**: KubeRay 오토스케일러와 협력하여 워커 그룹 확장

헤드 노드는 일반적으로 컴퓨팅 집약적인 워크로드를 직접 실행하지 않습니다. 이러한 워크로드는 리소스 요구사항(CPU, GPU, 메모리)에 따라 워커 노드에 분산됩니다.

```yaml
headGroupSpec:
  rayStartParams:
    dashboard-host: '0.0.0.0'
    block: 'true'
```

</details>

### 4. GPU 스케줄링에서 기존 Kubernetes 디바이스 플러그인 대비 동적 리소스 할당(DRA)의 주요 장점은 무엇인가요?

A) DRA가 GPU 하드웨어를 더 빠르게 감지
B) DRA가 세밀한 GPU 공유(MIG, MPS, 타임슬라이싱)와 토폴로지 인식 스케줄링을 지원
C) DRA가 메모리 오버헤드가 더 적음
D) DRA가 NVIDIA GPU에서만 작동

<details>
<summary>정답 보기</summary>

**정답: B) DRA가 세밀한 GPU 공유(MIG, MPS, 타임슬라이싱)와 토폴로지 인식 스케줄링을 지원**

**설명:**
동적 리소스 할당(DRA)은 기존 디바이스 플러그인이 제공할 수 없는 기능을 제공합니다:

| 기능 | 기존 디바이스 플러그인 | DRA |
|-----|---------------------|-----|
| GPU 할당 | 전체 GPU만 | 부분 할당(MIG, MPS, 타임슬라이스) |
| 토폴로지 인식 | 제한적 | NVLink/IMEX 인식 |
| 공유 모드 | 기본 타임슬라이싱 | MIG, MPS, 타임슬라이싱, 독점 |
| 리소스 클레임 | 정적 | 제약 조건이 있는 동적 |
| 멀티 GPU 스케줄링 | 독립적 | 토폴로지 제약 |

DRA는 ResourceClaim과 ResourceSlice를 사용하여 제공합니다:
- 세밀한 GPU 메모리 파티셔닝 (3g.20gb 같은 MIG 프로필)
- MPS를 통한 CUDA 컨텍스트 공유
- 개발 워크로드를 위한 타임슬라이싱
- NVLink로 연결된 GPU의 토폴로지 인식 스케줄링

이는 72개의 상호 연결된 GPU를 가진 P6e-GB200 UltraServer에 필수적입니다.

</details>

### 5. 워크로드 간 가장 강력한 격리를 제공하는 GPU 공유 전략은 무엇인가요?

A) 타임슬라이싱
B) MPS (Multi-Process Service)
C) MIG (Multi-Instance GPU)
D) 독점 모드

<details>
<summary>정답 보기</summary>

**정답: C) MIG (Multi-Instance GPU)**

**설명:**
GPU 공유 전략 중 MIG는 공유를 허용하면서도 가장 강력한 격리를 제공합니다:

| 전략 | 격리 수준 | 작동 방식 |
|-----|---------|----------|
| **독점** | 완전(공유 없음) | GPU당 하나의 워크로드 |
| **MIG** | 강함(하드웨어) | 하드웨어로 파티션된 GPU 인스턴스 |
| **MPS** | 중간 | 스레드 제한이 있는 공유 CUDA 컨텍스트 |
| **타임슬라이싱** | 약함 | 워크로드 간 컨텍스트 스위칭 |

MIG(A100/H100 GPU에서 사용 가능)는 다음을 제공합니다:
- **하드웨어 격리**: 각 MIG 인스턴스는 전용 SM 유닛, 메모리, 캐시를 가짐
- **장애 격리**: 한 인스턴스의 오류가 다른 인스턴스에 영향을 주지 않음
- **QoS 보장**: 인스턴스당 예측 가능한 성능
- **메모리 보호**: 별도의 메모리 공간으로 데이터 유출 방지

A100 80GB용 MIG 프로필 예시:
- `7g.80gb` - 전체 GPU
- `3g.40gb` - GPU의 절반 (2개 인스턴스)
- `1g.10gb` - GPU의 1/7 (7개 인스턴스)

</details>

### 6. 완전한 DRA 지원에 필요한 최소 NVIDIA GPU Operator 버전은 무엇인가요?

A) v22.9.0
B) v23.6.0
C) v24.3.0
D) v25.3.0

<details>
<summary>정답 보기</summary>

**정답: D) v25.3.0**

**설명:**
완전한 동적 리소스 할당(DRA) 지원을 위해서는 NVIDIA GPU Operator v25.3.0 이상이 필요합니다. 이 버전에는 다음이 포함됩니다:

1. **DRA 드라이버**: GPU 리소스 관리를 위한 네이티브 DRA 드라이버
2. **ResourceSlice 지원**: GPU 토폴로지 정보 노출
3. **공유 구성**: DRA를 통한 MIG, MPS, 타임슬라이싱
4. **CEL 표현식**: Common Expression Language를 사용한 디바이스 선택

DRA가 활성화된 구성:
```yaml
draDriver:
  enabled: true
  version: "v0.1.0"
  config:
    sharing:
      mps:
        enabled: true
      timeSlicing:
        enabled: true
      mig:
        enabled: true
        strategy: mixed
```

이전 버전은 DRA가 제공하는 세밀한 제어 없이 기존 디바이스 플러그인 모드만 지원합니다.

</details>

### 7. EKS 기반 Agents 플랫폼에서 Langfuse의 목적은 무엇인가요?

A) 임베딩을 저장하는 벡터 데이터베이스
B) 소스 제어 및 CI/CD 파이프라인
C) LLM 관찰 가능성, 추적, 모니터링
D) 도구 검색 및 등록

<details>
<summary>정답 보기</summary>

**정답: C) LLM 관찰 가능성, 추적, 모니터링**

**설명:**
Langfuse는 다음을 제공하는 오픈소스 LLM 관찰 가능성 플랫폼입니다:

1. **추적**: LLM 상호작용의 엔드투엔드 추적
2. **프롬프트 관리**: 프롬프트 버전 관리
3. **평가**: LLM 출력 점수 및 평가
4. **분석**: 사용량 메트릭, 지연 시간, 비용 추적
5. **디버깅**: LLM 체인 및 에이전트의 문제 식별

EKS 기반 Agents 플랫폼 아키텍처에서:
- **GitLab**: 소스 제어 및 CI/CD
- **Langfuse**: LLM 관찰 가능성 및 추적
- **Milvus**: RAG용 벡터 데이터베이스
- **MCP Gateway**: 도구 검색 및 등록

통합 예시:
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-xxx",
    secret_key="sk-xxx",
    host="https://langfuse.agents.example.com"
)

# LLM 호출 추적
trace = langfuse.trace(name="customer-support-agent")
```

</details>

### 8. EKS에서 고처리량 분산 훈련 워크로드에 권장되는 스토리지 솔루션은 무엇인가요?

A) Amazon EBS gp3 볼륨
B) 표준 성능 모드의 Amazon EFS
C) Amazon FSx for Lustre
D) Mountpoint가 포함된 Amazon S3

<details>
<summary>정답 보기</summary>

**정답: C) Amazon FSx for Lustre**

**설명:**
Amazon FSx for Lustre는 고처리량 분산 훈련에 권장되는 스토리지 솔루션입니다:

1. **고처리량**: 스토리지 TiB당 최대 1000+ MB/s
2. **저지연**: 메타데이터 작업에 서브밀리초 지연
3. **S3 통합**: S3와의 네이티브 데이터 저장소 통합
4. **병렬 액세스**: 병렬 파일 시스템 워크로드에 최적화
5. **POSIX 준수**: ML 프레임워크를 위한 완전한 POSIX 지원

AI/ML용 스토리지 비교:

| 스토리지 | 처리량 | 사용 사례 |
|---------|-------|----------|
| EFS | 최대 10 GB/s | 공유 노트북, 모델 스토리지 |
| FSx Lustre | 최대 1+ TB/s | 분산 훈련, HPC |
| S3 + Mountpoint | 가변 | 콜드 데이터, 체크포인트 |
| EBS gp3 | 최대 1 GB/s | 단일 노드 워크로드 |

FSx for Lustre 구성:
```yaml
parameters:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: "500"  # TiB당 MB/s
  dataCompressionType: LZ4
  s3ImportPath: s3://ml-datasets
```

</details>

### 9. AI/ML 워크로드에서 EFA(Elastic Fabric Adapter)는 무엇에 사용되나요?

A) GPU 노드에서 저장 데이터 암호화
B) 멀티 노드 분산 훈련을 위한 고대역폭, 저지연 네트워킹
C) GPU 메모리 할당 관리
D) 외부 서비스에 워크로드 인증

<details>
<summary>정답 보기</summary>

**정답: B) 멀티 노드 분산 훈련을 위한 고대역폭, 저지연 네트워킹**

**설명:**
Elastic Fabric Adapter(EFA)는 HPC 및 ML 워크로드를 위한 AWS의 고성능 네트워크 인터페이스입니다:

1. **고대역폭**: 최대 3200 Gbps (16x EFA가 있는 trn1n.32xlarge)
2. **저지연**: 집합 연산을 위한 일관된 저지연
3. **OS 바이패스**: 커널을 우회하는 직접 하드웨어 액세스
4. **NCCL 통합**: NVIDIA Collective Communications Library에 최적화

AI/ML용 EFA 지원 인스턴스:
- `p4d.24xlarge`: 4x 400 Gbps EFA
- `p5.48xlarge`: 32x 400 Gbps EFA
- `trn1.32xlarge`: 8x 800 Gbps EFA
- `trn1n.32xlarge`: 16x 1600 Gbps EFA

NCCL과 함께 EFA를 사용하기 위한 환경 변수:
```yaml
env:
- name: FI_PROVIDER
  value: "efa"
- name: FI_EFA_USE_DEVICE_RDMA
  value: "1"
- name: NCCL_ALGO
  value: "Ring,Tree"
```

리소스 요청:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4
```

</details>

### 10. 즉각적인 주의가 필요한 GPU 메모리 고갈을 나타내는 Prometheus 메트릭은 무엇인가요?

A) DCGM_FI_DEV_GPU_UTIL > 80
B) DCGM_FI_DEV_GPU_TEMP > 70
C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95
D) DCGM_FI_DEV_SM_CLOCK < 1000

<details>
<summary>정답 보기</summary>

**정답: C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95**

**설명:**
이 메트릭은 GPU 프레임 버퍼(메모리) 사용률 백분율을 계산합니다. 95%를 초과하면 GPU의 메모리가 거의 소진된 것입니다:

GPU 모니터링을 위한 주요 DCGM 메트릭:

| 메트릭 | 설명 | 임계 임계값 |
|-------|-----|-----------|
| `DCGM_FI_DEV_FB_USED` | 사용된 프레임 버퍼 메모리 | - |
| `DCGM_FI_DEV_FB_FREE` | 사용 가능한 프레임 버퍼 메모리 | - |
| `DCGM_FI_DEV_GPU_UTIL` | GPU 컴퓨팅 활용률 | <20% (활용 부족) |
| `DCGM_FI_DEV_GPU_TEMP` | GPU 온도 | >85C (과열) |
| `DCGM_FI_DEV_XID_ERRORS` | 하드웨어 오류 수 | >0 (하드웨어 문제) |

메모리 고갈에 대한 알림 규칙:
```yaml
- alert: GPUMemoryExhausted
  expr: (DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100 > 95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "GPU 메모리 거의 소진"
```

메모리 고갈의 원인:
- OOM(Out of Memory) 오류
- 훈련 작업 실패
- 추론 요청 거부

</details>

### 11. GPU 워크로드에서 Karpenter의 통합(consolidation) 기능의 목적은 무엇인가요?

A) 여러 GPU를 단일 가상 GPU로 병합
B) 훈련 체크포인트를 단일 파일로 결합
C) 워크로드를 빈 패킹하고 활용도가 낮은 노드를 제거하여 비용 절감
D) 여러 GPU 파드의 로그를 통합

<details>
<summary>정답 보기</summary>

**정답: C) 워크로드를 빈 패킹하고 활용도가 낮은 노드를 제거하여 비용 절감**

**설명:**
Karpenter의 통합 기능은 다음을 통해 클러스터 비용을 최적화합니다:

1. **빈 패킹**: 워크로드를 더 적은 수의 더 활용도 높은 노드로 이동
2. **노드 제거**: 비어 있거나 활용도가 낮은 노드 종료
3. **적정 크기 조정**: 더 적절한 인스턴스 유형으로 노드 교체
4. **비용 절감**: 유휴 GPU 리소스 최소화

통합 정책:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

- **WhenEmpty**: 완전히 비어 있는 노드만 통합
- **WhenEmptyOrUnderutilized**: 비어 있거나 활용도가 낮은 노드 통합

GPU 워크로드에서 통합이 중요한 이유:
- GPU 인스턴스는 비용이 높음($3-30+/시간)
- 활용도가 낮은 GPU는 상당한 비용 낭비
- 훈련 작업이 종종 완료되어 유휴 노드가 남음

모범 사례:
- 개발 환경에서는 짧은 `consolidateAfter` 사용 (5분)
- 프로덕션 훈련에서는 긴 기간 사용 (30분)
- 과도한 스케일링을 방지하기 위해 적절한 `limits` 설정

</details>

### 12. DRA에서 ResourceSlice는 무엇에 사용되나요?

A) 컨테이너 간 CPU 리소스 분할
B) 노드의 사용 가능한 GPU 리소스와 토폴로지를 나타냄
C) 다양한 워크로드에 대한 네트워크 대역폭 분할
D) 스토리지 볼륨 파티셔닝

<details>
<summary>정답 보기</summary>

**정답: B) 노드의 사용 가능한 GPU 리소스와 토폴로지를 나타냄**

**설명:**
ResourceSlice는 사용 가능한 디바이스와 토폴로지를 나타내는 DRA 리소스입니다:

```yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceSlice
metadata:
  name: gb200-nvl72-node-1
spec:
  nodeName: p6e-gb200-node-1
  pool:
    name: gb200-pool
    generation: 1
    resourceSliceCount: 1
  driver: gpu.nvidia.com
  devices:
  - name: gpu-0
    basic:
      attributes:
        gpu.nvidia.com/product: "NVIDIA-GB200"
        gpu.nvidia.com/memory: "192Gi"
        gpu.nvidia.com/nvlink.version: "5.0"
        gpu.nvidia.com/nvswitch.connected: "true"
```

ResourceSlice가 제공하는 것:
1. **디바이스 인벤토리**: 노드의 모든 사용 가능한 디바이스 나열
2. **속성**: GPU 모델, 메모리, 기능
3. **토폴로지 정보**: NVLink 연결, NUMA 노드, NVSwitch
4. **용량**: 스케줄링에 사용 가능한 리소스

스케줄러는 ResourceSlice를 사용하여:
- 필요한 GPU 유형이 있는 노드 찾기
- 토폴로지 인식 멀티 GPU 워크로드 스케줄링
- NVLink로 연결된 GPU가 함께 할당되도록 보장

</details>

### 13. EKS 기반 Agents 플랫폼에서 RAG(Retrieval-Augmented Generation)를 위한 벡터 스토리지를 제공하는 구성 요소는 무엇인가요?

A) GitLab
B) Langfuse
C) Milvus
D) MCP Gateway

<details>
<summary>정답 보기</summary>

**정답: C) Milvus**

**설명:**
Milvus는 AI 애플리케이션에 최적화된 오픈소스 벡터 데이터베이스입니다:

1. **벡터 스토리지**: 고차원 임베딩 벡터 저장
2. **유사도 검색**: 빠른 근사 최근접 이웃(ANN) 검색
3. **GPU 가속**: 쿼리 및 인덱스 노드가 GPU 사용 가능
4. **확장성**: 대규모 배포를 위한 분산 아키텍처

Milvus를 사용한 RAG 아키텍처:
```
사용자 쿼리 → 임베딩 모델 → Milvus (벡터 검색) → 검색된 컨텍스트 → LLM → 응답
```

EKS에서 Milvus 구성:
```yaml
queryNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU 가속 검색

indexNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU 가속 인덱싱
```

에이전트 통합:
```python
from pymilvus import connections, Collection

connections.connect(host="milvus.milvus.svc.cluster.local", port="19530")
collection = Collection("knowledge_base")

# 유사 문서 검색
results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param={"metric_type": "IP", "params": {"nprobe": 10}},
    limit=5
)
```

</details>

### 14. 분산 훈련 중 GPU 노드 장애를 처리하는 데 권장되는 접근 방식은 무엇인가요?

A) 처음부터 수동으로 훈련 재시작
B) Ray Train과 같은 장애 허용 훈련 프레임워크와 함께 체크포인팅 사용
C) 장애를 방지하기 위해 GPU 레플리카 수 증가
D) 중단을 피하기 위해 온디맨드 인스턴스만 사용

<details>
<summary>정답 보기</summary>

**정답: B) Ray Train과 같은 장애 허용 훈련 프레임워크와 함께 체크포인팅 사용**

**설명:**
장애 허용 프레임워크와 함께 체크포인팅을 사용하는 것이 권장되는 이유:

1. **자동 복구**: 마지막 체크포인트에서 훈련 재개
2. **비용 효율성**: 더 저렴한 스팟 인스턴스 사용 가능
3. **확장성**: 동적 클러스터 크기 변경 처리
4. **진행 상황 보존**: 손실된 컴퓨팅 시간 최소화

체크포인팅이 있는 Ray Train:
```python
from ray.train.torch import TorchTrainer
from ray.train import Checkpoint, ScalingConfig

def train_loop_per_worker():
    # 사용 가능한 경우 체크포인트에서 로드
    checkpoint = ray.train.get_checkpoint()
    if checkpoint:
        with checkpoint.as_directory() as checkpoint_dir:
            model.load_state_dict(torch.load(f"{checkpoint_dir}/model.pt"))

    for epoch in range(epochs):
        # 훈련 로직
        train_epoch()

        # 체크포인트 저장
        with tempfile.TemporaryDirectory() as temp_dir:
            torch.save(model.state_dict(), f"{temp_dir}/model.pt")
            ray.train.report(
                {"loss": loss},
                checkpoint=Checkpoint.from_directory(temp_dir)
            )

trainer = TorchTrainer(
    train_loop_per_worker,
    scaling_config=ScalingConfig(
        num_workers=4,
        use_gpu=True,
    ),
    run_config=ray.train.RunConfig(
        checkpoint_config=ray.train.CheckpointConfig(
            num_to_keep=3,
            checkpoint_frequency=10,
        )
    )
)
```

</details>

### 15. EKS 기반 Agents 플랫폼에서 MCP Gateway의 목적은 무엇인가요?

A) 마이크로서비스 간 트래픽 라우팅
B) 컨테이너 이미지 레지스트리 관리
C) AI 에이전트를 위한 도구 검색 및 등록 제공
D) 파드 간 통신 암호화

<details>
<summary>정답 보기</summary>

**정답: C) AI 에이전트를 위한 도구 검색 및 등록 제공**

**설명:**
MCP(Model Context Protocol) Gateway는 AI 에이전트를 위한 도구 검색 및 관리를 제공합니다:

1. **도구 레지스트리**: 사용 가능한 도구/함수의 중앙 레지스트리
2. **검색**: Kubernetes에서 도구 자동 검색
3. **라우팅**: 적절한 백엔드로 도구 호출 라우팅
4. **인증**: OIDC 기반 접근 제어
5. **속도 제한**: 도구 남용 방지

MCP Gateway 구성:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-gateway-config
data:
  config.yaml: |
    registry:
      type: kubernetes
      kubernetes:
        namespace: mcp-tools
        label_selector: "mcp.anthropic.com/tool=true"

    discovery:
      enabled: true
      interval: 30s
      endpoints:
      - name: kubernetes
        type: kubernetes
        config:
          namespaces: ["mcp-tools", "ai-agents"]
```

에이전트 통합:
```python
# 에이전트가 MCP Gateway를 통해 도구를 검색하고 사용
env:
- name: MCP_GATEWAY_URL
  value: "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"
```

MCP를 통해 에이전트가 수행할 수 있는 작업:
- 사용 가능한 도구를 동적으로 검색
- 외부 API 및 서비스 호출
- 데이터베이스 및 파일 시스템 액세스
- 코드 및 명령 실행

</details>

---

## 요약

이 퀴즈는 EKS의 AI 인프라에 대한 핵심 개념을 다루었습니다:

- **JARK 스택**: 완전한 ML 환경을 위한 JupyterHub + Argo Workflows + Ray + Karpenter
- **동적 리소스 할당**: MIG, MPS, 타임슬라이싱을 통한 세밀한 GPU 스케줄링
- **Agents 플랫폼**: AI 에이전트 개발을 위한 GitLab + Langfuse + Milvus + MCP Gateway
- **스토리지**: 공유를 위한 EFS, 고처리량 훈련을 위한 FSx Lustre
- **네트워킹**: 멀티 노드 분산 훈련을 위한 EFA
- **모니터링**: GPU 관찰 가능성을 위한 DCGM 메트릭 및 Prometheus 알림

자세한 내용은 [EKS 기반 AI 인프라](../../ai-ml/06-ai-infrastructure.md) 문서를 참조하세요.
