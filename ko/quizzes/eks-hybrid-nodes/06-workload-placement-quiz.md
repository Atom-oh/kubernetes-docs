# EKS Hybrid Nodes 워크로드 배치 퀴즈

> **관련 문서**: [워크로드 배치](../../eks-hybrid-nodes/06-workload-placement.md)
> **마지막 업데이트**: 2026년 9월 13일

### 1. Pod 배치·적격성을 직접 제어하는 기법이 아닌 것은?

A. nodeSelector

B. Node affinity

C. Taint와 toleration

D. PodDisruptionBudget

<details>
<summary>정답 보기</summary>

**정답: D. PodDisruptionBudget**

**설명:** PDB는 지원되는 자발적 eviction 요청을 제약하며 노드를 선택하거나 모든 삭제 경로의 가용성을 보장하지 않습니다. Node selection, affinity와 taint는 서로 다른 스케줄링 역할을 가집니다.

</details>

### 2. dedicated=gpu:NoSchedule의 의미는?

A. GPU를 요청한 컨테이너만 절대적으로 실행 가능

B. 새 Pod에 해당 toleration이 필요하지만 GPU 사용 증명이나 강제 배치는 아님

C. 기존 Pod 즉시 퇴거

D. 노드 GPU 리소스 자동 게시

<details>
<summary>정답 보기</summary>

**정답: B. 새 Pod에 해당 toleration이 필요하지만 GPU 사용 증명이나 강제 배치는 아님**

**설명:** CPU 전용 Pod도 taint를 허용할 수 있습니다. GPU 리소스 요청·admission policy는 별도입니다. NoSchedule은 새 스케줄링에 영향을 주며 NoExecute는 다른 퇴거 의미를 가집니다.

</details>

### 3. Burst 허용 워크로드에서 preferred node affinity가 제공하는 것은?

A. 실행 중인 cloud Pod의 온프레미스 자동 복귀

B. 고정 온프레미스·클라우드 replica 비율

C. 다른 제약·가용 용량을 고려한 적격 노드 사이 선호

D. Pod8개 이후 무제한 AWS 용량

<details>
<summary>정답 보기</summary>

**정답: C. 다른 제약·가용 용량을 고려한 적격 노드 사이 선호**

**설명:** Preferred affinity는 포화 감지기, 엄격한 순서나 이동 컨트롤러가 아닙니다. 노드 수는 Pod 용량이 아닙니다. Karpenter와 replica autoscaler는 별도 루프이며 quota, 가용 인스턴스, IP와 워크로드 의존성이 확장을 막을 수 있습니다.

</details>

### 4. DoNotSchedule에서 topology maxSkew는 어떻게 해석하는가?

A. 클러스터 전체 Pod 수 상한

B. 적격 도메인의 global minimum과 설정한 minDomains 동작을 기준으로 해석

C. ScheduleAnyway에서도 균등 분산 보장

D. AWS 계정 수

<details>
<summary>정답 보기</summary>

**정답: B. 적격 도메인의 global minimum과 설정한 minDomains 동작을 기준으로 해석**

**설명:** 적격 도메인은 Pod 제약·topology policy에 따라 달라집니다. ScheduleAnyway는 soft score이므로 maxSkew를 초과할 수 있습니다. 누락 도메인과 hard rule 때문에 Pod가 Pending일 수 있습니다.

</details>

### 5. 로컬 영구 데이터에 적절한 방법은?

A. Node label만으로 데이터 존재 가정

B. 관리된 local PV/PVC topology·binding을 사용하고 cloud 배치의 데이터 접근·복제를 별도 계획

C. hostPath의 /mnt/data를 이동 가능한 스토리지로 취급

D. Volume 확인 없이 임의 cloud node로 Pod 이동

<details>
<summary>정답 보기</summary>

**정답: B. 관리된 local PV/PVC topology·binding을 사용하고 cloud 배치의 데이터 접근·복제를 별도 계획**

**설명:** Label은 데이터를 생성·복제하지 않습니다. Local PV node affinity와 WaitForFirstConsumer가 배치를 조정하며 bound된 로컬 volume이 EC2 fallback 노드에서 자동 접근 가능해지지 않습니다.

</details>

### 6. Required hostname anti-affinity가 돕는 것은?

A. 애플리케이션 가용성 완전 보장

B. 충분한 용량이 있을 때 matching replica를 적격 Kubernetes Node 사이에 분리

C. 독립 물리 전원 사이 분리 보장

D. 다른 컨트롤러 없이 replica 자동 복구

<details>
<summary>정답 보기</summary>

**정답: B. 충분한 용량이 있을 때 matching replica를 적격 Kubernetes Node 사이에 분리**

**설명:** 상관 장애의 한 원인을 줄입니다. 남은 replica에도 readiness, 의존성과 충분한 처리 용량이 필요하며 서로 다른 Kubernetes Node가 같은 물리 호스트·장애 도메인을 공유할 수 있습니다.

</details>

### 7. Deletion-cost1000인 온프레미스 Pod가 cost0인 cloud Pod보다 먼저 삭제될 수 있는가?

A. 아니다.1000은 eviction 완전 보호

B. 아니다.cost가 ReplicaSet의 첫 비교 기준

C. 그렇다.확인한 컨트롤러에서는 할당·phase·readiness가 cost보다 먼저

D. Cost annotation이 없을 때만 가능

<details>
<summary>정답 보기</summary>

**정답: C. 그렇다.확인한 컨트롤러에서는 할당·phase·readiness가 cost보다 먼저**

**설명:** 미할당, Pending/Unknown, NotReady 기준이 먼저 적용될 수 있습니다. Deletion cost는 같은 ReplicaSet Pod 사이의 best-effort 선호이며 모든 컨트롤러·rollout·eviction·장애의 보호 장치가 아닙니다.

</details>

### 8. 이전 CREATE 전용 위치 기반 mutating webhook이 불완전한 이유는?

A. Pod 생성은 admission webhook을 지원하지 않음

B. Cloud에는 label이 없음

C. 일반 CREATE 요청은 아직 노드에 bound되지 않아 최종 위치를 알 수 없음

D. Deletion cost는 스케줄링 전에만 변경 가능

<details>
<summary>정답 보기</summary>

**정답: C. 일반 CREATE 요청은 아직 노드에 bound되지 않아 최종 위치를 알 수 없음**

**설명:** Post-binding 절차는 spec.nodeName을 조사할 수 있습니다. 운영 webhook에는 올바른 backend,Service,TLS와 제한된 policy도 필요하며 불완전한 fail-closed webhook은 Pod 생성을 막을 수 있습니다.

</details>

### 9. Karpenter1.14.1도 pod-deletion-cost를 읽는가?

A. 아니다.ReplicaSet만 읽을 수 있음

B. 그렇다.다른 입력과 함께 정규화한 eviction-cost에 사용하지만 중단 금지는 아님

C. 그렇다.1000은 보호1000배 보장

D. 그렇다.PDB와 모든 disruption budget 대체

<details>
<summary>정답 보기</summary>

**정답: B. 그렇다.다른 입력과 함께 정규화한 eviction-cost에 사용하지만 중단 금지는 아님**

**설명:** 태그된 Karpenter 소스는 Pod eviction cost에 annotation을 포함합니다. 후보 평가, 노드 상태, priority와 lifecycle 제약이 계속 적용되며 cost annotation은 빈 노드의 즉시 제거를 보장하지 않습니다.

</details>

### 10. 단일 Pod annotation patch가 이전 클러스터 전체 CronJob보다 안전한 이유는?

A. 모든 API 오류 숨김

B. Label 누락으로 cloud 배치 추론

C. 의도한 ReplicaSet owner·노드 분류·Pod UID·resourceVersion 확인 후 좁은 patch 검토

D. 첫 충돌 뒤 동시 변경 test 제거

<details>
<summary>정답 보기</summary>

**정답: C. 의도한 ReplicaSet owner·노드 분류·Pod UID·resourceVersion 확인 후 좁은 patch 검토**

**설명:** 예제는 알 수 없거나 미스케줄 상태를 거부하고 검토 가능한 patch를 만듭니다. UID·resourceVersion·node test가 오래된 상태를 거부하며 다른 annotation을 보존합니다. 모든 namespace를 조사·수정하지 않습니다.

</details>

