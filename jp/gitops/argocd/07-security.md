# ArgoCD セキュリティ

> **対応バージョン**: ArgoCD v2.9+
> **最終更新**: February 22, 2026

## 目次
- [SSO 統合](#sso-integration)
- [Secret 管理](#secret-management)
- [TLS 設定](#tls-configuration)
- [監査ログ](#audit-logging)
- [ネットワークセキュリティ](#network-security)
- [リポジトリ認証情報](#repository-credentials)
- [GPG 署名検証](#gpg-signature-verification)

## SSO 統合

ArgoCD は認証のために複数の SSO プロバイダーをサポートしています。

### OIDC 設定

`argocd-cm` の汎用 OIDC 設定:

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

クライアント Secret を保存します:

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

### Okta 統合

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

Okta Application の設定:
1. Okta で新しい OIDC Application を作成します
2. サインインリダイレクト URI を設定します: `https://argocd.example.com/api/dex/callback`
3. "groups" スコープを有効にします
4. ID token に groups claim を追加します

### Azure AD 統合

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

Azure AD の設定:
1. Azure AD で新しい Application を登録します
2. リダイレクト URI を設定します: `https://argocd.example.com/api/dex/callback`
3. API permissions を追加します: `openid`, `profile`, `email`
4. Token configuration で groups claim を設定します

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

### Dex LDAP 統合

LDAP/Active Directory には、ID ブローカーとして Dex を使用します:

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

### SAML 統合

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

### SSO グループを RBAC にマッピングする

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

Secret を暗号化して Git に安全に保存します:

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

外部プロバイダーから Secret を同期します:

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

Secret を manifests に直接挿入します:

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

manifests で使用します:

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

age、GPG、またはクラウド KMS で Secret を暗号化します:

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

復号するよう ArgoCD を設定します:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  kustomize.buildOptions: --enable-alpha-plugins
```

## TLS 設定

### カスタム TLS 証明書

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

### cert-manager 統合

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

### リポジトリサーバー向け TLS

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

## 監査ログ

### 監査ログを有効にする

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

### 監査ログの形式

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

### ログを外部システムへ転送する

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

## ネットワークセキュリティ

### NetworkPolicy

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

## リポジトリ認証情報

### Personal Access Token を使用する HTTPS

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

### SSH キー認証

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

### GitHub App 認証

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

### Helm リポジトリ認証情報

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

## GPG 署名検証

commit が信頼できるキーによって署名されていることを検証します。

### GPG キーを設定する

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

### 署名検証を有効にする

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

### 署名検証を使用する Application

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

署名検証が有効な場合、ArgoCD は次を実行します:
1. commit が署名されているか確認します
2. 設定済みのキーに対して署名を検証します
3. 検証に失敗した場合は sync を拒否します

## クイズ

学習内容を確認するには、[ArgoCD セキュリティクイズ](../../quizzes/gitops/argocd/07-security-quiz.md)に挑戦してください。
