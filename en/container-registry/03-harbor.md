# Harbor

> **Last Updated**: February 25, 2026

## Overview

Harbor is an open-source, cloud-native container registry that provides enterprise-grade features for storing, signing, and scanning container images. As a CNCF Graduated project, Harbor has proven its maturity, security, and adoption across the industry.

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-tenancy** | Project-based isolation with RBAC |
| **Vulnerability Scanning** | Built-in Trivy scanner |
| **Image Signing** | Cosign and Notation support |
| **Replication** | Push/pull replication between registries |
| **Garbage Collection** | Automated cleanup of unused layers |
| **Proxy Cache** | Cache remote registries (Docker Hub, etc.) |
| **Audit Logging** | Complete operation history |
| **OIDC/LDAP** | Enterprise identity integration |
| **Quota Management** | Storage limits per project |
| **Robot Accounts** | Service accounts for automation |

### Architecture

```mermaid
flowchart TB
    subgraph Harbor["Harbor"]
        Nginx["Nginx (Proxy)"]
        Portal["Portal (Web UI)"]
        Core["Core (API)"]
        Nginx --> Core
        Portal --> Core

        subgraph Services["Core Services"]
            Registry["Registry<br/>(Docker Registry)"]
            JobService["Job Service<br/>(Async Tasks)"]
            Trivy["Trivy<br/>(Vuln Scanner)"]
            Notary["Notary<br/>(Signing)"]
        end

        subgraph DataLayer["Data Services"]
            PG["PostgreSQL<br/>(Metadata Store)"]
            Redis["Redis<br/>(Job Queue/Cache)"]
        end

        subgraph Storage["Storage Backend"]
            Backend["Filesystem / S3 / Azure Blob / GCS"]
        end

        Core --> Services
        Services --> DataLayer
        Registry --> Storage
    end

    style Harbor fill:#60B932,stroke:#3d7a1f,color:#fff
    style Services fill:#4a9028,stroke:#3d7a1f,color:#fff
    style DataLayer fill:#4a9028,stroke:#3d7a1f,color:#fff
```

### Component Responsibilities

| Component | Purpose |
|-----------|---------|
| **Core** | API server, authentication, authorization, project management |
| **Registry** | Docker Distribution v2 API implementation, image storage |
| **Job Service** | Async task execution (replication, scanning, GC) |
| **Trivy** | Vulnerability scanning engine |
| **Notary** | Content trust and image signing (legacy) |
| **Portal** | Web UI for administration |
| **PostgreSQL** | Metadata, user data, audit logs |
| **Redis** | Job queue, session cache, registry cache |

## Helm Installation

### Prerequisites

```bash
# Add Harbor Helm repository
helm repo add harbor https://helm.goharbor.io
helm repo update

# Create namespace
kubectl create namespace harbor
```

### Basic Installation

```bash
helm install harbor harbor/harbor \
  --namespace harbor \
  --set expose.type=ingress \
  --set expose.ingress.hosts.core=harbor.example.com \
  --set externalURL=https://harbor.example.com \
  --set persistence.persistentVolumeClaim.registry.size=100Gi \
  --set persistence.persistentVolumeClaim.database.size=10Gi \
  --set persistence.persistentVolumeClaim.redis.size=5Gi
```

### Production values.yaml

```yaml
# harbor-values.yaml
expose:
  type: ingress
  tls:
    enabled: true
    certSource: secret
    secret:
      secretName: harbor-tls
  ingress:
    hosts:
      core: harbor.example.com
    className: nginx
    annotations:
      nginx.ingress.kubernetes.io/proxy-body-size: "0"
      nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
      nginx.ingress.kubernetes.io/proxy-send-timeout: "600"

externalURL: https://harbor.example.com

# Persistence configuration
persistence:
  enabled: true
  resourcePolicy: keep
  persistentVolumeClaim:
    registry:
      storageClass: gp3
      size: 500Gi
      accessMode: ReadWriteOnce
    database:
      storageClass: gp3
      size: 20Gi
      accessMode: ReadWriteOnce
    redis:
      storageClass: gp3
      size: 10Gi
      accessMode: ReadWriteOnce
    trivy:
      storageClass: gp3
      size: 10Gi
      accessMode: ReadWriteOnce

# Use S3 for registry storage (recommended for production)
# persistence:
#   imageChartStorage:
#     type: s3
#     s3:
#       region: us-east-1
#       bucket: my-harbor-registry
#       # Use IRSA for authentication
#       # accesskey: ""
#       # secretkey: ""

# Database configuration
database:
  type: internal
  internal:
    resources:
      requests:
        memory: 512Mi
        cpu: 250m
      limits:
        memory: 2Gi
        cpu: 1000m
  # For production, use external PostgreSQL
  # type: external
  # external:
  #   host: "harbor-db.cluster-xxx.us-east-1.rds.amazonaws.com"
  #   port: "5432"
  #   username: "harbor"
  #   password: "secretpassword"
  #   database: "harbor"
  #   sslmode: "require"

# Redis configuration
redis:
  type: internal
  internal:
    resources:
      requests:
        memory: 256Mi
        cpu: 100m
      limits:
        memory: 1Gi
        cpu: 500m
  # For production, use external Redis (ElastiCache)
  # type: external
  # external:
  #   addr: "harbor-redis.xxx.ng.0001.use1.cache.amazonaws.com:6379"

# Core component
core:
  replicas: 2
  resources:
    requests:
      memory: 512Mi
      cpu: 250m
    limits:
      memory: 2Gi
      cpu: 1000m
  # Secret key for encrypting credentials
  secretKey: "not-a-secure-key"  # Change this!
  # XSRF key
  xsrfKey: "not-a-secure-xsrf-key"  # Change this!

# Job Service
jobservice:
  replicas: 2
  resources:
    requests:
      memory: 512Mi
      cpu: 250m
    limits:
      memory: 2Gi
      cpu: 1000m
  jobLoggers:
    - stdout
    - database
  maxJobWorkers: 10

# Registry
registry:
  replicas: 2
  resources:
    requests:
      memory: 256Mi
      cpu: 100m
    limits:
      memory: 2Gi
      cpu: 1000m
  credentials:
    username: harbor_registry_user
    password: harbor_registry_password  # Change this!

# Trivy scanner
trivy:
  enabled: true
  replicas: 1
  resources:
    requests:
      memory: 512Mi
      cpu: 250m
    limits:
      memory: 2Gi
      cpu: 1000m
  # Trivy database auto-update
  gitHubToken: ""  # Optional: speeds up DB downloads

# Portal (Web UI)
portal:
  replicas: 2
  resources:
    requests:
      memory: 128Mi
      cpu: 50m
    limits:
      memory: 512Mi
      cpu: 500m

# Notary (optional, for Docker Content Trust)
notary:
  enabled: false

# Metrics
metrics:
  enabled: true
  core:
    path: /metrics
    port: 8001
  registry:
    path: /metrics
    port: 8001
  jobservice:
    path: /metrics
    port: 8001

# Cache settings
cache:
  enabled: true
  expireHours: 24

# Garbage collection (manual trigger via UI/API)
# Configure automatic GC via cron job externally

# Log level
logLevel: info

# Update strategy
updateStrategy:
  type: RollingUpdate
```

### Installation with Custom Values

```bash
# Install with production values
helm install harbor harbor/harbor \
  --namespace harbor \
  --values harbor-values.yaml \
  --wait

# Verify installation
kubectl get pods -n harbor
kubectl get ingress -n harbor

# Get initial admin password
kubectl get secret -n harbor harbor-core -o jsonpath="{.data.HARBOR_ADMIN_PASSWORD}" | base64 -d
```

### Upgrading Harbor

```bash
# Check current version
helm list -n harbor

# Update repo and check available versions
helm repo update
helm search repo harbor/harbor --versions

# Backup database before upgrade
kubectl exec -n harbor harbor-database-0 -- pg_dump -U postgres registry > harbor-backup.sql

# Upgrade
helm upgrade harbor harbor/harbor \
  --namespace harbor \
  --values harbor-values.yaml \
  --wait
```

## Projects and RBAC

### Project Types

| Type | Description | Use Case |
|------|-------------|----------|
| **Public** | Anyone can pull images | Open source, shared base images |
| **Private** | Only members can access | Application images, internal tools |

### Creating Projects

```bash
# Using Harbor API
# Login and get token
TOKEN=$(curl -s -u admin:Harbor12345 \
  "https://harbor.example.com/service/token?service=harbor-registry" | jq -r .token)

# Create project via API
curl -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "project_name": "myapp",
    "metadata": {
      "public": "false",
      "enable_content_trust": "true",
      "auto_scan": "true",
      "severity": "high"
    },
    "storage_limit": 107374182400
  }'
```

### RBAC Roles

| Role | Permissions |
|------|-------------|
| **Project Admin** | Full control: manage members, policies, images |
| **Maintainer** | Push/pull images, scan, delete tags |
| **Developer** | Push/pull images, scan |
| **Guest** | Pull images only |
| **Limited Guest** | Pull images from proxy cache only |

### Adding Members

```bash
# Add user to project
curl -X POST "https://harbor.example.com/api/v2.0/projects/myapp/members" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "role_id": 2,
    "member_user": {
      "username": "developer1"
    }
  }'

# Role IDs: 1=Admin, 2=Developer, 3=Guest, 4=Maintainer, 5=Limited Guest
```

### Robot Accounts

Robot accounts are service accounts for CI/CD automation:

```bash
# Create robot account
curl -X POST "https://harbor.example.com/api/v2.0/robots" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "name": "ci-robot",
    "description": "Robot account for CI/CD pipelines",
    "duration": 365,
    "level": "project",
    "permissions": [
      {
        "kind": "project",
        "namespace": "myapp",
        "access": [
          {"resource": "repository", "action": "push"},
          {"resource": "repository", "action": "pull"},
          {"resource": "artifact", "action": "delete"},
          {"resource": "tag", "action": "create"},
          {"resource": "tag", "action": "delete"},
          {"resource": "scan", "action": "create"}
        ]
      }
    ]
  }'

# Response includes robot name and secret
# {
#   "name": "robot$ci-robot",
#   "secret": "xxxxxxxxxxxxxxxxxxxx",
#   ...
# }
```

Using robot account in CI/CD:

```bash
# Docker login with robot account
docker login harbor.example.com \
  -u 'robot$myapp+ci-robot' \
  -p 'robot-secret-here'

# Push image
docker push harbor.example.com/myapp/app:v1.0.0
```

## Image Replication

```mermaid
flowchart LR
    subgraph Pull["Pull Replication (Mirror)"]
        direction LR
        ExtReg["External Registry<br/>Docker Hub / ECR"] -->|Pull| HarborLocal["Harbor (Local)"]
    end

    subgraph Push["Push Replication (Distribute)"]
        direction LR
        HarborSrc["Harbor (Source)"] -->|Push| RemoteReg["Remote Registry<br/>ECR / Harbor DR"]
    end
```

Harbor supports bidirectional replication between registries.

### Replication Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Push** | Harbor pushes to remote | Distribute to edge locations |
| **Pull** | Harbor pulls from remote | Mirror Docker Hub, sync from ECR |

### Setting Up Replication Endpoints

```bash
# Create registry endpoint (e.g., Docker Hub)
curl -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "name": "docker-hub",
    "type": "docker-hub",
    "url": "https://hub.docker.com",
    "credential": {
      "type": "basic",
      "access_key": "dockerhub-username",
      "access_secret": "dockerhub-password"
    }
  }'

# Create registry endpoint (ECR)
curl -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "name": "aws-ecr",
    "type": "aws-ecr",
    "url": "https://123456789012.dkr.ecr.us-east-1.amazonaws.com",
    "credential": {
      "type": "basic",
      "access_key": "AKIAIOSFODNN7EXAMPLE",
      "access_secret": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    }
  }'

# Create registry endpoint (another Harbor)
curl -X POST "https://harbor.example.com/api/v2.0/registries" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "name": "harbor-dr",
    "type": "harbor",
    "url": "https://harbor-dr.example.com",
    "credential": {
      "type": "basic",
      "access_key": "admin",
      "access_secret": "Harbor12345"
    }
  }'
```

### Creating Replication Rules

```bash
# Pull replication from Docker Hub (mirror official images)
curl -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "name": "mirror-dockerhub-nginx",
    "src_registry": {"id": 1},
    "dest_namespace": "dockerhub-mirror",
    "filters": [
      {"type": "name", "value": "library/nginx"},
      {"type": "tag", "value": "1.*"}
    ],
    "trigger": {
      "type": "scheduled",
      "trigger_settings": {
        "cron": "0 0 * * *"
      }
    },
    "enabled": true,
    "deletion": false,
    "override": true,
    "speed": -1
  }'

# Push replication to DR site
curl -X POST "https://harbor.example.com/api/v2.0/replication/policies" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "name": "replicate-to-dr",
    "dest_registry": {"id": 3},
    "src_namespaces": ["production"],
    "filters": [
      {"type": "tag", "value": "v*"}
    ],
    "trigger": {
      "type": "event_based"
    },
    "enabled": true,
    "deletion": true,
    "override": true,
    "speed": 102400
  }'
```

### Replication Filters

| Filter Type | Description | Example |
|-------------|-------------|---------|
| `name` | Repository name pattern | `library/**`, `myapp/*` |
| `tag` | Tag pattern | `v*`, `latest`, `!*-dev` |
| `label` | Harbor label | `production`, `approved` |
| `resource` | Resource type | `image`, `chart` |

## Vulnerability Scanning

### Trivy Integration

Harbor uses Trivy as its default vulnerability scanner. Trivy scans for:

- OS package vulnerabilities (Alpine, Debian, Ubuntu, RHEL, etc.)
- Application dependencies (npm, pip, gem, maven, go modules)
- Misconfigurations

### Scan-on-Push Configuration

```bash
# Enable automatic scanning for a project
curl -X PUT "https://harbor.example.com/api/v2.0/projects/myapp" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "metadata": {
      "auto_scan": "true"
    }
  }'
```

### Manual Scanning

```bash
# Trigger scan via API
curl -X POST "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/sha256:abc123/scan" \
  -u admin:Harbor12345

# Get scan results
curl "https://harbor.example.com/api/v2.0/projects/myapp/repositories/app/artifacts/sha256:abc123?with_scan_overview=true" \
  -u admin:Harbor12345
```

### CVE Allowlists

Create allowlists to ignore specific CVEs:

```bash
# Set project-level CVE allowlist
curl -X PUT "https://harbor.example.com/api/v2.0/projects/myapp" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "cve_allowlist": {
      "items": [
        {"cve_id": "CVE-2023-12345"},
        {"cve_id": "CVE-2023-67890"}
      ],
      "expires_at": 1735689600
    }
  }'

# System-wide CVE allowlist
curl -X PUT "https://harbor.example.com/api/v2.0/system/CVEAllowlist" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "items": [
      {"cve_id": "CVE-2023-12345"}
    ],
    "expires_at": null
  }'
```

### Preventing Vulnerable Image Deployment

Configure Harbor to block pulls of vulnerable images:

```bash
# Set vulnerability prevention policy
curl -X PUT "https://harbor.example.com/api/v2.0/projects/myapp" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "metadata": {
      "prevent_vul": "true",
      "severity": "high"
    }
  }'

# Severity options: none, low, medium, high, critical
```

When enabled, Harbor returns 412 Precondition Failed for pulls of images exceeding the severity threshold.

## Image Signing

Harbor supports image signing with Cosign and Notation for supply chain security.

### Cosign Integration

```bash
# Generate Cosign key pair
cosign generate-key-pair

# Sign image
cosign sign --key cosign.key harbor.example.com/myapp/app:v1.0.0

# Verify signature
cosign verify --key cosign.pub harbor.example.com/myapp/app:v1.0.0

# Sign with keyless (Sigstore/Fulcio)
COSIGN_EXPERIMENTAL=1 cosign sign harbor.example.com/myapp/app:v1.0.0
```

### Configuring Cosign in Harbor

```yaml
# harbor-values.yaml
core:
  # Enable Cosign signature verification
  cosignKeyFile: /etc/cosign/cosign.pub

# Mount Cosign public key
extraVolumes:
  - name: cosign-key
    secret:
      secretName: cosign-public-key
extraVolumeMounts:
  - name: cosign-key
    mountPath: /etc/cosign
    readOnly: true
```

### Notation (Notary v2) Integration

```bash
# Install Notation CLI
curl -sSL https://github.com/notaryproject/notation/releases/download/v1.0.0/notation_1.0.0_linux_amd64.tar.gz | tar xz

# Generate certificate
notation cert generate-test --default "mycompany.io"

# Sign image
notation sign harbor.example.com/myapp/app:v1.0.0

# Verify signature
notation verify harbor.example.com/myapp/app:v1.0.0
```

### Kubernetes Policy Enforcement

Use Kyverno or OPA Gatekeeper to enforce signed images:

```yaml
# Kyverno policy for Cosign verification
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
spec:
  validationFailureAction: Enforce
  background: false
  rules:
  - name: verify-cosign-signature
    match:
      resources:
        kinds:
        - Pod
    verifyImages:
    - imageReferences:
      - "harbor.example.com/*"
      attestors:
      - entries:
        - keys:
            publicKeys: |-
              -----BEGIN PUBLIC KEY-----
              MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...
              -----END PUBLIC KEY-----
```

## Air-Gap Scenarios

Harbor is ideal for disconnected or air-gapped environments.

### Offline Installer

```bash
# Download offline installer
wget https://github.com/goharbor/harbor/releases/download/v2.10.0/harbor-offline-installer-v2.10.0.tgz

# Transfer to air-gapped environment
# ... (USB, secure file transfer, etc.)

# Extract and install
tar xzvf harbor-offline-installer-v2.10.0.tgz
cd harbor

# Configure harbor.yml
cp harbor.yml.tmpl harbor.yml
vim harbor.yml

# Install
./install.sh --with-trivy
```

### harbor.yml Configuration

```yaml
# harbor.yml for air-gap deployment
hostname: harbor.internal.local

http:
  port: 80

https:
  port: 443
  certificate: /data/cert/server.crt
  private_key: /data/cert/server.key

harbor_admin_password: Harbor12345

database:
  password: root123
  max_idle_conns: 100
  max_open_conns: 900

data_volume: /data

trivy:
  ignore_unfixed: false
  skip_update: true  # Important for air-gap
  offline_scan: true  # Important for air-gap
  security_check: vuln
  insecure: false

jobservice:
  max_job_workers: 10

notification:
  webhook_job_max_retry: 10

log:
  level: info
  local:
    rotate_count: 50
    rotate_size: 200M
    location: /var/log/harbor

proxy:
  http_proxy:
  https_proxy:
  no_proxy:
  components:
    - core
    - jobservice
    - trivy
```

### Preloading Images for Air-Gap Kubernetes

```bash
# On connected environment: Export images from Docker Hub
IMAGES=(
  "nginx:1.25"
  "redis:7"
  "postgres:15"
  "busybox:1.36"
)

for img in "${IMAGES[@]}"; do
  docker pull $img
  docker save $img -o $(echo $img | tr '/:' '-').tar
done

# Create archive
tar czvf k8s-images.tar.gz *.tar

# Transfer to air-gapped environment
# ... (USB, secure file transfer, etc.)

# On air-gapped environment: Load and push to Harbor
tar xzvf k8s-images.tar.gz

for tarfile in *.tar; do
  docker load -i $tarfile
done

# Login to Harbor
docker login harbor.internal.local

# Re-tag and push
for img in "${IMAGES[@]}"; do
  new_tag="harbor.internal.local/library/$img"
  docker tag $img $new_tag
  docker push $new_tag
done
```

### Trivy Database Update for Air-Gap

```bash
# On connected environment: Download Trivy DB
trivy image --download-db-only
tar czvf trivy-db.tar.gz ~/.cache/trivy/db

# Transfer to air-gapped environment
# ...

# Extract to Harbor Trivy container
kubectl cp trivy-db.tar.gz harbor/harbor-trivy-0:/home/scanner/.cache/trivy/
kubectl exec -n harbor harbor-trivy-0 -- tar xzvf /home/scanner/.cache/trivy/trivy-db.tar.gz -C /home/scanner/.cache/trivy/
```

### Automated Image Sync Script

```bash
#!/bin/bash
# sync-images-to-harbor.sh
# Sync images from a manifest to Harbor

HARBOR_URL="harbor.internal.local"
PROJECT="library"
MANIFEST_FILE="required-images.txt"

# Login to Harbor
docker login $HARBOR_URL

# Read manifest and sync
while IFS= read -r image; do
  [[ "$image" =~ ^#.*$ ]] && continue  # Skip comments
  [[ -z "$image" ]] && continue  # Skip empty lines

  echo "Processing: $image"

  # Pull from source (if connected) or load from local
  if docker pull $image 2>/dev/null; then
    echo "  Pulled from remote"
  elif [ -f "images/$(echo $image | tr '/:' '-').tar" ]; then
    docker load -i "images/$(echo $image | tr '/:' '-').tar"
    echo "  Loaded from local archive"
  else
    echo "  ERROR: Cannot find image $image"
    continue
  fi

  # Determine target name
  if [[ "$image" == *"/"* ]]; then
    repo_name=$(echo $image | cut -d'/' -f2-)
  else
    repo_name="library/$image"
  fi

  target="${HARBOR_URL}/${PROJECT}/${repo_name}"

  # Re-tag and push
  docker tag $image $target
  docker push $target
  echo "  Pushed to $target"

done < "$MANIFEST_FILE"
```

Sample manifest file:

```text
# required-images.txt
# Base images
nginx:1.25
redis:7-alpine
postgres:15-alpine

# Kubernetes components
registry.k8s.io/ingress-nginx/controller:v1.9.0
registry.k8s.io/metrics-server/metrics-server:v0.6.4

# Monitoring
grafana/grafana:10.0.0
prom/prometheus:v2.47.0
```

## Harbor + Kubernetes Integration

### Creating imagePullSecrets

```bash
# Create secret for Harbor
kubectl create secret docker-registry harbor-secret \
  --docker-server=harbor.example.com \
  --docker-username=robot\$myapp+k8s \
  --docker-password=robot-secret \
  -n default

# Verify
kubectl get secret harbor-secret -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq
```

### ServiceAccount Configuration

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
  namespace: default
imagePullSecrets:
- name: harbor-secret
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: app-sa
      containers:
      - name: app
        image: harbor.example.com/myapp/app:v1.0.0
```

### Proxy Cache Configuration

```mermaid
flowchart LR
    Client["Docker/containerd"] --> Harbor{"Harbor<br/>Proxy Cache"}
    Harbor -->|Cache Hit| Return["Return cached image"]
    Harbor -->|Cache Miss| Upstream["Upstream Registry<br/>(Docker Hub, etc.)"]
    Upstream --> Store["Cache in Harbor"]
    Store --> Return
```

Configure Harbor as a proxy cache for external registries:

```bash
# Create proxy cache project via API
curl -X POST "https://harbor.example.com/api/v2.0/projects" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "project_name": "dockerhub-proxy",
    "registry_id": 1,
    "metadata": {
      "public": "true"
    }
  }'
```

Configure containerd to use Harbor proxy:

```toml
# /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri".registry.mirrors."docker.io"]
  endpoint = ["https://harbor.example.com/v2/dockerhub-proxy/"]

[plugins."io.containerd.grpc.v1.cri".registry.configs."harbor.example.com".auth]
  username = "robot$proxy+pull"
  password = "robot-secret"
```

### Garbage Collection

Harbor accumulates unused image layers over time. Configure garbage collection:

```bash
# Trigger GC manually via API
curl -X POST "https://harbor.example.com/api/v2.0/system/gc/schedule" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "schedule": {
      "type": "Manual"
    },
    "parameters": {
      "delete_untagged": true,
      "dry_run": false
    }
  }'

# Schedule automatic GC
curl -X POST "https://harbor.example.com/api/v2.0/system/gc/schedule" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "schedule": {
      "type": "Weekly",
      "cron": "0 0 0 * * 0"
    },
    "parameters": {
      "delete_untagged": true,
      "dry_run": false
    }
  }'

# Check GC history
curl "https://harbor.example.com/api/v2.0/system/gc" \
  -u admin:Harbor12345
```

### Tag Retention Policies

```bash
# Create retention policy
curl -X POST "https://harbor.example.com/api/v2.0/retentions" \
  -H "Content-Type: application/json" \
  -u admin:Harbor12345 \
  -d '{
    "algorithm": "or",
    "rules": [
      {
        "disabled": false,
        "action": "retain",
        "scope_selectors": {
          "repository": [
            {"kind": "doublestar", "decoration": "repoMatches", "pattern": "**"}
          ]
        },
        "tag_selectors": [
          {"kind": "doublestar", "decoration": "matches", "pattern": "v*"}
        ],
        "params": {
          "latestPushedK": 10
        }
      },
      {
        "disabled": false,
        "action": "retain",
        "scope_selectors": {
          "repository": [
            {"kind": "doublestar", "decoration": "repoMatches", "pattern": "**"}
          ]
        },
        "tag_selectors": [
          {"kind": "doublestar", "decoration": "matches", "pattern": "**"}
        ],
        "params": {
          "nDaysSinceLastPush": 30
        }
      }
    ],
    "trigger": {
      "kind": "Schedule",
      "settings": {
        "cron": "0 0 0 * * *"
      }
    },
    "scope": {
      "level": "project",
      "ref": 1
    }
  }'
```

## Best Practices

### High Availability

```yaml
# harbor-values.yaml for HA
core:
  replicas: 3
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            component: core
        topologyKey: kubernetes.io/hostname

registry:
  replicas: 3
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            component: registry
        topologyKey: kubernetes.io/hostname

portal:
  replicas: 2

jobservice:
  replicas: 2

# Use external PostgreSQL (RDS) and Redis (ElastiCache)
database:
  type: external
  external:
    host: harbor-db.cluster-xxx.us-east-1.rds.amazonaws.com
    port: "5432"
    username: harbor
    password: secretpassword
    database: harbor
    sslmode: require

redis:
  type: external
  external:
    addr: harbor-redis.xxx.cache.amazonaws.com:6379

# Use S3 for registry storage
persistence:
  imageChartStorage:
    type: s3
    s3:
      region: us-east-1
      bucket: harbor-registry-prod
      regionendpoint: s3.us-east-1.amazonaws.com
      encrypt: true
```

### Security Hardening

1. **Enable TLS everywhere**
2. **Use OIDC/LDAP instead of local users**
3. **Implement network policies**
4. **Regular security updates**
5. **Audit log monitoring**

```yaml
# Network policy for Harbor
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: harbor-network-policy
  namespace: harbor
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          harbor-access: "true"
    ports:
    - port: 443
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - port: 443
    - port: 5432  # PostgreSQL
    - port: 6379  # Redis
```

### Backup Strategy

```bash
#!/bin/bash
# harbor-backup.sh

BACKUP_DIR="/backups/harbor/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
kubectl exec -n harbor harbor-database-0 -- \
  pg_dump -U postgres registry > $BACKUP_DIR/harbor-db.sql

# Backup Harbor configuration
kubectl get configmap -n harbor -o yaml > $BACKUP_DIR/configmaps.yaml
kubectl get secret -n harbor -o yaml > $BACKUP_DIR/secrets.yaml

# Backup registry storage (if using PVC)
# For S3, enable versioning instead

# Compress
tar czvf $BACKUP_DIR.tar.gz $BACKUP_DIR

# Upload to S3 (if connected)
aws s3 cp $BACKUP_DIR.tar.gz s3://harbor-backups/

echo "Backup completed: $BACKUP_DIR.tar.gz"
```

## Summary

Harbor provides a comprehensive, enterprise-grade container registry solution that excels in:

- **Security**: Built-in vulnerability scanning, image signing, and RBAC
- **Flexibility**: Self-hosted with full control over data and infrastructure
- **Air-Gap Support**: Designed for disconnected environments
- **Multi-tenancy**: Project-based isolation with fine-grained access control
- **Integration**: Replication to/from any OCI-compliant registry

### When to Choose Harbor

| Scenario | Recommendation |
|----------|----------------|
| Air-gapped environment | Harbor (only option) |
| Strict data sovereignty | Harbor |
| Multi-cloud deployment | Harbor |
| AWS-native with EKS | Consider ECR first, Harbor for advanced features |
| Small team, limited ops | Docker Hub or ECR |
| Enterprise with compliance | Harbor or ECR |

### Key Takeaways

1. **Plan storage carefully**: Use S3-compatible storage for production
2. **Configure replication**: Set up DR replication from day one
3. **Enable scanning**: Auto-scan on push with severity thresholds
4. **Use robot accounts**: Never use personal credentials in CI/CD
5. **Implement retention**: Configure garbage collection and retention policies
6. **Monitor and alert**: Use Prometheus metrics and alerting
7. **Backup regularly**: Database backups are critical for disaster recovery
