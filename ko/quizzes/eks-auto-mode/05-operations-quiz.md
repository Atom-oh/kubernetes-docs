# EKS Auto Mode 운영 퀴즈

> **관련 문서**: [운영](../../eks-auto-mode/05-operations.md)

## 객관식 문제

### 1. NodePool의 Disruption Budget에서 업무 시간에 노드 중단을 최소화하는 설정은 무엇인가요?

- A) `nodes: "100%"`
- B) `nodes: "0"` with schedule
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>정답 보기</summary>

**정답: B) `nodes: "0"` with schedule**

**설명:**
Disruption Budget의 schedule과 함께 `nodes: "0"`을 설정하면 특정 시간대에 노드 중단을 완전히 방지할 수 있습니다.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # 기본: 전체 노드의 10%만 동시 중단
    - nodes: "10%"

    # 업무 시간: 중단 금지
    - nodes: "0"
      schedule: "0 9-18 * * mon-fri"  # 월-금 9-18시
      duration: 9h
```

</details>

### 2. PodDisruptionBudget(PDB)에서 `minAvailable: 80%`가 의미하는 것은?

- A) 최대 80%의 Pod만 실행
- B) 최소 80%의 Pod가 항상 실행 중이어야 함
- C) 80% 확률로 Pod 유지
- D) 80초 동안 Pod 보호

<details>
<summary>정답 보기</summary>

**정답: B) 최소 80%의 Pod가 항상 실행 중이어야 함**

**설명:**
PDB의 `minAvailable`은 항상 실행 중이어야 하는 최소 Pod 수 또는 비율을 지정합니다.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: web
```

대안으로 `maxUnavailable`을 사용할 수도 있습니다:
```yaml
spec:
  maxUnavailable: 1  # 동시에 1개의 Pod만 중단 가능
```

</details>

### 3. Auto Mode 노드의 문제를 진단할 때 가장 먼저 확인해야 하는 리소스는?

- A) Pod 로그
- B) NodeClaim 상태
- C) EC2 콘솔
- D) CloudWatch 메트릭

<details>
<summary>정답 보기</summary>

**정답: B) NodeClaim 상태**

**설명:**
NodeClaim은 노드 프로비저닝 과정과 상태를 추적하는 핵심 리소스입니다.

```bash
# NodeClaim 상태 확인
kubectl get nodeclaims

# 상세 정보 및 이벤트 확인
kubectl describe nodeclaim <name>

# 프로비저닝 실패 원인 확인
kubectl get nodeclaims -o yaml | grep -A 10 status
```

일반적인 문제 진단 순서:
1. NodeClaim 상태 확인
2. NodePool 구성 검토
3. IAM 역할/정책 확인
4. 서브넷/보안 그룹 검증

</details>

### 4. do-not-disrupt 어노테이션의 올바른 사용법은?

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>정답 보기</summary>

**정답: B) `karpenter.sh/do-not-disrupt: "true"`**

**설명:**
이 어노테이션을 Pod나 Node에 추가하면 Karpenter가 해당 노드를 consolidation이나 drift 교체 대상에서 제외합니다.

```yaml
# Pod에 적용
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
  annotations:
    karpenter.sh/do-not-disrupt: "true"
spec:
  containers:
    - name: app
      image: myapp:latest

# Node에 적용
kubectl annotate node <node-name> karpenter.sh/do-not-disrupt=true
```

</details>

### 5. Auto Mode 클러스터의 노드 상태를 모니터링하기 위해 권장되는 도구는?

- A) kubectl top nodes만 사용
- B) Container Insights + kubectl 조합
- C) EC2 콘솔에서 직접 확인
- D) AWS CLI만 사용

<details>
<summary>정답 보기</summary>

**정답: B) Container Insights + kubectl 조합**

**설명:**
효과적인 모니터링을 위해 여러 도구를 조합하여 사용합니다.

```bash
# 실시간 모니터링
watch -n 5 'echo "=== Pending Pods ===" && \
kubectl get pods -A --field-selector=status.phase=Pending && \
echo "=== Node Status ===" && kubectl get nodes -o wide'

# 리소스 사용량 확인
kubectl top nodes
kubectl top pods -A

# NodePool 상태 확인
kubectl get nodepools
kubectl describe nodepool <name>
```

Container Insights 메트릭:
- 노드 CPU/메모리 사용률
- Pod 스케줄링 지연 시간
- 컨테이너 재시작 횟수

</details>

### 6. Day-2 운영에서 노드 업데이트를 자동화하기 위해 설정해야 하는 NodePool 필드는?

- A) `autoUpdate: true`
- B) `expireAfter` 설정
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>정답 보기</summary>

**정답: B) `expireAfter` 설정**

**설명:**
`expireAfter`를 설정하면 노드가 지정된 시간 후 자동으로 교체되어 최신 AMI와 보안 패치가 적용됩니다.

```yaml
spec:
  template:
    spec:
      expireAfter: 168h  # 7일 후 자동 교체
```

Day-2 운영 자동화 설정:
- `expireAfter`: 정기적 노드 교체
- `consolidationPolicy`: 비용 최적화
- Disruption Budget: 서비스 영향 최소화

</details>

### 7. 프로덕션 환경에서 롤링 업데이트 시 권장되는 Disruption Budget 설정은?

- A) `nodes: "100%"`로 빠른 업데이트
- B) `nodes: "10%"` 또는 절대값으로 점진적 업데이트
- C) Disruption Budget 비활성화
- D) `nodes: "50%"`로 중간 속도

<details>
<summary>정답 보기</summary>

**정답: B) `nodes: "10%"` 또는 절대값으로 점진적 업데이트**

**설명:**
프로덕션 환경에서는 서비스 영향을 최소화하면서 점진적으로 업데이트해야 합니다.

```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
    # 기본: 10%씩 점진적 교체
    - nodes: "10%"

    # 피크 시간: 더 보수적
    - nodes: "1"
      schedule: "0 9-18 * * mon-fri"
      duration: 9h

    # 유지보수 윈도우: 더 적극적
    - nodes: "30%"
      schedule: "0 2-4 * * sun"
      duration: 2h
```

</details>

### 8. CloudWatch 알람을 설정할 때 Auto Mode 노드 관련 핵심 메트릭은?

- A) EC2 인스턴스 상태만
- B) Pending Pod 수, 노드 프로비저닝 시간, 워크로드 가용성
- C) 비용 메트릭만
- D) 네트워크 트래픽만

<details>
<summary>정답 보기</summary>

**정답: B) Pending Pod 수, 노드 프로비저닝 시간, 워크로드 가용성**

**설명:**
Auto Mode 운영에서 모니터링해야 할 핵심 메트릭:

| 지표 | 정상 범위 | 알람 조건 |
|------|----------|----------|
| Pending Pod 수 | 0-5 | > 10 for 5분 |
| 노드 프로비저닝 시간 | < 90초 | > 120초 |
| 워크로드 가용성 | > 99.9% | < 99.5% |
| API 응답 시간 | < 200ms | > 500ms |

CloudWatch Container Insights를 활성화하여 이러한 메트릭을 자동으로 수집할 수 있습니다.

</details>
