# ArgoCD 보안

> **지원 버전**: ArgoCD v2.9+
> **마지막 업데이트**: 2026년 2월 22일

## 목차

- [SSO 통합](#sso-통합)
- [시크릿 관리](#시크릿-관리)
- [TLS 구성](#tls-구성)
- [감사 로깅](#감사-로깅)
- [네트워크 보안](#네트워크-보안)
- [저장소 자격 증명](#저장소-자격-증명)
- [GPG 서명 검증](#gpg-서명-검증)

## SSO 통합

ArgoCD는 Dex를 통해 다양한 SSO 제공자와 통합할 수 있습니다.

### OIDC (OpenID Connect)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  oidc.config: |
    name: Okta
    issuer: https://myorg.okta.com
    clientID: 0oaxxxxxxxxxx
    clientSecret: $oidc.okta.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
    requestedIDTokenClaims:
      groups:
        essential: true
---
apiVersion: v1
kind: Secret
metadata:
  name: argocd-secret
  namespace: argocd
type: Opaque
stringData:
  oidc.okta.clientSecret: your-client-secret
```

### SAML

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  dex.config: |
    connectors:
      - type: saml
        id: okta
        name: Okta SAML
        config:
          ssoURL: https://myorg.okta.com/app/xxx/sso/saml
          caData: |
            -----BEGIN CERTIFICATE-----
            MIIDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            -----END CERTIFICATE-----
          redirectURI: https://argocd.example.com/api/dex/callback
          usernameAttr: email
          emailAttr: email
          groupsAttr: groups
          # 어설션 암호화 (선택)
          # entityIssuer: https://argocd.example.com/api/dex/callback
```

### LDAP / Active Directory

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  dex.config: |
    connectors:
      - type: ldap
        id: ldap
        name: LDAP
        config:
          host: ldap.example.com:636
          insecureNoSSL: false
          insecureSkipVerify: false
          rootCA: /etc/dex/ldap-ca.crt
          bindDN: cn=admin,dc=example,dc=com
          bindPW: $dex.ldap.bindPW
          usernamePrompt: Username
          userSearch:
            baseDN: ou=users,dc=example,dc=com
            filter: "(objectClass=person)"
            username: uid
            idAttr: uid
            emailAttr: mail
            nameAttr: cn
          groupSearch:
            baseDN: ou=groups,dc=example,dc=com
            filter: "(objectClass=groupOfNames)"
            userMatchers:
              - userAttr: DN
                groupAttr: member
            nameAttr: cn
```

### Azure AD

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  oidc.config: |
    name: Azure AD
    issuer: https://login.microsoftonline.com/TENANT_ID/v2.0
    clientID: APPLICATION_ID
    clientSecret: $oidc.azure.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
    requestedIDTokenClaims:
      groups:
        essential: true
    # 그룹 필터링 (선택)
    # groupsClaim: groups
```

### AWS IAM Identity Center (SSO)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  oidc.config: |
    name: AWS IAM Identity Center
    issuer: https://identitycenter.amazonaws.com/ssoins-xxxxxxxx
    clientID: your-client-id
    clientSecret: $oidc.aws.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
    requestedIDTokenClaims:
      groups:
        essential: true
```

### admin 계정 비활성화

SSO 설정 후 로컬 admin 계정을 비활성화합니다:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  admin.enabled: "false"
```

## 시크릿 관리

Git 저장소에 시크릿을 안전하게 저장하는 방법입니다.

### Sealed Secrets

Bitnami Sealed Secrets를 사용하면 암호화된 시크릿을 Git에 저장할 수 있습니다:

**설치:**

```bash
# Sealed Secrets 컨트롤러 설치
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets -n kube-system

# kubeseal CLI 설치
brew install kubeseal  # macOS
```

**사용:**

```bash
# 일반 Secret 생성
kubectl create secret generic my-secret \
  --from-literal=password=supersecret \
  --dry-run=client -o yaml > secret.yaml

# Sealed Secret으로 변환
kubeseal --format yaml < secret.yaml > sealed-secret.yaml

# Git에 커밋
git add sealed-secret.yaml
git commit -m "Add sealed secret"
```

**Sealed Secret 예시:**

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: my-secret
  namespace: production
spec:
  encryptedData:
    password: AgBy8hCM8FayQFfixS...encrypted...
  template:
    metadata:
      name: my-secret
      namespace: production
    type: Opaque
```

### External Secrets Operator

외부 시크릿 관리 시스템과 통합합니다:

**설치:**

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace
```

**AWS Secrets Manager 연동:**

```yaml
# SecretStore 정의
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: ap-northeast-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
# ExternalSecret 정의
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: production/database
        property: username
    - secretKey: password
      remoteRef:
        key: production/database
        property: password
```

### HashiCorp Vault

**Argocd Vault Plugin (AVP) 사용:**

```yaml
# Repo Server에 AVP 설치
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-repo-server
  namespace: argocd
spec:
  template:
    spec:
      containers:
        - name: argocd-repo-server
          volumeMounts:
            - name: custom-tools
              mountPath: /usr/local/bin/argocd-vault-plugin
              subPath: argocd-vault-plugin
          env:
            - name: AVP_TYPE
              value: vault
            - name: AVP_AUTH_TYPE
              value: k8s
            - name: VAULT_ADDR
              value: https://vault.example.com
      initContainers:
        - name: download-tools
          image: alpine:3.18
          command:
            - sh
            - -c
            - |
              wget -O /custom-tools/argocd-vault-plugin \
                https://github.com/argoproj-labs/argocd-vault-plugin/releases/download/v1.17.0/argocd-vault-plugin_1.17.0_linux_amd64
              chmod +x /custom-tools/argocd-vault-plugin
          volumeMounts:
            - name: custom-tools
              mountPath: /custom-tools
      volumes:
        - name: custom-tools
          emptyDir: {}
```

**AVP 사용 예시:**

```yaml
# AVP 플레이스홀더가 포함된 매니페스트
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  annotations:
    avp.kubernetes.io/path: "secret/data/production/database"
type: Opaque
stringData:
  username: <username>
  password: <password>
```

**Application에서 AVP 플러그인 사용:**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/myorg/myapp.git
    targetRevision: main
    path: manifests
    plugin:
      name: argocd-vault-plugin
  destination:
    server: https://kubernetes.default.svc
    namespace: production
```

### SOPS (Secrets OPerationS)

**SOPS 암호화 파일 사용:**

```yaml
# .sops.yaml (저장소 루트)
creation_rules:
  - path_regex: .*\.enc\.yaml$
    kms: arn:aws:kms:ap-northeast-2:123456789012:key/xxx
    # 또는 age
    # age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```bash
# 암호화
sops -e secret.yaml > secret.enc.yaml

# 복호화 (ArgoCD에서 자동)
sops -d secret.enc.yaml
```

**KSOPS (Kustomize + SOPS):**

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

generators:
  - secret-generator.yaml
---
# secret-generator.yaml
apiVersion: viaduct.ai/v1
kind: ksops
metadata:
  name: secret-generator
files:
  - secrets/db-secret.enc.yaml
```

## TLS 구성

### 자체 서명 인증서

```bash
# 인증서 생성
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout argocd.key -out argocd.crt \
  -subj "/CN=argocd.example.com"

# Secret 생성
kubectl create secret tls argocd-server-tls \
  --cert=argocd.crt \
  --key=argocd.key \
  -n argocd
```

### Let's Encrypt (cert-manager)

```yaml
# ClusterIssuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
---
# Certificate
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: argocd-server-tls
  namespace: argocd
spec:
  secretName: argocd-server-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - argocd.example.com
```

### Ingress TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-server
  namespace: argocd
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - argocd.example.com
      secretName: argocd-server-tls
  rules:
    - host: argocd.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: argocd-server
                port:
                  number: 443
```

## 감사 로깅

### 감사 로그 활성화

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # 감사 로그 레벨
  server.audit.enabled: "true"
```

### 로그 형식

ArgoCD는 JSON 형식으로 감사 로그를 출력합니다:

```json
{
  "level": "info",
  "action": "sync",
  "application": "my-app",
  "user": "admin@example.com",
  "timestamp": "2025-02-21T10:30:00Z",
  "message": "Application sync initiated"
}
```

### CloudWatch Logs 연동 (EKS)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-server
  namespace: argocd
spec:
  template:
    metadata:
      annotations:
        fluentbit.io/parser: json
    spec:
      containers:
        - name: argocd-server
          # 로그는 stdout으로 출력
```

**Fluent Bit ConfigMap:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: amazon-cloudwatch
data:
  fluent-bit.conf: |
    [INPUT]
        Name              tail
        Tag               argocd.*
        Path              /var/log/containers/argocd-server*.log
        Parser            docker
        DB                /var/log/flb_argocd.db
        Mem_Buf_Limit     5MB
        Skip_Long_Lines   On
        Refresh_Interval  10

    [OUTPUT]
        Name              cloudwatch
        Match             argocd.*
        region            ap-northeast-2
        log_group_name    /aws/eks/argocd
        log_stream_prefix audit-
        auto_create_group true
```

## 네트워크 보안

### NetworkPolicy

```yaml
# ArgoCD 컴포넌트 간 통신만 허용
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-server
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Ingress Controller에서 접근
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 8083
  egress:
    # Repo Server 접근
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-repo-server
      ports:
        - protocol: TCP
          port: 8081
    # Redis 접근
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-redis
      ports:
        - protocol: TCP
          port: 6379
    # Dex 접근
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-dex-server
      ports:
        - protocol: TCP
          port: 5556
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
    # Kubernetes API
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
---
# Repo Server NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-repo-server
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-repo-server
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-server
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-application-controller
      ports:
        - protocol: TCP
          port: 8081
  egress:
    # Git 저장소 접근 (HTTPS)
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
        - protocol: TCP
          port: 22
    # Redis 접근
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-redis
      ports:
        - protocol: TCP
          port: 6379
```

## 저장소 자격 증명

### HTTPS (사용자명/비밀번호)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg/myrepo.git
  username: git
  password: ghp_xxxxxxxxxxxxxxxxxxxx  # Personal Access Token
```

### SSH 키

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-ssh
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: git@github.com:myorg/myrepo.git
  sshPrivateKey: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
    ...
    -----END OPENSSH PRIVATE KEY-----
```

### GitHub Apps

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github-app
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg
  githubAppID: "123456"
  githubAppInstallationID: "12345678"
  githubAppPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    MIIEowIBAAKCAQEA...
    -----END RSA PRIVATE KEY-----
```

### 자격 증명 템플릿

여러 저장소에 동일한 자격 증명을 사용할 때:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: creds-template-github
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds  # repository가 아닌 repo-creds
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg  # 패턴 매칭
  username: git
  password: ghp_xxxxxxxxxxxxxxxxxxxx
```

## GPG 서명 검증

### GPG 키 등록

```bash
# 공개 키 내보내기
gpg --armor --export KEY_ID > public-key.asc

# ArgoCD에 키 등록
argocd gpg add --from public-key.asc

# 또는 선언적으로
kubectl create secret generic argocd-gpg-keys-secret \
  --from-file=public-key.asc \
  -n argocd
```

### 프로젝트에서 서명 검증 활성화

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: production
  namespace: argocd
spec:
  description: Production with GPG verification

  sourceRepos:
    - 'https://github.com/myorg/production-*'

  destinations:
    - namespace: 'prod-*'
      server: https://prod-cluster.example.com

  # 서명 검증 필수
  signatureKeys:
    - keyID: 4AEE18F83AFDEB23  # GPG 키 ID
    - keyID: ABCD1234EFGH5678

  # GPG 키 목록
  sourceNamespaces:
    - argocd
```

### 커밋 서명

```bash
# Git 커밋 서명 설정
git config --global user.signingkey KEY_ID
git config --global commit.gpgsign true

# 서명된 커밋
git commit -S -m "Signed commit message"

# 서명 확인
git log --show-signature
```

## 다음 단계

1. **[알림](08-notifications.md)**: 보안 이벤트에 대한 알림을 구성하세요.

2. **[모범 사례](09-best-practices.md)**: 보안 모범 사례를 학습하세요.

3. **[프로젝트와 RBAC](06-projects-rbac.md)**: RBAC과 함께 보안을 강화하세요.

## 참고 자료

- [ArgoCD 보안 문서](https://argo-cd.readthedocs.io/en/stable/operator-manual/security/)
- [SSO 구성](https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/)
- [시크릿 관리](https://argo-cd.readthedocs.io/en/stable/operator-manual/secret-management/)
- [GPG 서명](https://argo-cd.readthedocs.io/en/stable/user-guide/gpg-verification/)

## 퀴즈

이 장에서 배운 내용을 테스트하려면 [보안 퀴즈](../../quizzes/gitops/argocd/07-security-quiz.md)를 풀어보세요.
