# EKS Auto Mode 노드 수명 주기 퀴즈

> **관련 문서**: [노드 수명 주기](../../eks-auto-mode/07-node-lifecycle.md)
> **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

### 1. 새로 생성되는 NodeClaim의 나이 기준 만료를 지정하는 NodePool 필드는 무엇인가요?

- A) `nodeLifetime`
- B) `maxAge`
- C) `expireAfter`
- D) `rotationPeriod`

<details>
<summary>정답 보기</summary>

**정답: C) `expireAfter`**

**설명:**
`spec.template.spec` 아래의 필드입니다. Auto Mode 기본값은 문서상 336h이며 pool에서 생략한 termination grace는 NodeClaim에 24h로 적용됩니다. 관리형 인스턴스 최대 수명 21일은 최소 uptime 보장이 아닙니다. Template 변경이 기존 claim 값을 덮어쓰지는 않습니다. 이전 개발 336h, 스테이징 168h, 프로덕션 72–168h, 보안 24–48h는 미검증 정책 예시이며 필수 규정 간격이 아닙니다.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 2. Auto Mode NodeClaim이 만료될 때 맞는 설명은 무엇인가요?

- A) 항상 즉시 사라짐
- B) 대체 노드의 사전 Ready 보장 없이 termination/drain 시작
- C) 알림만 전송
- D) 같은 인스턴스 재부팅

<details>
<summary>정답 보기</summary>

**정답: B) 대체 노드의 사전 Ready 보장 없이 termination/drain 시작**

**설명:**
Expiration은 forceful trigger이며 NodePool disruption budget으로 속도가 제한되지 않습니다. Controller는 일반적인 신규 배치를 막고 drain/정리를 시도합니다. PDB·Pod annotation이 축출에 영향을 줄 수 있지만 termination grace·AWS 최대 수명이 보호를 제한합니다. 따라서 `nodes: 10%`는 expiration을 통제된 10% rolling update로 만들지 않습니다. 대체 용량·애플리케이션 readiness는 별도 증거가 필요합니다.

</details>

### 3. EKS Auto Mode OS 선택에 관한 올바른 설명은 무엇인가요?

- A) `amiFamily`로 AL2023 선택
- B) AWS가 Bottlerocket 변형을 관리하며 NodeClass는 AMI family 선택기가 아님
- C) `amiSelectorTerms`로 커스텀 AMI 선택
- D) GPU에는 사용자 관리 AL2023 필수

<details>
<summary>정답 보기</summary>

**정답: B) AWS가 Bottlerocket 변형을 관리하며 NodeClass는 AMI family 선택기가 아님**

**설명:**
Auto Mode에는 해당 커스텀 AMI 인터페이스나 SSH/SSM 접근이 없습니다. 관리형 이미지로 가속 워크로드도 지원합니다. 이전 퀴즈의 AL2023 20–40초/Bottlerocket 15–25초와 본문의 40–60초/20–30초·20–40초에는 확인된 실측 출처가 없으므로 보편적인 부팅 속도 순위가 아닙니다. 범용 OS 비교와 Auto Mode 관리형 인터페이스를 구분하세요.

</details>

### 4. 관리형 Auto Mode 이미지 갱신으로 기존 NodeClaim이 drift 상태가 되면 어떤 일이 가능한가요?

- A) 모든 인스턴스가 즉시 제자리 패치
- B) 적격 claim이 해당 graceful-disruption 제어 아래 교체될 수 있음
- C) 임의 Node tag가 바뀔 때까지 아무 동작 없음
- D) 모든 노드를 동시에 삭제해야 함

<details>
<summary>정답 보기</summary>

**정답: B) 적격 claim이 해당 graceful-disruption 제어 아래 교체될 수 있음**

**설명:**
`Drifted` condition, reason과 현재 정책을 확인합니다. 10% budget은 올림하며 다른 활성 상한과 결합하므로 한 개씩 교체한다는 뜻은 아닙니다. 배치/PDB 제약과 grace 의미도 고려합니다. 모든 NodePool 변경이 drift를 유발하지는 않습니다. 호환 requirement 확장, weight/limit/disruption 같은 동작 설정은 desired-state drift와 다릅니다. `amiFamily`는 Auto Mode 필드가 아닙니다.

</details>

### 5. 짧은 expiration 정책은 어떤 trade-off를 만들 수 있나요?

- A) 비용 감소 보장
- B) 더 많은 재배치·warm-up/복구 작업과 가용성 영향 가능성
- C) CVE 증가 보장
- D) 안정성 보장

<details>
<summary>정답 보기</summary>

**정답: B) 더 많은 재배치·warm-up/복구 작업과 가용성 영향 가능성**

**설명:**
잦은 교체는 관리형 이미지 rollout 기회를 늘릴 수 있지만 필요한 패치의 가용성이나 모든 워크로드 취약점 수정을 입증하지는 않습니다. 용량·image pull·checkpoint·복구 비용을 더할 수 있습니다. EC2 Spot 인스턴스의 interruption 확률 자체를 높이지는 않습니다. 애플리케이션 복구와 node grace를 별도로 평가하며 NodePool budget은 expiration 속도를 제한하지 않습니다.
```yaml
# Fragment of NodePool spec.template.spec
expireAfter: 168h
terminationGracePeriod: 24h
```


</details>

### 6. Consolidation과 expiration 조건이 겹칠 때 어떻게 이해해야 하나요?

- A) Consolidation이 항상 우선
- B) Expiration은 항상 drift·consolidation 이후 대기
- C) Graceful 작업과 forceful expiration은 다른 제어 경로이며 보편적인 전체 순서는 없음
- D) 관리자가 모든 작업을 수동 선택

<details>
<summary>정답 보기</summary>

**정답: C) Graceful 작업과 forceful expiration은 다른 제어 경로이며 보편적인 전체 순서는 없음**

**설명:**
Graceful controller는 consolidation보다 drift를 먼저 평가하지만 expiration은 별도 forceful 경로입니다. 전체 `drift > expiration > consolidation`이나 먼저 조건을 만족한 작업 승리는 문서화된 보장이 아닙니다. 5일 된 노드가 7일 만료 전에 consolidate될 수 있고, 8일 된 만료 claim은 충분히 활용 중이어도 종료를 시작할 수 있습니다.

</details>

### 7. 긴급 노드 패치 대응의 올바른 시작점은 무엇인가요?

- A) 모든 pool의 `expireAfter`를 0으로 설정
- B) 임의 drift annotation 생성
- C) 관리형 수정 확인·영향 claim 식별·health 확인을 포함한 단일 리소스 절차
- D) Pool 일괄 삭제를 순차 교체라고 부름

<details>
<summary>정답 보기</summary>

**정답: C) 관리형 수정 확인·영향 claim 식별·health 확인을 포함한 단일 리소스 절차**

**설명:**
관리형 이미지·수정 가용성을 확인한 뒤 대상 context에서 단일 NodeClaim UID·node mapping·PDB·영구 상태·여유/확보 가능 용량을 확인합니다. 적합하면 관리형 drift를 사용하며 수동 교체는 별도로 검토하고 다음 노드 전에 health·이미지를 재확인합니다. 장식용 `SecurityPatch` tag는 패치 trigger 보장이 아니고 label 일괄 삭제는 rolling update가 아닙니다. `--delete-emptydir-data`는 local 데이터를 버릴 수 있습니다.

연결된 본문에서 `KUBE_CONTEXT`를 설정합니다. 아래는 증거만 수집하는 명령입니다.

```bash
: "${NODECLAIM_NAME:?Select one NodeClaim for review}"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodeclaim "$NODECLAIM_NAME" -o json |
  jq '{name:.metadata.name,uid:.metadata.uid,node:.status.nodeName,
       pool:.metadata.labels["karpenter.sh/nodepool"],imageID:.status.imageID,
       expireAfter:.spec.expireAfter,terminationGracePeriod:.spec.terminationGracePeriod,
       conditions:[.status.conditions[]?|{type,status,reason}]}'
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pdb -A -o json |
  jq '[.items[]|{namespace:.metadata.namespace,name:.metadata.name,
       observedGeneration:.status.observedGeneration,generation:.metadata.generation,
       currentHealthy:.status.currentHealthy,desiredHealthy:.status.desiredHealthy,
       disruptionsAllowed:.status.disruptionsAllowed}]'
```


</details>

### 8. Upstream `expireAfter: Never`로 Auto Mode 노드를 무기한 보존할 수 있나요?

- A) 모든 maintenance·interruption까지 막고 가능
- B) 아니요. Auto Mode 관리형 인스턴스 최대 21일은 계속 적용
- C) Pod에 PDB가 있으면 가능
- D) 모든 stateful 워크로드에서 가능

<details>
<summary>정답 보기</summary>

**정답: B) 아니요. Auto Mode 관리형 인스턴스 최대 21일은 계속 적용**

**설명:**
Upstream 문법은 Auto Mode 서비스 수명을 무효화하는 권한이 아닙니다. Auto Mode 데이터베이스·장기 작업을 한 인스턴스에서 영구 실행하기 위해 `Never`를 권장하거나, 검증 없이 특정 admission 응답을 보장해서는 안 됩니다. Checkpoint·외부 영구 스토리지·복구를 설계하세요. Drift·interruption 등 다른 작업으로 더 일찍 종료될 수도 있습니다.

</details>

## 참고 자료

- [Auto Mode NodePool defaults](https://docs.aws.amazon.com/eks/latest/userguide/create-node-pool.html)
- [Auto Mode maximum lifetime](https://docs.aws.amazon.com/eks/latest/userguide/auto-security.html)
- [Disruption and drift](https://karpenter.sh/v1.14/concepts/disruption/)
