# Kubernetes 버전별 신규 기능과 로드맵 퀴즈

1. Kubernetes의 릴리스 주기는?
   - A) 연 1회 대규모 기능 릴리스
   - B) 연 약 3회, 약 4개월 간격으로 마이너 버전 릴리스
   - C) 월간 패치 릴리스와 분기별 기능 릴리스
   - D) AWS re:Invent와 Summit에 맞춘 연 2회 릴리스

<details>
<summary>정답 보기</summary>

**정답: B) 연 약 3회, 약 4개월 간격으로 마이너 버전 릴리스**

**설명:**
Kubernetes는 약 4개월 주기로 연 3회 마이너 버전을 릴리스합니다. 각 릴리스는 enhancement freeze, code freeze, release candidate 단계를 거칩니다. 최근 릴리스: 1.33 (2025년 4월), 1.34 (2025년 8월), 1.35 (2025년 12월), 1.36 (2026년 4월). 각 버전은 약 14개월간 패치 릴리스를 통해 유지보수됩니다.

</details>

---

2. EKS Standard Support와 Extended Support의 차이점은?
   - A) Standard는 무료, Extended는 Enterprise 라이선스 필요
   - B) Standard는 14개월 ($0.10/클러스터/시간), Extended는 추가 12개월 ($0.60/클러스터/시간)
   - C) Standard는 3개 버전 지원, Extended는 모든 버전 지원
   - D) Standard는 월간 패치, Extended는 주간 패치 제공

<details>
<summary>정답 보기</summary>

**정답: B) Standard는 14개월 ($0.10/클러스터/시간), Extended는 추가 12개월 ($0.60/클러스터/시간)**

**설명:**
EKS의 각 Kubernetes 버전은 14개월의 Standard Support($0.10/클러스터/시간)를 받고, 이후 12개월의 Extended Support($0.60/클러스터/시간 — 6배 비용)에 진입합니다. 총 26개월 지원됩니다. Extended Support는 기본 활성화되어 있습니다. Extended Support도 종료되면 클러스터가 자동 업그레이드됩니다. 이 가격 차이는 지원 버전을 유지하는 인센티브가 됩니다.

</details>

---

3. Sidecar Containers가 GA로 졸업한 Kubernetes 버전은?
   - A) 1.28 (alpha로 최초 도입)
   - B) 1.31
   - C) 1.33
   - D) 1.35

<details>
<summary>정답 보기</summary>

**정답: C) 1.33**

**설명:**
Native Sidecar Containers(KEP-753)의 졸업 경로: alpha v1.28 (2023년 8월), beta v1.29 (2023년 12월), GA v1.33 (2025년 4월). 사이드카는 `restartPolicy: Always`를 가진 init 컨테이너로 정의되며, 애플리케이션 컨테이너 전에 시작되고, Pod 수명 동안 계속 실행되며, 메인 컨테이너 후에 종료됩니다. 이를 통해 Job에서 "좀비 사이드카" 문제가 해결되었습니다.

</details>

---

4. In-Place Pod Resize 기능과 GA 도달 시점은?
   - A) Pod 레플리카를 재배포 없이 변경; 1.30에서 GA
   - B) 실행 중인 Pod의 CPU/메모리 요청과 한도를 재시작 없이 수정; 1.35에서 GA
   - C) PersistentVolume 온라인 크기 조정; 1.31에서 GA
   - D) 실행 중인 Pod의 컨테이너 이미지 변경; 1.34에서 GA

<details>
<summary>정답 보기</summary>

**정답: B) 실행 중인 Pod의 CPU/메모리 요청과 한도를 재시작 없이 수정; 1.35에서 GA**

**설명:**
In-Place Pod Resize(KEP-1287)는 실행 중인 Pod의 CPU와 메모리 요청/한도를 변경 가능하게 합니다. 졸업: alpha v1.27, beta v1.33, GA v1.35 (2025년 12월). v1.33부터 `/resize` 서브리소스를 통해 수정합니다. `resizePolicy` 필드로 리소스 유형별 컨테이너 재시작 필요 여부를 제어합니다. VPA 통합에 혁신적인 기능으로, Pod 중단 없이 리소스 최적화가 가능합니다.

</details>

---

5. Kubernetes 1.31에서 Dynamic Resource Allocation(DRA)에 발생한 주요 변화는?
   - A) DRA가 Deprecated되고 Device Plugins v2로 대체
   - B) Classic DRA가 제거되고 Structured Parameters DRA만 남음 (이후 1.34에서 GA)
   - C) DRA가 alpha에서 바로 GA로 졸업
   - D) DRA가 GPU 외에 네트워크 장치 지원 추가

<details>
<summary>정답 보기</summary>

**정답: B) Classic DRA가 제거되고 Structured Parameters DRA만 남음 (이후 1.34에서 GA)**

**설명:**
DRA는 대규모 재설계를 거쳤습니다. Classic DRA(KEP-3063, v1.26부터 alpha)는 스케줄러와 클러스터 오토스케일러가 이해할 수 없는 불투명한 벤더 파라미터를 사용했습니다. Structured Parameters DRA(KEP-4381)가 `ResourceSlice` 객체를 사용한 Kubernetes 네이티브 형식으로 대체했습니다. v1.31에서 Classic DRA가 완전히 제거되었고, Structured DRA는 beta v1.32, GA v1.34로 진행했습니다. AI/ML 워크로드의 GPU/가속기 스케줄링에 핵심적입니다.

</details>

---

6. Kubernetes 1.30에서 웹훅 없이 선언적 Admission Control을 가능하게 한 GA 기능은?
   - A) OPA Gatekeeper v4
   - B) Kyverno Native Policies
   - C) CEL 표현식을 사용하는 ValidatingAdmissionPolicy
   - D) Pod Security Standards 적용

<details>
<summary>정답 보기</summary>

**정답: C) CEL 표현식을 사용하는 ValidatingAdmissionPolicy**

**설명:**
ValidatingAdmissionPolicy(KEP-3488)는 CEL(Common Expression Language) 표현식을 사용한 인프로세스 검증을 제공하여 외부 웹훅 서버가 불필요합니다. 졸업: alpha v1.26, beta v1.28, GA v1.30 (2024년 4월). ValidatingAdmissionPolicy(규칙), ValidatingAdmissionPolicyBinding(리소스 바인딩), 선택적 파라미터 CRD의 세 가지 리소스 타입을 사용합니다. 웹훅 기반 대비 레이턴시, 복잡성, 장애 도메인이 감소합니다.

</details>

---

7. KYAML이란 무엇이며 현재 상태는?
   - A) Kubernetes YAML 린터; 1.35에서 GA
   - B) 엄격한 형식을 사용하는 Kubernetes 전용 안전한 YAML 하위 집합; 1.35에서 beta (기본 활성화)
   - C) YAML-to-JSON 변환 도구; 1.34에서 alpha
   - D) Kubernetes 매니페스트 유효성 검사 스키마; 1.30부터 stable

<details>
<summary>정답 보기</summary>

**정답: B) 엄격한 형식을 사용하는 Kubernetes 전용 안전한 YAML 하위 집합; 1.35에서 beta (기본 활성화)**

**설명:**
KYAML은 YAML의 악명 높은 모호성을 제거하는 Kubernetes 전용 엄격한 YAML 하위 집합입니다. 맵에는 중괄호({}), 리스트에는 대괄호([]), 모든 문자열에는 쌍따옴표를 사용합니다. v1.34에서 alpha로 도입되고, v1.35 (2025년 12월)에서 beta로 졸업하여 기본 활성화되었습니다. `KUBECTL_KYAML=false`로 비활성화 가능합니다. YAML의 "노르웨이 문제"(NO가 boolean false로 해석) 같은 오래된 문제를 해결합니다.

</details>

---

8. EKS 클러스터의 권장 버전 업그레이드 계획 전략은?
   - A) 업그레이드 빈도를 줄이기 위해 버전 건너뛰기 (예: 1.29 → 1.33)
   - B) 한 번에 하나의 마이너 버전씩 업그레이드하고, 스테이징에서 feature gate 테스트, API 호환성 및 애드온 정렬 확인 후 프로덕션 적용
   - C) 항상 최신 버전을 사용하고 롤백을 위해 Extended Support에 의존
   - D) 안정성을 보장하기 위해 버전이 Extended Support에 진입한 후 업그레이드

<details>
<summary>정답 보기</summary>

**정답: B) 한 번에 하나의 마이너 버전씩 업그레이드하고, 스테이징에서 feature gate 테스트, API 호환성 및 애드온 정렬 확인 후 프로덕션 적용**

**설명:**
EKS는 순차적 마이너 버전 업그레이드를 요구합니다 (1.33 → 1.34 → 1.35; 건너뛰기 불가). 모범 사례: (1) 스테이징에서 새 feature gate와 API 변경 사항을 먼저 테스트, (2) 대상 버전과의 애드온 호환성 확인, (3) `kubectl convert`로 Deprecated API 확인, (4) 컨트롤 플레인 → 애드온 → 노드 그룹 순서로 업그레이드. Standard Support 유지 시 Extended Support의 6배 비용 증가를 피하고 최신 보안 패치에 접근할 수 있습니다.

</details>
