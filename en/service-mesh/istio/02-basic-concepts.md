# Basic Concepts

This document explains Istio's core concepts and architecture. Understanding these basic concepts is important for effectively using Istio.

## Table of Contents

1. [Background and History](02-basic-concepts.md#background-and-history)
2. [Why Istio?](02-basic-concepts.md#why-istio)
3. [Istio Architecture](02-basic-concepts.md#istio-architecture)
4. [Deployment Modes: Sidecar vs Ambient](02-basic-concepts.md#deployment-modes-sidecar-vs-ambient)
5. [Core Resources](02-basic-concepts.md#core-resources)
6. [Traffic Management Concepts](02-basic-concepts.md#traffic-management-concepts)
7. [Security Concepts](02-basic-concepts.md#security-concepts)
8. [Observability Concepts](02-basic-concepts.md#observability-concepts)
9. [Namespaces and Service Mesh](02-basic-concepts.md#namespaces-and-service-mesh)
10. [Next Steps](02-basic-concepts.md#next-steps)

## Background and History

### The Birth of Service Mesh

#### Microservices Challenges

In the early 2010s, companies began breaking down monolithic applications into microservices.

```mermaid
flowchart TB
    subgraph Before[Monolithic Era]
        M[Monolithic<br/>Application]
        M -->|Single process| M
    end

    subgraph After[Microservices Era]
        S1[Service A]
        S2[Service B]
        S3[Service C]
        S4[Service D]
        S5[Service E]

        S1 --> S2
        S1 --> S3
        S2 --> S4
        S3 --> S4
        S4 --> S5
    end

    Before -.->|Transition| After

    %% Style definitions
    classDef monolith fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef micro fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class M monolith;
    class S1,S2,S3,S4,S5 micro;
```

**New Problems**:

| Problem                         | Description                                  | Impact                         |
| ------------------------------- | -------------------------------------------- | ------------------------------ |
| **Inter-service Communication** | Increased network calls                      | Latency, failure propagation   |
| **Observability**               | Need for distributed tracing                 | Difficult debugging            |
| **Security**                    | Service-to-service authentication/encryption | mTLS implementation complexity |
| **Traffic Control**             | Canary deployments, A/B testing              | Application code modifications |
| **Failure Handling**            | Circuit Breaker, Retry                       | Implementation per service     |

#### Early Solution: Libraries

**Problems**:

* Need to develop libraries for each language (Hystrix for Java, separate library for Go...)
* Tightly coupled to application code
* Requires redeployment of all services for updates
* Complex version management

```mermaid
flowchart LR
    subgraph App1[Java Service]
        J[Application Code]
        H[Hystrix<br/>Netflix OSS]
    end

    subgraph App2[Go Service]
        G[Application Code]
        L[Go Library]
    end

    subgraph App3[Python Service]
        P[Application Code]
        R[Requests + Retry]
    end

    J --- H
    G --- L
    P --- R

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef lib fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class J,G,P app;
    class H,L,R lib;
```

**Service Mesh Idea**: Move networking logic out of the application to an infrastructure layer

### The Birth of Envoy Proxy

#### Lyft's Problem

**In 2015, Lyft** was experiencing the following problems:

* Operating 200+ microservices
* Various languages and frameworks (Python, Go, Java, etc.)
* Existing proxies (HAProxy, NGINX) were insufficient
  * Difficult dynamic configuration changes
  * Lack of observability
  * Limited advanced routing features

#### Matt Klein and Envoy

**Matt Klein** (Lyft engineer) open-sourced Envoy in 2016.

**Problems Envoy Solved**:

```mermaid
flowchart TB
    subgraph Problems[Existing Proxy Problems]
        P1[Static configuration<br/>File-based]
        P2[Limited<br/>metrics]
        P3[Complex<br/>restart]
        P4[Simple<br/>routing]
    end

    subgraph Solutions[Envoy's Solutions]
        S1[Dynamic API<br/>xDS Protocol]
        S2[Rich<br/>statistics/tracing]
        S3[Hot Restart<br/>Zero downtime]
        S4[Advanced L7<br/>routing]
    end

    P1 -.->|Solved| S1
    P2 -.->|Solved| S2
    P3 -.->|Solved| S3
    P4 -.->|Solved| S4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef solution fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class S1,S2,S3,S4 solution;
```

**Key Features of Envoy**:

1. **Out-of-process Architecture**: Separate process from application
2. **xDS APIs**: Dynamic configuration updates
3. **L7 Proxy**: HTTP/2, gRPC, WebSocket support
4. **Observability**: Detailed metrics, tracing, logging
5. **Performance**: Written in C++, high performance

#### CNCF Adoption

**Timeline**:

* **September 2016**: Envoy open-sourced
* **September 2017**: Accepted as CNCF project (Incubating)
* **November 2018**: Promoted to CNCF Graduated project

### The Birth and History of Istio

#### Google, IBM, Lyft Collaboration

**In May 2017**, Google, IBM, and Lyft collaborated to announce Istio.

```mermaid
flowchart LR
    subgraph Companies[Participating Companies]
        G[Google<br/>Kubernetes experience]
        I[IBM<br/>Enterprise requirements]
        L[Lyft<br/>Envoy Proxy]
    end

    subgraph Istio[Istio Service Mesh]
        CP[Control Plane<br/>Google led]
        DP[Data Plane<br/>Envoy-based]
    end

    G --> CP
    I --> CP
    L --> DP

    %% Style definitions
    classDef company fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef component fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class G,I,L company;
    class CP,DP component;
```

**Contributions from Each Company**:

| Company    | Main Contribution    | Reason                           |
| ---------- | -------------------- | -------------------------------- |
| **Google** | Control Plane design | Borg, Kubernetes experience      |
| **IBM**    | Enterprise features  | Enterprise customer requirements |
| **Lyft**   | Envoy Proxy          | Production-proven proxy          |

#### Istio Version History

**Major Milestones**:

```mermaid
timeline
    title Istio Major Version History
    2017-05 : Istio 0.1 announced
    2018-07 : Istio 1.0 : Production ready
    2019-03 : Istio 1.1 : Performance improvements
    2020-03 : Istio 1.5 : Istiod consolidation
    2021-05 : Istio 1.10 : Discovery Selectors
    2022-02 : Istio 1.13 : Gateway API support
    2023-11 : Istio 1.20 : Ambient Mode
    2024-05 : Istio 1.22 : Stability improvements
    2025-01 : Istio 1.28 : Current version
```

**Version 1.5 (March 2020) - Important Turning Point**:

Previous architecture (Istio 1.4 and earlier):

```
Separated into individual components:
- Mixer (policy/telemetry)
- Pilot (traffic management)
- Citadel (certificate management)
- Galley (configuration validation)
```

New architecture (Istio 1.5+, current 1.28):

```
Istiod (consolidated into single binary)
├── Pilot functionality (Service Discovery, Traffic Management)
├── Citadel functionality (Certificate Authority, Identity)
└── Galley functionality (Configuration Validation)

Mixer completely removed (functionality moved to Envoy)
```

**Reasons for Change**:

* Reduced complexity (4 components → 1)
* Improved performance (50% latency reduction with Mixer removal)
* Simplified operations (single process management)
* Resource efficiency (reduced memory, CPU usage)

## Why Istio?

Kubernetes provides container orchestration, but has limitations in managing complex communication between microservices. Istio is a service mesh solution to address these problems.

### Microservices Challenges

```mermaid
flowchart TB
    subgraph Problems["Microservices Challenges"]
        P1[Traffic Management<br/>Complex routing]
        P2[Security<br/>Inter-service encryption]
        P3[Observability<br/>Difficult debugging]
        P4[Resilience<br/>Failure handling]
    end

    subgraph Without["Without Istio"]
        W1[Direct implementation<br/>in application code]
        W2[Duplicate code<br/>in each service]
        W3[Inconsistent<br/>implementation]
        W4[Difficult<br/>maintenance]
    end

    subgraph With["Using Istio"]
        I1[Automatic handling<br/>at infrastructure level]
        I2[Central management<br/>with declarative config]
        I3[Consistent<br/>policy application]
        I4[Add features<br/>without code changes]
    end

    P1 & P2 & P3 & P4 -->|Traditional approach| W1
    W1 --> W2 --> W3 --> W4

    P1 & P2 & P3 & P4 -->|Istio| I1
    I1 --> I2 --> I3 --> I4

    %% Style definitions
    classDef problem fill:#FF6B6B,stroke:#333,stroke-width:1px,color:white;
    classDef without fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef with fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class P1,P2,P3,P4 problem;
    class W1,W2,W3,W4 without;
    class I1,I2,I3,I4 with;
```

### Core Values Provided by Istio

#### 1. Traffic Management

**Problem**: Want to safely transition traffic when deploying new versions.

**Istio Solution**:

```yaml
# Canary deployment without code changes
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # Existing version 90%
    - destination:
        host: reviews
        subset: v2
      weight: 10  # New version 10%
```

**Benefits**:

* No application code modification required
* Real-time traffic split adjustment
* Automatic rollback possible
* A/B testing, Blue/Green deployment support

#### 2. Security

**Problem**: Want to encrypt and authenticate inter-service communication.

**Istio Solution**:

```yaml
# Automatic mTLS enablement
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: STRICT  # Automatic encryption for all inter-service communication
```

**Benefits**:

* Automatic certificate issuance and renewal
* Automatic service identity verification
* Fine-grained permission control
* Zero Trust network implementation

#### 3. Observability

**Problem**: Difficult to trace request flow across dozens of microservices.

**Istio Solution**:

* Automatic metric generation (Latency, Traffic, Errors, Saturation)
* Distributed Tracing
* Service topology visualization

**Benefits**:

* Automatic identification of bottlenecks
* Quick error root cause identification
* Real-time service status monitoring

#### 4. Resilience

**Problem**: Failure of one service propagates to the entire system.

**Istio Solution**:

```yaml
# Automatic Circuit Breaker configuration
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**Benefits**:

* Failure isolation (Circuit Breaker)
* Automatic retry and timeout
* Automatic removal of unhealthy instances
* Traffic limiting (Rate Limiting)

### When to Use Istio

**✅ When Istio is Suitable:**

1. **Microservices Architecture**
   * 10 or more services
   * Complex dependencies between services
   * Frequent deployments
2. **Advanced Traffic Management Needed**
   * Canary deployments, A/B testing
   * Fine-grained routing control
   * Traffic Mirroring
3. **Strong Security Requirements**
   * Inter-service encryption mandatory
   * Fine-grained access control
   * Regulatory compliance
4. **Observability and Debugging**
   * Complex inter-service problem tracking
   * Performance bottleneck identification
   * SLO/SLA monitoring

**❌ When Istio May Be Overkill:**

1. **Simple Applications**
   * Few services (less than 5)
   * Simple requirements
   * Kubernetes Ingress is sufficient
2. **Resource Constraints**
   * Small cluster
   * Cannot handle resource overhead
   * Sidecar memory cost burden
3. **Lack of Operations Capability**
   * Insufficient learning time
   * No dedicated platform team
   * Prefer simpler solutions

### Alternatives Comparison

#### Kubernetes Ingress vs Istio

| Feature           | Kubernetes Ingress | Istio                             |
| ----------------- | ------------------ | --------------------------------- |
| **Scope**         | External → Cluster | External + Internal inter-service |
| **Routing**       | Basic (Path, Host) | Advanced (Header, Cookie, etc.)   |
| **mTLS**          | Manual setup       | Automatic                         |
| **Observability** | Limited            | Rich                              |
| **Complexity**    | Low                | High                              |
| **Use Case**      | Simple apps        | Microservices                     |

#### AWS VPC Lattice vs Istio

For detailed comparison, refer to the [AWS Integration](04-aws-integration.md#istio-vs-other-solutions-comparison) document.

**Quick Summary:**

* **VPC Lattice**: AWS managed, simple, cross-VPC/account communication
* **Istio**: Open source, powerful features, Kubernetes-only, fine-grained control

#### Linkerd vs Istio

| Property           | Istio     | Linkerd            |
| ------------------ | --------- | ------------------ |
| **Complexity**     | High      | Low                |
| **Features**       | Very rich | Core features only |
| **Resources**      | High      | Low                |
| **Learning Curve** | Steep     | Gentle             |
| **Community**      | Large     | Small              |

**Selection Guide:**

* Need advanced features and flexibility → **Istio**
* Need simple and lightweight mesh → **Linkerd**

## Deployment Modes: Sidecar vs Ambient

Istio supports two deployment modes: **Sidecar Mode** and **Ambient Mode**.

### Sidecar Mode (Default)

Injects an Envoy proxy as a sidecar container into each application pod.

```mermaid
flowchart LR
    subgraph Pod["Pod"]
        App[Application<br/>Container]
        Envoy[Envoy Proxy<br/>Sidecar]
    end

    External[External Request] -->|Traffic| Envoy
    Envoy -->|Local| App
    App -->|Outbound call| Envoy
    Envoy -->|Network| Target[Target Service]

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class External,Target default;
```

**Advantages:**

* Mature and stable
* All Istio features supported
* Fine-grained control per pod

**Disadvantages:**

* Resource overhead (Envoy per pod)
* Increased startup time (Init Container)
* Complex permission setup (iptables)

### Ambient Mode (New Approach)

Handles traffic at the node level without sidecars.

```mermaid
flowchart TB
    subgraph Node["Worker Node"]
        subgraph Pod1["Pod 1"]
            App1[Application<br/>No sidecar]
        end

        subgraph Pod2["Pod 2"]
            App2[Application<br/>No sidecar]
        end

        Ztunnel[ztunnel<br/>1 per node<br/>L4 proxy]
        Waypoint[Waypoint Proxy<br/>L7 proxy<br/>Optional]
    end

    App1 <-->|Transparent redirect| Ztunnel
    App2 <-->|Transparent redirect| Ztunnel
    Ztunnel <-->|When L7 needed| Waypoint

    %% Style definitions
    classDef userApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class App1,App2 userApp;
    class Ztunnel,Waypoint proxy;
```

**Advantages:**

* Low resource usage (1 per node)
* Fast pod startup
* Simple operations
* Gradual L7 feature application possible

**Disadvantages:**

* Relatively new technology (less mature)
* Some advanced features limited
* Difficult fine-grained control per pod

### Comparison Table

| Property                   | Sidecar Mode                | Ambient Mode                   |
| -------------------------- | --------------------------- | ------------------------------ |
| **Resource Usage**         | High (per pod)              | Low (per node)                 |
| **Startup Time**           | Slow (Init Container)       | Fast                           |
| **Operational Complexity** | High                        | Low                            |
| **L4 Features**            | Supported                   | Supported                      |
| **L7 Features**            | Full support                | Optional (Waypoint)            |
| **Maturity**               | High                        | Medium                         |
| **Migration**              | -                           | Possible from existing sidecar |
| **Recommended Use**        | Advanced L7 features needed | Resource efficiency priority   |

### Selection Guide

**Choose Sidecar Mode:**

* Need to utilize all Istio features
* Need fine-grained policy control per pod
* Need production-proven stability

**Choose Ambient Mode:**

* Resource efficiency is important
* Only simple L4 features needed
* Planning to gradually add L7 features

**For details**, refer to the [Advanced: Ambient Mode](advanced/01-ambient-mode.md) document.

## Istio Architecture

Istio consists of two main components: **Control Plane** and **Data Plane**.

| Component                    | Description                                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Control Plane (istiod)**   | Central control system responsible for service discovery, configuration distribution, certificate management |
| **Data Plane (Envoy Proxy)** | Deployed as sidecar in each pod, handles actual traffic (routing, mTLS, metrics)                             |

**For detailed architecture structure, internal operation principles, and traffic interception mechanisms**, refer to the [Architecture document](03-architecture.md).

## Core Resources

Istio uses Kubernetes Custom Resource Definitions (CRDs) to manage configuration.

### 1. VirtualService

VirtualService defines how requests are routed to services.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
spec:
  hosts:
  - reviews  # Target service
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2  # Route specific user to v2
  - route:
    - destination:
        host: reviews
        subset: v1  # Route to v1 by default
```

**Key Features**:

* Path-based routing (Path, Header, Query Parameter)
* Traffic splitting (Canary, A/B testing)
* Retry, Timeout, Fault Injection
* URL Rewrite, Header manipulation

### 2. DestinationRule

DestinationRule defines service subsets (versions) and applies traffic policies.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-destination
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST  # Load balancing algorithm
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
  - name: v3
    labels:
      version: v3
```

**Key Features**:

* Service version (subset) definition
* Load balancing algorithm
* Connection Pool settings
* Circuit Breaker (Outlier Detection)
* TLS settings

### 3. Gateway

Gateway manages external traffic entering the mesh.

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
spec:
  selector:
    istio: ingressgateway  # Select Ingress Gateway pod
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "bookinfo.example.com"
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-credential  # TLS certificate
    hosts:
    - "bookinfo.example.com"
```

**Key Features**:

* Define external traffic entry point
* Host, port, protocol settings
* TLS termination
* SNI routing

### 4. ServiceEntry

ServiceEntry allows external services outside the mesh to be used like internal services.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

**Key Features**:

* External service registration
* Traffic control for external services
* Egress traffic management

### 5. PeerAuthentication

PeerAuthentication defines authentication policies between services.

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # STRICT, PERMISSIVE, DISABLE
```

### 6. AuthorizationPolicy

AuthorizationPolicy defines service access permissions.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: allow-ratings
  namespace: default
spec:
  selector:
    matchLabels:
      app: ratings
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/reviews"]
    to:
    - operation:
        methods: ["GET"]
```

## Traffic Management Concepts

### Traffic Routing Flow

```mermaid
flowchart LR
    Client[Client] -->|1. HTTP Request| Gateway[Gateway<br/>Ingress]
    Gateway -->|2. VirtualService<br/>Apply routing rules| VS[VirtualService]
    VS -->|3. Determine destination| DR[DestinationRule]
    DR -->|4. Select subset<br/>Apply traffic policy| Service[Kubernetes<br/>Service]
    Service -->|5. Endpoint<br/>routing| Pod1[Pod v1]
    Service -->|5. Endpoint<br/>routing| Pod2[Pod v2]

    %% Style definitions
    classDef gateway fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef istioResource fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef k8sResource fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class Gateway gateway;
    class VS,DR istioResource;
    class Service,Pod1,Pod2 k8sResource;
    class Client default;
```

### Traffic Splitting (Canary Deployment)

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-canary
spec:
  hosts:
  - reviews
  http:
  - route:
    - destination:
        host: reviews
        subset: v1
      weight: 90  # 90% of traffic
    - destination:
        host: reviews
        subset: v2
      weight: 10  # 10% of traffic (canary)
```

### Circuit Breaker

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-circuit-breaker
spec:
  host: reviews
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 2
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

## Security Concepts

### mTLS (Mutual TLS)

Istio automatically encrypts inter-service communication.

```mermaid
flowchart LR
    subgraph Pod1["Pod A"]
        App1[App]
        Envoy1[Envoy]
    end

    subgraph Pod2["Pod B"]
        Envoy2[Envoy]
        App2[App]
    end

    App1 -->|Plaintext| Envoy1
    Envoy1 <-->|mTLS Encrypted| Envoy2
    Envoy2 -->|Plaintext| App2

    Citadel[istiod<br/>Citadel] -.->|Certificate issuance| Envoy1
    Citadel -.->|Certificate issuance| Envoy2

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App1,App2 app;
    class Envoy1,Envoy2 proxy;
    class Citadel controlPlane;
```

**mTLS Modes**:

* **STRICT**: mTLS only allowed
* **PERMISSIVE**: Both mTLS and plaintext allowed (for migration)
* **DISABLE**: mTLS disabled

### Authentication and Authorization

```yaml
# JWT Authentication
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: jwt-auth
spec:
  jwtRules:
  - issuer: "https://accounts.google.com"
    jwksUri: "https://www.googleapis.com/oauth2/v3/certs"
---
# Authorization Policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: require-jwt
spec:
  action: DENY
  rules:
  - from:
    - source:
        notRequestPrincipals: ["*"]
```

## Observability Concepts

Istio automatically generates metrics, logs, and traces.

### Automatically Generated Metrics

```mermaid
flowchart TB
    subgraph Pod["Pod"]
        App[Application]
        Envoy[Envoy Proxy]
    end

    App <-->|Traffic| Envoy

    Envoy -->|Metrics| Prometheus[Prometheus<br/>Metric Collection]
    Envoy -->|Traces| Jaeger[Jaeger<br/>Distributed Tracing]
    Envoy -->|Logs| Logging[Logging System]

    Prometheus -->|Visualization| Grafana[Grafana<br/>Dashboard]
    Jaeger -->|Analysis| JaegerUI[Jaeger UI]

    Kiali[Kiali<br/>Service Mesh Dashboard] -->|Query| Prometheus

    %% Style definitions
    classDef app fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef monitoring fill:#E6522C,stroke:#333,stroke-width:1px,color:white;
    classDef visualization fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App app;
    class Envoy proxy;
    class Prometheus,Jaeger,Logging monitoring;
    class Grafana,JaegerUI,Kiali visualization;
```

### Key Metrics

| Metric                                | Description          |
| ------------------------------------- | -------------------- |
| `istio_requests_total`                | Total request count  |
| `istio_request_duration_milliseconds` | Request latency      |
| `istio_request_bytes`                 | Request size         |
| `istio_response_bytes`                | Response size        |
| `istio_tcp_connections_opened_total`  | TCP connection count |

### Distributed Tracing

```yaml
# Enable tracing in Envoy
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    defaultConfig:
      tracing:
        sampling: 100.0  # 100% sampling
        zipkin:
          address: jaeger-collector.istio-system:9411
```

## Namespaces and Service Mesh

### Namespace Isolation

```yaml
# Per-namespace mTLS policy
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
---
# Per-namespace authorization policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: production
spec:
  action: DENY
  rules:
  - {}
```

### Service Mesh Scope

```bash
# Include only specific namespaces in the mesh
kubectl label namespace default istio-injection=enabled
kubectl label namespace staging istio-injection=enabled

# Exclude specific namespace
kubectl label namespace kube-system istio-injection=disabled
```

### Multi-tenancy

```yaml
# Restrict mesh scope with Sidecar resource
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: production
spec:
  egress:
  - hosts:
    - "production/*"  # Only production namespace accessible
    - "istio-system/*"
```

## VM Workload Registration

Istio can register not only Kubernetes pods but also **Virtual Machine (VM) workloads** in the service mesh. This allows legacy applications or services outside the cluster to utilize Istio's traffic management, security, and observability features.

### Why VM Workloads Are Needed

```mermaid
flowchart TB
    subgraph Legacy[Legacy Environment]
        VM1[VM<br/>Legacy App]
        VM2[VM<br/>Database]
        VM3[VM<br/>External Service]
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

    VM1 -->|Before migration<br/>Direct communication| App1
    App1 -.->|After mesh registration<br/>mTLS, policy applied| VM1

    CP -.->|Configuration delivery| Envoy1
    CP -.->|Configuration delivery| Envoy2
    CP -.->|VM can also be registered| VM1

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class App1,App2 k8sApp;
    class Envoy1,Envoy2 proxy;
    class CP controlPlane;
```

**Usage Scenarios**:

* Gradual migration of legacy applications
* Including database servers in the mesh
* Integration of services outside the cluster
* Hybrid cloud environment configuration

### VM Registration Architecture

```mermaid
flowchart LR
    subgraph VM[Virtual Machine]
        LegacyApp[Legacy<br/>Application]
        EnvoyVM[Envoy<br/>Sidecar]
    end

    subgraph K8S[Kubernetes Cluster]
        subgraph Pod[Pod]
            App[Application]
            EnvoyPod[Envoy<br/>Sidecar]
        end

        Istiod[istiod<br/>Control Plane]
    end

    LegacyApp <-->|Local communication| EnvoyVM
    App <-->|Local communication| EnvoyPod

    EnvoyVM <-->|mTLS| EnvoyPod

    Istiod -.->|xDS configuration| EnvoyVM
    Istiod -.->|xDS configuration| EnvoyPod
    Istiod -.->|Certificate issuance| EnvoyVM

    %% Style definitions
    classDef vmApp fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8sApp fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef proxy fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef controlPlane fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class LegacyApp vmApp;
    class App k8sApp;
    class EnvoyVM,EnvoyPod proxy;
    class Istiod controlPlane;
```

### WorkloadEntry Resource

VM workloads are registered with the **WorkloadEntry** resource.

```yaml
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: legacy-database
  namespace: default
spec:
  address: 192.168.1.100  # VM IP address
  labels:
    app: mysql
    version: v5.7
  serviceAccount: database-sa
  ports:
    mysql: 3306
```

**WorkloadEntry Key Fields**:

* `address`: VM IP address
* `labels`: Matches with service selector
* `serviceAccount`: Service account for mTLS authentication
* `ports`: Exposed port definition

### Integration with ServiceEntry

WorkloadEntry is used with ServiceEntry to register VM services in the mesh.

```yaml
# Define service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-database
spec:
  hosts:
  - database.legacy.com
  ports:
  - number: 3306
    name: mysql
    protocol: TCP
  location: MESH_INTERNAL  # Register as internal mesh service
  resolution: STATIC
  workloadSelector:
    labels:
      app: mysql
---
# Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: mysql-vm-1
  namespace: default
spec:
  address: 192.168.1.100
  labels:
    app: mysql
    version: v5.7
  serviceAccount: mysql-sa
```

### VM Registration vs Multi-Cluster Comparison

| Feature                    | VM Workload Registration | Multi-Cluster                  | Kubernetes Pod      |
| -------------------------- | ------------------------ | ------------------------------ | ------------------- |
| **Workload Location**      | VM outside cluster       | Different Kubernetes cluster   | Inside cluster      |
| **Envoy Installation**     | Manual installation      | Automatic (sidecar)            | Automatic (sidecar) |
| **Registration Method**    | WorkloadEntry            | ServiceEntry + EndpointSlice   | Service + Pod       |
| **mTLS**                   | Supported                | Supported                      | Supported           |
| **Service Discovery**      | Manual (IP specified)    | Automatic                      | Automatic           |
| **Usage Scenario**         | Legacy apps, DB          | Multi-cloud, disaster recovery | Cloud-native apps   |
| **Operational Complexity** | High                     | Medium                         | Low                 |

### Benefits of VM Registration

#### 1. Gradual Migration

```mermaid
flowchart LR
    subgraph Phase1[Phase 1: Legacy Environment]
        VM1[VM<br/>Monolith App]
    end

    subgraph Phase2[Phase 2: VM Mesh Registration]
        VM2[VM<br/>Monolith App<br/>+ Envoy]
    end

    subgraph Phase3[Phase 3: Hybrid]
        VM3[VM<br/>Legacy Module]
        K8S1[K8s<br/>New Microservices]
        VM3 <-->|mTLS| K8S1
    end

    subgraph Phase4[Phase 4: Complete Migration]
        K8S2[K8s<br/>All Microservices]
    end

    Phase1 -->|VM registration| Phase2
    Phase2 -->|Partial migration| Phase3
    Phase3 -->|Complete| Phase4

    %% Style definitions
    classDef vm fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;
    classDef k8s fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class VM1,VM2,VM3 vm;
    class K8S1,K8S2 k8s;
```

**Benefits**:

* Integrate existing VM applications into mesh without modification
* Migrate to Kubernetes in stages
* Maintain consistent security and observability during migration

#### 2. Unified Security Policy

```yaml
# mTLS policy applied to both VMs and pods
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: default
spec:
  mtls:
    mode: STRICT  # Enforce mTLS for both VMs and pods
---
# VM database access control
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: database-access
  namespace: default
spec:
  selector:
    matchLabels:
      app: mysql  # WorkloadEntry label
  action: ALLOW
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/app-sa"]
    to:
    - operation:
        methods: ["*"]
```

#### 3. Consistent Observability

VM workloads provide the same metrics, logs, and distributed tracing as Kubernetes pods.

```promql
# Unified metric query for VMs and pods
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))

# Error rate from VM
sum(rate(istio_requests_total{destination_workload="mysql-vm-1",response_code="500"}[5m]))
/
sum(rate(istio_requests_total{destination_workload="mysql-vm-1"}[5m]))
```

### VM Registration Limitations

1. **Manual Envoy Installation**: Must manually install and configure Envoy proxy on VM
2. **Network Connectivity**: Network connection between VM and Kubernetes cluster required
3. **Certificate Management**: Service account certificates must be deployed to VM
4. **Operational Burden**: VM Envoy version management and updates required
5. **Auto-scaling Limitation**: No auto-scaling like Kubernetes HPA

### Practical Usage Example

#### Scenario: Legacy Database Integration

```yaml
# 1. Define database service with ServiceEntry
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: legacy-postgres
  namespace: production
spec:
  hosts:
  - postgres.production.svc.cluster.local
  addresses:
  - 240.240.1.10  # Virtual IP
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
# 2. Register VM instance with WorkloadEntry
apiVersion: networking.istio.io/v1
kind: WorkloadEntry
metadata:
  name: postgres-vm-1
  namespace: production
spec:
  address: 10.0.1.100  # Actual VM IP
  labels:
    app: postgres
    tier: database
    version: v13
  serviceAccount: postgres-sa
  ports:
    postgresql: 5432
---
# 3. Access control policy
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: postgres-access-control
  namespace: production
spec:
  selector:
    matchLabels:
      app: postgres
  action: ALLOW
  rules:
  - from:
    - source:
        namespaces: ["production"]
        principals: ["cluster.local/ns/production/sa/api-service"]
    to:
    - operation:
        ports: ["5432"]
```

**Result**:

* Kubernetes pods access database via `postgres.production.svc.cluster.local`
* Automatic mTLS encryption between VM and pods
* Access control policy applied
* Metrics and distributed tracing automatically collected

### Workload Registration Comparison Summary

```mermaid
flowchart TB
    subgraph Types[Workload Types]
        K8S[Kubernetes Pod<br/>Inside cluster]
        MC[Multi-Cluster<br/>Different cluster]
        VM[Virtual Machine<br/>Outside cluster]
    end

    subgraph Features[Common Features]
        mTLS[mTLS Encryption]
        Traffic[Traffic Management]
        Policy[Security Policy]
        Metrics[Metrics & Tracing]
    end

    K8S & MC & VM --> mTLS
    K8S & MC & VM --> Traffic
    K8S & MC & VM --> Policy
    K8S & MC & VM --> Metrics

    %% Style definitions
    classDef workload fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef feature fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class K8S,MC,VM workload;
    class mTLS,Traffic,Policy,Metrics feature;
```

Through Istio's flexible workload registration capabilities:

* **Kubernetes Pod**: Cloud-native applications
* **Multi-Cluster**: Multi-cloud, regional distribution, disaster recovery
* **Virtual Machine**: Legacy apps, databases, hybrid environments

All workloads receive consistent security, traffic management, and observability features.

## Next Steps

You now understand Istio's basic concepts. Learn how to use them in practice through the following documents:

### Core Features

1. [**Traffic Management**](traffic-management/)
   * Gateway and VirtualService usage
   * DestinationRule and subset definition
   * ServiceEntry and WorkloadEntry (VM registration)
   * Advanced routing patterns (Canary, A/B testing)
   * Traffic Mirroring and Shadowing
2. [**Security**](security/)
   * mTLS configuration and PeerAuthentication
   * Authentication (RequestAuthentication, JWT)
   * Authorization (AuthorizationPolicy)
   * Security policy management
   * External authentication integration
3. [**Observability**](/broken/pages/HT0uW6gT7EfVN0LF8wU5)
   * Metric collection (Prometheus)
   * Distributed tracing (Jaeger, Zipkin)
   * Logging configuration
   * Kiali service mesh visualization
   * Grafana dashboards
4. [**Resilience**](resilience/)
   * Circuit Breaker pattern
   * Retry and Timeout settings
   * Rate Limiting
   * Outlier Detection
   * Fault Injection testing

### Advanced Topics

5. [**Advanced Topics**](advanced/)
   * Ambient Mode (sidecar-less mesh)
   * Multi-Cluster configuration
   * EnvoyFilter customization
   * DNS Proxy and Caching
   * VM workload detailed configuration
   * WASM plugin development

## References

* [Istio Official Documentation - Concepts](https://istio.io/latest/docs/concepts/)
* [Istio Official Documentation - Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
* [Istio Official Documentation - Security](https://istio.io/latest/docs/concepts/security/)
* [Istio Official Documentation - Observability](https://istio.io/latest/docs/concepts/observability/)
* [Envoy Proxy Official Documentation](https://www.envoyproxy.io/docs/envoy/latest/)
