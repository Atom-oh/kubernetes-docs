# Pod Security Standards (PSS)

> **검증 기준**: Kubernetes PSA 라이브러리 v1.36.2, 예제 PSS 정책 v1.35
> **마지막 업데이트**: 2026년 9월 13일

Pod Security Standards(PSS)는 Kubernetes에서 Pod 보안을 위한 표준화된 정책 프레임워크입니다. 이 문서에서는 PSS의 개념, 구성 방법, 그리고 EKS 환경에서의 적용 방법을 상세히 알아봅니다.

PSS는 정책 정의이고 PSA는 이를 적용하는 내장 어드미션 구현입니다. 이 문서는 **일반 Linux Pod(사용자 네임스페이스를 선택하지 않은 경우)**를 기본으로 설명합니다. 실제 클러스터·EKS·컨테이너 실행은 검증하지 않았으며, 로컬 upstream 정책 평가와 스키마/명령 검증을 구분합니다. 예제의 `v1.35`는 정책 고정값이지 최신 Kubernetes/EKS 지원 버전 선언이 아닙니다. `latest`는 API 서버 업그레이드에 따라 의미가 달라집니다.

## 목차

1. [PSP에서 PSS로의 진화](#psp에서-pss로의-진화)
2. [Pod Security Admission (PSA) 컨트롤러](#pod-security-admission-psa-컨트롤러)
3. [보안 수준 (Security Levels)](#보안-수준-security-levels)
4. [적용 모드 (Enforcement Modes)](#적용-모드-enforcement-modes)
5. [네임스페이스 레벨 구성](#네임스페이스-레벨-구성)
6. [PSP에서 PSS로 마이그레이션](#psp에서-pss로-마이그레이션)
7. [EKS 기본 설정 및 구성](#eks-기본-설정-및-구성)
8. [보안 프로파일 상세](#보안-프로파일-상세)
9. [예외 구성](#예외-구성)
10. [점진적 도입 모범 사례](#점진적-도입-모범-사례)

---

## PSP에서 PSS로의 진화

### PodSecurityPolicy(PSP)의 역사

PodSecurityPolicy(PSP)는 Kubernetes 1.3에서 처음 도입된 Pod 보안 메커니즘이었습니다. 그러나 다음과 같은 문제점으로 인해 Kubernetes 1.21에서 사용 중단(deprecated)되었고, 1.25에서 완전히 제거되었습니다:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PSP의 주요 문제점                              │
├─────────────────────────────────────────────────────────────────┤
│ 1. 복잡한 RBAC 바인딩 요구사항                                    │
│ 2. 암묵적 정책 적용 (어떤 정책이 적용되는지 불명확)                  │
│ 3. 사용자 vs 워크로드 권한 혼동                                    │
│ 4. warn/audit 도입 모드 부재                                             │
│ 5. 감사(Audit) 기능 제한                                          │
└─────────────────────────────────────────────────────────────────┘
```

### PSS의 도입 배경

Pod Security Standards(PSS)와 Pod Security Admission(PSA)은 Kubernetes 1.22에서 알파로 도입되어, 1.23에서 베타, 1.25에서 GA(Generally Available)가 되었습니다.

![PSP 사용 중단과1.25의 PSP 제거·PSA GA, 이후 정책 버전별 발전을 구분한 로드맵.](../.gitbook/assets/ko-security-03-pod-security-standards-0.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-security-03-pod-security-standards-0.html)

> 그림 해석: PSA GA는 1.25이며 1.28이 별도의 안정화 이정표는 아닙니다.

### PSP vs PSS 비교

| 특성 | PodSecurityPolicy (PSP) | Pod Security Standards (PSS) |
|------|------------------------|------------------------------|
| **활성화 방법** | 과거 Admission Controller 플러그인 | PSS 정의를 내장 PSA 플러그인으로 적용 |
| **정책 정의** | 커스텀 PSP 리소스 | 사전 정의된 3가지 프로파일 |
| **정책 바인딩** | RBAC를 통한 복잡한 바인딩 | 네임스페이스 레이블로 간단히 적용 |
| **적용 범위** | 클러스터 전체 또는 네임스페이스 | 네임스페이스 레벨 |
| **정책 미리보기** | PSA식 warn/audit 모드 없음; API dry-run은 별도 | warn/audit 모드와 API dry-run |
| **감사** | 제한적 | 내장 감사 지원 |
| **유연성** | 높음 (세밀한 제어 가능) | 중간 (표준화된 프로파일) |
| **복잡성** | 높음 | 낮음 |

---

## Pod Security Admission (PSA) 컨트롤러

### PSA 아키텍처

PSA는 변이 어드미션 이후 **API 서버 내부의 검증 어드미션 단계**에서 동작합니다. 인증·인가·스키마 검증·다른 어드미션 검사도 적용됩니다. 외부 webhook이 아니며 PSA와 모든 다른 검증기의 세부 순서를 일률적으로 보장하지 않습니다.

```text
Request → authentication / authorization → mutating admission
        → validating admission (PSA + other checks) → persistence if accepted
```

### PSA 작동 방식

![인증·인가된 Pod CREATE의 단순화한 흐름. PSA는 API 서버 내부 검사이며 다른 admission과 저장도 성공한 경우에만201로 응답한다.](../.gitbook/assets/ko-security-03-pod-security-standards-1.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-security-03-pod-security-standards-1.html)

> 그림 범위: PSA는 API 서버 내부이며 Pod CREATE는 적용되는 모든 검사를 통과해야 저장됩니다. PSA 승인만으로 201 Created가 보장되지 않습니다.

### PSA 활성화 상태 확인

PSA는 Kubernetes 1.25부터 기본 활성화입니다. 명시적인 `--enable-admission-plugins=PodSecurity` 플래그가 없다고 비활성화인 것은 아닙니다. 자체 관리 API 서버의 비활성화 설정을 확인하되 EKS 관리형 설정은 직접 조회·수정할 수 없습니다. 메트릭은 기능 게이트 값이 아니라 평가 기록입니다. `/metrics` 조회 권한이 필요하며 아직 사용하지 않은 시계열은 없을 수 있습니다.

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" get --raw /metrics
```

아래의 정상/위반 Pod dry-run 대조군으로 실제 어드미션 경로를 확인합니다. Deployment dry-run 성공만으로 Pod 정책 준수를 판단하지 않습니다.

---

## 보안 수준 (Security Levels)

PSS는 세 가지 보안 수준(프로파일)을 정의합니다. 각 수준은 점진적으로 더 엄격한 보안 제약을 적용합니다.

### 1. Privileged (특권)

PSS 제약을 추가하지 않는 프로파일입니다. 컨테이너 특권을 자동 활성화하거나 RBAC·API 검증·다른 어드미션 정책을 우회하지 않습니다.

```yaml
# Privileged 프로파일: PSS 제약 없음; API/RBAC/다른 정책은 계속 적용
# 사용 사례: 시스템 데몬, CNI 플러그인, 모니터링 에이전트

apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
  namespace: pss-privileged-lab
spec:
  hostNetwork: true      # 허용
  hostPID: true          # 허용
  hostIPC: true          # 허용
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true   # 허용
      runAsUser: 0    # 허용
```

**Privileged 수준 허용 항목:**
- 호스트 네트워크, PID, IPC 네임스페이스
- 특권 컨테이너
- 모든 capabilities
- 호스트 경로 마운트
- 모든 사용자/그룹 ID

### 2. Baseline (기본)

최소한의 제한을 적용하여 알려진 권한 상승을 방지합니다. 대부분의 일반 워크로드에 적합합니다.

```yaml
# Baseline 수준: 알려진 권한 상승 방지
# 사용 사례: 일반 애플리케이션, 웹 서버, API 서버

apiVersion: v1
kind: Pod
metadata:
  name: baseline-pod
spec:
  containers:
  - name: app
    image: nginx
    securityContext:
      # 다음은 Baseline에서 금지됨:
      # privileged: true        ❌
      # allowPrivilegeEscalation은 Baseline에서 제한하지 않음

      # 다음은 Baseline에서 허용됨:
      runAsNonRoot: false      # ✓ (허용되지만 권장하지 않음)
      readOnlyRootFilesystem: false  # ✓ (허용)
    ports:
    - containerPort: 80
```

**Baseline 수준 제한 항목:**

| 항목 | 제한 내용 |
|------|----------|
| HostProcess | Windows HostProcess 컨테이너 금지 |
| Host Namespaces | hostNetwork, hostPID, hostIPC 금지 |
| Privileged Containers | privileged: true 금지 |
| Capabilities | 명시적 추가는 Baseline 허용 목록으로 제한; `NET_RAW`는 포함되지 않음 |
| HostPath Volumes | hostPath 볼륨 금지 |
| Host Ports | 내장 PSA는 미지정/0 허용; 사용자 지정 포트 허용 목록 없음 |
| AppArmor | 미지정 또는 RuntimeDefault/Localhost; 이전 annotation 값은 runtime/default 또는 localhost/* |
| SELinux | type은 제한된 값만, user/role 설정 금지 |
| /proc Mount Type | 기본값만 허용 |
| Seccomp | 생략 허용; 지정 시 RuntimeDefault 또는 Localhost, Unconfined 금지 |
| Sysctls | 해당 PSS 버전의 명시적 허용 목록; 모든 kubelet safe sysctl과 동일하지 않음 |

### 3. Restricted (제한)

가장 엄격한 정책으로, Pod 보안 강화 모범 사례를 적용합니다. 보안이 중요한 워크로드에 적합합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

**Restricted 수준 추가 제한 항목:**

| 항목 | 제한 내용 |
|------|----------|
| Volume Types | configMap, csi, downwardAPI, emptyDir, ephemeral, persistentVolumeClaim, projected, secret만 허용 |
| Privilege Escalation | allowPrivilegeEscalation: false 필수 |
| Running as Non-root | runAsNonRoot: true 필수 |
| Running as Non-root user | 명시적 runAsUser: 0 금지(v1.23+); 필드 생략은 허용 |
| Seccomp | RuntimeDefault 또는 Localhost 필수 |
| Capabilities | 모든 capabilities drop 필수, NET_BIND_SERVICE만 추가 허용 |



해당 제약은 일반·init·ephemeral 컨테이너에 적용됩니다. Pod 수준 non-root/seccomp 설정은 상속할 수 있지만 컨테이너에서 충돌하는 값으로 덮어쓰면 준수하지 않습니다. 정책 v1.34부터 HTTP/TCP probe와 lifecycle hook의 비어 있지 않은 `host`도 금지합니다. v1.35의 `hostUsers: false`는 non-root 검사를 완화하며 Baseline의 `procMount`도 완화하지만 Restricted는 계속 `Unmasked`를 금지합니다. 레이블만으로 되는 것이 아니라 실제 사용자 네임스페이스 지원이 필요합니다. Windows의 권한 상승·seccomp·Linux capability 관련 예외는 이 Linux 예제와 별도입니다.

### 보안 수준 비교 차트

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        보안 수준 비교                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  제한 수준  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━▶          │
│             낮음                                          높음            │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Privileged  │    │   Baseline   │    │  Restricted  │               │
│  │              │    │              │    │              │               │
│  │  제한 없음   │    │ 알려진 권한  │    │ 보안 모범    │               │
│  │              │    │ 상승 방지    │    │ 사례 적용    │               │
│  │              │    │              │    │              │               │
│  │ 사용 사례:   │    │ 사용 사례:   │    │ 사용 사례:   │               │
│  │ - CNI       │    │ - 일반 앱   │    │ - 금융 앱   │               │
│  │ - CSI       │    │ - 웹 서버   │    │ - 의료 앱   │               │
│  │ - 모니터링  │    │ - API 서버  │    │ - 멀티테넌트 │               │
│  └──────────────┘    └──────────────┘    └──────────────┘               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 적용 모드 (Enforcement Modes)

PSA는 세 가지 적용 모드를 제공합니다. 이 모드들은 독립적으로 또는 함께 사용할 수 있습니다.

### 1. enforce (적용)

위반한 Pod 생성과 관련 Pod 업데이트를 거부합니다. 워크로드 템플릿에는 warn/audit를 적용하고, enforce는 생성되는 Pod에서 수행합니다. 네임스페이스 레이블 변경이 기존 실행 Pod를 퇴거시키지는 않습니다.

```yaml
# enforce 모드: 정책 위반 시 Pod 생성 차단
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
```

**응답 일부의 설명용 예시(실제 클러스터 실행 기록 아님):**
```text
# 정책 위반 Pod 생성 시도
$ kubectl apply --dry-run=server -f privileged-pod.yaml -n production
Error from server (Forbidden): error when creating "privileged-pod.yaml":
pods "privileged-pod" is forbidden: violates PodSecurity "restricted:v1.35":
privileged (container "app" must not set securityContext.privileged=true),
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false)
```

### 2. audit (감사)

위반을 감사 이벤트 annotation으로 남기며 이 모드 자체는 요청을 거부하지 않습니다. 실제 기록 보존은 감사 정책과 로그 전달 설정에 달려 있고, 다른 모드·어드미션이 요청을 거부할 수 있습니다.

```yaml
# audit 모드: 정책 위반을 감사 로그에 기록
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
```

**설명용 합성 감사 이벤트 일부(실제 수집 이벤트 아님):**
```json
{
  "kind": "Event",
  "apiVersion": "audit.k8s.io/v1",
  "level": "Metadata",
  "auditID": "00000000-0000-4000-8000-000000000001",
  "stage": "ResponseComplete",
  "requestURI": "/api/v1/namespaces/staging/pods",
  "verb": "create",
  "user": {
    "username": "developer@example.com"
  },
  "objectRef": {
    "resource": "pods",
    "namespace": "staging",
    "name": "my-pod"
  },
  "annotations": {
    "pod-security.kubernetes.io/audit-violations": "privileged (container \"app\" must not set securityContext.privileged=true)"
  }
}
```

### 3. warn (경고)

클라이언트에 경고를 반환하지만 이 모드 자체는 거부하지 않습니다. enforce나 다른 어드미션 검사는 여전히 거부할 수 있습니다.

```yaml
# warn 모드: 정책 위반 시 경고 메시지 표시
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

**설명용 경고 일부(실행 기록 아님):**
```text
$ kubectl apply --dry-run=server -f non-compliant-pod.yaml -n development
Warning: would violate PodSecurity "restricted:v1.35":
allowPrivilegeEscalation != false (container "app" must set
securityContext.allowPrivilegeEscalation=false),
unrestricted capabilities (container "app" must set
securityContext.capabilities.drop=["ALL"])
pod/my-pod created (server dry run)
```

### 모드 조합 전략

초기 Privileged 단계는 더 강한 기존 정책이 없는 네임스페이스에만 해당합니다. 그림을 따르기 위해 기존 Baseline/Restricted를 낮추지 않습니다.

실제 환경에서는 여러 모드를 조합하여 사용하는 것이 권장됩니다:

```yaml
# 권장 구성: 모드 조합 사용
apiVersion: v1
kind: Namespace
metadata:
  name: app-namespace
  labels:
    # 현재 적용 수준
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    # 다음 단계 수준 감사
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    # 다음 단계 수준 경고
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    모드 조합 전략                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: 현재 상태 파악                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: privileged                                      │   │
│  │ audit: baseline                                          │   │
│  │ warn: baseline                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 2: 점진적 강화                                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: baseline                                        │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                     │
│                           ▼                                     │
│  Phase 3: 최종 목표                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ enforce: restricted                                      │   │
│  │ audit: restricted                                        │   │
│  │ warn: restricted                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 네임스페이스 레벨 구성

### 기본 레이블 구성

PSS는 네임스페이스 레이블을 통해 구성됩니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: secure-namespace
  labels:
    # 형식: pod-security.kubernetes.io/<MODE>: <LEVEL>
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### 버전 지정

특정 Kubernetes 버전의 PSS 정의를 사용할 수 있습니다:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: versioned-namespace
  labels:
    # 특정 버전의 PSS 정의 사용
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.35  # 특정 버전

    # 'latest'를 사용하면 현재 클러스터 버전의 PSS 적용
    # pod-security.kubernetes.io/enforce-version: latest
```

### 환경별 구성 예시

```yaml
---
# 개발 환경: 느슨한 정책
apiVersion: v1
kind: Namespace
metadata:
  name: development
  labels:
    environment: development
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/warn: restricted
---
# 스테이징 환경: 중간 정책
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
# 프로덕션 환경: 엄격한 정책
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    environment: production
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 기존 네임스페이스에 레이블 추가

```bash
# kubectl을 사용하여 레이블 추가
kubectl label namespace my-namespace \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# 레이블 확인
kubectl get namespace my-namespace -o yaml | grep pod-security
```

---

## PSP에서 PSS로 마이그레이션

### 마이그레이션 개요

PSP에서 PSS로의 마이그레이션은 신중하게 계획하고 단계적으로 수행해야 합니다.

![기존 enforce를 유지하면서 정책 차이를 분석하고 warn/audit·수정·목표 enforce를 검증하는 절차. PSP API 정리는1.24이하 과거 환경에만 적용한다.](../.gitbook/assets/ko-security-03-pod-security-standards-2.png)

[🔍 인터랙티브 다이어그램 보기](https://www.atomai.click/kubernetes-docs/archmaps/ko-security-03-pod-security-standards-2.html)

> 그림 범위: PSP 분석·제거는 과거 절차입니다. 관찰을 위해 기존 enforce 수준을 낮추지 않으며 readOnlyRootFilesystem은 Restricted 필수가 아닌 권장 설정입니다.

### 1단계: 현재 PSP 분석

**과거 마이그레이션 절차입니다.** 아래 PSP 명령/리소스는 `policy/v1beta1`을 제공하던 Kubernetes 1.24 이하 클러스터나 보관된 매니페스트 분석에만 해당합니다. 현재 클러스터에 적용하지 않습니다. PSP가 기본값을 채우거나 변이하던 필드도 조사해야 합니다. PSA는 그 값을 채워 주지 않습니다.

```bash
# 현재 PSP 목록 확인
kubectl get psp

# PSP 상세 정보 확인
kubectl get psp <psp-name> -o yaml

# PSP가 적용된 Pod 확인
kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.metadata.annotations.kubernetes\.io/psp}{"\n"}{end}'
```

### 2단계: PSP를 PSS 프로파일로 매핑

```yaml
# 예시: 기존 PSP
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: restricted-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  supplementalGroups:
    rule: RunAsAny
```

**매핑 결과:** Restricted는 검토할 목표일 뿐 동등한 정책이 아닙니다. 위 PSP에는 필수 seccomp 제약이 없고 PSS가 거부할 SELinux 설정도 허용합니다. 모든 제약과 실제 생성 Pod를 비교해야 하며 세 필드만으로 동등성을 판단할 수 없습니다.

### PSP → PSS 매핑 테이블

| 워크로드 요구사항 | 검토할 PSS 프로파일 | 추가 검토 |
|---|---|---|
| 호스트 namespace·특권 컨테이너·hostPath | Privileged | 예외 격리와 추가 제약 필요 |
| 호스트 접근 없이 root 프로세스 필요 | Baseline | capability·seccomp 등 모든 Baseline 제약 비교 |
| non-root·권한 상승 차단·ALL drop | Restricted | 볼륨·seccomp·override·버전별 제약도 확인 |

### 3단계: 테스트 환경에서 검증

```bash
# 테스트 네임스페이스 생성
kubectl create namespace pss-test

# warn 모드로 restricted 적용
kubectl label namespace pss-test \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/warn-version=v1.35

# 기존 워크로드 배포 테스트
kubectl apply -f my-deployment.yaml -n pss-test

# 경고 메시지 확인 및 워크로드 수정
```

### 4단계: 점진적 적용

```yaml
# 단계별 마이그레이션 네임스페이스 구성
apiVersion: v1
kind: Namespace
metadata:
  name: migrating-namespace
  labels:
    # Phase 1: 더 강한 기존 enforce 정책이 없는 새 네임스페이스
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: baseline
    pod-security.kubernetes.io/warn: baseline

    # Phase 2: baseline 적용 후 restricted 모니터링
    # pod-security.kubernetes.io/enforce: baseline
    # pod-security.kubernetes.io/audit: restricted
    # pod-security.kubernetes.io/warn: restricted

    # Phase 3: 최종 restricted 적용
    # pod-security.kubernetes.io/enforce: restricted
```

### 5단계: 워크로드 수정

수정 전의 기본 `nginx` Pod는 securityContext가 없어 Restricted 검사를 통과하지 못합니다. `runAsNonRoot`만 추가해서는 부족하며 이미지 사용자·리스너·쓰기 경로도 맞아야 합니다. 수정 예제는 upstream 비특권 이미지(UID/GID 101), 8080 포트, 읽기 전용 루트 파일시스템과 쓰기 가능한 `/tmp`를 사용합니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: new-pod
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### 마이그레이션 자동화 스크립트

**검토한 네임스페이스 하나**만 대상으로 기존에 없던 warn/audit 레이블을 추가하며 enforce를 보존합니다. 조회한 resourceVersion으로 동시 변경을 거부합니다. 실행하면 실제 네임스페이스가 변경되므로 대상을 먼저 확인합니다. 레이블이 이미 있으면 자동 하향 대신 실패하여 수동 비교하도록 합니다. 경고는 이후 요청에 적용되며 기존 모든 Pod를 소급 검사하지 않습니다.

```python
#!/usr/bin/env python3
# add-pss-observation.py CONTEXT NAMESPACE
import json, subprocess, sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: add-pss-observation.py CONTEXT NAMESPACE")
context, namespace = sys.argv[1:]
if namespace in {"kube-system", "kube-public", "kube-node-lease"}:
    raise SystemExit("Refusing system namespace; review its workload requirements separately")
base = ["kubectl", "--context", context, "--request-timeout=30s"]
obj = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = obj["metadata"].get("labels", {})
new = {
    "pod-security.kubernetes.io/warn": "restricted",
    "pod-security.kubernetes.io/warn-version": "v1.35",
    "pod-security.kubernetes.io/audit": "restricted",
    "pod-security.kubernetes.io/audit-version": "v1.35",
}
if any(key in labels for key in new):
    raise SystemExit("Existing observation policy: review it; do not overwrite automatically")
subprocess.run(base + [
    "label", "namespace", namespace,
    "--resource-version=" + obj["metadata"]["resourceVersion"],
] + [key + "=" + value for key, value in new.items()], check=True)
```

---

## EKS 기본 설정 및 구성

### EKS의 PSA 기본 설정

AWS는 EKS 1.23부터 PSA 기본 활성화, 세 모드의 클러스터 기본값 `privileged/latest`, 정적 예외 없음으로 설명합니다. 이 기본값 자체는 워크로드 강화 정책이 아닙니다. 플랫폼 도구나 관리자가 만든 namespace 레이블이 기본값을 바꾸므로 모든 namespace에 레이블이 없다고 가정하지 말고 실제 대상을 조회합니다.

```bash
kubectl --context "$PSS_CONTEXT" get namespace "$PSS_NAMESPACE" -o yaml
```

### EKS에서 PSS 구성

```yaml
# EKS 네임스페이스에 PSS 적용
apiVersion: v1
kind: Namespace
metadata:
  name: eks-app-namespace
  labels:
    # 도입 예제이며 모든 환경에 대한 AWS 요구사항이 아님
    pod-security.kubernetes.io/enforce: baseline
    pod-security.kubernetes.io/enforce-version: v1.35
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted

    # EKS 관련 레이블
    app.kubernetes.io/managed-by: eks
```

### EKS 시스템 네임스페이스 고려사항

호스트 접근 에이전트는 Baseline을 만족할 수 없지만 `kube-system`의 모든 Pod에 특권이 필요하다는 뜻은 아닙니다. 정확한 애드온 버전과 렌더된 Pod spec을 확인합니다. 전체 시스템 namespace의 warn/audit를 끄는 일괄 덮어쓰기를 피하고 승인된 호스트 에이전트를 일반 앱과 격리하며 배포 주체를 제한합니다. 아래는 전용 예제 namespace이며 기존 시스템 namespace를 재설정하는 명령이 아닙니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### EKS 애드온과 PSS 호환성

| 컴포넌트 / 일반적 배포 형태 | PSS 검토 지점 |
|---|---|
| VPC CNI `aws-node`, kube-proxy | 호스트 네트워크·특권 노드 작업이 Baseline 범위를 벗어날 수 있음 |
| EBS/EFS CSI 노드 DaemonSet | host mount가 Baseline을 벗어날 수 있으며 controller Pod 요구사항은 별도 |
| 노드 수준 CloudWatch Agent / Fluent Bit | 실제 설정에 따라 호스트 로그·파일시스템 접근 필요 |
| CoreDNS, AWS Load Balancer Controller, Cluster Autoscaler | 렌더된 spec을 Baseline/Restricted로 평가; 이름만으로 준수를 보장하지 않음 |

EKS Auto Mode 내장 노드 구성요소는 자체 관리 애드온과 다릅니다. 이 표는 검토 기준이지 실측 호환성 행렬이나 모든 애드온 설치 요구사항이 아닙니다.

### EKS Terraform 예시

앱 namespace 하나를 관리하는 조각입니다. Kubernetes provider 인증·대상 context는 별도로 구성·검토하며 provider 초기화·plan·apply는 실행하지 않았습니다. 기존 namespace는 소유자의 import/인수 절차를 따르고 Terraform/GitOps가 경쟁 소유하지 않게 합니다. 정책을 명시적으로 고정하며 시스템 namespace 레이블은 바꾸지 않습니다.

```hcl
# Provider authentication/context and ownership must be configured separately.
resource "kubernetes_namespace_v1" "app" {
  metadata {
    name = "my-app"
    labels = {
      "pod-security.kubernetes.io/enforce"         = "restricted"
      "pod-security.kubernetes.io/enforce-version" = "v1.35"
      "pod-security.kubernetes.io/audit"           = "restricted"
      "pod-security.kubernetes.io/audit-version"   = "v1.35"
      "pod-security.kubernetes.io/warn"            = "restricted"
      "pod-security.kubernetes.io/warn-version"    = "v1.35"
      "environment"                              = "production"
    }
  }
}
```

---

## 보안 프로파일 상세

### Privileged 프로파일 상세

Privileged 프로파일은 PSS 제약을 추가하지 않지만 API 검증·RBAC·다른 어드미션은 계속 적용됩니다. 아래 호스트 루트 접근 예제는 정책 분석용이며 배포를 권장하는 워크로드가 아닙니다.

```yaml
# Privileged 프로파일에서 허용되는 모든 옵션
apiVersion: v1
kind: Pod
metadata:
  name: privileged-example
spec:
  hostNetwork: true
  hostPID: true
  hostIPC: true
  containers:
  - name: privileged-container
    image: nginx
    securityContext:
      privileged: true
      allowPrivilegeEscalation: true
      runAsUser: 0
      capabilities:
        add:
          - ALL
    volumeMounts:
    - name: host-root
      mountPath: /host
  volumes:
  - name: host-root
    hostPath:
      path: /
      type: Directory
```

### Baseline 프로파일 상세

```yaml
# Baseline 프로파일 제한 사항 (v1.35)
#
# 금지되는 필드 및 값:
#
# spec.hostNetwork: true 금지
# spec.hostPID: true 금지
# spec.hostIPC: true 금지
#
# spec.containers[*].securityContext.privileged: true 금지
# spec.initContainers[*].securityContext.privileged: true 금지
# spec.ephemeralContainers[*].securityContext.privileged: true 금지
#
# spec.containers[*].securityContext.capabilities.add 제한
#   - 허용: NET_BIND_SERVICE (Restricted에서는 이것만)
#   - Baseline에서 추가 허용: AUDIT_WRITE, CHOWN, DAC_OVERRIDE,
#     FOWNER, FSETID, KILL, MKNOD, NET_BIND_SERVICE,
#     SETFCAP, SETGID, SETPCAP, SETUID, SYS_CHROOT
#
# spec.volumes[*].hostPath 금지
#
# spec.containers[*].ports[*].hostPort 금지 (0 제외)
#
# spec.securityContext.appArmorProfile.type 제한
#   - 허용: 프로파일 생략 또는 type RuntimeDefault/Localhost
#   - 금지: Unconfined
#
# spec.securityContext.seLinuxOptions.type 제한
#   - 금지: 빈 문자열이 아닌 사용자 정의 타입 (container_t 등은 허용)
#
# spec.securityContext.seccompProfile.type 제한
#   - 금지: Unconfined
#
# spec.securityContext.sysctls 제한
#   - 해당 PSS 버전의 명시적 sysctl 허용 목록만 허용

apiVersion: v1
kind: Pod
metadata:
  name: baseline-compliant
spec:
  automountServiceAccountToken: false
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    ports:
    - containerPort: 8080
    securityContext:
      capabilities:
        drop: [ALL]
```

### Restricted 프로파일 상세

Restricted는 Baseline에 허용 볼륨 종류·non-root 실행·명시적 seccomp·권한 상승 차단·ALL capability drop을 추가합니다. 추가할 수 있는 capability는 `NET_BIND_SERVICE`뿐이지만 이 8080 리스너에는 필요하지 않습니다. `readOnlyRootFilesystem`은 권장 강화이며 PSS 필수 조건이 아닙니다. `containerPort`는 메타데이터이며 Nginx 설정을 바꾸지 않습니다.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: restricted-compliant
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
    runAsGroup: 101
    fsGroup: 101
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: app
    image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
    ports:
    - containerPort: 8080
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 500m
        memory: 128Mi
    volumeMounts:
    - name: tmp
      mountPath: /tmp
  volumes:
  - name: tmp
    emptyDir: {}
```

### Restricted 준수 Nginx 완전 예시

digest는 upstream OCI의 Linux amd64/arm64 메타데이터(Nginx 1.30.4, 사용자 101)로 확인했으며 이미지 레이어 다운로드·컨테이너 실행은 하지 않았습니다. upstream은 8080 포트, `/tmp/nginx.pid`, `/tmp` 하위 임시 경로를 명시합니다. 아래 ConfigMap이 해당 리스너와 health endpoint를 제공하므로 Deployment보다 먼저 같은 namespace에 생성합니다. 실제 기동/readiness는 승인된 환경에서 배포 전에 검증해야 합니다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-restricted
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 101  # nginx user
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: nginx
        image: ghcr.io/nginx/nginx-unprivileged@sha256:442753882674b49ae2c1de83ed67896131c0777f56df5005e356e62bc3f7e7ce
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 101
          capabilities:
            drop:
              - ALL
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: 100m
            memory: 128Mi
          requests:
            cpu: 50m
            memory: 64Mi
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: config
          mountPath: /etc/nginx/conf.d
          readOnly: true
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthz
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
      - name: config
        configMap:
          name: nginx-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: production
data:
  default.conf: |
    server {
        listen 8080;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html;
        }

        location /healthz {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
```

---

## 예외 구성

### 클러스터 레벨 예외 구성

자체 관리 API 서버는 `--admission-control-config-file`로 이 설정을 읽을 수 있습니다. 예제는 모든 예외 목록을 비워 둡니다. 예외는 **모든 PSA 모드**를 건너뜁니다. `usernames`는 인증된 요청 username과 정확히 일치해야 하며 그룹·와일드카드·나중에 실행될 Pod의 ServiceAccount가 아닙니다. controller 계정을 예외로 두면 여러 사용자를 대신해 생성하는 Pod도 우회합니다. namespace와 RuntimeClass 이름도 정확히 일치하며 예외 사용 주체를 별도로 제한해야 합니다.

```yaml
# Self-managed API server configuration; not an EKS control-plane setting
apiVersion: apiserver.config.k8s.io/v1
kind: AdmissionConfiguration
plugins:
- name: PodSecurity
  configuration:
    apiVersion: pod-security.admission.config.k8s.io/v1
    kind: PodSecurityConfiguration
    defaults:
      enforce: baseline
      enforce-version: v1.35
      audit: restricted
      audit-version: v1.35
      warn: restricted
      warn-version: v1.35
    exemptions:
      usernames: []
      runtimeClasses: []
      namespaces: []
```

### EKS에서 예외 구성

EKS 관리형 API 서버의 AdmissionConfiguration은 수정할 수 없습니다. namespace의 `enforce: privileged`는 느슨한 프로파일이지 **정적 예외가 아닙니다**. warn/audit 평가는 유지할 수 있습니다. namespace 수정·배포 권한을 제한하고 호스트 에이전트와 일반 앱을 분리합니다. 예를 들어 hostNetwork/hostPID/hostPath를 사용하는 node-exporter는 Baseline을 통과하지 못하며 Baseline 지정으로 호스트 접근이 허용되는 것은 아닙니다.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: host-agents
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.35
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.35
```

### 런타임 클래스 기반 예외

RuntimeClass는 구성된 CRI 런타임 handler를 선택합니다. 리소스 생성만으로 gVisor/Kata가 설치되거나 PSA 예외가 부여되지 않습니다. 대상 노드에 handler가 있어야 하며 필요하면 스케줄링 제약을 추가합니다. 아래 정의만으로는 PSA 적용이 달라지지 않습니다.

```yaml
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: gvisor
handler: runsc
```

자체 관리 API 서버에서 별도로 `runtimeClasses: ["gvisor"]` 예외를 구성한 경우에만 PSA를 건너뜁니다. 그 클래스를 선택할 수 있는 요청은 PSA를 우회하므로 런타임 격리만으로 어드미션 인가를 대신하지 못합니다. EKS에서는 이 관리형 control plane 설정을 바꿀 수 없습니다.

### Kyverno를 사용한 세밀한 예외

Kyverno는 PSA가 거부한 요청을 허용으로 바꿀 수 없습니다. 호스트 에이전트에 예외가 필요하면 먼저 namespace PSA 프로파일과 배포 권한을 설계하고 독립적으로 적용되는 정책에 좁은 예외를 추가합니다. HostPath 예외만으로 hostNetwork/hostPID 검사까지 제외되지 않으며 이미지 태그나 수정 가능한 Pod 레이블 일치 자체는 인가가 아닙니다.

검토한 정책 API와 버전·폐기 예정 범위는 [Kyverno 정책 관리](./01-kyverno-policy-management.md)를 참고합니다. 소문자 `validationFailureAction: enforce`는 유효한 값이 아니며 ClusterPolicy는 Kyverno 1.19에서 deprecated입니다. 교체 정책은 일반 워크로드와 예외 워크로드 모두로 검증해야 합니다.

---

## 점진적 도입 모범 사례

### 1단계: 현재 상태 분석

기존 Pod 검사를 유발하는 것은 warn이 아니라 **enforce 수준/버전 변경**입니다. 아래 서버 dry-run은 레이블을 저장하거나 Pod를 퇴거시키지 않습니다. 유효 enforce 정책이 같으면 새 검사가 발생하지 않습니다. 검사는 best effort이며 경고 제한·중복 제거가 있으므로 무응답이 전체 워크로드 준수 증명이 아닙니다. 명령·인증 실패를 성공으로 처리하지 않습니다.

```bash
#!/usr/bin/env bash
# preview-pss.sh: no namespace mutation
set -euo pipefail
: "${PSS_CONTEXT:?Set the approved test context}"
: "${PSS_NAMESPACE:?Set one namespace to inspect}"
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  get namespace "$PSS_NAMESPACE" -o yaml
kubectl --context "$PSS_CONTEXT" --request-timeout=30s \
  label namespace "$PSS_NAMESPACE" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/enforce-version=v1.35 \
  --overwrite --dry-run=server
```

### 2단계: 점진적 롤아웃 전략

일수 범위는 실측 마이그레이션 시간이 아닌 계획 예시입니다. 명시적 namespace 목록을 사용하고 기존의 더 강한 정책을 낮추지 않으며 교체 Pod와 복구 여력을 검증한 뒤 다음 단계로 진행합니다.

```yaml
# GitOps를 사용한 점진적 롤아웃

# Phase 1: 모니터링 (Day 1-7)
# - 모든 네임스페이스에 warn: baseline 적용
# - 위반 사항 수집 및 분석

# Phase 2: 개발 환경 적용 (Day 8-14)
# - 개발 네임스페이스에 enforce: baseline 적용
# - 스테이징 네임스페이스에 warn: baseline 적용

# Phase 3: 스테이징 환경 적용 (Day 15-21)
# - 스테이징 네임스페이스에 enforce: baseline 적용
# - 프로덕션 네임스페이스에 warn: baseline 적용

# Phase 4: 프로덕션 환경 적용 (Day 22-28)
# - 프로덕션 네임스페이스에 enforce: baseline 적용
# - 모든 환경에 warn: restricted 적용

# Phase 5: restricted 강화 (Day 29+)
# - 새 네임스페이스에 enforce: restricted 기본 적용
# - 기존 네임스페이스 점진적 마이그레이션
```

### 3단계: 모니터링 및 알림 설정

Prometheus Operator CRD, 이 PrometheusRule을 선택하는 설정, `pod_security_evaluations_total`을 수집할 권한 있는 API 서버 scrape가 필요합니다. 내장 PSA는 `pod-security-webhook`이라는 webhook이 아닙니다. 평가 레이블은 decision·policy_level·policy_version·mode·request_operation·resource·subresource이며 **namespace 레이블은 없습니다**. namespace/요청 정보는 보존된 audit 이벤트와 연계합니다. 메트릭 부재는 위반 0건의 증거가 아니며 audit deny는 위반 평가이지 API 요청 거부와 동일하지 않습니다.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: pss-violations
  namespace: monitoring
spec:
  groups:
  - name: pod-security-standards
    rules:
    - alert: PSSViolationDetected
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="enforce",decision="deny"}[5m])
        ) > 0
      labels:
        severity: warning
      annotations:
        summary: "PSA denied a Pod request"
        description: "Policy {{ $labels.policy_level }}:{{ $labels.policy_version }}. Correlate audit logs for namespace and request identity."
    - alert: PSSAuditViolation
      expr: |
        sum by (policy_level, policy_version, mode) (
          increase(pod_security_evaluations_total{mode="audit",decision="deny"}[5m])
        ) > 10
      for: 5m
      labels:
        severity: info
      annotations:
        summary: "PSA audit violations increasing"
        description: "{{ $value }} violating evaluations over five minutes; not a count of unique Pods."
```

### 4단계: 자동화된 준수 검사

워크로드 소유 프로젝트에 아래 코드를 `check-pss.py`로 저장합니다. Python 3/PyYAML, 호환 kubectl, 승인된 클러스터 자격 증명, 정책 v1.35를 지원하는 API 서버, `restricted:v1.35`를 명시적으로 enforce하는 기존 테스트 네임스페이스가 필요합니다. 서버 dry-run에도 namespace 조회와 Pod 생성 인가가 필요합니다. 신뢰하지 않는 PR 코드에 클러스터 자격 증명을 제공하지 않습니다.

```python
#!/usr/bin/env python3
# check-pss.py CONTEXT NAMESPACE pod.yaml [pod2.yaml ...]
# Requires Python 3 + PyYAML and a preconfigured, authorized kubectl.
import copy, json, subprocess, sys
from pathlib import Path
import yaml

if len(sys.argv) < 4:
    raise SystemExit("Usage: check-pss.py CONTEXT NAMESPACE pod.yaml [...]")
context, namespace, *files = sys.argv[1:]
pods = []
for filename in files:
    docs = list(yaml.safe_load_all(Path(filename).read_text()))
    if not docs or any(not isinstance(p, dict) for p in docs):
        raise SystemExit(f"{filename}: empty/non-object YAML")
    for pod in docs:
        if (pod.get("apiVersion"), pod.get("kind")) != ("v1", "Pod"):
            raise SystemExit(f"{filename}: only explicit v1 Pod test inputs are supported")
        meta = pod.setdefault("metadata", {})
        if meta.get("namespace", namespace) != namespace:
            raise SystemExit(f"{filename}: namespace mismatch")
        meta["namespace"] = namespace
        pods.append(pod)
base = ["kubectl", "--context", context, "--request-timeout=30s"]
ns = json.loads(subprocess.run(
    base + ["get", "namespace", namespace, "-o", "json"],
    check=True, text=True, capture_output=True).stdout)
labels = ns["metadata"].get("labels", {})
if (labels.get("pod-security.kubernetes.io/enforce"),
    labels.get("pod-security.kubernetes.io/enforce-version")) != ("restricted", "v1.35"):
    raise SystemExit("Test namespace must explicitly enforce restricted:v1.35")

def dry_run(pod):
    return subprocess.run(
        base + ["create", "--dry-run=server", "--validate=strict",
                "--namespace", namespace, "-f", "-"],
        input=json.dumps(pod), text=True, capture_output=True)

control = {
    "apiVersion": "v1", "kind": "Pod",
    "metadata": {"generateName": "pss-control-", "namespace": namespace},
    "spec": {
        "automountServiceAccountToken": False,
        "securityContext": {"runAsNonRoot": True, "runAsUser": 65532,
                            "seccompProfile": {"type": "RuntimeDefault"}},
        "containers": [{"name": "probe", "image": "registry.k8s.io/pause:3.10",
                        "securityContext": {"allowPrivilegeEscalation": False,
                                            "capabilities": {"drop": ["ALL"]}}}],
    },
}
good = dry_run(control)
if good.returncode:
    raise SystemExit("Positive control failed; no compliance result:\n" + good.stderr)
bad = copy.deepcopy(control)
bad["spec"]["hostPID"] = True
denied = dry_run(bad)
if denied.returncode == 0 or 'violates PodSecurity "restricted:v1.35"' not in denied.stderr:
    raise SystemExit("Negative control did not confirm PSA rejection:\n" + denied.stderr)
for pod in pods:
    result = dry_run(pod)
    if result.returncode:
        raise SystemExit("Pod dry-run failed:\n" + result.stderr)
print(f"{len(pods)} explicit Pod inputs passed server dry-run in {namespace}")
```

```bash
python3 check-pss.py "$PSS_CONTEXT" "$PSS_NAMESPACE" ./pss-inputs/web-pod.yaml
```

명시적 입력 목록은 init 컨테이너를 포함한 각 워크로드의 Pod template을 빠짐없이 반영해야 합니다. Deployment·빈 파일·다른 namespace·조회 오류·미설정 enforce·예외/비활성 대조군 경로는 실패합니다. template 추출, 변이 webhook, 스케줄링, 이미지 기동, 이후 실행 동작은 별도 검증입니다. 위반 대조군은 PSA로 거부되어야 하며 다른 오류는 판정 불가로 실패합니다. 후보 Pod가 별도의 예외 RuntimeClass 등을 선택하는 경우도 테스트 클러스터 소유자가 금지하거나 별도 검사해야 합니다.

### 5단계: 문서화 및 교육

```markdown
# Pod Security Standards 가이드라인

## 개발자를 위한 체크리스트

### Restricted 수준 Pod 작성 시:

- [ ] `spec.securityContext.runAsNonRoot: true` 설정
- [ ] `spec.securityContext.seccompProfile.type: RuntimeDefault` 설정
- [ ] 모든 컨테이너에 `allowPrivilegeEscalation: false` 설정
- [ ] 모든 컨테이너에 `capabilities.drop: ["ALL"]` 설정
- [ ] `readOnlyRootFilesystem: true` 설정 (권장)
- [ ] 비특권 이미지 사용 (예: nginxinc/nginx-unprivileged)
- [ ] 쓰기 가능 경로에 emptyDir 마운트

### 일반적인 문제 해결:

1. **nginx가 포트 80에 바인딩 실패**
   → `NET_BIND_SERVICE` capability 추가 또는 8080 포트 사용

2. **파일 쓰기 실패**
   → emptyDir 볼륨을 필요한 경로에 마운트

3. **프로세스가 root로 실행됨**
   → 비특권 기본 이미지 사용 또는 Dockerfile에서 USER 지시자 사용
```

---

## 문제 해결

### 일반적인 오류 및 해결 방법

#### 1. "allowPrivilegeEscalation != false" 오류

오류 문구 예시이며 아래 YAML은 독립 매니페스트가 아닌 **Pod spec 수정 조각**입니다. 기존 이미지·설정을 보존하고 컨테이너별 제약은 init·ephemeral 컨테이너에도 적용합니다.

```text
allowPrivilegeEscalation != false
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
```

#### 2. "unrestricted capabilities" 오류

오류 문구 예시이며 아래 YAML은 독립 매니페스트가 아닌 **Pod spec 수정 조각**입니다. 기존 이미지·설정을 보존하고 컨테이너별 제약은 init·ephemeral 컨테이너에도 적용합니다.

```text
unrestricted capabilities
```

```yaml
spec:
  containers:
  - name: app
    securityContext:
      capabilities:
        drop: [ALL]
```

#### 3. "runAsNonRoot != true" 오류

오류 문구 예시이며 아래 YAML은 독립 매니페스트가 아닌 **Pod spec 수정 조각**입니다. 기존 이미지·설정을 보존하고 컨테이너별 제약은 init·ephemeral 컨테이너에도 적용합니다.

```text
runAsNonRoot != true
```

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 101
```

#### 4. "seccompProfile" 오류

오류 문구 예시이며 아래 YAML은 독립 매니페스트가 아닌 **Pod spec 수정 조각**입니다. 기존 이미지·설정을 보존하고 컨테이너별 제약은 init·ephemeral 컨테이너에도 적용합니다.

```text
seccompProfile must be RuntimeDefault or Localhost
```

```yaml
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault
```

### PSS 위반 검사 도구

Polaris·kube-score·Trivy는 추가 정적 검사 도구이며 클러스터의 버전별 PSA 정책·예외·변이를 정확히 대신하지 않습니다. 검토한 버전을 설치하고 CLI help를 확인합니다. 서버 dry-run 성공은 그 요청·주체·namespace·시점에 한정되며 위의 명시적 Pod 대조군 절차를 사용합니다.

```bash
# kubectl을 사용한 dry-run 검사
kubectl apply -f my-pod.yaml --dry-run=server

# Polaris를 사용한 검사
polaris audit --audit-path ./k8s/ --format pretty

# kube-score를 사용한 검사
kube-score score my-deployment.yaml

# Trivy를 사용한 설정 검사
trivy config ./k8s/
```

---

## 요약

Pod Security Standards(PSS)는 Kubernetes에서 Pod 보안을 관리하는 표준화된 방법을 제공합니다:

1. **세 가지 보안 수준**: Privileged(모든 권한), Baseline(알려진 권한 상승 방지), Restricted(최소 권한)
2. **세 가지 적용 모드**: enforce(차단), audit(로깅), warn(경고)
3. **네임스페이스 레이블로 간단히 구성**: RBAC 바인딩 없이 레이블만으로 정책 적용
4. **점진적 도입 지원**: warn/audit 모드를 통한 안전한 마이그레이션

### 권장 사항

- 새 클러스터는 처음부터 PSS를 활성화
- 기존 클러스터는 warn 모드부터 시작하여 점진적으로 강화
- 프로덕션 환경에서는 최소한 baseline 수준 적용 권장
- 민감한 워크로드에는 restricted 수준 적용

---

## 참고 자료

- [Kubernetes Pod Security Standards 공식 문서](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [Pod Security Admission 공식 문서](https://kubernetes.io/docs/concepts/security/pod-security-admission/)
- [EKS Best Practices Guide - Pod Security](https://docs.aws.amazon.com/eks/latest/best-practices/pod-security.html)
- [PSP에서 PSS로 마이그레이션 가이드](https://kubernetes.io/docs/tasks/configure-pod-container/migrate-from-psp/)

- [PSA namespace 레이블 미리보기와 기존 Pod 검사](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-namespace-labels/)
- [PSA 설정과 예외](https://kubernetes.io/docs/tasks/configure-pod-container/enforce-standards-admission-controller/)
- [Nginx 비특권 이미지와 쓰기 경로](https://github.com/nginx/docker-nginx-unprivileged)
