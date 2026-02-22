# ArgoCD Security

> **Supported Versions**: ArgoCD v2.9+
> **Last Updated**: February 21, 2026

## Table of Contents
- [SSO Integration](#sso-integration)
- [Secret Management](#secret-management)
- [TLS Configuration](#tls-configuration)
- [Audit Logging](#audit-logging)
- [Network Security](#network-security)
- [Repository Credentials](#repository-credentials)
- [GPG Signature Verification](#gpg-signature-verification)

## SSO Integration

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
2. Set sign-in redirect URI: `https://argocd.example.com/api/dex/callback`
3. Enable "groups" scope
4. Add groups claim to ID token

### Azure AD Integration

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

Azure AD Configuration:
1. Register a new application in Azure AD
2. Set redirect URI: `https://argocd.example.com/api/dex/callback`
3. Add API permissions: `openid`, `profile`, `email`
4. Configure groups claim in Token configuration

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

### Map SSO Groups to RBAC

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

## Secret Management

### Sealed Secrets

Encrypt secrets to safely store in Git:

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

Sync secrets from external providers:

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

Inject secrets directly into manifests:

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

Use in manifests:

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

Encrypt secrets with age, GPG, or cloud KMS:

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

Configure ArgoCD to decrypt:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  kustomize.buildOptions: --enable-alpha-plugins
```

## TLS Configuration

### Custom TLS Certificate

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

### cert-manager Integration

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

### TLS for Repository Server

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

## Audit Logging

### Enable Audit Logging

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

### Audit Log Format

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

### Forward Logs to External System

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

## Network Security

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

## Repository Credentials

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
  url: https://github.com/myorg
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
  url: https://github.com/myorg
  githubAppID: "123456"
  githubAppInstallationID: "12345678"
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
  username: admin
  password: secretpassword
```

## GPG Signature Verification

Verify that commits are signed by trusted keys.

### Configure GPG Keys

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

### Enable Signature Verification

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

### Application with Signature Verification

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

When signature verification is enabled, ArgoCD will:
1. Check if the commit is signed
2. Verify the signature against configured keys
3. Reject sync if verification fails

## Quiz

To test what you've learned, try the [ArgoCD security quiz](../../quizzes/gitops/argocd/07-security-quiz.md).
