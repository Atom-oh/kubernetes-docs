# ArgoCD のセキュリティ

> **確認したバージョン**: Argo CD 3.5.2、Sealed Secrets 0.40.0/chart 2.20.0、ESO 2.10.0（リリースノート確認後に 2.12.0 へ更新。例は再実行していません）、AVP 1.18.1、KSOPS 4.5.1、SOPS 3.13.3
> **最終更新日**: 2026年10月16日

## 目次
- [SSO 統合](#sso-integration)
- [Secret 管理](#secret-management)
- [TLS 設定](#tls-configuration)
- [監査ログ](#audit-logging)
- [ネットワークセキュリティ](#network-security)
- [リポジトリ認証情報](#repository-credentials)
- [GPG 署名検証](#gpg-signature-verification)

## SSO 統合 {#sso-integration}

SSO の各例は代替案です。既存の ConfigMap/Secret に必要なフィールドだけをマージし、server の署名鍵や argocd-secret 内の他の認証情報を置き換えないでください。プレースホルダーは実際の IdP 設定に置き換え、Secret は外部 Secret 管理または保護されたファイルから渡します。以下の Secret YAML は構造例です。平文の値を commit しないでください。

Argo CD は認証に複数の SSO provider を利用できます。

### OIDC の設定

`argocd-cm` に設定する汎用 OIDC の例:

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

クライアント Secret を保存します。

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

### Okta との統合

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
1. Okta で新しい OIDC application を作成します。
2. サインインの redirect URI を `https://argocd.example.com/auth/callback` に設定します。
3. `groups` scope を有効にします。
4. ID token に groups claim を追加します。

### Microsoft Entra ID との統合

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

Microsoft Entra ID の設定:
1. Azure AD に application を登録します。
2. redirect URI を `https://argocd.example.com/auth/callback` に設定します。
3. API permission として `openid`、`profile`、`email` を追加します。
4. Token configuration で groups claim を設定します。

### AWS IAM Identity Center (AWS SSO)

IAM Identity Center のカスタム SAML application を作成してアクセスを割り当て、`/api/dex/callback` 用の ACS/audience を設定します。`identitycenter.amazonaws.com` を issuer とする架空の値は、汎用 OIDC 統合として使えません。email attribute をマッピングし、metadata に記載された sign-on URL と署名証明書を使用してください。公式の動的 group-attribute mapping があると仮定せず、実際の assertion を確認します。この例では email claim を使います。

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

実際に承認された email と、RBAC の章で定義した制限付き viewer role に合わせて、この RBAC data fragment をマージします。

```yaml
data:
  scopes: '[groups, email]'
  policy.identity-center.csv: |
    g, approved.user@example.com, role:viewer
```

### Dex と LDAP の統合

LDAP/Active Directory の場合は、ID broker として Dex を使います。

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

検証済みの `ca.crt` を `ldap-ca` ConfigMap に登録し、以下の Helm values をマージします。必要最小限の検索権限を持つディレクトリアカウントを用意し、`bindPW` は `argocd-secret` の `dex.ldap.bindPW` key から渡してください。

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

### SAML との統合

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

### SSO group を RBAC に割り当てる

Projects/RBAC の章で定義した custom role と、以下の binding をマージします。developer と viewer は組み込み role ではありません。

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

Git の Secret manifest で Base64 に変換しても暗号化にはなりません。新しい構成では、ESO または Sealed Secrets を使って宛先クラスター側で Secret を作成する方法を優先してください。AVP/KSOPS で生成時に値を注入すると、repo-server や Redis の manifest cache に平文が残る可能性があります。これらは異なる信頼モデルです。

### Sealed Secrets

この例は controller 0.40.0/chart 2.20.0 を使います。古い bitnami-labs Helm URL は現在 404 を返すため、bitnami repository を使ってください。対応する kubeseal binary をインストールし、[公式 release](https://github.com/bitnami/sealed-secrets/releases/tag/v0.40.0) の checksum を検証します。宛先 namespace は platform 管理者が事前に作成します。

```bash
helm repo add sealed-secrets https://bitnami.github.io/sealed-secrets
helm repo update sealed-secrets
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --version 2.20.0 --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller --wait --timeout 5m
kubeseal --version  # use 0.40.0 for this example
```

現在の kubeconfig が意図したクラスターを指していることを確認し、その controller の公開証明書を取得してください。既定の strict scope は暗号文を Secret 名と namespace に結び付けるため、seal 後に名前や namespace を変更しないでください。この手順では password を Git やコマンド引数に置かず、保護されたファイルから読み取ります。

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

生成された SealedSecret だけを確認して commit してください。途中で切れた `Ag...` の例は有効な暗号文ではありません。controller key の backup/recovery は管理者作業として保護してください。sealing key を更新しても、アプリケーションの Secret 自体は自動的にローテーションされません。

### External Secrets Operator

ESO は外部 provider の Secret 値を宛先クラスターの Secret に同期します。Git 内の平文を暗号化するものではありません。以下の 2.12.0 の例は `external-secrets.io/v1` を使います。AWS の `jwt.serviceAccountRef` は IRSA 用です。namespace の ServiceAccount、IAM role annotation、OIDC trust を作成してください。Pod Identity ではこの jwt 設定の代わりに、controller の ServiceAccount association と SDK credential chain を使います。

外部 provider から Secret を同期します。

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.12.0 --namespace external-secrets --create-namespace --wait --timeout 5m
```

IRSA の ServiceAccount 例では、実際の role ARN/OIDC trust を設定し、必要な Secret ARN に対する GetSecretValue/DescribeSecret と、該当する場合の KMS Decrypt だけを許可します。Vault を使う場合は role をこの ServiceAccount/namespace と `audience=vault` に結び付け、制限された KV policy と適切な token reviewer を設定してください。Vault 1.21 以降では role audience が必要です。

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

### ArgoCD Vault Plugin (AVP)

既存の AVP 統合では、3.5.2 に対応する CMP sidecar を使ってください。binary をメインの repo-server にコピーしたり、ConfigMap だけを作成したりしても plugin は登録されません。ConfigManagementPlugin は sidecar の設定ファイルであり、Kubernetes CRD ではありません。生成された Secret 値が Redis/repo-server の平文 cache に残る可能性があるため、信頼できる repository と適切な分離境界に限定してください。

アーキテクチャに対応した AVP 1.18.1 binary を公式 checksum file で検証し、build context に `argocd-vault-plugin` として配置します。以下の例のイメージをそのまま使わず、このイメージを build/検証して公開した registry image に置き換えてください。

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

以下の値を argo-cd chart 10.8.4 の設定にマージし、既存の sidecar/volume 項目を保持します。chart は var-files/plugins を提供し、sidecar は専用の tmp volume を持ちます。

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

Vault の `argocd-readonly` role には ServiceAccount `argocd/argocd-repo-server`、`audience=vault`、範囲を絞った read policy、適切な token reviewer を設定します。`vault-ca` ConfigMap に `ca.crt` key を用意し、有効な Vault TLS certificate を設定してください。これらの要件を repo-server に広範な Kubernetes 権限を与えることで代替してはいけません。

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

Application/project/repository と Vault KV path の範囲を対象環境に限定してください。sidecar の認証情報共有は、互いを信頼しない project 間の分離境界にはなりません。

### SOPS (Secrets OPerationS)

この例は SOPS 3.13.3 と KSOPS 4.5.1 を使用します。公開 age recipient と秘密の identity を分離してください。例示用 recipient は置き換え、秘密鍵を Git に置かないでください。

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

`creation_rules` が照合するのは入力ファイルまたは filename override の path であり、shell のリダイレクト先ではありません。Argo CD は既定では SOPS を自動復号しません。KSOPS executable、Kustomize の alpha/exec support、復号用 credential が必要です。

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

以下の Helm values は、信頼できる repository に制限された既存 Argo CD instance 向けです。global exec support は repository が提供する実行コードを信頼する設定です。信頼できない project 間の分離と見なさないでください。新しい環境では宛先側の Secret 管理を優先します。

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

復号後の出力や秘密 identity を commit しないでください。これらの plugin の導入方法は代替案です。組み合わせる場合は values array、権限、key scope を明示的に統合する必要があります。

## TLS 設定 {#tls-configuration}

### Server certificate

本番環境では、信頼できる CA と正しい SAN を使ってください。外部から提供される証明書は保護されたファイルから読み込み、秘密鍵を Git に置かないでください。

```bash
: "${TLS_CERT_FILE:?Provide the certificate chain file}"
: "${TLS_KEY_FILE:?Provide the protected private-key file}"
kubectl create secret tls argocd-server-tls -n argocd \
  --cert="$TLS_CERT_FILE" --key="$TLS_KEY_FILE" --dry-run=client -o yaml \
  | kubectl apply --server-side -f -
```

開発用の自己署名証明書でも SAN は必要です。たとえば OpenSSL の `-addext "subjectAltName=DNS:argocd.example.com"` を指定します。本番で `--insecure` を既定にするのではなく、クライアント側に信頼設定を構成してください。

### cert-manager の例

この例は cert-manager と、信頼済みの `letsencrypt-prod` ClusterIssuer がすでに設定されている前提です。private service には DNS01 など適切な solver を準備してください。廃止された ingress-nginx HTTP01 統合を新規導入の前提にしないでください。

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

### Gateway API での TLS

この例は Envoy Gateway 1.9.1、`eg` GatewayClass、v1 BackendTLSPolicy を含む Gateway API CRD、前述の Certificate が Ready であることを前提とします。Gateway と argocd-server では同じ公開信頼済み証明書を使い、`server.insecure` は false のままにしてください。DNS と意図したアクセス境界を構成し、CLI では `--grpc-web` を使います。

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

`wellKnownCACertificates:System` は公開 CA の信頼を前提とします。内部 CA/自己署名証明書の場合は、実際の信頼 CA に対する `caCertificateRefs` を設定してください。Gateway listener、Route の Accepted/ResolvedRefs、backend certificate の検証を確認します。

### Git CA trust と内部 RPC TLS

`argocd-tls-certs-cm` は private Git/Helm HTTPS endpoint の信頼に使うもので、repo-server 自身の serving certificate ではありません。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-tls-certs-cm
  namespace: argocd
data:
  git.example.com: REPLACE_WITH_VERIFIED_PUBLIC_CA_PEM
```

内部 repo-server RPC は暗号化されていても、既定では server certificate が検証されない場合があります。service DNS SAN を持つ永続的な `argocd-repo-server-tls` を作成して repo-server を再起動します。trust CA を mount し、server/application-controller/applicationset-controller では `--repo-server-ca-cert-path`、notifications-controller では `--argocd-repo-server-ca-cert-path` を指定してください。非推奨の strict-tls flag より CA path を使う方法を優先します。これだけでは相互 TLS になりません。クライアント証明書については [mTLS ガイド](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/mtls.md)を参照してください。

## 監査ログ {#audit-logging}

`server.audit.enabled/path` は Argo CD 3.5.2 でサポートされない設定です。コンポーネントの stdout log を構成し、既存の `argocd-cmd-params-cm` に設定をマージしたうえで、該当 workload を再起動してください。

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

実際の field/event はコンポーネントとバージョンで異なります。1 つの運用ログを完全な監査証跡と見なさず、Argo CD/Kubernetes event、Kubernetes または EKS API audit log、Git 履歴を保持ポリシーに基づいて関連付けてください。debug log や render 済み manifest の出力に Secret を含めないでください。

### CloudWatch への収集例

既存のノードレベル Fluent Bit/observability deployment にマージします。container log/DB mount、parser 設定、IAM 権限、ネットワークアクセスは別途構成してください。空の共有 `audit.log` volume を mount しても stdout は収集されません。

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

log group を retention/encryption 設定付きで事前作成し、group/region を置き換えます。collector の stream/event 権限はその log group に限定してください。containerd の CRI framing とアプリケーションの JSON は別々の層です。

## ネットワークセキュリティ {#network-security}

以下は HA 構成ではない基本的な NetworkPolicy template です。CNI が NetworkPolicy をサポートし、強制できる必要があります。同じ Pod を選択する policy の許可ルールは加算されるため、既存の広い policy も確認してください。Gateway data plane の namespace/label、DNS、API/Git/IdP address は実環境の値に置き換えます。

192.0.2.10 (API)、198.51.100.10 (Git)、198.51.100.20 (IdP) はドキュメント用のアドレスです。標準 NetworkPolicy は FQDN を選択できません。宛先が動的な場合は、対応する CNI の FQDN policy または管理された egress proxy を使い、NAT 前後の挙動も考慮してください。

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

Redis HA/proxy、NodeLocal DNS、metrics collector、Dex LDAP/SAML/OIDC、AVP Vault/KMS、その他のコンポーネントには、それぞれ対応する通信経路が必要です。この 2 つの policy は、デプロイ全体に必要な通信を網羅するものではありません。既存 workload に Pod Security を enforce する前に、audit/warn mode で評価してください。

## リポジトリ認証情報 {#repository-credentials}

以下の Secret manifest は構造例です。PAT は必要な repository と read 権限に限定し、GitHub App は適切な installation と Contents-read scope に設定します。credential は外部 Secret 管理または保護されたファイルから渡します。検証済み SSH host key を `argocd-ssh-known-hosts-cm` に設定してください。`repo-creds.url` は glob ではなく URL prefix です。最長一致が優先され、template は repository Secret 自身の credential を上書きしません。

### Personal Access Token を使う HTTPS

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

### SSH key 認証

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
  url: https://github.com/myorg/
  githubAppID: '123456'
  githubAppInstallationID: '12345678'
  githubAppPrivateKey: |
    -----BEGIN RSA PRIVATE KEY-----
    ...
    -----END RSA PRIVATE KEY-----
```

### Helm repository の credential

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

## GPG 署名検証 {#gpg-signature-verification}

Argo CD 3.5 で導入された `sourceIntegrity` 形式を使います。これは Git commit/annotated tag を検証するもので、Helm/OCI/image の署名は検証しません。任意の Secret や `developer1.asc` という key 名の ConfigMap を作っても、信頼済み鍵として登録されません。

```bash
gpg --armor --export YOUR_VERIFIED_KEY_ID > public-key.asc
argocd gpg add --from public-key.asc
argocd gpg list
```

import 前に公開鍵の fingerprint を別経路で検証してください。宣言的な keyring entry は `argocd-gpg-keys-cm` に登録し、実際の GPG key ID を key として使います。例示用の `0123456789ABCDEF` は組織の鍵に置き換えてください。`sourceIntegrity` に移行する際は、従来の `signatureKeys` を削除します。

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

`head` は対象の commit または annotated tag を検証します。履歴全体を厳密に検証することは別の policy です。一致する source がない場合は検証されません。`sourceNamespaces` が制御するのは許可された Application CR の namespace であり、署名鍵ではありません。

```bash
# Repository-local configuration; replace the key ID first.
git config user.signingkey YOUR_VERIFIED_KEY_ID
git config commit.gpgsign true
git commit -S -m "Signed change"
git log --show-signature -1
```

## 参考資料

- [Argo CD 3.5.2 secret management](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/secret-management.md)
- [CMP sidecar configuration](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/config-management-plugins.md)
- [TLS trust boundaries](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/tls.md)
- [IAM Identity Center SAML](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/user-management/identity-center.md)
- [KSOPS 4.5.1](https://github.com/viaduct-ai/kustomize-sops/tree/v4.5.1)

## クイズ

学んだ内容を確認するには、[ArgoCD セキュリティクイズ](../../quizzes/gitops/argocd/07-security-quiz.md)に挑戦してください。
