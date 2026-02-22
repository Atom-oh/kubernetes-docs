# FluxCD 퀴즈

이 퀴즈는 FluxCD와 그 컴포넌트에 대한 이해도를 테스트합니다.

1. FluxCD는 어떤 CNCF 상태를 가지고 있나요?
   - A) Sandbox
   - B) Incubating
   - C) Graduated
   - D) Archived

<details>
<summary>정답 보기</summary>

**정답: C) Graduated**

**설명:**
FluxCD는 2022년 11월에 CNCF를 졸업했으며, 이는 성숙도에 도달했고 프로덕션 환경에서 널리 채택되었음을 나타냅니다.

</details>

2. Git 리포지토리에서 아티팩트를 가져오는 FluxCD 컨트롤러는 무엇인가요?
   - A) Kustomize Controller
   - B) Helm Controller
   - C) Source Controller
   - D) Notification Controller

<details>
<summary>정답 보기</summary>

**정답: C) Source Controller**

**설명:**
Source Controller는 Git 리포지토리(GitRepository), Helm 리포지토리(HelmRepository), OCI 레지스트리(OCIRepository), S3 버킷(Bucket)을 포함한 외부 소스에서 아티팩트를 가져오는 역할을 합니다.

</details>

3. FluxCD가 Kustomize 구성을 배포하는 데 사용하는 CRD는 무엇인가요?
   - A) Application
   - B) Kustomization
   - C) KustomizeConfig
   - D) Deployment

<details>
<summary>정답 보기</summary>

**정답: B) Kustomization**

**설명:**
Kustomization CRD는 Kustomize 오버레이를 클러스터에 적용하는 방법을 정의하는 데 사용됩니다. 소스(GitRepository)를 참조하고 Kustomize 구성의 경로를 지정합니다.

</details>

4. FluxCD는 Helm 차트 배포를 어떻게 처리하나요?
   - A) Application CRD 사용
   - B) HelmRelease CRD 사용
   - C) helm CLI 직접 사용
   - D) Helm 지원 안 함

<details>
<summary>정답 보기</summary>

**정답: B) HelmRelease CRD 사용**

**설명:**
HelmRelease CRD는 Helm 차트 릴리스를 선언적으로 관리하는 데 사용됩니다. 차트 소스, 버전, values 및 업그레이드/롤백 정책을 지정합니다.

</details>

5. FluxCD의 ImageUpdateAutomation의 목적은 무엇인가요?
   - A) 이미지 취약점 스캔
   - B) 새 버전이 감지되면 Git에서 이미지 태그 자동 업데이트
   - C) 컨테이너 이미지 빌드
   - D) 이미지 풀 시크릿 관리

<details>
<summary>정답 보기</summary>

**정답: B) 새 버전이 감지되면 Git에서 이미지 태그 자동 업데이트**

**설명:**
ImageUpdateAutomation은 ImageRepository 및 ImagePolicy와 함께 작동하여 새 컨테이너 이미지 태그를 감지하고 Git 리포지토리에 업데이트를 자동으로 커밋하여 자동 배포를 가능하게 합니다.

</details>

6. 클러스터에 FluxCD를 부트스트랩하는 데 사용되는 명령은 무엇인가요?
   - A) flux install
   - B) flux bootstrap
   - C) flux init
   - D) flux setup

<details>
<summary>정답 보기</summary>

**정답: B) flux bootstrap**

**설명:**
`flux bootstrap` 명령은 FluxCD 컴포넌트를 설치하고 클러스터를 관리하도록 Git 리포지토리를 구성합니다. GitHub, GitLab 및 일반 Git 서버를 포함한 다양한 Git 제공자를 지원합니다.

</details>

7. FluxCD는 멀티 테넌시를 어떻게 지원하나요?
   - A) ArgoCD와 같은 Projects 사용
   - B) 네임스페이스 격리 및 Kubernetes RBAC 사용
   - C) 멀티 테넌시 지원 안 함
   - D) 중앙 관리자 테넌트 사용

<details>
<summary>정답 보기</summary>

**정답: B) 네임스페이스 격리 및 Kubernetes RBAC 사용**

**설명:**
FluxCD는 각 테넌트가 Flux 리소스가 있는 자체 네임스페이스를 갖는 네임스페이스 격리와 접근 제어를 위한 Kubernetes 네이티브 RBAC를 결합하여 멀티 테넌시를 지원합니다.

</details>

8. FluxCD의 Notification Controller의 목적은 무엇인가요?
   - A) SMS 메시지 전송
   - B) 이벤트 처리 및 외부 서비스로 알림 전송
   - C) Git 웹훅만 관리
   - D) 파드 로그 모니터링

<details>
<summary>정답 보기</summary>

**정답: B) 이벤트 처리 및 외부 서비스로 알림 전송**

**설명:**
Notification Controller는 아웃바운드 알림(Slack, Teams 등으로의 Alerts)과 외부 이벤트가 발생할 때 재조정을 트리거하는 인바운드 웹훅(Receivers)을 모두 처리합니다.

</details>
