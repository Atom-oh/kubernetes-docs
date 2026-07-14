# Arquitectura de Linkerd

> **Versiones compatibles**: Linkerd 2.16+
> **Última actualización**: February 22, 2026

## Descripción general

Linkerd sigue una arquitectura de service mesh compuesta por un plano de control y un plano de datos. Este documento proporciona explicaciones detalladas de la función de cada componente, sus interacciones, la jerarquía de certificados y el ciclo de vida del proxy.

## Arquitectura general

```mermaid
graph TB
    subgraph "Control Plane (linkerd namespace)"
        subgraph "Core Components"
            DEST[Destination Controller<br/>Service Discovery<br/>Policy Distribution]
            ID[Identity Controller<br/>Certificate Issuance<br/>CA Management]
            PI[Proxy Injector<br/>Sidecar Injection<br/>Admission Webhook]
        end

        subgraph "Policy Engine"
            POL[Policy Controller<br/>Server/Authorization<br/>Policy Validation]
        end
    end

    subgraph "Data Plane"
        subgraph "Application Pod A"
            APP_A[Application Container]
            PROXY_A[linkerd-proxy<br/>Rust Micro Proxy]
            INIT_A[linkerd-init<br/>iptables Setup]
        end

        subgraph "Application Pod B"
            APP_B[Application Container]
            PROXY_B[linkerd-proxy]
            INIT_B[linkerd-init]
        end
    end

    subgraph "Extensions"
        VIZ[Viz Extension<br/>Metrics/Dashboard]
        JAEGER[Jaeger Extension<br/>Distributed Tracing]
        MC[Multicluster Extension<br/>Cluster Linking]
    end

    %% Control Plane Interactions
    PI -->|Webhook| PROXY_A
    PI -->|Webhook| PROXY_B
    ID -->|Certificate| PROXY_A
    ID -->|Certificate| PROXY_B
    DEST -->|Endpoints| PROXY_A
    DEST -->|Endpoints| PROXY_B
    POL -->|Policy| PROXY_A
    POL -->|Policy| PROXY_B

    %% Data Plane Traffic
    APP_A --> PROXY_A
    PROXY_A -->|mTLS| PROXY_B
    PROXY_B --> APP_B

    %% Extension Interactions
    VIZ -->|Metrics Collection| PROXY_A
    VIZ -->|Metrics Collection| PROXY_B

    classDef control fill:#e1f5fe
    classDef data fill:#f3e5f5
    classDef ext fill:#e8f5e9

    class DEST,ID,PI,POL control
    class APP_A,APP_B,PROXY_A,PROXY_B,INIT_A,INIT_B data
    class VIZ,JAEGER,MC ext
```

## Plano de control

El plano de control se implementa en el namespace `linkerd` y consta de componentes que configuran y gestionan los proxies del plano de datos.

### Destination Controller

El controlador Destination es el componente central responsable del descubrimiento de servicios y la distribución de políticas.

```mermaid
graph LR
    subgraph "Destination Controller"
        API[Destination API<br/>gRPC Server]
        DISC[Service Discovery<br/>Endpoint Lookup]
        PROF[ServiceProfile<br/>Routing Info]
        SPLIT[TrafficSplit<br/>Traffic Distribution]
    end

    subgraph "Kubernetes"
        SVC[Services]
        EP[Endpoints]
        SP[ServiceProfiles]
        TS[TrafficSplits]
    end

    subgraph "Proxies"
        P1[Proxy 1]
        P2[Proxy 2]
    end

    SVC --> DISC
    EP --> DISC
    SP --> PROF
    TS --> SPLIT

    API --> P1
    API --> P2
```

**Funciones principales:**

| Función | Descripción |
|----------|-------------|
| Descubrimiento de servicios | Supervisa los servicios y Endpoints de Kubernetes, y proporciona actualizaciones en tiempo real a los proxies |
| Distribución de políticas | Entrega políticas como ServiceProfile y TrafficSplit a los proxies |
| Información de balanceo de carga | Información de ponderación de Endpoints para el balanceo de carga basado en EWMA |
| Perfiles de servicio | Configuración de reintentos, tiempos de espera y métricas por ruta |

**Operación de la API Destination:**

```go
// Destination API sends updates to proxies via gRPC streaming
// Proxy requests information about target service
service Destination {
    // Get returns update stream for a specific destination
    rpc Get(GetDestination) returns (stream Update);

    // GetProfile returns service profile update stream
    rpc GetProfile(GetDestination) returns (stream DestinationProfile);
}
```

### Identity Controller

El controlador Identity gestiona la emisión y administración de certificados para mTLS.

```mermaid
sequenceDiagram
    participant Proxy as linkerd-proxy
    participant Identity as Identity Controller
    participant CA as Trust Anchor (CA)

    Note over Proxy: Pod starts
    Proxy->>Identity: CSR (Certificate Signing Request)
    Identity->>Identity: Validate ServiceAccount
    Identity->>CA: Certificate signing request
    CA-->>Identity: Signed certificate
    Identity-->>Proxy: Workload certificate

    Note over Proxy: Before certificate expiration
    Proxy->>Identity: Renewal CSR
    Identity-->>Proxy: New certificate
```

**Proceso de emisión de certificados:**

1. El proxy genera una CSR (Certificate Signing Request) al iniciarse.
2. El controlador Identity valida el ServiceAccount del Pod.
3. Firma el certificado con el Trust Anchor (Root CA).
4. Entrega el certificado de workload al proxy.
5. Validez predeterminada de 24 horas y renovación automática.

**Configuración de Identity:**

```yaml
# Identity settings in linkerd-config ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: linkerd-config
  namespace: linkerd
data:
  values: |
    identity:
      issuer:
        # Certificate issuance lifetime (default 24 hours)
        issuanceLifetime: 24h0m0s
        # Clock skew allowance
        clockSkewAllowance: 20s
        # Issuer scheme (kubernetes.io/tls)
        scheme: kubernetes.io/tls
```

### Proxy Injector

El Proxy Injector funciona como un Kubernetes Admission Webhook para inyectar automáticamente sidecars en los Pods.

```mermaid
sequenceDiagram
    participant User as kubectl
    participant API as API Server
    participant PI as Proxy Injector
    participant Pod as Pod

    User->>API: Pod creation request
    API->>PI: Admission Review
    PI->>PI: Check injection conditions
    alt Injection enabled
        PI->>PI: Add linkerd-proxy container
        PI->>PI: Add linkerd-init container
        PI->>PI: Configure volumes/env vars
        PI-->>API: Mutated Pod Spec
    else Injection disabled
        PI-->>API: Original Pod Spec
    end
    API->>Pod: Create Pod
```

**Condiciones de inyección:**

```yaml
# Namespace-level injection enablement
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled

---
# Pod-level injection control
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
  annotations:
    # Enable injection
    linkerd.io/inject: enabled
    # Or disable
    # linkerd.io/inject: disabled
```

**Componentes inyectados:**

| Componente | Función |
|-----------|------|
| `linkerd-init` | Init container, configura reglas de iptables |
| `linkerd-proxy` | Contenedor sidecar, proxy de tráfico |
| Volúmenes | Tokens de identidad, configuración |
| Variables de entorno | Configuración del proxy, direcciones de destino |

### Policy Controller

El Policy Controller gestiona las políticas de autorización de Linkerd.

```yaml
# Server resource - defines inbound traffic
apiVersion: policy.linkerd.io/v1beta2
kind: Server
metadata:
  name: web-http
  namespace: my-app
spec:
  podSelector:
    matchLabels:
      app: web
  port: http
  proxyProtocol: HTTP/1

---
# ServerAuthorization - defines access permissions
apiVersion: policy.linkerd.io/v1beta2
kind: ServerAuthorization
metadata:
  name: web-authz
  namespace: my-app
spec:
  server:
    name: web-http
  client:
    meshTLS:
      serviceAccounts:
        - name: api-gateway
          namespace: my-app
```

## Plano de datos

El plano de datos consta de sidecars `linkerd-proxy` inyectados en los Pods de aplicación.

### linkerd2-proxy

El proxy del plano de datos de Linkerd es un micro-proxy ultraligero escrito en Rust.

```mermaid
graph TB
    subgraph "Pod"
        subgraph "linkerd-proxy"
            IN[Inbound Listener<br/>:4143]
            OUT[Outbound Listener<br/>:4140]
            ADMIN[Admin Server<br/>:4191]

            subgraph "Processing"
                TLS[TLS Termination/Origination]
                LB[Load Balancing<br/>EWMA]
                RETRY[Retries]
                TO[Timeouts]
                CB[Circuit Breaking]
                METRICS[Metrics Collection]
            end
        end

        APP[Application]
    end

    EXT_IN[External Inbound] --> IN
    IN --> TLS
    TLS --> APP

    APP --> OUT
    OUT --> LB
    LB --> TLS
    TLS --> EXT_OUT[External Outbound]

    ADMIN --> METRICS
```

**Características del proxy:**

| Característica | Valor |
|----------------|-------|
| Lenguaje | Rust |
| Uso de memoria | ~10MB |
| Sobrecarga de CPU | Mínima |
| Sobrecarga de latencia | <1ms p99 |
| Protocolos | HTTP/1.1, HTTP/2, gRPC, TCP |
| TLS | TLS 1.3 (rustls) |

**Comparación con Istio Envoy:**

| Característica | linkerd2-proxy | Envoy (Istio) |
|----------------|---------------|---------------|
| Lenguaje | Rust | C++ |
| Memoria | ~10MB | ~50-100MB |
| Tamaño del binario | ~10MB | ~60MB |
| Latencia | <1ms p99 | 2-5ms p99 |
| Complejidad de configuración | Baja (automática) | Alta (xDS) |
| Extensibilidad | Limitada | Wasm, Lua |
| Compatibilidad de protocolos | HTTP, gRPC, TCP | Muy amplia |

### Flujo de tráfico del proxy

```mermaid
sequenceDiagram
    participant Client as Client App
    participant CProxy as Client Proxy<br/>(Outbound)
    participant SProxy as Server Proxy<br/>(Inbound)
    participant Server as Server App

    Client->>CProxy: HTTP Request<br/>(localhost)
    Note over CProxy: iptables redirect
    CProxy->>CProxy: Lookup target service<br/>(Destination API)
    CProxy->>CProxy: Load balancing<br/>(EWMA)
    CProxy->>CProxy: mTLS handshake
    CProxy->>SProxy: Encrypted Request
    SProxy->>SProxy: mTLS verification
    SProxy->>SProxy: Policy check
    SProxy->>Server: HTTP Request
    Server-->>SProxy: HTTP Response
    SProxy-->>CProxy: Encrypted Response
    CProxy-->>Client: HTTP Response
```

### linkerd-init (Init Container)

`linkerd-init` configura reglas de iptables para redirigir el tráfico al proxy.

```bash
# Example iptables rules set by linkerd-init
# Redirect outbound traffic (to port 4140)
iptables -t nat -A OUTPUT -p tcp -j REDIRECT --to-port 4140

# Redirect inbound traffic (to port 4143)
iptables -t nat -A PREROUTING -p tcp -j REDIRECT --to-port 4143

# Exclude proxy's own traffic
iptables -t nat -A OUTPUT -m owner --uid-owner 2102 -j RETURN
```

**Estructura del Pod inyectado:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  annotations:
    linkerd.io/inject: enabled
spec:
  initContainers:
  - name: linkerd-init
    image: cr.l5d.io/linkerd/proxy-init:v2.3.0
    args:
    - --incoming-proxy-port=4143
    - --outgoing-proxy-port=4140
    - --proxy-uid=2102
    securityContext:
      capabilities:
        add:
        - NET_ADMIN
        - NET_RAW

  containers:
  - name: my-app
    image: my-app:latest

  - name: linkerd-proxy
    image: cr.l5d.io/linkerd/proxy:stable-2.16.0
    ports:
    - containerPort: 4143  # Inbound
      name: linkerd-proxy
    - containerPort: 4191  # Admin/Metrics
      name: linkerd-admin
    env:
    - name: LINKERD2_PROXY_LOG
      value: warn,linkerd=info
    - name: LINKERD2_PROXY_DESTINATION_SVC_ADDR
      value: linkerd-dst.linkerd.svc.cluster.local:8086
    - name: LINKERD2_PROXY_IDENTITY_SVC_ADDR
      value: linkerd-identity.linkerd.svc.cluster.local:8080
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
      limits:
        cpu: 1000m
        memory: 250Mi
    readinessProbe:
      httpGet:
        path: /ready
        port: 4191
    livenessProbe:
      httpGet:
        path: /live
        port: 4191
```

## Jerarquía de certificados

Linkerd utiliza una PKI (Public Key Infrastructure) jerárquica para implementar mTLS.

### Estructura de la jerarquía de certificados

```mermaid
graph TB
    subgraph "Certificate Hierarchy"
        TA[Trust Anchor<br/>Root CA<br/>Validity: 10 years]
        II[Identity Issuer<br/>Intermediate CA<br/>Validity: 1 year]
        WC1[Workload Cert 1<br/>Validity: 24 hours]
        WC2[Workload Cert 2<br/>Validity: 24 hours]
        WC3[Workload Cert 3<br/>Validity: 24 hours]
    end

    TA --> II
    II --> WC1
    II --> WC2
    II --> WC3

    style TA fill:#ff9800
    style II fill:#2196f3
    style WC1 fill:#4caf50
    style WC2 fill:#4caf50
    style WC3 fill:#4caf50
```

### Trust Anchor (Root CA)

El Trust Anchor es la raíz de la PKI y la base de confianza para todas las cadenas de certificados.

```bash
# Create Trust Anchor (using step CLI)
step certificate create root.linkerd.cluster.local ca.crt ca.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h  # 10 years

# Verify Trust Anchor
openssl x509 -in ca.crt -text -noout

# Example output:
# Certificate:
#     Data:
#         Version: 3 (0x2)
#         Serial Number: ...
#         Signature Algorithm: ecdsa-with-SHA256
#         Issuer: CN = root.linkerd.cluster.local
#         Validity
#             Not Before: Feb 21 00:00:00 2026 GMT
#             Not After : Feb 21 00:00:00 2036 GMT
#         Subject: CN = root.linkerd.cluster.local
#         ...
#         X509v3 extensions:
#             X509v3 Key Usage: critical
#                 Certificate Sign, CRL Sign
#             X509v3 Basic Constraints: critical
#                 CA:TRUE
```

**Almacenamiento de Trust Anchor:**

```yaml
# Stored as Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: linkerd-identity-trust-roots
  namespace: linkerd
type: Opaque
data:
  ca-bundle.crt: <base64-encoded-ca.crt>
```

### Identity Issuer (Intermediate CA)

El Identity Issuer es la CA intermedia que emite certificados de workload.

```bash
# Create Identity Issuer certificate
step certificate create identity.linkerd.cluster.local issuer.crt issuer.key \
  --profile intermediate-ca \
  --ca ca.crt \
  --ca-key ca.key \
  --no-password \
  --insecure \
  --not-after=8760h  # 1 year

# Verify Issuer certificate
openssl x509 -in issuer.crt -text -noout
```

**Secret de Identity Issuer:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: linkerd-identity-issuer
  namespace: linkerd
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-issuer.crt>
  tls.key: <base64-encoded-issuer.key>
  ca.crt: <base64-encoded-ca.crt>
```

### Certificados de workload

Cada proxy recibe un certificado de workload único.

```mermaid
sequenceDiagram
    participant Proxy as linkerd-proxy
    participant ID as Identity Controller
    participant SA as ServiceAccount

    Note over Proxy: Pod starts
    Proxy->>SA: Obtain ServiceAccount token
    Proxy->>Proxy: Generate CSR (with SPIFFE ID)
    Proxy->>ID: Send CSR + SA token
    ID->>ID: Validate SA token
    ID->>ID: Validate SPIFFE ID
    ID->>ID: Sign certificate with Issuer key
    ID-->>Proxy: Signed certificate (24-hour validity)

    Note over Proxy: After 22 hours (2 hours before expiration)
    Proxy->>ID: Renewal CSR
    ID-->>Proxy: New certificate
```

**Formato de ID SPIFFE:**

```
spiffe://root.linkerd.cluster.local/ns/<namespace>/sa/<service-account>

# Example:
spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service
```

### Rotación de certificados

```yaml
# Certificate lifetime configuration
identity:
  issuer:
    # Workload certificate lifetime (default 24 hours)
    issuanceLifetime: 24h0m0s
    # Clock skew allowance (default 20 seconds)
    clockSkewAllowance: 20s

# Proxy automatically renews certificates before expiration
# By default, renewal starts at 70% of certificate lifetime
```

**Rotación de Trust Anchor:**

```bash
# Create new Trust Anchor
step certificate create root.linkerd.cluster.local ca-new.crt ca-new.key \
  --profile root-ca \
  --no-password \
  --insecure \
  --not-after=87600h

# Create bundle (existing + new)
cat ca.crt ca-new.crt > ca-bundle.crt

# Update ConfigMap
kubectl create configmap linkerd-identity-trust-roots \
  --from-file=ca-bundle.crt=ca-bundle.crt \
  -n linkerd \
  --dry-run=client -o yaml | kubectl apply -f -

# Then restart all proxies to apply new bundle
kubectl rollout restart deploy -n my-app
```

## Detalles de la inyección de sidecar

### Flujo de trabajo de inyección

```mermaid
graph TB
    subgraph "Injection Flow"
        REQ[Pod Creation Request]
        WH[Webhook Call]
        CHK[Check Injection Conditions]
        INJ[Inject Sidecar]
        POD[Create Pod]
    end

    subgraph "Injection Conditions"
        NS[Namespace Annotation]
        POD_ANN[Pod Annotation]
        WL[Workload Type]
    end

    REQ --> WH
    WH --> CHK
    CHK --> NS
    CHK --> POD_ANN
    CHK --> WL
    NS --> INJ
    POD_ANN --> INJ
    WL --> INJ
    INJ --> POD
```

### Anotaciones de inyección

```yaml
# Namespace level
metadata:
  annotations:
    linkerd.io/inject: enabled  # Inject into all Pods

# Pod/Deployment level
metadata:
  annotations:
    # Enable/disable injection
    linkerd.io/inject: enabled|disabled

    # Proxy configuration overrides
    config.linkerd.io/proxy-cpu-request: "100m"
    config.linkerd.io/proxy-memory-request: "64Mi"
    config.linkerd.io/proxy-cpu-limit: "1"
    config.linkerd.io/proxy-memory-limit: "250Mi"

    # Proxy log level
    config.linkerd.io/proxy-log-level: "warn,linkerd=info"

    # Skip ports (bypass proxy)
    config.linkerd.io/skip-inbound-ports: "25,587"
    config.linkerd.io/skip-outbound-ports: "25,587"

    # Opaque ports (bypass protocol detection)
    config.linkerd.io/opaque-ports: "3306,5432"
```

### Readiness/Liveness del proxy

```yaml
# Proxy health check endpoints
livenessProbe:
  httpGet:
    path: /live
    port: 4191
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 4191
  initialDelaySeconds: 2
  periodSeconds: 10
```

## Comunicación entre componentes

```mermaid
graph TB
    subgraph "Control Plane"
        DEST[Destination<br/>:8086]
        ID[Identity<br/>:8080]
        PI[Proxy Injector<br/>:8443]
        POL[Policy<br/>:8090]
    end

    subgraph "Data Plane"
        P1[Proxy 1]
        P2[Proxy 2]
    end

    subgraph "Kubernetes"
        API[API Server]
        WH[Webhook Config]
    end

    P1 -->|gRPC| DEST
    P2 -->|gRPC| DEST
    P1 -->|gRPC| ID
    P2 -->|gRPC| ID
    P1 -->|gRPC| POL
    P2 -->|gRPC| POL

    API -->|Admission| PI
    WH --> PI

    DEST --> API
    ID --> API
    POL --> API
```

**Resumen de puertos:**

| Componente | Puerto | Protocolo | Propósito |
|-----------|------|----------|---------|
| Destination | 8086 | gRPC | API de descubrimiento de servicios |
| Identity | 8080 | gRPC | API de emisión de certificados |
| Policy | 8090 | gRPC | API de políticas |
| Proxy Injector | 8443 | HTTPS | Admission Webhook |
| Proxy (entrante) | 4143 | HTTP/gRPC | Tráfico entrante |
| Proxy (saliente) | 4140 | HTTP/gRPC | Tráfico saliente |
| Proxy (Admin) | 4191 | HTTP | Métricas, comprobaciones de estado |

## Comparación con la arquitectura de Istio

### Comparación del plano de control

```mermaid
graph TB
    subgraph "Linkerd Control Plane"
        L_DEST[Destination]
        L_ID[Identity]
        L_PI[Proxy Injector]
    end

    subgraph "Istio Control Plane"
        ISTIOD[istiod<br/>Pilot + Citadel + Galley]
    end

    subgraph "Linkerd Data Plane"
        L_PROXY[linkerd-proxy<br/>Rust, ~10MB]
    end

    subgraph "Istio Data Plane"
        ENVOY[Envoy<br/>C++, ~50-100MB]
    end
```

| Característica | Linkerd | Istio |
|----------------|---------|-------|
| Plano de control | Distribuido (3 componentes) | Unificado (istiod) |
| Proxy | linkerd2-proxy (Rust) | Envoy (C++) |
| Protocolo de configuración | gRPC personalizado | xDS (complejo) |
| Número de CRD | ~10 | ~50+ |
| Curva de aprendizaje | Suave | Pronunciada |
| Uso de recursos | Bajo | Alto |
| Extensibilidad | Limitada | Wasm, Lua |

### Comparación de proxies

```yaml
# Linkerd Proxy Resources (typical)
resources:
  requests:
    cpu: 100m
    memory: 64Mi
  limits:
    cpu: 1000m
    memory: 250Mi

# Envoy Proxy Resources (typical)
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 2000m
    memory: 1Gi
```

## Próximos pasos

- [Gestión del tráfico](./03-traffic-management.md): ServiceProfile y división de tráfico
- [Seguridad](./04-security.md): mTLS y políticas de autorización
- [Observabilidad](./05-observability.md): Métricas y paneles

## Referencias

- [Arquitectura de Linkerd](https://linkerd.io/2/reference/architecture/)
- [linkerd2-proxy GitHub](https://github.com/linkerd/linkerd2-proxy)
- [Identidad de Linkerd](https://linkerd.io/2/features/automatic-mtls/)
- [Inyección de proxy](https://linkerd.io/2/features/proxy-injection/)
