# 노드 라이프사이클 관리 퀴즈

> 이 퀴즈는 [노드 라이프사이클 관리](../../eks-hybrid-nodes/07-node-lifecycle.md) 문서의 내용을 테스트합니다.

---

1. NodeConfig에서 kubelet의 `systemReserved`와 `kubeReserved`를 설정하는 주된 목적은 무엇인가요?
   - A) 파드의 리소스 요청을 자동으로 조정하기 위해
   - B) 시스템 프로세스와 Kubernetes 컴포넌트를 위한 리소스를 예약하여 노드 안정성을 보장하기 위해
   - C) 노드의 총 리소스를 증가시키기 위해
   - D) 파드 스케줄링 우선순위를 결정하기 위해

<details>
<summary>정답 보기</summary>

**정답: B) 시스템 프로세스와 Kubernetes 컴포넌트를 위한 리소스를 예약하여 노드 안정성을 보장하기 위해**

**설명:**
`systemReserved`는 OS 및 시스템 데몬(sshd, udev 등)을 위한 리소스를, `kubeReserved`는 kubelet과 containerd를 위한 리소스를 예약합니다. 이를 통해 파드가 노드 전체 리소스를 소모하지 않아 노드 안정성이 유지됩니다.

</details>

---

2. kubelet의 `evictionHard`와 `evictionSoft`의 차이점은 무엇인가요?
   - A) `evictionHard`는 소프트 리밋이고, `evictionSoft`는 하드 리밋이다
   - B) `evictionHard`는 즉시 축출을 실행하고, `evictionSoft`는 유예 기간 후 축출한다
   - C) `evictionHard`는 파드만 축출하고, `evictionSoft`는 노드를 종료한다
   - D) 두 설정은 동일하게 동작하며 이름만 다르다

<details>
<summary>정답 보기</summary>

**정답: B) `evictionHard`는 즉시 축출을 실행하고, `evictionSoft`는 유예 기간 후 축출한다**

**설명:**
`evictionHard` 임계값에 도달하면 kubelet은 즉시 파드를 축출합니다. `evictionSoft`는 `evictionSoftGracePeriod`에 설정된 유예 기간 동안 임계값이 지속될 때만 축출하여 갑작스러운 파드 종료를 방지합니다.

</details>

---

3. Kubernetes 버전 스큐 정책에 따르면, EKS 컨트롤 플레인이 1.31일 때 kubelet이 실행할 수 있는 가장 오래된 버전은?
   - A) 1.27
   - B) 1.28
   - C) 1.29
   - D) 1.30

<details>
<summary>정답 보기</summary>

**정답: B) 1.28**

**설명:**
Kubernetes 버전 스큐 정책에 따르면, kubelet은 API 서버보다 최대 3개의 마이너 버전까지 이전 버전일 수 있습니다. API 서버가 1.31이면 kubelet은 1.31, 1.30, 1.29, 1.28까지 호환됩니다. 1.27은 n-4이므로 지원되지 않습니다.

</details>

---

4. 카나리 업그레이드 전략의 핵심 원리는 무엇인가요?
   - A) 모든 노드를 동시에 업그레이드한다
   - B) 1개 노드를 먼저 업그레이드하고 검증한 후 나머지를 진행한다
   - C) 노드를 삭제하고 새로운 노드를 생성한다
   - D) 다운타임 없이 인플레이스로 업그레이드한다

<details>
<summary>정답 보기</summary>

**정답: B) 1개 노드를 먼저 업그레이드하고 검증한 후 나머지를 진행한다**

**설명:**
카나리 업그레이드는 1개의 "카나리" 노드를 먼저 업그레이드하고 그 결과를 검증합니다. 문제가 없으면 나머지 노드에 대해 롤링 업그레이드를 진행하여 위험을 최소화합니다.

</details>

---

5. nodeadm이 하이브리드 노드를 초기화할 때 자동으로 부여하는 레이블은 무엇인가요?
   - A) `node-role.kubernetes.io/hybrid=true`
   - B) `topology.kubernetes.io/zone=on-premises`
   - C) `eks.amazonaws.com/compute-type=hybrid`
   - D) `kubernetes.io/os=hybrid`

<details>
<summary>정답 보기</summary>

**정답: C) `eks.amazonaws.com/compute-type=hybrid`**

**설명:**
nodeadm은 하이브리드 노드 초기화 시 `eks.amazonaws.com/compute-type=hybrid` 레이블을 자동으로 부여합니다. 이 레이블은 `--node-labels` 플래그에 수동으로 추가할 필요가 없으며, Cilium affinity, 워크로드 배치 등에 사용됩니다.

</details>

---

6. SSM Hybrid Activation이 만료된 경우 올바른 조치는?
   - A) 기존 활성화의 만료일을 연장한다
   - B) 새로운 SSM Hybrid Activation을 생성하고 nodeconfig.yaml을 업데이트한다
   - C) IAM Roles Anywhere로 전환한다
   - D) kubelet을 재시작하면 자동으로 갱신된다

<details>
<summary>정답 보기</summary>

**정답: B) 새로운 SSM Hybrid Activation을 생성하고 nodeconfig.yaml을 업데이트한다**

**설명:**
SSM Hybrid Activation은 생성 시 설정한 만료일이 지나면 더 이상 사용할 수 없으며, 기존 활성화의 만료일을 연장할 수는 없습니다. 새로운 활성화를 생성하고, nodeconfig.yaml의 `activationCode`와 `activationId`를 업데이트한 후, 필요 시 노드를 재등록해야 합니다.

</details>

---

7. 노드 업그레이드 시 올바른 순서는?
   - A) 노드 먼저 업그레이드 → 컨트롤 플레인 업그레이드
   - B) 컨트롤 플레인과 노드를 동시에 업그레이드
   - C) 컨트롤 플레인(EKS) 먼저 업그레이드 → 노드 업그레이드
   - D) 순서는 관계없다

<details>
<summary>정답 보기</summary>

**정답: C) 컨트롤 플레인(EKS) 먼저 업그레이드 → 노드 업그레이드**

**설명:**
Kubernetes 버전 스큐 정책에 따라, kubelet은 API 서버보다 최신 버전일 수 없습니다. 따라서 반드시 컨트롤 플레인을 먼저 업그레이드한 후 노드를 업그레이드해야 합니다. 노드를 먼저 업그레이드하면 호환성 문제가 발생합니다.

</details>

---

8. `shutdownGracePeriod: 60s`와 `shutdownGracePeriodCriticalPods: 20s`가 설정된 경우, 일반 파드가 받는 종료 유예 시간은?
   - A) 20초
   - B) 40초
   - C) 60초
   - D) 80초

<details>
<summary>정답 보기</summary>

**정답: B) 40초**

**설명:**
`shutdownGracePeriodCriticalPods`는 `shutdownGracePeriod` 내에 포함됩니다. 전체 유예 기간 60초에서 크리티컬 파드용 20초를 빼면 일반 파드는 40초의 종료 유예 시간을 받습니다. 크리티컬 파드(priority class가 system-cluster-critical 또는 system-node-critical)는 마지막 20초 동안 종료됩니다.

</details>
