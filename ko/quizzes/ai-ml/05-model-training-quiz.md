# EKS에서의 모델 훈련 퀴즈

이 퀴즈는 Amazon EKS에서의 모델 훈련에 대한 이해를 테스트합니다. 분산 훈련 전략, Slurm/Slinky 통합, GPU 및 Trainium 기반 훈련, 스토리지 구성, 최적화 기법을 다룹니다.

## 퀴즈 문제

### 1. 단일 레이어를 여러 GPU에 분할하는 분산 훈련 전략은 무엇인가요?

A) 데이터 병렬화 (Data Parallelism)
B) 텐서 병렬화 (Tensor Parallelism)
C) 파이프라인 병렬화 (Pipeline Parallelism)
D) 전문가 병렬화 (Expert Parallelism)

<details>
<summary>정답 보기</summary>

**정답: B) 텐서 병렬화 (Tensor Parallelism)**

**설명:**
텐서 병렬화는 개별 레이어(어텐션 레이어나 피드포워드 네트워크 등)를 여러 GPU에 분할합니다. 각 GPU는 레이어 가중치의 일부를 보유하고 해당 부분의 연산을 수행합니다.

**병렬화 전략 비교:**

| 전략 | 분산 대상 | 통신 패턴 |
|------|----------|----------|
| 데이터 병렬화 | 훈련 데이터 배치 | 그래디언트 동기화 |
| 텐서 병렬화 | 개별 레이어 | 레이어 내부 통신 |
| 파이프라인 병렬화 | 레이어 그룹(스테이지) | 스테이지 간 활성화 전달 |
| 전문가 병렬화 | MoE의 전문가 네트워크 | 토큰 라우팅 |

텐서 병렬화는 대규모 언어 모델의 어텐션 레이어처럼 단일 GPU 메모리에 맞지 않는 매우 큰 레이어에 특히 유용합니다.

</details>

### 2. 2000억 파라미터 모델을 훈련할 때 권장되는 병렬화 전략은 무엇인가요?

A) 데이터 병렬화만 사용
B) 텐서 병렬화만 사용
C) 파이프라인 병렬화만 사용
D) 3D 병렬화 (DP + TP + PP)

<details>
<summary>정답 보기</summary>

**정답: D) 3D 병렬화 (DP + TP + PP)**

**설명:**
1000억 파라미터를 초과하는 모델의 경우, 3D 병렬화는 최대 효율성을 위해 세 가지 전략을 모두 결합합니다:

- **데이터 병렬화 (DP)**: GPU 그룹에 모델을 복제하여 각각 다른 데이터 배치 처리
- **텐서 병렬화 (TP)**: 노드 내에서 대규모 레이어 분할 (일반적으로 NVLink가 있는 8 GPU)
- **파이프라인 병렬화 (PP)**: 노드 간에 레이어 그룹을 분산하여 디바이스당 메모리 감소

64개 A100 GPU에서 2000억 모델 구성 예시:
```
TP=8  (각 노드 내)
PP=4  (4개 노드에 걸쳐)
DP=2  (2개 데이터 병렬 복제본)
총계: 8 × 4 × 2 = 64 GPU
```

이 접근 방식의 이점:
- 최대 메모리 효율성
- 연산과 통신의 균형
- 단일 노드 메모리 용량을 초과하는 모델 훈련 가능

</details>

### 3. Slinky 아키텍처에서 작업 어카운팅과 클러스터 상태를 관리하는 컴포넌트는 무엇인가요?

A) slurmctld
B) slurmdbd
C) slurmd
D) slurmrestd

<details>
<summary>정답 보기</summary>

**정답: B) slurmdbd**

**설명:**
Slinky/Slurm 컴포넌트는 각각 다른 목적을 가집니다:

| 컴포넌트 | 역할 | Kubernetes 리소스 |
|---------|------|------------------|
| **slurmctld** | 중앙 컨트롤러 - 작업, 파티션 및 리소스 할당 관리 | StatefulSet |
| **slurmdbd** | 데이터베이스 데몬 - 작업 어카운팅, 사용량 추적, 클러스터 상태 영속화 처리 | MySQL/MariaDB가 있는 StatefulSet |
| **slurmd** | 컴퓨트 데몬 - 각 워커 노드에서 실행, 작업 단계 실행 | DaemonSet |
| **slurmrestd** | REST API - 프로그래밍 방식 작업 제출 활성화 | Deployment |

slurmdbd 데몬의 중요한 역할:
- 과거 작업 데이터 저장
- 어카운팅을 위한 리소스 사용량 추적
- 장애 복구를 위한 클러스터 상태 유지
- 과거 사용량 기반 공정 공유 스케줄링 지원

</details>

### 4. Slinky가 컴퓨트 노드 그룹(파티션)을 정의하는 데 사용하는 CRD는 무엇인가요?

A) SlurmCluster
B) SlurmNodeSet
C) SlurmPartition
D) SlurmWorker

<details>
<summary>정답 보기</summary>

**정답: B) SlurmNodeSet**

**설명:**
Slinky는 두 가지 주요 Custom Resource Definition을 도입합니다:

1. **SlurmCluster**: 전체 클러스터 구성 정의:
   - 컨트롤러 (slurmctld) 설정
   - 데이터베이스 (slurmdbd) 구성
   - REST API 설정
   - 공유 스토리지 구성

2. **SlurmNodeSet**: 컴퓨트 노드 그룹(파티션) 정의:
   - 인스턴스 유형 및 GPU 구성
   - 리소스 할당 (CPU, 메모리, GPU 메모리)
   - GRES (Generic Resource Scheduling)를 위한 노드 기능
   - Karpenter 통합을 통한 오토스케일링 설정
   - 저지연 네트워킹을 위한 배치 그룹 구성

SlurmNodeSet 예시:
```yaml
apiVersion: slinky.slurm.net/v1alpha1
kind: SlurmNodeSet
metadata:
  name: gpu-a100-nodes
spec:
  partition: gpu-a100
  nodeCount: 4
  nodeTemplate:
    instanceType: p4d.24xlarge
    gpus:
      type: nvidia-a100
      count: 8
```

</details>

### 5. 분산 훈련에서 NCCL에 EFA(Elastic Fabric Adapter)를 활성화하는 환경 변수는 무엇인가요?

A) NCCL_EFA_ENABLE=1
B) FI_PROVIDER=efa
C) EFA_ENABLED=true
D) NCCL_NET=efa

<details>
<summary>정답 보기</summary>

**정답: B) FI_PROVIDER=efa**

**설명:**
분산 훈련을 위해 NCCL과 함께 EFA 네트워킹을 활성화하려면 여러 환경 변수를 설정해야 합니다:

```bash
# 주요 EFA 구성
export FI_PROVIDER=efa              # libfabric 프로바이더로 EFA 사용
export FI_EFA_USE_DEVICE_RDMA=1     # 디바이스 수준 RDMA 활성화
export RDMAV_FORK_SAFE=1            # RDMA와 함께 안전한 포킹

# EFA를 위한 NCCL 구성
export NCCL_DEBUG=INFO              # 디버깅 출력 활성화
export NCCL_ALGO=Ring               # Ring 알고리즘 사용 (EFA와 잘 작동)
export NCCL_PROTO=Simple            # EFA용 Simple 프로토콜
```

EFA는 지원되는 인스턴스 유형(p4d, p5, trn1)에서 최대 400 Gbps 네트워킹 대역폭을 제공하고 분산 훈련의 통신 지연 시간을 크게 줄입니다.

또한 파드는 EFA 디바이스를 요청해야 합니다:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # 4개 EFA 디바이스 요청
```

</details>

### 6. EKS에서 NVIDIA BioNeMo의 목적은 무엇인가요?

A) GPU 모니터링 및 메트릭 수집
B) 신약 개발 및 분자 모델링
C) 컨테이너 네트워킹 최적화
D) 모델 양자화 및 압축

<details>
<summary>정답 보기</summary>

**정답: B) 신약 개발 및 분자 모델링**

**설명:**
NVIDIA BioNeMo는 AI 기반 신약 개발 및 분자 모델링을 위한 특화된 프레임워크입니다:

**주요 기능:**
- **MegaMolBART**: 분자 생성 및 최적화
- **ESMFold**: 단백질 구조 예측
- **DiffDock**: 분자 도킹
- **NVIDIA Clara**: 신약 개발 파이프라인

**EKS에서의 사용 사례:**
- 새로운 신약 후보 물질 생성
- 단백질-리간드 상호작용 예측
- 분자 특성 최적화
- 대량 가상 스크리닝

**배포 요구사항:**
```yaml
resources:
  limits:
    nvidia.com/gpu: 8      # 대규모 모델을 위한 여러 GPU
    memory: "500Gi"        # 분자 데이터셋을 위한 높은 메모리
```

BioNeMo는 NVIDIA의 GPU 가속을 활용하여 CPU 기반 접근 방식에 비해 계산 화학 워크플로우를 크게 가속화합니다.

</details>

### 7. Trainium에서 HuggingFace 모델을 위한 고수준 훈련 API를 제공하는 Neuron SDK 패키지는 무엇인가요?

A) torch-neuronx
B) tensorflow-neuronx
C) optimum-neuron
D) transformers-neuronx

<details>
<summary>정답 보기</summary>

**정답: C) optimum-neuron**

**설명:**
Neuron SDK에는 각각 다른 목적을 가진 여러 패키지가 포함됩니다:

| 패키지 | 목적 | 수준 |
|--------|------|------|
| **torch-neuronx** | 코어 PyTorch 통합 | 저수준 |
| **tensorflow-neuronx** | 코어 TensorFlow 통합 | 저수준 |
| **transformers-neuronx** | 트랜스포머용 최적화된 추론 | 중간 수준 |
| **optimum-neuron** | 고수준 훈련/추론 API | 고수준 |

**optimum-neuron**은 HuggingFace의 Optimum 라이브러리의 일부이며 다음을 제공합니다:
- `NeuronTrainer`: HuggingFace Trainer의 드롭인 대체
- `NeuronTrainingArguments`: Neuron 특화 옵션이 있는 훈련 구성
- 자동 텐서 병렬화 구성
- 분산 훈련 통합 (ZeRO, 파이프라인 병렬화)
- 표준 HuggingFace 모델과의 체크포인트 호환성

사용 예시:
```python
from optimum.neuron import NeuronTrainer, NeuronTrainingArguments

training_args = NeuronTrainingArguments(
    tensor_parallel_size=8,
    bf16=True,
)
trainer = NeuronTrainer(model=model, args=training_args)
trainer.train()
```

</details>

### 8. EKS에서 고처리량 분산 훈련 데이터 접근을 위해 권장되는 스토리지 솔루션은 무엇인가요?

A) Amazon EBS gp3
B) Amazon EFS
C) FSx for Lustre
D) Amazon S3 직접 접근

<details>
<summary>정답 보기</summary>

**정답: C) FSx for Lustre**

**설명:**
FSx for Lustre는 다음과 같은 이유로 분산 ML 훈련에 권장되는 스토리지입니다:

**성능 특성:**
- 최대 1+ TB/s 집계 처리량
- 밀리초 미만의 지연 시간
- HPC/ML 워크로드에 최적화된 병렬 파일 시스템

**ML 훈련을 위한 주요 기능:**
- **S3 통합**: S3 데이터 리포지토리와 자동 데이터 가져오기/내보내기
- **ReadWriteMany**: 여러 파드가 동시에 접근 가능
- **높은 IOPS**: 훈련의 랜덤 접근 패턴에 중요
- **체크포인트 지원**: 훈련 중 빠른 체크포인트 쓰기

**비교:**

| 스토리지 | 처리량 | 접근 모드 | 적합한 용도 |
|---------|--------|----------|------------|
| FSx Lustre | 매우 높음 | ReadWriteMany | 훈련 데이터, 체크포인트 |
| EFS | 중간 | ReadWriteMany | 공유 설정, 모델 |
| EBS | 높음 | ReadWriteOnce | 단일 노드 워크로드 |
| S3 | 가변 | 객체 | 콜드 데이터, 아카이브 |

구성 예시:
```yaml
lustreConfiguration:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: 250  # TiB당 MB/s
  dataRepositoryAssociations:
    - fileSystemPath: /data
      dataRepositoryPath: s3://bucket/training-data
```

</details>

### 9. `minAvailable: 4`가 설정된 Volcano Job에서 3개의 노드만 사용 가능할 경우 어떻게 되나요?

A) 3개의 워커로 작업 시작
B) 4개의 노드가 사용 가능해질 때까지 대기
C) 즉시 작업 실패
D) Karpenter에 추가 노드 요청

<details>
<summary>정답 보기</summary>

**정답: B) 4개의 노드가 사용 가능해질 때까지 대기**

**설명:**
Volcano의 `minAvailable` 필드는 **Gang 스케줄링**을 구현하여 모든 필요한 파드가 함께 스케줄링되거나 전혀 스케줄링되지 않도록 합니다.

**Gang 스케줄링 동작:**
- `minAvailable: 4`가 설정되면 4개 파드 모두 동시에 스케줄링 가능해야 함
- 리소스가 사용 가능해질 때까지 작업이 대기 상태로 유지
- 분산 훈련에서 교착 상태 방지
- 일관된 훈련 환경 보장

**ML 훈련에서 중요한 이유:**
1. **분산 훈련은 모든 워커 필요**: 부분 워커로는 훈련 진행 불가
2. **리소스 효율성**: 리소스를 낭비하는 부분 할당 방지
3. **결정론적 동작**: 예상된 병렬 수준으로 훈련 시작

예시:
```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
spec:
  minAvailable: 4  # Gang 스케줄링 요구사항
  tasks:
    - name: worker
      replicas: 4
```

Gang 스케줄링이 없으면 일부 워커가 시작되고 다른 워커가 대기 중일 수 있어 타임아웃과 훈련 작업 실패로 이어질 수 있습니다.

</details>

### 10. 훈련에서 FP16 대신 BF16(bfloat16)을 사용할 때의 이점은 무엇인가요?

A) 더 높은 정밀도
B) 손실 스케일링 불필요
C) 더 작은 메모리 공간
D) 더 빠른 연산

<details>
<summary>정답 보기</summary>

**정답: B) 손실 스케일링 불필요**

**설명:**
BF16(Brain Floating Point 16)은 FP32와 동일한 지수 범위를 가지지만 가수 정밀도가 감소합니다:

| 형식 | 지수 비트 | 가수 비트 | 범위 |
|------|----------|----------|------|
| FP32 | 8 | 23 | 넓음 |
| FP16 | 5 | 10 | 제한적 |
| BF16 | 8 | 7 | 넓음 (FP32와 동일) |

**BF16이 손실 스케일링을 필요로 하지 않는 이유:**
- BF16의 8비트 지수는 FP32와 동일한 동적 범위 제공
- FP16의 제한된 범위는 훈련 중 언더플로우/오버플로우 발생
- 손실 스케일링은 FP16에서 언더플로우 방지를 위해 그래디언트를 인위적으로 증가

**BF16 장점:**
```python
# FP16은 손실 스케일링 필요
scaler = GradScaler()
with autocast(dtype=torch.float16):
    loss = model(inputs)
scaler.scale(loss).backward()
scaler.step(optimizer)

# BF16은 더 간단 - 스케일링 불필요
with autocast(dtype=torch.bfloat16):
    loss = model(inputs)
loss.backward()
optimizer.step()
```

BF16이 지원되는 하드웨어:
- NVIDIA A100, H100 GPU (Ampere 이상)
- AWS Trainium 칩
- Intel Sapphire Rapids CPU

</details>

### 11. 훈련 중 그래디언트 체크포인팅은 무엇을 달성하나요?

A) 더 빠른 순방향 패스
B) 감소된 통신 오버헤드
C) 활성화 재계산을 통한 메모리 절약
D) 향상된 모델 정확도

<details>
<summary>정답 보기</summary>

**정답: C) 활성화 재계산을 통한 메모리 절약**

**설명:**
그래디언트 체크포인팅(활성화 체크포인팅이라고도 함)은 순방향 패스 중 활성화를 선택적으로 저장하고 역전파 중에 재계산하여 연산과 메모리를 교환합니다.

**작동 방식:**
1. **체크포인팅 없이**: 모든 활성화가 메모리에 저장
2. **체크포인팅 사용**: 체크포인트 활성화만 저장; 역방향 패스 중 중간 활성화 재계산

**메모리 절약:**
- 활성화 메모리를 O(n)에서 O(sqrt(n))으로 감소 (n은 레이어 수)
- 3-4배 더 큰 배치 크기로 훈련 가능
- 제한된 GPU 메모리에서 대규모 모델 훈련에 필수

**PyTorch에서의 구성:**
```python
from torch.utils.checkpoint import checkpoint

class Model(nn.Module):
    def forward(self, x):
        # 특정 레이어 체크포인트
        x = checkpoint(self.layer1, x)
        x = checkpoint(self.layer2, x)
        return x

# 또는 전체 모델에 대해 활성화
model.gradient_checkpointing_enable()
```

**트레이드오프:**
- 연산 시간 ~30% 증가
- 활성화 메모리 3-4배 감소
- 더 큰 모델/배치 훈련 가능

</details>

### 12. 옵티마이저 상태와 모델 파라미터 모두를 CPU 메모리로 오프로드하는 DeepSpeed ZeRO 스테이지는 무엇인가요?

A) ZeRO Stage 1
B) ZeRO Stage 2
C) ZeRO Stage 3
D) ZeRO Stage 0

<details>
<summary>정답 보기</summary>

**정답: C) ZeRO Stage 3**

**설명:**
DeepSpeed ZeRO(Zero Redundancy Optimizer)는 스테이지별로 메모리 중복을 점진적으로 줄입니다:

| 스테이지 | 파티셔닝 대상 | CPU 오프로드 가능 |
|---------|-------------|------------------|
| Stage 0 | 없음 (기준선) | 아니오 |
| Stage 1 | 옵티마이저 상태 | 옵티마이저 상태 |
| Stage 2 | 옵티마이저 상태 + 그래디언트 | 옵티마이저 상태 |
| Stage 3 | 옵티마이저 상태 + 그래디언트 + 파라미터 | 옵티마이저와 파라미터 모두 |

**ZeRO Stage 3 구성:**
```json
{
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {
      "device": "cpu",
      "pin_memory": true
    },
    "offload_param": {
      "device": "cpu",
      "pin_memory": true
    }
  }
}
```

**ZeRO-3를 사용해야 할 때:**
- GPU 메모리보다 큰 모델 훈련
- 최대 메모리 효율성이 필요할 때
- 메모리를 위해 약간의 속도 저하 허용 가능할 때

**메모리 감소 (대략적):**
- Stage 1: 4배 감소
- Stage 2: 8배 감소
- Stage 3: GPU 수에 따른 선형 스케일링 (이론적으로 무제한)

</details>

### 13. MPIJob 명세에서 `slotsPerWorker` 필드의 목적은 무엇인가요?

A) 워커당 CPU 코어 수
B) 워커당 GPU 디바이스 수
C) 워커당 MPI 프로세스 수
D) 워커당 네트워크 인터페이스 수

<details>
<summary>정답 보기</summary>

**정답: C) 워커당 MPI 프로세스 수**

**설명:**
MPIJob에서 `slotsPerWorker`는 각 워커 파드가 실행할 MPI 랭크(프로세스) 수를 정의합니다:

```yaml
apiVersion: kubeflow.org/v1
kind: MPIJob
spec:
  slotsPerWorker: 8  # 워커당 8개 MPI 프로세스
  mpiReplicaSpecs:
    Worker:
      replicas: 4  # 4개 워커 파드
```

**총 MPI 프로세스 = slotsPerWorker × Worker replicas**
이 예시에서: 8 × 4 = 32 MPI 프로세스

**일반적인 구성:**
- `slotsPerWorker`를 노드당 GPU 수와 동일하게 설정
- 각 MPI 랭크는 일반적으로 하나의 GPU 처리
- 8-GPU 노드의 경우: `slotsPerWorker: 8`

**Launcher 명령 예시:**
```yaml
command:
  - mpirun
  - -np
  - "32"  # 총 프로세스 (slots × workers와 일치해야 함)
  - -bind-to
  - none
  - -map-by
  - slot
```

이렇게 하면 각 GPU가 정확히 하나의 MPI 프로세스에 할당되어 GPU 경합을 피하면서 병렬성을 최대화합니다.

</details>

### 14. 장기 실행 훈련 작업에 권장되는 체크포인트 빈도 전략은 무엇인가요?

A) 에포크당 한 번만 체크포인트
B) 최대 안전을 위해 매 스텝마다 체크포인트
C) N 스텝마다 체크포인트, 마지막 3-5개 유지
D) 훈련 속도 최대화를 위해 체크포인팅 없음

<details>
<summary>정답 보기</summary>

**정답: C) N 스텝마다 체크포인트, 마지막 3-5개 유지**

**설명:**
최적의 체크포인트 전략은 복구 능력과 스토리지 비용 및 훈련 오버헤드의 균형을 맞춥니다:

**권장 접근 방식:**
```yaml
checkpoint:
  save_steps: 500           # 500 스텝마다 저장
  save_total_limit: 5       # 마지막 5개 체크포인트만 유지
  save_on_each_node: false  # 랭크 0에서만 저장
```

**이 전략의 이유:**
1. **복구 세분성**: 데이터 손실을 최대 ~500 스텝으로 제한
2. **스토리지 효율성**: 3-5개 체크포인트 유지로 스토리지 팽창 방지
3. **훈련 오버헤드**: 매 스텝 체크포인팅은 너무 느림
4. **에포크만은 위험**: 긴 에포크는 실패 시 상당한 데이터 손실 의미

**체크포인트 크기 고려사항:**
- 대규모 모델 (700억+): 각 체크포인트가 100-200GB일 수 있음
- 5개 체크포인트 = 500GB-1TB 스토리지
- 오래된 체크포인트에는 S3 수명 주기 정책 사용

**모범 사례:**
```python
training_args = TrainingArguments(
    save_strategy="steps",
    save_steps=500,
    save_total_limit=5,
    save_safetensors=True,  # 더 빠르고 안전한 형식
)
```

프로덕션 훈련의 경우, 체크포인트 관리자 사이드카를 사용하여 체크포인트를 내구성 있는 스토리지(S3)에 동기화하세요.

</details>

### 15. 최적의 EFA 성능을 위해 GPU 훈련 파드가 단일 가용 영역에 스케줄링되도록 하는 Karpenter 구성은 무엇인가요?

A) `consolidationPolicy: WhenEmpty`
B) 단일 값이 있는 `topology.kubernetes.io/zone` 요구사항
C) `karpenter.sh/capacity-type: spot`
D) `disruption.budgets.nodes: "0"`

<details>
<summary>정답 보기</summary>

**정답: B) 단일 값이 있는 `topology.kubernetes.io/zone` 요구사항**

**설명:**
EFA(Elastic Fabric Adapter)는 통신하는 모든 인스턴스가 동일한 가용 영역에 있어야 합니다. Karpenter의 영역 요구사항이 이를 보장합니다:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
            - us-west-2a  # EFA를 위한 단일 AZ
```

**단일 AZ가 EFA에 중요한 이유:**
- EFA는 고대역폭, 저지연 통신을 위해 AWS의 커스텀 네트워크 인터페이스 사용
- 교차 AZ 통신은 EFA의 RDMA 기능을 사용할 수 없음
- AZ 간 네트워크 지연 시간이 크게 증가

**다른 옵션 설명:**
- A) `consolidationPolicy`: 노드 통합 제어, 배치가 아님
- C) `capacity-type: spot`: 가격 모델 결정, 영역이 아님
- D) `disruption.budgets`: 노드 중단 방지, 영역 선택이 아님

**GPU 훈련을 위한 전체 구성:**
```yaml
requirements:
  - key: node.kubernetes.io/instance-type
    operator: In
    values: [p4d.24xlarge]
  - key: topology.kubernetes.io/zone
    operator: In
    values: [us-west-2a]  # 단일 영역
  - key: karpenter.sh/capacity-type
    operator: In
    values: [on-demand]   # 훈련 안정성
```

</details>

## 요약

이 퀴즈는 EKS에서의 모델 훈련에 대한 핵심 개념을 다루었습니다:

1. **분산 훈련 전략**: 데이터, 텐서, 파이프라인, 전문가 병렬화
2. **Slinky/Slurm 통합**: 컴포넌트 (slurmctld, slurmdbd, slurmd) 및 CRD
3. **GPU 훈련**: NCCL 구성, EFA 네트워킹, BioNeMo
4. **Trainium 훈련**: Neuron SDK 패키지, optimum-neuron
5. **스토리지**: 고처리량 훈련을 위한 FSx for Lustre
6. **스케줄링**: Volcano gang 스케줄링
7. **최적화**: 혼합 정밀도 (BF16), 그래디언트 체크포인팅, DeepSpeed ZeRO
8. **인프라**: Karpenter NodePool, 체크포인트 관리

자세한 내용은 [EKS에서의 모델 훈련](../../ai-ml/05-model-training.md) 문서를 참조하세요.
