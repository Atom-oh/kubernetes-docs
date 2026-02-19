# EKS Auto Mode 비용 관리 퀴즈

> **관련 문서**: [비용 관리](../../eks-auto-mode/06-cost-management.md)

## 객관식 문제

### 1. 비용 최적화를 위해 Graviton(ARM) 인스턴스를 포함하면 약 몇 % 비용 절감이 가능한가요?

- A) 5%
- B) 10%
- C) 20%
- D) 50%

<details>
<summary>정답 보기</summary>

**정답: C) 20%**

**설명:**
AWS Graviton 프로세서 기반 인스턴스(arm64)는 동급 x86 인스턴스 대비 약 20% 저렴하면서도 우수한 성능을 제공합니다.

```yaml
spec:
  template:
    spec:
      requirements:
        # Graviton (ARM) 인스턴스 포함
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
```

**비용 최적화 전략:**
- Graviton(ARM) 인스턴스 사용: ~20% 절감
- Spot 인스턴스 사용: 최대 70-90% 절감
- 적극적인 Consolidation: 저사용률 노드 통합
- 적절한 리소스 요청: 오버프로비저닝 방지

</details>

### 2. NodePool의 `limits` 설정에서 CPU 제한을 500으로 설정한 경우의 의미는?

- A) 각 노드의 최대 CPU가 500 코어
- B) NodePool 전체에서 최대 500 vCPU까지 프로비저닝 가능
- C) Pod당 최대 500m CPU 사용 가능
- D) 클러스터 전체 CPU 제한

<details>
<summary>정답 보기</summary>

**정답: B) NodePool 전체에서 최대 500 vCPU까지 프로비저닝 가능**

**설명:**
NodePool의 `limits`는 해당 NodePool이 프로비저닝할 수 있는 총 리소스 양을 제한합니다.

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: compute-optimized
spec:
  limits:
    cpu: 500      # 최대 500 vCPU
    memory: 1Ti   # 최대 1TB 메모리
  template:
    spec:
      requirements:
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c"]
```

이를 통해 비용 폭주를 방지하고 예산을 관리할 수 있습니다.

</details>

### 3. 저사용률 노드를 자동으로 정리하여 비용을 최적화하는 Consolidation 정책은?

- A) `consolidationPolicy: WhenEmpty`
- B) `consolidationPolicy: WhenEmptyOrUnderutilized`
- C) `consolidationPolicy: Always`
- D) `consolidationPolicy: Aggressive`

<details>
<summary>정답 보기</summary>

**정답: B) `consolidationPolicy: WhenEmptyOrUnderutilized`**

**설명:**
`WhenEmptyOrUnderutilized` 정책은 빈 노드와 저사용률 노드 모두를 통합 대상으로 합니다.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

**정책 비교:**
- `WhenEmpty`: 빈 노드만 제거 (보수적, 안정성 우선)
- `WhenEmptyOrUnderutilized`: 적극적인 비용 최적화

비용 절감 효과: 저사용률 노드를 통합하여 전체 노드 수를 줄이고 인프라 비용 절감

</details>

### 4. Savings Plans를 EKS Auto Mode와 함께 사용할 때 권장되는 접근 방식은?

- A) Compute Savings Plans로 인스턴스 패밀리 유연성 확보
- B) EC2 Instance Savings Plans로 특정 인스턴스 타입 고정
- C) Reserved Instances만 사용
- D) Savings Plans 사용하지 않음

<details>
<summary>정답 보기</summary>

**정답: A) Compute Savings Plans로 인스턴스 패밀리 유연성 확보**

**설명:**
Auto Mode는 워크로드에 따라 다양한 인스턴스 타입을 사용하므로, Compute Savings Plans가 가장 적합합니다.

**Savings Plans 비교:**
| 유형 | 유연성 | 할인율 |
|------|--------|--------|
| Compute Savings Plans | 인스턴스 패밀리, 크기, 리전, OS 유연 | 최대 66% |
| EC2 Instance Savings Plans | 특정 인스턴스 패밀리 고정 | 최대 72% |

```
권장 전략:
1. 기본 워크로드 양 분석 (3개월 기준)
2. 최소 사용량의 70%를 Compute Savings Plans로 커버
3. 나머지는 Spot/On-Demand로 유연하게 운영
```

</details>

### 5. Kubecost를 사용한 비용 분석에서 Pod 수준 비용 할당을 위해 필요한 것은?

- A) 별도 설정 없이 자동 지원
- B) Pod에 cost-center 레이블 추가
- C) Kubecost 에이전트 설치 및 클러스터 통합
- D) AWS Cost Explorer만으로 충분

<details>
<summary>정답 보기</summary>

**정답: C) Kubecost 에이전트 설치 및 클러스터 통합**

**설명:**
Kubecost는 Kubernetes 네이티브 비용 모니터링 도구로, 상세한 비용 분석을 제공합니다.

```bash
# Kubecost 설치 (Helm)
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
    --namespace kubecost \
    --create-namespace
```

Kubecost 기능:
- 네임스페이스/워크로드별 비용 분석
- 리소스 효율성 권장 사항
- 예산 알림 설정
- AWS 통합으로 실제 비용 정확도 향상

</details>

### 6. 리소스 요청(requests) 설정 시 오버프로비저닝을 방지하기 위한 모범 사례는?

- A) 항상 limits와 requests를 동일하게 설정
- B) 실제 사용량 기반 VPA 권장값 참고
- C) requests를 가능한 높게 설정
- D) requests 설정 생략

<details>
<summary>정답 보기</summary>

**정답: B) 실제 사용량 기반 VPA 권장값 참고**

**설명:**
Vertical Pod Autoscaler(VPA)를 사용하여 실제 리소스 사용량을 분석하고 적절한 requests 값을 설정합니다.

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: my-app-vpa
spec:
  targetRef:
    apiVersion: "apps/v1"
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # 권장값만 제공, 자동 적용 안함
```

권장값 확인:
```bash
kubectl describe vpa my-app-vpa
```

이를 통해:
- 오버프로비저닝 방지 (비용 절감)
- 언더프로비저닝 방지 (성능 보장)

</details>

### 7. 다중 티어 워크로드에서 비용 효율적인 NodePool 분리 전략은?

- A) 모든 워크로드를 단일 NodePool에 배치
- B) 티어별 NodePool 분리 (프론트엔드/API/배치/ML)
- C) 인스턴스 크기별 NodePool 분리
- D) 가용영역별 NodePool 분리

<details>
<summary>정답 보기</summary>

**정답: B) 티어별 NodePool 분리 (프론트엔드/API/배치/ML)**

**설명:**
워크로드 특성에 맞게 NodePool을 분리하면 최적의 비용/성능 균형을 달성할 수 있습니다.

| 티어 | 전략 | 예상 절감률 |
|------|------|------------|
| 프론트엔드 | On-Demand + Graviton | ~20% |
| API | Spot 혼합 + Graviton | ~40% |
| 배치 | Spot 전용 + 다양화 | ~70% |
| ML | 적절한 인스턴스 크기 선택 | ~30% |

```yaml
# 배치 티어 예시 - 최대 비용 절감
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]  # Spot 전용
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]  # Graviton 포함
```

</details>

### 8. AWS Cost Explorer에서 EKS Auto Mode 비용을 태그별로 분류하려면?

- A) 자동으로 모든 태그가 적용됨
- B) NodeClass에 tags 필드 설정 필요
- C) AWS Organizations에서 설정
- D) 태그 기반 분류 불가능

<details>
<summary>정답 보기</summary>

**정답: B) NodeClass에 tags 필드 설정 필요**

**설명:**
NodeClass의 tags 필드를 통해 프로비저닝되는 노드에 비용 할당 태그를 적용합니다.

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: production-nodeclass
spec:
  tags:
    Environment: production
    Team: platform
    CostCenter: engineering-001
    Project: kubernetes-platform
```

AWS Cost Explorer 설정:
1. Billing Console에서 Cost Allocation Tags 활성화
2. 원하는 태그 키 선택
3. 24시간 후 Cost Explorer에서 확인 가능

</details>
