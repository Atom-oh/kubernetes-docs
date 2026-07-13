# Identidad de Workload con SPIFFE/SPIRE

> **Versiones compatibles**: SPIRE 1.12+, Kubernetes 1.31, 1.32, 1.33
> **Última actualización**: February 25, 2026

SPIFFE (Secure Production Identity Framework For Everyone) y SPIRE (the SPIFFE Runtime Environment) proporcionan un enfoque basado en estándares para la identidad de workload en entornos cloud-native. Como proyecto Graduated de CNCF, SPIFFE/SPIRE habilita la seguridad zero-trust al proporcionar identidades verificables criptográficamente a los workloads sin requerir cambios en el código de la aplicación.

## Tabla de contenido

1. [El problema de identidad Zero Trust](#the-zero-trust-identity-problem)
2. [Descripción general de la especificación SPIFFE](#spiffe-specification-overview)
3. [Conceptos principales](#core-concepts)
4. [Arquitectura de SPIRE](#spire-architecture)
5. [Instalación](#installation)
6. [Node Attestation](#node-attestation)
7. [Workload Attestation](#workload-attestation)
8. [Integración con Kubernetes](#kubernetes-integration)
9. [Integración con Service Mesh](#service-mesh-integration)
10. [Federación](#federation)
11. [Integración con EKS](#eks-integration)
12. [Buenas prácticas](#best-practices)
13. [Solución de problemas](#troubleshooting)
14. [Resumen y referencias](#summary-and-references)

---

## El problema de identidad Zero Trust

Los modelos de seguridad tradicionales basados en perímetro asumen que se puede confiar en los workloads dentro de un límite de red. Este enfoque falla en los sistemas distribuidos modernos donde:

- **Los microservices se comunican a través de límites de red** — Los Services abarcan múltiples clusters, clouds y data centers
- **Infraestructura dinámica** — Los containers y Pods son efímeros, con direcciones IP que cambian constantemente
- **Ataques de movimiento lateral** — Una vez que los atacantes vulneran el perímetro, pueden moverse libremente dentro de la red
- **Tenencia compartida** — Varios equipos y aplicaciones comparten la misma infraestructura

La seguridad Zero Trust requiere que cada workload pruebe su identidad antes de comunicarse, independientemente de su ubicación en la red. SPIFFE aborda esto proporcionando:

1. **Estándar de identidad universal** — Una forma coherente de identificar workloads en entornos heterogéneos
2. **Verificación criptográfica** — Identidades que pueden verificarse sin confiar en la red
3. **Rotación automática** — Credenciales de corta duración que minimizan el radio de impacto si se ven comprometidas
4. **Sin cambios en la aplicación** — Inyección de identidad transparente para las aplicaciones

---

## Descripción general de la especificación SPIFFE

SPIFFE es una especificación abierta que define tres componentes principales:

| Componente | Descripción |
|-----------|-------------|
| **SPIFFE ID** | Un URI que identifica de forma única un workload |
| **SVID** | SPIFFE Verifiable Identity Document — un documento criptográfico que prueba la identidad de un workload |
| **Trust Bundle** | Un conjunto de certificados CA usados para verificar SVIDs |
| **Workload API** | Una API local que los workloads usan para obtener sus SVIDs |

### Estado de graduación de CNCF

SPIFFE/SPIRE se graduó de CNCF en 2022, lo que indica preparación para producción y amplia adopción en la industria. Entre los adoptantes destacados se incluyen:

- Bloomberg
- ByteDance
- GitHub
- Pinterest
- Square
- Uber

---

## Conceptos principales

### SPIFFE ID

Un SPIFFE ID es un URI que identifica de forma única un workload dentro de un trust domain:

```
spiffe://trust-domain/workload-identifier
```

**Componentes:**

| Parte | Descripción | Ejemplo |
|------|-------------|---------|
| `spiffe://` | Esquema URI (siempre "spiffe") | `spiffe://` |
| `trust-domain` | Dominio administrativo de confianza | `prod.example.com` |
| `workload-identifier` | Ruta que identifica el workload | `/ns/payments/sa/api-server` |

**Ejemplos de SPIFFE IDs:**

```
# Kubernetes workload by namespace and service account
spiffe://prod.example.com/ns/payments/sa/api-server

# Workload by cluster and deployment
spiffe://example.com/cluster/us-east-1/deployment/frontend

# Legacy application by hostname
spiffe://example.com/host/db-server-01/app/mysql
```

### SVID (SPIFFE Verifiable Identity Document)

Un SVID es un documento criptográfico que contiene el SPIFFE ID de un workload. SPIFFE define dos formatos de SVID:

#### Comparación entre X.509-SVID y JWT-SVID

| Característica | X.509-SVID | JWT-SVID |
|---------|------------|----------|
| **Formato** | Certificado X.509 | JSON Web Token |
| **Transporte** | Certificados TLS de cliente | Encabezados HTTP, metadatos gRPC |
| **Verificación** | Validación de cadena de certificados | Verificación de firma |
| **Caso de uso** | Conexiones mTLS | Autenticación de API, proxies |
| **Audiencia** | No aplicable | Requerida (evita replay) |
| **TTL típico** | 1 hora (configurable) | 5 minutos (corta duración) |
| **Almacenamiento de clave** | Archivo de clave privada | Clave privada para firmar |
| **Revocación** | TTL corto (sin CRL/OCSP) | TTL corto |

**Estructura de X.509-SVID:**

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

**Estructura de JWT-SVID:**

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

Un trust bundle contiene los certificados CA raíz para un trust domain. Los workloads usan el trust bundle para verificar SVIDs de otros workloads en el mismo trust domain.

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

Un trust domain es un límite administrativo de confianza. Todos los workloads dentro de un trust domain comparten la misma raíz de confianza (SPIRE Server CA).

**Consideraciones de diseño de Trust Domain:**

| Patrón | Ejemplo | Caso de uso |
|---------|---------|----------|
| Dominio único | `example.com` | Deployments simples |
| Basado en entorno | `prod.example.com`, `staging.example.com` | Aislamiento de entornos |
| Basado en región | `us-east.example.com`, `eu-west.example.com` | Aislamiento regional |
| Basado en cluster | `cluster-a.example.com` | Multi-cluster con CAs separadas |

---

## Arquitectura de SPIRE

SPIRE implementa la especificación SPIFFE con una arquitectura server-agent:

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

El SPIRE Server es la autoridad central que:

| Función | Descripción |
|----------|-------------|
| **Operaciones de CA** | Firma X.509-SVIDs y JWT-SVIDs |
| **Registration API** | Gestiona entradas de registro de workloads |
| **Node Attestation** | Verifica la identidad del agent durante el bootstrap |
| **Data Store** | Persiste entradas de registro y el estado de CA |
| **Key Management** | Gestiona claves de firma (soporta HSM/KMS) |

**Ejemplo de configuración de Server:**

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

El SPIRE Agent se ejecuta en cada node y:

| Función | Descripción |
|----------|-------------|
| **Node Attestation** | Prueba la identidad del node ante el server |
| **Workload Attestation** | Identifica workloads que solicitan SVIDs |
| **Workload API** | Sirve SVIDs a workloads mediante un socket Unix |
| **Caché de SVID** | Almacena en caché y rota SVIDs automáticamente |
| **SDS Server** | Proporciona la API SDS de Envoy para service meshes |

**Ejemplo de configuración de Agent:**

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

### Flujo de emisión de SVID

El siguiente diagrama muestra cómo un workload obtiene su SVID:

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

## Instalación

### Requisitos previos

- Kubernetes cluster 1.31+
- Helm 3.10+
- kubectl configurado con acceso al cluster
- Permisos de administrador de cluster

### Instalación con Helm (recomendada)

SPIRE proporciona un Helm chart con SPIRE Controller Manager para el registro automatizado de workloads:

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

### Distribución de Namespace

Un deployment típico de SPIRE usa la siguiente estructura de namespace:

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

### Configuración de alta disponibilidad

Para deployments de producción, configura SPIRE Server para alta disponibilidad:

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

### Verificar la instalación

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

Node attestation establece confianza entre los SPIRE Agents y el SPIRE Server. El agent debe probar su identidad antes de poder solicitar SVIDs en nombre de workloads.

### Flujo de attestation

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

El método de attestation recomendado para Kubernetes. Usa tokens proyectados de Service Account que se rotan automáticamente.

**Configuración de Server:**

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

**Configuración de Agent:**

```yaml
# In agent.conf plugins section
NodeAttestor "k8s_psat" {
    plugin_data {
        cluster = "production"
        token_path = "/var/run/secrets/tokens/spire-agent"
    }
}
```

**Agent DaemonSet con PSAT:**

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

Para clusters de Kubernetes basados en EKS o EC2, AWS IID proporciona node attestation fuerte usando los metadatos de instancia firmados criptográficamente por AWS.

**Configuración de Server:**

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

**Configuración de Agent:**

```yaml
NodeAttestor "aws_iid" {
    plugin_data {}
}
```

### Join Token (Bootstrap)

Para configuración inicial o entornos que no son cloud. Tokens de un solo uso que expiran después de utilizarse.

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

### Comparación de Node Attestor

| Attestor | Seguridad | Automatización | Caso de uso |
|----------|----------|------------|----------|
| **k8s_psat** | Alta | Totalmente automática | Clusters de Kubernetes |
| **aws_iid** | Alta | Totalmente automática | AWS EC2/EKS |
| **gcp_iit** | Alta | Totalmente automática | GCP GKE |
| **azure_msi** | Alta | Totalmente automática | Azure AKS |
| **join_token** | Media | Manual | Bootstrap, air-gapped |
| **x509pop** | Alta | Semiautomática | Integración con PKI existente |

---

## Workload Attestation

Workload attestation identifica el workload específico que solicita un SVID al SPIRE Agent. El agent usa attestors para recopilar información sobre el proceso llamador.

### Kubernetes Workload Attestor

El attestor de Kubernetes consulta el kubelet para identificar Pods:

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

**Selectores disponibles:**

| Selector | Descripción | Ejemplo |
|----------|-------------|---------|
| `k8s:ns` | Namespace | `k8s:ns:payments` |
| `k8s:sa` | Service Account | `k8s:sa:api-server` |
| `k8s:pod-label` | Etiqueta de Pod | `k8s:pod-label:app:frontend` |
| `k8s:pod-owner` | Referencia de propietario | `k8s:pod-owner:Deployment:web` |
| `k8s:pod-owner-uid` | UID del propietario | `k8s:pod-owner-uid:abc123` |
| `k8s:pod-name` | Nombre del Pod | `k8s:pod-name:web-abc123` |
| `k8s:pod-uid` | UID del Pod | `k8s:pod-uid:def456` |
| `k8s:container-name` | Nombre del container | `k8s:container-name:app` |
| `k8s:container-image` | Imagen del container | `k8s:container-image:nginx:1.25` |
| `k8s:node-name` | Nombre del node | `k8s:node-name:node-01` |

### Ejemplos de Registration Entry

Las entradas de registro asignan selectores de workload a SPIFFE IDs:

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

Para workloads que no son de Kubernetes o attestation adicional a nivel de proceso:

```yaml
WorkloadAttestor "unix" {
    plugin_data {
        discover_workload_path = true
    }
}
```

**Selectores Unix:**

| Selector | Descripción |
|----------|-------------|
| `unix:uid` | ID de usuario del proceso |
| `unix:gid` | ID de grupo del proceso |
| `unix:user` | Nombre de usuario |
| `unix:group` | Nombre del grupo |
| `unix:path` | Ruta del ejecutable |
| `unix:sha256` | Hash SHA256 del binario |

---

## Integración con Kubernetes

### SPIFFE CSI Driver

El SPIFFE CSI Driver monta SVIDs directamente en los filesystems de los Pods sin requerir cambios en la aplicación:

```bash
# Install SPIFFE CSI Driver
helm install spiffe-csi-driver spiffe/spiffe-csi-driver \
  --namespace spiffe-csi-driver \
  --create-namespace \
  --set spire.agentSocketPath=/run/spire/sockets/agent.sock
```

**Uso del CSI Driver en Pods:**

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

**Archivos montados por CSI Driver:**

```
/run/spiffe/
├── svid.pem         # X.509-SVID certificate
├── key.pem          # Private key
├── bundle.pem       # Trust bundle (CA certificates)
└── svid.jwt         # JWT-SVID (if configured)
```

### SPIRE Controller Manager

SPIRE Controller Manager automatiza el registro de workloads usando CRDs de Kubernetes:

```bash
# Controller Manager is included in the main SPIRE Helm chart
# Verify it's running
kubectl -n spire-system get pods -l app.kubernetes.io/name=spire-controller-manager
```

**Recurso personalizado ClusterSPIFFEID:**

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

**Etiquetar Namespaces para registro automático:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: payments
  labels:
    spiffe-enabled: "true"
```

**Ejemplos avanzados de ClusterSPIFFEID:**

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

### Integración con Envoy SDS

SPIRE Agent expone una API SDS (Secret Discovery Service) para proxies basados en Envoy:

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

**Configuración de Envoy usando SPIRE SDS:**

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

## Integración con Service Mesh

### Integración Istio + SPIRE

SPIRE puede reemplazar la CA integrada de Istio (Citadel) para ofrecer garantías más sólidas de identidad de workload:

**Arquitectura:**

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

**Configurar Istio para usar SPIRE:**

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

**Inyección de Sidecar con SPIRE:**

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

### Autenticación mutua Cilium + SPIRE

Cilium puede usar SPIRE para autenticación mutua entre services:

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

**Configuración de Cilium SPIRE:**

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

### Trust Anchors de identidad de Linkerd

Linkerd puede configurarse para confiar en certificados emitidos por SPIRE:

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

## Federación

La federación permite que workloads en diferentes trust domains establezcan confianza mutua. Esto es esencial para la comunicación multi-cluster, multi-cloud y entre organizaciones.

### Establecimiento de confianza federada

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

### Configurar federación

**Configuración de Server A (us-east.example.com):**

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

**Configuración de Server B (eu-west.example.com):**

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

### Entradas de registro federadas

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

**ClusterSPIFFEID con federación:**

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

### Ejemplo de federación multi-cloud

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

## Integración con EKS

### Comparación entre IRSA y SPIFFE

| Característica | IRSA | SPIFFE/SPIRE |
|---------|------|--------------|
| **Alcance** | Solo services de AWS | Universal (cualquier service) |
| **Formato de identidad** | IAM Role ARN | SPIFFE ID (URI) |
| **Tipo de token** | OIDC JWT (AWS STS) | X.509-SVID, JWT-SVID |
| **Límite de confianza** | Una sola cuenta de AWS (o cross-account) | Cualquier trust domain (multi-cloud) |
| **Rotación** | Requiere reinicio de Pod | Automática (sin reinicio) |
| **mTLS** | No compatible | Soporte nativo |
| **Service Mesh** | No integrado | Integración nativa |
| **Caso de uso** | Acceso a AWS API | Autenticación service-to-service |

### Pod Identity frente a SPIRE

| Característica | EKS Pod Identity | SPIRE |
|---------|------------------|-------|
| **Complejidad de configuración** | Baja (gestionado por AWS) | Media (autogestionado) |
| **Cloud Lock-in** | Solo AWS | Cloud agnostic |
| **Identidad personalizada** | No (solo IAM) | Sí (cualquier identidad) |
| **Federación** | IAM cross-account | Cualquier trust domain |
| **On-premises** | No compatible | Totalmente compatible |
| **Hybrid Cloud** | Limitado | Soporte completo |

### Casos de uso híbridos

**Escenario 1: AWS API + Service-to-Service**

Usa IRSA para acceso a AWS API y SPIRE para autenticación service-to-service:

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

**Escenario 2: Cross-Cloud con EKS**

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

### Node Attestation específica para EKS

Para EKS, usa AWS IID attestation para una identidad de node más sólida:

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

## Buenas prácticas

### Nomenclatura de Trust Domain

| Directriz | Ejemplo | Justificación |
|-----------|---------|-----------|
| Usar nombres similares a DNS | `prod.example.com` | Globalmente único, familiar |
| Separación por entorno | `prod.corp.com`, `staging.corp.com` | Evita el acceso cross-env |
| Evitar direcciones IP | Nunca usar IPs | Las IPs cambian, los nombres no |
| Planificar para federación | `aws.corp.com`, `gcp.corp.com` | Configuración multi-cloud más sencilla |

### Ajuste de TTL de SVID

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

**Directrices de TTL:**

| Tipo de workload | TTL recomendado | Justificación |
|---------------|-----------------|-----------|
| Services de larga duración | 1h | Equilibra la sobrecarga de rotación |
| Batch jobs | 5-15m | Coincide con la duración del job |
| API gateways | 30m | La rotación frecuente es aceptable |
| Jobs de CI/CD | 5m | Corta duración, alta seguridad |

### Deployment de alta disponibilidad

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

### Rotación de claves

SPIRE rota automáticamente SVIDs antes de su expiración. Para la rotación de claves CA:

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

### Endurecimiento de seguridad

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

## Solución de problemas

### Problemas comunes

**Problema: Agent no puede conectarse al Server**

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

**Problema: Workload no puede obtener SVID**

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

**Problema: CSI Driver no monta SVIDs**

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

## Resumen y referencias

### Puntos clave

1. **SPIFFE proporciona identidad universal de workload** — Un enfoque basado en estándares que funciona en clouds, clusters y plataformas

2. **SPIRE implementa SPIFFE a escala** — Implementación lista para producción con attestation automatizada y gestión de SVID

3. **Integración sin cambios de código** — El CSI driver y las integraciones con service mesh no requieren cambios en la aplicación

4. **La federación habilita multi-cluster/multi-cloud** — Los trust domains pueden federarse para autenticación entre límites

5. **Complementa la identidad cloud-native** — SPIFFE funciona junto con IRSA/Pod Identity para una gestión de identidad integral

### Guía de decisiones de arquitectura

| Requisito | Recomendación |
|-------------|----------------|
| Solo AWS, AWS APIs | Usar IRSA o Pod Identity |
| Services multi-cloud | Usar SPIFFE/SPIRE |
| Service mesh mTLS | Usar SPIFFE/SPIRE |
| Hybrid cloud | Usar SPIFFE/SPIRE |
| Confianza entre organizaciones | Usar SPIFFE Federation |
| Configuración simple, cluster único | Empezar con cloud-native (IRSA), agregar SPIRE más adelante |

### Referencias

**Documentación oficial:**

- [Especificación SPIFFE](https://spiffe.io/docs/latest/spiffe-about/overview/)
- [Documentación de SPIRE](https://spiffe.io/docs/latest/spire-about/)
- [SPIRE Helm Charts](https://github.com/spiffe/helm-charts-hardened)
- [SPIFFE CSI Driver](https://github.com/spiffe/spiffe-csi)

**Guías de integración:**

- [Integración Istio + SPIRE](https://istio.io/latest/docs/ops/integrations/spire/)
- [Autenticación mutua de Cilium](https://docs.cilium.io/en/stable/network/servicemesh/mutual-authentication/)
- [Integración Envoy SDS](https://www.envoyproxy.io/docs/envoy/latest/configuration/security/secret)

**Recursos de CNCF:**

- [Página del proyecto SPIFFE en CNCF](https://www.cncf.io/projects/spiffe/)
- [Canal de Slack de SPIFFE](https://slack.spiffe.io/)
- [Reuniones de la comunidad SPIFFE](https://github.com/spiffe/spiffe/wiki/Community)
