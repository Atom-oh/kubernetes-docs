# Cilium Service Mesh Architecture Quiz

This quiz tests your understanding of Cilium Service Mesh architecture, eBPF datapath, node Envoy proxy, and CRD model.

## Quiz Questions

### 1. What is the key difference between Cilium Service Mesh and traditional sidecar-based service meshes?

A. Not Kubernetes native
B. Uses eBPF to process L3/L4 traffic at the kernel level
C. Processes all traffic in user space
D. Uses multiple proxies per Pod

<details>
<summary>Show Answer</summary>

**Answer: B. Uses eBPF to process L3/L4 traffic at the kernel level**

**Explanation:**
Cilium Service Mesh uses eBPF (extended Berkeley Packet Filter) to process L3/L4 traffic directly within the Linux kernel. This is fundamentally different from traditional service meshes that process all traffic through user-space sidecar proxies. Traffic is only forwarded to a shared per-node Envoy proxy when L7 processing is required.

</details>

### 2. Which is NOT an eBPF hook point where Cilium programs can execute?

A. XDP (eXpress Data Path)
B. TC (Traffic Control)
C. Application Layer
D. cgroup

<details>
<summary>Show Answer</summary>

**Answer: C. Application Layer**

**Explanation:**
eBPF programs run at the kernel level, with key hook points being XDP (NIC driver), TC (network stack entry), Socket Operations (socket level), and cgroup (process group). The Application Layer is in user space and therefore not an eBPF hook point.

</details>

### 3. What is the advantage of Cilium's per-node Envoy proxy model?

A. More complex configuration possible
B. Increased memory usage per Pod
C. Resource efficiency and low latency
D. Cannot encrypt all traffic

<details>
<summary>Show Answer</summary>

**Answer: C. Resource efficiency and low latency**

**Explanation:**
Using one Envoy proxy per node uses significantly less memory than deploying sidecars per Pod. In a 100-Pod cluster, Istio uses about 5GB (50MB per Pod), while Cilium uses only about 500MB (100MB per node). Additionally, L3/L4 traffic is processed directly in eBPF, significantly reducing latency.

</details>

### 4. What is the primary purpose of the CiliumEnvoyConfig CRD?

A. Define Kubernetes network policies
B. Define Envoy proxy configuration for specific services
C. Define Pod scheduling rules
D. Define storage classes

<details>
<summary>Show Answer</summary>

**Answer: B. Define Envoy proxy configuration for specific services**

**Explanation:**
CiliumEnvoyConfig is a namespace-scoped CRD that defines Envoy proxy settings (listeners, routes, clusters, etc.) for specific services. This allows configuring L7 features such as HTTP routing, header manipulation, and load balancing.

</details>

### 5. Which load balancing algorithm provides consistent hashing when Cilium replaces kube-proxy?

A. Random
B. Round Robin
C. Maglev
D. Least Connection

<details>
<summary>Show Answer</summary>

**Answer: C. Maglev**

**Explanation:**
Maglev is a consistent hashing algorithm developed by Google, used in Cilium's eBPF-based load balancer. This algorithm provides session affinity that maintains most existing connections even when backends change. It offers high performance with O(1) lookup time.

</details>

### 6. Which statement about Cilium Identity is correct?

A. Identifies workloads based on IP addresses
B. Generates numeric IDs by hashing Pod labels
C. Uses MAC addresses for identification
D. Must be manually assigned by users

<details>
<summary>Show Answer</summary>

**Answer: B. Generates numeric IDs by hashing Pod labels**

**Explanation:**
Cilium Identity generates unique numeric IDs by hashing Pod labels (namespace, service account, user-defined labels, etc.). This ID-based approach has the advantage that policies are not affected when IP addresses change.

</details>

### 7. What happens to traffic flow when an L7 policy is applied in Cilium?

A. All traffic always passes through Envoy
B. Only traffic with L7 policies is redirected to Envoy
C. Envoy is completely bypassed
D. Traffic is dropped

<details>
<summary>Show Answer</summary>

**Answer: B. Only traffic with L7 policies is redirected to Envoy**

**Explanation:**
For efficiency, Cilium only redirects traffic with L7 policies to the node Envoy proxy. Traffic with only L3/L4 policies or no policies is processed directly in eBPF and forwarded quickly within the kernel.

</details>

### 8. Where is Cilium's connection tracking performed?

A. conntrack daemon in user space
B. eBPF maps
C. Envoy proxy
D. Kubernetes API server

<details>
<summary>Show Answer</summary>

**Answer: B. eBPF maps**

**Explanation:**
Cilium uses eBPF maps for connection tracking. CT (Connection Tracking) maps store and look up connection state within the kernel, enabling caching and fast application of policy decisions for existing connections.

</details>

### 9. What is the difference between CiliumClusterwideNetworkPolicy and CiliumNetworkPolicy?

A. Both have the same scope
B. CiliumClusterwideNetworkPolicy applies cluster-wide
C. CiliumNetworkPolicy has more features
D. CiliumClusterwideNetworkPolicy does not support L7 policies

<details>
<summary>Show Answer</summary>

**Answer: B. CiliumClusterwideNetworkPolicy applies cluster-wide**

**Explanation:**
CiliumNetworkPolicy is namespace-scoped, while CiliumClusterwideNetworkPolicy is cluster-wide scoped. Cluster-wide policies are useful for default deny policies or security rules that must apply to all namespaces. Both CRDs support L7 policies.

</details>

### 10. What is the format of SPIFFE IDs used in Cilium Service Mesh?

A. urn:spiffe:cluster/namespace/pod
B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>
C. https://spiffe.io/id/\<pod-name\>
D. spiffe:\<namespace\>:\<pod-name\>

<details>
<summary>Show Answer</summary>

**Answer: B. spiffe://cluster.local/ns/\<namespace\>/sa/\<service-account\>**

**Explanation:**
SPIFFE (Secure Production Identity Framework for Everyone) IDs are unique identifiers for workloads. When integrating with SPIRE in Cilium Service Mesh, each workload receives a SPIFFE ID in the format `spiffe://cluster.local/ns/<namespace>/sa/<service-account>`. This ID is used for mTLS authentication.

</details>

### 11. Which is NOT a role of the Cilium Agent?

A. eBPF program management
B. Envoy configuration generation and synchronization
C. Kubernetes API server role
D. Identity management

<details>
<summary>Show Answer</summary>

**Answer: C. Kubernetes API server role**

**Explanation:**
The Cilium Agent runs on each node and is responsible for eBPF program management, policy compilation, Envoy configuration generation/synchronization, identity management, endpoint management, and flow logging. The Kubernetes API server is part of the Kubernetes control plane and is separate from Cilium.

</details>

### 12. What optimization does Cilium provide for Pod-to-Pod communication on the same node?

A. Always routes through external network
B. Direct kernel path via eBPF bypassing the network stack
C. Forwards all traffic to Envoy
D. Communication not possible

<details>
<summary>Show Answer</summary>

**Answer: B. Direct kernel path via eBPF bypassing the network stack**

**Explanation:**
For Pod-to-Pod communication on the same node, Cilium uses eBPF to forward traffic through a direct kernel path. This bypasses the entire Linux network stack, achieving very low latency (~0.1ms).

</details>
