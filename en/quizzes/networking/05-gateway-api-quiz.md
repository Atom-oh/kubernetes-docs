# Gateway API Quiz

This quiz tests your understanding of Kubernetes Gateway API resource model, implementations, and migration from Ingress.

## Quiz Questions

### 1. Which is NOT a way Gateway API improves upon the existing Ingress API?

A. Role-based resource separation (infrastructure provider, cluster operator, application developer)
B. Native support for various protocols like TCP, UDP, gRPC
C. Feature implementation through standardized fields instead of annotations
D. Integration of all network functions into a single resource

<details>
<summary>Show Answer</summary>

**Answer: D. Integration of all network functions into a single resource**

**Explanation:**
Gateway API improvements:
- **Role separation**: Responsibility separated into GatewayClass (infrastructure), Gateway (operator), Routes (developer)
- **Multiple protocols**: HTTPRoute, GRPCRoute, TCPRoute, TLSRoute, UDPRoute
- **Standardization**: Feature definition through explicit fields without annotations
- **Extensibility**: Easy to add new features based on CRDs

Gateway API is separated into multiple resources, so "single resource integration" is incorrect.

</details>

### 2. In Gateway API's role separation, who manages GatewayClass?

A. Application developer
B. Cluster operator
C. Infrastructure provider
D. Security administrator

<details>
<summary>Show Answer</summary>

**Answer: C. Infrastructure provider**

**Explanation:**
Gateway API role separation:

| Role | Managed Resources | Responsibility |
|------|------------------|----------------|
| **Infrastructure Provider** | GatewayClass | Define basic infrastructure config, specify controller |
| **Cluster Operator** | Gateway, ReferenceGrant | Load balancer provisioning, namespace permission management |
| **Application Developer** | HTTPRoute, GRPCRoute, etc. | Define application routing rules |

GatewayClass is defined by cloud providers or network teams.

</details>

### 3. What is the correct difference between TLS termination and passthrough in Gateway?

A. Terminate passes TLS to backend, Passthrough terminates at Gateway
B. Terminate terminates TLS at Gateway, Passthrough passes TLS to backend
C. Both modes behave identically
D. Terminate supports only HTTP, Passthrough supports only HTTPS

<details>
<summary>Show Answer</summary>

**Answer: B. Terminate terminates TLS at Gateway, Passthrough passes TLS to backend**

**Explanation:**
TLS modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Terminate** | TLS terminated at Gateway, backend receives plaintext | Standard HTTPS, centralized certificate management |
| **Passthrough** | TLS passed through to backend as-is | End-to-end encryption, backend manages certificates |

```yaml
listeners:
  - name: https
    protocol: HTTPS
    tls:
      mode: Terminate  # or Passthrough
```

</details>

### 4. How do you implement traffic splitting (weights) in HTTPRoute?

A. Use `trafficSplit` field
B. Specify `weight` field on multiple `backendRefs`
C. Use `canary` annotation
D. Create separate TrafficSplit CRD

<details>
<summary>Show Answer</summary>

**Answer: B. Specify `weight` field on multiple `backendRefs`**

**Explanation:**
Traffic splitting in HTTPRoute:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
spec:
  rules:
    - backendRefs:
        - name: app-stable
          port: 80
          weight: 90  # 90%
        - name: app-canary
          port: 80
          weight: 10  # 10%
```

Use cases:
- Canary deployments
- A/B testing
- Blue-green deployments

Weights don't need to sum to 100; they're calculated as ratios.

</details>

### 5. What is the primary purpose of ReferenceGrant?

A. Gateway resource permission management
B. Allow cross-namespace references
C. API version compatibility management
D. TLS certificate authorization

<details>
<summary>Show Answer</summary>

**Answer: B. Allow cross-namespace references**

**Explanation:**
ReferenceGrant usage:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-routes
  namespace: backend-services
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: frontend
  to:
    - group: ""
      kind: Service
```

Use cases:
- Allow referencing Services in other namespaces
- Gateway referencing Secrets (TLS certificates) in other namespaces
- Explicit authorization for security

Cross-namespace references are blocked by default.

</details>

### 6. Which is NOT a resource included in the Gateway API Standard channel?

A. GatewayClass
B. Gateway
C. HTTPRoute
D. TCPRoute

<details>
<summary>Show Answer</summary>

**Answer: D. TCPRoute**

**Explanation:**
Gateway API channel classification:

**Standard Channel (GA)**:
- GatewayClass
- Gateway
- HTTPRoute
- ReferenceGrant

**Experimental Channel (Beta/Alpha)**:
- GRPCRoute
- TCPRoute
- TLSRoute
- UDPRoute

Standard channel resources use `gateway.networking.k8s.io/v1` API version, Experimental uses `v1alpha2` or `v1beta1`.

</details>

### 7. Which HTTPRoute filter type changes the request to a different URL?

A. RequestHeaderModifier
B. ResponseHeaderModifier
C. URLRewrite
D. RequestMirror

<details>
<summary>Show Answer</summary>

**Answer: C. URLRewrite**

**Explanation:**
HTTPRoute filter types:

| Filter | Description |
|--------|-------------|
| RequestHeaderModifier | Add/modify/remove request headers |
| ResponseHeaderModifier | Add/modify/remove response headers |
| **URLRewrite** | Change URL path or host |
| RequestRedirect | Redirect to different URL (3xx response) |
| RequestMirror | Mirror traffic (copy to shadow service) |

```yaml
filters:
  - type: URLRewrite
    urlRewrite:
      path:
        type: ReplacePrefixMatch
        replacePrefixMatch: /new-api
      hostname: "new-api.example.com"
```

</details>

### 8. Which is NOT an implementation that supports Gateway API?

A. Istio
B. Cilium
C. kube-proxy
D. Envoy Gateway

<details>
<summary>Show Answer</summary>

**Answer: C. kube-proxy**

**Explanation:**
Gateway API implementations:

| Implementation | Controller |
|----------------|------------|
| **Istio** | istio.io/gateway-controller |
| **Cilium** | io.cilium/gateway-controller |
| **Envoy Gateway** | gateway.envoyproxy.io/gatewayclass-controller |
| **AWS Gateway API Controller** | application-networking.k8s.aws/gateway-api-controller |
| **Contour** | projectcontour.io/gateway-controller |
| **NGINX Gateway Fabric** | gateway.nginx.org/nginx-gateway-controller |

kube-proxy handles Service ClusterIP/NodePort routing and is unrelated to Gateway API.

</details>

### 9. When migrating from Ingress to Gateway API, what Gateway API feature corresponds to Ingress annotations?

A. Gateway metadata
B. HTTPRoute matches and filters
C. GatewayClass parameters
D. ReferenceGrant spec

<details>
<summary>Show Answer</summary>

**Answer: B. HTTPRoute matches and filters**

**Explanation:**
Ingress annotation → Gateway API mapping:

| Ingress annotation | Gateway API |
|-------------------|-------------|
| `nginx.ingress.kubernetes.io/rewrite-target` | HTTPRoute filter: URLRewrite |
| `nginx.ingress.kubernetes.io/ssl-redirect` | HTTPRoute filter: RequestRedirect |
| `nginx.ingress.kubernetes.io/canary-weight` | HTTPRoute backendRefs weight |
| Path-based routing | HTTPRoute matches path |
| Header-based routing | HTTPRoute matches headers |

Gateway API uses explicit fields instead of annotations for better portability.

</details>

### 10. What is the configuration to allow only Routes from specific namespaces in Gateway?

A. `allowedRoutes.namespaces.from: All`
B. `allowedRoutes.namespaces.from: Same`
C. `allowedRoutes.namespaces.from: Selector`
D. Both B and C are possible

<details>
<summary>Show Answer</summary>

**Answer: D. Both B and C are possible**

**Explanation:**
Gateway allowedRoutes configuration:

```yaml
listeners:
  - name: https
    allowedRoutes:
      namespaces:
        from: All  # All namespaces
        # or
        from: Same  # Only same namespace as Gateway
        # or
        from: Selector  # Select by label selector
        selector:
          matchLabels:
            gateway-access: "true"
```

- **All**: Allow Routes from all namespaces
- **Same**: Only allow from same namespace as Gateway
- **Selector**: Only allow from namespaces with specific labels

</details>

### 11. What is the matches configuration for routing to a specific method of a specific service in GRPCRoute?

A. `path.service` and `path.method`
B. `method.service` and `method.method`
C. `grpc.service` and `grpc.method`
D. `rpc.service` and `rpc.method`

<details>
<summary>Show Answer</summary>

**Answer: B. `method.service` and `method.method`**

**Explanation:**
GRPCRoute matching:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
spec:
  rules:
    - matches:
        - method:
            service: "myapp.UserService"
            method: "GetUser"
      backendRefs:
        - name: user-service
          port: 50051
```

gRPC routing options:
- Service only: All methods of that service
- Service + method: Specific method only
- Header-based routing also supported

</details>

### 12. Which comparison between Gateway API and Ingress API is NOT correct?

A. Gateway API supports role-based separation, Ingress does not
B. Gateway API natively supports TCP/UDP, Ingress does not
C. Gateway API natively supports traffic splitting, Ingress requires annotations
D. Gateway API uses fewer resource types than Ingress

<details>
<summary>Show Answer</summary>

**Answer: D. Gateway API uses fewer resource types than Ingress**

**Explanation:**
Gateway API vs Ingress:

| Feature | Ingress | Gateway API |
|---------|---------|-------------|
| Resource count | 1 (Ingress) | Multiple (GatewayClass, Gateway, Routes, etc.) |
| Role separation | None | 3-tier separation |
| TCP/UDP | Not supported | Native support |
| Traffic splitting | Annotation | Native (weight) |
| Extensibility | Limited | CRD-based |

Gateway API uses more resource types, but this provides role separation and flexibility.

</details>

---

## Additional Learning Resources

- [Gateway API Official Documentation](https://gateway-api.sigs.k8s.io/)
- [Gateway API GitHub](https://github.com/kubernetes-sigs/gateway-api)
- [Implementation-specific Guides](https://gateway-api.sigs.k8s.io/implementations/)
