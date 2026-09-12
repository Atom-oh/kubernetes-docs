# Gateway API Quiz

Based on the v1.6 API baseline and the guide’s implementation-specific prerequisites. Each code example is a separate scenario.

## 1. Which is NOT a design goal of Gateway API?

- A. More explicit infrastructure/operator/application resource ownership
- B. API types for several traffic protocols
- C. Standard fields with defined feature support levels
- D. Combining every network function into one object

<details>
<summary>Show answer</summary>

D. GatewayClass, Gateway and Route resources separate responsibilities. Controllers still need to implement the relevant API version, profile and features, and RBAC/admission enforces ownership. Standard fields improve portability without eliminating implementation-specific extensions.

</details>

## 2. Who usually manages GatewayClass in the role-oriented model?

- A. Every application developer independently
- B. Only a backend Service owner
- C. The infrastructure provider or platform/network team
- D. An unauthenticated application client

<details>
<summary>Show answer</summary>

C. GatewayClass selects the installed controller and any supported implementation-specific parameters. Platform operators manage Gateways and attachment policy; developers manage Routes. A referenced namespace’s owner manages its ReferenceGrant. These are operating roles, not automatic Kubernetes permissions.

</details>

## 3. What is the difference between TLS termination and passthrough?

- A. Terminate passes encrypted bytes unchanged
- B. Terminate ends downstream TLS at the gateway; Passthrough lets the backend terminate it
- C. Both require an HTTPS listener with interchangeable modes
- D. Termination always forces plaintext on the backend

<details>
<summary>Show answer</summary>

B. HTTPS termination and TLS passthrough use different listener configurations. Backend encryption after termination is a separate decision, with a supported BackendTLSPolicy or implementation configuration.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-tls
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
  - name: tls-passthrough
    protocol: TLS
    port: 8443
    tls:
      mode: Passthrough
```

The referenced TLS Secret and the appropriate Routes/backends must exist. Passthrough cannot be enabled on an HTTPS listener just by changing mode.

</details>

## 4. How does HTTPRoute express a weighted backend split?

- A. A trafficSplit field
- B. weight on multiple backendRefs
- C. A mandatory canary annotation
- D. A TrafficSplit CRD from another API

<details>
<summary>Show answer</summary>

B. With the guide’s Gateway/Namespace setup and existing backend Services:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-split
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

Weights express relative distribution and do not have to sum to 100. A small sample need not match exactly. They select backends behind this Gateway; they do not shift clients between an old Ingress frontend and a new Gateway frontend.

</details>

## 5. Where is a ReferenceGrant for a cross-namespace backend created?

- A. Always in the Route namespace
- B. In the referenced backend’s namespace, by its owner
- C. Only in kube-system
- D. On the client’s workstation

<details>
<summary>Show answer</summary>

B. The receiver grants the reference. For example:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-shared-api
  namespace: backend-services
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: production
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api
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
        type: PathPrefix
        value: /shared
    backendRefs:
    - name: shared-api
      namespace: backend-services
      port: 80
```

The shared-api Service must exist in backend-services. to.name limits the grant to that Service. Route→Gateway attachment instead uses parentRefs and allowedRoutes; it does not need a ReferenceGrant for that attachment. A grant does not authenticate application users.

</details>

## 6. Which resource is outside the Gateway API v1.6 Standard bundle?

- A. GatewayClass
- B. GRPCRoute
- C. TCPRoute
- D. Istio VirtualService

<details>
<summary>Show answer</summary>

D. VirtualService is an Istio API. The v1.6 Standard bundle includes HTTPRoute, GRPCRoute, TCPRoute, TLSRoute and UDPRoute, among other resources. The old answer that TCPRoute is Experimental is no longer correct. Channel and API version differ: ReferenceGrant v1beta1 remains served in Standard alongside v1, while experimental fields can exist on v1 resources in the Experimental bundle.

</details>

## 7. Which filter rewrites the upstream request without returning a client redirect?

- A. RequestHeaderModifier
- B. ResponseHeaderModifier
- C. URLRewrite
- D. RequestMirror

<details>
<summary>Show answer</summary>

C. URLRewrite changes the upstream path/Host; backendRefs still select the destination. RequestRedirect returns a 3xx response to the client.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-rewrite
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
```

Here /old-api/users becomes /new-api/users. ReplaceFullPath instead replaces the entire path. Those behaviors are different when translating legacy rewrites.

</details>

## 8. Which component does NOT reconcile Gateway API resources?

- A. Istio’s Gateway controller
- B. Cilium’s Gateway controller
- C. kube-proxy
- D. Envoy Gateway

<details>
<summary>Show answer</summary>

C. kube-proxy handles Service forwarding and can participate in a backend network path, but it does not reconcile GatewayClass/Gateway/Route resources. Installing Gateway API CRDs alone does not install any of the listed controllers.

</details>

## 9. Which Gateway API construct expresses an HTTP path rewrite from a legacy Ingress configuration?

- A. The Gateway object name
- B. HTTPRoute URLRewrite filter
- C. A ReferenceGrant from any namespace
- D. Namespace labels alone

<details>
<summary>Show answer</summary>

B. Verify the old rewrite semantics before choosing ReplaceFullPath or ReplacePrefixMatch. The guide’s constant rewrite-target: / requires a full-path replacement, not preservation of a suffix. Other Ingress annotations can map to Gateway settings or controller policy CRDs, and some have no supported equivalent. HTTP-to-HTTPS redirects must be bound to the HTTP listener.

</details>

## 10. How can a Gateway restrict which namespaces attach Routes?

- A. from: All limits attachment to one namespace
- B. from: Same allows its own namespace
- C. from: Selector chooses Namespace labels
- D. Both B and C are valid, with different scopes

<details>
<summary>Show answer</summary>

D. Choose one value for from. For a selector:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-namespace-selector
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
```

The label belongs to the Namespace, not the Route or Pod. Control who can change Namespace labels. allowedRoutes limits attachment; it does not grant cross-namespace backend access or authorize application requests.

</details>

## 11. Which GRPCRoute match selects a specific method of a service?

- A. path.service and path.method
- B. method.service and method.method
- C. grpc.service and grpc.method
- D. rpc.service and rpc.method

<details>
<summary>Show answer</summary>

B. For the guide’s gRPC listener:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata:
  name: quiz-grpc
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
        method: GetUser
    backendRefs:
    - name: user-service
      port: 50051
```

The method name is case-sensitive under the default Exact matching. The backend must serve the expected gRPC transport and have appropriate TLS configuration; a port number alone does not prove that. A service-only method match covers the methods of that service.

</details>

## 12. Which comparison with Ingress is incorrect?

- A. Gateway API separates listener and Route ownership more explicitly
- B. Gateway API defines dedicated TCP/UDP/gRPC routing types
- C. Standard routing fields have implementation support requirements
- D. Gateway API has fewer resource types than Ingress

<details>
<summary>Show answer</summary>

D. Gateway API introduces multiple resource types. Ingress also has IngressClass and can use RBAC/admission; it is inaccurate to say that it has no authorization or ownership controls. Gateway API makes several responsibility and cross-namespace handshakes more explicit. Check controller/version support instead of assuming every API field behaves identically everywhere.

</details>

[Return to the guide](../../networking/04-gateway-api.md)
