# EKS Auto Mode Spot 전략 퀴즈

> **관련 문서**: [Spot 인스턴스 전략](../../eks-auto-mode/04-spot-strategies.md)

## 객관식 문제

### 1. Spot 인스턴스 인터럽트 위험을 분산하기 위한 최적의 전략은 무엇인가요?

- A) 단일 인스턴스 타입만 사용
- B) 다양한 인스턴스 패밀리, 세대, 크기 사용
- C) On-Demand만 사용
- D) 가장 저렴한 인스턴스만 선택

<details>
<summary>정답 보기</summary>

**정답: B) 다양한 인스턴스 패밀리, 세대, 크기 사용**

**설명:**
Spot 인스턴스는 용량 풀별로 인터럽트가 발생합니다. 다양한 인스턴스 타입을 허용하면 여러 용량 풀에서 인스턴스를 확보할 수 있어 인터럽트 위험이 분산됩니다.

```yaml
spec:
  template:
    spec:
      requirements:
        # 다양한 인스턴스 패밀리
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["m", "c", "r", "i", "d"]
        # 다양한 세대
        - key: karpenter.k8s.aws/instance-generation
          operator: In
          values: ["5", "6", "7"]
        # 다양한 크기
        - key: karpenter.k8s.aws/instance-size
          operator: In
          values: ["large", "xlarge", "2xlarge"]
        # 다양한 아키텍처
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

</details>

### 2. Spot 인스턴스와 On-Demand 인스턴스를 구분하는 Karpenter 레이블 키는 무엇인가요?

- A) `node.kubernetes.io/capacity-type`
- B) `karpenter.sh/capacity-type`
- C) `eks.amazonaws.com/instance-type`
- D) `karpenter.k8s.aws/spot-or-ondemand`

<details>
<summary>정답 보기</summary>

**정답: B) `karpenter.sh/capacity-type`**

**설명:**
이 레이블을 통해 Pod의 nodeAffinity나 NodePool의 requirements에서 Spot/On-Demand 인스턴스를 지정할 수 있습니다.

```yaml
# Pod에서 Spot 인스턴스 선호 설정
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        preference:
          matchExpressions:
            - key: karpenter.sh/capacity-type
              operator: In
              values: ["spot"]
```

</details>

### 3. Spot 인스턴스가 인터럽트될 때 기본적으로 주어지는 경고 시간은 얼마인가요?

- A) 30초
- B) 2분
- C) 5분
- D) 10분

<details>
<summary>정답 보기</summary>

**정답: B) 2분**

**설명:**
AWS Spot 인스턴스는 회수되기 전 2분의 경고 시간이 주어집니다. 이 시간 동안 워크로드를 graceful하게 종료해야 합니다.

**Spot 인터럽트 처리 모범 사례:**
- Pod의 terminationGracePeriodSeconds를 2분 이하로 설정
- 애플리케이션에 SIGTERM 핸들러 구현
- 상태가 없는 워크로드 우선 배치
- 체크포인팅 메커니즘 구현 (배치 작업)

</details>

### 4. Spot 인스턴스 사용 시 권장되는 워크로드 유형이 아닌 것은?

- A) 배치 처리 작업
- B) 스테이트리스 웹 서버
- C) 단일 인스턴스 데이터베이스
- D) 개발/테스트 환경

<details>
<summary>정답 보기</summary>

**정답: C) 단일 인스턴스 데이터베이스**

**설명:**
단일 인스턴스 데이터베이스는 인터럽트 시 가용성 문제가 발생하므로 Spot에 적합하지 않습니다.

**Spot에 적합한 워크로드:**
- 배치 처리 / 빅데이터 분석
- CI/CD 파이프라인
- 스테이트리스 웹 서버 (Auto Scaling)
- 개발/테스트 환경
- 컨테이너 기반 마이크로서비스

**On-Demand가 필요한 워크로드:**
- 데이터베이스
- 메시지 큐
- 클러스터 관리 컴포넌트
- 장기 실행 상태 저장 작업

</details>

### 5. NodePool에서 Spot과 On-Demand를 혼합할 때 Spot 우선 선택을 설정하는 방법은?

- A) `spotPriority: high`
- B) weight 값을 통한 NodePool 우선순위 설정
- C) `capacityPriority: spot`
- D) `preferSpot: true`

<details>
<summary>정답 보기</summary>

**정답: B) weight 값을 통한 NodePool 우선순위 설정**

**설명:**
여러 NodePool을 생성하고 weight 값으로 우선순위를 지정합니다. weight가 높을수록 먼저 사용됩니다.

```yaml
# Spot 우선 NodePool (weight: 100)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: spot-first
spec:
  weight: 100  # 높은 우선순위
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
---
# On-Demand 폴백 NodePool (weight: 10)
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ondemand-fallback
spec:
  weight: 10  # 낮은 우선순위
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

</details>

### 6. Spot 인스턴스 최대 절감률은 On-Demand 대비 약 얼마인가요?

- A) 30-40%
- B) 50-60%
- C) 70-90%
- D) 95% 이상

<details>
<summary>정답 보기</summary>

**정답: C) 70-90%**

**설명:**
Spot 인스턴스는 On-Demand 대비 최대 70-90%까지 비용을 절감할 수 있습니다.

**비용 최적화 전략 조합:**
| 전략 | 예상 절감률 |
|------|------------|
| Spot 인스턴스 | 70-90% |
| Graviton (ARM) | ~20% |
| Spot + Graviton | 최대 90% |

다만, Spot 절감률은 인스턴스 타입과 가용 영역에 따라 변동됩니다.

</details>
