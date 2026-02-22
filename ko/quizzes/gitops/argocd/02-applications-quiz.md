# ArgoCD 애플리케이션 퀴즈

이 퀴즈는 ArgoCD 애플리케이션과 그 구성에 대한 이해도를 테스트합니다.

1. ArgoCD Application 리소스의 주요 목적은 무엇인가요?
   - A) 사용자 접근 제어 정의
   - B) 애플리케이션의 원하는 상태와 동기화 설정 지정
   - C) 알림 구성
   - D) 시크릿 관리

<details>
<summary>정답 보기</summary>

**정답: B) 애플리케이션의 원하는 상태와 동기화 설정 지정**

**설명:**
ArgoCD Application은 애플리케이션의 소스(Git 리포지토리, 경로, 리비전)와 대상(클러스터, 네임스페이스)을 정의하는 Kubernetes 커스텀 리소스이며, 동기화 정책과 헬스 체크도 포함합니다.

</details>

2. Application spec에서 매니페스트가 배포될 위치를 정의하는 필드는 무엇인가요?
   - A) source
   - B) target
   - C) destination
   - D) cluster

<details>
<summary>정답 보기</summary>

**정답: C) destination**

**설명:**
`destination` 필드는 애플리케이션의 리소스가 배포될 대상 클러스터(서버 URL 또는 이름)와 네임스페이스를 지정합니다.

</details>

3. Application에서 `spec.source.path` 필드는 무엇을 지정하나요?
   - A) ArgoCD 설치 경로
   - B) 매니페스트가 포함된 Git 리포지토리 내의 디렉토리
   - C) 로컬 파일 시스템 경로
   - D) API 서버 경로

<details>
<summary>정답 보기</summary>

**정답: B) 매니페스트가 포함된 Git 리포지토리 내의 디렉토리**

**설명:**
`source` 아래의 `path` 필드는 Kubernetes 매니페스트, Helm 차트 또는 Kustomize 구성이 포함된 Git 리포지토리 내의 디렉토리를 지정합니다.

</details>

4. 아직 존재하지 않는 특정 네임스페이스에 애플리케이션을 배포하려면 어떻게 해야 하나요?
   - A) 먼저 네임스페이스를 수동으로 생성
   - B) syncPolicy.syncOptions에 CreateNamespace=true 사용
   - C) 불가능함
   - D) pre-sync hook 사용

<details>
<summary>정답 보기</summary>

**정답: B) syncPolicy.syncOptions에 CreateNamespace=true 사용**

**설명:**
`syncPolicy.syncOptions`에 `CreateNamespace=true`를 설정하면 ArgoCD가 애플리케이션 리소스를 동기화하기 전에 대상 네임스페이스가 없으면 자동으로 생성합니다.

</details>

5. `targetRevision: HEAD`와 `targetRevision: main`의 차이점은 무엇인가요?
   - A) 차이 없음
   - B) HEAD는 항상 기본 브랜치를 가리키고, main은 명시적
   - C) HEAD가 더 빠름
   - D) main은 웹훅을 지원하고, HEAD는 지원하지 않음

<details>
<summary>정답 보기</summary>

**정답: B) HEAD는 항상 기본 브랜치를 가리키고, main은 명시적**

**설명:**
`HEAD`는 리포지토리의 기본 브랜치가 무엇이든 가리키는 심볼릭 참조이고, `main`은 main 브랜치를 명시적으로 지정합니다. 기본 브랜치가 변경되면 `HEAD`를 사용하는 것이 더 유연합니다.

</details>

6. Helm 리포지토리(Git이 아닌)에서 Helm 차트를 배포할 때 사용할 소스 유형은 무엇인가요?
   - A) git
   - B) helm
   - C) directory
   - D) kustomize

<details>
<summary>정답 보기</summary>

**정답: B) helm**

**설명:**
Helm 리포지토리에서 배포할 때는 `source.chart`와 `source.repoURL`을 Helm 리포지토리를 가리키도록 설정하면 ArgoCD가 Git 소스가 아닌 Helm 소스로 처리합니다.

</details>

7. `spec.source.helm.releaseName`을 설정하면 어떻게 되나요?
   - A) 새 Helm 리포지토리 생성
   - B) 기본 릴리스 이름(Application 이름)을 재정의
   - C) Helm hooks 활성화
   - D) 차트 버전 설정

<details>
<summary>정답 보기</summary>

**정답: B) 기본 릴리스 이름(Application 이름)을 재정의**

**설명:**
기본적으로 ArgoCD는 Application 이름을 Helm 릴리스 이름으로 사용합니다. `releaseName`을 명시적으로 설정하면 Helm 릴리스에 다른 이름을 사용할 수 있습니다.

</details>

8. ArgoCD Application에서 Helm values를 어떻게 지정하나요?
   - A) 리포지토리의 values 파일을 통해서만
   - B) Application spec에 인라인으로만
   - C) values 파일과 인라인 values 둘 다
   - D) values는 ConfigMap에 저장해야 함

<details>
<summary>정답 보기</summary>

**정답: C) values 파일과 인라인 values 둘 다**

**설명:**
ArgoCD는 `spec.source.helm.valueFiles`(리포지토리의 파일 참조) 및/또는 `spec.source.helm.values`(인라인 YAML)를 통해 Helm values를 지정하는 것을 지원합니다. 둘 다 함께 사용할 수 있으며, 인라인 values가 우선합니다.

</details>
