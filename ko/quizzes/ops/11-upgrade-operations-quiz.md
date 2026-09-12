# EKS 업그레이드 운영 퀴즈

> **관련 문서**: [EKS 업그레이드](../../ops/11-upgrade-operations.md)

## 1. EKS 컨트롤 플레인 minor 업그레이드에서 건너뛸 수 있는 중간 버전 수는?

- A) 0개: 다음 minor로 한 단계씩 진행
- B) 1개
- C) 2개
- D) 제한 없음

<details>
<summary>정답 보기</summary>

**정답: A**

예를 들어 1.34→1.36은 1.35를 거쳐야 합니다. kubelet의 허용 skew와 CP 업그레이드 단계를 구별합니다.

</details>

## 2. 순수 Auto Mode에서 CoreDNS Deployment가 없을 때 올바른 해석은?

- A) 항상 DNS 장애다
- B) 노드 system service의 DNS를 사용하므로 관리 주체와 실제 DNS 동작을 확인한다
- C) 반드시 자체 Karpenter를 설치한다
- D) 모든 클러스터에서 CoreDNS Deployment를 삭제한다

<details>
<summary>정답 보기</summary>

**정답: B**

일반 노드가 섞인 클러스터는 필요한 DNS Deployment와 애드온을 유지해야 합니다.

</details>

## 3. Velero 1.18.2 restore create -o json에 대한 올바른 설명은?

- A) 실제 복원을 완료한다
- B) 완전히 오프라인으로만 동작한다
- C) 객체를 생성하지 않지만 discovery/Backup 읽기는 수행할 수 있다
- D) --dry-run과 함께 써야만 유효하다

<details>
<summary>정답 보기</summary>

**정답: C**

restore create에는 해당 --dry-run flag가 없습니다. 출력 전용 객체 확인과 실제 격리 복원 시험은 별개입니다.

</details>

## 4. Preflight 도구가 API 오류나 잘못된 kubecontext를 만났을 때 해야 할 일은?

- A) 빈 결과를 정상으로 취급한다
- B) 상태를 알 수 없거나 context 불일치로 실패시키고 확인한다
- C) 자동으로 현재 context를 바꿔 업그레이드한다
- D) PDB를 삭제한다

<details>
<summary>정답 보기</summary>

**정답: B**

Running만으로 Pod Ready를 보장하지 않으며 Deployment generation과 rollout 상태도 확인해야 합니다.

</details>

## 5. EKS 네이티브 롤백의 기본 자격 조건은?

- A) 현재 버전으로 새로 만든 모든 클러스터
- B) 업그레이드 완료 후 7일 안에 이전 minor로 롤백을 시작하는 등 자격 조건 충족
- C) 언제든 원하는 이전 버전
- D) etcd 백업이 있으면 모든 제약 우회

<details>
<summary>정답 보기</summary>

**정답: B**

대상 지원 상태, EXTENDED 정책, 현재 ACTIVE 상태와 호환되지 않는 EKS 기능 등도 확인합니다.

</details>

## 6. Auto Mode 노드 롤백 중 cluster status가 ACTIVE이면?

- A) 롤백이 모두 끝났다
- B) CP가 현재 버전으로 서비스 중일 수 있으므로 update ID 상태를 확인한다
- C) 노드 롤백이 불가능하다
- D) 즉시 이전 클러스터를 삭제한다

<details>
<summary>정답 보기</summary>

**정답: B**

Auto Mode는 노드를 먼저 조정합니다. 기본 node timeout은 720분이며 클라이언트 대기 timeout은 AWS 작업 취소가 아닙니다.

</details>

## 7. Rollback --force의 범위는?

- A) 7일 창과 모든 PDB
- B) 모든 노드 disruption과 데이터 호환성
- C) Insight 검사이며 자격 조건이나 Auto Mode disruption 제약을 해제하지 않는다
- D) etcd 데이터 보존

<details>
<summary>정답 보기</summary>

**정답: C**

ERROR/UNKNOWN은 차단하고 WARNING은 advisory입니다. force를 기본 복구 방법으로 사용하지 않습니다.

</details>

## 8. 네이티브 버전 롤백이 자동으로 과거 상태로 복원하지 않는 것은?

- A) API server minor 버전
- B) Auto Mode 노드의 버전 조정
- C) 애드온·앱·etcd 객체·PV 데이터
- D) 제어 플레인 구성 요소 버전

<details>
<summary>정답 보기</summary>

**정답: C**

일반 managed node group은 별도 UpdateNodegroupVersion이 필요합니다. 데이터 snapshot 복원과 버전 롤백을 구별합니다.

</details>

## 9. NLB TG 가중치 0 전환에 대한 올바른 설명은?

- A) 기존 연결은 무조건 끝까지 유지된다
- B) 짧은 시간 후 기존 연결도 닫힐 수 있으므로 retry/session 동작을 시험한다
- C) 가중치 합은 반드시 100이어야 한다
- D) NLB는 weighted TG를 지원하지 않는다

<details>
<summary>정답 보기</summary>

**정답: B**

가중치는 0–999 상대값입니다. 일반 변경과 0 전환을 구별하며 TLS listener의 TG stickiness 미지원도 확인합니다.

</details>

## 10. Blue 클러스터 정리 전 올바른 확인은?

- A) weight가 0이면 즉시 destroy
- B) 공유 자원/TG 참조·데이터 호환성·복구 기간·소유권을 확인
- C) HTTP 200 한 번이면 모든 데이터 정합성 보장
- D) 공유 EFS이면 동시 writer를 검토할 필요 없음

<details>
<summary>정답 보기</summary>

**정답: B**

Auto Mode TGB/클러스터 삭제의 TG 수명주기와 shared listener를 고려합니다. namespace 변경도 consumer/DB/DNS 격리를 보장하지 않습니다.

</details>
