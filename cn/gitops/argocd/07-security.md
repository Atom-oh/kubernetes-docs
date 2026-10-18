# ArgoCD 安全

> **审查版本**：Argo CD 3.5.2、Sealed Secrets 0.40.0/chart 2.20.0、ESO 2.10.0（根据发行说明审查后更新至 2.12.0；未重新运行示例）、AVP 1.18.1、KSOPS 4.5.1、SOPS 3.13.3
> **最后更新**：October 16, 2026

## 目录
- [SSO 集成](#sso-integration)
- [Secret 管理](#secret-management)
- [TLS 配置](#tls-configuration)
- [审计日志](#audit-logging)
- [网络安全](#network-security)
- [仓库凭证](#repository-credentials)
- [GPG 签名验证](#gpg-signature-verification)

## SSO 集成 {#sso-integration}

SSO 示例互为替代方案：将必需字段合并到现有 ConfigMap/Secret 中，不要替换 argocd-secret 中的服务器签名密钥或其他凭证。将占位符替换为实际的 IdP 设置，并通过外部 Secret 管理系统或受保护的文件提供 Secret。下面的 Secret YAML 仅用于说明结构；不要将其中的明文值提交到仓库。

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

Okta 应用配置：
1. 在 Okta 中创建新的 OIDC 应用
2. 设置登录重定向 URI：`https://argocd.example.com/auth/callback`
3. 启用 "groups" 范围
4. 将 groups 声明添加到 ID token

### Microsoft Entra ID 集成

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  oidc.config: |
    name: Microsoft Entra ID
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
```

Microsoft Entra ID 配置：
1. 在 Azure AD 中注册新的应用
2. 设置重定向 URI：`https://argocd.example.com/auth/callback`
3. 添加 API 权限：`openid`、`profile`、`email`
4. 在 Token 配置中配置 groups 声明

### AWS IAM Identity Center（AWS SSO）

创建 IAM Identity Center 自定义 SAML 应用，分配访问权限，并为 /api/dex/callback 配置 ACS/受众。虚构的 identitycenter.amazonaws.com issuer 并不是通用 OIDC 集成。映射 email 属性，并使用元数据中的登录 URL/签名证书。不要假定存在官方的动态 group 属性映射；应检查实际的断言。此示例使用 email 声明路径。

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
      id: identity-center
      name: AWS IAM Identity Center
      config:
        ssoURL: https://portal.sso.ap-northeast-2.amazonaws.com/saml/assertion/APP_ID
        caData: BASE64_OF_THE_COMPLETE_IDP_SIGNING_CERTIFICATE_PEM
        entityIssuer: https://argocd.example.com/api/dex/callback
        redirectURI: https://argocd.example.com/api/dex/callback
        usernameAttr: email
        emailAttr: email
```

将此 RBAC 数据片段合并到配置中，为真实且获批的 email 设置绑定，并使用 RBAC 章节中定义的受限 viewer 角色。

```yaml
data:
  scopes: '[groups, email]'
  policy.identity-center.csv: |
    g, approved.user@example.com, role:viewer
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
        bindDN: cn=argocd-reader,ou=Service Accounts,dc=example,dc=com
        bindPW: $dex.ldap.bindPW
        usernamePrompt: Username
        userSearch:
          baseDN: ou=Users,dc=example,dc=com
          filter: (objectClass=person)
          username: sAMAccountName
          idAttr: sAMAccountName
          emailAttr: mail
          nameAttr: displayName
        groupSearch:
          baseDN: ou=Groups,dc=example,dc=com
          filter: (objectClass=group)
          userMatchers:
          - userAttr: DN
            groupAttr: member
          nameAttr: cn
        rootCA: /etc/dex/ldap-ca/ca.crt
```

在 ldap-ca ConfigMap 中提供经过验证的 ca.crt，并合并以下 Helm values。通过 argocd-secret 中的 dex.ldap.bindPW 键提供 bindPW，并使用仅具备所需搜索权限的目录账户。

```yaml
dex:
  volumes:
  - name: ldap-ca
    configMap:
      name: ldap-ca
  volumeMounts:
  - name: ldap-ca
    mountPath: /etc/dex/ldap-ca
    readOnly: true
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
        caData: BASE64_OF_THE_COMPLETE_IDP_SIGNING_CERTIFICATE_PEM
        redirectURI: https://argocd.example.com/api/dex/callback
        usernameAttr: name
        emailAttr: email
        groupsAttr: groups
        entityIssuer: https://argocd.example.com/api/dex/callback
```

### 将 SSO 组映射到 RBAC

将这些绑定与 Projects/RBAC 章节中的自定义角色定义合并；developer 和 viewer 并非内置角色。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.security-sso.csv: |
    # Map SSO groups to ArgoCD roles
    g, ArgoCD-Admins, role:admin
    g, ArgoCD-Developers, role:developer
    g, ArgoCD-Viewers, role:viewer

    # Azure AD group IDs
    g, 12345678-1234-1234-1234-123456789012, role:admin

    # Okta groups
    g, argocd-admins, role:admin
  scopes: '[groups]'
```

## Secret 管理 {#secret-management}

Git Secret 清单中的 Base64 并不等于加密。新环境优先使用 ESO 或 Sealed Secrets 在目标端创建 Secret。AVP/KSOPS 在生成时注入内容可能会使明文暴露在 repo-server 和 Redis 清单缓存中；它们采用不同的信任模型。

### Sealed Secrets

此示例使用 controller 0.40.0/chart 2.20.0。旧的 bitnami-labs Helm URL 现在会返回 404；请使用 bitnami 仓库。安装匹配的 kubeseal 二进制文件，并从[官方发行版本](https://github.com/bitnami/sealed-secrets/releases/tag/v0.40.0)验证校验和。平台管理员需要预先创建目标 namespace。

```bash
helm repo add sealed-secrets https://bitnami.github.io/sealed-secrets
helm repo update sealed-secrets
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --version 2.20.0 --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller --wait --timeout 5m
kubeseal --version  # use 0.40.0 for this example
```

确认当前 kubeconfig 指向预期的集群，并获取该 controller 的公钥证书。默认的 strict 范围会将密文绑定到 Secret 名称和 namespace；密封后不要重命名或移动它。本流程从受保护的文件读取密码，而不是将其放入 Git 或命令参数中。

```bash
set -euo pipefail
umask 077
: "${SECRET_INPUT_FILE:?Provide a protected password file outside Git}"
seal_dir="$(mktemp -d)"
trap 'rm -rf "$seal_dir"' EXIT
kubeseal --controller-name sealed-secrets-controller \
  --controller-namespace kube-system --fetch-cert > "$seal_dir/controller.pem"
kubectl create secret generic my-secret --namespace my-app \
  --from-file=password="$SECRET_INPUT_FILE" --dry-run=client -o yaml \
  | kubeseal --format yaml --cert "$seal_dir/controller.pem" > sealed-secret.yaml
test -s sealed-secret.yaml
```

检查并仅提交生成的 SealedSecret。被截断的 Ag... 示例不是可用的密文。将 controller 密钥的备份/恢复作为管理员操作加以保护；密封密钥续期本身并不会轮换应用的 Secret。

### External Secrets Operator

ESO 会将外部 Secret 值同步到目标集群的 Secret 中；它不会加密 Git 中的明文。2.12.0 示例使用 external-secrets.io/v1。下面 AWS 配置中的 jwt.serviceAccountRef 使用 IRSA：请为该 namespace 配置 ServiceAccount、IAM 角色注解和 OIDC 信任。Pod Identity 使用 controller ServiceAccount 关联/SDK 凭证链，而不是此 jwt 配置。

从外部提供商同步 Secret：

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.12.0 --namespace external-secrets --create-namespace --wait --timeout 5m
```

IRSA ServiceAccount 示例：配置真实的角色 ARN/OIDC 信任，并仅允许访问所需的 Secret ARN，以执行 GetSecretValue/DescribeSecret 操作；适用时还需允许 KMS Decrypt。对于 Vault，将其角色绑定到此 SA/namespace 和 audience=vault，并配置受限的 KV 策略及适当的 reviewer。Vault 1.21+ 要求角色 audience。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: external-secrets-sa
  namespace: my-app
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/eso-my-app-reader
automountServiceAccountToken: false
```

#### AWS Secrets Manager

```yaml
apiVersion: external-secrets.io/v1
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
apiVersion: external-secrets.io/v1
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
apiVersion: external-secrets.io/v1
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
            audiences:
            - vault
---
apiVersion: external-secrets.io/v1
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

### ArgoCD Vault Plugin（AVP）

对于现有 AVP 集成，请使用 CMP sidecar，并搭配 3.5.2。将二进制文件复制到主 repo-server 中，或仅创建 ConfigMap，都不会注册插件。ConfigManagementPlugin 是 sidecar 配置文件，不是 Kubernetes CRD。生成的 Secret 值可能以明文形式存在于 Redis/repo-server 缓存中；应将其限制为受信任的仓库，并设置适当的隔离边界。

根据架构验证 AVP 1.18.1 二进制文件与其官方校验和文件，并将其放入构建上下文，命名为 argocd-vault-plugin。构建/验证此镜像，并将下面示例中的 registry 镜像替换为你发布的镜像。

```dockerfile
FROM quay.io/argoproj/argocd:v3.5.2
COPY --chmod=0755 --chown=999:999 argocd-vault-plugin /usr/local/bin/argocd-vault-plugin
USER 999
```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: avp-plugin-config
  namespace: argocd
data:
  plugin.yaml: |
    apiVersion: argoproj.io/v1alpha1
    kind: ConfigManagementPlugin
    metadata:
      name: argocd-vault-plugin
    spec:
      generate:
        command:
        - argocd-vault-plugin
        - generate
        - .
```

将这些 values 合并到 argo-cd chart 10.8.4 配置中，并保留其他 sidecar/volume 条目。chart 会提供 var-files/plugins；sidecar 使用自己的 tmp volume。

```yaml
repoServer:
  automountServiceAccountToken: false
  serviceAccount:
    create: true
    name: argocd-repo-server
  extraContainers:
  - name: avp
    image: registry.example.com/argocd-avp:3.5.2-avp1.18.1
    command:
    - /var/run/argocd/argocd-cmp-server
    securityContext:
      runAsNonRoot: true
      runAsUser: 999
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
      seccompProfile:
        type: RuntimeDefault
    env:
    - name: AVP_TYPE
      value: vault
    - name: AVP_AUTH_TYPE
      value: k8s
    - name: AVP_K8S_ROLE
      value: argocd-readonly
    - name: AVP_K8S_MOUNT_PATH
      value: auth/kubernetes
    - name: AVP_K8S_TOKEN_PATH
      value: /var/run/secrets/avp/token
    - name: VAULT_ADDR
      value: https://vault.example.com
    - name: VAULT_CACERT
      value: /etc/vault/ca.crt
    volumeMounts:
    - name: var-files
      mountPath: /var/run/argocd
    - name: plugins
      mountPath: /home/argocd/cmp-server/plugins
    - name: avp-config
      mountPath: /home/argocd/cmp-server/config/plugin.yaml
      subPath: plugin.yaml
      readOnly: true
    - name: avp-tmp
      mountPath: /tmp
    - name: avp-cache
      mountPath: /home/argocd/.avp
    - name: avp-token
      mountPath: /var/run/secrets/avp
      readOnly: true
    - name: vault-ca
      mountPath: /etc/vault
      readOnly: true
  volumes:
  - name: avp-config
    configMap:
      name: avp-plugin-config
  - name: avp-tmp
    emptyDir: {}
  - name: avp-cache
    emptyDir:
      medium: Memory
  - name: avp-token
    projected:
      sources:
      - serviceAccountToken:
          path: token
          audience: vault
          expirationSeconds: 600
  - name: vault-ca
    configMap:
      name: vault-ca
```

为 Vault 配置 argocd-readonly 角色，使其适用于 ServiceAccount argocd/argocd-repo-server，并设置 audience=vault、范围严格受限的只读策略以及合适的 token reviewer。提供包含 ca.crt 键的 vault-ca ConfigMap 和有效的 Vault TLS 证书。不要用 repo-server 的宽泛 Kubernetes 权限替代这些要求。

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
    namespace: my-app
```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
  namespace: my-app
  annotations:
    avp.kubernetes.io/path: secret/data/my-app/database
type: Opaque
stringData:
  username: <username>
  password: <password>
```

将 Application/project/repository 和 Vault KV 路径限制在预期环境内。共享的 sidecar 凭证无法在彼此不信任的项目之间提供隔离边界。

### SOPS（Secrets OPerationS）

此示例使用 SOPS 3.13.3 和 KSOPS 4.5.1。将公开的 age recipient 与其私有 identity 分开。替换示例 recipient，并确保私钥不进入 Git。

```yaml
creation_rules:
- path_regex: ^secrets/.*\.enc\.yaml$
  encrypted_regex: ^(data|stringData)$
  age: age1_REPLACE_WITH_YOUR_PUBLIC_RECIPIENT
```

```bash
set -euo pipefail
umask 077
: "${KUBERNETES_SECRET_FILE:?Provide a protected Secret YAML file outside Git}"
mkdir -p secrets
sops --encrypt --filename-override secrets/db-secret.enc.yaml \
  "$KUBERNETES_SECRET_FILE" > secrets/db-secret.enc.yaml
test -s secrets/db-secret.enc.yaml
```

creation_rules 匹配的是输入/filename-override 路径，而不是 shell 重定向目标。默认情况下，Argo CD 不会自动解密 SOPS；它需要 KSOPS 可执行文件、Kustomize alpha/exec 支持和解密凭证。

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: my-app
generators:
- secret-generator.yaml
```

```yaml
apiVersion: viaduct.ai/v1
kind: ksops
metadata:
  name: secret-generator
  annotations:
    config.kubernetes.io/function: |
      exec:
        path: ksops
files:
- secrets/db-secret.enc.yaml
```

以下 Helm values 适用于限制为受信任仓库的现有 Argo CD 实例。全局 exec 支持会信任仓库提供的执行内容；不要将其视为不可信项目之间的隔离机制。新环境优先使用目标端 Secret 管理。

```yaml
configs:
  cm:
    kustomize.buildOptions: --enable-alpha-plugins --enable-exec
repoServer:
  env:
  - name: SOPS_AGE_KEY_FILE
    value: /etc/sops-age/key.txt
  volumes:
  - name: ksops-tools
    emptyDir: {}
  - name: sops-age
    secret:
      secretName: sops-age
  initContainers:
  - name: install-ksops
    image: viaductoss/ksops:v4.5.1
    command:
    - /usr/local/bin/ksops
    - install
    - --with-kustomize
    - /custom-tools
    volumeMounts:
    - name: ksops-tools
      mountPath: /custom-tools
  volumeMounts:
  - name: ksops-tools
    mountPath: /usr/local/bin/kustomize
    subPath: kustomize
  - name: ksops-tools
    mountPath: /usr/local/bin/ksops
    subPath: ksops
  - name: sops-age
    mountPath: /etc/sops-age
    readOnly: true
```

```bash
# Create the Secret from an existing protected age identity file.
kubectl create secret generic sops-age -n argocd \
  --from-file=key.txt=./age-identity.txt
# Validate in a protected local environment; generated output contains plaintext.
umask 077
render_dir="$(mktemp -d)"
trap 'rm -rf "$render_dir"' EXIT
kustomize build --enable-alpha-plugins --enable-exec . > "$render_dir/rendered.yaml"
```

不要提交解密后的输出或私有 identity。这些插件安装方式互为替代方案；如要组合使用，必须明确合并 values 数组、权限和密钥范围。

## TLS 配置 {#tls-configuration}

### 服务器证书

生产环境应使用受信任的 CA 和正确的 SAN。通过受保护的文件导入外部提供的证书；私钥不要放入 Git。

```bash
: "${TLS_CERT_FILE:?Provide the certificate chain file}"
: "${TLS_KEY_FILE:?Provide the protected private-key file}"
kubectl create secret tls argocd-server-tls -n argocd \
  --cert="$TLS_CERT_FILE" --key="$TLS_KEY_FILE" --dry-run=client -o yaml \
  | kubectl apply --server-side -f -
```

即使是开发用的自签名证书也需要 SAN，例如 OpenSSL `-addext "subjectAltName=DNS:argocd.example.com"`；应配置客户端信任，而不是将 --insecure 设为生产环境默认值。

### cert-manager 示例

此示例假设 cert-manager 和受信任的 letsencrypt-prod ClusterIssuer 已配置。对于私有服务，应准备合适的 solver，例如 DNS01。不要基于已弃用的 ingress-nginx HTTP01 集成部署新环境。

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
    size: 4096
```

### 使用 Gateway API 配置 TLS

此示例假设使用 Envoy Gateway 1.9.1、GatewayClass eg、包含 v1 BackendTLSPolicy 的 Gateway API CRD，并且上面的 Certificate 已处于 Ready 状态。Gateway 和 argocd-server 使用同一张受公共 CA 信任的证书；保持 server.insecure 为 false。配置 DNS 和预期的访问边界，并在 CLI 中使用 --grpc-web。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: argocd-gateway
  namespace: argocd
spec:
  gatewayClassName: eg
  listeners:
  - name: https
    hostname: argocd.example.com
    port: 443
    protocol: HTTPS
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: argocd-server-tls
    allowedRoutes:
      namespaces:
        from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: argocd-server
  namespace: argocd
spec:
  parentRefs:
  - name: argocd-gateway
    sectionName: https
  hostnames:
  - argocd.example.com
  rules:
  - backendRefs:
    - name: argocd-server
      port: 443
---
apiVersion: gateway.networking.k8s.io/v1
kind: BackendTLSPolicy
metadata:
  name: argocd-server
  namespace: argocd
spec:
  targetRefs:
  - group: ''
    kind: Service
    name: argocd-server
    sectionName: https
  validation:
    hostname: argocd.example.com
    wellKnownCACertificates: System
```

wellKnownCACertificates:System 假设信任公共 CA。对于内部/自签名证书，请为实际的信任 CA 配置 caCertificateRefs。检查 Gateway listener、Route 的 Accepted/ResolvedRefs 状态以及后端证书验证。

### Git CA 信任与内部 RPC TLS

argocd-tls-certs-cm 用于信任私有 Git/Helm HTTPS 端点；它不是 repo-server 自身的服务证书。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-tls-certs-cm
  namespace: argocd
data:
  git.example.com: REPLACE_WITH_VERIFIED_PUBLIC_CA_PEM
```

默认情况下，内部 repo-server RPC 可以加密传输，但不会验证服务器证书。配置持久化的 argocd-repo-server-tls，并设置服务 DNS SAN，然后重启 repo-server。挂载信任 CA，并在 server/application-controller/applicationset-controller 上使用 --repo-server-ca-cert-path，在 notifications-controller 上使用 --argocd-repo-server-ca-cert-path。应优先使用 CA 路径方法，而不是已弃用的 strict-tls 标志。这本身不构成双向 TLS；客户端证书配置请参阅 [mTLS 指南](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/mtls.md)。

## 审计日志 {#audit-logging}

server.audit.enabled/path 不是 3.5.2 支持的设置。配置组件的 stdout 日志，将其合并到现有的 argocd-cmd-params-cm，然后重启相关工作负载。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cmd-params-cm
  namespace: argocd
data:
  server.log.format: json
  server.log.level: info
  controller.log.format: json
  controller.log.level: info
  reposerver.log.format: json
  reposerver.log.level: info
```

```bash
kubectl logs -n argocd deployment/argocd-server --tail=100
```

实际字段/事件因组件和版本而异。不要将单一运维日志流视为完整的审计记录；应根据保留策略关联 Argo CD/Kubernetes 事件、Kubernetes 或 EKS API 审计日志以及 Git 历史。避免在 debug 日志和渲染后的清单输出中记录 Secret。

### CloudWatch 收集示例

将此配置合并到现有的节点级 Fluent Bit/可观测性部署中。容器日志/DB 挂载、parsers.conf、IAM 权限和网络访问需另行配置。挂载一个空的共享 audit.log volume 并不会收集 stdout。

```ini
[SERVICE]
    Parsers_File      /fluent-bit/etc/parsers.conf
[INPUT]
    Name              tail
    Tag               argocd.*
    Path              /var/log/containers/argocd-server-*_argocd_*.log
    multiline.parser  docker, cri
    DB                /var/log/fluent-bit/argocd.db
    Mem_Buf_Limit     10MB
    Skip_Long_Lines   On
[OUTPUT]
    Name              cloudwatch_logs
    Match             argocd.*
    region            ap-northeast-2
    log_group_name    /aws/eks/example-cluster/argocd
    log_stream_prefix argocd-
    auto_create_group false
    log_key           log
```

预先创建日志组并设置保留/加密策略，然后替换日志组和区域。将收集器的 stream/event 权限限制在该日志组内。Containerd CRI 封装和应用 JSON 属于不同层。

## 网络安全 {#network-security}

这些是适用于非 HA 环境的基线策略模板。CNI 必须支持并执行 NetworkPolicy。选择同一 Pod 的策略允许规则会累加，因此也要检查现有的宽泛策略。将 Gateway 数据平面 namespace/labels、DNS、API/Git/IdP 地址替换为实际部署中的值。

192.0.2.10(API)、198.51.100.10(Git) 和 198.51.100.20(IdP) 是仅供文档使用的地址。标准 NetworkPolicy 无法选择 FQDN；应使用受支持 CNI 的 FQDN 策略或托管出站代理来设计动态目标，并考虑 NAT 前后行为。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-server-restricted
  namespace: argocd
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: argocd-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: envoy-gateway-system
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-repo-server
    ports:
    - protocol: TCP
      port: 8081
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-dex-server
    ports:
    - protocol: TCP
      port: 5556
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 192.0.2.10/32
    ports:
    - protocol: TCP
      port: 443
  - to:
    - ipBlock:
        cidr: 198.51.100.20/32
    ports:
    - protocol: TCP
      port: 443
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: argocd-repo-server-restricted
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
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-applicationset-controller
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-notifications-controller
    ports:
    - protocol: TCP
      port: 8081
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: argocd-redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - ipBlock:
        cidr: 198.51.100.10/32
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 22
```

Redis HA/代理、NodeLocal DNS、metrics collector、Dex LDAP/SAML/OIDC、AVP Vault/KMS 和其他组件都需要相应的流量规则。这两项策略并未涵盖完整的部署清单。在现有工作负载上启用 Pod Security 强制模式之前，应先以 audit/warn 模式进行评估。

## 仓库凭证 {#repository-credentials}

以下 Secret 清单仅用于说明结构。PAT 应仅具备所需仓库的读取权限；GitHub Apps 应限制为适当的安装范围和 Contents-read 权限。通过外部 Secret 管理系统或受保护的文件提供凭证。在 argocd-ssh-known-hosts-cm 中配置经过验证的 SSH 主机密钥。repo-creds.url 是 URL 前缀，而不是 glob；最长匹配项优先，且模板不会覆盖 repository Secret 自身的凭证。

### 使用 HTTPS 和 Personal Access Token

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
  url: https://github.com/myorg/
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
  url: https://github.com/myorg/
  githubAppID: '123456'
  githubAppInstallationID: '12345678'
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
  username: repo-reader
  password: REPLACE_FROM_SECRET_MANAGER
```

## GPG 签名验证 {#gpg-signature-verification}

使用 Argo CD 3.5 引入的 sourceIntegrity 格式。它会验证 Git commit/annotated tag，而不是 Helm/OCI/image 签名。任意 Secret 或名为 developer1.asc 的 ConfigMap 键都不会注册为受信任密钥。

```bash
gpg --armor --export YOUR_VERIFIED_KEY_ID > public-key.asc
argocd gpg add --from public-key.asc
argocd gpg list
```

导入前应通过带外方式验证公钥指纹。声明式密钥环条目应放在 argocd-gpg-keys-cm 中，并以实际的 GPG key ID 为键。将示例中的 0123456789ABCDEF 替换为已导入的组织密钥。从 sourceIntegrity 迁移时，应移除旧的 signatureKeys。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: secure-project
  namespace: argocd
spec:
  sourceRepos:
  - https://github.com/myorg/secure-repo
  destinations:
  - namespace: my-app
    server: https://kubernetes.default.svc
  clusterResourceWhitelist: []
  sourceIntegrity:
    git:
      policies:
      - repos:
        - url: '*'
        gpg:
          mode: head
          keys:
          - 0123456789ABCDEF
```

head 会验证目标 commit 或 annotated tag；严格的历史验证是另一项独立策略。未匹配的源不会经过验证。sourceNamespaces 控制允许使用的 Application CR namespace，而不是签名密钥。

```bash
# Repository-local configuration; replace the key ID first.
git config user.signingkey YOUR_VERIFIED_KEY_ID
git config commit.gpgsign true
git commit -S -m "Signed change"
git log --show-signature -1
```



## 参考资料

- [Argo CD 3.5.2 Secret 管理](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/secret-management.md)
- [CMP sidecar 配置](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/config-management-plugins.md)
- [TLS 信任边界](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/tls.md)
- [IAM Identity Center SAML](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/user-management/identity-center.md)
- [KSOPS 4.5.1](https://github.com/viaduct-ai/kustomize-sops/tree/v4.5.1)

## 测验

要检验你学到的内容，请尝试 [ArgoCD 安全测验](../../quizzes/gitops/argocd/07-security-quiz.md)。
