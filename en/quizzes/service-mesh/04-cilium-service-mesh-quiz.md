# Cilium Service Mesh Quiz

Test your knowledge of Cilium Service Mesh, the eBPF-based sidecar-less service mesh. This quiz covers architecture, eBPF fundamentals, traffic management, mTLS, observability, and EKS deployment.

---

## Architecture and Core Concepts

1. What is the key architectural difference between Cilium Service Mesh and traditional service meshes like Istio?
   - A) Cilium uses more sidecars
   - B) Cilium uses a sidecar-less architecture with eBPF
   - C) Cilium requires more control plane components
   - D) Cilium only supports L4 traffic

<details>
<summary>Show Answer</summary>

**Answer: B) Cilium uses a sidecar-less architecture with eBPF**

**Explanation:**
Cilium Service Mesh's defining characteristic is its sidecar-less architecture. Instead of injecting proxy sidecars into every pod, Cilium uses eBPF programs in the Linux kernel for L3/L4 processing and a per-node Envoy proxy for L7 features.

</details>

---

2. What technology powers Cilium's high-performance networking at L3/L4?
   - A) iptables
   - B) IPVS
   - C) eBPF (extended Berkeley Packet Filter)
   - D) userspace networking

<details>
<summary>Show Answer</summary>

**Answer: C) eBPF (extended Berkeley Packet Filter)**

**Explanation:**
eBPF is the core technology behind Cilium. It allows Cilium to run custom programs directly in the Linux kernel, providing extremely fast packet processing for L3/L4 operations without the overhead of userspace proxies.

</details>

---

3. In Cilium Service Mesh, where does L7 processing occur?
   - A) In the Linux kernel via eBPF
   - B) In a per-pod sidecar proxy
   - C) In a per-node Envoy proxy
   - D) In the control plane only

<details>
<summary>Show Answer</summary>

**Answer: C) In a per-node Envoy proxy**

**Explanation:**
While eBPF handles L3/L4 traffic directly in the kernel, L7 features (HTTP routing, gRPC load balancing, etc.) require the Envoy proxy. Cilium uses a per-node Envoy instance shared by all pods on that node, rather than per-pod sidecars.

</details>

---

4. What is a major benefit of Cilium's per-node proxy model compared to per-pod sidecars?
   - A) More isolation between pods
   - B) Significantly lower memory and CPU overhead
   - C) Better per-pod configuration options
   - D) Simpler debugging

<details>
<summary>Show Answer</summary>

**Answer: B) Significantly lower memory and CPU overhead**

**Explanation:**
With per-node proxies, you have one Envoy instance per node instead of one per pod. For a cluster with 1000 pods across 50 nodes, this means 50 Envoy instances instead of 1000, dramatically reducing resource consumption.

</details>

---

5. What CRD does Cilium use to configure Envoy for L7 traffic management?
   - A) VirtualService
   - B) Gateway
   - C) CiliumEnvoyConfig
   - D) EnvoyFilter

<details>
<summary>Show Answer</summary>

**Answer: C) CiliumEnvoyConfig**

**Explanation:**
CiliumEnvoyConfig is the CRD that allows you to configure Envoy for specific services in Cilium. It enables L7 features like HTTP routing, traffic splitting, and load balancing by embedding Envoy configuration.

</details>

---

## eBPF and Data Plane

6. Which eBPF attachment point does Cilium use for pod network interface handling?
   - A) XDP only
   - B) tc (traffic control) ingress/egress
   - C) kprobes only
   - D) raw sockets

<details>
<summary>Show Answer</summary>

**Answer: B) tc (traffic control) ingress/egress**

**Explanation:**
Cilium attaches eBPF programs to the tc (traffic control) hook points on network interfaces. The bpf_lxc program handles pod network interfaces at tc ingress/egress, enabling policy enforcement and routing decisions.

</details>

---

7. What is the purpose of eBPF maps in Cilium?
   - A) To visualize network topology
   - B) To store state and share data between eBPF programs and userspace
   - C) To define network routes
   - D) To configure Envoy filters

<details>
<summary>Show Answer</summary>

**Answer: B) To store state and share data between eBPF programs and userspace**

**Explanation:**
eBPF maps are key-value data structures that allow eBPF programs to store state and share data with userspace applications. Cilium uses maps for identity mapping, policy lookup, service discovery, and connection tracking.

</details>

---

8. What Cilium feature can completely replace kube-proxy in a Kubernetes cluster?
   - A) Cilium Network Policies
   - B) Hubble
   - C) kube-proxy replacement (kubeProxyReplacement)
   - D) Cluster Mesh

<details>
<summary>Show Answer</summary>

**Answer: C) kube-proxy replacement (kubeProxyReplacement)**

**Explanation:**
When `kubeProxyReplacement` is enabled, Cilium implements Kubernetes Service load balancing directly in eBPF, eliminating the need for kube-proxy and its iptables/IPVS rules. This provides better performance and scalability.

</details>

---

9. Which eBPF program component handles socket-level operations in Cilium?
   - A) bpf_lxc
   - B) bpf_host
   - C) bpf_sock
   - D) bpf_overlay

<details>
<summary>Show Answer</summary>

**Answer: C) bpf_sock**

**Explanation:**
The bpf_sock program attaches to cgroup/sock_ops and handles socket-level operations. It enables features like socket-level load balancing, which can bypass network stack overhead for local service connections.

</details>

---

10. What is the main advantage of Cilium's identity-based security model?
    - A) Uses IP addresses for identification
    - B) Decouples security from IP addresses, scales better with dynamic IPs
    - C) Requires no authentication
    - D) Only works with static IPs

<details>
<summary>Show Answer</summary>

**Answer: B) Decouples security from IP addresses, scales better with dynamic IPs**

**Explanation:**
Cilium assigns numeric identities to endpoints based on labels rather than IP addresses. This decouples security policies from ephemeral IPs, making it more scalable and appropriate for dynamic container environments.

</details>

---

## L7 Traffic Management

11. How do you configure HTTP header-based routing in Cilium Service Mesh?
    - A) Using Istio VirtualService
    - B) Using CiliumEnvoyConfig with Envoy RouteConfiguration
    - C) Using Kubernetes Ingress only
    - D) Through Cilium Network Policies

<details>
<summary>Show Answer</summary>

**Answer: B) Using CiliumEnvoyConfig with Envoy RouteConfiguration**

**Explanation:**
L7 routing rules including header-based routing are configured through CiliumEnvoyConfig, which embeds Envoy xDS resources. RouteConfiguration resources define virtual hosts and routing rules including header matching.

</details>

---

12. What Envoy load balancing algorithms are supported by Cilium?
    - A) Round Robin only
    - B) Round Robin, Least Request, Random, Ring Hash, Maglev
    - C) Only Maglev
    - D) IP hash only

<details>
<summary>Show Answer</summary>

**Answer: B) Round Robin, Least Request, Random, Ring Hash, Maglev**

**Explanation:**
Cilium, through Envoy, supports multiple load balancing algorithms: ROUND_ROBIN (default), LEAST_REQUEST, RANDOM, RING_HASH (for session affinity), and MAGLEV (for consistent hashing). These are configured in CiliumEnvoyConfig.

</details>

---

13. How do you implement canary deployments with traffic splitting in Cilium?
    - A) Using TrafficSplit CRD
    - B) Using CiliumEnvoyConfig with weighted_clusters
    - C) Using Kubernetes native Services only
    - D) Traffic splitting is not supported

<details>
<summary>Show Answer</summary>

**Answer: B) Using CiliumEnvoyConfig with weighted_clusters**

**Explanation:**
Traffic splitting for canary deployments is configured in CiliumEnvoyConfig using Envoy's weighted_clusters in route configuration. You specify weights for each backend service to control traffic distribution.

</details>

---

14. What is required to enable L7 visibility for a service in Cilium?
    - A) L7 visibility is always on
    - B) A CiliumNetworkPolicy with L7 rules or CiliumEnvoyConfig
    - C) Hubble installation only
    - D) Manual proxy injection

<details>
<summary>Show Answer</summary>

**Answer: B) A CiliumNetworkPolicy with L7 rules or CiliumEnvoyConfig**

**Explanation:**
L7 visibility requires explicitly enabling L7 processing via CiliumNetworkPolicy with L7 rules or CiliumEnvoyConfig. This redirects traffic through Envoy for L7 inspection, which is not the default for all traffic.

</details>

---

15. In CiliumEnvoyConfig, what does the `backendServices` field specify?
    - A) The frontend service name
    - B) The services that receive traffic after routing
    - C) The Envoy admin port
    - D) The control plane endpoint

<details>
<summary>Show Answer</summary>

**Answer: B) The services that receive traffic after routing**

**Explanation:**
The `backendServices` field in CiliumEnvoyConfig specifies the Kubernetes Services that can receive traffic through this configuration. These are the backends that Envoy routes requests to based on the configured rules.

</details>

---

## mTLS and Security

16. What is the basis for workload identity in Cilium's mTLS implementation?
    - A) IP addresses
    - B) DNS names
    - C) SPIFFE (Secure Production Identity Framework for Everyone)
    - D) MAC addresses

<details>
<summary>Show Answer</summary>

**Answer: C) SPIFFE (Secure Production Identity Framework for Everyone)**

**Explanation:**
Cilium uses SPIFFE for workload identity. SPIFFE IDs follow the format `spiffe://cluster.local/ns/<namespace>/sa/<service-account>`, providing a standardized way to identify workloads cryptographically.

</details>

---

17. How do you enable mTLS for all traffic in a Cilium mesh?
    - A) It's enabled by default for all traffic
    - B) Using CiliumNetworkPolicy with authentication mode required
    - C) Through Envoy configuration only
    - D) mTLS is not supported in Cilium

<details>
<summary>Show Answer</summary>

**Answer: B) Using CiliumNetworkPolicy with authentication mode required**

**Explanation:**
mTLS is enabled by applying CiliumNetworkPolicy or CiliumClusterwideNetworkPolicy with `authentication.mode: required`. This can be applied selectively or cluster-wide to enforce mutual authentication.

</details>

---

18. What command verifies the encryption status in a Cilium deployment?
    - A) `cilium status --verbose`
    - B) `cilium encrypt status`
    - C) `kubectl get secrets`
    - D) Both A and B

<details>
<summary>Show Answer</summary>

**Answer: D) Both A and B**

**Explanation:**
Both commands can verify encryption: `cilium status --verbose` shows encryption information in its output, and `cilium encrypt status` (run from within a Cilium pod) provides detailed encryption status including certificate information.

</details>

---

19. What is Cilium's approach to certificate management for mTLS?
    - A) Manual certificate creation required
    - B) Automatic certificate generation and rotation via built-in CA or SPIRE
    - C) Uses Kubernetes secrets only
    - D) Requires external PKI for all deployments

<details>
<summary>Show Answer</summary>

**Answer: B) Automatic certificate generation and rotation via built-in CA or SPIRE**

**Explanation:**
Cilium can automatically manage certificates using its built-in CA or integrate with SPIRE for more advanced deployments. Certificates are automatically generated, distributed, and rotated without manual intervention.

</details>

---

20. What CiliumNetworkPolicy field specifies that authentication is required?
    - A) `spec.security.mtls`
    - B) `spec.ingress.authentication.mode`
    - C) `spec.tls.required`
    - D) `spec.encryption.enabled`

<details>
<summary>Show Answer</summary>

**Answer: B) spec.ingress.authentication.mode**

**Explanation:**
In CiliumNetworkPolicy, the `authentication.mode: required` field under ingress or egress rules specifies that mutual authentication is required. Setting this to "required" enforces mTLS for matching traffic.

</details>

---

## Observability (Hubble)

21. What is Hubble in the Cilium ecosystem?
    - A) A service mesh control plane
    - B) The observability layer providing visibility into network flows
    - C) A certificate authority
    - D) A traffic splitting controller

<details>
<summary>Show Answer</summary>

**Answer: B) The observability layer providing visibility into network flows**

**Explanation:**
Hubble is Cilium's dedicated observability platform. It provides visibility into network flows, service dependencies, security events, and L7 protocol details through the Hubble CLI, UI, and metrics.

</details>

---

22. What command allows you to observe live traffic flows in Hubble?
    - A) `hubble watch`
    - B) `hubble observe`
    - C) `hubble tap`
    - D) `hubble flow`

<details>
<summary>Show Answer</summary>

**Answer: B) hubble observe**

**Explanation:**
The `hubble observe` command is the primary tool for viewing network flows in real-time. It supports various filters (namespace, pod, protocol, verdict) and can output in different formats including JSON.

</details>

---

23. Which Hubble metric tracks HTTP request latency?
    - A) `hubble_flows_processed_total`
    - B) `hubble_http_request_duration_seconds`
    - C) `hubble_tcp_flags_total`
    - D) `hubble_drop_total`

<details>
<summary>Show Answer</summary>

**Answer: B) hubble_http_request_duration_seconds**

**Explanation:**
The `hubble_http_request_duration_seconds` metric is a histogram that tracks HTTP request latency. It can be used to calculate percentiles (P50, P90, P99) for monitoring service response times.

</details>

---

24. What does the `--verdict DROPPED` filter show in `hubble observe`?
    - A) Successful connections
    - B) Packets that were dropped by policy or other reasons
    - C) All network traffic
    - D) Only encrypted traffic

<details>
<summary>Show Answer</summary>

**Answer: B) Packets that were dropped by policy or other reasons**

**Explanation:**
The `--verdict DROPPED` filter shows only packets that were dropped by Cilium. This is useful for debugging connectivity issues, policy violations, or understanding why certain traffic is being blocked.

</details>

---

25. How do you enable Hubble metrics for Prometheus scraping?
    - A) Metrics are always enabled
    - B) Set `hubble.metrics.enabled` in Helm values with desired metrics
    - C) Install a separate metrics addon
    - D) Configure each pod individually

<details>
<summary>Show Answer</summary>

**Answer: B) Set `hubble.metrics.enabled` in Helm values with desired metrics**

**Explanation:**
Hubble metrics are enabled through Helm values: `hubble.metrics.enabled="{dns,drop,tcp,flow,icmp,http}"`. You specify which metric categories to collect, and Hubble exposes them for Prometheus scraping.

</details>

---

## Ingress and Gateway API

26. What is the recommended ingress solution for new Cilium deployments?
    - A) nginx-ingress
    - B) Kubernetes Ingress with IngressClass cilium
    - C) Gateway API with GatewayClass cilium
    - D) AWS ALB only

<details>
<summary>Show Answer</summary>

**Answer: C) Gateway API with GatewayClass cilium**

**Explanation:**
Cilium fully supports Gateway API, which is the recommended approach for new deployments. Gateway API provides a more expressive and extensible API compared to legacy Ingress, with better separation of concerns.

</details>

---

27. What loadbalancer modes does Cilium Ingress Controller support?
    - A) Dedicated only
    - B) Shared only
    - C) Shared and Dedicated
    - D) None, it uses NodePort

<details>
<summary>Show Answer</summary>

**Answer: C) Shared and Dedicated**

**Explanation:**
Cilium Ingress Controller supports both `shared` mode (single LoadBalancer for all Ingress resources) and `dedicated` mode (separate LoadBalancer per Ingress). Shared mode is more cost-effective for most deployments.

</details>

---

28. How do you enable Gateway API support in Cilium?
    - A) It's enabled by default
    - B) Set `gatewayAPI.enabled=true` in Helm values
    - C) Install a separate Gateway controller
    - D) Apply Gateway CRDs only

<details>
<summary>Show Answer</summary>

**Answer: B) Set `gatewayAPI.enabled=true` in Helm values**

**Explanation:**
Gateway API support is enabled by setting `gatewayAPI.enabled=true` in the Cilium Helm values. You also need to install the Gateway API CRDs from the Kubernetes SIG Gateway repository.

</details>

---

## EKS Deployment

29. When deploying Cilium on EKS, what must be done with the AWS VPC CNI?
    - A) Keep it alongside Cilium
    - B) Replace it by deleting the aws-node DaemonSet
    - C) Disable only IPv6 support
    - D) AWS VPC CNI is automatically replaced

<details>
<summary>Show Answer</summary>

**Answer: B) Replace it by deleting the aws-node DaemonSet**

**Explanation:**
To use Cilium as the CNI on EKS, you must remove the AWS VPC CNI by deleting the aws-node DaemonSet. Cilium then takes over all CNI responsibilities, including pod networking and IP address management.

</details>

---

30. What IPAM mode should be used for Cilium on EKS to integrate with AWS networking?
    - A) cluster-pool
    - B) kubernetes
    - C) eni (Elastic Network Interface)
    - D) host-scope

<details>
<summary>Show Answer</summary>

**Answer: C) eni (Elastic Network Interface)**

**Explanation:**
ENI mode (`ipam.mode=eni`) allows Cilium to allocate pod IPs directly from AWS ENIs, providing native VPC networking. Pods get IPs from VPC subnets and can be directly routable within the VPC.

</details>

---

31. What additional Helm parameter enables kube-proxy replacement on EKS?
    - A) `proxy.enabled=false`
    - B) `kubeProxyReplacement=true` with k8sServiceHost/Port
    - C) `iptables.enabled=false`
    - D) `kube-proxy` is automatically replaced

<details>
<summary>Show Answer</summary>

**Answer: B) kubeProxyReplacement=true with k8sServiceHost/Port**

**Explanation:**
To enable kube-proxy replacement, set `kubeProxyReplacement=true` and provide the API server endpoint via `k8sServiceHost` and `k8sServicePort`. After enabling this, you should delete the kube-proxy DaemonSet.

</details>

---

32. What AWS feature does Cilium's ENI mode with prefix delegation use for IP efficiency?
    - A) Secondary IP addresses
    - B) Elastic IPs
    - C) IPv6 /56 prefixes
    - D) /28 prefix delegation to assign more IPs per ENI

<details>
<summary>Show Answer</summary>

**Answer: D) /28 prefix delegation to assign more IPs per ENI**

**Explanation:**
With `awsEnablePrefixDelegation=true`, Cilium uses AWS VPC's prefix delegation feature, which assigns /28 prefixes to ENIs instead of individual IPs. This allows up to 16 IPs per prefix, significantly increasing pod density per node.

</details>

---

## Comparison and Best Practices

33. What is Cilium Service Mesh's primary advantage over Istio in terms of latency?
    - A) Better caching
    - B) Kernel-level processing via eBPF reduces proxy hops
    - C) More proxy instances
    - D) No encryption overhead

<details>
<summary>Show Answer</summary>

**Answer: B) Kernel-level processing via eBPF reduces proxy hops**

**Explanation:**
Cilium processes L3/L4 traffic directly in the kernel using eBPF, avoiding userspace proxy hops. For L7 traffic, the per-node proxy model still results in fewer hops than per-pod sidecars. This results in lower latency overhead.

</details>

---

34. When should you choose Cilium Service Mesh over Istio?
    - A) When you need the most configuration options
    - B) When you need high performance and lower resource overhead
    - C) When you prefer a sidecar-based architecture
    - D) When you need Kiali dashboards

<details>
<summary>Show Answer</summary>

**Answer: B) When you need high performance and lower resource overhead**

**Explanation:**
Cilium is ideal when performance and resource efficiency are priorities. Its eBPF-based architecture and per-node proxy model provide significantly lower overhead compared to sidecar-based meshes, especially in large-scale deployments.

</details>

---

35. What is the recommended approach for implementing network policies with Cilium Service Mesh?
    - A) Use only Kubernetes NetworkPolicy
    - B) Start with default deny and explicitly allow traffic using CiliumNetworkPolicy
    - C) No policies are needed with Cilium
    - D) Use Istio AuthorizationPolicy

<details>
<summary>Show Answer</summary>

**Answer: B) Start with default deny and explicitly allow traffic using CiliumNetworkPolicy**

**Explanation:**
The security best practice is to implement default-deny policies and explicitly allow necessary traffic. CiliumNetworkPolicy (and CiliumClusterwideNetworkPolicy) provide L3-L7 policy capabilities beyond standard Kubernetes NetworkPolicy.

</details>

---

36. What tool should you use to verify Cilium installation and connectivity?
    - A) `kubectl cluster-info`
    - B) `cilium connectivity test`
    - C) `istioctl analyze`
    - D) `linkerd check`

<details>
<summary>Show Answer</summary>

**Answer: B) cilium connectivity test**

**Explanation:**
The `cilium connectivity test` command runs a comprehensive suite of tests to verify Cilium installation, network connectivity, policy enforcement, and service discovery. It's essential for validating deployments and troubleshooting issues.

</details>

---

## Summary

This quiz covered the key aspects of Cilium Service Mesh:
- Architecture: Sidecar-less design, eBPF data plane, per-node Envoy
- eBPF: Program types, maps, kube-proxy replacement
- Traffic Management: CiliumEnvoyConfig, L7 routing, load balancing
- Security: SPIFFE identities, mTLS with CiliumNetworkPolicy
- Observability: Hubble CLI, UI, and metrics
- Gateway API: Native support, GatewayClass cilium
- EKS: VPC CNI replacement, ENI mode, prefix delegation
- Best Practices: Default deny policies, connectivity testing
