# Workload Identity with SPIFFE/SPIRE

> **Supported Versions**: SPIRE 1.12+, Kubernetes 1.31, 1.32, 1.33
> **Last Updated**: February 25, 2026

SPIFFE (Secure Production Identity Framework For Everyone) and SPIRE (the SPIFFE Runtime Environment) provide a standards-based approach to workload identity in cloud-native environments. As a CNCF Graduated project, SPIFFE/SPIRE enables zero-trust security by providing cryptographically verifiable identities to workloads without requiring application code changes.

## Table of Contents

1. [The Zero Trust Identity Problem](#the-zero-trust-identity-problem)
2. [SPIFFE Specification Overview](#spiffe-specification-overview)
3. [Core Concepts](#core-concepts)
4. [SPIRE Architecture](#spire-architecture)
5. [Installation](#installation)
6. [Node Attestation](#node-attestation)
7. [Workload Attestation](#workload-attestation)
8. [Kubernetes Integration](#kubernetes-integration)
9. [Service Mesh Integration](#service-mesh-integration)
10. [Federation](#federation)
11. [EKS Integration](#eks-integration)
12. [Best Practices](#best-practices)
13. [Troubleshooting](#troubleshooting)
14. [Summary and References](#summary-and-references)

---

## The Zero Trust Identity Problem

Traditional perimeter-based security models assume that workloads within a network boundary can be trusted. This approach fails in modern distributed systems where:

- **Microservices communicate across network boundaries** — Services span multiple clusters, clouds, and data centers
- **Dynamic infrastructure** — Containers and pods are ephemeral with constantly changing IP addresses
- **Lateral movement attacks** — Once attackers breach the perimeter, they can move freely within the network
- **Shared tenancy** — Multiple teams and applications share the same infrastructure

Zero Trust security requires that every workload prove its identity before communicating, regardless of network location. SPIFFE addresses this by providing:

1. **Universal identity standard** — A consistent way to identify workloads across heterogeneous environments
2. **Cryptographic verification** — Identities that can be verified without trusting the network
3. **Automatic rotation** — Short-lived credentials that minimize blast radius if compromised
4. **No application changes** — Identity injection transparent to applications

---

## SPIFFE Specification Overview

SPIFFE is an open specification that defines three core components:

| Component | Description |
|-----------|-------------|
| **SPIFFE ID** | A URI that uniquely identifies a workload |
| **SVID** | SPIFFE Verifiable Identity Document — a cryptographic document that proves a workload's identity |
| **Trust Bundle** | A set of CA certificates used to verify SVIDs |
| **Workload API** | A local API that workloads use to obtain their SVIDs |

### CNCF Graduation Status

SPIFFE/SPIRE graduated from CNCF in 2022, indicating production-readiness and broad industry adoption. Notable adopters include:

- Bloomberg
- ByteDance
- GitHub
- Pinterest
- Square
- Uber

---

## Core Concepts

### SPIFFE ID

A SPIFFE ID is a URI that uniquely identifies a workload within a trust domain:

```
spiffe://trust-domain/workload-identifier
```

**Components:**

| Part | Description | Example |
|------|-------------|---------|
| `spiffe://` | URI scheme (always "spiffe") | `spiffe://` |
| `trust-domain` | Administrative domain of trust | `prod.example.com` |
| `workload-identifier` | Path identifying the workload | `/ns/payments/sa/api-server` |

**Examples of SPIFFE IDs:**

```
# Kubernetes workload by namespace and service account
spiffe://prod.example.com/ns/payments/sa/api-server

# Workload by cluster and deployment
spiffe://example.com/cluster/us-east-1/deployment/frontend

# Legacy application by hostname
spiffe://example.com/host/db-server-01/app/mysql
```

### SVID (SPIFFE Verifiable Identity Document)

An SVID is a cryptographic document that carries a workload's SPIFFE ID. SPIFFE defines two SVID formats:

#### X.509-SVID vs JWT-SVID Comparison

| Feature | X.509-SVID | JWT-SVID |
|---------|------------|----------|
| **Format** | X.509 certificate | JSON Web Token |
| **Transport** | TLS client certificates | HTTP headers, gRPC metadata |
| **Verification** | Certificate chain validation | Signature verification |
| **Use Case** | mTLS connections | API authentication, proxies |
| **Audience** | Not applicable | Required (prevents replay) |
| **Typical TTL** | 1 hour (configurable) | 5 minutes (short-lived) |
| **Key Storage** | Private key file | Private key for signing |
| **Revocation** | Short TTL (no CRL/OCSP) | Short TTL |

**X.509-SVID Structure:**

```
┌─────────────────────────────────────────────────────────────┐
│                      X.509-SVID                             │
├─────────────────────────────────────────────────────────────┤
│  Subject: CN=<workload-identifier>                          │
│  URI SAN: spiffe://trust-domain/workload-identifier         │
│  Issuer: SPIRE Server CA                                    │
│  Not Before: 2026-02-25T10:00:00Z                          │
│  Not After: 2026-02-25T11:00:00Z (1 hour TTL)              │
│  Public Key: [workload's public key]                        │
│  Signature: [signed by SPIRE Server CA]                     │
└─────────────────────────────────────────────────────────────┘
```

**JWT-SVID Structure:**

```json
{
  "alg": "RS256",
  "kid": "abcd1234",
  "typ": "JWT"
}
.
{
  "sub": "spiffe://prod.example.com/ns/payments/sa/api",
  "aud": ["spiffe://prod.example.com/ns/orders/sa/processor"],
  "exp": 1708858200,
  "iat": 1708857900
}
.
[signature]
```

### Trust Bundle

A trust bundle contains the root CA certificates for a trust domain. Workloads use the trust bundle to verify SVIDs from other workloads in the same trust domain.

```yaml
# Trust bundle structure
trust_domain: "prod.example.com"
root_certificates:
  - |
    -----BEGIN CERTIFICATE-----
    MIIBzDCCAVKgAwIBAgIJAJR2...
    -----END CERTIFICATE-----
jwt_signing_keys:
  - kid: "key-1"
    public_key: |
      -----BEGIN PUBLIC KEY-----
      MIIBIjANBgkqhkiG9w0BAQEF...
      -----END PUBLIC KEY-----
```

### Trust Domain

A trust domain is an administrative boundary of trust. All workloads within a trust domain share the same root of trust (SPIRE Server CA).

**Trust Domain Design Considerations:**

| Pattern | Example | Use Case |
|---------|---------|----------|
| Single domain | `example.com` | Simple deployments |
| Environment-based | `prod.example.com`, `staging.example.com` | Environment isolation |
| Region-based | `us-east.example.com`, `eu-west.example.com` | Regional isolation |
| Cluster-based | `cluster-a.example.com` | Multi-cluster with separate CAs |

---

## SPIRE Architecture

SPIRE implements the SPIFFE specification with a server-agent architecture:

```mermaid
flowchart TB
    subgraph ControlPlane["Control Plane"]
        SERVER[SPIRE Server]
        DATASTORE[(Data Store<br/>SQLite/PostgreSQL)]
        SERVER --> DATASTORE
    end

    subgraph Node1["Kubernetes Node 1"]
        AGENT1[SPIRE Agent]
        WORKLOAD1[Workload Pod A]
        WORKLOAD2[Workload Pod B]
        WORKLOAD1 -->|Workload API| AGENT1
        WORKLOAD2 -->|Workload API| AGENT1
    end

    subgraph Node2["Kubernetes Node 2"]
        AGENT2[SPIRE Agent]
        WORKLOAD3[Workload Pod C]
        WORKLOAD3 -->|Workload API| AGENT2
    end

    AGENT1 -->|Node Attestation<br/>SVID Requests| SERVER
    AGENT2 -->|Node Attestation<br/>SVID Requests| SERVER

    subgraph External["External Components"]
        REGISTRAR[K8s Registrar]
        CSI[SPIFFE CSI Driver]
    end

    REGISTRAR -->|Auto-registration| SERVER
    CSI -->|Mount SVIDs| Node1
    CSI -->|Mount SVIDs| Node2
```

### SPIRE Server

The SPIRE Server is the central authority that:

| Function | Description |
|----------|-------------|
| **CA Operations** | Signs X.509-SVIDs and JWT-SVIDs |
| **Registration API** | Manages workload registration entries |
| **Node Attestation** | Verifies agent identity during bootstrap |
| **Data Store** | Persists registration entries and CA state |
| **Key Management** | Manages signing keys (supports HSM/KMS) |

**Server Configuration Example:**

```yaml
# server.conf
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "prod.example.com"
    data_dir = "/run/spire/data"
    log_level = "INFO"

    ca_ttl = "24h"
    default_x509_svid_ttl = "1h"
    default_jwt_svid_ttl = "5m"

    ca_subject {
        country = ["US"]
        organization = ["Example Corp"]
        common_name = "SPIRE Server CA"
    }
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "postgres"
            connection_string = "dbname=spire host=postgres user=spire"
        }
    }

    NodeAttestor "k8s_psat" {
        plugin_data {
            clusters = {
                "production" = {
                    service_account_allow_list = ["spire:spire-agent"]
                }
            }
        }
    }

    KeyManager "disk" {
        plugin_data {
            keys_path = "/run/spire/data/keys.json"
        }
    }

    UpstreamAuthority "disk" {
        plugin_data {
            key_file_path = "/run/spire/conf/ca.key"
            cert_file_path = "/run/spire/conf/ca.crt"
        }
    }
}
```

### SPIRE Agent

The SPIRE Agent runs on each node and:

| Function | Description |
|----------|-------------|
| **Node Attestation** | Proves node identity to the server |
| **Workload Attestation** | Identifies workloads requesting SVIDs |
| **Workload API** | Serves SVIDs to workloads via Unix socket |
| **SVID Caching** | Caches and rotates SVIDs automatically |
| **SDS Server** | Provides Envoy SDS API for service meshes |

**Agent Configuration Example:**

```yaml
# agent.conf
agent {
    data_dir = "/run/spire/data"
    log_level = "INFO"
    server_address = "spire-server"
    server_port = "8081"
    socket_path = "/run/spire/sockets/agent.sock"
    trust_domain = "prod.example.com"
}

plugins {
    NodeAttestor "k8s_psat" {
        plugin_data {
            cluster = "production"
        }
    }

    KeyManager "memory" {
        plugin_data {}
    }

    WorkloadAttestor "k8s" {
        plugin_data {
            skip_kubelet_verification = true
        }
    }
}
```

### SVID Issuance Flow

The following diagram shows how a workload obtains its SVID:

```mermaid
flowchart LR
    subgraph Workload["Workload Pod"]
        APP[Application]
    end

    subgraph Agent["SPIRE Agent"]
        WAPI[Workload API]
        ATTESTOR[Workload Attestor]
        CACHE[SVID Cache]
    end

    subgraph Server["SPIRE Server"]
        CA[Certificate Authority]
        REGISTRY[Registration Entries]
    end

    APP -->|1. Request SVID<br/>via Unix Socket| WAPI
    WAPI -->|2. Get caller info<br/>PID, UID, container| ATTESTOR
    ATTESTOR -->|3. Query K8s API<br/>for pod metadata| K8S[(Kubernetes API)]
    ATTESTOR -->|4. Match against<br/>registration entries| WAPI
    WAPI -->|5. Request SVID<br/>for matched identity| Server
    CA -->|6. Validate request<br/>sign certificate| CA
    Server -->|7. Return signed<br/>X.509-SVID| WAPI
    WAPI -->|8. Cache SVID| CACHE
    CACHE -->|9. Return SVID<br/>to workload| APP
```

---

## Installation

### Prerequisites

- Kubernetes cluster 1.31+
- Helm 3.10+
- kubectl configured with cluster access
- Cluster admin permissions

### Helm Installation (Recommended)

SPIRE provides a Helm chart with the SPIRE Controller Manager for automated workload registration:

```bash
# Add the SPIFFE Helm repository
helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/
helm repo update

# Create namespace
kubectl create namespace spire-system

# Install SPIRE with Controller Manager
helm install spire spiffe/spire \
  --namespace spire-system \
  --set global.spire.trustDomain="prod.example.com" \
  --set global.spire.clusterName="production" \
  --set spire-server.replicaCount=3 \
  --set spire-server.persistence.enabled=true \
  --set spire-server.persistence.size=1Gi
```

### Namespace Layout

A typical SPIRE deployment uses the following namespace structure:

```
┌─────────────────────────────────────────────────────────────┐
│                    Namespace Layout                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  spire-system/                                              │
│  ├── spire-server (StatefulSet, 3 replicas for HA)         │
│  ├── spire-server-0, spire-server-1, spire-server-2        │
│  ├── spire-controller-manager (Deployment)                  │
│  └── spire-bundle-configmap                                 │
│                                                             │
│  spire-agents/                                              │
│  └── spire-agent (DaemonSet, one per node)                 │
│                                                             │
│  spiffe-csi-driver/                                        │
│  └── spiffe-csi-driver (DaemonSet)                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### High Availability Configuration

For production deployments, configure SPIRE Server for high availability:

```yaml
# values-ha.yaml
spire-server:
  replicaCount: 3

  persistence:
    enabled: true
    size: 5Gi
    storageClass: gp3

  dataStore:
    sql:
      databaseType: postgres
      connectionString: "host=spire-postgres dbname=spire sslmode=verify-full"

  resources:
    requests:
      cpu: 200m
      memory: 512Mi
    limits:
      cpu: 1000m
      memory: 1Gi

  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app.kubernetes.io/name: spire-server
          topologyKey: kubernetes.io/hostname

spire-agent:
  resources:
    requests:
      cpu: 50m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi
```

```bash
# Install with HA values
helm install spire spiffe/spire \
  --namespace spire-system \
  -f values-ha.yaml
```

### Verify Installation

```bash
# Check SPIRE Server status
kubectl -n spire-system get pods -l app.kubernetes.io/name=spire-server

# Check SPIRE Agent status
kubectl -n spire-system get pods -l app.kubernetes.io/name=spire-agent

# Verify server health
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server healthcheck

# List registered entries
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server entry show
```

---

## Node Attestation

Node attestation establishes trust between SPIRE Agents and the SPIRE Server. The agent must prove its identity before it can request SVIDs on behalf of workloads.

### Attestation Flow

```mermaid
flowchart TB
    subgraph NodeAttestation["Node Attestation Methods"]
        direction TB
        PSAT[K8s PSAT<br/>Projected Service Account Token]
        AWSIID[AWS IID<br/>Instance Identity Document]
        JOIN[Join Token<br/>One-time Bootstrap]
    end

    subgraph Agent["SPIRE Agent Bootstrap"]
        AGENT_START[Agent Starts]
        COLLECT[Collect Attestation Data]
        SEND[Send to Server]
    end

    subgraph Server["SPIRE Server"]
        VALIDATE[Validate Attestation]
        ISSUE_NODE[Issue Node SVID]
        STORE[Store Node Record]
    end

    AGENT_START --> COLLECT
    COLLECT --> PSAT
    COLLECT --> AWSIID
    COLLECT --> JOIN

    PSAT --> SEND
    AWSIID --> SEND
    JOIN --> SEND

    SEND --> VALIDATE
    VALIDATE -->|Valid| ISSUE_NODE
    ISSUE_NODE --> STORE
    STORE -->|Node SVID| Agent

    VALIDATE -->|Invalid| REJECT[Reject Connection]
```

### Kubernetes PSAT (Projected Service Account Token)

The recommended attestation method for Kubernetes. Uses projected service account tokens that are automatically rotated.

**Server Configuration:**

```yaml
# In server.conf plugins section
NodeAttestor "k8s_psat" {
    plugin_data {
        clusters = {
            "production" = {
                service_account_allow_list = ["spire-system:spire-agent"]
                audience = ["spire-server"]
            }
        }
    }
}
```

**Agent Configuration:**

```yaml
# In agent.conf plugins section
NodeAttestor "k8s_psat" {
    plugin_data {
        cluster = "production"
        token_path = "/var/run/secrets/tokens/spire-agent"
    }
}
```

**Agent DaemonSet with PSAT:**

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spire-agent
  namespace: spire-system
spec:
  selector:
    matchLabels:
      app: spire-agent
  template:
    metadata:
      labels:
        app: spire-agent
    spec:
      serviceAccountName: spire-agent
      containers:
        - name: spire-agent
          image: ghcr.io/spiffe/spire-agent:1.12.0
          volumeMounts:
            - name: spire-token
              mountPath: /var/run/secrets/tokens
      volumes:
        - name: spire-token
          projected:
            sources:
              - serviceAccountToken:
                  path: spire-agent
                  expirationSeconds: 7200
                  audience: spire-server
```

### AWS Instance Identity Document (IID)

For EKS or EC2-based Kubernetes clusters, AWS IID provides strong node attestation using AWS's cryptographically signed instance metadata.

**Server Configuration:**

```yaml
NodeAttestor "aws_iid" {
    plugin_data {
        access_key_id = "AKIAIOSFODNN7EXAMPLE"      # Or use IRSA
        secret_access_key = "wJalrXUtnFEMI/K7MDENG" # Or use IRSA
        skip_block_device = true
        account_ids_for_local_validation = ["123456789012"]
    }
}
```

**Agent Configuration:**

```yaml
NodeAttestor "aws_iid" {
    plugin_data {}
}
```

### Join Token (Bootstrap)

For initial setup or non-cloud environments. One-time tokens that expire after use.

```bash
# Generate a join token on the server
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server token generate \
  -spiffeID spiffe://prod.example.com/agent/node-01 \
  -ttl 3600

# Output: Token: abc123-def456-ghi789

# Use the token when starting the agent
spire-agent run -joinToken abc123-def456-ghi789
```

### Node Attestor Comparison

| Attestor | Security | Automation | Use Case |
|----------|----------|------------|----------|
| **k8s_psat** | High | Fully automatic | Kubernetes clusters |
| **aws_iid** | High | Fully automatic | AWS EC2/EKS |
| **gcp_iit** | High | Fully automatic | GCP GKE |
| **azure_msi** | High | Fully automatic | Azure AKS |
| **join_token** | Medium | Manual | Bootstrap, air-gapped |
| **x509pop** | High | Semi-automatic | Existing PKI integration |

---

## Workload Attestation

Workload attestation identifies the specific workload requesting an SVID from the SPIRE Agent. The agent uses attestors to collect information about the calling process.

### Kubernetes Workload Attestor

The Kubernetes attestor queries the kubelet to identify pods:

```yaml
# In agent.conf
WorkloadAttestor "k8s" {
    plugin_data {
        kubelet_read_only_port = 10255  # Or use secure port
        skip_kubelet_verification = false
        node_name_env = "MY_NODE_NAME"
    }
}
```

**Selectors Available:**

| Selector | Description | Example |
|----------|-------------|---------|
| `k8s:ns` | Namespace | `k8s:ns:payments` |
| `k8s:sa` | Service Account | `k8s:sa:api-server` |
| `k8s:pod-label` | Pod label | `k8s:pod-label:app:frontend` |
| `k8s:pod-owner` | Owner reference | `k8s:pod-owner:Deployment:web` |
| `k8s:pod-owner-uid` | Owner UID | `k8s:pod-owner-uid:abc123` |
| `k8s:pod-name` | Pod name | `k8s:pod-name:web-abc123` |
| `k8s:pod-uid` | Pod UID | `k8s:pod-uid:def456` |
| `k8s:container-name` | Container name | `k8s:container-name:app` |
| `k8s:container-image` | Container image | `k8s:container-image:nginx:1.25` |
| `k8s:node-name` | Node name | `k8s:node-name:node-01` |

### Registration Entry Examples

Registration entries map workload selectors to SPIFFE IDs:

```bash
# Register a workload by namespace and service account
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://prod.example.com/ns/payments/sa/api-server \
  -parentID spiffe://prod.example.com/agent/k8s-node \
  -selector k8s:ns:payments \
  -selector k8s:sa:api-server

# Register with pod labels
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://prod.example.com/app/frontend \
  -parentID spiffe://prod.example.com/agent/k8s-node \
  -selector k8s:ns:web \
  -selector k8s:pod-label:app:frontend

# Register with container image (for supply chain security)
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://prod.example.com/verified/nginx \
  -parentID spiffe://prod.example.com/agent/k8s-node \
  -selector k8s:container-image:nginx:1.25-alpine
```

### Unix Workload Attestor

For non-Kubernetes workloads or additional process-level attestation:

```yaml
WorkloadAttestor "unix" {
    plugin_data {
        discover_workload_path = true
    }
}
```

**Unix Selectors:**

| Selector | Description |
|----------|-------------|
| `unix:uid` | Process user ID |
| `unix:gid` | Process group ID |
| `unix:user` | Username |
| `unix:group` | Group name |
| `unix:path` | Executable path |
| `unix:sha256` | Binary SHA256 hash |

---

## Kubernetes Integration

### SPIFFE CSI Driver

The SPIFFE CSI Driver mounts SVIDs directly into pod filesystems without requiring application changes:

```bash
# Install SPIFFE CSI Driver
helm install spiffe-csi-driver spiffe/spiffe-csi-driver \
  --namespace spiffe-csi-driver \
  --create-namespace \
  --set spire.agentSocketPath=/run/spire/sockets/agent.sock
```

**Using CSI Driver in Pods:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-workload
  namespace: payments
spec:
  serviceAccountName: api-server
  containers:
    - name: app
      image: myapp:latest
      volumeMounts:
        - name: spiffe
          mountPath: /run/spiffe
          readOnly: true
      env:
        - name: SVID_PATH
          value: /run/spiffe/svid.pem
        - name: KEY_PATH
          value: /run/spiffe/key.pem
        - name: BUNDLE_PATH
          value: /run/spiffe/bundle.pem
  volumes:
    - name: spiffe
      csi:
        driver: csi.spiffe.io
        readOnly: true
```

**Files Mounted by CSI Driver:**

```
/run/spiffe/
├── svid.pem         # X.509-SVID certificate
├── key.pem          # Private key
├── bundle.pem       # Trust bundle (CA certificates)
└── svid.jwt         # JWT-SVID (if configured)
```

### SPIRE Controller Manager

The SPIRE Controller Manager automates workload registration using Kubernetes CRDs:

```bash
# Controller Manager is included in the main SPIRE Helm chart
# Verify it's running
kubectl -n spire-system get pods -l app.kubernetes.io/name=spire-controller-manager
```

**ClusterSPIFFEID Custom Resource:**

```yaml
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: payments-api
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/ns/{{ .PodMeta.Namespace }}/sa/{{ .PodSpec.ServiceAccountName }}"
  podSelector:
    matchLabels:
      app: payments-api
  namespaceSelector:
    matchLabels:
      spiffe-enabled: "true"
  ttl: 1h
  dnsNameTemplates:
    - "{{ .PodMeta.Name }}.{{ .PodMeta.Namespace }}.svc.cluster.local"
  workloadSelectorTemplates:
    - "k8s:ns:{{ .PodMeta.Namespace }}"
    - "k8s:sa:{{ .PodSpec.ServiceAccountName }}"
```

**Label Namespaces for Auto-Registration:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: payments
  labels:
    spiffe-enabled: "true"
```

**Advanced ClusterSPIFFEID Examples:**

```yaml
# Identity based on deployment and container
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: deployment-identity
spec:
  spiffeIDTemplate: >-
    spiffe://{{ .TrustDomain }}/cluster/{{ .ClusterName }}/ns/{{ .PodMeta.Namespace }}/deploy/{{ index .PodMeta.Labels "app" }}
  podSelector:
    matchExpressions:
      - key: app
        operator: Exists
  ttl: 30m
  federatesWith:
    - "partner.example.com"
---
# Identity for jobs with short TTL
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: batch-jobs
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/job/{{ .PodMeta.Namespace }}/{{ index .PodMeta.Labels \"job-name\" }}"
  podSelector:
    matchLabels:
      workload-type: batch
  ttl: 5m
```

### Envoy SDS Integration

SPIRE Agent exposes an SDS (Secret Discovery Service) API for Envoy-based proxies:

```yaml
# Agent configuration for SDS
agent {
    # ... other config ...

    # Enable SDS for Envoy
    sds {
        default_svid_name = "default"
        default_bundle_name = "ROOTCA"
    }
}
```

**Envoy Configuration Using SPIRE SDS:**

```yaml
static_resources:
  listeners:
    - name: mtls_listener
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8443
      filter_chains:
        - transport_socket:
            name: envoy.transport_sockets.tls
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
              common_tls_context:
                tls_certificate_sds_secret_configs:
                  - name: "spiffe://prod.example.com/ns/web/sa/frontend"
                    sds_config:
                      api_config_source:
                        api_type: GRPC
                        grpc_services:
                          - envoy_grpc:
                              cluster_name: spire_agent
                validation_context_sds_secret_config:
                  name: "ROOTCA"
                  sds_config:
                    api_config_source:
                      api_type: GRPC
                      grpc_services:
                        - envoy_grpc:
                            cluster_name: spire_agent

  clusters:
    - name: spire_agent
      connect_timeout: 1s
      type: STATIC
      lb_policy: ROUND_ROBIN
      typed_extension_protocol_options:
        envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
          "@type": type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
          explicit_http_config:
            http2_protocol_options: {}
      load_assignment:
        cluster_name: spire_agent
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    pipe:
                      path: /run/spire/sockets/agent.sock
```

---

## Service Mesh Integration

### Istio + SPIRE Integration

SPIRE can replace Istio's built-in CA (Citadel) for stronger workload identity guarantees:

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                  Istio + SPIRE Integration                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   │   istiod    │     │ SPIRE Server│     │  SPIRE      │  │
│   │ (disabled   │     │    (CA)     │     │  Agent      │  │
│   │    CA)      │     │             │     │             │  │
│   └─────────────┘     └──────┬──────┘     └──────┬──────┘  │
│                              │                    │         │
│                              │ SVID               │ SDS     │
│                              ▼                    ▼         │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              Envoy Sidecar (istio-proxy)            │  │
│   │         Receives SVID via SPIRE Agent SDS           │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Configure Istio to Use SPIRE:**

```yaml
# IstioOperator configuration
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-spire
spec:
  profile: default
  meshConfig:
    trustDomain: prod.example.com
  values:
    global:
      caAddress: ""  # Disable Citadel
    pilot:
      env:
        PILOT_CERT_PROVIDER: spiffe
        SPIFFE_BUNDLE_ENDPOINTS: "prod.example.com|https://spire-server.spire-system:8443"
  components:
    pilot:
      k8s:
        env:
          - name: PILOT_ENABLE_WORKLOAD_ENTRY_AUTOREGISTRATION
            value: "true"
```

**Sidecar Injection with SPIRE:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: istio-sidecar-injector
  namespace: istio-system
data:
  values: |
    {
      "global": {
        "caAddress": "spire-agent.spire-system:8081",
        "pilotCertProvider": "spiffe"
      }
    }
```

### Cilium + SPIRE Mutual Authentication

Cilium can use SPIRE for mutual authentication between services:

```yaml
# CiliumNetworkPolicy with SPIFFE identity
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: payments-api-policy
  namespace: payments
spec:
  endpointSelector:
    matchLabels:
      app: payments-api
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      authentication:
        mode: required
  egress:
    - toEndpoints:
        - matchLabels:
            app: database
      authentication:
        mode: required
```

**Cilium SPIRE Configuration:**

```yaml
# Cilium Helm values
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
      serverAddress: spire-server.spire-system:8081
      trustDomain: prod.example.com
```

### Linkerd Identity Trust Anchors

Linkerd can be configured to trust SPIRE-issued certificates:

```bash
# Export SPIRE trust bundle
kubectl -n spire-system exec spire-server-0 -- \
  /opt/spire/bin/spire-server bundle show -format spiffe > spire-bundle.json

# Install Linkerd with SPIRE trust anchor
linkerd install \
  --identity-trust-anchors-file spire-bundle.json \
  --identity-issuer-certificate-file spire-ca.crt \
  --identity-issuer-key-file spire-ca.key \
  | kubectl apply -f -
```

---

## Federation

Federation enables workloads in different trust domains to establish mutual trust. This is essential for multi-cluster, multi-cloud, and cross-organization communication.

### Federation Trust Establishment

```mermaid
flowchart LR
    subgraph TrustDomainA["Trust Domain A<br/>us-east.example.com"]
        SERVER_A[SPIRE Server A]
        AGENT_A[SPIRE Agent A]
        WORKLOAD_A[Workload A]
    end

    subgraph TrustDomainB["Trust Domain B<br/>eu-west.example.com"]
        SERVER_B[SPIRE Server B]
        AGENT_B[SPIRE Agent B]
        WORKLOAD_B[Workload B]
    end

    subgraph BundleExchange["Bundle Exchange"]
        ENDPOINT_A[Bundle Endpoint A<br/>:8443/bundle]
        ENDPOINT_B[Bundle Endpoint B<br/>:8443/bundle]
    end

    SERVER_A -->|Publish Bundle| ENDPOINT_A
    SERVER_B -->|Publish Bundle| ENDPOINT_B

    SERVER_A -->|Fetch Bundle B| ENDPOINT_B
    SERVER_B -->|Fetch Bundle A| ENDPOINT_A

    WORKLOAD_A <-->|mTLS with<br/>Cross-Domain Trust| WORKLOAD_B

    AGENT_A --> SERVER_A
    AGENT_B --> SERVER_B
    WORKLOAD_A --> AGENT_A
    WORKLOAD_B --> AGENT_B
```

### Configuring Federation

**Server A Configuration (us-east.example.com):**

```yaml
server {
    trust_domain = "us-east.example.com"

    federation {
        bundle_endpoint {
            address = "0.0.0.0"
            port = 8443
        }

        federates_with "eu-west.example.com" {
            bundle_endpoint_url = "https://spire-server-eu.example.com:8443"
            bundle_endpoint_profile "https_spiffe" {
                endpoint_spiffe_id = "spiffe://eu-west.example.com/spire/server"
            }
        }
    }
}
```

**Server B Configuration (eu-west.example.com):**

```yaml
server {
    trust_domain = "eu-west.example.com"

    federation {
        bundle_endpoint {
            address = "0.0.0.0"
            port = 8443
        }

        federates_with "us-east.example.com" {
            bundle_endpoint_url = "https://spire-server-us.example.com:8443"
            bundle_endpoint_profile "https_spiffe" {
                endpoint_spiffe_id = "spiffe://us-east.example.com/spire/server"
            }
        }
    }
}
```

### Federated Registration Entries

```bash
# Register a workload that can communicate with federated domain
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://us-east.example.com/ns/payments/sa/api \
  -parentID spiffe://us-east.example.com/agent/node \
  -selector k8s:ns:payments \
  -selector k8s:sa:api \
  -federatesWith "spiffe://eu-west.example.com"
```

**ClusterSPIFFEID with Federation:**

```yaml
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: cross-region-api
spec:
  spiffeIDTemplate: "spiffe://{{ .TrustDomain }}/ns/{{ .PodMeta.Namespace }}/sa/{{ .PodSpec.ServiceAccountName }}"
  podSelector:
    matchLabels:
      federation-enabled: "true"
  federatesWith:
    - "eu-west.example.com"
    - "ap-south.example.com"
```

### Multi-Cloud Federation Example

```
┌─────────────────────────────────────────────────────────────┐
│                 Multi-Cloud Federation                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   AWS (us-east-1)              GCP (us-central1)            │
│   ┌─────────────────┐          ┌─────────────────┐          │
│   │ Trust Domain:   │          │ Trust Domain:   │          │
│   │ aws.corp.com    │◄────────►│ gcp.corp.com    │          │
│   │                 │ HTTPS    │                 │          │
│   │ EKS Cluster     │ Bundle   │ GKE Cluster     │          │
│   └─────────────────┘ Exchange └─────────────────┘          │
│           ▲                            ▲                     │
│           │                            │                     │
│           ▼                            ▼                     │
│   ┌─────────────────┐          ┌─────────────────┐          │
│   │ On-Prem DC      │          │ Azure (eastus)  │          │
│   │ Trust Domain:   │          │ Trust Domain:   │          │
│   │ dc.corp.com     │◄────────►│ azure.corp.com  │          │
│   └─────────────────┘          └─────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## EKS Integration

### IRSA vs SPIFFE Comparison

| Feature | IRSA | SPIFFE/SPIRE |
|---------|------|--------------|
| **Scope** | AWS services only | Universal (any service) |
| **Identity Format** | IAM Role ARN | SPIFFE ID (URI) |
| **Token Type** | OIDC JWT (AWS STS) | X.509-SVID, JWT-SVID |
| **Trust Boundary** | Single AWS account (or cross-account) | Any trust domain (multi-cloud) |
| **Rotation** | Pod restart required | Automatic (no restart) |
| **mTLS** | Not supported | Native support |
| **Service Mesh** | Not integrated | Native integration |
| **Use Case** | AWS API access | Service-to-service auth |

### Pod Identity vs SPIRE

| Feature | EKS Pod Identity | SPIRE |
|---------|------------------|-------|
| **Setup Complexity** | Low (AWS managed) | Medium (self-managed) |
| **Cloud Lock-in** | AWS only | Cloud agnostic |
| **Custom Identity** | No (IAM only) | Yes (any identity) |
| **Federation** | Cross-account IAM | Any trust domain |
| **On-premises** | Not supported | Fully supported |
| **Hybrid Cloud** | Limited | Full support |

### Hybrid Use Cases

**Scenario 1: AWS API + Service-to-Service**

Use IRSA for AWS API access and SPIRE for service-to-service authentication:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: hybrid-workload
  annotations:
    # IRSA for AWS API access
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/my-role
spec:
  serviceAccountName: my-service-account
  containers:
    - name: app
      image: myapp:latest
      volumeMounts:
        # SPIRE for service-to-service mTLS
        - name: spiffe
          mountPath: /run/spiffe
          readOnly: true
      env:
        # AWS credentials from IRSA
        - name: AWS_ROLE_ARN
          value: arn:aws:iam::123456789012:role/my-role
        - name: AWS_WEB_IDENTITY_TOKEN_FILE
          value: /var/run/secrets/eks.amazonaws.com/serviceaccount/token
        # SPIRE certificates for mTLS
        - name: SVID_PATH
          value: /run/spiffe/svid.pem
  volumes:
    - name: spiffe
      csi:
        driver: csi.spiffe.io
        readOnly: true
```

**Scenario 2: Cross-Cloud with EKS**

```yaml
# EKS cluster federates with GKE and on-premises
apiVersion: spire.spiffe.io/v1alpha1
kind: ClusterSPIFFEID
metadata:
  name: eks-cross-cloud
spec:
  spiffeIDTemplate: "spiffe://eks.example.com/ns/{{ .PodMeta.Namespace }}/sa/{{ .PodSpec.ServiceAccountName }}"
  podSelector:
    matchLabels:
      cross-cloud: "true"
  federatesWith:
    - "gke.example.com"
    - "onprem.example.com"
```

### EKS-Specific Node Attestation

For EKS, use AWS IID attestation for stronger node identity:

```yaml
# Server plugin configuration for EKS
NodeAttestor "aws_iid" {
    plugin_data {
        skip_block_device = true
        disable_instance_profile_selectors = false

        # Allow specific EKS node groups
        agent_path_template = "/eks/{{ .ClusterName }}/{{ .NodeGroupName }}/{{ .InstanceID }}"
    }
}

NodeResolver "aws_iid" {
    plugin_data {
        # Resolve AWS-specific selectors
        # tag:kubernetes.io/cluster/my-cluster = owned
        # tag:eks:nodegroup-name = my-nodegroup
    }
}
```

---

## Best Practices

### Trust Domain Naming

| Guideline | Example | Rationale |
|-----------|---------|-----------|
| Use DNS-like names | `prod.example.com` | Globally unique, familiar |
| Environment separation | `prod.corp.com`, `staging.corp.com` | Prevent cross-env access |
| Avoid IP addresses | Never use IPs | IPs change, names don't |
| Plan for federation | `aws.corp.com`, `gcp.corp.com` | Easier multi-cloud setup |

### SVID TTL Tuning

```yaml
# Recommended TTL values
server {
    # Root CA certificate - long lived
    ca_ttl = "168h"  # 7 days

    # X.509-SVID for workloads
    default_x509_svid_ttl = "1h"  # Balance security vs performance

    # JWT-SVID for API calls
    default_jwt_svid_ttl = "5m"  # Short for stateless auth
}
```

**TTL Guidelines:**

| Workload Type | Recommended TTL | Rationale |
|---------------|-----------------|-----------|
| Long-running services | 1h | Balance rotation overhead |
| Batch jobs | 5-15m | Match job duration |
| API gateways | 30m | Frequent rotation acceptable |
| CI/CD jobs | 5m | Short-lived, high security |

### High Availability Deployment

```yaml
# Production HA configuration
spire-server:
  replicaCount: 3

  # Use external PostgreSQL for HA
  dataStore:
    sql:
      databaseType: postgres
      connectionString: "host=spire-postgres-cluster..."

  # Pod anti-affinity for spread
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app.kubernetes.io/name: spire-server
          topologyKey: topology.kubernetes.io/zone

  # Resource limits
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi

  # Persistent storage for CA keys
  persistence:
    enabled: true
    storageClass: gp3
    size: 10Gi
```

### Key Rotation

SPIRE automatically rotates SVIDs before expiration. For CA key rotation:

```bash
# Prepare new upstream CA (if using disk-based upstream authority)
# 1. Generate new CA key pair
# 2. Update server configuration
# 3. Restart servers one at a time

# For AWS KMS-based key management
UpstreamAuthority "aws_kms" {
    plugin_data {
        region = "us-east-1"
        key_arn = "arn:aws:kms:us-east-1:123456789012:key/abc123"
    }
}
```

### Security Hardening

```yaml
# Agent security configuration
agent {
    # Restrict socket access
    socket_path = "/run/spire/sockets/agent.sock"

    # Require attestation for all workloads
    authorized_delegates = []

    # Log all workload API requests
    log_level = "INFO"
}

# Network policies for SPIRE
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: spire-server-policy
  namespace: spire-system
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: spire-server
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: spire-agent
      ports:
        - port: 8081
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
```

---

## Troubleshooting

### Common Issues

**Issue: Agent Cannot Connect to Server**

```bash
# Check agent logs
kubectl -n spire-system logs -l app.kubernetes.io/name=spire-agent

# Verify server is reachable
kubectl -n spire-system exec -it spire-agent-xxxxx -- \
  nc -zv spire-server 8081

# Check node attestation
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server agent list
```

**Issue: Workload Cannot Get SVID**

```bash
# Verify registration entry exists
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server entry show

# Check workload attestation from agent
kubectl -n spire-system exec -it spire-agent-xxxxx -- \
  /opt/spire/bin/spire-agent api fetch x509 -socketPath /run/spire/sockets/agent.sock

# Debug workload selectors
kubectl -n spire-system exec -it spire-agent-xxxxx -- \
  /opt/spire/bin/spire-agent api fetch x509 -socketPath /run/spire/sockets/agent.sock -debug
```

**Issue: CSI Driver Not Mounting SVIDs**

```bash
# Check CSI driver pods
kubectl -n spiffe-csi-driver get pods

# Verify CSI driver registration
kubectl get csidrivers csi.spiffe.io

# Check events on failing pod
kubectl describe pod <pod-name> -n <namespace>
```

### Health Checks

```bash
# Server health
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server healthcheck

# Agent health
kubectl -n spire-system exec -it spire-agent-xxxxx -- \
  /opt/spire/bin/spire-agent healthcheck

# Bundle status
kubectl -n spire-system exec -it spire-server-0 -- \
  /opt/spire/bin/spire-server bundle show
```

---

## Summary and References

### Key Takeaways

1. **SPIFFE provides universal workload identity** — A standards-based approach that works across clouds, clusters, and platforms

2. **SPIRE implements SPIFFE at scale** — Production-ready implementation with automated attestation and SVID management

3. **Zero-code integration** — CSI driver and service mesh integrations mean no application changes required

4. **Federation enables multi-cluster/multi-cloud** — Trust domains can federate for cross-boundary authentication

5. **Complements cloud-native identity** — SPIFFE works alongside IRSA/Pod Identity for comprehensive identity management

### Architecture Decision Guide

| Requirement | Recommendation |
|-------------|----------------|
| AWS-only, AWS APIs | Use IRSA or Pod Identity |
| Multi-cloud services | Use SPIFFE/SPIRE |
| Service mesh mTLS | Use SPIFFE/SPIRE |
| Hybrid cloud | Use SPIFFE/SPIRE |
| Cross-organization trust | Use SPIFFE Federation |
| Simple setup, single cluster | Start with cloud-native (IRSA), add SPIRE later |

### References

**Official Documentation:**

- [SPIFFE Specification](https://spiffe.io/docs/latest/spiffe-about/overview/)
- [SPIRE Documentation](https://spiffe.io/docs/latest/spire-about/)
- [SPIRE Helm Charts](https://github.com/spiffe/helm-charts-hardened)
- [SPIFFE CSI Driver](https://github.com/spiffe/spiffe-csi)

**Integration Guides:**

- [Istio + SPIRE Integration](https://istio.io/latest/docs/ops/integrations/spire/)
- [Cilium Mutual Authentication](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/)
- [Envoy SDS Integration](https://www.envoyproxy.io/docs/envoy/latest/configuration/security/secret)

**CNCF Resources:**

- [SPIFFE CNCF Project Page](https://www.cncf.io/projects/spiffe/)
- [SPIFFE Slack Channel](https://slack.spiffe.io/)
- [SPIFFE Community Meetings](https://github.com/spiffe/spiffe/wiki/Community)
