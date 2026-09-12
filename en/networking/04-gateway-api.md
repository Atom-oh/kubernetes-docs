# Kubernetes Gateway API

> **API baseline**: Gateway API v1.6 Standard; select the exact bundle supported by your controller.
> **Reviewed**: September 12, 2026

## Overview

Gateway API is the next-generation ingress API for Kubernetes, designed to overcome the limitations of the existing Ingress API and provide more expressive and extensible network routing capabilities. Developed by SIG-Network, it is supported by various implementations including Istio, Cilium, Envoy Gateway, and more.

### Limitations of Ingress API

| Problem | Description |
|---------|-------------|
| **Limited Expressiveness** | Poor support for TCP/UDP/gRPC beyond HTTP routing |
| **Combined Responsibilities** | RBAC/IngressClass can restrict access, but listener and route concerns are less explicitly separated |
| **Annotation Abuse** | Implementation-specific features handled via annotations, reducing portability |
| **Limited Extensibility** | Difficult to add new protocols or features |
| **Cross-Namespace** | Complex routing across namespaces |

### Benefits of Gateway API

![Four Gateway API design goals: expressiveness, responsibility separation, portability and extensibility.](../.gitbook/assets/en-networking-04-gateway-api-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-04-gateway-api-0.html)

Expressiveness, separation of responsibilities, portability and extensibility are independent design goals. Actual feature support depends on the controller and conformance profile; Kubernetes RBAC and admission policies enforce who can change each resource.

## Resource Model

Gateway API uses a layered resource model.

![GatewayClass, Gateway and Route relationships with backend Services in a typical implementation; the exact Gateway infrastructure is controller-specific.](../.gitbook/assets/en-networking-04-gateway-api-1.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-04-gateway-api-1.html)

The figure shows resource relationships and a common gateway deployment model. A Gateway is not universally one cloud load balancer: Istio can provision a proxy Deployment/Service, while VPC Lattice maps it to a service network. The owner of a **referenced namespace** grants cross-namespace backend/Secret access with ReferenceGrant.

### Role Separation

| Role | Managed Resources | Responsibility |
|------|------------------|----------------|
| **Infrastructure Provider** | GatewayClass | Define basic infrastructure configuration |
| **Cluster Operator** | Gateway | Gateway infrastructure and Route attachment policy |
| **Referenced Namespace Owner** | ReferenceGrant | Authorize references to owned backends/Secrets |
| **Application Developer** | HTTPRoute, GRPCRoute, etc. | Define application routing rules |

## GatewayClass

GatewayClass defines the controller and configuration to use when creating Gateways.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: istio
spec:
  controllerName: istio.io/gateway-controller
  description: Istio Gateway Controller for production workloads
```

A GatewayClass selects an already installed controller; creating the class does not install that controller. The definitions below are alternatives. Use a class whose `Accepted` condition is true, and replace the example class names with the accepted names in your cluster.

`parametersRef` support and its group/kind depend on the implementation. For Istio 1.31, a per-Gateway ConfigMap goes under `Gateway.spec.infrastructure.parametersRef` in the Gateway's namespace. Class-wide defaults use a ConfigMap labeled `gateway.istio.io/defaults-for-class` in Istio's root namespace. The ALB→Istio example below demonstrates the per-Gateway form.

### GatewayClass by Implementation

```yaml
# Istio
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: istio
spec:
  controllerName: istio.io/gateway-controller
---
# Cilium
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium
spec:
  controllerName: io.cilium/gateway-controller
---
# AWS Gateway API Controller
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
# Envoy Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: envoy-gateway
spec:
  controllerName: gateway.envoyproxy.io/gatewayclass-controller
---
# Contour
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: contour
spec:
  controllerName: projectcontour.io/gateway-controller
---
# NGINX Gateway Fabric
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: nginx
spec:
  controllerName: gateway.nginx.org/nginx-gateway-controller
```

## Gateway

Gateway describes traffic-handling infrastructure and listeners. Its mapping to proxy workloads, managed load balancers, or a service network depends on the controller.

### Basic Gateway Configuration

These are separate configuration scenarios, not a single set of Routes to apply together. Overlapping Routes on the same host/listener can change precedence. Install the selected controller and its compatible CRDs first, create `gateway-system`, and provide the named Services, ready endpoints, and TLS Secrets. Certificates must cover the configured DNS names. Configure the data-plane Service exposure, DNS and network controls for the platform; a GatewayClass or a requested IP address does not reserve an external address by itself.

The HTTP/gRPC/TCP/TLS examples use Istio 1.31. The UDP example uses a separate Envoy Gateway instance because Istio 1.31 explicitly rejects UDP listeners. Envoy Gateway 1.9 requires Gateway API 1.6.1 and its published Kubernetes version combination. Review shared CRDs before changing their version/channel.

The Namespace in the basic example has `gateway-access: "true"`. This is a **Namespace label**, and permission to change it should stay with the administrators controlling Gateway access. `allowedRoutes` does not authenticate application clients.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    gateway-access: 'true'
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: production-gateway
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: tls-cert
        namespace: gateway-system
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
```

### Advanced Gateway Configuration

The following is a separate Gateway named `multi-protocol-gateway`. The gRPC, TLS and TCP Routes below attach to its matching listener names. The database and other TCP examples have distinct listeners, so both can be used without competing for one L4 listener.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: multi-protocol-gateway
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
  - name: https-wildcard
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: wildcard-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: HTTPRoute
  - name: grpc
    protocol: HTTPS
    port: 443
    hostname: grpc.example.com
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: grpc-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: GRPCRoute
  - name: tcp-passthrough
    protocol: TLS
    port: 8443
    tls:
      mode: Passthrough
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: TLSRoute
  - name: tcp
    protocol: TCP
    port: 9000
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: TCPRoute
  - name: database
    protocol: TCP
    port: 5432
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: TCPRoute
```

### TLS Modes

Termination ends the downstream TLS connection at the gateway. The backend connection is configured separately and can use HTTP or TLS, for example through a supported BackendTLSPolicy. Passthrough uses a `TLS` listener with `mode: Passthrough`, and the backend terminates TLS. A `HTTPS` listener cannot be switched to passthrough merely by changing `mode`.

| Mode | Description | Use Case |
|------|-------------|----------|
| **Terminate** | TLS termination at Gateway | Standard HTTPS |
| **Passthrough** | Pass TLS to backend | End-to-end encryption |

```yaml
# TLS Terminate example
listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
        - kind: Secret
          name: server-cert
---
# TLS Passthrough example
listeners:
  - name: tls-passthrough
    protocol: TLS
    port: 443
    tls:
      mode: Passthrough
```

## HTTPRoute

HTTPRoute defines routing rules for HTTP/HTTPS traffic.

### Basic HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: basic-route
  namespace: production
spec:
  # Gateway to attach to
  parentRefs:
    - name: production-gateway
      namespace: gateway-system
      sectionName: https  # Target specific listener

  # Host matching
  hostnames:
    - "api.example.com"
    - "www.example.com"

  # Routing rules
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api/v1
      backendRefs:
        - name: api-v1-service
          port: 80

    - matches:
        - path:
            type: PathPrefix
            value: /api/v2
      backendRefs:
        - name: api-v2-service
          port: 80

    # Default path
    - backendRefs:
        - name: default-service
          port: 80
```

### Advanced Matching Rules

Fields inside one `matches` item are ANDed; multiple items are ORed. PathPrefix matches path elements rather than an arbitrary string prefix. RegularExpression support and syntax are implementation-specific. The demo tenant header below is a routing selector that any client could supply, not authentication for the administrative application.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: advanced-matching
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: Exact
        value: /health
    backendRefs:
    - name: health-service
      port: 80
  - matches:
    - path:
        type: RegularExpression
        value: /users/[0-9]+
    backendRefs:
    - name: user-service
      port: 80
  - matches:
    - headers:
      - name: X-Version
        value: v2
    backendRefs:
    - name: api-v2-service
      port: 80
  - matches:
    - queryParams:
      - name: debug
        value: 'true'
    backendRefs:
    - name: debug-service
      port: 80
  - matches:
    - method: POST
      path:
        type: PathPrefix
        value: /api/data
    backendRefs:
    - name: write-service
      port: 80
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /api/data
    backendRefs:
    - name: read-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /admin
      headers:
      - name: X-Demo-Tenant
        type: Exact
        value: operations
    backendRefs:
    - name: admin-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /api
    - path:
        type: PathPrefix
        value: /v1
    backendRefs:
    - name: api-service
      port: 80
```

### Filters

Header modifiers set literal values. `X-Example-Source: gateway-demo` is a static marker, not a generated unique request ID; use the proxy/application's tracing facilities for IDs. The mirror example uses its own `/mirror` path so the earlier `/api` rule cannot shadow it. It copies GET requests to a shadow backend and ignores that backend's response. Isolate side effects and review the data/credentials copied to the shadow service. The public cache header is appropriate only for content that is actually safe to cache publicly.

Filters allow modifying requests/responses.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: filtered-route
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: RequestHeaderModifier
      requestHeaderModifier:
        add:
        - name: X-Example-Source
          value: gateway-demo
        set:
        - name: X-Api-Version
          value: v1
        remove:
        - X-Internal-Header
    backendRefs:
    - name: api-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /public
    filters:
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: Cache-Control
          value: public, max-age=3600
        set:
        - name: X-Content-Type-Options
          value: nosniff
    backendRefs:
    - name: public-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /old-api
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /new-api
        hostname: new-api.example.com
    backendRefs:
    - name: new-api-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /legacy
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        hostname: new.example.com
        port: 443
        statusCode: 301
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /modern
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /mirror
    filters:
    - type: RequestMirror
      requestMirror:
        backendRef:
          name: shadow-service
          port: 80
    backendRefs:
    - name: main-service
      port: 80
```

### Traffic Splitting (Weights)

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: canary-route
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

### Timeouts and Retries

The v1.6 Standard schema includes `timeouts`; it does not include `HTTPRoute.rules.retry`. Experimental schemas add retry fields and have separate admission/implementation requirements. The example below only sets budgets for GET requests: `backendRequest` must not exceed the nonzero total `request` budget.

Omitting a retry field does not prove that a client, gateway, mesh proxy or SDK will never retry. Configure and verify each applicable layer, especially for non-idempotent writes. A retry count of zero is not a valid way to disable the experimental v1.6 `retry.attempts` field, whose minimum is one. Use the implementation's documented controls and application idempotency behavior.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: resilient-route
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
      method: GET
    timeouts:
      request: 30s
      backendRequest: 25s
    backendRefs:
    - name: api-service
      port: 80
```

## GRPCRoute

Backends must serve the expected gRPC/HTTP2 transport and appropriate TLS configuration. A port number alone does not configure that behavior.

Defines routing rules for gRPC traffic.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata:
  name: grpc-route
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: grpc
  hostnames:
  - grpc.example.com
  rules:
  - matches:
    - method:
        service: myapp.UserService
    backendRefs:
    - name: user-grpc-service
      port: 50051
  - matches:
    - method:
        service: myapp.OrderService
        method: CreateOrder
    backendRefs:
    - name: order-grpc-service
      port: 50052
  - matches:
    - headers:
      - name: x-environment
        value: staging
    backendRefs:
    - name: staging-grpc-service
      port: 50051
  - backendRefs:
    - name: default-grpc-service
      port: 50051
```

## TCPRoute

Defines TCP traffic routing.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: database-route
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: database
  rules:
  - backendRefs:
    - name: database-service
      port: 5432
---
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: tcp-loadbalance
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: tcp
  rules:
  - backendRefs:
    - name: tcp-backend-1
      port: 9000
      weight: 50
    - name: tcp-backend-2
      port: 9000
      weight: 50
```

## TLSRoute

Defines TLS passthrough traffic routing.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TLSRoute
metadata:
  name: tls-passthrough-route
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: tcp-passthrough
  hostnames:
  - secure.example.com
  rules:
  - backendRefs:
    - name: secure-backend
      port: 8443
```

## UDPRoute

This scenario requires an installed Envoy Gateway controller with an accepted `envoy-gateway` class, its compatible Gateway API bundle, and the `dns-service` UDP backend. It exposes UDP port 5300 and routes to backend port 53. Envoy's UDP proxy is non-transparent: the backend sees the gateway's source IP/port. Ensure the platform load-balancer/Service supports this UDP exposure.

Defines UDP traffic routing.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: udp-gateway
  namespace: gateway-system
spec:
  gatewayClassName: envoy-gateway
  listeners:
  - name: udp
    protocol: UDP
    port: 5300
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: UDPRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: UDPRoute
metadata:
  name: dns-route
  namespace: production
spec:
  parentRefs:
  - name: udp-gateway
    namespace: gateway-system
    sectionName: udp
  rules:
  - backendRefs:
    - name: dns-service
      port: 53
```

## ReferenceGrant

ReferenceGrant is created in the namespace **containing the referenced Service or Secret**, by that namespace's owner. `from` selects source group/kind/namespace; `to.name` can constrain the target name. Grants are additive and authorize references, not application callers.

Route→Gateway attachment across namespaces uses `parentRefs` plus the Gateway listener's `allowedRoutes` handshake, rather than a ReferenceGrant. Backend and certificate references use ReferenceGrant as shown below. The named `shared-api` Service and `shared-tls` Secret must exist; a grant alone does not create them.

ReferenceGrant allows cross-namespace references.

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-routes-to-backend
  namespace: backend-services
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: production
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: staging
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-gateway-to-secrets
  namespace: cert-management
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: Gateway
    namespace: gateway-system
  to:
  - group: ''
    kind: Secret
    name: shared-tls
```

## Implementation Comparison

### Major Implementations

| Implementation | Controller | Features |
|----------------|------------|----------|
| **Istio** | istio.io/gateway-controller | Service Mesh integration, advanced traffic management |
| **Cilium** | io.cilium/gateway-controller | Cilium networking with Envoy L7 processing |
| **Envoy Gateway** | gateway.envoyproxy.io/gatewayclass-controller | Envoy-based, standards compliant |
| **AWS Gateway API Controller** | application-networking.k8s.aws/gateway-api-controller | VPC Lattice integration |
| **Contour** | projectcontour.io/gateway-controller | Envoy-based, simple configuration |
| **NGINX Gateway Fabric** | gateway.nginx.org/nginx-gateway-controller | NGINX-based |
| **Traefik** | traefik.io/gateway-controller | Dynamic configuration |

### Versioned Implementation Notes

The API's release channel, a feature's Core/Extended/implementation-specific support level, and a controller's conformance profile are different concepts. A CRD accepting a field does not prove the controller implements it. Check published conformance results and resource conditions, including `Accepted`, `ResolvedRefs` and `Programmed` where applicable.

| Implementation checked | Verified scope and important limits |
|---|---|
| Istio **1.31.0** | HTTP/gRPC and v1 TCP/TLS routes; UDP listeners are explicitly unsupported. Configurable Envoy data plane, not a guarantee that every Gateway API extension is supported |
| Cilium **1.20.1** | Gateway API **1.6.1**, including TCPRoute/UDPRoute; combines Cilium networking with Envoy for L7 processing |
| Envoy Gateway **1.9.1** | Gateway API **1.6.1**; published Kubernetes matrix is **1.33–1.36**. Supports UDP routing and TLS passthrough with their documented transport behavior |
| AWS Load Balancer Controller **3.5.0** | Gateway API **1.6.0**; ALB handles HTTP/gRPC and NLB handles L4 routes. Only the oldest attached L4 Route is eligible per NLB listener; use one Route per listener |
| AWS Gateway API Controller **2.1.3** | VPC Lattice integration; v2.1 requires Gateway API **1.5+**. HTTPRoute, GRPCRoute and TLSRoute are supported. TCP resource access is a separate Lattice resource-configuration model, not generic TCPRoute/UDPRoute support |
| Contour **1.33.7** | Built with Gateway API **1.3.0** and release-tested on Kubernetes **1.32–1.34**. Documents HTTP/gRPC/TCP/TLS routes; use its matching channel/provisioning configuration rather than applying a newer bundle blindly |
| NGINX Gateway Fabric **2.7.0** | Gateway API **1.6.1**, published Kubernetes minimum **1.32**; adds v1 TCPRoute/UDPRoute support. Separate product from retired community ingress-nginx |

These notes replace a versionless yes/no feature grid. Consult each implementation's documentation for individual filters, TLS policies, extensions, supported versions and operating requirements. Contour's bundled compatibility page does not have a 1.33.7-specific row; the API dependency and Kubernetes range above are taken from that exact release's module file and release notes.

## AWS Load Balancer Controller Gateway API Support

Gateway API reached GA in **LBC v3.0.0 on 2026-01-23**. Existing Ingress and Service APIs remain supported, so a Gateway migration can be planned independently of the controller upgrade. Current v3.5.0 requires the compatible Gateway API and LBC Gateway CRDs described in the [LBC installation guide](./03-aws-lb-controller.md). EKS Auto Mode has a separate managed implementation; self-managed LBC features do not automatically describe Auto Mode.

The retired controller is the Kubernetes community **ingress-nginx** project, whose maintenance ended in March 2026. This does not mean the Kubernetes Ingress API or F5's other NGINX products were retired.

The `keepTLSSecret=false` workaround in v3.0 release notes applied to users **staying on older versions** affected by the cert-manager ownership bug. Users upgrading to v3.0 received the fix without that extra action. Follow the current chart's certificate-management options rather than applying the historical mitigation to every upgrade.

### LBC v3.4.0 Migration Tools

The **2026-06-03** release introduced the real `lbc-migrate` CLI and Migration Console. They target working **LBC Ingress** resources; they are not a generic converter for every Ingress implementation.

- `lbc-migrate` reads files or, with `--from-cluster`, lists/gets cluster resources. It translates supported annotations and emits Gateway API resources. The default output has the LBC Gateway dry-run annotation.
- The Migration Console compares controller-generated resource plans. It requires the appropriate plan annotations, feature configuration and read access. Treat plans as configuration data that may need access restrictions and redaction.
- Applying reviewed live Gateway manifests creates **new ALBs alongside the existing ALBs**. Validate them and shift frontend traffic separately. Backend weights inside one HTTPRoute do not perform this frontend migration.

For a binary built from the selected LBC release, file-based translation can start with:

```bash
lbc-migrate -f ingress.yaml --output-dir ./gateway-output/
```

The converter does not generate the existing Deployments/Services or revalidate all Ingress annotations. Review unsupported annotations, Service/IngressClassParams overrides, cross-namespace IngressGroup membership, rule precedence and TLS settings. External target groups already associated with the old ALB cannot simply be attached to the new ALB simultaneously; plan a compatible duplicate/cutover strategy.

The tools provide a migration workflow, not a zero-downtime guarantee. See the [versioned migration guide](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress2gateway/migrate_from_ingress.md) and [CLI reference](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/ingress2gateway/lbc_migrate_reference.md).

## Migrating from Ingress to Gateway API

### Step-by-Step Migration Guide

#### Step 1: Analyze Existing Ingress

The following is a **historical community ingress-nginx input** used to explain a manual configuration translation to Istio Gateway API. It is not a new ingress-nginx installation recommendation or input for the LBC-specific converter above. Preserve the actual request behavior, not just the names of settings.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: 'true'
  namespace: default
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /api/v1
        pathType: Prefix
        backend:
          service:
            name: api-v1
            port:
              number: 80
      - path: /api/v2
        pathType: Prefix
        backend:
          service:
            name: api-v2
            port:
              number: 80
```

#### Step 2: Create Gateway and GatewayClass

The new Gateway is named `migration-gateway`. The existing `api-tls` Secret remains in `default`; a ReferenceGrant in that namespace explicitly allows this Gateway namespace to reference it. Provide a certificate valid for `api.example.com`. The `default` Namespace's built-in name label supplies the route-attachment selector.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: production
spec:
  controllerName: istio.io/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: migration-tls
  namespace: default
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: Gateway
    namespace: gateway-system
  to:
  - group: ''
    kind: Secret
    name: api-tls
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: migration-gateway
  namespace: gateway-system
spec:
  gatewayClassName: production
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            kubernetes.io/metadata.name: default
    hostname: api.example.com
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: api-tls
        namespace: default
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            kubernetes.io/metadata.name: default
    hostname: api.example.com
```

#### Step 3: Create HTTPRoute

The redirect Route attaches only to the HTTP listener. The HTTPS Route forwards application requests. The old `rewrite-target: /` example replaces the entire matched request path with `/`, so the translated example uses **ReplaceFullPath**. ReplacePrefixMatch would preserve a suffix (`/api/v1/users` → `/users`) and change behavior. Test root paths, subpaths, query strings and redirects against the old application before cutover.

The redirect below assumes ingress-nginx’s default **308**, preserving the request method/body; check any `http-redirect-code` override. Its rewrite annotation also enables case-insensitive regex locations for that host, while Gateway API PathPrefix is case-sensitive and matches path elements. Thus `/API/V1` or `/api/v10` can differ. The example demonstrates a stricter PathPrefix policy, not complete matching equivalence. If clients depend on the old behavior, design and test a supported regex match or another explicit compatibility rule before switching.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-route
  namespace: default
spec:
  parentRefs:
  - name: migration-gateway
    namespace: gateway-system
    sectionName: http
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-route-https
  namespace: default
spec:
  parentRefs:
  - name: migration-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api/v1
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplaceFullPath
          replaceFullPath: /
    backendRefs:
    - name: api-v1
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /api/v2
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplaceFullPath
          replaceFullPath: /
    backendRefs:
    - name: api-v2
      port: 80
```

#### Step 4: Shift Frontend Traffic

Validate the new Gateway's address, certificate, HTTP redirects, route matching, backend behavior and observability before moving clients. Shift traffic using the mechanism appropriate for the frontends, such as reviewed DNS/load-balancer routing, then monitor failures and latency. Account for DNS caches, persistent connections and sessions. Keep a tested way to send traffic back to the old frontend.

HTTPRoute backend weights control traffic **inside the chosen Gateway**; the dedicated traffic-splitting section explains that operation. For the frontend migration, retain the old Ingress/controller until clients have moved and the required drain/rollback checks have completed.

### Migration Checklist

- [ ] Analyze existing Ingress annotations
- [ ] Select implementation and create GatewayClass
- [ ] Create Gateway resource and configure listeners
- [ ] Convert routing rules to HTTPRoute
- [ ] Configure allowedRoutes for attachment and ReferenceGrant for backend/Secret references
- [ ] Migrate TLS certificates
- [ ] Verify and shift frontend traffic with a tested rollback path
- [ ] Set up monitoring and logging
- [ ] Remove old Ingress resources only after cutover and drain/rollback checks

## EKS Patterns

### AWS Gateway API Controller (VPC Lattice)

Use the installed controller, `my-network` service network with its reviewed `AWS_IAM` policy, caller permissions, and `service-stable:8080` backend from the [VPC Lattice guide](./02-vpc-lattice.md). The Gateway name selects the network; it does not create it. This separate Route has its own Lattice service and domain. The IAMAuthPolicy below secures that service; retain the network-level policy during reconciliation. Retrieve the assigned Route domain and use the guide's signed HTTPS client. The `unused` certificate reference follows this controller's documented AWS-managed-certificate behavior, not generic Kubernetes Secret loading.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-network
  namespace: lattice-demo
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: unused
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: lattice-route
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
---
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: lattice-route-auth
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: lattice-route
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/MyAppRole"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/api","/api/*"]}}}]}'
```

### Using with ALB Controller

This topology uses an ALB in front of an Istio gateway when the application needs Istio's gateway behavior. The ConfigMap sets the generated Service to ClusterIP through Istio's documented infrastructure parameters. The ALB Ingress is in the **same namespace** as that Service and references its generated name, `internal-gateway-istio`.

The application HTTPRoute is in the labeled `production` namespace and points to an existing `api-service:80` there. Replace the ACM ARN and configure the LBC/network prerequisites. TLS terminates at the ALB in this example; its connection to Istio is HTTP. Permit the actual gateway traffic and health ports through security controls. `/healthz/ready` on 15021 checks gateway readiness, not every application's health. Verify Route conditions and application responses separately.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: internal-gateway-options
  namespace: istio-system
data:
  service: |
    spec:
      type: ClusterIP
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: internal-gateway
  namespace: istio-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
  infrastructure:
    parametersRef:
      group: ''
      kind: ConfigMap
      name: internal-gateway-options
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: alb-internal-route
  namespace: production
spec:
  parentRefs:
  - name: internal-gateway
    namespace: istio-system
    sectionName: http
  hostnames:
  - api.example.com
  rules:
  - backendRefs:
    - name: api-service
      port: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alb-to-gateway
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
    alb.ingress.kubernetes.io/healthcheck-port: '15021'
    alb.ingress.kubernetes.io/healthcheck-path: /healthz/ready
  namespace: istio-system
spec:
  ingressClassName: alb
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-gateway-istio
            port:
              number: 80
```

## API Channels and Maturity

### Channel and API Version Are Separate

| Gateway API v1.6.0 bundle | Included resources/fields |
|---|---|
| Standard | GatewayClass, Gateway, HTTPRoute, GRPCRoute, TLSRoute, TCPRoute, UDPRoute, ReferenceGrant, BackendTLSPolicy and ListenerSet |
| Experimental | The Standard content plus experimental fields such as HTTPRoute retry/session persistence, and XBackend, XBackendTrafficPolicy and XMesh |

Current Standard examples use `v1` for the Route types. The v1.6.0 Standard bundle no longer **serves** the older TLSRoute/TCPRoute/UDPRoute alpha versions. The Experimental bundle still serves some deprecated versions, so a manifest working there does not prove it works with Standard.

ReferenceGrant is a useful counterexample to “Standard always means v1 only”: the v1.6.0 bundle serves both `v1` and `v1beta1`, with `v1beta1` as its storage version. The ReferenceGrant examples here retain the served beta version.

New experimental X resources use `gateway.networking.x-k8s.io`. Experimental fields on established resources can still be in `gateway.networking.k8s.io`; the entire Experimental channel did not move to another group. Its compatibility guarantees differ from Standard, and admission policies protect channel/field boundaries. Review the published upgrade procedure instead of deleting shared CRDs or admission policies to force a change.

### v1.6 Release Context

Gateway API v1.6.0 was published on **2026-06-29 UTC / 2026-06-30 KST**. TCPRoute and UDPRoute graduated to Standard `v1`. GRPCRoute and TLSRoute are also in the current Standard bundle. Choose the bundle/channel supported by the selected implementation, rather than equating the newest catalog version with compatibility.

## Comparison with Ingress API

| Aspect | Ingress | Gateway API |
|---|---|---|
| Resource model | Ingress and IngressClass; listener/routing concerns largely combined | GatewayClass, Gateway and separate Route types |
| Authorization | Kubernetes RBAC/admission can restrict ownership | RBAC/admission plus explicit attachment and reference handshakes |
| HTTP routing | Standard HTTP routing | Standard HTTPRoute fields, with support levels for individual features |
| TCP/UDP/gRPC | Controller-specific extensions beyond the Ingress API | Dedicated API types; actual support depends on controller/version |
| TLS passthrough / traffic split / rewrites | Controller-specific configuration | Relevant Route/filter fields and implementation support requirements |
| Cross-namespace references | Implementation-specific behavior | ReferenceGrant for backends/Secrets; allowedRoutes for Gateway attachment |
| Portability | Reduced by differing annotation semantics | Improved by standard fields and conformance, with extensions still varying |

## Best Practices

### 1. Follow Role Separation

```yaml
# Infrastructure team: Manage GatewayClass
# Platform team: Manage Gateway
# App team: Manage HTTPRoute
```

### 2. Least Privilege ReferenceGrant

```yaml
# Explicitly allow only required namespaces
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: minimal-access
  namespace: backend
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: frontend  # Specific namespace only
  to:
    - group: ""
      kind: Service
      name: specific-service  # Specific service only
```

### 3. Gateway Separation

```yaml
# Separate Gateway by environment
# production-gateway, staging-gateway

# Separate Gateway by protocol
# http-gateway, grpc-gateway
```

### 4. Monitoring Configuration

```yaml
# Prometheus metrics collection (varies by implementation)
# - Request count, latency, error rate
# - Backend status
# - TLS certificate expiry
```

---

## References

- [Gateway API Official Documentation](https://gateway-api.sigs.k8s.io/)
- [Gateway API GitHub](https://github.com/kubernetes-sigs/gateway-api)
- [Istio Gateway API Support](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)
- [Cilium Gateway API](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/gateway-api/gateway-api.rst)
- [AWS Gateway API Controller](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs)
- [Envoy Gateway](https://gateway.envoyproxy.io/)

- [Gateway API 1.6 versioning](https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.0/site/content/en/docs/concepts/versioning.md)
- [ReferenceGrant and attachment exceptions](https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.0/site/content/en/reference/api-types/referencegrant.md)
- [Envoy Gateway compatibility](https://github.com/envoyproxy/gateway/blob/v1.9.1/site/content/en/news/releases/matrix.md)
- [NGINX Gateway Fabric 2.7 release](https://github.com/nginx/nginx-gateway-fabric/blob/v2.7.0/CHANGELOG.md)
- [Contour 1.33.7 release](https://github.com/projectcontour/contour/releases/tag/v1.33.7)
- [Community ingress-nginx retirement](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)

- [Legacy ingress-nginx redirect and rewrite behavior](https://github.com/kubernetes/ingress-nginx/blob/main/docs/user-guide/nginx-configuration/annotations.md)
- [Legacy ingress-nginx redirect-code configuration](https://github.com/kubernetes/ingress-nginx/blob/main/docs/user-guide/nginx-configuration/configmap.md)
