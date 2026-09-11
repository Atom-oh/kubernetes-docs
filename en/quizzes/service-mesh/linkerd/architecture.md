# Linkerd Architecture Quiz

Reviewed September 11, 2026 for edge-26.9.1. Read the [architecture guide](../../../service-mesh/linkerd/02-architecture.md) for the source-backed model and limitations.

### 1. Which is not a Linkerd control-plane component?

A. Destination controller

B. Identity controller

C. Proxy Injector

D. Envoy proxy

<details>
<summary>Answer and explanation</summary>

**Answer: D**

Linkerd uses a Rust data-plane proxy. The pinned control plane has three core Deployments, with additional logical controllers such as policy running inside them. Envoy is used by Istio sidecars/waypoints, not as a Linkerd controller.

</details>

### 2. Which language is linkerd2-proxy written in?

A. Go

B. C++

C. Rust

D. Java

<details>
<summary>Answer and explanation</summary>

**Answer: C**

It is written in Rust. Language choice does not establish a universal 10MB footprint, sub-millisecond p99 or fixed superiority over another proxy. Compare actual builds, workloads and configurations.

</details>

### 3. Which is not a primary Destination responsibility?

A. Service discovery

B. Workload certificate issuance

C. Supported ServiceProfile information

D. Endpoint updates

<details>
<summary>Answer and explanation</summary>

**Answer: B**

Identity issues workload certificates using its configured issuer credential. Destination provides discovery/profile information; current Gateway API routing and authorization also involve the policy controller. A legacy TrafficSplit extension is not the complete current policy model.

</details>

### 4. What is the trust basis at the top of the default certificate hierarchy?

A. Workload certificate

B. Identity issuer

C. Trust anchor

D. A unique Pod name

<details>
<summary>Answer and explanation</summary>

**Answer: C**

The public trust anchor anchors certificate-chain validation. Normally it signs the intermediate issuer, whose key signs workload certificates. Linkerd does not require the root private key to process every workload CSR.

</details>

### 5. What is the nominal default workload certificate lifetime?

A. 1 hour

B. 24 hours

C. 7 days

D. 30 days

<details>
<summary>Answer and explanation</summary>

**Answer: B**

The default configured issuance lifetime is 24 hours, with renewal before expiry. Actual validity and refresh timing depend on configuration and certificate state. Certificate renewal is not automatically a fresh private key, issuer rotation or root rotation.

</details>

### 6. What Kubernetes mechanism performs automatic proxy injection?

A. DaemonSet

B. CronJob

C. Mutating admission webhook

D. Application load balancer

<details>
<summary>Answer and explanation</summary>

**Answer: C**

The webhook mutates eligible newly created Pods. In the selected release, the proxy normally becomes a native sidecar; linkerd-init is omitted when Linkerd CNI is configured. Existing Pods and excluded/overridden Pods require separate consideration.

</details>

### 7. What does linkerd-init do when Linkerd CNI is not used?

A. Downloads every routing policy

B. Configures Pod-network traffic capture

C. Acts as the root CA

D. Stores Prometheus time series

<details>
<summary>Answer and explanation</summary>

**Answer: B**

It configures capture rules inside the Pod network namespace. Proxy-UID and configured bypass rules must be accounted for before redirecting intercepted TCP. It does not mean every protocol and every bypassed port is handled by the proxy.

</details>

### 8. What is the default inbound proxy port?

A. 4140

B. 4143

C. 4191

D. 8080

<details>
<summary>Answer and explanation</summary>

**Answer: B**

Defaults are 4143 inbound, 4140 outbound and 4191 admin/metrics. Inbound/outbound handle intercepted TCP, which may contain HTTP/gRPC or opaque payloads. Ports are configurable.

</details>

### 9. For ServiceAccount web-service in my-app, what is the default Kubernetes identity when the control-plane namespace is linkerd and trust domain is cluster.local?

A. spiffe://root.linkerd.cluster.local/ns/my-app/sa/web-service

B. web-service.my-app.serviceaccount.identity.linkerd.cluster.local

C. https://linkerd.io/identity/my-pod

D. urn:linkerd:my-pod

<details>
<summary>Answer and explanation</summary>

**Answer: B**

Kubernetes TokenReview yields the ServiceAccount identity, formatted as a DNS name. Multiple Pods using that ServiceAccount share the identity. SPIFFE/SPIRE external-workload identities use a different bootstrap path and are not this default Kubernetes URI format.

</details>

### 10. Which comparison is justified without a matched benchmark?

A. Linkerd always uses exactly 10MB

B. Compare architecture and supported APIs; measure resource/latency differences for the actual workload

C. Istio always adds 2–5ms p99

D. The smaller configured memory request proves lower runtime consumption

<details>
<summary>Answer and explanation</summary>

**Answer: B**

Configured reservations, binary size, actual memory and latency are different properties. Compare a matching version/build, architecture, traffic pattern and policy set. Extensibility must also be checked for the selected mode/API rather than inferred from a generic product ranking.

</details>

### 11. What does the default Kubernetes identity validator check?

A. Only the Pod IP

B. The submitted ServiceAccount token through Kubernetes TokenReview

C. Only a namespace label

D. Only a ConfigMap name

<details>
<summary>Answer and explanation</summary>

**Answer: B**

The released validator authenticates the token and derives the DNS-form identity from Kubernetes user information. The certification request also includes identity and CSR data. This is not a claim that a caller-supplied SPIFFE URI is accepted merely because it looks plausible.

</details>

### 12. How are dynamically updated routing/policy settings normally delivered to the proxy?

A. By writing to its Prometheus metrics endpoint

B. By changing the root certificate subject

C. Through the control-plane APIs, including streaming gRPC

D. By applying arbitrary REDIRECT rules in the node namespace

<details>
<summary>Answer and explanation</summary>

**Answer: C**

The admin port provides health and metric interfaces, not a substitute for control-plane policy APIs. Startup environment/injection configuration and dynamically delivered policies are distinct inputs; inspect both when diagnosing behavior.

</details>
