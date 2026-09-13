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
AppProjects는 허용되는 소스, 대상 및 리소스에 대한 제한이 있는 Applications의 논리적 그룹을 제공합니다. 각 팀의 Argo CD 배포 범위를 제한하지만 Kubernetes RBAC, Pod Security Admission, 네트워크와 쿼터 격리는 별도로 구성해야 합니다.

</details>

2. AppProject의 `sourceRepos` 필드는 무엇을 제어하나요?
   - A) 사용할 수 있는 Git 브랜치
   - B) Applications가 사용할 수 있는 소스 저장소(Git/Helm/OCI)
   - C) 컨테이너 이미지 리포지토리
   - D) Helm 차트 버전

<details>
<summary>정답 보기</summary>

**정답: B) Applications가 사용할 수 있는 소스 저장소(Git/Helm/OCI)**

**설명:**
`sourceRepos` 필드는 이 프로젝트의 Applications가 소스로 사용할 수 있는 Git·Helm·OCI 저장소를 제한합니다. Git 브랜치나 컨테이너 이미지 레지스트리를 직접 제한하는 필드는 아닙니다. `*`를 사용하면 모든 리포지토리를 허용하고, 특정 URL은 해당 리포지토리만으로 제한합니다.

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
`destinations` 필드는 허용되는 클러스터와 네임스페이스 조합을 정의합니다. 각 항목은 허용된 server 또는 등록된 name과 namespace 조합을 지정합니다. 배포 대상 제한이며 Application CR의 위치를 지정하는 sourceNamespaces와 다릅니다.

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
새 커스텀 프로젝트에서 허용 목록을 생략하면 클러스터 범위 리소스를 관리할 수 없습니다. 초기 default 프로젝트는 명시적으로 모든 종류를 허용하므로 예외입니다. `clusterResourceWhitelist`는 프로젝트의 Applications가 관리할 수 있는 특정 종류(예: Namespaces 또는 ClusterRoles)를 허용합니다.

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
프로젝트 역할은 AppProject의 `spec.roles` 필드에 정의됩니다. 각 역할에는 이름, 설명, 정책(허용되는 작업), 발급된 JWT의 메타데이터 또는 그룹 바인딩이 있습니다. JWT 서명 발급은 CLI/API로 수행하며 메타데이터 선언만으로 토큰이 생성되지는 않습니다.

</details>
