# ArgoCD 安全

> **支持的版本**: ArgoCD v2.9+
> **最后更新**: February 22, 2026

## 目录
- [SSO 集成](#sso-integration)
- [Secret 管理](#secret-management)
- [TLS 配置](#tls-configuration)
- [审计日志](#audit-logging)
- [网络安全](#network-security)
- [仓库凭证](#repository-credentials)
- [GPG 签名验证](#gpg-signature-verification)

## SSO 集成

ArgoCD 支持多个用于身份验证的 SSO 提供商。

### OIDC 配置

`argocd-cm` 中的通用 OIDC 配置：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com

  oidc.config: |
    name: OIDC
    issuer: https://auth.example.com
    clientID: argocd
    clientSecret: $oidc.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
    requestedIDTokenClaims:
      groups:
        essential: true
```

存储客户端 Secret：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-secret
  namespace: argocd
type: Opaque
stringData:
  oidc.clientSecret: <your-client-secret>
```

### Okta 集成

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
    issuer: https://dev-123456.okta.com
    clientID: 0oa1234567890abcdef
    clientSecret: $oidc.okta.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
    requestedIDTokenClaims:
      groups:
        essential: true
```

Okta 应用程序配置：
1. 在 Okta 中创建新的 OIDC 应用程序
2. 设置登录重定向 URI：`https://argocd.example.com/api/dex/callback`
3. 启用“groups”scope
4. 将 groups claim 添加到 ID token

### Azure AD 集成

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
    issuer: https://login.microsoftonline.com/<tenant-id>/v2.0
    clientID: <application-id>
    clientSecret: $oidc.azure.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
    requestedIDTokenClaims:
      groups:
        essential: true
    # For Azure AD groups, use the groups claim
    # Configure in Azure: Token configuration > Add groups claim
```

Azure AD 配置：
1. 在 Azure AD 中注册新的应用程序
2. 设置重定向 URI：`https://argocd.example.com/api/dex/callback`
3. 添加 API 权限：`openid`、`profile`、`email`
4. 在 Token 配置中配置 groups claim

### AWS IAM Identity Center (AWS SSO)

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
    issuer: https://identitycenter.amazonaws.com/ssoins-1234567890abcdef
    clientID: <client-id>
    clientSecret: $oidc.aws.clientSecret
    requestedScopes:
      - openid
      - profile
      - email
    requestedIDTokenClaims:
      groups:
        essential: true
```

### Dex LDAP 集成

对于 LDAP/Active Directory，请使用 Dex 作为身份代理：

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
        name: Active Directory
        id: ad
        config:
          host: ldap.example.com:636
          insecureNoSSL: false
          insecureSkipVerify: false
          rootCAData: |
            -----BEGIN CERTIFICATE-----
            ...
            -----END CERTIFICATE-----

          bindDN: cn=argocd,ou=Service Accounts,dc=example,dc=com
          bindPW: $dex.ldap.bindPW

          usernamePrompt: Username

          userSearch:
            baseDN: ou=Users,dc=example,dc=com
            filter: "(objectClass=person)"
            username: sAMAccountName
            idAttr: sAMAccountName
            emailAttr: mail
            nameAttr: displayName

          groupSearch:
            baseDN: ou=Groups,dc=example,dc=com
            filter: "(objectClass=group)"
            userMatchers:
              - userAttr: DN
                groupAttr: member
            nameAttr: cn
```

### SAML 集成

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
        id: saml
        name: SAML Provider
        config:
          ssoURL: https://idp.example.com/sso/saml
          caData: |
            -----BEGIN CERTIFICATE-----
            ...
            -----END CERTIFICATE-----
          redirectURI: https://argocd.example.com/api/dex/callback
          usernameAttr: name
          emailAttr: email
          groupsAttr: groups
          entityIssuer: https://argocd.example.com/api/dex/callback
```

### 将 SSO 组映射到 RBAC

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.csv: |
    # Map SSO groups to ArgoCD roles
    g, ArgoCD-Admins, role:admin
    g, ArgoCD-Developers, role:developer
    g, ArgoCD-Viewers, role:readonly

    # Azure AD group IDs
    g, 12345678-1234-1234-1234-123456789012, role:admin

    # Okta groups
    g, argocd-admins, role:admin
```

## Secret 管理

### Sealed Secrets

加密 Secret 以便安全地存储在 Git 中：

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Install kubeseal CLI
brew install kubeseal

# Seal a secret
kubectl create secret generic my-secret \
  --from-literal=password=secret123 \
  --dry-run=client -o yaml | \
  kubeseal --format yaml > sealed-secret.yaml
```

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: my-secret
  namespace: my-app
spec:
  encryptedData:
    password: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEq...
```

### External Secrets Operator

从外部提供商同步 Secret：

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace
```

#### AWS Secrets Manager

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets
  namespace: my-app
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: my-app-secrets
  namespace: my-app
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets
    kind: SecretStore
  target:
    name: my-app-secrets
    creationPolicy: Owner
  data:
    - secretKey: database-password
      remoteRef:
        key: myapp/production
        property: database-password
    - secretKey: api-key
      remoteRef:
        key: myapp/production
        property: api-key
```

#### HashiCorp Vault

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault
  namespace: my-app
spec:
  provider:
    vault:
      server: https://vault.example.com
      path: secret
      version: v2
      auth:
        kubernetes:
          mountPath: kubernetes
          role: external-secrets
          serviceAccountRef:
            name: external-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: vault-secrets
  namespace: my-app
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: SecretStore
  target:
    name: app-secrets
  data:
    - secretKey: password
      remoteRef:
        key: myapp/config
        property: password
```

### ArgoCD Vault Plugin (AVP)

将 Secret 直接注入 manifests：

```bash
# Install AVP as ArgoCD plugin
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: cmp-plugin
  namespace: argocd
data:
  avp.yaml: |
    apiVersion: argoproj.io/v1alpha1
    kind: ConfigManagementPlugin
    metadata:
      name: argocd-vault-plugin
    spec:
      allowConcurrency: true
      discover:
        find:
          command:
            - sh
            - "-c"
            - "find . -name '*.yaml' | xargs -I {} grep \"<path\\|avp\\.kubernetes\\.io\" {} | grep ."
      generate:
        command:
          - argocd-vault-plugin
          - generate
          - "."
      lockRepo: false
EOF
```

在 manifests 中使用：

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  annotations:
    avp.kubernetes.io/path: "secret/data/myapp"
type: Opaque
stringData:
  password: <password>
  api-key: <api-key>
```

### SOPS (Secrets OPerationS)

使用 age、GPG 或云 KMS 加密 Secret：

```bash
# Install SOPS
brew install sops

# Create .sops.yaml configuration
cat > .sops.yaml <<EOF
creation_rules:
  - path_regex: .*secrets.*\.yaml$
    kms: arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012
EOF

# Encrypt a secret file
sops -e secrets.yaml > secrets.enc.yaml
```

配置 ArgoCD 进行解密：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  kustomize.buildOptions: --enable-alpha-plugins
```

## TLS 配置

### 自定义 TLS 证书

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: argocd-server-tls
  namespace: argocd
type: kubernetes.io/tls
stringData:
  tls.crt: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
  tls.key: |
    -----BEGIN PRIVATE KEY-----
    ...
    -----END PRIVATE KEY-----
```

### cert-manager 集成

```yaml
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
  privateKey:
    algorithm: RSA
    size: 2048
```

### 用于 Repository Server 的 TLS

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-tls-certs-cm
  namespace: argocd
data:
  # Add custom CA certificates for private Git servers
  git.example.com: |
    -----BEGIN CERTIFICATE-----
    ...
    -----END CERTIFICATE-----
```

## 审计日志

### 启用审计日志

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  # API server audit logging
  server.audit.enabled: "true"
  server.audit.path: "/var/log/argocd/audit.log"

  # Application controller logging
  controller.log.format: json
  controller.log.level: info
```

### 审计日志格式

```json
{
  "level": "info",
  "time": "2024-01-15T10:30:00Z",
  "msg": "sync operation completed",
  "application": "my-app",
  "project": "default",
  "user": "admin@example.com",
  "action": "sync",
  "result": "success",
  "revision": "abc1234",
  "destination": {
    "server": "https://kubernetes.default.svc",
    "namespace": "my-app"
  }
}
```

### 将日志转发到外部系统

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: argocd-server
  namespace: argocd
spec:
  template:
    spec:
      containers:
        - name: argocd-server
          volumeMounts:
            - name: audit-logs
              mountPath: /var/log/argocd
        # Sidecar for log forwarding
        - name: fluentbit
          image: fluent/fluent-bit:latest
          volumeMounts:
            - name: audit-logs
              mountPath: /var/log/argocd
            - name: fluentbit-config
              mountPath: /fluent-bit/etc/
      volumes:
        - name: audit-logs
          emptyDir: {}
        - name: fluentbit-config
          configMap:
            name: fluentbit-config
```

## 网络安全

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-server-network-policy
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from ingress controller
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
    # Allow to repo server
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-repo-server
      ports:
        - protocol: TCP
          port: 8081
    # Allow to Redis
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: argocd-redis
      ports:
        - protocol: TCP
          port: 6379
    # Allow to Kubernetes API
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-repo-server-network-policy
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
    # Allow to Git servers
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
        - protocol: TCP
          port: 22
```

### Pod Security Standards

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: argocd
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

## 仓库凭证

### 使用 Personal Access Token 的 HTTPS

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg
  password: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  username: git
```

### SSH 密钥身份验证

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: private-repo-ssh
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: git
  url: git@github.com:myorg/private-repo.git
  sshPrivateKey: |
    -----BEGIN OPENSSH PRIVATE KEY-----
    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
    ...
    -----END OPENSSH PRIVATE KEY-----
```

### GitHub App 身份验证

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: repo-creds-github-app
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repo-creds
type: Opaque
stringData:
  type: git
  url: https://github.com/myorg
  githubAppID: "123456"
  githubAppInstallationID: "12345678"
  githubAppPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
```

### Helm 仓库凭证

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: helm-repo-creds
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  name: private-charts
  url: https://charts.example.com
  username: admin
  password: secretpassword
```

## GPG 签名验证

验证提交是否由受信任的密钥签名。

### 配置 GPG 密钥

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-gpg-keys-cm
  namespace: argocd
data:
  # Add GPG public keys
  developer1.asc: |
    -----BEGIN PGP PUBLIC KEY BLOCK-----
    ...
    -----END PGP PUBLIC KEY BLOCK-----
  developer2.asc: |
    -----BEGIN PGP PUBLIC KEY BLOCK-----
    ...
    -----END PGP PUBLIC KEY BLOCK-----
```

### 启用签名验证

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: secure-project
  namespace: argocd
spec:
  signatureKeys:
    - keyID: ABC123DEF456
    - keyID: DEF456GHI789
  sourceRepos:
    - https://github.com/myorg/secure-repo
```

### 使用签名验证的 Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: verified-app
  namespace: argocd
spec:
  project: secure-project
  source:
    repoURL: https://github.com/myorg/secure-repo
    targetRevision: HEAD
    path: manifests
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
```

启用签名验证后，ArgoCD 将：
1. 检查提交是否已签名
2. 根据已配置的密钥验证签名
3. 如果验证失败，则拒绝同步

## 测验

要测试你所学的内容，请尝试[ArgoCD 安全测验](../../quizzes/gitops/argocd/07-security-quiz.md)。
