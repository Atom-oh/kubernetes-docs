# EKS Hybrid Nodes 비용 최적화 퀴즈

> **관련 문서**: [비용 최적화](../../eks-hybrid-nodes/07-cost-optimization.md)

## 객관식 문제

### 1. Hybrid Nodes 환경에서 비용 최적화를 위한 전략으로 적합하지 않은 것은?

A. 온프레미스 GPU는 추론 워크로드에 활용
B. 버스트 트래픽은 클라우드 노드에서 처리
C. 모든 워크로드를 Hybrid Nodes로 이전
D. 데이터 로컬리티가 필요한 워크로드는 온프레미스에서 실행

<details>
<summary>정답 보기</summary>

**정답: C. 모든 워크로드를 Hybrid Nodes로 이전**

**설명:**
모든 워크로드를 Hybrid Nodes로 이전하면 오히려 복잡성이 증가하고 비용 효율성이 떨어집니다. 워크로드 특성에 따라 적절한 위치를 선택해야 합니다.

**비용 최적화 전략:**

| 워크로드 유형 | 권장 위치 | 이유 |
|-------------|----------|-----|
| 상시 GPU 추론 | 온프레미스 | 기존 하드웨어 활용 |
| 버스트 트래픽 | 클라우드 | 탄력적 확장 |
| 데이터 집약적 | 데이터 근처 | 전송 비용 절감 |
| 스테이트리스 | 클라우드 | 관리 용이성 |
| 규제 대상 | 온프레미스 | 컴플라이언스 |

</details>

### 2. 온프레미스 GPU와 클라우드 GPU의 비용 손익분기점(Break-even) 분석에서 고려해야 할 요소가 아닌 것은?

A. 하드웨어 감가상각비
B. 전력 및 냉각 비용
C. 클라우드 인스턴스 시간당 비용
D. 사용자 인터페이스 디자인

<details>
<summary>정답 보기</summary>

**정답: D. 사용자 인터페이스 디자인**

**설명:**
비용 손익분기점 분석은 인프라 운영 비용에 초점을 맞춥니다. UI 디자인은 비용 분석과 관련이 없습니다.

**비용 분석 요소:**

```
온프레미스 TCO (월간):
├── 하드웨어 감가상각 (GPU 서버 / 36개월)
├── 전력 비용 (kWh × 단가)
├── 냉각 비용 (PUE 계수)
├── 네트워크 비용 (Direct Connect)
├── 인건비 (운영/유지보수)
└── 시설 비용 (렌탈/공간)

클라우드 TCO (월간):
├── 인스턴스 비용 (시간당 × 사용 시간)
├── 데이터 전송 비용
├── 스토리지 비용
└── 관리형 서비스 비용
```

```python
# 손익분기점 계산 예시
onprem_monthly = 5000  # 온프레미스 월 비용 (고정)
cloud_hourly = 32.77   # p4d.24xlarge 시간당 비용

# 손익분기점 = 온프레미스 월 비용 / 클라우드 시간당 비용
breakeven_hours = onprem_monthly / cloud_hourly
print(f"손익분기점: {breakeven_hours:.0f}시간/월")  # 약 153시간
```

</details>

### 3. Karpenter를 사용하여 비용을 최적화할 때 Spot 인스턴스 우선 사용 설정 방법은?

A. nodeSelector로 Spot 레이블 지정
B. Provisioner에서 capacity-type을 spot으로 우선 설정
C. 수동으로 Spot 인스턴스 생성
D. Fargate 프로파일 사용

<details>
<summary>정답 보기</summary>

**정답: B. Provisioner에서 capacity-type을 spot으로 우선 설정**

**설명:**
Karpenter Provisioner에서 Spot 인스턴스를 우선적으로 사용하도록 설정할 수 있습니다.

```yaml
apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: gpu-spot-provisioner
spec:
  requirements:
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot", "on-demand"]  # Spot 우선
  - key: node.kubernetes.io/instance-type
    operator: In
    values: ["p4d.24xlarge", "p3.16xlarge"]

  # Spot 인스턴스 우선 (weight가 높을수록 우선)
  weight: 100

  limits:
    resources:
      nvidia.com/gpu: 32

  # 비용 최적화: 사용 안하면 빠르게 축소
  ttlSecondsAfterEmpty: 300
```

**Spot 인스턴스 이점:**
- 온디맨드 대비 최대 90% 비용 절감
- 내결함성 있는 워크로드에 적합
- 배치 처리, 학습 작업에 권장

</details>

### 4. GPU 사용률을 모니터링하여 비용을 최적화하기 위해 사용하는 NVIDIA 도구는?

A. nvidia-smi만 사용
B. DCGM (Data Center GPU Manager) Exporter
C. kubectl top
D. htop

<details>
<summary>정답 보기</summary>

**정답: B. DCGM (Data Center GPU Manager) Exporter**

**설명:**
DCGM Exporter는 GPU 메트릭을 Prometheus 형식으로 노출하여 상세한 GPU 사용률 모니터링을 가능하게 합니다.

```yaml
# DCGM Exporter 배포 (GPU Operator에 포함)
# 또는 수동 배포
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: dcgm-exporter
  namespace: gpu-operator
spec:
  template:
    spec:
      containers:
      - name: dcgm-exporter
        image: nvcr.io/nvidia/k8s/dcgm-exporter:3.2.6-3.1.9-ubuntu22.04
        ports:
        - containerPort: 9400
```

```yaml
# Prometheus 알림 규칙 예시
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
spec:
  groups:
  - name: gpu.cost.rules
    rules:
    - alert: GPUUnderutilized
      expr: |
        avg_over_time(DCGM_FI_DEV_GPU_UTIL[1h]) < 20
      for: 2h
      labels:
        severity: info
      annotations:
        summary: "GPU 사용률 20% 미만 - 비용 최적화 검토 필요"
```

**주요 모니터링 메트릭:**
- `DCGM_FI_DEV_GPU_UTIL`: GPU 사용률 (%)
- `DCGM_FI_DEV_MEM_USED`: GPU 메모리 사용량
- `DCGM_FI_DEV_POWER_USAGE`: 전력 사용량

</details>

### 5. 하이브리드 환경에서 데이터 전송 비용을 절감하기 위한 전략은?

A. 모든 데이터를 클라우드로 복사
B. 데이터 로컬리티를 고려한 워크로드 배치
C. 데이터 압축 없이 전송
D. 실시간으로 모든 데이터 동기화

<details>
<summary>정답 보기</summary>

**정답: B. 데이터 로컬리티를 고려한 워크로드 배치**

**설명:**
데이터가 있는 위치에서 처리하면 네트워크 전송 비용을 크게 절감할 수 있습니다.

```yaml
# 데이터 위치 기반 워크로드 배치
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
spec:
  template:
    spec:
      nodeSelector:
        data-location: primary-storage
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: location
                operator: In
                values: ["onprem"]  # 데이터 근처 노드 선호
```

**데이터 전송 비용 최적화 전략:**

| 전략 | 절감 효과 |
|-----|---------|
| 데이터 로컬리티 배치 | 40-60% |
| 데이터 압축 | 30-50% |
| 캐싱 레이어 | 20-40% |
| 배치 전송 | 10-20% |

</details>

### 6. Reserved Instances 또는 Savings Plans를 사용할 때 가장 적합한 워크로드 유형은?

A. 예측 불가능한 버스트 워크로드
B. 일회성 배치 작업
C. 안정적이고 예측 가능한 상시 워크로드
D. 테스트 및 개발 환경

<details>
<summary>정답 보기</summary>

**정답: C. 안정적이고 예측 가능한 상시 워크로드**

**설명:**
Reserved Instances와 Savings Plans는 1-3년 약정으로 할인을 제공하므로, 지속적으로 사용하는 워크로드에 적합합니다.

```
비용 모델 비교:

워크로드 유형          | 권장 가격 모델
----------------------|------------------
상시 운영 (24/7)      | Reserved/Savings Plans (최대 72% 할인)
예측 가능한 피크      | On-Demand + Scheduled Reserved
버스트/유휴          | Spot Instances (최대 90% 할인)
테스트/개발          | Spot 또는 On-Demand
```

**EKS 환경에서의 비용 최적화 조합:**
```yaml
# 기본 용량: Reserved Instances
# 피크 용량: Spot Instances
# 버스트: On-Demand (Karpenter 자동 확장)

apiVersion: karpenter.sh/v1alpha5
kind: Provisioner
metadata:
  name: mixed-capacity
spec:
  requirements:
  - key: karpenter.sh/capacity-type
    operator: In
    values: ["spot", "on-demand"]
  # 비용 최적화 우선순위: spot > on-demand
```

</details>

