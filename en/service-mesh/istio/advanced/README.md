# Advanced

This section covers advanced Istio features including Ambient Mode, Multi-cluster, EnvoyFilter, gRPC/WebSocket support, and more.

## Table of Contents

1. [Ambient Mode](01-ambient-mode.md)
2. [Multi-cluster](02-multi-cluster.md)
3. [EnvoyFilter](03-envoy-filter.md)
4. [DNS Caching](04-dns-cache.md)
5. [gRPC](05-grpc.md)
6. [WebSocket](06-websocket.md)
7. [Sidecar Injection](07-sidecar-injection.md)
8. [Argo Rollouts Integration](08-argo-rollouts.md)
9. [Zone-Aware Argo Rollouts](09-zone-aware-argo-rollouts.md)
10. [KEDA Autoscaling](10-keda-autoscaling.md)

## Overview

This section covers advanced Istio features and in-depth topics needed for production environments.

### Key Topics

```mermaid
flowchart TB
    subgraph Deployment["Deployment Modes"]
        Sidecar[Sidecar Mode<br/>Traditional Approach]
        Ambient[Ambient Mode<br/>New Architecture]
    end

    subgraph MultiCluster["Multi-cluster"]
        Primary[Primary Cluster<br/>Control Plane]
        Remote[Remote Cluster<br/>Workload Only]
    end

    subgraph Advanced["Advanced Features"]
        EnvoyFilter[EnvoyFilter<br/>Customization]
        DNS[DNS Caching<br/>Performance Optimization]
        Protocol[gRPC/WebSocket<br/>Protocol Support]
    end

    subgraph Integration["Integration"]
        ArgoRollouts[Argo Rollouts<br/>Progressive Delivery]
    end

    Sidecar --> EnvoyFilter
    Ambient --> EnvoyFilter
    Primary --> Remote
    EnvoyFilter --> Protocol
    ArgoRollouts -.-> Sidecar

    %% Style definitions
    classDef deployment fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef multi fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef advanced fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef integration fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;

    %% Class assignments
    class Sidecar,Ambient deployment;
    class Primary,Remote multi;
    class EnvoyFilter,DNS,Protocol advanced;
    class ArgoRollouts integration;
```

## 1. Ambient Mode

A new data plane architecture introduced in Istio 1.28+.

### Sidecar Mode vs Ambient Mode

| Characteristic | Sidecar Mode | Ambient Mode |
|----------------|-------------|--------------|
| **Architecture** | Envoy proxy injected in each pod | ztunnel (node-level) + waypoint (optional) |
| **Resource Usage** | High (proxy per pod) | Low (proxy per node) |
| **Deployment Complexity** | High (redeployment required) | Low (transparently applied) |
| **Performance** | Slightly slower (additional hop) | Faster (L4 only when needed) |
| **Features** | All features supported | L4 by default, L7 requires waypoint |

### Ambient Mode Architecture

```mermaid
flowchart TB
    subgraph Pod1["Pod (App Only)"]
        App1[Application<br/>No Sidecar]
    end

    subgraph Node["Kubernetes Node"]
        Ztunnel[ztunnel<br/>L4 Proxy<br/>mTLS, Telemetry]
    end

    subgraph Waypoint["Waypoint Proxy (Optional)"]
        WP[Waypoint<br/>L7 Proxy<br/>Advanced Routing]
    end

    App1 -->|Transparent| Ztunnel
    Ztunnel -->|L4 only| Service[Service]
    Ztunnel -.->|L7 needed| WP
    WP --> Service

    %% Style definitions
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef ztunnel fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef waypoint fill:#3B48CC,stroke:#333,stroke-width:1px,color:white;
    classDef service fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;

    %% Class assignments
    class App1 pod;
    class Ztunnel ztunnel;
    class WP waypoint;
    class Service service;
```

**More details**: [Ambient Mode Detailed Guide](01-ambient-mode.md)

## 2. Multi-cluster

Connect multiple Kubernetes clusters as a single service mesh.

### Multi-cluster Topology

```mermaid
flowchart TB
    subgraph Primary["Primary Cluster<br/>us-east-1"]
        CP1[Istiod<br/>Control Plane]
        Service1[Service A]
    end

    subgraph Remote1["Remote Cluster 1<br/>us-west-2"]
        Service2[Service B]
    end

    subgraph Remote2["Remote Cluster 2<br/>eu-west-1"]
        Service3[Service C]
    end

    CP1 -.->|Config Push| Service2
    CP1 -.->|Config Push| Service3
    Service1 <-->|Cross-cluster<br/>Communication| Service2
    Service1 <-->|Cross-cluster<br/>Communication| Service3

    %% Style definitions
    classDef primary fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef remote fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef service fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;

    %% Class assignments
    class CP1 primary;
    class Service2,Service3 remote;
    class Service1 service;
```

**Use Cases**:
- Multi-region deployment
- Disaster Recovery (DR)
- Blue/Green cluster deployment
- Environment isolation (dev/staging/prod)

**More details**: [Multi-cluster Setup Guide](02-multi-cluster.md)

## 3. EnvoyFilter

Directly customize Envoy proxy configuration.

### EnvoyFilter Use Cases

```yaml
# Add custom header
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: custom-header
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          inline_code: |
            function envoy_on_request(request_handle)
              request_handle:headers():add("x-custom-header", "value")
            end
```

**Key Use Cases**:
- Rate Limiting
- Custom Authentication/Authorization
- Header Manipulation
- Request/Response Transformation
- WASM Plugins

**More details**: [EnvoyFilter Guide](03-envoy-filter.md)

## 4. DNS Caching

Optimize performance by caching DNS lookups.

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: dns-cache
spec:
  host: external-api.example.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 100
```

**Benefits**:
- Reduced DNS lookup latency
- Reduced load on external DNS servers
- Consistent DNS responses

**More details**: [DNS Caching Guide](04-dns-cache.md)

## 5. gRPC Support

Provides optimized routing and load balancing for the gRPC protocol.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: grpc-service
spec:
  hosts:
  - grpc-service
  http:
  - match:
    - uri:
        prefix: /mypackage.MyService/
    route:
    - destination:
        host: grpc-service
        subset: v2
```

**Key Features**:
- HTTP/2-based load balancing
- gRPC health checks
- Deadlines and Retries
- Metadata-based routing

**More details**: [gRPC Guide](05-grpc.md)

## 6. WebSocket Support

Provides special handling for WebSocket connections.

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: websocket-service
spec:
  hosts:
  - ws.example.com
  http:
  - match:
    - headers:
        upgrade:
          exact: websocket
    route:
    - destination:
        host: websocket-service
```

**Key Features**:
- Long-lived connection maintenance
- Connection Pool configuration
- Idle Timeout management

**More details**: [WebSocket Guide](06-websocket.md)

## 7. Sidecar Injection

Covers sidecar proxy injection mechanisms and customization.

### Injection Methods

```mermaid
flowchart TB
    Pod[Pod Creation]
    Check{Namespace has<br/>label?}
    Inject[Sidecar Injection]
    Deploy[Pod Deployment]
    Skip[Skip Injection]

    Pod --> Check
    Check -->|istio-injection=enabled| Inject
    Check -->|No| Skip
    Inject --> Deploy
    Skip --> Deploy

    %% Style definitions
    classDef pod fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef decision fill:#F8B52A,stroke:#333,stroke-width:1px,color:black;
    classDef inject fill:#326CE5,stroke:#333,stroke-width:1px,color:white;

    %% Class assignments
    class Pod,Deploy pod;
    class Check decision;
    class Inject inject;
    class Skip pod;
```

**More details**: [Sidecar Injection Guide](07-sidecar-injection.md)

## 8. Argo Rollouts Integration

Implement advanced deployment strategies by integrating Argo Rollouts with Istio.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: myapp
spec:
  strategy:
    canary:
      trafficRouting:
        istio:
          virtualService:
            name: myapp-vsvc
            routes:
            - primary
      steps:
      - setWeight: 10
      - pause: {duration: 2m}
      - setWeight: 50
      - pause: {duration: 2m}
```

**Key Features**:
- Metrics-based automatic Canary deployment
- Analysis and automatic rollback
- Blue/Green deployment
- Progressive Delivery

**More details**: [Argo Rollouts Integration Guide](08-argo-rollouts.md)

## 9. Zone-Aware Argo Rollouts

Perform zone-aware Canary deployments by availability zone.

**More details**: [Zone-Aware Argo Rollouts Guide](09-zone-aware-argo-rollouts.md)

## 10. KEDA Autoscaling

Implement Istio metrics-based autoscaling using KEDA.

### KEDA vs HPA

| Feature | Kubernetes HPA | KEDA |
|---------|---------------|------|
| **Metric Sources** | CPU/Memory + Custom Metrics | 60+ Scalers (Prometheus, CloudWatch, Kafka, etc.) |
| **Scale to Zero** | Not supported (minimum 1) | Supported (0 pods possible) |
| **External Metrics** | Requires Metrics Server | Native support |
| **Complex Queries** | Limited | PromQL, CloudWatch Insights |

### KEDA Architecture

```mermaid
flowchart TB
    subgraph IstioMesh[Istio Service Mesh]
        Service[Service<br/>with Envoy]
        Envoy[Envoy Proxy]
        Service --> Envoy
    end

    subgraph Observability[Observability Stack]
        Prometheus[Prometheus<br/>Metrics Collection]
        CloudWatch[CloudWatch<br/>AWS Metrics]
    end

    subgraph Autoscaling[Autoscaling]
        KEDA[KEDA<br/>Operator]
        HPA[HPA<br/>Controller]
        ScaledObject[ScaledObject<br/>Policy]
    end

    Envoy -->|Metrics| Prometheus
    Envoy -->|Metrics| CloudWatch

    Prometheus -->|Query| KEDA
    CloudWatch -->|Query| KEDA

    KEDA -->|Create/Manage| HPA
    ScaledObject -->|Define| KEDA

    HPA -->|Scale| Service

    %% Style definitions
    classDef istio fill:#326CE5,stroke:#333,stroke-width:2px,color:white;
    classDef observability fill:#E6522C,stroke:#333,stroke-width:2px,color:white;
    classDef autoscaling fill:#00C7B7,stroke:#333,stroke-width:2px,color:white;

    %% Class assignments
    class Service,Envoy istio;
    class Prometheus,CloudWatch observability;
    class KEDA,HPA,ScaledObject autoscaling;
```

### Key Scaling Strategies

```yaml
# RPS-based scaling
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: reviews-rps-scaler
spec:
  scaleTargetRef:
    name: reviews
  triggers:
  - type: prometheus
    metadata:
      query: |
        sum(rate(istio_requests_total{
          destination_workload="reviews"
        }[1m]))
      threshold: '100'
```

**Scaling Metrics**:
- **RPS (Requests Per Second)**: Based on requests per second
- **Latency (P50/P95/P99)**: Based on latency percentiles
- **Error Rate**: Based on 5xx error rate
- **Circuit Breaker**: Based on Circuit Breaker state
- **Composite Metrics**: Combination of multiple metrics

**Metric Sources**:
- **Prometheus**: Real-time Istio/Envoy metrics
- **AWS CloudWatch**: CloudWatch metrics via ADOT Collector

**More details**: [KEDA Autoscaling Guide](10-keda-autoscaling.md)

## Learning Path

1. **[Ambient Mode](01-ambient-mode.md)** - Understanding the new architecture
2. **[Multi-cluster](02-multi-cluster.md)** - Multi-cluster configuration
3. **[EnvoyFilter](03-envoy-filter.md)** - Advanced customization
4. **[Sidecar Injection](07-sidecar-injection.md)** - Injection mechanisms
5. **[gRPC](05-grpc.md)** - gRPC protocol support
6. **[WebSocket](06-websocket.md)** - WebSocket support
7. **[DNS Caching](04-dns-cache.md)** - Performance optimization
8. **[Argo Rollouts](08-argo-rollouts.md)** - Progressive Delivery
9. **[Zone-Aware Argo Rollouts](09-zone-aware-argo-rollouts.md)** - Zone-based deployment
10. **[KEDA Autoscaling](10-keda-autoscaling.md)** - Metrics-based autoscaling

## References

- [Istio Advanced Features](https://istio.io/latest/docs/ops/)
- [Ambient Mode Documentation](https://istio.io/latest/docs/ops/ambient/)
- [Multi-cluster Documentation](https://istio.io/latest/docs/setup/install/multicluster/)
- [EnvoyFilter Reference](https://istio.io/latest/docs/reference/config/networking/envoy-filter/)

## Quiz

To test what you've learned in this chapter, take the [Istio Advanced Quiz](../../../quizzes/service-mesh/istio/advanced.md).
