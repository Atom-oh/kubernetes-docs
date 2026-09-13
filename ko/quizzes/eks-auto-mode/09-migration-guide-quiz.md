# EKS Auto Mode 마이그레이션 가이드 퀴즈

> **관련 문서**: [마이그레이션 가이드](../../eks-auto-mode/09-migration-guide.md)
> **마지막 업데이트**: 2026년 9월 12일

## 객관식 문제

### 1. 이전 용량을 활성화하거나 제거하기 전에 무엇을 해야 하나요?

- A) 기존 node group 삭제
- B) Workload·의존성·소유권·복구 요구 인벤토리
- C) 모든 Pod drain
- D) 같은 인스턴스 이름이면 호환된다고 가정

<details>
<summary>정답 보기</summary>

**정답: B) Workload·의존성·소유권·복구 요구 인벤토리**

**설명:**
계정·cluster·old group identity를 고정한 뒤 placement·data·IAM·network·controller·cost·app health를 조사합니다. 축소/삭제 전에 각 wave를 검증하며 마지막 검증 단계가 최초 health check는 아닙니다. 본문에서 아래 명령용 private WORK_DIR·KUBE_CONTEXT를 설정합니다.

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s \
  get deployments,statefulsets,daemonsets,jobs,cronjobs -A -o json |
jq '[.items[] | (.spec.template // .spec.jobTemplate.spec.template) as $t |
 {kind,namespace:.metadata.namespace,name:.metadata.name,uid:.metadata.uid,
  nodeSelector:$t.spec.nodeSelector,affinity:$t.spec.affinity,tolerations:$t.spec.tolerations,
  serviceAccountName:$t.spec.serviceAccountName,hostNetwork:$t.spec.hostNetwork,
  pvcNames:[$t.spec.volumes[]?.persistentVolumeClaim.claimName // empty]}]' \
  > "$WORK_DIR/workload-placement.json"
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get pods -A -o json |
jq '[.items[] | {namespace:.metadata.namespace,name:.metadata.name,node:.spec.nodeName,
  phase:.status.phase,deletionTimestamp:.metadata.deletionTimestamp,
  ready:([.status.conditions[]?|select(.type=="Ready")|.status]|first // "NotReported"),
  owners:[.metadata.ownerReferences[]?|{kind,name,controller}]}]' \
  > "$WORK_DIR/pod-state.json"
```


</details>

### 2. 기존 managed node와 Auto Mode를 예측 가능하게 공존시키는 방법은 무엇인가요?

- A) 공존 불가능
- B) Workload별 명시적 placement와 controller 소유권 사용
- C) 별도 cluster만 가능
- D) AWS resource tag만 매칭

<details>
<summary>정답 보기</summary>

**정답: B) Workload별 명시적 placement와 controller 소유권 사용**

**설명:**
정확한 old node-group selector와 Auto pool/compute-type selector로 fleet을 구분합니다. 일반 Karpenter label은 자체 Karpenter도 선택합니다. 의존성이 이전될 때까지 혼합 노드 DNS/agent와 기존 storage/load-balancer controller를 유지하세요. 아래는 Pod spec 조각이며 본문에는 완전한 canary Deployment가 있습니다.

기존 managed group:
```yaml
# Pod template spec fragment
nodeSelector:
  eks.amazonaws.com/nodegroup: REPLACE_WITH_OLD_NODEGROUP
tolerations: []
```

Auto canary:
```yaml
# Pod template spec fragment
nodeSelector:
  karpenter.sh/nodepool: migration-pool
  eks.amazonaws.com/compute-type: auto
tolerations:
- key: migration
  operator: Equal
  value: auto-mode
  effect: NoSchedule
```


</details>

### 3. 이전 위험을 낮추는 순서는 무엇인가요?

- A) 중요 production부터
- B) 대표 저위험 workload부터 점차 중요한 의존성으로
- C) 모두 동시에
- D) 무작위

<details>
<summary>정답 보기</summary>

**정답: B) 대표 저위험 workload부터 점차 중요한 의존성으로**

**설명:**
실제 의존성을 반영한다면 development/staging·비중요 production·중요 production 순서가 유용합니다. 소유 controller/GitOps placement를 변경한 뒤 app 동작·storage·IAM·DNS·traffic을 확인합니다. Soft preference나 임의 `node-type=auto-mode` label은 이전 증거가 아닙니다. Health 실패·불명 시 중단하며 고정 sleep은 검증이 아닙니다.

</details>

### 4. 복구 경로를 보존하는 rollback 순서는 무엇인가요?

- A) 먼저 cluster 삭제·재생성
- B) 호환 old capacity·placement 복원 후 health 검증, 그다음 정확한 Auto 리소스 정리
- C) Auto NodePool 먼저 삭제
- D) Auto Mode만 비활성화

<details>
<summary>정답 보기</summary>

**정답: B) 호환 old capacity·placement 복원 후 health 검증, 그다음 정확한 Auto 리소스 정리**

**설명:**
이전 용량이 Ready가 될 때까지 Auto pool을 유지합니다. 충돌하는 Auto selector를 남기거나 관련 없는 affinity를 지우지 말고 의도한 placement를 검토·복원하세요. Pod뿐 아니라 data·traffic도 확인한 뒤 migration 소유 용량을 정리합니다. NodePool 삭제는 node까지 cascade될 수 있으며 scaling JSON만으로 삭제된 group을 재생성할 수 없습니다. 이는 workload 이전 rollback이지 Kubernetes version rollback이 아닙니다.

</details>

### 5. 기존 managed node group의 desired size를 줄이기 전에 무엇이 필요한가요?

- A) 즉시 0으로 설정
- B) 이전 workload 검증·old 앱 용량 cordon/비움·owner 조율
- C) 항상 절반씩 축소
- D) 5분 대기만

<details>
<summary>정답 보기</summary>

**정답: B) 이전 workload 검증·old 앱 용량 cordon/비움·owner 조율**

**설명:**
MNG scaling 설정 변경은 ASG scale-down을 사용하며 PDB를 따르지 않습니다. 본문은 old-node cordon·active non-DaemonSet Pod를 확인하고 조회 실패 시 중단합니다. System 의존성·Job 결과 export를 검토하고 controller가 old node를 다시 채우지 않도록 합니다. Desired를 절반으로 줄이고 sleep해도 안전성이 입증되지 않으며 원래 IaC/scaling 소유권도 적용됩니다.

</details>

### 6. 이전 중 비용은 어떻게 관측해야 하나요?

- A) 기존 리소스 전체 삭제까지 무시
- B) 현재 node 수를 정확한 청구액으로 사용
- C) 양쪽 fleet/load balancer 비용과 가용성·성능을 함께 추적
- D) Auto Mode가 기존 비용을 모두 자동 제거한다고 가정

<details>
<summary>정답 보기</summary>

**정답: C) 양쪽 fleet/load balancer 비용과 가용성·성능을 함께 추적**

**설명:**
공존 기간에는 양쪽 fleet/traffic 경로에 과금될 수 있습니다. 실제 청구와 구성한 운영 publisher를 사용합니다. 다음 원래 수치는 미검증 계획 예시이며 Auto Mode 기본 메트릭·정상 범위가 아닙니다.

| 신호 | 이전 baseline 예시 | 이전 alert 예시 |
|------|--------------------|-----------------|
| Pending Pod | 0–5 | 5분간 >10 |
| 프로비저닝 시간 | <90초 | >120초 |
| 가용성 | >99.9% | <99.5% |
| API latency | <200ms | >500ms |

Pending은 unschedulable과 같지 않고 Running은 app readiness가 아닙니다. Collector 데이터 부재는 실패 0이 아닙니다.

</details>

### 7. Workload 검증 후 rollback 선택지를 보존하기 위해 미룰 수 있는 작업은 무엇인가요?

- A) 앱 동작 확인
- B) 예상 placement 확인
- C) 기존 node-group 정의 삭제
- D) Data·controller health 확인

<details>
<summary>정답 보기</summary>

**정답: C) 기존 node-group 정의 삭제**

**설명:**
정한 안정화 기간 동안 old 정의/설정을 보존하고 남은 리소스·비용을 추적합니다. 이전 1–2주는 예시이지 보편적 요구가 아닙니다. 모든 Pod에 Running을 요구하지 말고 실제 readiness·성공한 Job을 확인하세요. Data/traffic/workload 검증 후 원래 IaC owner로 삭제합니다.

</details>

### 8. 기존 self-managed Karpenter controller는 어떻게 다뤄야 하나요?

- A) Auto Mode 전에 항상 제거
- B) 호환 Karpenter를 공존 중 유지하고 old 소유 리소스 finalization 후 uninstall
- C) 공유 Karpenter CRD 전체 삭제
- D) Karpenter label 노드를 모두 선택해 삭제

<details>
<summary>정답 보기</summary>

**정답: B) 호환 Karpenter를 공존 중 유지하고 old 소유 리소스 finalization 후 uninstall**

**설명:**
AWS는 직접 공존 이전을 문서화합니다. v1.1 migration 최소값은 현재 Kubernetes 호환 조건을 대체하지 않습니다. 별도 NodeClass reference·taint Auto pool을 사용하고 공유 NodePool/NodeClaim CRD를 변경·삭제하지 마세요. 기존 controller가 finalization할 수 있는 동안 그 소유 pool/claim을 정리하고 인스턴스·의존성 정리를 확인한 뒤 해당 release/IAM/queue만 제거합니다.

</details>

## 참고 자료

- [Managed node-group scaling and PDBs](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)
- [Auto Mode migration reference](https://docs.aws.amazon.com/eks/latest/userguide/migrate-auto.html)
- [Karpenter coexistence migration](https://docs.aws.amazon.com/eks/latest/userguide/auto-migrate-karpenter.html)
