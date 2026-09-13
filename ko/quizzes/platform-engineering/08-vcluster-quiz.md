# vCluster 퀴즈

[vCluster](../../platform-engineering/08-vcluster.md)

원문의 8개 주제를 vCluster 0.37.0 기준으로 검토했습니다.

## 1. Shared Nodes vCluster가 분리하는 것과 공유하는 것은 무엇인가요?

<details>
<summary>정답 보기</summary>

가상 API·RBAC·controller·데이터 저장소를 분리할 수 있지만 실제 workload의 node/kernel/CNI/CSI는 공유합니다. 완전한 하드웨어·네트워크·성능 격리를 보장하지 않습니다.

</details>

## 2. Syncer의 역할은 무엇인가요?

<details>
<summary>정답 보기</summary>

설정된 가상 리소스와 참조를 host 리소스로 변환하고 관찰 상태를 되돌립니다. 기본 동기화 대상과 이름 변환은 mode/version에 따라 달라지므로 모든 리소스가 항상 양방향 동기화된다고 가정하지 않습니다.

</details>

## 3. PR preview에 필요한 조건은 무엇인가요?

<details>
<summary>정답 보기</summary>

검증한 profile, 충분한 host capacity, 신뢰한 CI identity/event, 정확한 namespace/context와 cleanup이 필요합니다. 30초 생성이나 테스트 시간 단축을 보장하지 않으며 fork 코드에 host credential을 주지 않습니다.

</details>

## 4. Pause와 자동 Sleep은 어떻게 이해해야 하나요?

<details>
<summary>정답 보기</summary>

현재 pause는 workload를 삭제하고 resume 시 재생성하며 PVC/Service는 별도 보존합니다. 메모리 상태의 suspend나 backup이 아닙니다. 자동 sleep/wake와 entitlement·실제 비용 절감은 별도로 검증합니다.

</details>

## 5. Shared Nodes에서 StorageClass와 PVC는 어떻게 동작하나요?

<details>
<summary>정답 보기</summary>

지원되는 fromHost StorageClass 설정과 host CSI를 사용하고 PVC를 host로 동기화합니다. volumeBindingMode·topology·reclaim/retention을 확인합니다. 0.37은 snapshot sync를 지원하지만 제거된 deploy.volumeSnapshotController와 혼동하지 않습니다.

</details>

## 6. Backstage와 GitOps의 연결 조건은 무엇인가요?

<details>
<summary>정답 보기</summary>

준비된 action/skeleton, 검토한 PR, 실제 ArgoCD AppProject·destination·repo 권한과 values source가 필요합니다. debug:log는 승인이나 배포 대기를 수행하지 않습니다. kubeconfig는 공개 출력이 아니라 승인된 credential 경로로 전달합니다.

</details>

## 7. NetworkPolicy만 추가하면 host 접근이 모두 차단되나요?

<details>
<summary>정답 보기</summary>

아닙니다. 허용 규칙은 합쳐지며 기존 allow를 별도 deny로 줄일 수 없습니다. Syncer는 host API 접근이 필요합니다. 본문 profile은 workload public egress를 끄지만 control-plane 포트 허용이 남으므로 실제 CNI와 필요한 경로를 검증합니다.

</details>

## 8. 어떤 기준으로 배포 모드를 선택하나요?

<details>
<summary>정답 보기</summary>

API 자율성, node/kernel/CNI/CSI·계정·관리자 경계, 성능과 lifecycle 요구를 함께 평가합니다. Shared Nodes, Dedicated/Private Nodes, Standalone과 별도 cluster를 비교하고 측정하지 않은 속도·비용·규제 적합성을 보장하지 않습니다.

</details>
