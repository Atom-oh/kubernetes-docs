# ArgoCD 퀴즈

이 퀴즈는 ArgoCD에 대한 이해를 테스트합니다.

## 퀴즈 문제

### 1. ArgoCD의 주요 목적은 무엇인가요?

A. 컨테이너 이미지 빌드 자동화  
B. 쿠버네티스 클러스터 모니터링  
C. GitOps 기반의 지속적 배포 자동화  
D. 쿠버네티스 클러스터 생성 및 관리  

<details>
<summary>정답 및 설명</summary>

**정답: C. GitOps 기반의 지속적 배포 자동화**

**설명:**
ArgoCD는 GitOps 기반의 지속적 배포 자동화 도구입니다. GitOps는 Git 저장소를 단일 진실 공급원(single source of truth)으로 사용하여 인프라와 애플리케이션을 선언적으로 관리하는 방법론입니다. ArgoCD는 Git 저장소에 저장된 쿠버네티스 매니페스트를 클러스터의 실제 상태와 지속적으로 비교하고 동기화하여 선언된 상태를 유지합니다.

**ArgoCD의 주요 특징:**
1. **자동 동기화**: Git 저장소의 변경 사항을 감지하고 클러스터에 자동으로 적용합니다.
2. **다중 클러스터 지원**: 여러 쿠버네티스 클러스터에 애플리케이션을 배포할 수 있습니다.
3. **웹 UI 및 CLI**: 직관적인 웹 인터페이스와 명령줄 도구를 제공합니다.
4. **SSO 통합**: 기업 ID 제공자와 통합하여 인증을 관리합니다.
5. **RBAC**: 세분화된 접근 제어를 제공합니다.
6. **상태 모니터링**: 애플리케이션 배포 상태를 실시간으로 모니터링합니다.
7. **롤백 지원**: 이전 버전으로 쉽게 롤백할 수 있습니다.

**ArgoCD 작동 방식:**
1. Git 저장소에 쿠버네티스 매니페스트(YAML 파일)를 저장합니다.
2. ArgoCD는 이 저장소를 지속적으로 모니터링합니다.
3. 변경 사항이 감지되면 ArgoCD는 클러스터의 상태를 Git 저장소의 상태와 비교합니다.
4. 차이가 있으면 ArgoCD는 클러스터를 Git 저장소에 정의된 상태로 동기화합니다.

**ArgoCD 아키텍처:**
```
+----------------+      +----------------+      +----------------+
|                |      |                |      |                |
|  Git 저장소    |----->|    ArgoCD      |----->|  쿠버네티스    |
|                |      |                |      |  클러스터      |
+----------------+      +----------------+      +----------------+
                               |
                               v
                        +----------------+
                        |                |
                        |    ArgoCD UI   |
                        |                |
                        +----------------+
```

**다른 옵션들의 문제점:**
- A. 컨테이너 이미지 빌드 자동화: 이는 주로 CI 도구(Jenkins, GitHub Actions 등)의 역할입니다.
- B. 쿠버네티스 클러스터 모니터링: 이는 주로 Prometheus, Grafana 등의 모니터링 도구의 역할입니다.
- D. 쿠버네티스 클러스터 생성 및 관리: 이는 주로 kOps, EKS, GKE 등의 클러스터 관리 도구의 역할입니다.
</details>

### 2. ArgoCD에서 'Application'은 무엇을 의미하나요?

A. 쿠버네티스 클러스터에 배포된 컨테이너화된 소프트웨어  
B. Git 저장소와 쿠버네티스 클러스터를 연결하는 ArgoCD의 사용자 정의 리소스  
C. ArgoCD 웹 인터페이스에서 실행되는 JavaScript 애플리케이션  
D. 쿠버네티스 클러스터에서 실행되는 ArgoCD 컨트롤러  

<details>
<summary>정답 및 설명</summary>

**정답: B. Git 저장소와 쿠버네티스 클러스터를 연결하는 ArgoCD의 사용자 정의 리소스**

**설명:**
ArgoCD에서 'Application'은 Git 저장소와 쿠버네티스 클러스터를 연결하는 사용자 정의 리소스(Custom Resource)입니다. Application 리소스는 소스 코드(Git 저장소)와 대상 환경(쿠버네티스 클러스터) 간의 매핑을 정의하고, ArgoCD가 이 두 환경 간의 상태를 동기화하는 방법을 지정합니다.

**Application 리소스의 주요 구성 요소:**
1. **소스(Source)**: Git 저장소 URL, 브랜치/태그/커밋, 경로 등을 지정합니다.
2. **대상(Destination)**: 쿠버네티스 클러스터 URL과 네임스페이스를 지정합니다.
3. **동기화 정책(Sync Policy)**: 자동 또는 수동 동기화, 프루닝, 자체 힐링 등의 동작을 정의합니다.
4. **리비전 히스토리(Revision History)**: 이전 배포 버전의 기록을 유지합니다.

**Application 리소스 예시:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: guestbook
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: guestbook
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

**Application 리소스의 상태:**
ArgoCD Application은 다음과 같은 상태를 가질 수 있습니다:
- **Synced**: Git 저장소와 클러스터 상태가 일치합니다.
- **OutOfSync**: Git 저장소와 클러스터 상태가 불일치합니다.
- **Unknown**: 애플리케이션 상태를 확인할 수 없습니다.
- **Degraded**: 애플리케이션이 배포되었지만 정상적으로 작동하지 않습니다.

**Application 관리 방법:**
1. **UI를 통한 생성**: ArgoCD 웹 인터페이스를 통해 Application을 생성할 수 있습니다.
2. **CLI를 통한 생성**: `argocd app create` 명령을 사용하여 Application을 생성할 수 있습니다.
3. **YAML 매니페스트**: Application YAML 매니페스트를 직접 적용할 수 있습니다.
4. **App of Apps 패턴**: 하나의 Application이 다른 여러 Application을 관리하는 패턴을 사용할 수 있습니다.

**다른 옵션들의 문제점:**
- A. 쿠버네티스 클러스터에 배포된 컨테이너화된 소프트웨어: 이는 일반적인 의미의 애플리케이션이지만, ArgoCD의 'Application' 리소스를 특정하게 설명하지는 않습니다.
- C. ArgoCD 웹 인터페이스에서 실행되는 JavaScript 애플리케이션: ArgoCD UI는 웹 애플리케이션이지만, 'Application' 리소스와는 다릅니다.
- D. 쿠버네티스 클러스터에서 실행되는 ArgoCD 컨트롤러: 이는 ArgoCD의 컨트롤러 컴포넌트를 설명하지만, 'Application' 리소스와는 다릅니다.
</details>
