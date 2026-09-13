# EKS Auto Mode 운영 퀴즈

> **관련 문서**: [운영 및 관리](../../eks-auto-mode/05-operations.md)
> **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

### 1. 서울 업무 시간의 해당 자발적 NodePool 중단을 막는 예약 설정은 무엇인가요?

- A) `nodes: "100%"`
- B) 정확한 UTC 시간 창과 `nodes: "0"`
- C) `consolidateAfter: 0s`
- D) `consolidationPolicy: Never`

<details>
<summary>정답 보기</summary>

**정답: B) 정확한 UTC 시간 창과 `nodes: "0"`**

**설명:**
0 budget은 활성 구간의 consolidation·drift 등 해당 graceful 작업을 막습니다. EC2 interruption, expiration, repair나 모든 수동 삭제를 막지는 않습니다. 아래 매일 UTC 00:00 시작·9시간 구간은 서울 평일 09:00–18:00입니다. 매시간 `9-18` schedule에 9시간 duration을 주면 창이 반복해서 중첩됩니다.
```yaml
# Fragment of NodePool spec.disruption
budgets:
  - nodes: "10%"
  - nodes: "0"
    schedule: "0 0 * * mon-fri"
    duration: 9h
```


</details>

### 2. 하나의 scale 가능한 controller에 속한 복제본 6개를 선택하는 PDB에서 `minAvailable: "80%"`는 무엇을 뜻하나요?

- A) 최대 80%만 실행 가능
- B) 올림 계산 후 정상 복제본 5개를 유지하는 축출 결정
- C) 각 Pod의 보존 확률 80%
- D) 80초 동안 Pod 보호

<details>
<summary>정답 보기</summary>

**정답: B) 올림 계산 후 정상 복제본 5개를 유지하는 축출 결정**

**설명:**
Controller는 6개의 80%를 올림해 healthy/Ready 복제본 5개를 요구합니다. Eviction API 결정을 제한하며 모든 장애·직접 삭제·복제본 생성을 통제하지는 않습니다. `minAvailable`과 `maxUnavailable`은 의미가 다른 선택지이며 함께 설정하지 않습니다. 본문의 복제본 5개·`minAvailable: 3`은 최대 2개 축출을 허용하므로 `maxUnavailable: 1`과 다릅니다.
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
  namespace: ops-lab
spec:
  minAvailable: "80%"
  selector:
    matchLabels:
      app: web-app
```

`disruptionsAllowed`가 0이어도 의도한 정상 상태일 수 있습니다. 위반이라고 판단하기 전에 `observedGeneration`, `currentHealthy`, `desiredHealthy`를 확인하세요.

</details>

### 3. Auto Mode 노드의 프로비저닝 수명 주기를 진단하는 데 도움이 되는 리소스는 무엇인가요?

- A) 애플리케이션 로그만
- B) NodeClaim condition과 관련 NodePool/NodeClass 증거
- C) EC2 콘솔만
- D) CloudWatch widget만

<details>
<summary>정답 보기</summary>

**정답: B) NodeClaim condition과 관련 NodePool/NodeClass 증거**

**설명:**
Condition과 reason을 읽고 증거에 따라 배치 제약, NodeClass readiness, IAM·네트워크 구성을 조사합니다. NodeClaim에는 일반적인 `.status.phase` 필드가 없습니다. 아래는 연결된 본문에서 검토한 `KUBE_CONTEXT`를 사용하며 전체 객체 대신 필요한 진단 필드를 선택합니다.
```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaims -o json |
  jq '[.items[] | {name: .metadata.name, uid: .metadata.uid, node: .status.nodeName,
      pool: .metadata.labels["karpenter.sh/nodepool"], createdAt: .metadata.creationTimestamp,
      expireAfter: .spec.expireAfter, terminationGracePeriod: .spec.terminationGracePeriod,
      imageID: .status.imageID,
      conditions: [.status.conditions[]? | {type,status,reason,lastTransitionTime,observedGeneration}]}]'
```


</details>

### 4. 인식되는 do-not-disrupt annotation은 무엇인가요?

- A) `kubernetes.io/do-not-disrupt: "true"`
- B) `karpenter.sh/do-not-disrupt: "true"`
- C) `eks.amazonaws.com/no-disrupt: "true"`
- D) `node.kubernetes.io/exclude-disruption: "true"`

<details>
<summary>정답 보기</summary>

**정답: B) `karpenter.sh/do-not-disrupt: "true"`**

**설명:**
Pod와 Node에 적용할 때 범위가 다릅니다. Pod annotation은 해당 Pod의 자발적 축출과 노드 consolidation을 막습니다. NodeClaim termination grace period가 있으면 해당 Pod가 있는 노드도 drift 대상이 될 수 있고 최종 drain 시간도 제한됩니다. Node annotation은 노드를 자발적 중단에서 제외합니다. 어느 쪽도 expiration, interruption, repair나 수동 삭제에 대한 무기한 보장이 아닙니다. Auto Mode에는 자체 기본 termination grace period가 있으므로 미설정이라고 가정하지 마세요.
```yaml
# Metadata fragment for a deliberately selected Pod or Node.
# Review the different Pod/Node semantics before applying.
metadata:
  annotations:
    karpenter.sh/do-not-disrupt: "true"
```

Metadata 조각은 완전한 실행용 Pod가 아닙니다. 실제 워크로드에 적용하기 전에 복구·annotation 제거 계획을 정하세요.

</details>

### 5. Auto Mode 운영에 유용한 증거를 얻는 모니터링 방법은 무엇인가요?

- A) `kubectl top`만 사용
- B) 구성한 collector·로그 전송과 Kubernetes condition·워크로드 신호 결합
- C) EC2 콘솔만 사용
- D) 별도 수집 없이 모든 CloudWatch 메트릭이 있다고 가정

<details>
<summary>정답 보기</summary>

**정답: B) 구성한 collector·로그 전송과 Kubernetes condition·워크로드 신호 결합**

**설명:**
Container Insights, EKS control-plane 메트릭, kube-state-metrics/node-exporter와 관리형 Auto Mode 컴포넌트 로그는 전제 조건이 다릅니다. 각 publisher와 dimension을 확인하세요. `kubectl top`에는 정상 metrics API가 필요하며 오류가 metrics-server 부재를 입증하지는 않습니다. 관리형 컴포넌트 로그에는 별도 Vended Logs delivery가 필요합니다. 배치 지연·애플리케이션 가용성은 적합한 계측이 필요하며 Container Insights 활성화만으로 제안된 모든 신호가 자동 생성되지는 않습니다.

</details>

### 6. 나이 기준 expiration 자격을 설정하는 NodePool 필드는 무엇인가요?

- A) `autoUpdate: true`
- B) `expireAfter`
- C) `updatePolicy: Rolling`
- D) `refreshInterval: 24h`

<details>
<summary>정답 보기</summary>

**정답: B) `expireAfter`**

**설명:**
예제는 NodeClaim이 168시간 후 expiration 대상이 되게 하고 termination 단계는 별도로 제한합니다. 중단 없는 7일 uptime, 정확한 시각의 교체나 그 시각까지 최신 보안 patch를 보장하지 않습니다. Drift/consolidation/interruption으로 더 일찍 중단될 수 있고 template 변경이 기존 NodeClaim 값을 덮어쓰지도 않습니다. Auto Mode 기본값·최대 수명과 애플리케이션 복구 요구를 확인하세요.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 7. 여러 NodePool disruption budget이 동시에 적용되면 어떻게 계산하나요?

- A) 가장 최근 예약 항목이 이전 항목을 덮어씀
- B) 가장 작은 허용량 적용
- C) 백분율을 더함
- D) 교체 노드 개수를 보장함

<details>
<summary>정답 보기</summary>

**정답: B) 가장 작은 허용량 적용**

**설명:**
항상 적용되는 10% 상한은 예약된 30% budget으로 완화할 수 없습니다. 본문은 30%에서 시작해 서울 평일 10%, 업무 시간 1개와 명시적인 UTC 월간 freeze를 추가합니다. 그 외 모두 정상인 노드 20개에서 각각 6개·2개·1개·0개를 허용합니다. 삭제 중·NotReady 노드가 허용량을 줄이며 모든 forceful 중단을 이 budget으로 제어하지는 않습니다.
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
  budgets:
  - nodes: 30%
  - nodes: 10%
    schedule: 0 15 * * sun-thu
    duration: 24h
  - nodes: '1'
    schedule: 0 0 * * mon-fri
    duration: 9h
  - nodes: '0'
    schedule: 0 0 1 * *
    duration: 24h
```


</details>

### 8. Publisher가 구성됐을 때 노드 관련 운영 알림을 정의하는 데 유용한 신호는 무엇인가요?

- A) EC2 상태만
- B) 배치 backlog·측정한 프로비저닝 지연·워크로드 가용성
- C) 비용만
- D) 네트워크 트래픽만

<details>
<summary>정답 보기</summary>

**정답: B) 배치 backlog·측정한 프로비저닝 지연·워크로드 가용성**

**설명:**
각 알림에 publisher, dimension, 통계, 시간 구간과 애플리케이션 목표를 정합니다. Pending은 unschedulable과 같은 뜻이 아닙니다. 아래 원 수치는 검증되지 않은 계획용 예시로 보존하며, 실측 정상 범위·Auto Mode 기본값·보장된 Container Insights 메트릭이 아닙니다.

| 신호 | 이전 계획 예시 | 이전 알림 예시 |
|------|----------------|----------------|
| Pending Pod | 0–5 | 5분간 >10 |
| 노드 프로비저닝 시간 | <90초 | >120초 |
| 워크로드 가용성 | >99.9% | <99.5% |
| API 응답 시간 | <200ms | >500ms |

메트릭 부재나 오래된 collector를 오류 0과 구분해야 합니다. 본문은 메트릭 이름을 만들어내지 않고 실제 catalog로 로컬 CloudWatch dashboard 정의를 생성합니다.

</details>

## 참고 자료

- [Karpenter disruption controls](https://karpenter.sh/v1.14/concepts/disruption/)
- [Kubernetes PDB semantics](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Auto Mode NodePools](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
