# ArgoCD 모범 사례 퀴즈

이 퀴즈는 ArgoCD 모범 사례와 운영 패턴에 대한 이해도를 테스트합니다.

1. ArgoCD 자체 구성을 관리하는 권장 접근 방식은 무엇인가요?
   - A) UI를 통한 수동 구성
   - B) ArgoCD로 ArgoCD 관리 (app-of-apps 패턴)
   - C) kubectl apply 직접 사용
   - D) 구성은 절대 변경하면 안 됨

<details>
<summary>정답 보기</summary>

**정답: B) ArgoCD로 ArgoCD 관리 (app-of-apps 패턴)**

**설명:**
"app-of-apps" 패턴은 ArgoCD가 자체 구성과 다른 ArgoCD Applications를 관리하도록 합니다. 이렇게 하면 ArgoCD의 구성이 버전 관리되고 GitOps 원칙을 따릅니다.

</details>

2. GitOps를 위한 권장 리포지토리 구조는 무엇인가요?
   - A) 애플리케이션 코드와 매니페스트를 같은 리포지토리에 혼합
   - B) 애플리케이션 코드와 배포 매니페스트를 위한 별도 리포지토리
   - C) 모든 것을 단일 파일에 저장
   - D) 공개 리포지토리의 Helm 차트만 사용

<details>
<summary>정답 보기</summary>

**정답: B) 애플리케이션 코드와 배포 매니페스트를 위한 별도 리포지토리**

**설명:**
애플리케이션 코드를 배포 매니페스트와 분리하면 더 명확한 감사 추적을 제공하고, 다른 팀이 각각을 관리할 수 있으며, 배포 변경에서 CI 트리거를 방지합니다.

</details>

3. 환경별 구성을 어떻게 처리해야 하나요?
   - A) 각 환경에 대해 별도의 Applications 생성
   - B) 환경별 Kustomize 오버레이 또는 Helm values 파일 사용
   - C) 매니페스트에 값 하드코딩
   - D) 파드에서 환경 변수 사용

<details>
<summary>정답 보기</summary>

**정답: B) 환경별 Kustomize 오버레이 또는 Helm values 파일 사용**

**설명:**
Kustomize 오버레이 또는 Helm values 파일을 사용하면 공통 기본 구성을 유지하면서 환경별로 특정 값(복제본, 리소스, 도메인)을 사용자 정의할 수 있습니다.

</details>

4. 환경 간 변경 사항을 프로모션하는 권장 접근 방식은 무엇인가요?
   - A) 프로덕션 브랜치에 직접 커밋
   - B) 스테이징에서 프로덕션으로 리뷰가 있는 Pull Request
   - C) UI에서 수동 동기화
   - D) 리뷰 없이 자동 프로모션

<details>
<summary>정답 보기</summary>

**정답: B) 스테이징에서 프로덕션으로 리뷰가 있는 Pull Request**

**설명:**
프로모션에 Pull Request를 사용하면 변경 사항이 프로덕션에 도달하기 전에 검토되고, 감사 추적을 제공하며, 병합 전에 자동화된 검사(테스트, 정책 검증)를 허용합니다.

</details>

5. GitOps 워크플로우에서 시크릿을 어떻게 처리해야 하나요?
   - A) Git에 일반 텍스트 시크릿 커밋
   - B) 암호화된 시크릿(Sealed Secrets, SOPS) 또는 외부 시크릿 관리자 사용
   - C) 각 클러스터에서 시크릿 수동 생성
   - D) 환경 변수에 시크릿 저장

<details>
<summary>정답 보기</summary>

**정답: B) 암호화된 시크릿(Sealed Secrets, SOPS) 또는 외부 시크릿 관리자 사용**

**설명:**
시크릿은 Git에 일반 텍스트로 저장하면 안 됩니다. Sealed Secrets 또는 SOPS와 같은 암호화 도구를 사용하거나 External Secrets Operator와 함께 HashiCorp Vault와 같은 외부 시크릿 관리자를 사용하세요.

</details>
