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
### 3. ArgoCD에서 'Project'의 주요 목적은 무엇인가요?

A. 여러 Git 저장소를 그룹화하는 논리적 단위  
B. 여러 쿠버네티스 클러스터를 그룹화하는 논리적 단위  
C. 여러 Application을 그룹화하고 RBAC, 클러스터, 네임스페이스 등에 대한 제약 조건을 설정하는 논리적 단위  
D. 여러 개발 팀을 그룹화하는 논리적 단위  

<details>
<summary>정답 및 설명</summary>

**정답: C. 여러 Application을 그룹화하고 RBAC, 클러스터, 네임스페이스 등에 대한 제약 조건을 설정하는 논리적 단위**

**설명:**
ArgoCD에서 'Project'는 여러 Application을 그룹화하고 RBAC(Role-Based Access Control), 대상 클러스터, 소스 저장소, 네임스페이스 등에 대한 제약 조건을 설정하는 논리적 단위입니다. Project는 멀티 테넌트 환경에서 여러 팀이나 사용자 그룹이 ArgoCD를 안전하게 공유할 수 있도록 격리와 제어를 제공합니다.

**Project의 주요 기능:**

1. **접근 제어**: 특정 사용자나 그룹에게 Project 내의 Application에 대한 접근 권한을 부여합니다.
2. **소스 저장소 제한**: Project가 사용할 수 있는 Git 저장소를 제한합니다.
3. **대상 클러스터 및 네임스페이스 제한**: Project가 배포할 수 있는 클러스터와 네임스페이스를 제한합니다.
4. **리소스 제한**: Project가 생성하거나 수정할 수 있는 쿠버네티스 리소스 종류를 제한합니다.
5. **동기화 윈도우**: Project의 Application이 동기화될 수 있는 시간 윈도우를 정의합니다.
6. **OrphanedResources 모니터링**: Git에서 삭제된 리소스를 감지하고 보고합니다.

**Project 리소스 예시:**
```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: my-project
  namespace: argocd
spec:
  description: "My team's project"
  
  # Project에 속한 Application이 사용할 수 있는 소스 저장소
  sourceRepos:
  - "https://github.com/my-org/my-repo.git"
  
  # Project에 속한 Application이 배포할 수 있는 대상 클러스터와 네임스페이스
  destinations:
  - namespace: my-namespace
    server: https://kubernetes.default.svc
  
  # Project에 속한 Application이 생성할 수 있는 쿠버네티스 리소스 종류
  clusterResourceWhitelist:
  - group: ""
    kind: Namespace
  
  namespaceResourceBlacklist:
  - group: ""
    kind: ResourceQuota
  
  # RBAC 설정
  roles:
  - name: developer
    description: Developer role
    policies:
    - p, proj:my-project:developer, applications, get, my-project/*, allow
    - p, proj:my-project:developer, applications, sync, my-project/*, allow
    groups:
    - my-org:developers
  
  # 동기화 윈도우 설정
  syncWindows:
  - kind: allow
    schedule: "10 1 * * *"
    duration: 1h
    applications:
    - "*"
    namespaces:
    - "*"
    clusters:
    - "*"
```

**Project의 사용 사례:**

1. **팀 기반 격리**: 여러 팀이 동일한 ArgoCD 인스턴스를 사용할 때, 각 팀에게 자체 Project를 할당하여 다른 팀의 Application에 영향을 주지 않도록 합니다.
2. **환경 분리**: 개발, 스테이징, 프로덕션 환경을 위한 별도의 Project를 생성하여 환경 간의 격리를 제공합니다.
3. **규정 준수**: 특정 규정 준수 요구 사항이 있는 애플리케이션을 위한 Project를 생성하여 특별한 제약 조건을 적용합니다.
4. **리소스 제한**: 중요한 시스템 리소스에 대한 접근을 제한하여 실수로 인한 변경을 방지합니다.

**기본 Project:**
ArgoCD는 기본적으로 'default' Project를 제공합니다. 이 Project는 제약 조건이 없으며, 모든 소스 저장소, 대상 클러스터, 네임스페이스에 접근할 수 있습니다. 보안을 강화하기 위해 사용자 정의 Project를 생성하고 적절한 제약 조건을 설정하는 것이 좋습니다.

**다른 옵션들의 문제점:**
- A. 여러 Git 저장소를 그룹화하는 논리적 단위: Project는 Git 저장소를 그룹화하는 것이 아니라, 어떤 저장소를 사용할 수 있는지 제한합니다.
- B. 여러 쿠버네티스 클러스터를 그룹화하는 논리적 단위: Project는 클러스터를 그룹화하는 것이 아니라, 어떤 클러스터에 배포할 수 있는지 제한합니다.
- D. 여러 개발 팀을 그룹화하는 논리적 단위: Project는 개발 팀을 직접 그룹화하지 않지만, 팀 기반 격리를 위해 사용될 수 있습니다.
</details>

### 4. ArgoCD의 동기화 정책(Sync Policy)에서 'automated'가 의미하는 것은 무엇인가요?

A. Git 저장소의 변경 사항이 감지되면 자동으로 클러스터와 동기화  
B. 클러스터의 변경 사항이 감지되면 자동으로 Git 저장소와 동기화  
C. 정해진 일정에 따라 자동으로 동기화  
D. 클러스터 리소스 사용량에 따라 자동으로 스케일링  

<details>
<summary>정답 및 설명</summary>

**정답: A. Git 저장소의 변경 사항이 감지되면 자동으로 클러스터와 동기화**

**설명:**
ArgoCD의 동기화 정책(Sync Policy)에서 'automated'는 Git 저장소의 변경 사항이 감지되면 자동으로 클러스터와 동기화하는 것을 의미합니다. 이 설정을 통해 GitOps 워크플로우를 완전히 자동화할 수 있으며, Git 저장소에 변경 사항이 커밋되면 ArgoCD가 이를 감지하고 클러스터에 자동으로 적용합니다.

**자동 동기화 정책의 주요 옵션:**

1. **prune**: `true`로 설정하면 Git 저장소에서 삭제된 리소스를 클러스터에서도 자동으로 삭제합니다.
2. **selfHeal**: `true`로 설정하면 클러스터의 리소스가 Git 저장소와 다를 경우 자동으로 Git 저장소의 상태로 복원합니다.
3. **allowEmpty**: `true`로 설정하면 소스 디렉토리가 비어 있어도 동기화를 허용합니다.

**자동 동기화 정책 예시:**
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
      allowEmpty: false
```

**자동 동기화의 장점:**
1. **지속적 배포**: 코드 변경이 자동으로 배포되어 지속적 배포(CD) 파이프라인을 구현합니다.
2. **일관성 유지**: Git 저장소와 클러스터 상태의 일관성을 자동으로 유지합니다.
3. **수동 개입 최소화**: 배포 프로세스에서 수동 개입이 필요 없습니다.
4. **빠른 피드백**: 변경 사항이 빠르게 적용되어 피드백 루프가 단축됩니다.

**자동 동기화의 단점:**
1. **위험성**: 잘못된 변경 사항이 자동으로 적용될 수 있습니다.
2. **제어 부족**: 변경 사항이 적용되는 시점을 제어하기 어렵습니다.
3. **테스트 부족**: 변경 사항이 충분히 테스트되지 않고 적용될 수 있습니다.

**자동 동기화 vs 수동 동기화:**
- **자동 동기화**: Git 저장소의 변경 사항이 감지되면 자동으로 클러스터와 동기화합니다.
- **수동 동기화**: 사용자가 명시적으로 동기화 작업을 트리거해야 합니다.

**자동 동기화 사용 시 고려 사항:**
1. **환경에 따른 설정**: 개발 환경에서는 자동 동기화를 활성화하고, 프로덕션 환경에서는 수동 동기화를 사용하는 것이 좋습니다.
2. **프루닝 주의**: `prune: true` 설정은 리소스를 자동으로 삭제하므로 주의해서 사용해야 합니다.
3. **셀프 힐링 고려**: `selfHeal: true` 설정은 클러스터에서 직접 변경한 내용을 덮어쓰므로 주의해야 합니다.
4. **동기화 윈도우**: 특정 시간에만 자동 동기화가 발생하도록 동기화 윈도우를 설정할 수 있습니다.

**다른 옵션들의 문제점:**
- B. 클러스터의 변경 사항이 감지되면 자동으로 Git 저장소와 동기화: ArgoCD는 Git 저장소를 단일 진실 공급원으로 사용하므로, 클러스터의 변경 사항을 Git 저장소로 동기화하지 않습니다.
- C. 정해진 일정에 따라 자동으로 동기화: 이는 동기화 윈도우(Sync Window)의 기능이며, 'automated' 설정 자체는 Git 저장소의 변경 사항을 감지하여 동기화합니다.
- D. 클러스터 리소스 사용량에 따라 자동으로 스케일링: 이는 Horizontal Pod Autoscaler(HPA)와 같은 쿠버네티스 스케일링 메커니즘의 기능이며, ArgoCD의 동기화 정책과는 관련이 없습니다.
</details>
