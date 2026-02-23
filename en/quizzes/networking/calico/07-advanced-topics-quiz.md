# Advanced Topics Quiz

> **Related Document**: [Advanced Topics](../../../networking/calico/07-advanced-topics.md)
> **Last Updated**: February 22, 2026

## Quiz

1. In Calico's block-based IPAM, how many IP addresses does a /26 CIDR block provide?
   - A) 32 IPs
   - B) 64 IPs
   - C) 128 IPs
   - D) 256 IPs

<details>
<summary>Show Answer</summary>

**Answer: B) 64 IPs**

**Explanation:**
A /26 CIDR block provides 64 IP addresses (2^(32-26) = 2^6 = 64). Calico allocates IP blocks of configurable size to nodes, and then assigns individual IPs from these blocks to pods. The default block size is /26, which balances efficiency with IP utilization.

</details>

2. What is IP block affinity in Calico's IPAM?
   - A) Pods with the same label always get IPs from the same block
   - B) Nodes claim and preferentially use specific IP blocks
   - C) Services are assigned IPs close to their endpoints
   - D) IP addresses are grouped by availability zone

<details>
<summary>Show Answer</summary>

**Answer: B) Nodes claim and preferentially use specific IP blocks**

**Explanation:**
IP block affinity means that when a node needs to allocate pod IPs, it claims one or more IP blocks and preferentially allocates from those blocks. This improves routing efficiency because all pods on a node typically share the same IP prefix, enabling route aggregation.

</details>

3. How is WireGuard encryption activated in Calico?
   - A) Installing a separate WireGuard operator
   - B) Setting wireguardEnabled: true in FelixConfiguration
   - C) Applying a WireGuard NetworkPolicy
   - D) Enabling it in the Kubernetes API server flags

<details>
<summary>Show Answer</summary>

**Answer: B) Setting wireguardEnabled: true in FelixConfiguration**

**Explanation:**
WireGuard encryption is enabled by setting `wireguardEnabled: true` in the FelixConfiguration resource. Calico automatically manages WireGuard key generation and distribution between nodes, creating encrypted tunnels for pod-to-pod traffic across nodes.

</details>

4. What is a key advantage of WireGuard over IPsec for encrypting pod traffic?
   - A) WireGuard supports more encryption algorithms
   - B) WireGuard has simpler configuration and lower CPU overhead
   - C) WireGuard works without kernel support
   - D) WireGuard provides better compression

<details>
<summary>Show Answer</summary>

**Answer: B) WireGuard has simpler configuration and lower CPU overhead**

**Explanation:**
WireGuard offers simpler configuration with fewer options (which reduces misconfiguration risk) and typically lower CPU overhead compared to IPsec. It uses modern cryptographic primitives and has a smaller codebase, making it easier to audit and maintain.

</details>

5. What is the primary use case for Calico's Egress Gateway feature?
   - A) Load balancing ingress traffic to services
   - B) Providing consistent source IPs for pods accessing external services
   - C) Caching DNS responses for faster resolution
   - D) Rate limiting outbound API calls

<details>
<summary>Show Answer</summary>

**Answer: B) Providing consistent source IPs for pods accessing external services**

**Explanation:**
Egress Gateway allows pods to access external services using a consistent, predictable source IP address. This is essential when external services use IP-based allowlisting, as it ensures traffic from specific pods always appears to come from known gateway IPs.

</details>

6. What capability does Calico's multi-cluster federation provide?
   - A) Automatic failover between clusters
   - B) Shared network policies and service discovery across clusters
   - C) Centralized logging for all clusters
   - D) Unified billing across clusters

<details>
<summary>Show Answer</summary>

**Answer: B) Shared network policies and service discovery across clusters**

**Explanation:**
Multi-cluster federation allows Calico to share network policies, enable cross-cluster service discovery, and provide consistent networking across multiple Kubernetes clusters. This enables workloads in different clusters to communicate securely using unified policies.

</details>

7. Which statement about Calico's Windows support is correct?
   - A) Windows nodes require a different CNI plugin
   - B) Calico supports Windows nodes with some feature limitations
   - C) Windows support is only available in Calico Enterprise
   - D) Windows nodes cannot participate in BGP peering

<details>
<summary>Show Answer</summary>

**Answer: B) Calico supports Windows nodes with some feature limitations**

**Explanation:**
Calico supports Windows nodes in Kubernetes clusters, enabling mixed Linux/Windows environments. However, some features like eBPF dataplane are not available on Windows due to OS differences. Windows support covers basic networking and network policy enforcement.

</details>

8. What is a key difference between Calico Enterprise and Calico Open Source?
   - A) Enterprise uses a different dataplane technology
   - B) Enterprise includes additional security, compliance, and observability features
   - C) Enterprise only works with specific Kubernetes distributions
   - D) Enterprise does not support BGP

<details>
<summary>Show Answer</summary>

**Answer: B) Enterprise includes additional security, compliance, and observability features**

**Explanation:**
Calico Enterprise builds on the open source project and adds features like hierarchical policy tiers, flow visualization, compliance reporting, threat defense, and enterprise support. The core networking dataplane is the same between both versions.

</details>

9. What is the Typha sizing formula for large Calico deployments?
   - A) 1 Typha per 100 nodes
   - B) 1 Typha per 500 nodes, minimum 3 for HA
   - C) Typha replicas = nodes / 200, recommended for 1000+ node clusters
   - D) Fixed at 5 replicas regardless of cluster size

<details>
<summary>Show Answer</summary>

**Answer: C) Typha replicas = nodes / 200, recommended for 1000+ node clusters**

**Explanation:**
For clusters with 1000+ nodes, Typha becomes essential for scalability. The general sizing formula is approximately 1 Typha replica per 200 nodes, with a minimum of 3 replicas for high availability. Typha fans out datastore updates to Felix instances, reducing API server load.

</details>

10. What is required for Calico to support IPv6 and dual-stack networking?
    - A) A separate IPv6-specific installation
    - B) Configuring IPPools for both IPv4 and IPv6 address ranges
    - C) Using only the eBPF dataplane
    - D) Disabling network policy enforcement

<details>
<summary>Show Answer</summary>

**Answer: B) Configuring IPPools for both IPv4 and IPv6 address ranges**

**Explanation:**
Dual-stack support in Calico requires configuring IPPools for both IPv4 and IPv6 CIDR ranges. Pods can then receive addresses from both pools. The cluster must also have dual-stack enabled at the Kubernetes level, and underlying infrastructure must support IPv6.

</details>

11. How can you detect IP address exhaustion in Calico's IPAM?
    - A) Checking the kube-apiserver logs
    - B) Using calicoctl ipam show to view allocation status
    - C) Monitoring node memory usage
    - D) Checking pod restart counts

<details>
<summary>Show Answer</summary>

**Answer: B) Using calicoctl ipam show to view allocation status**

**Explanation:**
The `calicoctl ipam show` command displays IPAM allocation status including total IPs, allocated IPs, and available IPs across all pools and blocks. The `--show-blocks` flag provides detailed per-node block allocation information, helping identify exhaustion issues.

</details>

12. When should you choose etcd as Calico's datastore instead of the Kubernetes API?
    - A) For clusters smaller than 100 nodes
    - B) When running in managed Kubernetes services
    - C) For very large clusters or non-Kubernetes deployments
    - D) When using the eBPF dataplane

<details>
<summary>Show Answer</summary>

**Answer: C) For very large clusters or non-Kubernetes deployments**

**Explanation:**
The etcd datastore is recommended for very large clusters where Kubernetes API server load is a concern, or for non-Kubernetes deployments (bare metal, VMs). For most Kubernetes deployments, the Kubernetes datastore is simpler as it doesn't require managing a separate etcd cluster.

</details>
