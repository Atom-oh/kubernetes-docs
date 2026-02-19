# EKS Auto Mode 노드 수명주기 퀴즈

> **관련 문서**: [노드 수명주기](../../eks-auto-mode/07-node-lifecycle.md)

## 객관식 문제

### 1. NodePool에서 노드를 주기적으로 교체하기 위한 설정 필드 이름은 무엇인가요?

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>정답 보기</summary>

**정답: C) `expireAfter`**

**설명:**
`expireAfter` 필드를 사용하면 노드의 최대 수명을 설정하여 보안 패치나 AMI 업데이트를 위해 노드를 주기적으로 교체할 수 있습니다.

```yaml
spec:
  template:
    spec:
      # 노드 최대 수명 설정
      expireAfter: 168h  # 7일 후 자동 교체
```

**일반적인 설정값:**
- 개발 환경: 336h (14일)
- 스테이징: 168h (7일)
- 프로덕션: 72h ~ 168h (3-7일)
- 보안 중요 환경: 24h ~ 48h (1-2일)

</details>

### 2. expireAfter가 설정된 노드가 만료되면 어떤 일이 발생하나요?

- A) 노드가 즉시 삭제됨
- B) 노드가 cordon되고 drain 후 삭제됨
- C) 관리자에게 알림만 전송됨
- D) 노드가 자동으로 재부팅됨

<details>
<summary>정답 보기</summary>

**정답: B) 노드가 cordon되고 drain 후 삭제됨**

**설명:**
노드가 만료되면 Karpenter가 graceful한 프로세스를 실행합니다:

1. **Cordon**: 새 Pod 스케줄링 차단
2. **Drain**: 기존 Pod를 다른 노드로 이동
3. **Delete**: EC2 인스턴스 종료

이 과정에서 PodDisruptionBudget과 Disruption Budget이 존중됩니다.

```yaml
disruption:
  budgets:
    # 만료로 인한 교체도 이 budget의 제한을 받음
    - nodes: "10%"
```

</details>

### 3. AL2023과 Bottlerocket AMI 중 더 빠른 부팅 시간을 제공하는 것은?

- A) AL2023
- B) Bottlerocket
- C) 동일함
- D) 인스턴스 타입에 따라 다름

<details>
<summary>정답 보기</summary>

**정답: B) Bottlerocket**

**설명:**
Bottlerocket은 컨테이너 워크로드에 최적화된 OS로, AL2023보다 빠른 부팅 시간을 제공합니다.

**부팅 시간 비교:**
| AMI | 부팅 시간 | 특징 |
|-----|----------|------|
| AL2023 | 20-40초 | 범용 패키지, 유연성 |
| Bottlerocket | 15-25초 | 컨테이너 전용, 최소 OS |

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: fast-boot
spec:
  amiFamily: Bottlerocket  # 빠른 부팅
```

Bottlerocket 추가 장점:
- 불변 루트 파일 시스템
- 자동 보안 업데이트
- 작은 공격 표면

</details>

### 4. AMI 업데이트가 발생했을 때 기존 노드에서 Drift가 감지되면 어떤 일이 발생하나요?

- A) 노드가 자동으로 인플레이스 업데이트됨
- B) 새 AMI로 노드가 순차적으로 교체됨
- C) 관리자 승인 후 교체됨
- D) 아무 일도 발생하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) 새 AMI로 노드가 순차적으로 교체됨**

**설명:**
EKS Auto Mode는 새 AMI가 사용 가능해지면 Drift를 감지하고 노드를 순차적으로 교체합니다.

**Drift 감지 조건:**
- 새로운 EKS 최적화 AMI 릴리스
- NodeClass의 amiFamily 변경
- 보안 그룹 변경
- 서브넷 설정 변경

```yaml
# Drift로 인한 교체도 Disruption Budget 적용
disruption:
  budgets:
    - nodes: "10%"  # 한 번에 10%만 교체
```

</details>

### 5. 노드 freshness(신선도)를 위해 expireAfter를 짧게 설정하면 발생할 수 있는 trade-off는?

- A) 비용 절감
- B) 노드 교체 빈도 증가로 인한 일시적 성능 저하 가능성
- C) 보안 취약점 증가
- D) 클러스터 안정성 향상

<details>
<summary>정답 보기</summary>

**정답: B) 노드 교체 빈도 증가로 인한 일시적 성능 저하 가능성**

**설명:**
짧은 expireAfter는 보안을 강화하지만 다음과 같은 trade-off가 있습니다:

**장점:**
- 최신 보안 패치 적용
- AMI 업데이트 빠른 적용
- 노드 드리프트 방지

**단점:**
- 노드 교체 중 일시적 용량 감소
- 더 많은 Pod 재스케줄링
- 스팟 인스턴스의 경우 추가 인터럽트 가능성

**권장 사항:**
```yaml
# 균형 잡힌 설정
spec:
  template:
    spec:
      expireAfter: 168h  # 7일
  disruption:
    budgets:
      - nodes: "10%"  # 동시 교체 제한
```

</details>

### 6. Consolidation과 Expiration이 동시에 트리거되면 어떤 것이 우선인가요?

- A) Consolidation이 항상 우선
- B) Expiration이 항상 우선
- C) 둘 중 노드 교체 조건에 먼저 도달한 것이 실행
- D) 관리자가 선택해야 함

<details>
<summary>정답 보기</summary>

**정답: C) 둘 중 노드 교체 조건에 먼저 도달한 것이 실행**

**설명:**
Karpenter는 여러 disruption 이유를 독립적으로 평가하고, 조건에 맞으면 실행합니다.

**Disruption 우선순위 (일반적인 평가 순서):**
1. **Drift**: 설정 변경이나 AMI 업데이트 감지
2. **Expiration**: expireAfter 시간 초과
3. **Consolidation**: 저사용률 또는 빈 노드

```yaml
# 예: 5일 된 저사용률 노드
# - expireAfter: 7일 -> 아직 만료 안됨
# - consolidation 조건 충족 -> Consolidation으로 교체

# 예: 8일 된 정상 사용률 노드
# - expireAfter: 7일 -> 만료됨
# - Expiration으로 교체
```

</details>

### 7. 보안 패치 적용을 위해 노드를 즉시 교체해야 할 때 사용하는 방법은?

- A) expireAfter를 0으로 설정
- B) 노드에 Drift 어노테이션 추가
- C) NodeClass 업데이트로 Drift 트리거 또는 노드 drain
- D) 클러스터 재시작

<details>
<summary>정답 보기</summary>

**정답: C) NodeClass 업데이트로 Drift 트리거 또는 노드 drain**

**설명:**
긴급 보안 패치 적용 방법:

**방법 1: NodeClass 업데이트 (권장)**
```yaml
# tags나 설정 변경으로 drift 트리거
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: default
spec:
  tags:
    SecurityPatch: "2025-02-19"  # 태그 변경으로 drift
```

**방법 2: 수동 drain**
```bash
# 특정 노드 drain
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 노드 삭제 (Auto Mode가 새 노드 프로비저닝)
kubectl delete node <node-name>
```

**방법 3: Rolling 교체**
```bash
# 모든 노드를 순차적으로 교체
kubectl delete nodes -l karpenter.sh/nodepool=general-purpose
```

</details>

### 8. expireAfter를 Never로 설정하면 어떤 동작이 되나요?

- A) 노드가 즉시 만료됨
- B) 시간 기반 자동 교체가 비활성화됨
- C) 설정이 무효화되고 기본값 적용
- D) 에러 발생

<details>
<summary>정답 보기</summary>

**정답: B) 시간 기반 자동 교체가 비활성화됨**

**설명:**
`expireAfter: Never`를 설정하면 시간 기반 노드 만료가 비활성화됩니다.

```yaml
spec:
  template:
    spec:
      expireAfter: Never  # 시간 기반 만료 비활성화
```

**주의사항:**
- Drift와 Consolidation은 여전히 작동
- 보안 패치 적용이 지연될 수 있음
- 장기 실행 워크로드에만 권장

**권장 사용 사례:**
- 상태 저장 워크로드 (데이터베이스)
- 매우 긴 실행 작업
- 수동 유지보수 일정이 있는 환경

</details>
