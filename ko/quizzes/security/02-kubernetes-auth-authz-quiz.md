# Kubernetes 인증 및 권한 부여 퀴즈

> **관련 문서**: [Kubernetes 인증 및 권한 부여 시스템](../../security/02-kubernetes-auth-authz.md)

## 객관식 문제

### 1. Kubernetes에서 X.509 인증서를 사용한 인증 시, 사용자 이름은 어느 필드에서 추출됩니까?

- A) Subject Alternative Name (SAN)
- B) Common Name (CN)
- C) Organization Unit (OU)
- D) Issuer

<details>
<summary>정답 보기</summary>

**정답: B) Common Name (CN)**

**설명:**
X.509 인증서에서 Common Name(CN)은 사용자 이름으로, Organization(O)은 그룹으로 매핑됩니다.

</details>

### 2. RBAC에서 ClusterRole과 Role의 주요 차이점은 무엇입니까?

- A) ClusterRole은 읽기 전용, Role은 읽기/쓰기
- B) ClusterRole은 클러스터 전체 범위, Role은 네임스페이스 범위
- C) ClusterRole은 관리자 전용, Role은 일반 사용자 전용
- D) ClusterRole은 노드에만 적용, Role은 파드에만 적용

<details>
<summary>정답 보기</summary>

**정답: B) ClusterRole은 클러스터 전체 범위, Role은 네임스페이스 범위**

**설명:**
Role은 특정 네임스페이스 내의 리소스에 대한 권한을 정의하고, ClusterRole은 클러스터 전체 또는 네임스페이스가 없는 리소스에 대한 권한을 정의합니다.

</details>

### 3. ServiceAccount 토큰이 파드에 자동으로 마운트되는 기본 경로는?

- A) /var/run/secrets/kubernetes.io/token
- B) /etc/kubernetes/serviceaccount
- C) /var/run/secrets/kubernetes.io/serviceaccount
- D) /opt/kubernetes/secrets

<details>
<summary>정답 보기</summary>

**정답: C) /var/run/secrets/kubernetes.io/serviceaccount**

**설명:**
ServiceAccount 토큰은 기본적으로 `/var/run/secrets/kubernetes.io/serviceaccount` 경로에 마운트됩니다.

</details>

### 4. MutatingAdmissionWebhook과 ValidatingAdmissionWebhook의 실행 순서는?

- A) Validating이 먼저, Mutating이 나중에
- B) Mutating이 먼저, Validating이 나중에
- C) 동시에 병렬로 실행
- D) 순서 없이 무작위로 실행

<details>
<summary>정답 보기</summary>

**정답: B) Mutating이 먼저, Validating이 나중에**

**설명:**
어드미션 컨트롤러 실행 순서: 1) MutatingAdmissionWebhook(요청 수정), 2) ValidatingAdmissionWebhook(요청 검증).

</details>

### 5. EKS에서 IAM 사용자/역할을 Kubernetes RBAC에 매핑하는 ConfigMap은?

- A) kube-config
- B) aws-auth
- C) eks-iam-mapping
- D) cluster-auth

<details>
<summary>정답 보기</summary>

**정답: B) aws-auth**

**설명:**
Amazon EKS에서 `aws-auth` ConfigMap(kube-system 네임스페이스)은 AWS IAM 사용자 및 역할을 Kubernetes 사용자와 그룹에 매핑합니다.

</details>

### 6. 프로덕션 Kubernetes 클러스터에 권장되는 인증 방법은?

- A) 정적 토큰 파일
- B) 기본 인증
- C) OIDC (OpenID Connect)
- D) 익명 인증

<details>
<summary>정답 보기</summary>

**정답: C) OIDC (OpenID Connect)**

**설명:**
OIDC는 토큰 만료, 갱신 토큰, Okta, Azure AD, Google과 같은 ID 공급자와의 통합 등 엔터프라이즈급 인증 기능을 제공합니다.

</details>

### 7. Kubernetes에서 `system:masters` 그룹의 목적은?

- A) 마스터 노드 관리
- B) cluster-admin 권한 제공
- C) 마스터 노드에 파드 스케줄링
- D) 시스템 네임스페이스 관리

<details>
<summary>정답 보기</summary>

**정답: B) cluster-admin 권한 제공**

**설명:**
`system:masters` 그룹은 `cluster-admin` ClusterRole에 바인딩되어 클러스터에 대한 전체 관리 액세스 권한을 부여합니다.

</details>

### 8. ServiceAccount가 특정 네임스페이스에서 파드만 읽을 수 있도록 제한하는 방법은?

- A) ClusterRole + ClusterRoleBinding
- B) Role + ClusterRoleBinding
- C) ClusterRole + RoleBinding
- D) Role + RoleBinding

<details>
<summary>정답 보기</summary>

**정답: D) Role + RoleBinding**

**설명:**
네임스페이스 범위 권한의 경우, Role(네임스페이스 내 권한 정의)과 RoleBinding(동일 네임스페이스 내 주체에 역할 바인딩)을 사용합니다.

</details>

### 9. RBAC에서 `impersonate` 동사의 목적은?

- A) 가짜 리소스 생성
- B) 사용자가 다른 사용자나 그룹으로 행동할 수 있게 허용
- C) 리소스 복제
- D) 리소스 이름 마스킹

<details>
<summary>정답 보기</summary>

**정답: B) 사용자가 다른 사용자나 그룹으로 행동할 수 있게 허용**

**설명:**
`impersonate` 동사는 사용자가 다른 사용자, 그룹 또는 ServiceAccount인 것처럼 작업을 수행할 수 있게 합니다. 디버깅과 관리 목적에 유용합니다.

</details>

### 10. 마운트된 볼륨에서 ServiceAccount 토큰이 포함된 파일은?

- A) ca.crt
- B) namespace
- C) token
- D) serviceaccount.json

<details>
<summary>정답 보기</summary>

**정답: C) token**

**설명:**
ServiceAccount 볼륨 마운트에는 세 개의 파일이 포함됩니다: `ca.crt`(CA 인증서), `namespace`(현재 네임스페이스), `token`(인증용 JWT 토큰).

</details>

## 단답형 문제

### 1. Kubernetes에서 사용자 계정과 서비스 계정의 주요 차이점은 무엇입니까?

<details>
<summary>정답 보기</summary>

**정답: 사용자 계정은 외부에서 관리되고 Kubernetes가 직접 관리하지 않으며, 서비스 계정은 Kubernetes API로 관리되는 네임스페이스 리소스입니다.**

</details>

### 2. 서비스 계정 토큰의 자동 마운트를 비활성화하는 방법은?

<details>
<summary>정답 보기</summary>

**정답: ServiceAccount 또는 Pod spec에서 automountServiceAccountToken: false를 설정합니다.**

</details>

### 3. ClusterRole에서 `rules`와 `aggregationRule`의 차이점은?

<details>
<summary>정답 보기</summary>

**정답: `rules`는 권한을 직접 정의하고, `aggregationRule`은 특정 레이블과 일치하는 다른 ClusterRole의 권한을 자동으로 결합합니다.**

**설명:**
집계된 ClusterRole은 내장 역할을 직접 수정하지 않고 확장하는 데 유용합니다.

</details>

### 4. TokenRequest API란 무엇이며 정적 토큰보다 선호되는 이유는?

<details>
<summary>정답 보기</summary>

**정답: TokenRequest API는 장수명 정적 토큰보다 더 안전한 시간 제한, 대상 바인딩 토큰을 생성합니다.**

**설명:**
TokenRequest API의 토큰은 자동으로 만료되고 특정 대상에 바인딩되어 토큰 도난 및 오용 위험을 줄입니다.

</details>

### 5. 여러 인증 방법이 구성된 경우 Kubernetes가 어떤 방법을 사용할지 결정하는 방법은?

<details>
<summary>정답 보기</summary>

**정답: Kubernetes는 각 인증 방법을 순서대로 시도하여 첫 번째로 성공한 인증을 사용합니다.**

**설명:**
인증 방법은 체인으로 시도됩니다. 모든 방법이 실패하면 요청은 401 Unauthorized 오류로 거부됩니다.

</details>

## 실습 문제

### 1. 다음 요구사항을 충족하는 Role과 RoleBinding을 작성하세요.

- 네임스페이스: development
- 권한: Pod 읽기(get, list, watch), ConfigMap 전체 권한
- 사용자: developer@example.com

<details>
<summary>정답 보기</summary>

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: development
  name: developer-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: developer-binding
  namespace: development
subjects:
- kind: User
  name: developer@example.com
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-role
  apiGroup: rbac.authorization.k8s.io
```

</details>

### 2. 커스텀 토큰 만료 시간이 있는 ServiceAccount를 생성하세요.

<details>
<summary>정답 보기</summary>

```yaml
# ServiceAccount 정의
apiVersion: v1
kind: ServiceAccount
metadata:
  name: custom-sa
  namespace: default
---
# 커스텀 만료가 있는 projected 토큰을 사용하는 Pod
apiVersion: v1
kind: Pod
metadata:
  name: app-with-custom-token
spec:
  serviceAccountName: custom-sa
  containers:
  - name: app
    image: nginx
    volumeMounts:
    - name: token
      mountPath: /var/run/secrets/tokens
  volumes:
  - name: token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          expirationSeconds: 3600  # 1시간
          audience: api
```

**설명:**
`serviceAccountToken`이 있는 projected 볼륨을 사용하면 커스텀 `expirationSeconds`(최소 600초)와 토큰의 `audience`를 지정할 수 있습니다.

</details>

### 3. 특정 사용자의 권한을 확인하는 명령어를 작성하세요.

<details>
<summary>정답 보기</summary>

```bash
# 사용자가 특정 작업을 수행할 수 있는지 확인
kubectl auth can-i create deployments --as=developer@example.com -n development

# 네임스페이스에서 사용자의 모든 권한 나열
kubectl auth can-i --list --as=developer@example.com -n development

# ServiceAccount의 권한 확인
kubectl auth can-i --list --as=system:serviceaccount:default:my-sa

# 그룹 가장
kubectl auth can-i create pods --as=developer@example.com --as-group=developers -n development
```

**설명:**
`kubectl auth can-i` 명령어는 현재 사용자의 권한을 확인하거나 다른 사용자/그룹을 가장하여 액세스 수준을 확인할 수 있습니다.

</details>

## 심화 문제

### 1. 멀티 테넌트 Kubernetes 클러스터에서 테넌트 간 격리를 위한 보안 전략을 설계하세요.

<details>
<summary>정답 보기</summary>

**네임스페이스 및 RBAC 설계:**
- 테넌트별 네임스페이스 생성
- Pod Security Standards 적용
- NetworkPolicy로 네트워크 격리
- ResourceQuota로 리소스 제한

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-alpha
  labels:
    tenant: alpha
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: tenant-alpha
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-quota
  namespace: tenant-alpha
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: tenant-admin
  namespace: tenant-alpha
rules:
- apiGroups: ["", "apps", "batch"]
  resources: ["*"]
  verbs: ["*"]
- apiGroups: ["networking.k8s.io"]
  resources: ["networkpolicies"]
  verbs: ["get", "list"]  # 네트워크 정책은 읽기 전용
```

**추가 보안 조치:**
- 애플리케이션별 별도 ServiceAccount 사용
- 감사 로깅 구현
- 정책 적용을 위한 어드미션 웹훅 사용
- 하위 테넌트 관리를 위한 계층적 네임스페이스 고려

</details>

### 2. kubectl 명령어 실행 시 완전한 인증 및 권한 부여 흐름을 설명하세요.

<details>
<summary>정답 보기</summary>

**완전한 흐름:**

1. **클라이언트 인증 (kubeconfig)**
   - kubectl이 `~/.kube/config` 읽음
   - 자격 증명 추출 (인증서, 토큰 또는 exec 플러그인)
   - EKS의 경우: `aws eks get-token`이 임시 토큰 생성

2. **API 서버 인증**
   - API 서버가 자격 증명과 함께 요청 수신
   - 순서대로 인증 방법 시도:
     - X.509 클라이언트 인증서
     - Bearer 토큰 (ServiceAccount, OIDC)
     - 인증 프록시
     - 웹훅 토큰 인증
   - 첫 번째 성공한 방법이 신원 결정

3. **권한 부여**
   - API 서버가 권한 부여 확인 (일반적으로 RBAC)
   - 적용 가능한 모든 Role/ClusterRole 평가
   - 결정: 허용 또는 거부
   - 여러 권한 부여자가 있는 경우: 첫 번째 비거부가 승리

4. **어드미션 제어**
   - **Mutating Admission**: 요청 수정
     - 기본값 추가, 사이드카 주입
   - **Validating Admission**: 요청 검증
     - 정책 적용, 쿼터 확인
   - 둘 다 요청을 거부할 수 있음

5. **지속성**
   - 모든 검사를 통과하면 리소스가 etcd에 저장됨
   - 클라이언트에 응답 반환

```
kubectl -> kubeconfig -> API Server
                            |
                     Authentication
                            |
                     Authorization (RBAC)
                            |
                   Mutating Admission
                            |
                  Validating Admission
                            |
                         etcd
```

**핵심 포인트:**
- 인증은 당신이 누구인지 결정
- 권한 부여는 당신이 무엇을 할 수 있는지 결정
- 어드미션은 리소스가 어떻게 수정/검증되는지 제어

</details>
