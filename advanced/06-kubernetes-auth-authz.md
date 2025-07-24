# Kubernetes 인증 및 권한 부여 시스템

> **지원 버전**: Kubernetes 1.31, 1.32, 1.33  
> **마지막 업데이트**: 2025년 7월 25일

## 개요

Kubernetes의 인증(Authentication) 및 권한 부여(Authorization) 시스템은 클러스터 보안의 핵심 요소입니다. 이 문서에서는 Kubernetes의 인증 및 권한 부여 메커니즘을 자세히 살펴보고, 실제 환경에서 이를 구성하는 방법을 설명합니다.

## 인증(Authentication)

인증은 사용자 또는 서비스가 자신이 주장하는 대상인지 확인하는 프로세스입니다. Kubernetes는 여러 인증 방법을 지원하며, 이들은 동시에 활성화될 수 있습니다.

### 인증 전략

#### 1. X.509 인증서

X.509 인증서는 Kubernetes에서 가장 일반적인 인증 방법입니다. 클라이언트 인증서는 클러스터의 인증 기관(CA)에 의해 서명되어야 합니다.

**인증서 생성 예시:**

```bash
# 개인 키 생성
openssl genrsa -out john.key 2048

# 인증서 서명 요청(CSR) 생성
openssl req -new -key john.key -out john.csr -subj "/CN=john/O=engineering"

# Kubernetes CA로 CSR 서명
openssl x509 -req -in john.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out john.crt -days 365
```

**kubeconfig 구성:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority-data: <BASE64_ENCODED_CA_CERT>
    server: https://kubernetes.example.com
users:
- name: john
  user:
    client-certificate-data: <BASE64_ENCODED_CLIENT_CERT>
    client-key-data: <BASE64_ENCODED_CLIENT_KEY>
contexts:
- name: john@my-cluster
  context:
    cluster: my-cluster
    user: john
current-context: john@my-cluster
```

#### 2. 서비스 계정 토큰

서비스 계정은 파드 내에서 실행되는 프로세스의 ID를 제공합니다. 각 네임스페이스에는 기본 서비스 계정이 있으며, 추가 서비스 계정을 생성할 수 있습니다.

**서비스 계정 생성:**

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
```

**파드에 서비스 계정 할당:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  serviceAccountName: my-service-account
  containers:
  - name: my-container
    image: nginx
```

#### 3. OpenID Connect (OIDC)

OIDC는 외부 ID 제공자(예: Google, Azure AD, Okta)를 통한 인증을 지원합니다.

**API 서버 구성 예시:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    server: https://kubernetes.example.com
    certificate-authority-data: <BASE64_ENCODED_CA_CERT>
users:
- name: oidc-user
  user:
    auth-provider:
      name: oidc
      config:
        client-id: <CLIENT_ID>
        client-secret: <CLIENT_SECRET>
        id-token: <ID_TOKEN>
        refresh-token: <REFRESH_TOKEN>
        idp-issuer-url: https://accounts.google.com
contexts:
- name: oidc-context
  context:
    cluster: my-cluster
    user: oidc-user
current-context: oidc-context
```

#### 4. 웹훅 토큰 인증

웹훅 토큰 인증은 외부 서비스를 통해 토큰을 검증합니다.

**API 서버 구성:**

```yaml
apiVersion: v1
kind: Config
# ...
authentication:
  webhook:
    config:
      url: https://authn.example.com/authenticate
      caCert: <BASE64_ENCODED_CA_CERT>
```

#### 5. 인증 프록시

인증 프록시는 API 서버 앞에 위치하여 인증을 처리합니다.

**API 서버 구성:**

```yaml
apiVersion: v1
kind: Config
# ...
authentication:
  proxy:
    headerName: X-Remote-User
    usernameHeaders: ["X-Remote-User"]
    groupHeaders: ["X-Remote-Group"]
```

### 사용자 및 그룹

Kubernetes에서 사용자는 다음과 같이 분류됩니다:

1. **일반 사용자**: 클러스터 외부에서 관리되며, Kubernetes에서는 직접 관리하지 않습니다.
2. **서비스 계정**: Kubernetes API에 의해 관리되는 계정입니다.

사용자는 하나 이상의 그룹에 속할 수 있으며, 그룹은 권한 부여 정책에서 사용됩니다.

## 권한 부여(Authorization)

권한 부여는 인증된 사용자가 요청한 작업을 수행할 권한이 있는지 확인하는 프로세스입니다. Kubernetes는 여러 권한 부여 모듈을 지원합니다.

### 권한 부여 모드

#### 1. RBAC (Role-Based Access Control)

RBAC는 역할 기반 액세스 제어를 제공하며, 현재 Kubernetes에서 가장 널리 사용되는 권한 부여 메커니즘입니다.

**주요 개념:**

1. **Role**: 네임스페이스 내에서 권한을 정의합니다.
2. **ClusterRole**: 클러스터 전체 범위의 권한을 정의합니다.
3. **RoleBinding**: Role을 사용자, 그룹 또는 서비스 계정에 바인딩합니다.
4. **ClusterRoleBinding**: ClusterRole을 사용자, 그룹 또는 서비스 계정에 바인딩합니다.

**Role 예시:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**RoleBinding 예시:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: read-pods
  namespace: default
subjects:
- kind: User
  name: john
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

**ClusterRole 예시:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: secret-reader
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get", "watch", "list"]
```

**ClusterRoleBinding 예시:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-secrets-global
subjects:
- kind: Group
  name: security-team
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

#### 2. ABAC (Attribute-Based Access Control)

ABAC는 속성 기반 액세스 제어를 제공합니다. 정책은 JSON 파일로 정의됩니다.

**정책 예시:**

```json
{
  "apiVersion": "abac.authorization.kubernetes.io/v1beta1",
  "kind": "Policy",
  "spec": {
    "user": "john",
    "namespace": "default",
    "resource": "pods",
    "readonly": true
  }
}
```

#### 3. Node 권한 부여

Node 권한 부여는 kubelet이 API 서버에 접근할 때 사용됩니다.

#### 4. Webhook 권한 부여

Webhook 권한 부여는 외부 서비스를 통해 권한 부여 결정을 내립니다.

**API 서버 구성:**

```yaml
apiVersion: v1
kind: Config
# ...
authorization:
  webhook:
    config:
      url: https://authz.example.com/authorize
      caCert: <BASE64_ENCODED_CA_CERT>
```

### 권한 부여 모범 사례

1. **최소 권한 원칙**: 필요한 최소한의 권한만 부여합니다.
2. **역할 분리**: 관리자, 개발자, 운영자 등 역할에 따라 적절한 권한을 부여합니다.
3. **네임스페이스 분리**: 팀 또는 프로젝트별로 네임스페이스를 분리하고 적절한 권한을 부여합니다.
4. **서비스 계정 분리**: 각 애플리케이션에 대해 별도의 서비스 계정을 사용합니다.
5. **정기적인 감사**: 권한 부여 정책을 정기적으로 검토하고 업데이트합니다.

## 어드미션 컨트롤(Admission Control)

어드미션 컨트롤은 인증 및 권한 부여 후에 요청을 처리하기 전에 추가 검증 및 수정을 수행합니다.

### 어드미션 컨트롤러 유형

1. **변경 어드미션 컨트롤러**: 요청을 수정할 수 있습니다.
2. **검증 어드미션 컨트롤러**: 요청을 검증만 하고 수정하지 않습니다.

### 주요 어드미션 컨트롤러

1. **LimitRanger**: 파드 및 컨테이너의 리소스 제한을 설정합니다.
2. **ResourceQuota**: 네임스페이스별 리소스 사용량을 제한합니다.
3. **PodSecurityPolicy**: 파드의 보안 컨텍스트를 제한합니다.
4. **ServiceAccount**: 파드에 서비스 계정을 자동으로 할당합니다.
5. **DefaultStorageClass**: 기본 스토리지 클래스를 설정합니다.

### 동적 어드미션 컨트롤

동적 어드미션 컨트롤은 웹훅을 통해 구현됩니다:

1. **MutatingAdmissionWebhook**: 요청을 수정할 수 있습니다.
2. **ValidatingAdmissionWebhook**: 요청을 검증만 하고 수정하지 않습니다.

**웹훅 구성 예시:**

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingWebhookConfiguration
metadata:
  name: pod-policy-webhook
webhooks:
- name: pod-policy.example.com
  clientConfig:
    url: https://pod-policy.example.com/validate
    caBundle: <BASE64_ENCODED_CA_CERT>
  rules:
  - apiGroups: [""]
    apiVersions: ["v1"]
    resources: ["pods"]
    operations: ["CREATE", "UPDATE"]
    scope: "Namespaced"
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

## 실제 구현 예시

### EKS에서의 인증 및 권한 부여 구성

#### IAM과 RBAC 통합

Amazon EKS는 AWS IAM과 Kubernetes RBAC를 통합하여 인증 및 권한 부여를 제공합니다.

**aws-auth ConfigMap:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aws-auth
  namespace: kube-system
data:
  mapRoles: |
    - rolearn: arn:aws:iam::123456789012:role/EKSAdminRole
      username: admin
      groups:
        - system:masters
    - rolearn: arn:aws:iam::123456789012:role/EKSDeveloperRole
      username: developer
      groups:
        - developers
  mapUsers: |
    - userarn: arn:aws:iam::123456789012:user/john
      username: john
      groups:
        - developers
```

#### OIDC 제공자 구성

```bash
# OIDC 제공자 생성
eksctl utils associate-iam-oidc-provider \
    --cluster my-cluster \
    --approve

# IAM 역할 생성 및 서비스 계정 연결
eksctl create iamserviceaccount \
    --name my-service-account \
    --namespace default \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
    --approve
```

### 멀티 테넌트 클러스터 보안

멀티 테넌트 환경에서는 테넌트 간 격리가 중요합니다.

**네임스페이스 격리:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-a
  labels:
    tenant: a
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-from-other-namespaces
  namespace: tenant-a
spec:
  podSelector: {}
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

**리소스 할당량:**

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-a-quota
  namespace: tenant-a
spec:
  hard:
    pods: "10"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.cpu: "8"
    limits.memory: 16Gi
```

## 보안 모범 사례

1. **정기적인 인증서 순환**: 인증서를 정기적으로 갱신합니다.
2. **서비스 계정 토큰 자동 마운트 비활성화**: 필요하지 않은 경우 서비스 계정 토큰 자동 마운트를 비활성화합니다.
3. **RBAC 정책 최소화**: 필요한 최소한의 권한만 부여합니다.
4. **네트워크 정책 구현**: 파드 간 통신을 제한합니다.
5. **감사 로깅 활성화**: 모든 API 요청을 로깅하고 모니터링합니다.
6. **보안 컨텍스트 설정**: 파드 및 컨테이너의 보안 컨텍스트를 적절히 구성합니다.
7. **이미지 스캐닝**: 컨테이너 이미지의 취약점을 정기적으로 스캔합니다.

## 결론

Kubernetes의 인증 및 권한 부여 시스템은 클러스터 보안의 핵심 요소입니다. 적절한 인증 방법을 선택하고, RBAC를 통해 세밀한 권한 제어를 구현하며, 어드미션 컨트롤러를 활용하여 추가적인 보안 정책을 적용함으로써 안전한 Kubernetes 환경을 구축할 수 있습니다.

인증, 권한 부여, 어드미션 컨트롤은 서로 보완적인 역할을 하며, 이들을 함께 사용하여 심층 방어(Defense in Depth) 전략을 구현하는 것이 중요합니다.
