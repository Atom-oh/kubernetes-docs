# EKS 업그레이드 운영 퀴즈

> **관련 문서**: [EKS 업그레이드 운영](../../ops/11-upgrade-operations.md)

## 객관식 문제

### 1. EKS 업그레이드 전 deprecated API를 확인하기 위해 사용하는 도구는 무엇인가요?

- A) kubectl version
- B) pluto 또는 kubent
- C) helm list
- D) aws eks describe-cluster

<details>
<summary>정답 보기</summary>

**정답: B) pluto 또는 kubent**

**설명:**
pluto와 kubent는 클러스터나 Helm 차트에서 deprecated 또는 removed API를 검색하는 도구입니다. 업그레이드 전에 이 도구들을 실행하여 새 Kubernetes 버전에서 제거될 API를 사용하는 리소스를 미리 파악하고 수정해야 합니다.

</details>

### 2. Velero를 사용한 백업에서 기본적으로 제외되는 네임스페이스는 무엇인가요?

- A) default
- B) kube-system
- C) velero
- D) 모든 네임스페이스 포함

<details>
<summary>정답 보기</summary>

**정답: C) velero**

**설명:**
Velero는 기본적으로 자신이 설치된 velero 네임스페이스를 백업에서 제외합니다. kube-system은 필요에 따라 포함하거나 제외할 수 있습니다. 일반적으로 애플리케이션 네임스페이스 중심으로 백업하고, 시스템 네임스페이스는 클러스터 재구성으로 복원합니다.

</details>

### 3. EKS Auto Mode 업그레이드 시 권장되는 컴포넌트 업그레이드 순서는 무엇인가요?

- A) Add-ons → Control Plane → Nodes
- B) Nodes → Control Plane → Add-ons
- C) Control Plane → Add-ons → Nodes
- D) 동시에 모두 업그레이드

<details>
<summary>정답 보기</summary>

**정답: C) Control Plane → Add-ons → Nodes**

**설명:**
EKS 업그레이드는 Control Plane을 먼저 업그레이드하고, 그 다음 Add-ons(CoreDNS, kube-proxy, VPC CNI 등), 마지막으로 Nodes 순서로 진행합니다. Control Plane이 먼저 업그레이드되어야 새 버전의 API를 지원하고, Nodes는 Control Plane과 최대 2개 마이너 버전 차이까지 호환됩니다.

</details>

### 4. Blue/Green 클러스터 업그레이드 전략의 주요 장점은 무엇인가요?

- A) 비용 절감
- B) 업그레이드 실패 시 빠른 롤백 가능
- C) 자동 업그레이드
- D) 다운타임 없는 in-place 업그레이드

<details>
<summary>정답 보기</summary>

**정답: B) 업그레이드 실패 시 빠른 롤백 가능**

**설명:**
Blue/Green 업그레이드는 새 버전의 클러스터(Green)를 별도로 구축하고 검증한 후 트래픽을 전환합니다. 문제가 발생하면 트래픽을 기존 클러스터(Blue)로 즉시 되돌릴 수 있어 롤백이 빠르고 안전합니다. 단점은 일시적으로 두 클러스터 비용이 발생한다는 것입니다.

</details>

### 5. kubectl drain 명령의 --ignore-daemonsets 옵션이 필요한 이유는 무엇인가요?

- A) DaemonSet Pod를 강제 삭제
- B) DaemonSet Pod는 다른 노드로 이동할 수 없으므로 무시
- C) DaemonSet을 먼저 업그레이드
- D) DaemonSet 로그 무시

<details>
<summary>정답 보기</summary>

**정답: B) DaemonSet Pod는 다른 노드로 이동할 수 없으므로 무시**

**설명:**
DaemonSet은 모든 노드에 하나의 Pod를 실행하도록 설계되어 있어 다른 노드로 evict할 수 없습니다. --ignore-daemonsets 옵션을 사용하면 drain 시 DaemonSet Pod를 무시하고 진행합니다. 노드가 다시 Ready가 되면 DaemonSet Pod가 자동으로 재생성됩니다.

</details>

### 6. EKS 버전 업그레이드 시 한 번에 건너뛸 수 있는 마이너 버전 수는 몇 개인가요?

- A) 제한 없음
- B) 최대 1개 (순차 업그레이드 필요)
- C) 최대 2개
- D) 최대 3개

<details>
<summary>정답 보기</summary>

**정답: B) 최대 1개 (순차 업그레이드 필요)**

**설명:**
EKS는 한 번에 한 마이너 버전씩만 업그레이드할 수 있습니다. 예를 들어 1.27에서 1.29로 업그레이드하려면 1.27 → 1.28 → 1.29 순서로 두 번 업그레이드해야 합니다. 이는 Kubernetes의 API 호환성 정책 때문입니다.

</details>

### 7. Velero의 Schedule 리소스의 역할은 무엇인가요?

- A) 복원 일정 관리
- B) 정기적인 자동 백업 실행
- C) 업그레이드 일정 관리
- D) Pod 스케줄링

<details>
<summary>정답 보기</summary>

**정답: B) 정기적인 자동 백업 실행**

**설명:**
Velero Schedule은 cron 표현식을 사용하여 정기적인 백업을 자동으로 실행합니다. 예: `schedule: "0 2 * * *"`는 매일 오전 2시에 백업을 실행합니다. ttl(Time To Live)로 백업 보존 기간도 설정할 수 있습니다.

</details>

### 8. PodDisruptionBudget(PDB)의 역할과 업그레이드 관련성은 무엇인가요?

- A) Pod 성능 최적화
- B) 노드 drain 시 최소 가용 Pod 수를 보장하여 서비스 중단 방지
- C) Pod 메모리 제한
- D) Pod 네트워크 정책

<details>
<summary>정답 보기</summary>

**정답: B) 노드 drain 시 최소 가용 Pod 수를 보장하여 서비스 중단 방지**

**설명:**
PDB는 minAvailable 또는 maxUnavailable을 설정하여 voluntary disruption(업그레이드, 노드 drain 등) 시 최소한의 Pod가 항상 실행되도록 보장합니다. 예를 들어 minAvailable: 2면 drain 시에도 최소 2개 Pod가 유지됩니다.

</details>

### 9. EKS 업그레이드 후 확인해야 할 항목이 아닌 것은 무엇인가요?

- A) 모든 노드가 Ready 상태인지 확인
- B) 핵심 Pod들이 Running 상태인지 확인
- C) 이전 버전 클러스터 즉시 삭제
- D) Add-on 버전 호환성 확인

<details>
<summary>정답 보기</summary>

**정답: C) 이전 버전 클러스터 즉시 삭제**

**설명:**
Blue/Green 업그레이드의 경우 이전 클러스터를 즉시 삭제하지 않고 일정 기간 유지하여 문제 발생 시 롤백할 수 있도록 합니다. 업그레이드 후에는 노드 상태, Pod 상태, Add-on 호환성, 애플리케이션 기능 테스트 등을 확인해야 합니다.

</details>

### 10. AWS에서 EKS 버전의 표준 지원 기간은 얼마인가요?

- A) 6개월
- B) 12개월
- C) 14개월 (표준 지원)
- D) 24개월

<details>
<summary>정답 보기</summary>

**정답: C) 14개월 (표준 지원)**

**설명:**
EKS의 각 Kubernetes 버전은 출시 후 14개월간 표준 지원을 받습니다. 이후 12개월간 연장 지원(Extended Support)을 받을 수 있지만 추가 비용이 발생합니다. 지원 종료 전에 새 버전으로 업그레이드하는 것이 권장됩니다.

</details>
