# Feature Flags와 OpenFeature 퀴즈

1. OpenFeature의 Provider 모델의 핵심 장점은?
   - A) 특정 벤더에 종속되어 최적의 성능을 제공
   - B) 벤더 중립적인 API로 Feature Flag 백엔드를 자유롭게 교체 가능
   - C) 자체 Feature Flag 서버를 반드시 운영해야 함
   - D) REST API만 지원

<details>
<summary>정답 보기</summary>

**정답: B) 벤더 중립적인 API로 Feature Flag 백엔드를 자유롭게 교체 가능**

**설명:**
OpenFeature는 CNCF 표준으로, 벤더 중립적인 SDK API를 제공합니다. Provider 인터페이스를 통해 flagd, LaunchDarkly, Flagsmith 등 다양한 백엔드를 교체할 수 있으며, 애플리케이션 코드 변경 없이 Provider만 변경하면 됩니다.

</details>

---

2. flagd의 Kubernetes 배포 방식 중 Sidecar 모드와 Standalone 모드의 차이점은?
   - A) Sidecar는 성능이 좋고, Standalone은 관리가 쉬움
   - B) Sidecar는 각 Pod에 주입되어 지연이 최소화되고, Standalone은 중앙 서비스로 운영
   - C) Sidecar는 TCP만 지원하고, Standalone은 HTTP만 지원
   - D) Sidecar는 CRD를 사용하고, Standalone은 ConfigMap만 사용

<details>
<summary>정답 보기</summary>

**정답: B) Sidecar는 각 Pod에 주입되어 지연이 최소화되고, Standalone은 중앙 서비스로 운영**

**설명:**
Sidecar 모드에서는 OpenFeature Operator가 각 Pod에 flagd 컨테이너를 주입하여 로컬 통신으로 지연을 최소화합니다. Standalone 모드에서는 flagd를 별도의 Deployment로 운영하여 중앙에서 관리하며, 리소스 효율성이 높지만 네트워크 호출이 필요합니다.

</details>

---

3. Feature Flag의 Evaluation Context에 포함되는 정보의 역할은?
   - A) 빌드 정보를 전달하여 컴파일 타임에 Flag를 결정
   - B) 사용자 ID, 리전, 환경 등의 컨텍스트로 타겟팅 규칙을 평가
   - C) 데이터베이스 연결 정보를 전달
   - D) Kubernetes 노드 정보를 전달

<details>
<summary>정답 보기</summary>

**정답: B) 사용자 ID, 리전, 환경 등의 컨텍스트로 타겟팅 규칙을 평가**

**설명:**
Evaluation Context는 Flag 평가 시 동적으로 전달되는 메타데이터입니다. 사용자 ID, 리전, 환경(dev/staging/prod), 사용자 그룹 등의 정보를 포함하며, 타겟팅 규칙에서 이 정보를 기반으로 특정 사용자나 그룹에게만 기능을 활성화할 수 있습니다.

</details>

---

4. Dark Launch 패턴에서 Feature Flag의 역할은?
   - A) 서비스를 완전히 숨기고 접근을 차단
   - B) 새 기능의 코드를 배포하되, Flag로 비활성화하여 사용자에게 노출하지 않음
   - C) 서버를 다크 모드로 전환
   - D) 야간에만 배포를 실행

<details>
<summary>정답 보기</summary>

**정답: B) 새 기능의 코드를 배포하되, Flag로 비활성화하여 사용자에게 노출하지 않음**

**설명:**
Dark Launch는 새 기능의 코드를 프로덕션에 배포하지만 Feature Flag로 비활성화하여 사용자에게는 보이지 않게 합니다. 이후 Flag를 점진적으로 활성화하여 일부 사용자부터 테스트하고, 문제가 없으면 전체 사용자에게 노출합니다. 배포와 릴리스를 분리하는 핵심 패턴입니다.

</details>

---

5. Feature Flag as Code (GitOps)의 장점은?
   - A) GUI에서만 Flag를 관리할 수 있음
   - B) Flag 변경을 Git PR로 관리하여 리뷰, 감사, 롤백이 가능
   - C) Flag 평가 속도가 빨라짐
   - D) 서버 리소스를 절약

<details>
<summary>정답 보기</summary>

**정답: B) Flag 변경을 Git PR로 관리하여 리뷰, 감사, 롤백이 가능**

**설명:**
Feature Flag as Code는 FeatureFlag CR을 Git 리포지토리에서 관리하여, PR 기반의 리뷰와 승인 프로세스를 적용합니다. 변경 이력이 Git에 기록되어 감사가 가능하고, 문제 발생 시 Git revert로 빠르게 롤백할 수 있습니다. ArgoCD나 Flux로 자동 동기화됩니다.

</details>

---

6. Feature Flag의 기술 부채를 방지하기 위한 모범 사례는?
   - A) 모든 Flag를 영구적으로 유지
   - B) Flag에 만료일을 설정하고, 릴리스 완료 후 Flag 코드를 정리
   - C) Flag 수를 제한하지 않고 자유롭게 생성
   - D) Flag 이름에 날짜를 포함하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) Flag에 만료일을 설정하고, 릴리스 완료 후 Flag 코드를 정리**

**설명:**
Feature Flag는 임시적인 릴리스 도구로 사용되는 경우가 많습니다. 릴리스가 완료되면 Flag와 관련 조건문 코드를 정리해야 기술 부채가 쌓이지 않습니다. Flag에 만료일이나 소유자를 태깅하고, 정기적으로 사용되지 않는 Flag를 감지하여 제거하는 프로세스를 운영해야 합니다.

</details>

---

7. OpenFeature Operator가 Kubernetes에서 제공하는 핵심 기능은?
   - A) Pod에 자동으로 flagd 사이드카를 주입하고 FeatureFlag CRD를 관리
   - B) Kubernetes 클러스터의 보안을 감사
   - C) 컨테이너 이미지를 자동으로 빌드
   - D) HPA를 자동으로 구성

<details>
<summary>정답 보기</summary>

**정답: A) Pod에 자동으로 flagd 사이드카를 주입하고 FeatureFlag CRD를 관리**

**설명:**
OpenFeature Operator는 Kubernetes에서 Feature Flag를 네이티브하게 관리하기 위한 Operator입니다. FeatureFlag CRD로 Flag를 선언적으로 관리하고, FeatureFlagSource CRD로 Flag 소스를 정의하며, 어노테이션이 있는 Pod에 자동으로 flagd 사이드카 컨테이너를 주입합니다.

</details>

---

8. Flagger + Feature Flag 조합에서 메트릭 기반 자동 롤아웃의 동작 방식은?
   - A) Feature Flag가 직접 트래픽을 제어
   - B) Flagger가 Canary 트래픽을 전환하고, Feature Flag는 기능 레벨에서 점진적 노출을 제어
   - C) Feature Flag가 Flagger를 완전히 대체
   - D) 두 도구가 동일한 메트릭을 사용

<details>
<summary>정답 보기</summary>

**정답: B) Flagger가 Canary 트래픽을 전환하고, Feature Flag는 기능 레벨에서 점진적 노출을 제어**

**설명:**
Flagger와 Feature Flag는 서로 다른 레벨에서 동작합니다. Flagger는 인프라 레벨에서 트래픽을 분할하고 메트릭을 분석하여 배포를 제어합니다. Feature Flag는 애플리케이션 레벨에서 개별 기능의 활성화/비활성화를 제어합니다. 함께 사용하면 배포(Flagger)와 릴리스(Feature Flag)를 완전히 분리할 수 있습니다.

</details>
