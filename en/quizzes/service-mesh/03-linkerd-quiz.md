# Linkerd Quiz

Test your knowledge of Linkerd, the lightweight and secure service mesh. This quiz covers architecture, mTLS, traffic management, observability, and EKS deployment.

---

## Architecture and Core Concepts

1. What is Linkerd's primary design philosophy compared to other service meshes?
   - A) Maximum feature completeness
   - B) Simplicity, security, and performance
   - C) Complex traffic management
   - D) Multi-cloud federation

<details>
<summary>Show Answer</summary>

**Answer: B) Simplicity, security, and performance**

**Explanation:**
Linkerd was designed with simplicity as a core principle. It focuses on being lightweight, easy to operate, and secure by default, while maintaining high performance. This contrasts with more feature-rich but complex alternatives.

</details>

---

2. What language is the Linkerd2-proxy (data plane) written in?
   - A) Go
   - B) C++
   - C) Rust
   - D) Java

<details>
<summary>Show Answer</summary>

**Answer: C) Rust**

**Explanation:**
Linkerd2-proxy is written in Rust, chosen for its memory safety guarantees and performance characteristics. Rust provides the speed of C/C++ without the memory safety issues, making it ideal for a high-performance proxy.

</details>

---

3. Which component is NOT part of the Linkerd control plane?
   - A) Destination
   - B) Identity
   - C) Proxy Injector
   - D) Pilot

<details>
<summary>Show Answer</summary>

**Answer: D) Pilot**

**Explanation:**
Pilot is a component of Istio, not Linkerd. The Linkerd control plane consists of the Destination controller (service discovery), Identity controller (mTLS certificates), and Proxy Injector (sidecar injection).

</details>

---

4. How does Linkerd inject its proxy sidecar into pods?
   - A) Manual container configuration only
   - B) Kubernetes mutating admission webhook
   - C) DaemonSet on each node
   - D) eBPF programs in the kernel

<details>
<summary>Show Answer</summary>

**Answer: B) Kubernetes mutating admission webhook**

**Explanation:**
Linkerd uses a Kubernetes mutating admission webhook (the proxy-injector) to automatically inject the linkerd2-proxy sidecar container into pods. This can be enabled via namespace annotations or pod annotations.

</details>

---

5. What annotation enables automatic Linkerd proxy injection for a namespace?
   - A) `linkerd.io/inject: true`
   - B) `linkerd.io/inject: enabled`
   - C) `sidecar.linkerd.io/inject: true`
   - D) `linkerd.io/auto-inject: enabled`

<details>
<summary>Show Answer</summary>

**Answer: B) linkerd.io/inject: enabled**

**Explanation:**
The annotation `linkerd.io/inject: enabled` on a namespace enables automatic proxy injection for all pods created in that namespace. Individual pods can override this with the same annotation set to `disabled`.

</details>

---

## mTLS and Security

6. What is the default behavior of mTLS in Linkerd?
   - A) Disabled by default, must be explicitly enabled
   - B) Enabled by default with automatic certificate rotation
   - C) Enabled only for specific namespaces
   - D) Requires manual certificate management

<details>
<summary>Show Answer</summary>

**Answer: B) Enabled by default with automatic certificate rotation**

**Explanation:**
Linkerd enables mTLS by default for all meshed communication. The Identity controller automatically generates and rotates certificates without requiring any user configuration, providing "zero-config" encryption.

</details>

---

7. What is the default certificate validity period for workload certificates in Linkerd?
   - A) 1 hour
   - B) 24 hours
   - C) 7 days
   - D) 30 days

<details>
<summary>Show Answer</summary>

**Answer: B) 24 hours**

**Explanation:**
Linkerd workload certificates have a default validity of 24 hours. They are automatically rotated before expiration. This short-lived certificate approach limits the window of vulnerability if a certificate is compromised.

</details>

---

8. Which of the following is used by Linkerd for service identity?
   - A) IP addresses
   - B) DNS names
   - C) ServiceAccount tokens
   - D) Custom JWT tokens

<details>
<summary>Show Answer</summary>

**Answer: C) ServiceAccount tokens**

**Explanation:**
Linkerd uses Kubernetes ServiceAccount tokens for workload identity. The Identity controller issues certificates to workloads based on their ServiceAccount, providing a cryptographic identity tied to Kubernetes RBAC.

</details>

---

9. What command checks if Linkerd's mTLS is working correctly between services?
   - A) `linkerd check --proxy`
   - B) `linkerd edges`
   - C) `linkerd tap`
   - D) `linkerd stat`

<details>
<summary>Show Answer</summary>

**Answer: B) linkerd edges**

**Explanation:**
The `linkerd edges` command shows the TLS status of connections between meshed services. It displays whether mTLS is active (indicated by a lock icon or "secured" status) for each service-to-service connection.

</details>

---

10. In Linkerd, what is the purpose of the trust anchor certificate?
    - A) To encrypt individual pod traffic
    - B) To serve as the root CA for the mesh
    - C) To authenticate external clients
    - D) To validate DNS responses

<details>
<summary>Show Answer</summary>

**Answer: B) To serve as the root CA for the mesh**

**Explanation:**
The trust anchor is the root certificate authority for the Linkerd mesh. All workload certificates chain back to this trust anchor, enabling workloads to verify each other's identities and establish mutual TLS.

</details>

---

## Traffic Management

11. What CRD does Linkerd use for traffic splitting?
    - A) VirtualService
    - B) DestinationRule
    - C) TrafficSplit
    - D) HTTPRoute

<details>
<summary>Show Answer</summary>

**Answer: C) TrafficSplit**

**Explanation:**
Linkerd uses the TrafficSplit CRD from the Service Mesh Interface (SMI) specification for traffic splitting. This enables canary deployments and A/B testing by distributing traffic across multiple backend services.

</details>

---

12. In a Linkerd TrafficSplit configuration, what do the `weight` values represent?
    - A) Absolute number of requests
    - B) Relative proportion of traffic (must sum to 1000)
    - C) Relative proportion of traffic (can be any values)
    - D) Maximum requests per second

<details>
<summary>Show Answer</summary>

**Answer: C) Relative proportion of traffic (can be any values)**

**Explanation:**
TrafficSplit weights are relative proportions that can be any positive integers. For example, weights of 90 and 10 would send 90% to one service and 10% to another. The system calculates percentages based on the sum of all weights.

</details>

---

13. Which of the following is NOT a native Linkerd traffic management feature?
    - A) Traffic splitting
    - B) Retries
    - C) Timeouts
    - D) Circuit breaking with custom thresholds

<details>
<summary>Show Answer</summary>

**Answer: D) Circuit breaking with custom thresholds**

**Explanation:**
While Linkerd has built-in circuit breaking through its failure accrual mechanism, it does not expose custom circuit breaker threshold configuration like Istio does. Linkerd focuses on automatic, sensible defaults rather than extensive configurability.

</details>

---

14. How does Linkerd implement automatic retries?
    - A) Through VirtualService configuration
    - B) Via ServiceProfile CRD with isRetryable routes
    - C) Using DestinationRule retry policies
    - D) Through proxy-level annotations only

<details>
<summary>Show Answer</summary>

**Answer: B) Via ServiceProfile CRD with isRetryable routes**

**Explanation:**
Linkerd uses ServiceProfile CRDs to configure retries. By marking routes as `isRetryable: true` in a ServiceProfile, Linkerd will automatically retry failed requests on those routes, with built-in safety mechanisms.

</details>

---

15. What command can you use to observe live traffic flowing through Linkerd proxies?
    - A) `linkerd watch`
    - B) `linkerd tap`
    - C) `linkerd trace`
    - D) `linkerd flow`

<details>
<summary>Show Answer</summary>

**Answer: B) linkerd tap**

**Explanation:**
The `linkerd tap` command provides real-time visibility into requests flowing through the mesh. It allows you to filter by namespace, deployment, or even specific HTTP paths to debug traffic issues.

</details>

---

## Observability

16. Which dashboard tool is included with linkerd-viz?
    - A) Kiali
    - B) Jaeger
    - C) Grafana
    - D) Datadog

<details>
<summary>Show Answer</summary>

**Answer: C) Grafana**

**Explanation:**
The linkerd-viz extension includes Grafana with pre-configured dashboards for monitoring the health of your services. It provides metrics like success rate, request volume, and latency distributions out of the box.

</details>

---

17. What metrics does Linkerd expose by default for meshed services?
    - A) Only error counts
    - B) Request rate, success rate, and latency (Golden Signals)
    - C) Only CPU and memory usage
    - D) Only network bandwidth

<details>
<summary>Show Answer</summary>

**Answer: B) Request rate, success rate, and latency (Golden Signals)**

**Explanation:**
Linkerd automatically collects and exposes the "Golden Signals" metrics: request rate (traffic), success rate (errors), and latency distribution. These metrics are available without any application instrumentation.

</details>

---

18. What is the `linkerd stat` command used for?
    - A) Checking cluster health
    - B) Viewing aggregated metrics for resources
    - C) Installing Linkerd components
    - D) Managing certificates

<details>
<summary>Show Answer</summary>

**Answer: B) Viewing aggregated metrics for resources**

**Explanation:**
The `linkerd stat` command displays aggregated metrics (success rate, RPS, latency percentiles) for deployments, pods, namespaces, or other resources. It provides a quick overview of service health from the command line.

</details>

---

19. What protocol does Linkerd use for distributed tracing propagation?
    - A) Zipkin B3
    - B) W3C Trace Context
    - C) OpenTelemetry native
    - D) Both B3 and W3C Trace Context

<details>
<summary>Show Answer</summary>

**Answer: D) Both B3 and W3C Trace Context**

**Explanation:**
Linkerd supports both Zipkin B3 headers and W3C Trace Context for distributed tracing propagation. Applications must propagate these headers; Linkerd adds its own span information to the traces.

</details>

---

20. What extension adds Jaeger integration to Linkerd?
    - A) linkerd-viz
    - B) linkerd-jaeger
    - C) linkerd-tracing
    - D) linkerd-otel

<details>
<summary>Show Answer</summary>

**Answer: B) linkerd-jaeger**

**Explanation:**
The linkerd-jaeger extension adds distributed tracing support with Jaeger. It deploys a Jaeger collector and configures the Linkerd proxies to emit trace spans, enabling end-to-end request tracing.

</details>

---

## Multi-Cluster

21. What does Linkerd multi-cluster require for cross-cluster communication?
    - A) Direct pod-to-pod networking
    - B) A gateway service and service mirroring
    - C) VPN tunnel between clusters
    - D) Shared certificate authority only

<details>
<summary>Show Answer</summary>

**Answer: B) A gateway service and service mirroring**

**Explanation:**
Linkerd multi-cluster uses a gateway service in each cluster and service mirroring to enable cross-cluster communication. Services from remote clusters are mirrored into the local cluster with a `-<cluster>` suffix.

</details>

---

22. In Linkerd multi-cluster, what is the naming convention for mirrored services?
    - A) `service.namespace.cluster.local`
    - B) `service-<remote-cluster-name>`
    - C) `cluster-<service-name>`
    - D) `<cluster>.<service>.svc`

<details>
<summary>Show Answer</summary>

**Answer: B) service-<remote-cluster-name>**

**Explanation:**
When a service is mirrored from a remote cluster, it appears in the local cluster with the name `<service-name>-<remote-cluster-name>`. For example, `orders-west` for the `orders` service from the `west` cluster.

</details>

---

23. What is required for Linkerd multi-cluster mTLS to work across clusters?
    - A) Different trust anchors per cluster
    - B) Shared trust anchor certificate
    - C) No certificates needed
    - D) External certificate authority only

<details>
<summary>Show Answer</summary>

**Answer: B) Shared trust anchor certificate**

**Explanation:**
For multi-cluster mTLS to work, all clusters must share the same trust anchor certificate. This allows workloads in different clusters to validate each other's certificates and establish secure connections.

</details>

---

## EKS Deployment

24. What is the recommended method for installing Linkerd on EKS?
    - A) kubectl apply from YAML only
    - B) Helm charts with EKS-specific values
    - C) EKS add-on from AWS console
    - D) AWS CDK construct

<details>
<summary>Show Answer</summary>

**Answer: B) Helm charts with EKS-specific values**

**Explanation:**
While Linkerd can be installed via CLI or Helm, using Helm charts is recommended for production EKS deployments. This allows customization of values specific to your EKS environment and enables GitOps workflows.

</details>

---

25. When using Linkerd with AWS ALB Ingress Controller, what must be considered?
    - A) ALB cannot work with Linkerd
    - B) mTLS termination at ALB and re-initiation in the mesh
    - C) ALB requires special Linkerd annotations
    - D) ALB automatically integrates with Linkerd

<details>
<summary>Show Answer</summary>

**Answer: B) mTLS termination at ALB and re-initiation in the mesh**

**Explanation:**
When using AWS ALB with Linkerd, TLS typically terminates at the ALB. Traffic from ALB to the mesh can either be unencrypted (within the VPC) or re-encrypted. Linkerd's automatic mTLS will encrypt traffic between meshed services.

</details>

---

26. What is the purpose of the `linkerd check` command before installation on EKS?
    - A) To install Linkerd components
    - B) To verify cluster prerequisites are met
    - C) To generate certificates
    - D) To configure AWS resources

<details>
<summary>Show Answer</summary>

**Answer: B) To verify cluster prerequisites are met**

**Explanation:**
Running `linkerd check --pre` before installation verifies that your EKS cluster meets all prerequisites for Linkerd, such as Kubernetes version, necessary permissions, and network configuration.

</details>

---

27. How should you handle Linkerd certificate management in production EKS environments?
    - A) Use auto-generated certificates only
    - B) Use cert-manager with external CA or bring your own certificates
    - C) Certificates are not needed in EKS
    - D) AWS Certificate Manager automatically provides certificates

<details>
<summary>Show Answer</summary>

**Answer: B) Use cert-manager with external CA or bring your own certificates**

**Explanation:**
For production EKS deployments, it's recommended to use cert-manager with an external CA or bring your own certificates for the trust anchor and issuer. This provides better control over certificate lifecycle and security.

</details>

---

28. What resource requests are recommended for Linkerd proxies in EKS?
    - A) 1 CPU, 1Gi memory
    - B) 100m CPU, 100Mi memory (approximately)
    - C) No resources needed
    - D) 500m CPU, 512Mi memory

<details>
<summary>Show Answer</summary>

**Answer: B) 100m CPU, 100Mi memory (approximately)**

**Explanation:**
Linkerd proxies are extremely lightweight, typically requiring around 100m CPU and 100Mi memory. The actual resource usage is often even lower, making Linkerd one of the most resource-efficient service meshes.

</details>

---

## Comparison and Best Practices

29. Compared to Istio, what is Linkerd's main advantage?
    - A) More features
    - B) Simpler operations and lower resource overhead
    - C) Better multi-cloud support
    - D) More configuration options

<details>
<summary>Show Answer</summary>

**Answer: B) Simpler operations and lower resource overhead**

**Explanation:**
Linkerd's main advantage over Istio is its simplicity and lower resource overhead. The Rust-based proxy is significantly lighter than Envoy, and Linkerd's design philosophy prioritizes ease of operation over feature completeness.

</details>

---

30. What is the recommended approach for gradual Linkerd adoption in an existing EKS cluster?
    - A) Mesh all namespaces at once
    - B) Start with non-critical namespaces, use annotation-based injection
    - C) Only mesh the control plane
    - D) Wait until all applications support mTLS

<details>
<summary>Show Answer</summary>

**Answer: B) Start with non-critical namespaces, use annotation-based injection**

**Explanation:**
The recommended approach is gradual adoption: start by meshing non-critical namespaces or individual deployments using annotation-based injection. This allows you to validate behavior and gradually extend to more critical workloads.

</details>

---

## Summary

This quiz covered the key aspects of Linkerd:
- Architecture: Control plane components, Rust-based proxy, sidecar injection
- Security: Automatic mTLS, certificate rotation, identity management
- Traffic Management: TrafficSplit, ServiceProfiles, retries
- Observability: linkerd-viz, Grafana, tap, and stat commands
- Multi-cluster: Service mirroring, shared trust anchors
- EKS Deployment: Best practices, certificate management, resource planning
