# AI/ML 모범 사례 퀴즈

이 퀴즈는 벤치마킹, 컨테이너 최적화, GPU 선택, 네트워킹, 스토리지, 관측성, 비용 최적화를 포함한 Amazon EKS의 AI/ML 모범 사례에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. LLM 추론 벤치마킹에서 TTFT(Time to First Token)는 무엇을 측정하나요?

A) 응답의 모든 토큰을 생성하는 데 걸리는 총 시간
B) 요청 제출부터 첫 번째 토큰이 생성될 때까지의 시간
C) 연속 토큰 간의 평균 시간
D) 초당 생성되는 토큰 수

<details>
<summary>정답 보기</summary>

**정답: B) 요청 제출부터 첫 번째 토큰이 생성될 때까지의 시간**

**설명:**
TTFT(Time to First Token)는 요청이 제출된 시점부터 응답의 첫 번째 토큰이 생성될 때까지의 지연 시간을 측정합니다. 이 지표는 사용자가 응답의 시작을 얼마나 빨리 볼 수 있는지를 결정하므로 사용자 경험에 매우 중요합니다.

공식: `TTFT = t_first_token - t_request`

TTFT에 대한 주요 사항:
- 애플리케이션의 인지된 응답성에 직접적인 영향
- 대화형 애플리케이션의 경우 < 500ms 권장
- 모델 로딩, 프롬프트 처리(프리필), 대기열 깊이에 영향받음
- 높은 TTFT는 GPU 메모리, 배치 크기 또는 시스템 부하에 잠재적 문제가 있음을 나타냄

기타 지표:
- ITL(Inter-Token Latency): 연속 토큰 간 시간
- TPS(Tokens Per Second): 생성 속도
- E2E Latency: 요청부터 완료까지의 총 시간

</details>

### 2. 콜드 스타트 시간을 가장 많이 줄이는 컨테이너 시작 최적화 기법은 무엇인가요?

A) 멀티 스테이지 Docker 빌드만
B) 모델 아티팩트 분리만
C) 통합 접근 방식(분리 + 멀티 스테이지 + 프리페칭 + SOCI)
D) 더 작은 기본 이미지 사용만

<details>
<summary>정답 보기</summary>

**정답: C) 통합 접근 방식(분리 + 멀티 스테이지 + 프리페칭 + SOCI)**

**설명:**
통합 접근 방식은 단순한 구현에 비해 80-95%의 개선을 달성하여 콜드 스타트 시간을 가장 많이 줄입니다.

콜드 스타트 최적화 비교:

| 기법 | 시작 시간 단축 |
|------|----------------|
| 모델 분리 | 50-70% |
| 멀티 스테이지 빌드 | 30-50% |
| SOCI snapshotter | 60-80% |
| 이미지 프리페칭 | 70-90% |
| **통합 접근 방식** | **80-95%** |

통합 접근 방식의 작동 원리:
1. **모델 분리**: 컨테이너 이미지에서 대용량 모델 가중치 분리
2. **멀티 스테이지 빌드**: 빌드 의존성을 제외하여 이미지 크기 축소
3. **SOCI snapshotter**: 전체 이미지 다운로드 전에 컨테이너 시작이 가능한 지연 풀링 활성화
4. **이미지 프리페칭**: 노드 부트스트랩 중 이미지 사전 풀

10-50GB에 달할 수 있는 AI/ML 이미지의 경우, 이 조합으로 시작 시간을 5-15분에서 1분 미만으로 줄일 수 있습니다.

</details>

### 3. 고대역폭 노드 간 통신이 필요한 대규모 분산 훈련에 가장 적합한 GPU 인스턴스 패밀리는 무엇인가요?

A) G5 (NVIDIA A10G)
B) G6 (NVIDIA L4)
C) P5 (NVIDIA H100)
D) Inf2 (AWS Inferentia2)

<details>
<summary>정답 보기</summary>

**정답: C) P5 (NVIDIA H100)**

**설명:**
NVIDIA H100 GPU가 장착된 P5 인스턴스는 다음을 제공하므로 대규모 분산 훈련에 가장 적합합니다:

- **8x NVIDIA H100 GPU**, 각각 80GB HBM3 메모리
- **3200 Gbps EFA 네트워킹** - 분산 훈련에 필수
- **NVLink 4.0**: 노드 내 GPU 간 고대역폭 통신
- **192 vCPU 및 2048GB 메모리**: 데이터 전처리용

분산 훈련 비교:

| 인스턴스 | GPU | GPU 메모리 | 네트워크 | 훈련 적합성 |
|----------|-----|------------|----------|-------------|
| G5 | 1-8 A10G | 24GB | 100 Gbps | 소/중형 모델 |
| G6 | 1-8 L4 | 24GB | 100 Gbps | 추론 중심 |
| P4d | 8 A100 | 40-80GB | 400 Gbps EFA | 대규모 훈련 |
| **P5** | **8 H100** | **80GB** | **3200 Gbps EFA** | **최첨단 모델** |
| Inf2 | 1-12 Inferentia2 | 32GB | 100 Gbps | 추론 전용 |

P5의 3200 Gbps EFA 대역폭은 P4d의 8배로, 노드 간 그래디언트 동기화가 병목인 훈련 작업에 이상적입니다.

</details>

### 4. 분산 AI/ML 훈련에서 EFA(Elastic Fabric Adapter)의 주요 목적은 무엇인가요?

A) GPU 메모리 용량 증가
B) 저지연, 고대역폭 노드 간 통신 제공
C) GPU 시간 공유 활성화
D) 모델 추론 가속화

<details>
<summary>정답 보기</summary>

**정답: B) 저지연, 고대역폭 노드 간 통신 제공**

**설명:**
EFA(Elastic Fabric Adapter)는 고성능 컴퓨팅(HPC) 및 머신러닝 애플리케이션이 온프레미스 HPC 클러스터의 노드 간 통신 성능을 달성할 수 있게 해주는 Amazon EC2 인스턴스용 네트워크 인터페이스입니다.

분산 훈련을 위한 EFA의 주요 이점:
1. **OS 우회 기능**: 애플리케이션이 네트워크 어댑터와 직접 통신하여 지연 시간 감소
2. **고대역폭**: P5 인스턴스에서 최대 3200 Gbps
3. **저지연**: 집합 연산에 대해 마이크로초 미만의 지연 시간
4. **NCCL 최적화**: AWS OFI NCCL 플러그인과 함께 작동하여 최적화된 GPU 간 통신

EFA 구성 요구 사항:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # EFA 장치 요청
```

EFA를 위한 NCCL 환경 변수:
```bash
export FI_PROVIDER=efa
export FI_EFA_USE_DEVICE_RDMA=1
export NCCL_ALGO=Ring,Tree
```

EFA가 필수인 경우:
- PyTorch DDP, Horovod와 같은 프레임워크를 사용한 멀티 노드 분산 훈련
- 텐서/파이프라인 병렬화를 사용한 대규모 모델 훈련
- 그래디언트 동기화가 병목인 모든 워크로드

</details>

### 5. AI/ML 워크로드에서 EFS 대신 FSx for Lustre를 사용해야 하는 경우는 언제인가요?

A) 여러 파드에서 공유 액세스가 필요할 때
B) 훈련 데이터셋이 10TB를 초과하고 높은 처리량이 필요할 때
C) 모델 체크포인트를 임시로 저장할 때
D) 소형 모델로 추론 워크로드를 실행할 때

<details>
<summary>정답 보기</summary>

**정답: B) 훈련 데이터셋이 10TB를 초과하고 높은 처리량이 필요할 때**

**설명:**
FSx for Lustre는 높은 처리량이 필요한 대규모 훈련 데이터셋(>10TB)에 최적의 선택이며, EFS는 더 작은 데이터셋과 공유 모델 저장에 더 적합합니다.

스토리지 선택 가이드:

| 사용 사례 | 권장 스토리지 | 이유 |
|----------|---------------|------|
| 훈련 데이터셋 <500GB | EBS gp3 | 단일 노드, 비용 효율적 |
| 훈련 데이터셋 500GB-10TB | EFS | 멀티 노드 읽기, 적당한 처리량 |
| **훈련 데이터셋 >10TB** | **FSx Lustre** | **병렬 파일시스템, TB/s 처리량** |
| 공유 모델 가중치 | EFS | ReadWriteMany, 캐싱 |
| 임시 체크포인트 | 인스턴스 스토어 | 최저 지연 시간, 임시 |
| 장기 모델 저장 | S3 | 비용 효율적, 내구성 |

FSx for Lustre 장점:
- 처리량 최대 1+ TB/s (EFS의 ~1-3 GB/s 대비)
- 밀리초 미만의 지연 시간
- `s3ImportPath`를 통한 직접 S3 통합
- HPC 워크로드용으로 설계된 병렬 파일시스템

```yaml
# 대규모 데이터셋용 FSx Lustre
storageClassName: fsx-lustre-sc
parameters:
  perUnitStorageThroughput: "250"  # TiB당 MB/s
  s3ImportPath: s3://training-data  # 투명한 S3 액세스
```

</details>

### 6. GPU 열 스로틀링을 감지하기 위해 모니터링해야 하는 DCGM 지표는 무엇인가요?

A) DCGM_FI_DEV_GPU_UTIL
B) DCGM_FI_DEV_FB_USED
C) DCGM_FI_DEV_GPU_TEMP
D) DCGM_FI_DEV_XID_ERRORS

<details>
<summary>정답 보기</summary>

**정답: C) DCGM_FI_DEV_GPU_TEMP**

**설명:**
DCGM_FI_DEV_GPU_TEMP는 GPU 온도를 섭씨로 모니터링하며, 열 스로틀링 조건을 감지하기 위한 주요 지표입니다.

주요 GPU 지표와 그 목적:

| 지표 | 목적 | 알림 임계값 |
|------|------|-------------|
| **DCGM_FI_DEV_GPU_TEMP** | **열 모니터링** | **>80C 경고, >90C 심각** |
| DCGM_FI_DEV_GPU_UTIL | 컴퓨팅 사용률 | >95% 지속 |
| DCGM_FI_DEV_FB_USED | 메모리 사용량 | >전체의 95% |
| DCGM_FI_DEV_SM_CLOCK | 클럭 주파수(스로틀링 감지) | 기준선 미만 |
| DCGM_FI_DEV_POWER_USAGE | 전력 소비 | TDP 한계 근접 |
| DCGM_FI_DEV_XID_ERRORS | 하드웨어 오류 | 모든 증가 |

열 스로틀링 감지:
```yaml
# 열 문제에 대한 알림 규칙
- alert: GPUHighTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 80
  for: 5m
  labels:
    severity: warning

- alert: GPUCriticalTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 90
  for: 1m
  labels:
    severity: critical
```

온도가 임계값을 초과하면 GPU가 자동으로 클럭 속도를 낮추어(열 스로틀링) 훈련 및 추론 성능에 영향을 미칩니다.

</details>

### 7. GPU 추론 워크로드에 스팟 인스턴스를 사용하는 권장 접근 방식은 무엇인가요?

A) 추론에 스팟 인스턴스를 절대 사용하지 않음
B) 훈련에만 스팟 사용, 추론에는 온디맨드
C) 우아한 종료 처리 및 토폴로지 분산과 함께 스팟 사용
D) 특별한 구성 없이 스팟 사용

<details>
<summary>정답 보기</summary>

**정답: C) 우아한 종료 처리 및 토폴로지 분산과 함께 스팟 사용**

**설명:**
스팟 인스턴스는 우아한 종료 처리 및 가용성 고려 사항과 함께 적절하게 구성되면 상태 비저장 추론 워크로드에 60-90%의 비용 절감을 제공할 수 있습니다.

스팟 추론을 위한 모범 사례:

1. **우아한 종료 처리**:
```yaml
spec:
  terminationGracePeriodSeconds: 120
  containers:
  - lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "curl -X POST localhost:8000/drain; sleep 30"]
```

2. **가용성을 위한 토폴로지 분산**:
```yaml
topologySpreadConstraints:
- maxSkew: 2
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
```

3. **혼합 용량 유형**:
```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
    - weight: 50
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

스팟이 추론에 적합한 이유:
- 추론 파드는 일반적으로 상태 비저장
- 여러 레플리카가 중복성 제공
- 2분 인터럽션 경고로 우아한 드레인 가능

</details>

### 8. Inter-Token Latency(ITL)를 계산하는 공식은 무엇인가요?

A) `t_last_token - t_request`
B) `(t_last_token - t_first_token) / (n_tokens - 1)`
C) `n_tokens / total_generation_time`
D) `t_first_token - t_request`

<details>
<summary>정답 보기</summary>

**정답: B) `(t_last_token - t_first_token) / (n_tokens - 1)`**

**설명:**
Inter-Token Latency(ITL)는 생성 중 연속 토큰 간의 평균 시간을 측정합니다. 공식은:

`ITL = (t_last_token - t_first_token) / (n_tokens - 1)`

여기서:
- `t_last_token`: 마지막 토큰이 생성된 타임스탬프
- `t_first_token`: 첫 번째 토큰이 생성된 타임스탬프
- `n_tokens`: 생성된 총 토큰 수
- 토큰 간 간격을 측정하므로 `(n_tokens - 1)`로 나눔

ITL의 중요성:
- 채팅 애플리케이션의 스트리밍 품질 결정
- 목표: 부드러운 사용자 경험을 위해 < 50ms
- 높은 ITL은 GPU 메모리 압력 또는 컴퓨팅 병목 표시

기타 지표 공식:
- **TTFT**: `t_first_token - t_request` (첫 토큰까지의 시간)
- **TPS**: `n_tokens / total_generation_time` (초당 토큰 수)
- **E2E Latency**: `t_complete - t_request` (종단간)

계산 예시:
- 첫 토큰 500ms, 마지막 토큰 2500ms, 50개 토큰 생성
- ITL = (2500 - 500) / (50 - 1) = 2000 / 49 = ~41ms

</details>

### 9. LLM 추론 서비스의 최대 처리량을 찾기 위해 가장 적합한 테스트 시나리오는 무엇인가요?

A) 기준선 테스트
B) 포화 테스트
C) 실제 데이터셋 테스트
D) 긴 컨텍스트 테스트

<details>
<summary>정답 보기</summary>

**정답: B) 포화 테스트**

**설명:**
포화 테스트는 지연 시간이 저하될 때까지 동시성을 점진적으로 증가시켜 최대 처리량을 찾도록 특별히 설계되었으며, 시스템의 용량 한계를 드러냅니다.

테스트 시나리오 비교:

| 시나리오 | 목적 | 구성 |
|----------|------|------|
| 기준선 | 단일 요청 성능 확립 | 동시성=1, 100 요청 |
| **포화** | **처리량 한계 찾기** | **동시성=[1,5,10,20,50,100]** |
| 프로덕션 | 실제 성능 검증 | 가변 프롬프트, 현실적 부하 |
| 실제 데이터셋 | 실제 데이터 패턴 테스트 | ShareGPT 또는 도메인 데이터 |
| 긴 컨텍스트 | 컨텍스트 윈도우 처리 테스트 | 4K-128K 토큰 프롬프트 |

포화 테스트 구성:
```yaml
saturation:
  description: "최대 처리량 찾기"
  concurrency: [1, 5, 10, 20, 50, 100]  # 점진적 증가
  num_requests: 500
  prompt_length: 256
  max_tokens: 512
```

포화 테스트가 보여주는 것:
- 처리량 vs 지연 시간 곡선
- 지연 시간이 저하되기 시작하는 지점
- 시스템이 GPU 바운드인지, 메모리 바운드인지, CPU 바운드인지
- 최적의 운영 동시성 수준

목표는 처리량이 안정되고 지연 시간이 허용 가능한 상태를 유지하는 곡선의 "무릎"을 찾는 것입니다.

</details>

### 10. AI/ML 컨테이너를 위한 SOCI(Seekable OCI) snapshotter의 목적은 무엇인가요?

A) 컨테이너 이미지 압축
B) 전체 이미지 다운로드 전에 컨테이너 시작이 가능한 지연 풀링 활성화
C) 컨테이너 이미지 암호화
D) 노드 간 이미지 공유

<details>
<summary>정답 보기</summary>

**정답: B) 전체 이미지 다운로드 전에 컨테이너 시작이 가능한 지연 풀링 활성화**

**설명:**
SOCI(Seekable OCI) snapshotter는 컨테이너 이미지의 지연 로딩을 활성화하여 전체 이미지가 다운로드되기 전에 컨테이너가 시작할 수 있게 합니다. 이는 대규모 AI/ML 이미지(10-50GB)에 특히 유용합니다.

SOCI 작동 방식:
1. 컨테이너 이미지 레이어의 인덱스 생성
2. 초기에 메타데이터와 필수 레이어만 다운로드
3. 애플리케이션이 파일에 액세스할 때 나머지 레이어를 온디맨드로 가져옴
4. 이미지의 ~10-20%만 다운로드된 상태에서 컨테이너 시작 가능

AI/ML을 위한 이점:
- 컨테이너 시작 시간 60-80% 단축
- 드물게 액세스되는 대용량 레이어가 있는 이미지에 특히 효과적
- 모델 가중치가 컨테이너 시작 후 액세스될 때 가장 잘 작동

SOCI 설정:
```bash
# 이미지에 대한 SOCI 인덱스 생성
soci create \
  --ref public.ecr.aws/myrepo/vllm:latest \
  --platform linux/amd64

# 레지스트리에 인덱스 푸시
soci push \
  --ref public.ecr.aws/myrepo/vllm:latest
```

다른 최적화와 결합:
- 모델 분리 (50-70%)
- 멀티 스테이지 빌드 (30-50%)
- SOCI snapshotter (60-80%)
- 이미지 프리페칭 (70-90%)

SOCI는 컨테이너 런타임이 이를 지원하고(SOCI 플러그인이 있는 containerd) 이미지가 호환 가능한 레지스트리(Amazon ECR)에 저장될 때 가장 효과적입니다.

</details>

### 11. 업무 시간 동안 노드 중단을 방지하는 Karpenter 통합 정책 설정은 무엇인가요?

A) consolidationPolicy: WhenEmpty
B) consolidateAfter: 0
C) schedule과 nodes: "0"이 있는 budgets
D) weight: 0

<details>
<summary>정답 보기</summary>

**정답: C) schedule과 nodes: "0"이 있는 budgets**

**설명:**
Karpenter의 disruption budgets에서 schedule과 `nodes: "0"`은 지정된 시간 창(일반적으로 업무 시간) 동안 노드 통합을 방지합니다.

구성 예시:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m

  budgets:
  # 업무 시간 동안 통합 없음
  - nodes: "0"
    schedule: "0 9-17 * * 1-5"  # 오전 9시~오후 5시, 월-금
    duration: 8h

  # 비피크 시간에 30% 통합 허용
  - nodes: "30%"
```

Budget 파라미터:
- `nodes`: 중단될 수 있는 최대 노드 수/비율
- `schedule`: budget이 적용되는 시점의 cron 표현식
- `duration`: schedule이 트리거된 후 budget이 활성화되는 시간

AI/ML에서 중요한 이유:
- GPU 노드는 비싸고 중단 시 콜드 스타트 발생
- 노드 교체 중 추론 지연 시간 급증
- 체크포인트가 자주 이루어지지 않으면 훈련 작업의 진행 상황 손실 가능
- 업무 시간에 일반적으로 트래픽이 가장 높음

기타 통합 설정:
- `consolidationPolicy: WhenEmpty`: 완전히 비어 있는 노드만 통합
- `consolidationPolicy: WhenEmptyOrUnderutilized`: 미활용 노드도 통합
- `consolidateAfter`: 통합 전 지연 시간(예: 5m)

</details>

### 12. Kubernetes에서 HuggingFace 및 NGC API 키를 관리하는 권장 방법은 무엇인가요?

A) Dockerfile에 하드코딩
B) 파드 스펙에 환경 변수로 전달
C) AWS Secrets Manager와 함께 External Secrets Operator 사용
D) ConfigMap에 저장

<details>
<summary>정답 보기</summary>

**정답: C) AWS Secrets Manager와 함께 External Secrets Operator 사용**

**설명:**
External Secrets Operator(ESO)와 AWS Secrets Manager는 자동 로테이션 및 감사 기능과 함께 안전하고 중앙 집중화된 시크릿 관리를 제공합니다.

ESO가 권장되는 이유:
1. **중앙 집중 관리**: 시크릿이 AWS Secrets Manager에 저장됨
2. **자동 동기화**: ESO가 자동으로 Kubernetes 시크릿 업데이트
3. **로테이션 지원**: 파드 재배포 없이 시크릿 로테이션 가능
4. **감사 추적**: AWS CloudTrail이 모든 시크릿 액세스 기록
5. **IAM 통합**: IRSA를 통한 세밀한 액세스 제어

구성 예시:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: model-registry-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: model-registry-credentials
  data:
  - secretKey: HUGGING_FACE_HUB_TOKEN
    remoteRef:
      key: ai-ml/huggingface-token
      property: token
  - secretKey: NGC_API_KEY
    remoteRef:
      key: ai-ml/ngc-api-key
      property: key
```

다른 옵션의 문제점:
- **Dockerfile에 하드코딩**: 이미지 레이어에 시크릿 노출
- **파드 스펙의 환경 변수**: kubectl describe에서 보임
- **ConfigMap**: 암호화되지 않음, 읽기 권한이 있는 누구에게나 보임

보안 모범 사례:
- 서비스 계정 인증에 IRSA 사용
- Secrets Manager에서 저장 시 암호화 활성화
- 최소 권한 액세스 정책 구현
- 정기적으로 시크릿 로테이션

</details>

### 13. 중간 예산으로 30B 파라미터 모델 추론 워크로드에 가장 적합한 GPU 인스턴스 유형은 무엇인가요?

A) g5.xlarge (1x A10G, 24GB)
B) g5.4xlarge (1x A10G, 24GB)
C) g5.12xlarge (4x A10G, 총 96GB)
D) p4d.24xlarge (8x A100, 총 640GB)

<details>
<summary>정답 보기</summary>

**정답: C) g5.12xlarge (4x A10G, 총 96GB)**

**설명:**
30B 파라미터 모델은 FP16 추론에 약 60GB의 GPU 메모리가 필요하므로(파라미터당 2바이트), 4x A10G GPU(총 96GB)를 갖춘 g5.12xlarge가 중간 예산에 적절한 선택입니다.

메모리 계산:
- 30B 파라미터 x 2바이트(FP16) = 최소 60GB
- KV 캐시 오버헤드 포함: ~70-80GB 권장
- g5.12xlarge: 4 x 24GB = 96GB (마진과 함께 충분)

인스턴스 선택 가이드:

| 모델 크기 | 필요한 메모리 | 권장 인스턴스 | 예산 |
|-----------|---------------|---------------|------|
| <7B | 14GB | g5.xlarge | 낮음 |
| 7-13B | 26GB | g5.2xlarge | 낮음-중간 |
| 13-30B | 60GB | g5.4xlarge(양자화) 또는 g5.12xlarge | 중간 |
| **30B** | **60GB** | **g5.12xlarge (4x A10G)** | **중간** |
| 30-70B | 140GB | g5.12xlarge + 텐서 병렬 | 중간-높음 |
| >70B | 280GB+ | p4d.24xlarge | 높음 |

30B에 g5.12xlarge인 이유:
- 4-way 텐서 병렬화로 모델을 GPU에 분산
- 각 GPU가 ~15GB의 모델 가중치 보유
- 나머지 메모리는 KV 캐시용으로 사용 가능
- 추론에 P4d보다 비용 효율적

P4d.24xlarge는 작동하지만 30B 추론에는 과잉이며 훨씬 더 비쌉니다.

</details>

### 14. 메모리 압력으로 인해 시스템이 요청을 거부하기 시작할 수 있음을 나타내는 vLLM 지표는 무엇인가요?

A) vllm:num_requests_running
B) vllm:time_to_first_token_seconds
C) vllm:gpu_cache_usage_perc
D) vllm:request_success_total

<details>
<summary>정답 보기</summary>

**정답: C) vllm:gpu_cache_usage_perc**

**설명:**
`vllm:gpu_cache_usage_perc`는 KV(Key-Value) 캐시 사용률을 측정합니다. 이 지표가 100%에 가까워지면 어텐션 상태를 저장할 메모리가 없어 vLLM이 새 요청을 수락할 수 없습니다.

KV 캐시의 중요성:
- 각 토큰에 대해 계산된 어텐션 키와 값을 저장
- 시퀀스 길이와 배치 크기에 따라 증가
- 가득 차면 vLLM은 실행 중인 요청을 선점하거나 새 요청을 거부해야 함

알림 구성:
```yaml
- alert: vLLMKVCacheFull
  expr: vllm:gpu_cache_usage_perc > 0.95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "vLLM KV 캐시가 거의 가득 참"
    description: "KV 캐시 사용량이 95% 이상, 요청이 거부될 수 있음"
```

KV 캐시가 가득 찼을 때 해야 할 일:
1. `--max-num-seqs` 줄이기(동시 시퀀스)
2. `--max-model-len` 줄이기(최대 시퀀스 길이)
3. 청크 프리필 활성화
4. 수평 확장(레플리카 추가)
5. 더 큰 GPU 인스턴스 사용

기타 vLLM 지표:
- `vllm:num_requests_running`: 현재 동시 요청
- `vllm:num_requests_waiting`: 대기열 깊이
- `vllm:time_to_first_token_seconds`: TTFT 지연 시간
- `vllm:gpu_prefix_cache_hit_rate`: 캐싱 효율성

</details>

### 15. 분산 훈련을 위해 클러스터 전략의 배치 그룹을 사용하는 주요 이점은 무엇인가요?

A) EC2 인스턴스 비용 절감
B) 자동 로드 밸런싱
C) 노드 간 최저 네트워크 지연 시간
D) GPU 메모리 증가

<details>
<summary>정답 보기</summary>

**정답: C) 노드 간 최저 네트워크 지연 시간**

**설명:**
클러스터 배치 그룹은 인스턴스를 단일 가용 영역 내에서 물리적으로 가깝게 배치하여 노드 간 통신의 네트워크 지연 시간을 최소화하고 대역폭을 최대화합니다.

클러스터 배치 그룹의 이점:
1. **최저 지연 시간**: 동일한 네트워크 스파인에 있는 인스턴스
2. **최대 대역폭**: 전체 이등분 대역폭 사용 가능
3. **일관된 성능**: 네트워크 지터 감소
4. **EFA 최적화**: 최상의 EFA 성능을 위해 클러스터 배치 필요

구성:
```bash
# 클러스터 배치 그룹 생성
aws ec2 create-placement-group \
  --group-name training-cluster-pg \
  --strategy cluster

# Karpenter 구성
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
spec:
  tags:
    aws:ec2:placement-group: training-cluster-pg
```

배치 그룹 전략:

| 전략 | 사용 사례 | 지연 시간 | 가용성 |
|------|----------|----------|--------|
| **클러스터** | **분산 훈련** | **최저** | **단일 AZ** |
| 분산 | 고가용성 | 더 높음 | 멀티 AZ |
| 파티션 | 대규모 배포 | 중간 | 멀티 랙 |

훈련에 클러스터 전략인 이유:
- NCCL all-reduce 연산은 지연 시간에 민감
- 그래디언트 동기화가 자주 발생(매 배치마다)
- 작은 지연 시간 증가도 수천 번의 반복에 걸쳐 누적됨
- P4d/P5 인스턴스는 클러스터 배치에서 최상의 EFA 성능 달성

트레이드오프: 클러스터 배치 그룹은 단일 AZ로 제한되어 가용성이 감소합니다. 훈련의 경우 다음 이유로 허용됩니다:
- 훈련 작업은 체크포인트를 만들고 재시작할 수 있음
- 낮은 지연 시간이 중복성보다 훈련 시간을 더 많이 개선

</details>
