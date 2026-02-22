# ArgoCD 설치 퀴즈

이 퀴즈는 ArgoCD 설치 및 구성에 대한 이해도를 테스트합니다.

1. 프로덕션 환경에서 ArgoCD를 설치하는 권장 방법은 무엇인가요?
   - A) GitHub URL에서 kubectl apply 사용
   - B) 커스텀 values를 사용한 Helm 차트
   - C) Docker Compose
   - D) 수동 바이너리 설치

<details>
<summary>정답 보기</summary>

**정답: B) 커스텀 values를 사용한 Helm 차트**

**설명:**
ArgoCD는 공식 매니페스트에서 kubectl apply를 사용하여 설치할 수 있지만, 프로덕션 환경에서는 Helm 차트를 사용하는 것이 권장됩니다. 더 쉬운 사용자 정의, 업그레이드 및 구성 값 관리가 가능하기 때문입니다.

</details>

2. ArgoCD는 기본적으로 어떤 네임스페이스에 설치되나요?
   - A) default
   - B) kube-system
   - C) argocd
   - D) gitops

<details>
<summary>정답 보기</summary>

**정답: C) argocd**

**설명:**
관례적으로 ArgoCD는 `argocd` 네임스페이스에 설치됩니다. 이렇게 하면 ArgoCD 컴포넌트가 격리되고 RBAC 및 리소스 쿼터를 더 쉽게 관리할 수 있습니다.

</details>

3. ArgoCD Repo Server 컴포넌트의 목적은 무엇인가요?
   - A) 애플리케이션 상태 저장
   - B) Git 리포지토리 클론 및 Kubernetes 매니페스트 생성
   - C) Web UI 제공
   - D) 사용자 인증 관리

<details>
<summary>정답 보기</summary>

**정답: B) Git 리포지토리 클론 및 Kubernetes 매니페스트 생성**

**설명:**
Repo Server는 Git 리포지토리를 클론하고 다양한 소스(Helm, Kustomize, 일반 YAML)에서 Kubernetes 매니페스트를 생성하는 역할을 합니다. 성능을 위해 리포지토리 데이터를 캐시합니다.

</details>

4. ArgoCD 설치 후 초기 관리자 비밀번호는 어떻게 가져오나요?
   - A) 설치 중에 출력됨
   - B) argocd-initial-admin-secret이라는 Secret에서
   - C) ArgoCD ConfigMap에서
   - D) 항상 "admin"

<details>
<summary>정답 보기</summary>

**정답: B) argocd-initial-admin-secret이라는 Secret에서**

**설명:**
초기 관리자 비밀번호는 자동 생성되어 `argocd-initial-admin-secret`이라는 Kubernetes Secret에 저장됩니다. 다음 명령으로 가져올 수 있습니다: `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d`

</details>

5. 리소스를 적게 사용하지만 기능이 제한된 ArgoCD 설치 모드는 무엇인가요?
   - A) HA 모드
   - B) Core 모드
   - C) Lite 모드
   - D) Minimal 모드

<details>
<summary>정답 보기</summary>

**정답: B) Core 모드**

**설명:**
ArgoCD Core 모드는 필수 컴포넌트(Application Controller 및 Repo Server)만 설치하며 API Server, UI 또는 Dex는 포함되지 않습니다. 이 모드는 ArgoCD가 Git과 CLI를 통해서만 관리되는 환경에 적합합니다.

</details>
