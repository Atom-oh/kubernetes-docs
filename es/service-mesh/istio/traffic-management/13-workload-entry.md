# WorkloadEntry

> **Versión compatible**: Istio 1.28+
> **Última actualización**: February 19, 2026

WorkloadEntry es un recurso para registrar Máquinas Virtuales (VM) o servidores bare-metal en la malla de servicios de Istio. Esto permite que las cargas de trabajo fuera de Kubernetes utilicen las funciones de gestión del tráfico, seguridad y observabilidad de la malla.

## Tabla de contenidos

1. [Descripción general](#overview)
2. [WorkloadEntry frente a Kubernetes Pod](#workloadentry-vs-kubernetes-pod)
3. [Arquitectura](#architecture)
4. [Uso básico](#basic-usage)
5. [Integración con ServiceEntry](#serviceentry-integration)
6. [Guía práctica de registro de VM](#vm-registration-practical-guide)
7. [Configuración de seguridad (mTLS)](#security-settings-mtls)
8. [Comprobaciones de estado y monitorización](#health-checks-and-monitoring)
9. [Configuración avanzada](#advanced-configuration)
10. [Solución de problemas](#troubleshooting)
11. [Prácticas recomendadas](#best-practices)

## Descripción general

### ¿Qué es WorkloadEntry?

WorkloadEntry es una Custom Resource Definition (CRD) de Istio que registra en la malla de servicios de Istio cargas de trabajo (VM, bare-metal) externas a la malla.

### Escenarios de uso

```mermaid
flowchart TB
    subgraph Legacy[Legacy Environment]
        VM1[VM<br/>Legacy App]
        VM2[VM<br/>Database]
        BM[Bare Metal<br/>High-Performance Server]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod1[Pod]
            App1[New App]
            Envoy1[Envoy]
        end

        subgraph Pod2[Pod]
            App2[Microservice]
            Envoy2[Envoy]
        end
    end

    subgraph Istiod[Control Plane]
        CP[istiod]
    end

    VM1 -.->|Mesh Registration| CP
    VM2 -.->|Mesh Registration| CP
    BM -.->|Mesh Registration| CP

    CP -.->|Config Delivery| Envoy1
    CP -.->|Config Delivery| Envoy2

    App1 <-->|mTLS| VM1
    App2 <-->|mTLS| VM2

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,BM vm;
    class App1,App2 k8sApp;
    class Envoy1,Envoy2 proxy;
    class CP controlPlane;
```

**Casos de uso principales**:
1. **Migración gradual**: Migrar incrementalmente aplicaciones heredadas a Kubernetes
2. **Arquitectura híbrida**: Operar VM y contenedores simultáneamente
3. **Integración de bases de datos**: Incluir bases de datos externas en la malla
4. **Cargas de trabajo de alto rendimiento**: Utilizar hardware especializado, como servidores GPU

## WorkloadEntry frente a Kubernetes Pod

### Tabla comparativa

| Característica | Kubernetes Pod | WorkloadEntry (VM) |
|----------------|---------------|-------------------|
| **Ubicación del Deployment** | Dentro del clúster | Fuera del clúster |
| **Inyección de Envoy** | Automática (sidecar) | Instalación manual |
| **Descubrimiento de servicios** | Automático (Service) | Manual (WorkloadEntry) |
| **Gestión de IP** | Kubernetes CNI | Especificación manual |
| **mTLS** | Automático | Automático (se requiere implementar el certificado) |
| **Comprobaciones de estado** | Automáticas (Liveness/Readiness) | Configuración manual |
| **Escalado** | HPA | Manual |
| **Complejidad operativa** | Baja | Alta |
| **Escenario de uso** | Aplicaciones cloud-native | Aplicaciones heredadas, hardware especializado |

### Comparación del flujo de tráfico

```mermaid
flowchart LR
    subgraph PodFlow[Kubernetes Pod Flow]
        Client1[Client]
        K8sService[Service<br/>Auto Discovery]
        K8sPod[Pod<br/>Auto Envoy Injection]

        Client1 -->|1\. Request| K8sService
        K8sService -->|2\. Routing| K8sPod
    end

    subgraph VMFlow[WorkloadEntry Flow]
        Client2[Client]
        ServiceEntry[ServiceEntry<br/>Manual Registration]
        WorkloadEntry[WorkloadEntry<br/>VM + Envoy]

        Client2 -->|1\. Request| ServiceEntry
        ServiceEntry -->|2\. Routing| WorkloadEntry
    end

    %% Style definitions
    classDef client fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;
    classDef k8s fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Client1,Client2 client;
    class K8sService,K8sPod k8s;
    class ServiceEntry,WorkloadEntry vm;
```

## Arquitectura

### Arquitectura de carga de trabajo en VM

```mermaid
flowchart TB
    subgraph VM[Virtual Machine]
        App[Legacy<br/>Application<br/>Port 8080]
        EnvoyVM[Envoy Sidecar<br/>Manual Install]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod[Pod]
            PodApp[Application]
            EnvoyPod[Envoy<br/>Auto Injection]
        end

        Istiod[istiod<br/>Control Plane]
    end

    App <-->|Local Communication| EnvoyVM
    PodApp <-->|Local Communication| EnvoyPod

    EnvoyVM <-->|mTLS Traffic| EnvoyPod

    Istiod -.->|xDS Config<br/>ServiceEntry<br/>DestinationRule| EnvoyVM
    Istiod -.->|xDS Config| EnvoyPod
    Istiod -.->|Certificate Issuance<br/>Service Account| EnvoyVM

    %% Style definitions
    classDef vmApp fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App vmApp;
    class PodApp k8sApp;
    class EnvoyVM,EnvoyPod proxy;
    class Istiod controlPlane;
```

### Componentes clave

1. **WorkloadEntry**: Registro de información de VM (IP, puertos, etiquetas)
2. **ServiceEntry**: Definición de Service y referencia a WorkloadEntry
3. **Envoy Proxy**: Sidecar instalado manualmente en la VM
4. **istiod**: Implementación de configuración y gestión de certificados
5. **Service Account**: Autenticación de identidad de VM

## Uso básico

### Definición del recurso WorkloadEntry

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm-1
  namespace: production
spec:
  # VM's IP address
  address: 192.168.1.100

  # Labels for service selection
  labels:
    app: legacy-api
    version: v1.0
    tier: backend

  # Service account for mTLS authentication
  serviceAccount: legacy-api-sa

  # Ports to expose
  ports:
    http: 8080
    https: 8443
    metrics: 9090

  # Locality information (optional)
  locality: us-west-2/us-west-2a

  # Weight (for load balancing, optional)
  weight: 100

  # Network (multi-network environment, optional)
  network: vm-network
```

### Descripción de campos obligatorios

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| **address** | Dirección IP de la VM (obligatorio) | `192.168.1.100` |
| **labels** | Etiquetas para la coincidencia con ServiceEntry | `app: legacy-api` |
| **serviceAccount** | SA para autenticación mTLS | `legacy-api-sa` |
| **ports** | Mapa de puertos que se expondrán | `http: 8080` |

### Registro de varias VM

```yaml
# VM 1
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-1
  namespace: production
spec:
  address: 192.168.1.101
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
  ports:
    http: 8080
---
# VM 2
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-2
  namespace: production
spec:
  address: 192.168.1.102
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
  ports:
    http: 8080
---
# VM 3 (different version)
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-3
  namespace: production
spec:
  address: 192.168.1.103
  labels:
    app: api-service
    version: v2  # New version
  serviceAccount: api-sa
  ports:
    http: 8080
```

## Integración con ServiceEntry

WorkloadEntry siempre se utiliza junto con ServiceEntry.

### Patrón básico de integración

```yaml
# 1. Define service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-api
  namespace: production
spec:
  hosts:
  - api.legacy.internal
  addresses:
  - 240.240.1.1  # Virtual IP
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: legacy-api  # Match with WorkloadEntry labels
---
# 2. Register VM with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm-1
  namespace: production
spec:
  address: 192.168.1.100
  labels:
    app: legacy-api  # Match with ServiceEntry
    version: v1
  serviceAccount: legacy-api-sa
  ports:
    http: 8080
```

### Flujo de operación

```mermaid
sequenceDiagram
    autonumber
    participant Client as Kubernetes<br/>Pod
    participant DNS as Istio DNS
    participant Envoy as Envoy Proxy
    participant VM as VM<br/>WorkloadEntry

    Client->>DNS: Lookup api.legacy.internal
    DNS->>Client: 240.240.1.1 (Virtual IP)

    Client->>Envoy: HTTP Request<br/>240.240.1.1:8080
    Envoy->>Envoy: Lookup ServiceEntry<br/>workloadSelector matching
    Envoy->>Envoy: Find WorkloadEntry<br/>192.168.1.100

    Envoy->>VM: mTLS Connection<br/>192.168.1.100:8080
    VM->>Envoy: Response
    Envoy->>Client: Response
```

### Balanceo de carga

Balanceo de carga automático cuando existen varios WorkloadEntry:

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: database-cluster
spec:
  hosts:
  - db.cluster.internal
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
      tier: database
---
# Primary DB
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-primary
spec:
  address: 10.0.1.100
  labels:
    app: postgres
    tier: database
    role: primary
  weight: 100  # Weight
---
# Replica DB 1
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-replica-1
spec:
  address: 10.0.1.101
  labels:
    app: postgres
    tier: database
    role: replica
  weight: 50
---
# Replica DB 2
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-replica-2
spec:
  address: 10.0.1.102
  labels:
    app: postgres
    tier: database
    role: replica
  weight: 50
```

## Guía práctica de registro de VM

### Requisitos previos

1. **Requisitos de la VM**:
   - Red: Puede comunicarse con el clúster de Kubernetes
   - SO: Linux (se recomienda Ubuntu 20.04+)
   - Puertos: Puertos de Envoy abiertos (15012, 15017, etc.)

2. **Preparación de Kubernetes**:
   - Instalación de Istio completada
   - Crear un namespace para el uso de VM
   - Crear un ServiceAccount

### Paso 1: Crear ServiceAccount

```bash
# Create namespace
kubectl create namespace vm-workloads

# Create ServiceAccount
kubectl create serviceaccount vm-postgres-sa -n vm-workloads

# (Optional) RBAC setup
kubectl create role vm-postgres-role \
  --verb=get,list,watch \
  --resource=configmaps,secrets \
  -n vm-workloads

kubectl create rolebinding vm-postgres-binding \
  --role=vm-postgres-role \
  --serviceaccount=vm-workloads:vm-postgres-sa \
  -n vm-workloads
```

### Paso 2: Crear WorkloadGroup (opcional)

WorkloadGroup sirve como plantilla para varios WorkloadEntry:

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadGroup
metadata:
  name: postgres-vms
  namespace: vm-workloads
spec:
  metadata:
    labels:
      app: postgres
      version: v14
  template:
    serviceAccount: vm-postgres-sa
    network: vm-network
    ports:
      postgresql: 5432
```

### Paso 3: Instalar Envoy en la VM

#### Generar script de instalación automática

```bash
# Generate VM registration files with istioctl
istioctl x workload entry configure \
  -f workloadgroup.yaml \
  -o vm-postgres-1 \
  --clusterID Kubernetes \
  --autoregister

# Generated files:
# - cluster.env: Cluster information
# - istio-token: Authentication token
# - mesh.yaml: Mesh configuration
# - root-cert.pem: Root certificate
# - hosts: /etc/hosts entries
```

#### Ejecutar la instalación en la VM

```bash
# Connect to VM
ssh user@192.168.1.100

# Copy files (using SCP)
scp -r vm-postgres-1/* user@192.168.1.100:/tmp/

# Install Envoy on VM
sudo apt-get update
sudo apt-get install -y curl

# Install Istio sidecar
curl -LO https://storage.googleapis.com/istio-release/releases/1.28.0/deb/istio-sidecar.deb
sudo dpkg -i istio-sidecar.deb

# Place configuration files
sudo mkdir -p /etc/certs
sudo cp /tmp/root-cert.pem /etc/certs/
sudo cp /tmp/istio-token /var/run/secrets/tokens/
sudo cp /tmp/cluster.env /var/lib/istio/envoy/
sudo cp /tmp/mesh.yaml /etc/istio/config/mesh

# Start Envoy
sudo systemctl start istio
sudo systemctl enable istio

# Check status
sudo systemctl status istio
```

### Paso 4: Registrar WorkloadEntry

Si el registro automático está habilitado, se crea automáticamente cuando se inicia Envoy. Registro manual:

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: vm-workloads
spec:
  address: 192.168.1.100
  labels:
    app: postgres
    version: v14
  serviceAccount: vm-postgres-sa
  ports:
    postgresql: 5432
```

```bash
kubectl apply -f workloadentry.yaml
```

### Paso 5: Crear ServiceEntry

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: postgres-service
  namespace: vm-workloads
spec:
  hosts:
  - postgres.vm.internal
  addresses:
  - 240.240.2.1
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
```

```bash
kubectl apply -f serviceentry.yaml
```

### Paso 6: Probar la conexión

```bash
# Create test pod
kubectl run -it --rm debug \
  --image=postgres:14 \
  --restart=Never \
  --namespace=vm-workloads \
  -- psql -h postgres.vm.internal -U dbuser -d mydb

# On successful connection:
# Password for user dbuser:
# psql (14.x)
# Type "help" for help.
# mydb=#
```

## Configuración de seguridad (mTLS)

### Habilitación automática de mTLS

WorkloadEntry admite mTLS automáticamente:

```yaml
# Force mTLS with PeerAuthentication
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: vm-workloads
spec:
  mtls:
    mode: STRICT  # mTLS required for both VM and pod
```

### Verificación de identidad de la VM

```bash
# Check certificates on VM
sudo ls -la /etc/certs/
# cert-chain.pem: Certificate chain
# key.pem: Private key
# root-cert.pem: Root CA

# Check certificate contents
sudo openssl x509 -in /etc/certs/cert-chain.pem -text -noout

# Check Subject Alternative Name (SAN):
# spiffe://cluster.local/ns/vm-workloads/sa/vm-postgres-sa
```

### Control de acceso (AuthorizationPolicy)

```yaml
# PostgreSQL access control
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: postgres-access
  namespace: vm-workloads
spec:
  selector:
    matchLabels:
      app: postgres  # WorkloadEntry labels
  action: ALLOW
  rules:
  # Allow only API service access
  - from:
    - source:
        principals:
        - cluster.local/ns/production/sa/api-service-sa
    to:
    - operation:
        ports: ["5432"]
        methods: ["*"]

  # Allow monitoring service access
  - from:
    - source:
        principals:
        - cluster.local/ns/istio-system/sa/prometheus
    to:
    - operation:
        ports: ["9187"]  # postgres_exporter
```

### Verificación de mTLS

```bash
# Test connection from pod to VM
kubectl exec -it <pod-name> -n production -- \
  curl -v --cacert /etc/certs/root-cert.pem \
  --cert /etc/certs/cert-chain.pem \
  --key /etc/certs/key.pem \
  https://postgres.vm.internal:5432

# Verify mTLS with Envoy stats
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats | grep ssl

# Example output:
# listener.0.0.0.0_15006.ssl.connection_error: 0
# listener.0.0.0.0_15006.ssl.handshake: 1234
```

## Comprobaciones de estado y monitorización

### Configuración de comprobaciones de estado

WorkloadEntry no admite comprobaciones de estado automáticas, por lo que se requiere configuración manual:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: postgres-healthcheck
  namespace: vm-workloads
spec:
  host: postgres.vm.internal
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
    outlierDetection:
      consecutiveErrors: 5  # Exclude after 5 consecutive failures
      interval: 30s         # Check every 30 seconds
      baseEjectionTime: 30s # Exclude for 30 seconds
      maxEjectionPercent: 50 # Exclude up to 50%
      minHealthPercent: 50   # Maintain at least 50%
```

### Endpoint de comprobación de estado de VM

Agregue un endpoint de comprobación de estado a la aplicación de su VM:

```python
# Python Flask example
from flask import Flask, jsonify
import psycopg2

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    try:
        # Verify database connection
        conn = psycopg2.connect("dbname=mydb user=dbuser")
        conn.close()
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Recopilación de métricas de Prometheus

```yaml
# Collect VM metrics with ServiceMonitor
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-vm-metrics
  namespace: vm-workloads
spec:
  selector:
    matchLabels:
      app: postgres
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### Consultas del dashboard de Grafana

```promql
# VM workload request count
sum(rate(istio_requests_total{destination_workload="postgres-vm-1"}[5m]))

# VM workload error rate
sum(rate(istio_requests_total{destination_workload="postgres-vm-1",response_code="500"}[5m]))
/
sum(rate(istio_requests_total{destination_workload="postgres-vm-1"}[5m]))
* 100

# VM workload latency (P99)
histogram_quantile(0.99,
  sum(rate(istio_request_duration_milliseconds_bucket{destination_workload="postgres-vm-1"}[5m])) by (le)
)
```

## Configuración avanzada

### Entorno de varias redes

Registre VM en redes diferentes:

```yaml
# VM in Network A
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-network-a
spec:
  address: 192.168.1.100
  labels:
    app: api-service
  serviceAccount: api-sa
  network: network-a
  ports:
    http: 8080
---
# VM in Network B
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-network-b
spec:
  address: 10.0.1.100
  labels:
    app: api-service
  serviceAccount: api-sa
  network: network-b
  ports:
    http: 8080
```

### Balanceo de carga según la localidad

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-us-west
spec:
  address: 192.168.1.100
  labels:
    app: api-service
  locality: us-west/us-west-2/us-west-2a
  weight: 100
---
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-us-east
spec:
  address: 10.0.1.100
  labels:
    app: api-service
  locality: us-east/us-east-1/us-east-1a
  weight: 100
---
# Locality-aware routing with DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-locality-lb
spec:
  host: api.service.internal
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/*
          to:
            "us-west/*": 80
            "us-east/*": 20
        - from: us-east/*
          to:
            "us-east/*": 80
            "us-west/*": 20
```

### Despliegue canary

El despliegue canary también se puede aplicar a WorkloadEntry:

```yaml
# v1 version VM
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-v1
spec:
  address: 192.168.1.100
  labels:
    app: api-service
    version: v1
  serviceAccount: api-sa
---
# v2 version VM (Canary)
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: api-vm-v2
spec:
  address: 192.168.1.101
  labels:
    app: api-service
    version: v2
  serviceAccount: api-sa
---
# Traffic splitting with VirtualService
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-canary
spec:
  hosts:
  - api.service.internal
  http:
  - route:
    - destination:
        host: api.service.internal
        subset: v1
      weight: 90
    - destination:
        host: api.service.internal
        subset: v2
      weight: 10
---
# Define subsets with DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-service-subsets
spec:
  host: api.service.internal
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## Solución de problemas

### WorkloadEntry no registrado

**Síntoma**: Recurso visible en `kubectl get workloadentry`, pero el tráfico no se enruta

**Verificación**:

```bash
# 1. Check WorkloadEntry status
kubectl get workloadentry -n vm-workloads -o yaml

# 2. Check ServiceEntry's workloadSelector
kubectl get serviceentry -n vm-workloads -o yaml | grep -A 5 workloadSelector

# 3. Verify label matching
# WorkloadEntry labels:
#   app: postgres
# ServiceEntry workloadSelector:
#   labels:
#     app: postgres  # Must match

# 4. Check Envoy configuration
istioctl proxy-config endpoints <pod-name> -n production

# Output should include WorkloadEntry's IP:
# ENDPOINT            STATUS      CLUSTER
# 192.168.1.100:5432  HEALTHY     outbound|5432||postgres.vm.internal
```

**Resolución**:

```yaml
# Modify labels to match exactly
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
spec:
  labels:
    app: postgres  # Must be identical to ServiceEntry
    version: v14
```

### Fallo de conexión mTLS en la VM

**Síntoma**: `connection refused` o `TLS handshake failed`

**Verificación**:

```bash
# Check Envoy logs on VM
sudo journalctl -u istio -f | grep -i tls

# Check certificates
sudo ls -la /etc/certs/
sudo openssl x509 -in /etc/certs/cert-chain.pem -text -noout

# Check certificate expiration
sudo openssl x509 -in /etc/certs/cert-chain.pem -noout -dates

# Check ServiceAccount token
sudo ls -la /var/run/secrets/tokens/
sudo cat /var/run/secrets/tokens/istio-token
```

**Resolución**:

```bash
# Reissue certificates
istioctl x workload entry configure \
  -f workloadgroup.yaml \
  -o vm-postgres-1 \
  --clusterID Kubernetes \
  --autoregister

# Copy to VM and restart Envoy
scp -r vm-postgres-1/* user@192.168.1.100:/tmp/
ssh user@192.168.1.100 "sudo cp /tmp/root-cert.pem /etc/certs/ && sudo systemctl restart istio"
```

### El tráfico no llega debido a un fallo de comprobación de estado

**Síntoma**: Envoy marca WorkloadEntry como `UNHEALTHY`

**Verificación**:

```bash
# Check Envoy endpoint status
istioctl proxy-config endpoints <pod-name> -n production | grep postgres

# Output:
# 192.168.1.100:5432  UNHEALTHY  outbound|5432||postgres.vm.internal

# Check DestinationRule's outlierDetection
kubectl get destinationrule -n vm-workloads -o yaml
```

**Resolución**:

```yaml
# Adjust OutlierDetection settings
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: postgres-healthcheck
spec:
  host: postgres.vm.internal
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 10     # More lenient
      interval: 60s             # Increase check interval
      baseEjectionTime: 60s
      maxEjectionPercent: 100   # Prevent all from being excluded
```

### Fallo de búsqueda DNS

**Síntoma**: La búsqueda de `postgres.vm.internal` falla desde el pod

**Verificación**:

```bash
# Check ServiceEntry
kubectl get serviceentry -n vm-workloads

# DNS lookup test
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup postgres.vm.internal

# Check Istio DNS Proxy enablement
kubectl get pod <pod-name> -o yaml | grep ISTIO_META_DNS_CAPTURE
```

**Resolución**:

```yaml
# Add addresses to ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: postgres-service
spec:
  hosts:
  - postgres.vm.internal
  addresses:
  - 240.240.2.1  # Specify virtual IP
  ports:
  - number: 5432
    name: postgresql
    protocol: TCP
  location: MESH_INTERNAL
  resolution: STATIC
  workloadSelector:
    labels:
      app: postgres
```

## Prácticas recomendadas

### 1. Convenciones de nomenclatura

```yaml
# WorkloadEntry name: <app>-<role>-<id>
name: postgres-primary-1
name: postgres-replica-2
name: api-backend-vm-3

# ServiceEntry name: <app>-service
name: postgres-service
name: api-service

# ServiceAccount name: <app>-sa
name: postgres-sa
name: api-sa
```

### 2. Estrategia de etiquetas

```yaml
spec:
  labels:
    # Required labels
    app: postgres          # Application name
    version: v14           # Version

    # Optional labels
    tier: database         # Tier (frontend, backend, database)
    role: primary          # Role (primary, replica, canary)
    environment: production # Environment
    team: platform         # Team
```

### 3. Gestión de ServiceAccount

```bash
# Separate ServiceAccount by namespace
kubectl create sa db-sa -n databases
kubectl create sa api-sa -n applications
kubectl create sa cache-sa -n middleware

# Principle of least privilege
kubectl create role db-limited \
  --verb=get \
  --resource=configmaps \
  -n databases
```

### 4. Monitorización y alertas

```yaml
# Alert setup with PrometheusRule
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: workloadentry-alerts
spec:
  groups:
  - name: workloadentry
    rules:
    - alert: WorkloadEntryDown
      expr: up{job="workloadentry-postgres"} == 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "WorkloadEntry {{ $labels.instance }} is down"

    - alert: WorkloadEntryHighErrorRate
      expr: |
        rate(istio_requests_total{
          destination_workload=~".*-vm-.*",
          response_code="500"
        }[5m]) > 0.05
      for: 10m
      labels:
        severity: warning
```

### 5. Documentación

Mantenga documentación para cada WorkloadEntry:

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-primary-1
  annotations:
    description: "Primary PostgreSQL database for production"
    owner: "platform-team@example.com"
    provisioned-date: "2025-11-26"
    os: "Ubuntu 22.04 LTS"
    location: "us-west-2a"
    runbook: "https://wiki.example.com/postgres-vm-runbook"
spec:
  address: 192.168.1.100
  labels:
    app: postgres
    version: v14
```

### 6. Copia de seguridad y recuperación ante desastres

```bash
# Backup WorkloadEntry
kubectl get workloadentry -n vm-workloads -o yaml > workloadentries-backup.yaml

# Backup ServiceEntry
kubectl get serviceentry -n vm-workloads -o yaml > serviceentries-backup.yaml

# Restore
kubectl apply -f workloadentries-backup.yaml
kubectl apply -f serviceentries-backup.yaml
```

### 7. Estrategia de migración gradual

```mermaid
flowchart TD
    Phase1[Phase 1:<br/>VM Mesh Registration] --> Phase2[Phase 2:<br/>Traffic Splitting]
    Phase2 --> Phase3[Phase 3:<br/>Kubernetes Deployment]
    Phase3 --> Phase4[Phase 4:<br/>Traffic Transition]
    Phase4 --> Phase5[Phase 5:<br/>VM Removal]

    %% Style definitions
    classDef phase fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class Phase1,Phase2,Phase3,Phase4,Phase5 phase;
```

**Fase 1: Registro de VM en la malla**
```yaml
# Register WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-api-vm
spec:
  address: 192.168.1.100
  labels:
    app: api
    version: legacy
```

**Fase 2: División de tráfico (100 % VM)**
```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-migration
spec:
  hosts:
  - api.internal
  http:
  - route:
    - destination:
        host: api.internal
        subset: legacy
      weight: 100
```

**Fase 3: Kubernetes Deployment**
```bash
kubectl apply -f kubernetes-deployment.yaml
```

**Fase 4: Transición gradual del tráfico**
```yaml
# 10% Kubernetes
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-migration
spec:
  http:
  - route:
    - destination:
        subset: legacy  # VM
      weight: 90
    - destination:
        subset: k8s     # Kubernetes
      weight: 10
```

**Fase 5: Eliminación de VM**
```bash
# After transitioning 100% traffic to Kubernetes
kubectl delete workloadentry legacy-api-vm -n vm-workloads
```

## Referencias

### Documentación oficial
- [Referencia de WorkloadEntry](https://istio.io/latest/docs/reference/config/networking/workload-entry/)
- [Referencia de WorkloadGroup](https://istio.io/latest/docs/reference/config/networking/workload-group/)
- [Instalación de máquina virtual](https://istio.io/latest/docs/setup/install/virtual-machine/)

### Documentos relacionados
- [Conceptos básicos: registro de cargas de trabajo de VM](../02-basic-concepts.md#vm-workload-registration)
- [ServiceEntry](12-service-entry.md)
- [Control de Egress](11-egress-control.md)
- [Seguridad: mTLS](../security/01-mtls.md)

### Recursos adicionales
- [Guía de integración de VM de Istio](https://istio.io/latest/blog/2020/workload-entry/)
- [Documentación de Envoy Proxy](https://www.envoyproxy.io/docs/envoy/latest/)
