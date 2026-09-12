# Cilium Service Mesh Ingress & Gateway Quiz

Review baseline: Cilium 1.20.1, Gateway API 1.6.1 and AWS LBC 3.5.0. Read the [guide](../../../service-mesh/cilium-service-mesh/05-ingress-gateway.md) and its primary sources.

## Quiz Questions

### 1. What does Cilium Ingress `loadbalancerMode: shared` share?

- A. One frontend across every controller in the cluster
- B. The shared Cilium Ingress Service for resources using that mode
- C. Only an internal NodePort
- D. Every Gateway API Gateway automatically

<details>
<summary>Show Answer</summary>

**Answer: B. The shared Cilium Ingress Service for resources using that mode**

The setting applies to Cilium-managed Ingress resources using shared mode. Dedicated-mode overrides and other controllers are separate. A shared GatewayClass also does not imply one shared cloud load balancer.

</details>

### 2. How does an HTTPRoute explicitly attach only to a Gateway's HTTPS listener?

- A. Name a parent Pod
- B. Use `parentRefs` with the Gateway name and `sectionName: https`
- C. Set only the Route namespace
- D. Use an arbitrary listener annotation

<details>
<summary>Show Answer</summary>

**Answer: B. Use `parentRefs` with the Gateway name and `sectionName: https`**

The section name must match the listener, its `allowedRoutes` must permit attachment, and the hostname/protocol must be compatible. Inspect the correct parent status entry for Accepted/ResolvedRefs; a parent reference alone does not prove reachability.

</details>

### 3. Which Cilium Ingress annotation enables TLS passthrough?

- A. `ingress.cilium.io/tls-mode: passthrough`
- B. `ingress.cilium.io/tls-passthrough: "true"`
- C. `cilium.io/tls: passthrough`
- D. An nginx-specific annotation

<details>
<summary>Show Answer</summary>

**Answer: B. `ingress.cilium.io/tls-passthrough: "true"`**

The backend terminates TLS. The Ingress requires a host and path `/`; Cilium uses SNI rather than inspecting HTTP paths. The backend sees the Envoy/node connection, not the original client socket address.

</details>

### 4. Where are a Gateway's protocol and port configured?

- A. `protocols`
- B. `listeners`
- C. `endpoints`
- D. `handlers`

<details>
<summary>Show Answer</summary>

**Answer: B. `listeners`**

Each listener defines its protocol/port and applicable hostname/TLS/attachment settings. Actual protocol combinations depend on the controller. For example, LBC 3.5 does not support mixing its L4/NLB and L7/ALB listeners in one Gateway.

</details>

### 5. Which configuration selects AWS LBC for the guide's Cilium shared Ingress NLB frontend?

- A. Only the legacy `aws-load-balancer-type: nlb` annotation
- B. Service `spec.loadBalancerClass: service.k8s.aws/nlb`, instance targets and allocated NodePorts
- C. IP targets without checking EndpointSlices
- D. An arbitrary EKS namespace label

<details>
<summary>Show Answer</summary>

**Answer: B. Service `spec.loadBalancerClass: service.k8s.aws/nlb`, instance targets and allocated NodePorts**

The Helm equivalent is `ingressController.service.loadBalancerClass`. Cilium's L7 shared Ingress EndpointSlice is synthetic and lacks Pod target references; LBC's IP resolver skips it. EC2 instance/NodePort prerequisites still need validation.

</details>

### 6. Which HTTPRoute filter rewrites the upstream hostname/path without redirecting the client?

- A. `PathRewrite`
- B. `URLRewrite`
- C. `RequestTransform`
- D. `RequestRedirect`

<details>
<summary>Show Answer</summary>

**Answer: B. `URLRewrite`**

URLRewrite changes the request forwarded to the backend. RequestRedirect returns a redirect to the client. Header values in the guide are literal strings, not automatic UUID or latency generation.

</details>

### 7. Which listener setting restricts cross-namespace Route attachment to namespaces with an approved label?

- A. `allowedRoutes.namespaces.from: All`
- B. `allowedRoutes.namespaces.from: Selector` with a matching selector
- C. `crossNamespace: true`
- D. `routes.scope: cluster`

<details>
<summary>Show Answer</summary>

**Answer: B. `allowedRoutes.namespaces.from: Selector` with a matching selector**

All also permits cross-namespace attachment, but does not restrict it by label. Same restricts it to the Gateway namespace. A cross-namespace backend Service reference additionally needs ReferenceGrant in the backend namespace; that is a separate check.

</details>

### 8. Where are Envoy active health checks configured?

- A. Listener's name
- B. Cluster's `health_checks`
- C. Route's name
- D. Endpoint's namespace

<details>
<summary>Show Answer</summary>

**Answer: B. Cluster's `health_checks`**

A usable CEC still needs a Service→Listener→route→Cluster chain. HTTP health host/path must work on the actual backend. The expected status interval excludes its upper bound, so start 200/end 300 covers all 2xx.

</details>

### 9. Which permanent redirect preserves the request method/body, and how should the HTTP→HTTPS Route attach?

- A. 302 on both HTTP and HTTPS
- B. 307 on both HTTP and HTTPS
- C. 308 on the HTTP listener only
- D. 303 on the HTTPS listener only

<details>
<summary>Show Answer</summary>

**Answer: C. 308 on the HTTP listener only**

308 is permanent and preserves method/body; 307 is its temporary counterpart. Binding the scheme redirect only to HTTP avoids an HTTPS self-redirect loop. Redirects cannot protect data already sent in the initial plaintext request.

</details>

### 10. Which cost and capability comparison is accurate?

- A. Cilium never needs a cloud load balancer
- B. AWS LBC is always faster
- C. Cilium node/proxy costs can coexist with cloud LB charges; compare version-specific features
- D. Every controller supports every Gateway API feature

<details>
<summary>Show Answer</summary>

**Answer: C. Cilium node/proxy costs can coexist with cloud LB charges; compare version-specific features**

Cilium can run behind ALB/NLB, which still incur charges. LBC 3.5 maps HTTP/GRPC Routes to ALB and TCP/UDP/TLS Routes to NLB. Workload mTLS and ACM server certificates are different mechanisms; performance requires comparable measurements.

</details>

### 11. What does TCPRoute do in the guide's Gateway API 1.6.1 baseline?

- A. Inspect HTTP paths
- B. Terminate TLS by default
- C. Forward an opaque TCP stream using the served v1 API
- D. Handle UDP only

<details>
<summary>Show Answer</summary>

**Answer: C. Forward an opaque TCP stream using the served v1 API**

TCP can carry HTTP or TLS, but TCPRoute does not gain their L7 semantics. The old TCPRoute v1alpha2 API is not served in this baseline. TLSRoute v1 instead requires a compatible TLS passthrough listener for SNI routing.

</details>

### 12. If NLB PPv2 is enabled for this Cilium Ingress topology, what must be coordinated?

- A. Only a client X-Forwarded-For header
- B. Both the NLB sender and Cilium `enableProxyProtocol` receiver, health checks and trusted access path
- C. No receiver change is needed
- D. PPv2 is mandatory for every NLB

<details>
<summary>Show Answer</summary>

**Answer: B. Both the NLB sender and Cilium `enableProxyProtocol` receiver, health checks and trusted access path**

The parser requires a PROXY header, so enabling one side alone breaks traffic. PPv2 is optional; client-IP preservation also depends on target type/attributes. AWS LBC warns against PPv2 with instance targets and externalTrafficPolicy Local. PROXY metadata is not authenticated identity.

</details>
