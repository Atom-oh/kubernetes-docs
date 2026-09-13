# Kubernetes 인증 및 권한 부여 시스템

> **범위**: Kubernetes 안정 API와 Amazon EKS 사용자 접근 관리
> **마지막 업데이트**: 2026년 9월 13일

## 개요

인증은 요청의 신원을 확인하고, 인가는 그 신원이 수행할 수 있는 API 작업을 결정하며, 어드미션은 허용된 변경 요청에 추가 정책을 적용합니다. 아래 매니페스트는 독립적인 학습 예제이며, 네임스페이스·관리 권한·인증서·웹훅 서버를 미리 준비해야 합니다. 실제 클러스터/API 호출이나 EKS 접근 변경은 검증하지 않았습니다.

`kube-apiserver` 플래그 예제는 **직접 운영하는 컨트롤 플레인**에만 해당합니다. EKS에는 관리형 접근 설정을 사용하며, 사용자가 API 서버 플래그나 EKS CA 개인 키를 직접 설정·취득하는 절차로 해석하면 안 됩니다.

## 인증(Authentication)

인증은 사용자 또는 서비스가 자신이 주장하는 대상인지 확인하는 프로세스입니다. Kubernetes는 여러 인증 방법을 지원하며, 이들은 동시에 활성화될 수 있습니다.

여러 인증기를 함께 사용할 때 첫 번째 성공한 인증 결과가 사용되지만, 실행 순서는 보장되지 않습니다. 잘못된 자격 증명은 인증 실패를 일으킵니다. 자격 증명이 없는 요청의 익명 처리는 서버 설정에 따라 달라지며, 익명 신원도 인가를 통과해야 합니다.

### 인증 전략

#### 1. X.509 인증서

API 서버가 `--client-ca-file`로 신뢰하는 **클라이언트 CA**가 서명한 인증서를 사용합니다. Subject의 CN은 사용자 이름, O는 그룹으로 해석되며, 인증서에는 클라이언트 인증 용도(`clientAuth`)가 필요합니다. 서버 TLS를 검증하는 CA와 클라이언트를 인증하는 CA는 역할이 다릅니다.

**로컬 개인 키와 CSR 생성 예시:**

```bash
umask 077
auth_lab_dir=$(mktemp -d)
openssl genrsa -out "$auth_lab_dir/john.key" 2048
openssl req -new -key "$auth_lab_dir/john.key" \
  -out "$auth_lab_dir/john.csr" -subj '/CN=john/O=engineering'
openssl req -in "$auth_lab_dir/john.csr" -noout -verify
```

이 명령은 인증서를 발급하지 않습니다. 승인된 발급자에게 **CSR만** 전달하고, 사용자·그룹·용도·유효기간을 검토받습니다. CA 개인 키를 작업자에게 복사하거나 CSR의 조직명을 검토 없이 승인하지 않습니다. EKS의 `beta.eks.amazonaws.com/app-serving` 서명자는 서버 인증서용이며 사용자 클라이언트 인증서 서명을 지원하지 않습니다. EKS 사용자 접근에는 아래 IAM/OIDC 경로를 사용합니다.

**발급 후 kubeconfig 구성:**

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    certificate-authority: /secure/path/server-ca.crt
    server: https://kubernetes.example.com
users:
- name: john
  user:
    client-certificate: /secure/path/john.crt
    client-key: /secure/path/john.key
contexts:
- name: john@my-cluster
  context:
    cluster: my-cluster
    user: john
    namespace: default
current-context: john@my-cluster
```

경로를 실제 발급 파일로 바꾸고 개인 키·kubeconfig 접근 권한을 제한합니다. `*-data` 필드의 base64는 암호화가 아닙니다. 신뢰하지 않는 kubeconfig는 `exec` 플러그인 등을 실행할 수 있으므로 사용 전에 검사합니다.

#### 2. 서비스 계정 토큰

ServiceAccount는 네임스페이스에 속하는 워크로드 신원입니다. 각 네임스페이스에는 `default` 계정이 있으며, Pod의 `serviceAccountName`은 같은 네임스페이스의 계정을 가리킵니다. 계정을 지정하는 것만으로 업무 리소스 접근 권한이 생기지 않습니다.

API를 호출하지 않는 아래 예제는 자동 토큰 마운트를 비활성화합니다. 이미지도 네트워크 서비스를 제공하지 않는 예제용입니다.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
automountServiceAccountToken: false
---
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  namespace: default
spec:
  serviceAccountName: my-service-account
  automountServiceAccountToken: false
  containers:
  - name: my-container
    image: registry.k8s.io/pause:3.10
```

`automountServiceAccountToken`은 ServiceAccount에서는 최상위 필드, Pod에서는 `spec` 필드입니다. 둘 다 설정하면 Pod 설정이 우선합니다. 이 설정은 기본 마운트만 제어하며 명시적으로 선언한 `serviceAccountToken` projected volume을 막지 않습니다.

API 접근이 필요한 Pod의 기본 projected 토큰은 kubelet이 TokenRequest로 요청하고 갱신합니다. 기본 파일은 `/var/run/secrets/kubernetes.io/serviceaccount/token`입니다. 애플리케이션은 교체된 파일을 다시 읽어야 하며, 만료·audience가 있는 토큰도 보유자가 사용할 수 있는 비밀 자격 증명입니다. 장기 Secret 토큰이 계정 생성 시 자동 발급된다고 가정하지 않습니다. 사용자 지정 audience·만료 요청은 [퀴즈의 projected-volume 예제](../quizzes/security/02-kubernetes-auth-authz-quiz.md)에서 설명합니다.

#### 3. OpenID Connect (OIDC)

OIDC는 외부 IdP가 발급한 **ID 토큰**을 API 서버에서 검증하는 방식입니다. issuer·audience·서명·만료와 신원 매핑을 설정해야 합니다. API 서버가 로그인 화면이나 refresh token 발급을 제공하지는 않습니다. 클라이언트는 해당 IdP용으로 검토된 인증 도구 또는 `exec` 자격 증명 플러그인을 사용합니다.

**직접 운영하는 API 서버에 추가할 플래그 예시**입니다. 실행 가능한 전체 시작 명령이나 kubeconfig가 아니며, 실제 HTTPS IdP와 client ID로 바꿔야 합니다.

```text
--oidc-issuer-url=https://idp.example.com
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-username-prefix=oidc:
--oidc-groups-claim=groups
--oidc-groups-prefix=oidc:
```

사용자·그룹 접두사로 `system:` 등 기존 신원과 충돌하지 않도록 합니다. 구조화된 `AuthenticationConfiguration`을 사용하는 대안도 있으나 `--authentication-config`와 `--oidc-*` 플래그를 혼합하지 않습니다. EKS의 외부 OIDC 설정은 아래 별도 절차를 따릅니다.

#### 4. 웹훅 토큰 인증

직접 운영하는 API 서버가 외부 서비스에 `authentication.k8s.io/v1` **TokenReview**를 보내 토큰을 검증합니다. 아래는 API 서버가 서비스에 연결할 때 쓰는 **별도 kubeconfig**입니다. 사용자 kubeconfig에 `authentication.webhook` 필드를 추가하는 방식이 아닙니다.

```yaml
apiVersion: v1
kind: Config
clusters:
- name: authentication-service
  cluster:
    server: https://authn.example.com/authenticate
    certificate-authority: /etc/kubernetes/authn-webhook/ca.crt
users:
- name: kube-apiserver-webhook-client
  user:
    client-certificate: /etc/kubernetes/authn-webhook/client.crt
    client-key: /etc/kubernetes/authn-webhook/client.key
contexts:
- name: webhook
  context:
    cluster: authentication-service
    user: kube-apiserver-webhook-client
current-context: webhook
```

파일을 `/etc/kubernetes/authn-webhook.kubeconfig`에 설치했다면 `--authentication-token-webhook-config-file=/etc/kubernetes/authn-webhook.kubeconfig`와 `--authentication-token-webhook-version=v1`을 API 서버 설정에 추가합니다. 위 경로의 인증서와 서버는 별도 준비가 필요합니다. 서버는 토큰과 대상 audience를 검증하고 TokenReview 응답을 반환해야 합니다. TLS 상호 인증, 자격 증명 보호, 결과 캐시 TTL과 장애 시 동작도 설계해야 합니다. 이 예제에는 웹훅 구현이나 가용성 검증이 포함되지 않습니다.

#### 5. 인증 프록시

인증 프록시는 사용자를 인증한 뒤 검증된 사용자·그룹 정보를 API 서버에 전달합니다. 헤더 이름만 설정하는 것으로 신뢰가 만들어지지 않습니다. 전용 front-proxy CA와 허용된 클라이언트 인증서 CN을 사용해 프록시의 TLS 신원을 먼저 검증합니다.

**직접 운영하는 API 서버의 플래그 일부:**

```text
--requestheader-client-ca-file=/etc/kubernetes/front-proxy-ca.crt
--requestheader-allowed-names=front-proxy-client
--requestheader-username-headers=X-Remote-User
--requestheader-group-headers=X-Remote-Group
```

프록시는 외부 요청이 보낸 신원 헤더를 제거한 뒤 검증한 값으로 다시 설정해야 합니다. 일반 사용자용 CA를 프록시 CA로 재사용하거나 허용 CN을 비워 모든 인증서를 신뢰하지 않습니다. 위 구성은 인증 프록시 서버 자체를 구현하지 않습니다.

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
2. **ClusterRole**: 클러스터 범위 객체이며, 클러스터 리소스·비리소스 URL 또는 재사용할 네임스페이스 리소스 권한을 정의합니다.
3. **RoleBinding**: 같은 네임스페이스의 Role 또는 ClusterRole을 참조하여 **바인딩 네임스페이스 안에서만** 권한을 부여합니다. 다른 네임스페이스의 ServiceAccount도 주체로 명시할 수 있습니다.
4. **ClusterRoleBinding**: ClusterRole의 권한을 클러스터 전체에 부여합니다. Role은 참조할 수 없습니다.

역할 정의만으로 권한이 생기지 않습니다. RBAC는 허용 권한의 합집합이며 명시적 거부 규칙이 없습니다. Secret의 `get/list/watch`는 비밀 데이터 읽기를 허용하므로 아래 예제는 Pod 읽기만 사용합니다.

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
  name: pod-reader-reusable
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "watch", "list"]
```

**ClusterRoleBinding 예시:**

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: read-pods-global
subjects:
- kind: Group
  name: cluster-inventory-readers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: pod-reader-reusable
  apiGroup: rbac.authorization.k8s.io
```

위 ClusterRoleBinding은 **모든 네임스페이스의 Pod 정보**가 필요한 운영 그룹을 설명하는 예시이며 기본 권장 권한이 아닙니다. 한 네임스페이스만 필요하면 ClusterRoleBinding 대신 해당 네임스페이스의 RoleBinding에서 `roleRef.kind: ClusterRole`, `roleRef.name: pod-reader-reusable`을 참조합니다.

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
    "apiGroup": "",
    "resource": "pods",
    "readonly": true
  }
}
```

ABAC는 기존 직접 운영 클러스터를 이해하기 위한 내용입니다. `--authorization-policy-file`로 읽는 정책은 **한 줄에 JSON 객체 하나**를 기록하는 파일이며 Kubernetes API 리소스가 아닙니다. 위 들여쓰기는 설명용이고 실제 파일에서는 한 줄로 직렬화해야 합니다. 파일 변경 후 API 서버 재시작이 필요합니다. 새 구성에는 일반적으로 RBAC를 사용하며 EKS에 이 플래그를 적용하지 않습니다.

#### 3. Node 권한 부여

Node 인가는 kubelet 전용입니다. 요청 신원이 `system:nodes` 그룹과 `system:node:<nodeName>` 사용자 형식에 맞고 실제 노드 이름과 일치해야 합니다. 일반 워크로드용 접근 권한이 아닙니다. 직접 운영 클러스터에서는 NodeRestriction 어드미션과 함께 구성하여 kubelet의 노드·Pod 변경 범위를 제한합니다.

#### 4. Webhook 권한 부여

직접 운영하는 API 서버가 외부 서비스에 `authorization.k8s.io/v1` **SubjectAccessReview**를 보내 인가 결정을 받습니다. 위 인증 웹훅 kubeconfig와 같은 연결 형식을 사용하되 인가 서비스 URL, CA, 클라이언트 인증서를 별도로 설정합니다. `--authorization-webhook-config-file`과 `--authorization-webhook-version=v1`을 사용하거나 구조화된 `AuthorizationConfiguration`에서 체인·실패 정책을 구성합니다. 사용자 kubeconfig의 `authorization.webhook` 필드는 존재하지 않습니다.

인가기는 구성 순서대로 실행하며 첫 **Allow 또는 Deny**가 결정입니다. `NoOpinion`이면 다음 인가기에서 평가하고 모두 NoOpinion이면 거부합니다. RBAC가 먼저 허용하면 뒤의 웹훅은 이를 취소할 수 없습니다. `system:masters`는 RBAC·웹훅 인가를 우회하는 특별한 그룹이므로 일반 관리자 배정에 사용하지 않습니다. 역할 바인딩만 지워 이 그룹의 권한을 회수할 수 있다고 가정하면 안 됩니다.

### 권한 부여 모범 사례

1. **최소 권한 원칙**: 필요한 최소한의 권한만 부여합니다.
2. **역할 분리**: 관리자, 개발자, 운영자 등 역할에 따라 적절한 권한을 부여합니다.
3. **네임스페이스 분리**: 팀 또는 프로젝트별로 네임스페이스를 분리하고 적절한 권한을 부여합니다.
4. **서비스 계정 분리**: 각 애플리케이션에 대해 별도의 서비스 계정을 사용합니다.
5. **정기적인 감사**: 권한 부여 정책을 정기적으로 검토하고 업데이트합니다.

## 어드미션 컨트롤(Admission Control)

어드미션 컨트롤은 인증 및 권한 부여 후에 요청을 처리하기 전에 추가 검증 및 수정을 수행합니다.

생성·수정·삭제와 일부 연결 요청이 대상이며 **get/list/watch 읽기는 어드미션을 거치지 않습니다**. 변경 단계가 검증 단계보다 먼저이고 둘 다 요청을 거부할 수 있습니다.

### 어드미션 컨트롤러 유형

1. **변경 어드미션 컨트롤러**: 요청을 수정할 수 있습니다.
2. **검증 어드미션 컨트롤러**: 요청을 검증만 하고 수정하지 않습니다.

### 주요 어드미션 컨트롤러

1. **LimitRanger**: LimitRange에 정의된 기본값과 최소·최대 등 제약을 적용합니다.
2. **ResourceQuota**: 설정된 네임스페이스 객체 수·요청량 등의 할당량을 검사합니다. 실제 CPU/메모리 사용량이나 비용 상한은 아닙니다.
3. **PodSecurity**: 네임스페이스 레이블에 따른 Pod Security Standards를 적용합니다. 이전 PodSecurityPolicy는 Kubernetes 1.25에서 제거되었습니다.
4. **ServiceAccount**: 파드에 서비스 계정을 자동으로 할당합니다.
5. **DefaultStorageClass**: 클래스가 지정되지 않은 PVC에 기본 StorageClass를 선택합니다. StorageClass 자체를 생성하지 않습니다.

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
  namespaceSelector:
    matchLabels:
      training.example.com/pod-policy: "enabled"
  failurePolicy: Fail
  matchPolicy: Equivalent
  admissionReviewVersions: ["v1"]
  sideEffects: None
  timeoutSeconds: 5
```

이 웹훅은 명시적으로 레이블을 붙인 네임스페이스만 대상으로 합니다. 실제 HTTPS 서버·CA와 AdmissionReview의 UID를 보존하는 응답 구현 없이 적용하지 않습니다. `failurePolicy: Fail`은 연결 오류/시간 초과 시 일치하는 요청을 막습니다. `Ignore`는 호출 실패를 무시하는 설정이지 웹훅이 정상 반환한 거부를 허용으로 바꾸는 설정이 아닙니다. 신규 정책은 테스트 네임스페이스에서 가용성·복구 절차를 확인합니다. 검증 정책은 CEL ValidatingAdmissionPolicy로 구현할 수도 있습니다.

## 실제 구현 예시

### EKS에서의 인증 및 권한 부여 구성

#### IAM과 RBAC 통합

현재 EKS IAM 사용자 접근은 **access entry**를 사용합니다. IAM 역할은 인증 신원이고, Kubernetes 권한은 연결된 EKS access policy 또는 RBAC가 부여합니다. 두 경로의 허용 권한은 누적되며 access policy는 IAM 정책이 아닙니다.

다음은 기존 클러스터·IAM 역할에 대한 관리자용 변경 예시입니다. 먼저 대상 계정·리전·클러스터와 `API` 또는 `API_AND_CONFIG_MAP` 모드, `development` 네임스페이스, 중복되지 않는 access entry, `eks:CreateAccessEntry`와 RBAC 변경 권한을 확인합니다. 아래는 리소스 생성 스크립트나 전체 마이그레이션 절차가 아닙니다.

```bash
# Example inputs: replace with the approved cluster and existing IAM role.
region=ap-northeast-2
cluster_name=my-cluster
principal_arn=arn:aws:iam::123456789012:role/EKSDeveloperRole
aws eks describe-cluster --region "$region" --name "$cluster_name" \
  --query 'cluster.accessConfig.authenticationMode' --output text

# Mutates access configuration; run only after the prerequisites above.
aws eks create-access-entry --region "$region" --cluster-name "$cluster_name" \
  --principal-arn "$principal_arn" --type STANDARD \
  --kubernetes-groups eks:developers
```

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-pod-reader
  namespace: development
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: eks-developer-pod-reader
  namespace: development
subjects:
- kind: Group
  name: eks:developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: developer-pod-reader
  apiGroup: rbac.authorization.k8s.io
```

RBAC 객체를 적용한 뒤 역할의 실제 자격 증명으로 접근을 확인합니다. 위 예제는 access policy를 연결하지 않으며, access entry 생성만으로 RBAC 객체가 만들어지지 않습니다. 기존 바인딩이나 연결된 정책이 있다면 최종 권한은 위 Pod 읽기보다 넓을 수 있습니다. 전파에는 지연이 있을 수 있습니다.

기존 `aws-auth` ConfigMap은 레거시 방식입니다. 전체 ConfigMap을 덮어쓰면 노드/Fargate 매핑 등을 잃을 수 있습니다. 전환은 `CONFIG_MAP` → `API_AND_CONFIG_MAP`에서 매핑을 옮기고 검증한 뒤 `API`로 진행하는 순서로 계획합니다. API 접근을 켠 뒤 이를 제거하는 모드로 돌아갈 수 없고, `API`에서는 ConfigMap 모드로 되돌릴 수 없습니다. 두 모드를 사용하는 동안 같은 IAM principal은 access entry가 우선하며 모든 기존 매핑이 자동 이관되는 것은 아닙니다.

`kubectl auth can-i --list`에는 EKS access policy의 권한이 표시되지 않습니다. `--as`/`--as-group` 가장은 Kubernetes RBAC 평가를 강제하므로 IAM 역할의 access policy 권한까지 검증하지 않습니다. 실제 역할로 개별 동작을 확인하고 네임스페이스 밖·Secret 읽기 같은 거부 사례도 확인해야 합니다.

#### OIDC 제공자 구성

다음 세 경로는 방향과 목적이 다릅니다.

| 경로 | 인증 대상과 구성 |
|---|---|
| 외부 OIDC 사용자 → Kubernetes API | EKS `AssociateIdentityProviderConfig`로 외부 IdP를 연결하고 사용자·그룹에 RBAC를 바인딩합니다. issuer는 EKS에서 공개 HTTPS로 접근 가능해야 하며 자체 서명 인증서는 지원하지 않습니다. IAM 인증을 끄는 기능은 아닙니다. |
| Pod → AWS API, IRSA | 클러스터의 ServiceAccount OIDC issuer를 IAM이 신뢰하도록 연결하고, 특정 네임스페이스/ServiceAccount의 역할 trust 및 필요한 AWS 리소스만 허용합니다. `eksctl utils associate-iam-oidc-provider`는 이 경로에 해당하며 외부 사용자 로그인 구성이 아닙니다. |
| Pod → AWS API, EKS Pod Identity | 지원되는 실행 환경에서 Pod Identity Agent와 역할 association을 사용합니다. IRSA의 IAM OIDC provider 생성 절차와 다릅니다. |

어느 워크로드 방식도 그 자체로 Kubernetes API RBAC를 부여하지 않습니다. AWS 권한 예제로 계정 전체 S3 읽기 관리형 정책을 기본 부여하지 말고 실제 bucket/object ARN 범위로 설계합니다. 자세한 설정은 [EKS 외부 OIDC](https://docs.aws.amazon.com/eks/latest/userguide/authenticate-oidc-identity-provider.html)와 [워크로드 IAM 역할](https://docs.aws.amazon.com/eks/latest/userguide/service-accounts.html)을 따릅니다.

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
  policyTypes: [Ingress]
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          tenant: a
```

위 정책은 `tenant: a` 레이블이 있는 **모든** 네임스페이스에서의 ingress를 허용합니다. 다른 ingress 정책이 추가 허용할 수 있고 egress는 제한하지 않습니다. CNI의 NetworkPolicy 지원이 필요하며 네임스페이스 레이블과 정책 변경 권한은 신뢰할 수 있는 관리자만 가져야 합니다. 강한 적대적 테넌트 격리를 네임스페이스 하나로 보장하지 않습니다. 양방향 기본 거부 예제는 퀴즈에 있으며 DNS·필수 통신 허용 정책을 별도 검토해야 합니다.

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
5. **감사 로깅 활성화**: API 서버 감사 정책에 따른 기록 범위와 민감 데이터 제외·보존 기간·접근 권한을 확인합니다. EKS에서는 제어 영역 로그의 `audit` 유형을 켜고 CloudWatch 전달을 검증합니다. 모든 요청 본문이 기록된다고 가정하지 않습니다.
6. **보안 컨텍스트 설정**: 파드 및 컨테이너의 보안 컨텍스트를 적절히 구성합니다.
7. **이미지 스캐닝**: 컨테이너 이미지의 취약점을 정기적으로 스캔합니다.

## 결론

Kubernetes의 인증 및 권한 부여 시스템은 클러스터 보안의 핵심 요소입니다. 적절한 인증 방법을 선택하고, RBAC를 통해 세밀한 권한 제어를 구현하며, 어드미션 컨트롤러를 활용하여 추가적인 보안 정책을 적용함으로써 안전한 Kubernetes 환경을 구축할 수 있습니다.

인증, 권한 부여, 어드미션 컨트롤은 서로 보완적인 역할을 하며, 이들을 함께 사용하여 심층 방어(Defense in Depth) 전략을 구현하는 것이 중요합니다.

## 공식 참고 자료

- [Kubernetes authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/)
- [Kubernetes authorization](https://kubernetes.io/docs/reference/access-authn-authz/authorization/)
- [RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [ServiceAccount configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/)
- [ABAC](https://kubernetes.io/docs/reference/access-authn-authz/abac/)
- [Node authorization](https://kubernetes.io/docs/reference/access-authn-authz/node/)
- [Admission controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
- [Admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
- [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [EKS certificate signing](https://docs.aws.amazon.com/eks/latest/userguide/cert-signing.html)
- [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html)
- [EKS authentication modes](https://docs.aws.amazon.com/eks/latest/userguide/setting-up-access-entries.html)
- [EKS access policy evaluation](https://docs.aws.amazon.com/eks/latest/userguide/access-policies.html)
- [EKS audit logs](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [Trusted kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
