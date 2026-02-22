# ArgoCD 프로젝트와 RBAC 퀴즈

이 퀴즈는 ArgoCD Projects와 역할 기반 접근 제어에 대한 이해도를 테스트합니다.

1. ArgoCD Project(AppProject)의 주요 목적은 무엇인가요?
   - A) 관련 Git 리포지토리 그룹화
   - B) 접근 제한이 있는 애플리케이션의 논리적 그룹 제공
   - C) Kubernetes 네임스페이스 관리
   - D) CI/CD 파이프라인 구성

<details>
<summary>정답 보기</summary>

**정답: B) 접근 제한이 있는 애플리케이션의 논리적 그룹 제공**

**설명:**
AppProjects는 허용되는 소스, 대상 및 리소스에 대한 제한이 있는 Applications의 논리적 그룹을 제공합니다. 각 팀이 배포할 수 있는 것을 제한하여 멀티 테넌시를 가능하게 합니다.

</details>

2. AppProject의 `sourceRepos` 필드는 무엇을 제어하나요?
   - A) 사용할 수 있는 Git 브랜치
   - B) Applications가 매니페스트를 가져올 수 있는 Git 리포지토리
   - C) 컨테이너 이미지 리포지토리
   - D) Helm 차트 버전

<details>
<summary>정답 보기</summary>

**정답: B) Applications가 매니페스트를 가져올 수 있는 Git 리포지토리**

**설명:**
`sourceRepos` 필드는 이 프로젝트의 Applications가 소스로 사용할 수 있는 Git 리포지토리를 제한합니다. `*`를 사용하면 모든 리포지토리를 허용하고, 특정 URL은 해당 리포지토리만으로 제한합니다.

</details>

3. AppProject가 배포할 수 있는 클러스터와 네임스페이스를 어떻게 제한하나요?
   - A) `destinations` 필드 사용
   - B) `clusters` 필드 사용
   - C) `namespaces` 필드 사용
   - D) Kubernetes NetworkPolicies 사용

<details>
<summary>정답 보기</summary>

**정답: A) `destinations` 필드 사용**

**설명:**
`destinations` 필드는 허용되는 클러스터와 네임스페이스 조합을 정의합니다. 각 항목은 Applications가 대상으로 할 수 있는 `server`(클러스터 URL 또는 `*`)와 `namespace`(특정 네임스페이스 또는 `*`)를 지정합니다.

</details>

4. AppProject에서 `clusterResourceWhitelist`의 목적은 무엇인가요?
   - A) 특정 클러스터 범위 리소스 관리 허용
   - B) IP 주소 화이트리스트
   - C) 특정 사용자 허용
   - D) 특정 기능 활성화

<details>
<summary>정답 보기</summary>

**정답: A) 특정 클러스터 범위 리소스 관리 허용**

**설명:**
기본적으로 프로젝트는 클러스터 범위 리소스를 관리할 수 없습니다. `clusterResourceWhitelist`는 프로젝트의 Applications가 관리할 수 있는 특정 종류(예: Namespaces 또는 ClusterRoles)를 허용합니다.

</details>

5. ArgoCD Project 내에서 역할을 어떻게 정의하나요?
   - A) Kubernetes RBAC 사용
   - B) AppProject spec의 `roles` 필드 사용
   - C) 별도의 Role CRD 사용
   - D) 프로젝트에서 역할 정의 불가

<details>
<summary>정답 보기</summary>

**정답: B) AppProject spec의 `roles` 필드 사용**

**설명:**
프로젝트 역할은 AppProject의 `spec.roles` 필드에 정의됩니다. 각 역할에는 이름, 설명, 정책(허용되는 작업), 선택적 JWT 토큰 또는 그룹 바인딩이 있습니다.

</details>
