# Linkerd Architecture Quiz

This quiz tests your understanding of Linkerd architecture.

## Quiz Questions

### 1. Which is NOT a core component of the Linkerd control plane?

A. Destination Controller
B. Identity Controller
C. Proxy Injector
D. Envoy Proxy

<details>
<summary>Show Answer</summary>

**Answer: D. Envoy Proxy**

**Explanation:**
The Linkerd control plane consists of Destination, Identity, and Proxy Injector. Envoy is Istio's data plane proxy; Linkerd uses its own linkerd2-proxy written in Rust.

</details>

### 2. What programming language is linkerd2-proxy written in?

A. Go
B. C++
C. Rust
D. Java

<details>
<summary>Show Answer</summary>

**Answer: C. Rust**

**Explanation:**
linkerd2-proxy is written in Rust, providing memory safety and high performance. It uses only about 10MB of memory and adds less than 1ms p99 latency.

</details>

### 3. Which is NOT a primary role of the Destination Controller?

A. Service discovery
B. Certificate issuance
C. ServiceProfile information delivery
D. Endpoint updates

<details>
<summary>Show Answer</summary>

**Answer: B. Certificate issuance**

**Explanation:**
Certificate issuance is the role of the Identity Controller. The Destination Controller is responsible for service discovery, endpoint updates, and distributing ServiceProfile and TrafficSplit policies.

</details>

### 4. What is at the top of Linkerd's certificate hierarchy?

A. Workload Certificate
B. Identity Issuer
C. Trust Anchor
D. Proxy Certificate

<details>
<summary>Show Answer</summary>

**Answer: C. Trust Anchor**

**Explanation:**
The certificate hierarchy is Trust Anchor (Root CA) → Identity Issuer (Intermediate CA) → Workload Certificate. The Trust Anchor is the root of the PKI and the foundation of trust for all certificate chains.

</details>

### 5. What is the default validity period of workload certificates?

A. 1 hour
B. 24 hours
C. 7 days
D. 30 days

<details>
<summary>Show Answer</summary>

**Answer: B. 24 hours**

**Explanation:**
Linkerd workload certificates have a default validity period of 24 hours. Proxies automatically renew certificates before expiration. Short validity periods minimize risk in case of certificate compromise.

</details>

### 6. What Kubernetes mechanism does the Proxy Injector use?

A. DaemonSet
B. CronJob
C. Admission Webhook
D. Custom Controller

<details>
<summary>Show Answer</summary>

**Answer: C. Admission Webhook**

**Explanation:**
The Proxy Injector operates as a Mutating Admission Webhook. It intercepts Pod creation requests and automatically injects the linkerd-proxy sidecar and linkerd-init init container.

</details>

### 7. What is the role of the linkerd-init container?

A. Download proxy configuration
B. Set up iptables rules
C. Generate certificates
D. Collect metrics

<details>
<summary>Show Answer</summary>

**Answer: B. Set up iptables rules**

**Explanation:**
linkerd-init runs as an Init container to set up iptables rules. These rules redirect all inbound/outbound traffic to the linkerd-proxy.

</details>

### 8. What is the Linkerd proxy inbound port?

A. 4140
B. 4143
C. 4191
D. 8080

<details>
<summary>Show Answer</summary>

**Answer: B. 4143**

**Explanation:**
Linkerd proxy ports: 4143 (inbound), 4140 (outbound), 4191 (admin/metrics). The inbound port receives traffic from other services.

</details>

### 9. What is the correct SPIFFE ID format?

A. `spiffe://cluster/namespace/service`
B. `spiffe://trust-domain/ns/namespace/sa/service-account`
C. `https://linkerd.io/identity/namespace/pod`
D. `urn:linkerd:identity:namespace:pod`

<details>
<summary>Show Answer</summary>

**Answer: B. `spiffe://trust-domain/ns/namespace/sa/service-account`**

**Explanation:**
Linkerd's SPIFFE ID follows the format `spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>`. Example: `spiffe://root.linkerd.cluster.local/ns/production/sa/web-server`

</details>

### 10. Which is NOT a characteristic of linkerd2-proxy compared to Istio's Envoy?

A. Lower memory usage
B. Wasm extension support
C. Lower latency
D. Smaller binary size

<details>
<summary>Show Answer</summary>

**Answer: B. Wasm extension support**

**Explanation:**
linkerd2-proxy does not support Wasm extensions (limited extensibility). Instead, it is more lightweight with ~10MB memory (Envoy ~50-100MB), <1ms p99 latency (Envoy 2-5ms), and ~10MB binary (Envoy ~60MB).

</details>

### 11. What does the Identity Controller verify before issuing a certificate?

A. Pod's IP address
B. ServiceAccount token
C. Namespace labels
D. ConfigMap settings

<details>
<summary>Show Answer</summary>

**Answer: B. ServiceAccount token**

**Explanation:**
The Identity Controller verifies the ServiceAccount token sent along with the CSR submitted by the proxy. This confirms that the proxy's identity (SPIFFE ID) matches the actual workload.

</details>

### 12. What is NOT provided by the Linkerd proxy admin port (4191)?

A. Prometheus metrics
B. Health check endpoints
C. Traffic routing configuration
D. Proxy version information

<details>
<summary>Show Answer</summary>

**Answer: C. Traffic routing configuration**

**Explanation:**
The admin port (4191) provides Prometheus metrics (/metrics), health checks (/ready, /live), and proxy information. Traffic routing configuration is delivered to proxies via gRPC from the Destination Controller.

</details>
