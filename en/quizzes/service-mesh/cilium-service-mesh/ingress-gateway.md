# Cilium Service Mesh Ingress & Gateway Quiz

This quiz tests your understanding of Cilium Ingress Controller, Gateway API, TLS termination, and EKS integration patterns.

## Quiz Questions

### 1. What does 'shared' mode mean in Cilium Ingress Controller's loadbalancerMode option?

A. Creates a separate load balancer for each Ingress
B. All Ingresses share one load balancer
C. Uses NodePort only without load balancer
D. Handles only internal traffic

<details>
<summary>Show Answer</summary>

**Answer: B. All Ingresses share one load balancer**

**Explanation:**
The loadbalancerMode: shared setting makes all Ingress resources use a single shared load balancer. This is cost-effective, while dedicated mode creates a separate load balancer for each Ingress.

</details>

### 2. What is the role of the parentRefs field in Gateway API's HTTPRoute?

A. Define parent Pod
B. Specify which Gateway this route connects to
C. Reference parent namespace
D. Define policies to inherit

<details>
<summary>Show Answer</summary>

**Answer: B. Specify which Gateway this route connects to**

**Explanation:**
parentRefs specifies which Gateway the HTTPRoute connects to. By referencing the Gateway's name and namespace, it determines which listener the route applies to.

</details>

### 3. What annotation enables TLS passthrough in Cilium Ingress?

A. ingress.cilium.io/tls-mode: passthrough
B. ingress.cilium.io/tls-passthrough: "true"
C. cilium.io/tls: passthrough
D. nginx.ingress.kubernetes.io/ssl-passthrough

<details>
<summary>Show Answer</summary>

**Answer: B. ingress.cilium.io/tls-passthrough: "true"**

**Explanation:**
The `ingress.cilium.io/tls-passthrough: "true"` annotation forwards TLS traffic directly to the backend service without terminating it. This is useful when the backend needs to handle TLS.

</details>

### 4. What field is used in Gateway API's Gateway resource to support multiple protocols?

A. protocols
B. listeners
C. endpoints
D. handlers

<details>
<summary>Show Answer</summary>

**Answer: B. listeners**

**Explanation:**
Multiple listeners can be defined in the Gateway's listeners field to support various protocols such as HTTP, HTTPS, TCP, TLS. Each listener can configure protocol, port, hostname, etc. individually.

</details>

### 5. What annotation is required to use NLB with Cilium Ingress on EKS?

A. service.kubernetes.io/load-balancer-type: nlb
B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
C. eks.amazonaws.com/load-balancer: nlb
D. aws.load-balancer/type: network

<details>
<summary>Show Answer</summary>

**Answer: B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"**

**Explanation:**
To use Network Load Balancer on AWS EKS, add the `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` annotation to the service. Additional annotations like scheme, target-type can further configure NLB behavior.

</details>

### 6. What filter type is used to configure URL rewriting in Gateway API's HTTPRoute?

A. PathRewrite
B. URLRewrite
C. RequestTransform
D. PathModifier

<details>
<summary>Show Answer</summary>

**Answer: B. URLRewrite**

**Explanation:**
In the HTTPRoute's filters section, type: URLRewrite is used to rewrite request URLs. Both path and hostname can be modified.

</details>

### 7. What Gateway setting is needed to allow cross-namespace routing in Cilium Gateway API?

A. allowedRoutes.namespaces.from: All
B. allowedRoutes.namespaces.from: Selector
C. crossNamespace: true
D. routes.scope: cluster

<details>
<summary>Show Answer</summary>

**Answer: B. allowedRoutes.namespaces.from: Selector**

**Explanation:**
In Gateway's listeners, setting allowedRoutes.namespaces.from: Selector allows routes only from namespaces with specific labels using a selector. 'All' allows all namespaces, and 'Same' allows only the same namespace.

</details>

### 8. What Envoy resource type is used to configure service health checks in CiliumEnvoyConfig?

A. envoy.config.listener.v3.Listener
B. envoy.config.cluster.v3.Cluster
C. envoy.config.route.v3.Route
D. envoy.config.endpoint.v3.Endpoint

<details>
<summary>Show Answer</summary>

**Answer: B. envoy.config.cluster.v3.Cluster**

**Explanation:**
Health check settings are defined in the health_checks field of the Cluster resource. HTTP health checks, TCP health checks, intervals, thresholds, etc. can be configured.

</details>

### 9. What is the recommended statusCode when redirecting from HTTP to HTTPS in Gateway API?

A. 302 (Found)
B. 307 (Temporary Redirect)
C. 301 (Moved Permanently)
D. 303 (See Other)

<details>
<summary>Show Answer</summary>

**Answer: C. 301 (Moved Permanently)**

**Explanation:**
For permanent redirect from HTTP to HTTPS, status code 301 is recommended. This informs browsers and search engines that the URL has permanently changed, which is beneficial for caching and SEO.

</details>

### 10. What is the main difference between Cilium and AWS Load Balancer Controller?

A. Cilium only supports L4
B. AWS LBC provides lower latency
C. Cilium uses only node resources without additional LB costs
D. AWS LBC fully supports Gateway API

<details>
<summary>Show Answer</summary>

**Answer: C. Cilium uses only node resources without additional LB costs**

**Explanation:**
Cilium Ingress/Gateway handles external traffic using node's eBPF and Envoy, so there are no separate AWS load balancer costs. In contrast, AWS LBC provisions ALB/NLB incurring additional costs.

</details>

### 11. What is TCPRoute used for in Gateway API?

A. HTTP traffic routing
B. Traffic requiring TLS termination
C. Raw TCP traffic routing (non-HTTP)
D. UDP traffic only

<details>
<summary>Show Answer</summary>

**Answer: C. Raw TCP traffic routing (non-HTTP)**

**Explanation:**
TCPRoute is used to route raw TCP traffic that is not HTTP, such as database connections and message queues. It works with Gateway's TCP listener to provide external access to non-HTTP services.

</details>

### 12. What NLB setting is used to preserve client IP in Cilium Ingress?

A. X-Forwarded-For header
B. Proxy Protocol
C. Disable Source NAT
D. Direct Server Return

<details>
<summary>Show Answer</summary>

**Answer: B. Proxy Protocol**

**Explanation:**
To preserve client IP with NLB, Proxy Protocol must be enabled. Use the `service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"` annotation. Envoy extracts the original client IP from the Proxy Protocol header.

</details>
