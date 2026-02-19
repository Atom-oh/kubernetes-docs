# ServiceEntry

ServiceEntry registers external services in the Istio service mesh, allowing them to be managed like internal services.

## Table of Contents

1. [Why ServiceEntry?](#why-serviceentry)
2. [ServiceEntry Overview](#serviceentry-overview)
3. [Resolution Modes](#resolution-modes)
4. [Location Settings](#location-settings)
5. [Practical Examples](#practical-examples)
6. [Combining with Egress Gateway](#combining-with-egress-gateway)
7. [Security and TLS](#security-and-tls)
8. [Monitoring and Control](#monitoring-and-control)
9. [Best Practices](#best-practices)

## Why ServiceEntry?

### The Need for External Service Management

By default, Istio mesh does not control traffic to external services. Using ServiceEntry:

```mermaid
flowchart TB
    subgraph Without["Without ServiceEntry"]
        A1[Mesh Internal<br/>Service] -->|Unknown Traffic| E1[External API]
        A1 -.->|No Monitoring| E1
        A1 -.->|Cannot Apply Policies| E1
        A1 -.->|No Circuit Breaker| E1
    end

    subgraph With["With ServiceEntry"]
        A2[Mesh Internal<br/>Service] -->|Registered Traffic| E2[External API<br/>ServiceEntry]
        A2 -->|Monitoring Enabled| E2
        A2 -->|Policy Applied| E2
        A2 -->|Circuit Breaker| E2
    end

    %% Style definitions
    classDef internal fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#FF9900,stroke:#333,stroke-width:1px,color:black;
    classDef unknown fill:#95A5A6,stroke:#333,stroke-width:1px,color:white;

    %% Apply classes
    class A1,A2 internal;
    class E2 external;
    class E1 unknown;
```

### Key Benefits

| Feature | Without ServiceEntry | With ServiceEntry |
|---------|---------------------|-------------------|
| **Monitoring** | Black hole | Full metrics collection |
| **Traffic Control** | Impossible | Timeout, Retry, Circuit Breaker |
| **Security** | Limited | mTLS, certificate management |
| **Egress Control** | All external traffic allowed | Explicit allow/block |
| **Service Discovery** | Manual management | Automatic DNS lookup |

## ServiceEntry Overview

ServiceEntry adds external services to the Istio service registry.

```mermaid
flowchart LR
    subgraph Mesh["Service Mesh"]
        App[Application]
        SE[ServiceEntry<br/>Registration]
    end

    subgraph External["External Services"]
        API[External API<br/>api.example.com]
        DB[External DB<br/>db.example.com]
    end

    App -->|1. Request| SE
    SE -->|2. Traffic Control<br/>Monitoring<br/>Security| API
    SE -->|2. Traffic Control<br/>Monitoring<br/>Security| DB

    %% Style definitions
    classDef meshService fill:#00C7B7,stroke:#333,stroke-width:1px,color:white;
    classDef serviceEntry fill:#326CE5,stroke:#333,stroke-width:1px,color:white;
    classDef external fill:#FF9900,stroke:#333,stroke-width:1px,color:black;

    %% Apply classes
    class App meshService;
    class SE serviceEntry;
    class API,DB external;
```

### Basic Structure

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:                  # External service hostname
  - api.example.com
  ports:                  # Port and protocol
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL # External/internal location
  resolution: DNS         # Address resolution method
```

## Resolution Modes

ServiceEntry supports 4 address resolution modes.

### 1. DNS Resolution

The most common mode, dynamically resolving IP addresses through DNS.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-dns
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS  # DNS lookup
```

**Use Cases**:
- Public APIs (AWS S3, Google Cloud Storage)
- SaaS services (Stripe, SendGrid)
- Cloud managed services

### 2. STATIC Resolution

Explicitly specify fixed IP addresses.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api-static
spec:
  hosts:
  - legacy-api.company.internal
  addresses:
  - 10.10.10.10
  - 10.10.10.11
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_EXTERNAL
  resolution: STATIC  # Fixed IP
  endpoints:
  - address: 10.10.10.10
  - address: 10.10.10.11
```

**Use Cases**:
- Legacy systems (no DNS)
- Compliance requiring fixed IPs
- Internal datacenter services

### 3. NONE Resolution

Does not perform address resolution, uses the address provided by the client as-is.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: wildcard-api
spec:
  hosts:
  - "*.api.example.com"  # Wildcard
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: NONE  # No address resolution
```

**Use Cases**:
- Wildcard domains
- Client-side load balancing
- TCP/TLS proxy

### 4. DNS_ROUND_ROBIN Resolution (Deprecated)

Uses DNS round robin (now integrated into DNS mode).

## Location Settings

### MESH_EXTERNAL (External Service)

Register services outside the mesh.

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-service
spec:
  hosts:
  - external-api.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL  # External service
  resolution: DNS
```

**Characteristics**:
- mTLS not applied
- Can exit through Egress Gateway
- Classified as external traffic

### MESH_INTERNAL (Internal Service)

Treat as mesh internal service (rarely used).

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: internal-vm-service
spec:
  hosts:
  - vm-service.internal
  ports:
  - number: 8080
    name: http
    protocol: HTTP
  location: MESH_INTERNAL  # Treat as internal service
  resolution: STATIC
  endpoints:
  - address: 10.0.0.5
    labels:
      app: vm-service
```

**Use Cases**:
- Include VM workloads in mesh
- Multi-cluster environments
- Hybrid cloud configurations

## Practical Examples

### 1. Registering External REST API

#### Scenario: Payment Gateway API

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-gateway-api
  namespace: production
spec:
  hosts:
  - api.payment-gateway.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
# VirtualService: Timeout and Retry settings
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: payment-gateway-routing
  namespace: production
spec:
  hosts:
  - api.payment-gateway.com
  http:
  - route:
    - destination:
        host: api.payment-gateway.com
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset,connect-failure
---
# DestinationRule: Circuit Breaker
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: payment-gateway-circuit-breaker
  namespace: production
spec:
  host: api.payment-gateway.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutiveErrors: 3
      interval: 30s
      baseEjectionTime: 120s
    tls:
      mode: SIMPLE  # TLS connection
```

### 2. Registering External Database

#### Scenario: AWS RDS MySQL

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: aws-rds-mysql
spec:
  hosts:
  - mydb.abc123.us-west-2.rds.amazonaws.com
  ports:
  - number: 3306
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: aws-rds-mysql-circuit-breaker
spec:
  host: mydb.abc123.us-west-2.rds.amazonaws.com
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 5s
    outlierDetection:
      consecutiveErrors: 5
      interval: 60s
      baseEjectionTime: 60s
```

### 3. Registering Wildcard Domain

#### Scenario: AWS S3 Bucket Access

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: aws-s3-buckets
spec:
  hosts:
  - "*.s3.amazonaws.com"
  - "*.s3.*.amazonaws.com"
  - "*.s3-*.amazonaws.com"
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: NONE  # Use NONE for wildcards
```

### 4. External Service with Multiple Endpoints

#### Scenario: Multi-Region API

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: multi-region-api
spec:
  hosts:
  - api.global-service.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: multi-region-routing
spec:
  hosts:
  - api.global-service.com
  http:
  # Region-based routing
  - match:
    - headers:
        x-region:
          exact: "us-west"
    route:
    - destination:
        host: api.global-service.com
      headers:
        request:
          set:
            Host: us-west.api.global-service.com

  - match:
    - headers:
        x-region:
          exact: "eu-central"
    route:
    - destination:
        host: api.global-service.com
      headers:
        request:
          set:
            Host: eu-central.api.global-service.com

  # Default routing
  - route:
    - destination:
        host: api.global-service.com
```

### 5. Registering TCP Service

#### Scenario: External Redis Cluster

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-redis
spec:
  hosts:
  - redis.external-cluster.com
  addresses:
  - 203.0.113.10
  - 203.0.113.11
  ports:
  - number: 6379
    name: tcp
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
    labels:
      instance: primary
  - address: 203.0.113.11
    labels:
      instance: replica
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-redis-lb
spec:
  host: redis.external-cluster.com
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 50
        connectTimeout: 3s
```

## Combining with Egress Gateway

Control external traffic centrally through Egress Gateway.

### Basic Egress Gateway Configuration

```yaml
# ServiceEntry: Register external service
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
# Gateway: Egress Gateway configuration
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-gateway
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    hosts:
    - api.example.com
    tls:
      mode: PASSTHROUGH
---
# VirtualService: Mesh internal -> Egress Gateway
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: direct-api-through-egress
spec:
  hosts:
  - api.example.com
  gateways:
  - mesh
  - egress-gateway
  http:
  - match:
    - gateways:
      - mesh
      port: 443
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - egress-gateway
      port: 443
    route:
    - destination:
        host: api.example.com
        port:
          number: 443
```

### TLS Origination (HTTP Internal, HTTPS External)

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-http-to-https
spec:
  hosts:
  - api.secure-service.com
  ports:
  - number: 80
    name: http
    protocol: HTTP
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: originate-tls
spec:
  host: api.secure-service.com
  trafficPolicy:
    portLevelSettings:
    - port:
        number: 80
      tls:
        mode: SIMPLE  # HTTP -> HTTPS conversion
```

## Security and TLS

### mTLS to External Service

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: mtls-external-service
spec:
  hosts:
  - mtls-api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: mtls-external-tls
spec:
  host: mtls-api.example.com
  trafficPolicy:
    tls:
      mode: MUTUAL
      clientCertificate: /etc/certs/client-cert.pem
      privateKey: /etc/certs/client-key.pem
      caCertificates: /etc/certs/ca-cert.pem
```

### SNI Routing

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: egress-sni-gateway
spec:
  selector:
    istio: egressgateway
  servers:
  - port:
      number: 443
      name: tls
      protocol: TLS
    hosts:
    - api.example.com
    - api2.example.com
    tls:
      mode: PASSTHROUGH
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: sni-routing
spec:
  hosts:
  - api.example.com
  - api2.example.com
  gateways:
  - mesh
  - egress-sni-gateway
  tls:
  - match:
    - gateways:
      - mesh
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: istio-egressgateway.istio-system.svc.cluster.local
        port:
          number: 443
  - match:
    - gateways:
      - egress-sni-gateway
      port: 443
      sniHosts:
      - api.example.com
    route:
    - destination:
        host: api.example.com
        port:
          number: 443
```

## Monitoring and Control

### Metrics Collection

```bash
# Check ServiceEntry traffic
kubectl exec -it <pod-name> -c istio-proxy -- \
  curl localhost:15000/stats/prometheus | grep "api.example.com"

# Egress traffic metrics
istio_requests_total{destination_service_name="api.example.com"}
```

### Prometheus Queries

```yaml
# External service request count
sum(rate(istio_requests_total{destination_service_namespace="",destination_service_name="api.example.com"}[5m]))

# External service error rate
sum(rate(istio_requests_total{destination_service_name="api.example.com",response_code=~"5.."}[5m])) /
sum(rate(istio_requests_total{destination_service_name="api.example.com"}[5m]))

# External service response time
histogram_quantile(0.95,
  sum(rate(istio_request_duration_milliseconds_bucket{destination_service_name="api.example.com"}[5m])) by (le)
)
```

### Blocking Egress Traffic

```yaml
# Block all Egress by default
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # Allow only same namespace
    - "istio-system/*"  # Allow istio-system
  outboundTrafficPolicy:
    mode: REGISTRY_ONLY  # Allow only those registered in ServiceEntry
```

## Best Practices

### 1. Explicit ServiceEntry Registration

```yaml
# Good example: Explicit registration
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-api
  namespace: production
  annotations:
    description: "Payment gateway API"
    owner: "payments-team"
    sla: "99.9%"
spec:
  hosts:
  - api.payment.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 2. Always Apply Circuit Breaker

```yaml
# Always apply Circuit Breaker for external services
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: external-api-protection
spec:
  host: api.example.com
  trafficPolicy:
    connectionPool:
      http:
        http1MaxPendingRequests: 10
        maxRequestsPerConnection: 1
    outlierDetection:
      consecutiveErrors: 3
      interval: 30s
      baseEjectionTime: 120s
```

### 3. Timeout Settings

```yaml
# Set explicit Timeout for external services
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: external-api-timeout
spec:
  hosts:
  - api.example.com
  http:
  - route:
    - destination:
        host: api.example.com
    timeout: 10s  # Explicit Timeout
    retries:
      attempts: 2
      perTryTimeout: 5s
```

### 4. Use Egress Gateway (Production)

```yaml
# Control external traffic through Egress Gateway in production
# - Centralized monitoring
# - Easy IP whitelist management
# - Consistent security policies
```

### 5. Namespace Isolation

```yaml
# Isolate ServiceEntry by namespace
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: team-a
spec:
  egress:
  - hosts:
    - "team-a/*"  # Only own namespace
    - "istio-system/*"
    - "external/*"  # Shared external services
  outboundTrafficPolicy:
    mode: REGISTRY_ONLY
```

### 6. Documentation Template

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-service
  annotations:
    # Service information
    service-description: "Third-party payment API"
    service-owner: "payments-team@company.com"
    service-documentation: "https://wiki.company.com/payment-api"

    # SLA information
    sla-availability: "99.9%"
    sla-latency-p95: "500ms"
    rate-limit: "1000 req/min"

    # Cost information
    cost-per-request: "$0.01"
    monthly-budget: "$10000"

    # Incident response
    oncall: "payments-oncall"
    escalation: "CTO"
    fallback-strategy: "Use cached data"
```

## References

- [Istio ServiceEntry](https://istio.io/latest/docs/reference/config/networking/service-entry/)
- [Istio Egress Traffic](https://istio.io/latest/docs/tasks/traffic-management/egress/)
- [Istio TLS Origination](https://istio.io/latest/docs/tasks/traffic-management/egress/egress-tls-origination/)
- [Envoy External Services](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery)
