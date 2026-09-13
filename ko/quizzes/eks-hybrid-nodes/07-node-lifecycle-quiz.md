# 노드 라이프사이클 관리 퀴즈

> 이 퀴즈는 [노드 라이프사이클 관리](../../eks-hybrid-nodes/07-node-lifecycle.md) 문서의 내용을 테스트합니다.

---

1. NodeConfig에서 kubelet의 `systemReserved`와 `kubeReserved`를 설정하는 주된 목적은 무엇인가요?
   - A) 파드의 리소스 요청을 자동으로 조정하기 위해
   - B) 시스템 프로세스와 Kubernetes 컴포넌트를 위한 리소스를 예약하여 Node Allocatable을 산정하기 위해
   - C) 노드의 총 리소스를 증가시키기 위해
   - D) 파드 스케줄링 우선순위를 결정하기 위해

<details>
<summary>정답 보기</summary>

**정답: B) 시스템 프로세스와 Kubernetes 컴포넌트를 위한 리소스를 예약하여 Node Allocatable을 산정하기 위해**

**설명:**
`systemReserved`는 OS 및 시스템 데몬(sshd, udev 등)을 위한 리소스를, `kubeReserved`는 kubelet과 containerd를 위한 리소스를 예약합니다. 예약량은 allocatable 용량에서 차감됩니다. 호스트 프로세스 cgroup 예약의 강제 적용에는 추가 설정이 필요하며 이 값만으로 안정성이 보장되지는 않습니다.

</details>

---

2. kubelet의 `evictionHard`와 `evictionSoft`의 차이점은 무엇인가요?
   - A) `evictionHard`는 소프트 리밋이고, `evictionSoft`는 하드 리밋이다
   - B) `evictionHard`에는 soft 관측 유예가 없고, `evictionSoft`는 임계값이 관측 유예 동안 지속되어야 한다
   - C) `evictionHard`는 파드만 축출하고, `evictionSoft`는 노드를 종료한다
   - D) 두 설정은 동일하게 동작하며 이름만 다르다

<details>
<summary>정답 보기</summary>

**정답: B) `evictionHard`에는 soft 관측 유예가 없고, `evictionSoft`는 임계값이 관측 유예 동안 지속되어야 한다**

**설명:**
kubelet은 먼저 노드 수준의 회수를 시도하고 필요하면 Pod를 축출합니다. `evictionHard`에는 soft 관측 유예가 없으며 Pod를 축출할 때 종료 유예를 부여하지 않습니다. `evictionSoft`는 임계값이 `evictionSoftGracePeriod` 동안 지속되어야 하고, `evictionMaxPodGracePeriod`가 Pod 종료 유예의 상한을 별도로 정합니다. Hard 축출이나 OOM이 방지되는 것은 아닙니다.

</details>

---

3. Kubernetes 버전 스큐 정책에 따르면, 현재 EKS 버전 공급 여부와 별개로 과거 1.31 API 서버 예시에서 허용하는 가장 오래된 kubelet 버전은?
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

6. SSM 활성화가 만료됐지만 노드가 이미 등록되어 있다면 올바른 조치는?
   - A) 기존 활성화의 만료일을 연장한다
   - B) 기존 등록을 유지하고 필요한 새 등록에만 새 활성화를 사용한다
   - C) IAM Roles Anywhere로 전환한다
   - D) kubelet을 재시작하면 자동으로 갱신된다

<details>
<summary>정답 보기</summary>

**정답: B) 기존 등록을 유지하고 필요한 새 등록에만 새 활성화를 사용한다**

**설명:**
활성화 만료는 새 등록을 제한합니다. 이미 등록한 노드는 명시적으로 등록 해제할 때까지 관리형 노드로 남습니다. 활성화 만료만으로 정상 노드를 uninstall/재등록하지 않으며 에이전트 자격 증명·역할 권한·연결 상태는 별도로 확인합니다.

</details>

---

7. 노드가 현재 컨트롤 플레인의 minor 버전과 같을 때 다음 minor 버전으로 올리는 순서는?
   - A) 노드 먼저 업그레이드 → 컨트롤 플레인 업그레이드
   - B) 컨트롤 플레인과 노드를 동시에 업그레이드
   - C) 컨트롤 플레인(EKS) 먼저 업그레이드 → 노드 업그레이드
   - D) 순서는 관계없다

<details>
<summary>정답 보기</summary>

**정답: C) 컨트롤 플레인(EKS) 먼저 업그레이드 → 노드 업그레이드**

**설명:**
Kubernetes 버전 스큐 정책에 따라, kubelet은 API 서버보다 최신 버전일 수 없습니다. 이 다음 minor 전환에서는 컨트롤 플레인을 먼저 업그레이드합니다. 뒤처진 노드를 현재 컨트롤 플레인 버전으로 먼저 맞추는 작업은 skew 위반이 아닙니다.

</details>

---

8. `shutdownGracePeriod: 60s`와 `shutdownGracePeriodCriticalPods: 20s`가 설정된 경우, 일반 파드 그룹에 배분한 전체 종료 창은?
   - A) 20초
   - B) 40초
   - C) 60초
   - D) 80초

<details>
<summary>정답 보기</summary>

**정답: B) 40초**

**설명:**
`shutdownGracePeriodCriticalPods`는 `shutdownGracePeriod` 내에 포함됩니다. 전체 유예 기간 60초에서 크리티컬 파드용 20초를 빼면 일반 파드 그룹에는 전체 40초의 종료 창이 배분됩니다. 마지막 20초는 critical Pod의 종료 창입니다. 강제 종료 상황에서도 각 Pod에 이 시간이 보장되는 것은 아니며 개별 terminationGracePeriodSeconds도 적용됩니다.

</details>
