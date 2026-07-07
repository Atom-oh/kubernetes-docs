# GitOps 멀티 클러스터 퀴즈

> **관련 문서**: [GitOps 멀티 클러스터](../../ops/04-gitops-multi-cluster.md)

## 객관식 문제

### 1. ArgoCD Hub-Spoke 모델에서 Hub 클러스터의 역할은 무엇인가요?

- A) 모든 애플리케이션 워크로드 실행
- B) 중앙에서 여러 클러스터의 배포를 관리하고 조정
- C) 데이터베이스 호스팅
- D) 로드 밸런싱

<details>
<summary>정답 보기</summary>

**정답: B) 중앙에서 여러 클러스터의 배포를 관리하고 조정**

**설명:**
Hub-Spoke 모델에서 Hub 클러스터는 ArgoCD가 설치된 중앙 관리 클러스터입니다. 이 클러스터에서 여러 Spoke(워크로드) 클러스터들의 애플리케이션 배포를 중앙에서 관리하고 모니터링합니다. 실제 워크로드는 Spoke 클러스터에서 실행됩니다.

</details>

### 2. ArgoCD ApplicationSet의 주요 용도는 무엇인가요?

- A) 단일 애플리케이션 배포
- B) 템플릿 기반으로 여러 Application을 자동 생성
- C) ArgoCD 서버 설정
- D) Git 저장소 연결

<details>
<summary>정답 보기</summary>

**정답: B) 템플릿 기반으로 여러 Application을 자동 생성**

**설명:**
ApplicationSet은 템플릿과 Generator를 사용하여 여러 ArgoCD Application을 자동으로 생성합니다. 예를 들어, 동일한 애플리케이션을 여러 클러스터나 환경에 배포하거나, Git 디렉토리 구조를 기반으로 Application을 동적으로 생성할 수 있습니다.

</details>

### 3. ArgoCD HA(High Availability) 구성에서 redis-ha를 사용하는 이유는 무엇인가요?

- A) 웹 UI 성능 향상
- B) Git 저장소 캐싱
- C) ArgoCD 컴포넌트 간 상태 공유 및 캐시 저장
- D) 로그 저장

<details>
<summary>정답 보기</summary>

**정답: C) ArgoCD 컴포넌트 간 상태 공유 및 캐시 저장**

**설명:**
ArgoCD는 Redis를 사용하여 컴포넌트 간 상태 공유, 애플리케이션 캐시, 클러스터 정보 캐시 등을 저장합니다. HA 구성에서 redis-ha를 사용하면 Redis 장애 시에도 ArgoCD가 정상 작동하고, 여러 ArgoCD 서버 인스턴스가 동일한 상태를 공유할 수 있습니다.

</details>

### 4. ApplicationSet의 Cluster Generator는 어떤 정보를 기반으로 Application을 생성하나요?

- A) Git 저장소의 디렉토리 구조
- B) ArgoCD에 등록된 클러스터 목록
- C) Kubernetes 네임스페이스 목록
- D) ConfigMap의 키-값 쌍

<details>
<summary>정답 보기</summary>

**정답: B) ArgoCD에 등록된 클러스터 목록**

**설명:**
Cluster Generator는 ArgoCD에 등록된 클러스터 목록을 순회하면서 각 클러스터에 대해 Application을 생성합니다. 클러스터의 이름, URL, 레이블 등의 정보를 템플릿에서 사용할 수 있어 멀티 클러스터 배포에 유용합니다.

</details>

### 5. ArgoCD에서 새 클러스터를 등록할 때 사용하는 CLI 명령은 무엇인가요?

- A) argocd cluster create
- B) argocd cluster add
- C) argocd cluster register
- D) argocd cluster connect

<details>
<summary>정답 보기</summary>

**정답: B) argocd cluster add**

**설명:**
`argocd cluster add <context-name>` 명령을 사용하여 kubeconfig의 context를 ArgoCD에 클러스터로 등록합니다. 이 명령은 대상 클러스터에 ArgoCD가 사용할 ServiceAccount와 ClusterRoleBinding을 생성하고 연결 정보를 ArgoCD에 저장합니다.

</details>

### 6. ApplicationSet의 Git Generator - Directory는 어떤 방식으로 Application을 생성하나요?

- A) Git 브랜치마다 하나의 Application 생성
- B) 지정된 경로 아래의 각 디렉토리마다 Application 생성
- C) Git 태그마다 하나의 Application 생성
- D) Git 커밋마다 하나의 Application 생성

<details>
<summary>정답 보기</summary>

**정답: B) 지정된 경로 아래의 각 디렉토리마다 Application 생성**

**설명:**
Git Generator - Directory는 Git 저장소의 특정 경로 아래에 있는 각 디렉토리를 순회하면서 Application을 생성합니다. 예를 들어, `apps/*` 패턴을 지정하면 apps 디렉토리 아래의 각 하위 디렉토리(apps/frontend, apps/backend 등)에 대해 Application이 생성됩니다.

</details>

### 7. ArgoCD Application의 syncPolicy.automated 설정에서 selfHeal의 역할은 무엇인가요?

- A) ArgoCD 자체 복구
- B) 클러스터 상태가 Git과 다를 때 자동으로 Git 상태로 복원
- C) Git 저장소 자동 복구
- D) 네트워크 연결 자동 복구

<details>
<summary>정답 보기</summary>

**정답: B) 클러스터 상태가 Git과 다를 때 자동으로 Git 상태로 복원**

**설명:**
selfHeal: true 설정은 누군가 kubectl로 직접 클러스터 리소스를 수정했을 때 ArgoCD가 자동으로 이를 감지하고 Git에 정의된 상태로 되돌립니다. 이를 통해 Git을 단일 진실 공급원(Single Source of Truth)으로 유지할 수 있습니다.

</details>

### 8. ArgoCD HA 구성에서 argocd-server의 replicas를 2 이상으로 설정할 때 필요한 추가 구성은 무엇인가요?

- A) PodDisruptionBudget만 설정
- B) Ingress에서 세션 어피니티 또는 스티키 세션 설정
- C) 각 서버에 고유한 포트 할당
- D) 추가 구성 불필요

<details>
<summary>정답 보기</summary>

**정답: B) Ingress에서 세션 어피니티 또는 스티키 세션 설정**

**설명:**
ArgoCD 웹 UI는 WebSocket을 사용하므로 여러 서버 인스턴스가 있을 때 세션 어피니티(스티키 세션)를 설정해야 합니다. 이를 통해 클라이언트가 동일한 서버 인스턴스에 연결을 유지하여 실시간 업데이트가 정상 작동합니다.

</details>

### 9. ApplicationSet의 Matrix Generator는 무엇을 위해 사용하나요?

- A) 행렬 연산 수행
- B) 두 Generator의 조합으로 모든 가능한 조합 생성
- C) 데이터 변환
- D) 숫자 범위 생성

<details>
<summary>정답 보기</summary>

**정답: B) 두 Generator의 조합으로 모든 가능한 조합 생성**

**설명:**
Matrix Generator는 두 개의 Generator를 조합하여 가능한 모든 조합에 대해 Application을 생성합니다. 예를 들어, Cluster Generator(3개 클러스터)와 List Generator(2개 환경)를 조합하면 3 x 2 = 6개의 Application이 생성됩니다.

</details>

### 10. ArgoCD에서 멀티 클러스터 배포 시 클러스터별로 다른 설정을 적용하려면 어떤 기능을 사용해야 하나요?

- A) 별도의 Git 저장소 사용
- B) ApplicationSet의 템플릿과 Generator 파라미터 활용
- C) 각 클러스터에 ArgoCD 별도 설치
- D) Helm 차트만 사용

<details>
<summary>정답 보기</summary>

**정답: B) ApplicationSet의 템플릿과 Generator 파라미터 활용**

**설명:**
ApplicationSet에서 Generator는 각 클러스터의 메타데이터(이름, 레이블, URL 등)를 파라미터로 제공하고, 템플릿에서 이 파라미터를 사용하여 클러스터별로 다른 설정을 적용할 수 있습니다. 예를 들어, <code v-pre>{{cluster.name}}</code>을 사용하여 클러스터별 values 파일을 지정할 수 있습니다.

</details>
