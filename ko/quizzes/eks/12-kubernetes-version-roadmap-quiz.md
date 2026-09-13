# Kubernetes 버전별 신규 기능과 로드맵 퀴즈

> **마지막 업데이트**: 2026년 9월 12일

버전별 전제와 감사 근거의 한계는 [본문](../../eks/12-kubernetes-version-roadmap.md)을 참고하세요.

1. Kubernetes minor release 주기는?

   - A) 연 1회 feature release
   - B) 연 약 3회, 약 4개월 간격
   - C) 매월 minor release
   - D) AWS 행사에 고정된 일정

<details>
<summary>정답 보기</summary>

**정답: B) 연 약 3회, 약 4개월 간격**

Upstream minor release는 보통 연 3회이며 patch release 주기는 별개입니다. Upstream patch 지원은 약14개월(일반12+maintenance2)입니다. EKS standard support도14개월이지만 EKS 출시일부터 계산하므로 두 일정을 혼동하지 않습니다.

</details>

---

2. EKS standard·extended 버전 지원 요금은 어떻게 다른가요?

   - A) Standard는 무료
   - B) Standard14개월·시간당$0.10, extended추가12개월·총시간당$0.60
   - C) Extended면 모든 과거 버전을 영구 지원
   - D) Extended에는 보안 patch가 없음

<details>
<summary>정답 보기</summary>

**정답: B) Standard14개월·시간당$0.10, extended추가12개월·총시간당$0.60**

전체 compute/storage/network 비용이 아닌 버전 지원 요금입니다. 기본 upgrade policy는 EXTENDED이며 STANDARD는 standard 종료 후 자동 upgrade될 수 있습니다. Extended에도 관련 보안 patch가 제공됩니다. 현재 release 일정·실제 지원 종료일·workload 위험을 함께 확인합니다.

</details>

---

3. Native sidecar container의 stable 도달 버전은?

   - A) 1.28
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>정답 보기</summary>

**정답: C) 1.33**

Alpha1.28 → beta 1.29 → stable 1.33입니다. 재시작 가능한 init container는 restartPolicy:Always를 사용합니다. 시작 순서는 started/startupProbe 상태에 따르고 정상 종료는 Pod의 공통 termination budget을 사용합니다. GA가 모든 helper의 정상 종료나 proxy image 설정의 정확성을 보장하지는 않습니다.

</details>

---

4. Container in-place resize의 기능과 stable 버전은?

   - A) Replica scaling;1.30
   - B) 기존 Pod의 CPU/memory 할당 변경;1.35, 재시작/runtime 제약 존재
   - C) PVC 확장;1.31
   - D) 프로세스 재시작 없는 image 변경;1.34

<details>
<summary>정답 보기</summary>

**정답: B) 기존 Pod의 CPU/memory 할당 변경;1.35, 재시작/runtime 제약 존재**

Alpha1.27·beta 1.33·stable 1.35입니다. Container resizePolicy가 재시작 동작을 제어하고 resource 변경이 pending/infeasible 상태에 머물 수 있습니다. PATCH 수락·containerID 유지만으로 cgroup 적용 완료나 무중단을 증명하지 않습니다. Desired/reported resource·generation·condition을 비교하며 VPA mode의 버전·gate도 별도로 확인합니다.

</details>

---

5. Kubernetes 1.31의 DRA에 대한 올바른 설명은?

   - A) Classic DRA가 Device Plugins v2로 대체됨
   - B) DRA는 아직 alpha였고 structured API가 발전하는 동안 classic 할당은 별도 gate로 남음
   - C) DRA가 이미 GA
   - D) Stable v1 request 구문이 모든 과거 alpha API와 같음

<details>
<summary>정답 보기</summary>

**정답: B) DRA는 아직 alpha였고 structured API가 발전하는 동안 classic 할당은 별도 gate로 남음**

1.31 릴리스·소스에는 DRAControlPlaneController가 기본 비활성 alpha gate로 남아 있습니다. 1.32에서 제거되며 DRA core는1.32 beta·1.34 stable입니다. 기존 퀴즈의 “1.31에서 제거” 답은 잘못되었습니다. 현재 v1 request는 exactly를 사용하고 실제 driver·ResourceSlice·attribute를 확인해야 합니다.

</details>

---

6. 1.30에서 native CEL admission validation으로 stable이 된 기능은?

   - A) OPA Gatekeeper v4
   - B) 필수 parameter CRD
   - C) ValidatingAdmissionPolicy
   - D) 모든 mutating admission 기능

<details>
<summary>정답 보기</summary>

**정답: C) ValidatingAdmissionPolicy**

ValidatingAdmissionPolicy는 policy·binding과 선택적인 parameter object를 사용하며 parameter가 반드시 CRD일 필요는 없습니다. 적합한 로직에는 외부 validation webhook이 필요 없지만 오류·failurePolicy가 요청에 영향을 줄 수 있습니다. Binding 범위를 제한하고 Audit와 Deny를 구분합니다. MAP mutation은 별도 기능이며1.36에서 stable이 되었습니다.

</details>

---

7. 확인한 릴리스 이력에서 KYAML은 무엇인가요?

   - A) 일반 YAML anchor를 모두 거부하는 API server validator
   - B) Kubectl 출력 형식: alpha 1.34, beta 1.35~1.36, stable 1.37
   - C) 지원 티켓으로 켜는 새 EKS 서버 기능
   - D) 모든 입력 manifest를 YAML1.2로 변환해야 하는 요구사항

<details>
<summary>정답 보기</summary>

**정답: B) Kubectl 출력 형식: alpha 1.34, beta 1.35~1.36, stable 1.37**

KYAML은 KEP-5295입니다. 실제 kubectl 1.36.2 검사는 일반 YAML anchor를 읽어 KYAML로 출력했습니다. KUBECTL_KYAML=false는 출력 printer를 끄지만 KYAML input을 JSON으로 출력하는 것은 가능했습니다. Formatting은 schema/admission 검증과 별개입니다. 검토일에는 upstream1.37이 이미 출시되었지만 EKS 1.37 제공을 뜻하지는 않습니다.

</details>

---

8. 적절한 EKS upgrade 계획은?

   - A) 시간 절약을 위해 minor version 건너뛰기
   - B) Minor 단계별 연습·실제 호환성/소유권 확인·복구 준비
   - C) Scanner exit0을 완전한 증거로 취급
   - D) 컨트롤 플레인 이후 모든 add-on을 항상 같은 순서로 변경

<details>
<summary>정답 보기</summary>

**정답: B) Minor 단계별 연습·실제 호환성/소유권 확인·복구 준비**

현재 지원 일정·manifest/client 사용 근거·정확한 add-on 호환성과 compute별 순서를 확인합니다. 일부 사전 작업은 컨트롤 플레인 이전에 필요합니다. 실제 update ID·readiness·data를 검증하고 Pod resize·node 교체·scaling을 구분합니다. EKS native rollback은 완료된 in-place upgrade 후7일 안의 조건부 기능이지 DB rollback이나 모든 제어 우회 허가가 아닙니다.

</details>

---
