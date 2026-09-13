# ArgoCD Security

> **Reviewed Against**: Argo CD 3.5.2, Sealed Secrets 0.40.0/chart 2.20.0, ESO 2.10.0, AVP 1.18.1, KSOPS 4.5.1, SOPS 3.13.3
> **Last Updated**: September 11, 2026

## Table of Contents
- [SSO Integration](#sso-integration)
- [Secret Management](#secret-management)
- [TLS Configuration](#tls-configuration)
- [Audit Logging](#audit-logging)
- [Network Security](#network-security)
- [Repository Credentials](#repository-credentials)
- [GPG Signature Verification](#gpg-signature-verification)

## SSO Integration

SSO examples are alternatives: merge required fields into existing ConfigMaps/Secrets without replacing server signing keys or other credentials in argocd-secret. Replace placeholders with actual IdP settings and provide secrets through external Secret management or protected files. Secret YAML below illustrates structure; do not commit its plaintext values.

ArgoCD supports multiple SSO providers for authentication.

### OIDC Configuration

Generic OIDC configuration in `argocd-cm`:

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

Store the client secret:

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

### Okta Integration

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

Okta Application Configuration:
1. Create a new OIDC application in Okta
2. Set sign-in redirect URI: `https://argocd.example.com/auth/callback`
3. Enable "groups" scope
4. Add groups claim to ID token

### Microsoft Entra ID Integration

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

Microsoft Entra ID Configuration:
1. Register a new application in Azure AD
2. Set redirect URI: `https://argocd.example.com/auth/callback`
3. Add API permissions: `openid`, `profile`, `email`
4. Configure groups claim in Token configuration

### AWS IAM Identity Center (AWS SSO)

Create an IAM Identity Center custom SAML application, assign access, and configure ACS/audience for /api/dex/callback. An invented identitycenter.amazonaws.com issuer is not a generic OIDC integration. Map the email attribute and use the metadata’s sign-on URL/signing certificate. Do not assume official dynamic group-attribute mapping; inspect the actual assertion. This example uses the email-claim path.

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

Merge this RBAC data fragment for a real approved email and the restricted viewer role defined in the RBAC chapter.

```yaml
data:
  scopes: '[groups, email]'
  policy.identity-center.csv: |
    g, approved.user@example.com, role:viewer
```

### Dex LDAP Integration

For LDAP/Active Directory, use Dex as the identity broker:

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

Provision verified ca.crt in the ldap-ca ConfigMap and merge these Helm values. Supply bindPW through argocd-secret key dex.ldap.bindPW, using a directory account with only required search permissions.

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

### SAML Integration

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

### Map SSO Groups to RBAC

Merge these bindings with the custom role definitions from the Projects/RBAC chapter; developer and viewer are not built-in roles.

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

## Secret Management

Base64 in a Git Secret manifest is not encryption. Prefer destination-side Secret creation with ESO or Sealed Secrets for new setups. AVP/KSOPS generation-time injection can expose plaintext through repo-server and Redis manifest caches; it has a different trust model.

### Sealed Secrets

This example uses controller 0.40.0/chart2.20.0. The old bitnami-labs Helm URL now returns 404; use the bitnami repository. Install the matching kubeseal binary and verify checksums from the [official release](https://github.com/bitnami/sealed-secrets/releases/tag/v0.40.0). Platform administrators pre-create the destination namespace.

```bash
helm repo add sealed-secrets https://bitnami.github.io/sealed-secrets
helm repo update sealed-secrets
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --version 2.20.0 --namespace kube-system \
  --set fullnameOverride=sealed-secrets-controller --wait --timeout 5m
kubeseal --version  # use 0.40.0 for this example
```

Verify the current kubeconfig targets the intended cluster and fetch that controller’s public certificate. Default strict scope binds ciphertext to the Secret name and namespace; do not rename/move it after sealing. This procedure reads the password from a protected file rather than placing it in Git or command arguments.

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

Review and commit only the generated SealedSecret. A truncated Ag... sample is not usable ciphertext. Protect controller-key backup/recovery as an administrator operation; sealing-key renewal does not itself rotate the application’s secret.

### External Secrets Operator

ESO synchronizes external secret values into destination-cluster Secrets; it does not encrypt plaintext in Git. The 2.10.0 examples use external-secrets.io/v1. AWS jwt.serviceAccountRef below uses IRSA: provision that namespace’s ServiceAccount, IAM role annotation and OIDC trust. Pod Identity uses the controller ServiceAccount association/SDK credential chain instead of this jwt configuration.

Sync secrets from external providers:

```bash
# Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm upgrade --install external-secrets external-secrets/external-secrets \
  --version 2.10.0 --namespace external-secrets --create-namespace --wait --timeout 5m
```

IRSA ServiceAccount example: configure the real role ARN/OIDC trust and allow only required secret ARNs for GetSecretValue/DescribeSecret and, when applicable, KMS Decrypt. For Vault, bind its role to this SA/namespace and audience=vault, with a restricted KV policy and appropriate reviewer setup. Vault 1.21+ requires role audiences.

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

For existing AVP integrations, use a CMP sidecar with 3.5.2. Copying a binary into the main repo-server or creating only a ConfigMap does not register the plugin. ConfigManagementPlugin is a sidecar configuration file, not a Kubernetes CRD. Generated Secret values can be present in Redis/repo-server plaintext caches; restrict this to trusted repositories and an appropriate isolation boundary.

Verify the architecture-specific AVP 1.18.1 binary against its official checksums file and place it in the build context as argocd-vault-plugin. Build/verify this image and replace the illustrative registry image below with your published image.

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

Merge these values into argo-cd chart 10.8.4 configuration, preserving other sidecar/volume entries. The chart supplies var-files/plugins; the sidecar has its own tmp volume.

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

Configure the Vault argocd-readonly role for ServiceAccount argocd/argocd-repo-server, audience=vault, a narrowly scoped read policy and a suitable token reviewer. Provision vault-ca ConfigMap key ca.crt and a valid Vault TLS certificate. Do not substitute broad Kubernetes permissions on repo-server for those requirements.

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

Scope the Application/project/repository and Vault KV paths to the intended environment. Shared sidecar credentials are not an isolation boundary between mutually untrusted projects.

### SOPS (Secrets OPerationS)

This example uses SOPS 3.13.3 and KSOPS 4.5.1. Keep the public age recipient separate from its private identity. Replace the illustrative recipient and keep the private key out of Git.

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

creation_rules matches the input/filename-override path, not the shell redirection target. Argo CD does not automatically decrypt SOPS by default: it needs the KSOPS executable, Kustomize alpha/exec support and decryption credentials.

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

The following Helm values are for an existing Argo CD instance restricted to trusted repositories. Global exec support trusts repository-supplied execution; do not treat it as isolation between untrusted projects. Prefer destination-side Secret management for new environments.

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

Do not commit decrypted output or the private identity. These plugin installations are alternatives; combining them requires explicitly merging values arrays, permissions and key scopes.

## TLS Configuration

### Server Certificate

Use a trusted CA and correct SANs in production. Import externally supplied certificates from protected files; keep private keys out of Git.

```bash
: "${TLS_CERT_FILE:?Provide the certificate chain file}"
: "${TLS_KEY_FILE:?Provide the protected private-key file}"
kubectl create secret tls argocd-server-tls -n argocd \
  --cert="$TLS_CERT_FILE" --key="$TLS_KEY_FILE" --dry-run=client -o yaml \
  | kubectl apply --server-side -f -
```

Even a development self-signed certificate needs SANs, for example OpenSSL `-addext "subjectAltName=DNS:argocd.example.com"`; configure client trust instead of making --insecure a production default.

### cert-manager Example

This assumes cert-manager and a trusted letsencrypt-prod ClusterIssuer are already configured. Prepare an appropriate solver such as DNS01 for private services. Do not base new installations on the retired ingress-nginx HTTP01 integration.

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

### TLS with Gateway API

This assumes Envoy Gateway 1.9.1, GatewayClass eg, Gateway API CRDs including v1 BackendTLSPolicy, and the Certificate above is Ready. Gateway and argocd-server use the same publicly trusted certificate; keep server.insecure false. Configure DNS and the intended access boundary, and use --grpc-web for the CLI.

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

wellKnownCACertificates:System assumes public CA trust. For internal/self-signed certificates, configure caCertificateRefs for the actual trust CA. Check Gateway listeners, Route Accepted/ResolvedRefs and backend certificate validation.

### Git CA Trust versus Internal RPC TLS

argocd-tls-certs-cm trusts private Git/Helm HTTPS endpoints; it is not the repo-server’s own serving certificate.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-tls-certs-cm
  namespace: argocd
data:
  git.example.com: REPLACE_WITH_VERIFIED_PUBLIC_CA_PEM
```

Internal repo-server RPC may be encrypted without server-certificate validation by default. Provision persistent argocd-repo-server-tls with service DNS SANs and restart repo-server. Mount the trust CA and use --repo-server-ca-cert-path on server/application-controller/applicationset-controller, and --argocd-repo-server-ca-cert-path on notifications-controller. Prefer the CA-path method over deprecated strict-tls flags. This is not mutual TLS by itself; follow the [mTLS guide](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/mtls.md) for client certificates.

## Audit Logging

server.audit.enabled/path are not supported 3.5.2 settings. Configure component stdout logs, merge into the existing argocd-cmd-params-cm, then restart the relevant workloads.

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

Actual fields/events vary by component and version. Do not treat one operational log stream as a complete audit trail; correlate Argo CD/Kubernetes events, Kubernetes or EKS API audit logs and Git history under a retention policy. Keep secrets out of debug logs and rendered-manifest output.

### CloudWatch Collection Example

Merge this into an existing node-level Fluent Bit/observability deployment. Configure container-log/DB mounts, parsers.conf, IAM permissions and network access separately. stdout is not collected by attaching an empty shared audit.log volume.

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

Pre-create the log group with retention/encryption settings and replace the group/region. Scope the collector’s stream/event permissions to that group. Containerd CRI framing and application JSON are separate layers.

## Network Security

These are baseline non-HA policy templates. The CNI must support/enforce NetworkPolicy. Allow rules from policies selecting the same Pod are additive, so review existing broad policies too. Replace Gateway data-plane namespace/labels, DNS, API/Git/IdP addresses with the actual deployment.

192.0.2.10(API),198.51.100.10(Git) and198.51.100.20(IdP) are documentation-only addresses. Standard NetworkPolicy cannot select FQDNs; design dynamic destinations with supported CNI FQDN policies or a managed egress proxy, considering pre/post-NAT behavior.

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

Redis HA/proxies, NodeLocal DNS, metrics collectors, Dex LDAP/SAML/OIDC, AVP Vault/KMS and extra components need corresponding flows. These two policies are not a complete deployment inventory. Evaluate Pod Security in audit/warn mode before enforcing it on existing workloads.

## Repository Credentials

Secret manifests below show structure only. Restrict PATs to required repositories/read permissions and GitHub Apps to the appropriate installation/Contents-read scope. Supply credentials through external Secret management or protected files. Configure verified SSH host keys in argocd-ssh-known-hosts-cm. repo-creds.url is a URL prefix, not a glob; the longest match wins, and templates do not override a repository Secret’s own credentials.

### HTTPS with Personal Access Token

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

### SSH Key Authentication

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

### GitHub App Authentication

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

### Helm Repository Credentials

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

## GPG Signature Verification

Use the sourceIntegrity format introduced in Argo CD 3.5. It verifies Git commits/annotated tags, not Helm/OCI/image signatures. An arbitrary Secret or a ConfigMap key named developer1.asc does not register a trusted key.

```bash
gpg --armor --export YOUR_VERIFIED_KEY_ID > public-key.asc
argocd gpg add --from public-key.asc
argocd gpg list
```

Verify the public-key fingerprint out of band before importing. Declarative keyring entries belong in argocd-gpg-keys-cm, keyed by the actual GPG key ID. Replace the illustrative 0123456789ABCDEF with an imported organization key. Remove legacy signatureKeys when migrating to sourceIntegrity.

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

head verifies the target commit or annotated tag; strict history verification is a separate policy. Unmatched sources are not verified. sourceNamespaces controls allowed Application CR namespaces, not signing keys.

```bash
# Repository-local configuration; replace the key ID first.
git config user.signingkey YOUR_VERIFIED_KEY_ID
git config commit.gpgsign true
git commit -S -m "Signed change"
git log --show-signature -1
```



## References

- [Argo CD 3.5.2 secret management](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/secret-management.md)
- [CMP sidecar configuration](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/config-management-plugins.md)
- [TLS trust boundaries](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/tls.md)
- [IAM Identity Center SAML](https://github.com/argoproj/argo-cd/blob/v3.5.2/docs/operator-manual/user-management/identity-center.md)
- [KSOPS 4.5.1](https://github.com/viaduct-ai/kustomize-sops/tree/v4.5.1)

## Quiz

To test what you've learned, try the [ArgoCD security quiz](../../quizzes/gitops/argocd/07-security-quiz.md).
