# Secrets Management

> **Supported Versions**: Kubernetes 1.31, 1.32, 1.33
> **最終更新**: February 22, 2026

Kubernetes の secrets management は、アプリケーションセキュリティの基盤です。このドキュメントでは、native Secrets から External Secrets Operator、Sealed Secrets、HashiCorp Vault、SOPS まで、さまざまな secrets management tools を扱います。

## Table of Contents

1. [Kubernetes Native Secrets](#kubernetes-native-secrets)
2. [External Secrets Operator (ESO)](#external-secrets-operator-eso)
3. [AWS Secrets Manager Integration](#aws-secrets-manager-integration)
4. [AWS Systems Manager Parameter Store Integration](#aws-systems-manager-parameter-store-integration)
5. [Sealed Secrets](#sealed-secrets)
6. [HashiCorp Vault Integration](#hashicorp-vault-integration)
7. [SOPS (Secrets OPerationS)](#sops-secrets-operations)
8. [EKS Pod Identity and IRSA](#eks-pod-identity-and-irsa)
9. [Tool Comparison](#tool-comparison)
10. [Best Practices](#best-practices)

---

## Kubernetes Native Secrets

### Secret Overview

Kubernetes Secrets は、password、token、key などの機密情報を保存する objects です。

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  namespace: default
type: Opaque
data:
  # Base64 encoded values
  username: YWRtaW4=          # admin
  password: cGFzc3dvcmQxMjM=  # password123
```

### Secret Types

| Type | Description | Use Case |
|------|-------------|----------|
| `Opaque` | Default type, stores arbitrary data | General secrets |
| `kubernetes.io/service-account-token` | Service account token | Auto-generated |
| `kubernetes.io/dockerconfigjson` | Docker registry auth | Image pull secrets |
| `kubernetes.io/basic-auth` | Basic authentication | Username/password |
| `kubernetes.io/ssh-auth` | SSH authentication | SSH keys |
| `kubernetes.io/tls` | TLS certificates | HTTPS certificates |

### Creating Secrets

```bash
# Create from literals
kubectl create secret generic db-credentials \
  --from-literal=username=admin \
  --from-literal=password=secret123

# Create from files
kubectl create secret generic ssh-key \
  --from-file=id_rsa=/path/to/id_rsa \
  --from-file=id_rsa.pub=/path/to/id_rsa.pub

# Create TLS Secret
kubectl create secret tls my-tls-secret \
  --cert=path/to/cert.pem \
  --key=path/to/key.pem

# Docker registry Secret
kubectl create secret docker-registry regcred \
  --docker-server=myregistry.io \
  --docker-username=user \
  --docker-password=password
```

### Using Secrets

```yaml
# Using as environment variables
apiVersion: v1
kind: Pod
metadata:
  name: secret-env-pod
spec:
  containers:
  - name: app
    image: myapp:latest
    env:
      # Reference individual keys
      - name: DB_USERNAME
        valueFrom:
          secretKeyRef:
            name: db-credentials
            key: username
      - name: DB_PASSWORD
        valueFrom:
          secretKeyRef:
            name: db-credentials
            key: password
    # All Secret as env vars
    envFrom:
      - secretRef:
          name: app-config
---
# Mounting as volume
apiVersion: v1
kind: Pod
metadata:
  name: secret-volume-pod
spec:
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
      - name: secret-volume
        mountPath: /etc/secrets
        readOnly: true
  volumes:
    - name: secret-volume
      secret:
        secretName: db-credentials
        # Mount specific keys only
        items:
          - key: username
            path: db-user
          - key: password
            path: db-pass
            mode: 0400  # File permissions
```

### Limitations of Secrets

```
┌─────────────────────────────────────────────────────────────────┐
│              Kubernetes Native Secrets Limitations               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Base64 encoding ≠ encryption                                │
│     - Base64 is easily decoded                                  │
│     - Does not provide actual security                          │
│                                                                 │
│  2. Stored in plaintext in etcd (by default)                    │
│     - Secrets exposed if etcd access is compromised             │
│     - Requires separate encryption at rest configuration        │
│                                                                 │
│  3. Cannot commit to Git                                        │
│     - YAML contains sensitive information                       │
│     - Conflicts with GitOps workflows                           │
│                                                                 │
│  4. Difficult rotation                                          │
│     - Manual Secret updates required                            │
│     - No automatic rotation support                             │
│                                                                 │
│  5. Limited audit trail                                         │
│     - Limited logging of Secret access                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### etcd Encryption Configuration

```yaml
# /etc/kubernetes/encryption-config.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      # AES-CBC encryption (recommended)
      - aescbc:
          keys:
            - name: key1
              secret: <32-byte-base64-encoded-key>
      # AWS KMS usage (EKS)
      - kms:
          name: aws-kms
          endpoint: unix:///var/run/kmsplugin/socket.sock
          cachesize: 100
          timeout: 3s
      # Plaintext (fallback)
      - identity: {}
```

---

## External Secrets Operator (ESO)

### ESO Overview

External Secrets Operator は、外部の secret management systems と Kubernetes を接続し、Secrets を自動的に同期します。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  External Secrets Operator Architecture                  │
│                                                                         │
│  ┌─────────────────┐         ┌─────────────────┐                       │
│  │  ExternalSecret │────────▶│ ESO Controller  │                       │
│  │     (CRD)       │         │                 │                       │
│  └─────────────────┘         └────────┬────────┘                       │
│                                       │                                 │
│  ┌─────────────────┐                  │                                 │
│  │   SecretStore   │◀─────────────────┤                                 │
│  │     (CRD)       │                  │                                 │
│  └────────┬────────┘                  │                                 │
│           │                           │                                 │
│           ▼                           ▼                                 │
│  ┌─────────────────┐         ┌─────────────────┐                       │
│  │ External Secret │         │   Kubernetes    │                       │
│  │    Provider     │         │     Secret      │                       │
│  │ (AWS, Vault,..) │         │ (Auto-created)  │                       │
│  └─────────────────┘         └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### ESO Installation

```bash
# Install using Helm
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets \
  --create-namespace \
  --set installCRDs=true
```

### SecretStore Configuration

```yaml
# Namespace-scoped SecretStore
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        # Use IRSA (recommended)
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
---
# Cluster-scoped ClusterSecretStore
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secretsmanager-cluster
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
```

### ExternalSecret Definition

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
  namespace: production
spec:
  # Refresh interval
  refreshInterval: 1h

  # SecretStore reference
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore

  # Kubernetes Secret to create
  target:
    name: db-secret
    creationPolicy: Owner
    template:
      type: Opaque
      data:
        # Using templates
        connection-string: "postgresql://{{ .username }}:{{ .password }}@db.example.com:5432/mydb"

  # Fetch data from external secret
  data:
    - secretKey: username
      remoteRef:
        key: production/database
        property: username

    - secretKey: password
      remoteRef:
        key: production/database
        property: password
---
# Sync entire secret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: full-secret-sync
  namespace: production
spec:
  refreshInterval: 30m
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: app-secrets
  dataFrom:
    - extract:
        key: production/app-config
```

### PushSecret (Reverse Sync)

```yaml
# Push Kubernetes Secret to external system
apiVersion: external-secrets.io/v1alpha1
kind: PushSecret
metadata:
  name: push-to-aws
  namespace: production
spec:
  # Refresh interval
  refreshInterval: 10m

  # SecretStore reference
  secretStoreRefs:
    - name: aws-secretsmanager
      kind: SecretStore

  # Source Kubernetes Secret
  selector:
    secret:
      name: local-secret

  # Push target
  data:
    - match:
        secretKey: api-key
        remoteRef:
          remoteKey: production/api-keys
          property: api-key
```

---

## AWS Secrets Manager Integration

### IRSA Setup

```bash
# Create IAM policy
cat <<EOF > secrets-manager-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecrets"
            ],
            "Resource": [
                "arn:aws:secretsmanager:us-east-1:*:secret:production/*"
            ]
        }
    ]
}
EOF

aws iam create-policy \
    --policy-name EKSSecretsManagerPolicy \
    --policy-document file://secrets-manager-policy.json

# Configure IRSA
eksctl create iamserviceaccount \
    --name external-secrets-sa \
    --namespace external-secrets \
    --cluster my-cluster \
    --attach-policy-arn arn:aws:iam::123456789012:policy/EKSSecretsManagerPolicy \
    --approve
```

### Creating Secrets in AWS Secrets Manager

```bash
# Create secret
aws secretsmanager create-secret \
    --name production/database \
    --secret-string '{"username":"admin","password":"supersecret123","host":"db.example.com"}'

# Update secret
aws secretsmanager update-secret \
    --secret-id production/database \
    --secret-string '{"username":"admin","password":"newsecret456","host":"db.example.com"}'

# Configure automatic rotation
aws secretsmanager rotate-secret \
    --secret-id production/database \
    --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRotation \
    --rotation-rules AutomaticallyAfterDays=30
```

### Complete AWS ESO Example

```yaml
---
# 1. Service Account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: external-secrets-sa
  namespace: external-secrets
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/EKSSecretsManagerRole
---
# 2. ClusterSecretStore
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
# 3. ExternalSecret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: production-db
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
  data:
    - secretKey: DB_HOST
      remoteRef:
        key: production/database
        property: host
    - secretKey: DB_USER
      remoteRef:
        key: production/database
        property: username
    - secretKey: DB_PASS
      remoteRef:
        key: production/database
        property: password
---
# 4. Application Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api
        image: myapi:latest
        envFrom:
          - secretRef:
              name: db-credentials
```

---

## AWS Systems Manager Parameter Store Integration

### Parameter Store Setup

```bash
# Create parameters
aws ssm put-parameter \
    --name "/production/api/key" \
    --value "api-key-value" \
    --type "SecureString" \
    --key-id "alias/aws/ssm"

aws ssm put-parameter \
    --name "/production/database/password" \
    --value "db-password" \
    --type "SecureString"

# Get parameter
aws ssm get-parameter \
    --name "/production/api/key" \
    --with-decryption
```

### ESO Parameter Store Configuration

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-parameter-store
spec:
  provider:
    aws:
      service: ParameterStore
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: ssm-parameters
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-parameter-store
    kind: ClusterSecretStore
  target:
    name: app-config
  data:
    - secretKey: API_KEY
      remoteRef:
        key: /production/api/key
    - secretKey: DB_PASSWORD
      remoteRef:
        key: /production/database/password
```

---

## Sealed Secrets

### Sealed Secrets Overview

Sealed Secrets は、暗号化された Secrets を Git に安全に保存できる tool です。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Sealed Secrets Workflow                               │
│                                                                         │
│  Developer Workstation                        Kubernetes Cluster         │
│  ┌─────────────────┐                        ┌─────────────────────┐    │
│  │  Secret YAML    │                        │  Sealed Secrets     │    │
│  │  (plaintext)    │                        │  Controller         │    │
│  └────────┬────────┘                        └──────────┬──────────┘    │
│           │                                            │               │
│           ▼                                            │               │
│  ┌─────────────────┐                                   │               │
│  │   kubeseal      │◀──── Public Key ─────────────────┘               │
│  │   (encrypt)     │                                                   │
│  └────────┬────────┘                                   │               │
│           │                                            │               │
│           ▼                                            ▼               │
│  ┌─────────────────┐     ┌───────┐          ┌─────────────────────┐   │
│  │  SealedSecret   │────▶│  Git  │─────────▶│  Decrypt and        │   │
│  │  (encrypted)    │     └───────┘          │  create K8s Secret  │   │
│  └─────────────────┘                        └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Sealed Secrets Installation

```bash
# Install Controller
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm repo update

helm install sealed-secrets sealed-secrets/sealed-secrets \
    -n kube-system \
    --set fullnameOverride=sealed-secrets-controller

# Install kubeseal CLI
KUBESEAL_VERSION=$(curl -s https://api.github.com/repos/bitnami-labs/sealed-secrets/releases/latest | jq -r .tag_name | cut -c2-)
curl -OL "https://github.com/bitnami-labs/sealed-secrets/releases/download/v${KUBESEAL_VERSION}/kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz"
tar -xvzf kubeseal-${KUBESEAL_VERSION}-linux-amd64.tar.gz kubeseal
sudo install -m 755 kubeseal /usr/local/bin/kubeseal
```

### Creating SealedSecrets

```bash
# Fetch public key (for offline use)
kubeseal --fetch-cert \
    --controller-name=sealed-secrets-controller \
    --controller-namespace=kube-system \
    > sealed-secrets-pub.pem

# Create Secret YAML
cat <<EOF > secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  namespace: production
type: Opaque
stringData:
  username: admin
  password: supersecret123
EOF

# Convert to SealedSecret
kubeseal --format yaml < secret.yaml > sealed-secret.yaml

# Or use public key file
kubeseal --cert sealed-secrets-pub.pem --format yaml < secret.yaml > sealed-secret.yaml
```

### SealedSecret YAML

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: my-secret
  namespace: production
spec:
  encryptedData:
    username: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEq...
    password: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEq...
  template:
    type: Opaque
    metadata:
      name: my-secret
      namespace: production
      labels:
        app: my-app
```

### Scope Settings

```bash
# strict (default): Bound to both namespace + name
kubeseal --scope strict

# namespace-wide: Can use with different name in same namespace
kubeseal --scope namespace-wide

# cluster-wide: Can use in any namespace
kubeseal --scope cluster-wide
```

### Key Rotation

```bash
# Backup current key
kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key=active -o yaml > sealed-secrets-key.yaml

# New key creation (automatically every 30 days)
# Controller automatically creates new keys

# Re-encrypt existing SealedSecret
kubeseal --re-encrypt < sealed-secret.yaml > sealed-secret-new.yaml
```

---

## HashiCorp Vault Integration

### Vault Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HashiCorp Vault + Kubernetes                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Vault Server                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │   │
│  │  │   Secrets   │  │    Auth     │  │   Audit     │             │   │
│  │  │   Engine    │  │   Methods   │  │    Log      │             │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘             │   │
│  └─────────────────────────┬───────────────────────────────────────┘   │
│                            │                                            │
│         ┌──────────────────┼──────────────────┐                        │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                │
│  │ CSI Driver  │    │   Agent     │    │  ArgoCD     │                │
│  │             │    │  Injector   │    │  Vault      │                │
│  │             │    │             │    │  Plugin     │                │
│  └─────────────┘    └─────────────┘    └─────────────┘                │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Kubernetes Pods                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Vault Installation (Helm)

```bash
# Install Vault Helm chart
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update

# Development mode installation (for testing)
helm install vault hashicorp/vault \
    -n vault \
    --create-namespace \
    --set "server.dev.enabled=true"

# Production installation
helm install vault hashicorp/vault \
    -n vault \
    --create-namespace \
    -f vault-values.yaml
```

```yaml
# vault-values.yaml
server:
  ha:
    enabled: true
    replicas: 3
    raft:
      enabled: true

  dataStorage:
    enabled: true
    size: 10Gi
    storageClass: gp3

  auditStorage:
    enabled: true
    size: 10Gi

injector:
  enabled: true
  replicas: 2

csi:
  enabled: true
```

### Kubernetes Authentication Setup

```bash
# Enable Kubernetes auth in Vault
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443" \
    token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create policy
vault policy write app-policy - <<EOF
path "secret/data/production/*" {
  capabilities = ["read"]
}
EOF

# Create Role (ServiceAccount binding)
vault write auth/kubernetes/role/app-role \
    bound_service_account_names=app-sa \
    bound_service_account_namespaces=production \
    policies=app-policy \
    ttl=24h
```

### Vault Agent Injector

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: production
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: production
spec:
  replicas: 1
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
      annotations:
        # Vault Agent Injector annotations
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "app-role"

        # Secret injection
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/production/config"
        vault.hashicorp.com/agent-inject-template-config: |
          {{- with secret "secret/data/production/config" -}}
          export DB_HOST="{{ .Data.data.db_host }}"
          export DB_USER="{{ .Data.data.db_user }}"
          export DB_PASS="{{ .Data.data.db_pass }}"
          {{- end }}
    spec:
      serviceAccountName: app-sa
      containers:
      - name: app
        image: myapp:latest
        command: ["/bin/sh", "-c"]
        args:
          - source /vault/secrets/config && /app/start.sh
```

### Vault CSI Driver

```yaml
# SecretProviderClass definition
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: vault-database
  namespace: production
spec:
  provider: vault
  parameters:
    vaultAddress: "http://vault.vault:8200"
    roleName: "app-role"
    objects: |
      - objectName: "db-password"
        secretPath: "secret/data/production/database"
        secretKey: "password"
      - objectName: "db-username"
        secretPath: "secret/data/production/database"
        secretKey: "username"
  # Sync to Kubernetes Secret (optional)
  secretObjects:
    - secretName: vault-db-creds
      type: Opaque
      data:
        - objectName: db-password
          key: password
        - objectName: db-username
          key: username
---
# Using in Pod
apiVersion: v1
kind: Pod
metadata:
  name: app-csi
  namespace: production
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
    - name: secrets-store
      mountPath: "/mnt/secrets"
      readOnly: true
    env:
      - name: DB_PASSWORD
        valueFrom:
          secretKeyRef:
            name: vault-db-creds
            key: password
  volumes:
  - name: secrets-store
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: vault-database
```

### ArgoCD Vault Plugin (AVP)

```yaml
# Configure AVP in ArgoCD ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  configManagementPlugins: |
    - name: argocd-vault-plugin
      generate:
        command: ["argocd-vault-plugin"]
        args: ["generate", "./"]
---
# Use AVP in Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
spec:
  source:
    repoURL: https://github.com/myorg/my-app
    path: k8s
    plugin:
      name: argocd-vault-plugin
---
# Secret with AVP placeholders
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  annotations:
    avp.kubernetes.io/path: "secret/data/production/database"
type: Opaque
stringData:
  username: <username>
  password: <password>
```

---

## SOPS (Secrets OPerationS)

### SOPS Overview

SOPS は、Age、PGP、AWS KMS などのさまざまな encryption backends をサポートする、暗号化ファイルを管理するための tool です。

### SOPS Installation and Setup

```bash
# Install SOPS
brew install sops  # macOS
# or
curl -LO https://github.com/getsops/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64
chmod +x sops-v3.8.1.linux.amd64
sudo mv sops-v3.8.1.linux.amd64 /usr/local/bin/sops

# Generate Age key
age-keygen -o key.txt
# Public key: age1...
# Secret key: AGE-SECRET-KEY-...

# Configure .sops.yaml
cat <<EOF > .sops.yaml
creation_rules:
  - path_regex: .*secrets.*\.yaml$
    age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
  - path_regex: .*\.enc\.yaml$
    aws_kms: arn:aws:kms:us-east-1:123456789012:key/abc-123
EOF
```

### Encrypting Secrets with SOPS

```bash
# Create Secret file
cat <<EOF > secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  api-key: my-secret-api-key
  db-password: super-secret-password
EOF

# Encrypt
sops -e secrets.yaml > secrets.enc.yaml

# Decrypt
sops -d secrets.enc.yaml > secrets.yaml

# Edit directly (decrypt -> edit -> re-encrypt)
sops secrets.enc.yaml
```

### Encrypted File Format

```yaml
# secrets.enc.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  api-key: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
  db-password: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
sops:
  kms: []
  gcp_kms: []
  azure_kv: []
  hc_vault: []
  age:
    - recipient: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
      enc: |
        -----BEGIN AGE ENCRYPTED FILE-----
        ...
        -----END AGE ENCRYPTED FILE-----
  lastmodified: "2026-02-21T10:00:00Z"
  mac: ENC[AES256_GCM,data:...,iv:...,tag:...,type:str]
  version: 3.8.1
```

### FluxCD SOPS Integration

```yaml
# FluxCD Kustomization with SOPS
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: app
  namespace: flux-system
spec:
  interval: 10m
  path: ./k8s
  prune: true
  sourceRef:
    kind: GitRepository
    name: my-repo
  # Enable SOPS decryption
  decryption:
    provider: sops
    secretRef:
      name: sops-age
---
# Secret containing Age key
apiVersion: v1
kind: Secret
metadata:
  name: sops-age
  namespace: flux-system
type: Opaque
stringData:
  age.agekey: |
    AGE-SECRET-KEY-1QFPJKM...
```

### AWS KMS with SOPS

```bash
# Encrypt with KMS key
sops --kms arn:aws:kms:us-east-1:123456789012:key/abc-123 \
     -e secrets.yaml > secrets.enc.yaml

# Use multiple keys (for key rotation)
sops --kms "arn:aws:kms:us-east-1:123456789012:key/abc-123,arn:aws:kms:us-west-2:123456789012:key/def-456" \
     -e secrets.yaml > secrets.enc.yaml
```

---

## EKS Pod Identity and IRSA

### IRSA (IAM Roles for Service Accounts)

```yaml
# 1. Create IAM policy and role
# eksctl IRSA setup
# eksctl create iamserviceaccount \
#   --name my-app-sa \
#   --namespace production \
#   --cluster my-cluster \
#   --attach-policy-arn arn:aws:iam::123456789012:policy/MyAppPolicy \
#   --approve

# 2. ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/MyAppRole
---
# 3. Use ServiceAccount in Pod
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  namespace: production
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
    # AWS SDK automatically uses IAM Role credentials
```

### EKS Pod Identity (New)

```bash
# Install EKS Pod Identity Agent
aws eks create-addon \
    --cluster-name my-cluster \
    --addon-name eks-pod-identity-agent

# Create Pod Identity association
aws eks create-pod-identity-association \
    --cluster-name my-cluster \
    --namespace production \
    --service-account my-app-sa \
    --role-arn arn:aws:iam::123456789012:role/MyAppRole
```

```yaml
# ServiceAccount using Pod Identity
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-app-sa
  namespace: production
  # No annotation needed (managed via Pod Identity Association)
---
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  serviceAccountName: my-app-sa
  containers:
  - name: app
    image: myapp:latest
```

### IRSA vs Pod Identity Comparison

| Feature | IRSA | EKS Pod Identity |
|---------|------|------------------|
| **Configuration** | ServiceAccount annotation | API/console association |
| **IAM Role Management** | OIDC trust policy required | EKS managed |
| **Token Format** | OIDC token | EKS Pod Identity token |
| **Role Reuse** | Per-cluster setup | Reuse across clusters |
| **Auditing** | CloudTrail + ServiceAccount | CloudTrail + Pod level |
| **Recommended Use** | Existing clusters | New clusters |

---

## Tool Comparison

### Secrets Management Tool Comparison Table

| Feature | Native Secrets | ESO | Sealed Secrets | Vault | SOPS |
|---------|---------------|-----|----------------|-------|------|
| **Git Storage** | ✗ | ✗ (external) | ✓ | ✗ | ✓ |
| **Auto Rotation** | ✗ | ✓ | ✗ | ✓ | ✗ |
| **Centralized Management** | ✗ | ✓ | ✗ | ✓ | ✗ |
| **Audit Logs** | Limited | Provider-dependent | ✗ | ✓ | ✗ |
| **Complexity** | Low | Medium | Low | High | Low |
| **External Dependency** | None | External store | Controller | Vault server | None |
| **Encryption** | etcd encryption | Provider encryption | Asymmetric | Self-encryption | Various backends |
| **GitOps Friendly** | ✗ | ✓ | ✓ | Plugin needed | ✓ |
| **EKS Integration** | Basic | Excellent | Good | Excellent | Good |

### Recommendations by Use Case

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Recommended Tools by Use Case                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Small/Simple Environments                                              │
│  └─▶ Sealed Secrets + GitOps                                           │
│                                                                         │
│  AWS-Centric Environments                                               │
│  └─▶ ESO + AWS Secrets Manager + IRSA/Pod Identity                     │
│                                                                         │
│  Multi-Cloud/Hybrid                                                     │
│  └─▶ HashiCorp Vault                                                   │
│                                                                         │
│  GitOps First                                                           │
│  └─▶ SOPS + FluxCD or Sealed Secrets + ArgoCD                          │
│                                                                         │
│  Enterprise (Audit/Compliance)                                          │
│  └─▶ HashiCorp Vault + ESO                                             │
│                                                                         │
│  Development/Test Environments                                          │
│  └─▶ Kubernetes Native Secrets + etcd encryption                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Best Practices

### 1. Secret Creation and Storage

```yaml
# DO NOT do this
apiVersion: v1
kind: Secret
metadata:
  name: bad-practice
stringData:
  password: "hardcoded-password"  # Committed to Git!

# Recommended: Use External Secrets or Sealed Secrets
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: good-practice
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: my-secret
  data:
    - secretKey: password
      remoteRef:
        key: production/database
        property: password
```

### 2. Principle of Least Privilege

```yaml
# Restrict Secret access with RBAC
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: secret-reader
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    resourceNames: ["app-config"]  # Specific Secret only
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-secret-reader
  namespace: production
subjects:
  - kind: ServiceAccount
    name: app-sa
    namespace: production
roleRef:
  kind: Role
  name: secret-reader
  apiGroup: rbac.authorization.k8s.io
```

### 3. Secret Rotation

```bash
#!/bin/bash
# secret-rotation.sh

# Set up automatic rotation in AWS Secrets Manager
aws secretsmanager rotate-secret \
    --secret-id production/database \
    --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:RotateSecret \
    --rotation-rules '{"ScheduleExpression": "rate(30 days)"}'

# ESO automatically syncs new values (based on refreshInterval)
```

### 4. Auditing and Monitoring

```yaml
# Falco rule for Secret access monitoring
- rule: Unauthorized Secret Access
  desc: Detect unauthorized access to secrets
  condition: >
    kevt and
    ka.verb in (get, list) and
    ka.target.resource = secrets and
    not ka.user.name in (system:serviceaccount:kube-system:*)
  output: >
    Unauthorized secret access
    (user=%ka.user.name verb=%ka.verb secret=%ka.target.name
    namespace=%ka.target.namespace)
  priority: WARNING
  tags: [k8s, secrets]
```

### 5. Environment Separation

```yaml
# Separate SecretStore per environment
---
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: dev-secrets
  namespace: development
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: dev-secrets-sa
---
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: prod-secrets
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: prod-secrets-sa
```

---

## Summary

Kubernetes secrets management は、セキュリティの基盤です。

1. **Native Secrets**: シンプルですが、Base64 encoding のみを提供します
2. **External Secrets Operator**: 外部の secret stores と同期します
3. **Sealed Secrets**: 暗号化された secrets を Git に安全に保存します
4. **HashiCorp Vault**: enterprise-grade の centralized secret management
5. **SOPS**: file-based encryption で、GitOps friendly です

### Key Recommendations

- production で Native Secrets だけを使用しないでください
- secrets を plaintext で Git に commit しないでください
- automatic rotation を実装してください
- principle of least privilege を適用してください
- secret access auditing を有効にしてください

---

## References

- [Kubernetes Secrets Official Documentation](https://kubernetes.io/docs/concepts/configuration/secret/)
- [External Secrets Operator](https://external-secrets.io/)
- [Sealed Secrets](https://sealed-secrets.netlify.app/)
- [HashiCorp Vault](https://www.vaultproject.io/)
- [SOPS](https://github.com/getsops/sops)
- [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
