# EKS Auto Mode 워크로드 최적화 퀴즈

> **관련 문서**: [워크로드 최적화](../../eks-auto-mode/08-workload-optimization.md)

## 객관식 문제

### 1. 대규모 이커머스 플랫폼에서 프론트엔드 워크로드에 권장되는 NodePool 설정은?

- A) Spot 전용, Consolidation 적극적
- B) On-Demand 우선, 가용성 중심 Disruption Budget
- C) GPU 인스턴스, 고성능 설정
- D) 메모리 최적화 인스턴스만

<details>
<summary>정답 보기</summary>

**정답: B) On-Demand 우선, 가용성 중심 Disruption Budget**

**설명:**
프론트엔드 워크로드는 사용자 대면이므로 가용성이 최우선입니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: frontend-tier
spec:
  template:
    metadata:
      labels:
        tier: frontend
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]  # 가용성 우선
      taints:
        - key: tier
          value: frontend
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 10m
    budgets:
      - nodes: "10%"
      - nodes: "1"
        schedule: "0 9-23 * * *"  # 피크 시간
        duration: 14h
```

</details>

### 2. 배치 처리 워크로드에 가장 적합한 NodePool 설정은?

- A) On-Demand 전용, 보수적 Consolidation
- B) Spot 전용, 다양한 인스턴스 패밀리, 빠른 정리
- C) GPU 인스턴스만 사용
- D) 시스템 NodePool에 배치

<details>
<summary>정답 보기</summary>

**정답: B) Spot 전용, 다양한 인스턴스 패밀리, 빠른 정리**

**설명:**
배치 작업은 인터럽트에 내성이 있어 Spot 인스턴스에 적합합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    metadata:
      labels:
        tier: batch
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r", "i", "d"]  # 다양한 패밀리
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot 전용
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      taints:
        - key: tier
          value: batch
          effect: NoSchedule
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s  # 빠른 정리
```

</details>

### 3. GPU ML 추론 워크로드에서 권장되는 Consolidation 설정은?

- A) `consolidateAfter: 0s`
- B) `consolidateAfter: 15m` (GPU 시작 시간 고려)
- C) `consolidationPolicy: WhenEmptyOrUnderutilized`
- D) Consolidation 비활성화

<details>
<summary>정답 보기</summary>

**정답: B) `consolidateAfter: 15m` (GPU 시작 시간 고려)**

**설명:**
GPU 인스턴스는 시작 시간이 오래 걸리므로 충분한 consolidateAfter가 필요합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-inference
spec:
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["g"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["g5.xlarge", "g5.2xlarge", "g5.4xlarge"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
      taints:
        - key: nvidia.com/gpu
          value: "true"
          effect: NoSchedule
  limits:
    nvidia.com/gpu: 20
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 15m  # GPU 시작 시간 고려
```

</details>

### 4. API 서버 워크로드에서 안정성과 비용의 균형을 맞추기 위한 전략은?

- A) On-Demand 전용
- B) Spot 전용
- C) Spot/On-Demand 혼합 + Graviton 포함
- D) Fargate 전용

<details>
<summary>정답 보기</summary>

**정답: C) Spot/On-Demand 혼합 + Graviton 포함**

**설명:**
API 서버는 적절한 가용성이 필요하면서도 비용 최적화가 가능합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: api-tier
spec:
  template:
    metadata:
      labels:
        tier: api
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand", "spot"]  # 혼합
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Graviton 포함
      taints:
        - key: tier
          value: api
          effect: NoSchedule
  weight: 10
```

**예상 비용 절감:** ~40%

</details>

### 5. 다중 아키텍처(amd64/arm64) 지원을 위해 애플리케이션에서 확인해야 할 사항은?

- A) 특별한 확인 필요 없음
- B) 컨테이너 이미지가 multi-arch를 지원하는지 확인
- C) Kubernetes 버전만 확인
- D) AWS 리전만 확인

<details>
<summary>정답 보기</summary>

**정답: B) 컨테이너 이미지가 multi-arch를 지원하는지 확인**

**설명:**
Graviton(arm64) 인스턴스를 활용하려면 컨테이너 이미지가 해당 아키텍처를 지원해야 합니다.

```bash
# 이미지의 지원 아키텍처 확인
docker manifest inspect nginx:latest | grep architecture

# multi-arch 이미지 빌드 예시
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t myapp:latest \
    --push .
```

**체크리스트:**
- 베이스 이미지 multi-arch 지원 확인
- 네이티브 바이너리가 있는 경우 양쪽 아키텍처 빌드
- CI/CD 파이프라인에서 multi-arch 빌드 설정

</details>

### 6. 워크로드별 NodePool 분리 시 Pod가 올바른 NodePool로 스케줄되게 하는 방법은?

- A) Pod 이름으로 자동 매칭
- B) Taint/Toleration과 NodeSelector 또는 Affinity 사용
- C) 네임스페이스 기반 자동 분리
- D) AWS 태그만으로 분리

<details>
<summary>정답 보기</summary>

**정답: B) Taint/Toleration과 NodeSelector 또는 Affinity 사용**

**설명:**
NodePool에 taint를 설정하고, Pod에 toleration과 affinity를 추가합니다.

```yaml
# NodePool에 taint 설정
spec:
  template:
    spec:
      taints:
        - key: tier
          value: batch
          effect: NoSchedule

---
# Pod에 toleration과 affinity 설정
apiVersion: apps/v1
kind: Deployment
metadata:
  name: batch-job
spec:
  template:
    spec:
      tolerations:
        - key: tier
          value: batch
          effect: NoSchedule
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: tier
                    operator: In
                    values: ["batch"]
```

</details>
