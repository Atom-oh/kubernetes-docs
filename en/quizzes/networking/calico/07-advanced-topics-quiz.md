# Advanced Topics Quiz

> **Related Document**: [Advanced Topics](../../../networking/calico/07-advanced-topics.md)
> **Last Updated**: September 12, 2026

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
An IPv4 /26 contains 64 addresses. This is not always 64 usable Pod addresses: Calico Windows reserves four per owned block. IPv6 defaults use /122, also 64 addresses. Set blockSize when creating a pool; it is not an in-place tuning change.

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
Nodes preferentially allocate from their affine blocks, subject to pool selection and limits. A node may have several blocks, and permitted borrowing can create more-specific routes. Block affinity is not the same as Node.spec.podCIDR or a guarantee that every Pod on a node shares one prefix.

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
wireguardEnabled enables the supported IPv4 path; wireguardEnabledV6 is separate. Both peers need compatible kernel/network support. Calico manages node keys and publishes public keys. Same-node traffic and unsupported peers are not automatically encrypted by the inter-node tunnel.

</details>

4. Which statement describes WireGuard’s design without claiming a universal performance result?
   - A) WireGuard supports more encryption algorithms
   - B) WireGuard uses a deliberately limited cryptographic design and key configuration
   - C) Calico WireGuard needs no node or runtime prerequisites
   - D) WireGuard provides better compression

<details>
<summary>Show Answer</summary>

**Answer: B) WireGuard uses a deliberately limited cryptographic design and key configuration**

**Explanation:**
WireGuard deliberately limits cryptographic choices. CPU cost, throughput, roaming and offload comparisons depend on the implementation and workload. Unversioned code-line counts and the chapter’s unverified performance ranges are not a universal security or speed ranking.

</details>

5. What is the primary use case for the documented Calico Enterprise Egress Gateway?
   - A) Load balancing ingress traffic to services
   - B) Providing consistent source IPs for pods accessing external services
   - C) Caching DNS responses for faster resolution
   - D) Rate limiting outbound API calls

<details>
<summary>Show Answer</summary>

**Answer: B) Providing consistent source IPs for pods accessing external services**

**Explanation:**
A transit gateway Pod performs SNAT for selected clients, exposing a controlled source-address set. Actual observed addresses depend on pool/upstream NAT and availability. NetworkPolicy Allow and BGP serviceExternalIPs do not create that routing/SNAT behavior. Source allowlisting is not complete compliance or application authorization.

</details>

6. What does the current Calico Enterprise federation feature provide?
   - A) Automatic replication and failover of application databases
   - B) Remote endpoint identity and selected Service discovery while policies remain locally applied
   - C) Centralized logging for all clusters
   - D) Unified billing across clusters

<details>
<summary>Show Answer</summary>

**Answer: B) Remote endpoint identity and selected Service discovery while policies remain locally applied**

**Explanation:**
Federated endpoint identity feeds remote endpoint information into local policy calculation; it does not copy remote policies onto local endpoints. A separate Federated Services Controller reads remote Kubernetes APIs. Routable, source-preserved Pod paths and controller credentials/configuration are prerequisites; Typha is not a shared Federation Controller.

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
Calico Windows uses HNS/HostProcess with platform and version limits. IPv4 VXLAN or supported non-overlay BGP are available, but IPv6/dual stack, eBPF, WireGuard, HostEndpoint policy and Service advertisement are excluded in the reviewed Windows guide. Match OS/container builds and the actual provider profile.

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
Open Source 3.32 already includes tiers, Whisker/flow visibility, staged policies and HTTP policy through Istio/Dikastes. Commercial editions add product-specific capabilities such as domain policy, egress gateways, remote identity/services and reporting. Feature/support terms depend on the selected product and version.

</details>

9. What Typha replica target does Tigera Operator 1.42.6 calculate for 1,000 counted nodes?
   - A) 5 replicas
   - B) 3 replicas
   - C) 7 replicas
   - D) 10 replicas

<details>
<summary>Show Answer</summary>

**Answer: C) 7 replicas**

**Explanation:**
For N>4, the reviewed operator uses max(3, floor(N/200)+2), giving 7 at 1,000 nodes. N<=2 gives 1 and N<=4 gives 2. This is an implementation target with node-count/placement conditions, not a measured “200 nodes per Typha” capacity guarantee.

</details>

10. Which pool prerequisite applies to a Calico-IPAM dual-stack deployment?
    - A) A separate IPv6-specific installation
    - B) Configuring IPPools for both IPv4 and IPv6 address ranges
    - C) Using only the eBPF dataplane
    - D) Disabling network policy enforcement

<details>
<summary>Show Answer</summary>

**Answer: B) Configuring IPPools for both IPv4 and IPv6 address ranges**

**Explanation:**
Calico-IPAM dual stack uses IPv4 and IPv6 pools, while Kubernetes, CNI, node addressing and the underlay must also support both families. IPv6-only does not require an IPv4 pool. Felix ipv6Support is a boolean; adding that flag or pools alone does not convert an existing cluster’s IP-family configuration.

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
ipam show reports allocation usage and --show-blocks adds block detail. Use BlockAffinity for node association and consider eligible pools, reservations and affinity/host limits. Free addresses elsewhere do not guarantee allocation. Clean up only verified stale allocations using a fresh recovery report, not a copied sample IP.

</details>

12. Which is a reason to consider a direct-etcd Calico profile?
    - A) For clusters smaller than 100 nodes
    - B) When running in managed Kubernetes services
    - C) A supported non-Kubernetes deployment with an explicit etcd operating and recovery plan
    - D) When using the eBPF dataplane

<details>
<summary>Show Answer</summary>

**Answer: C) A supported non-Kubernetes deployment with an explicit etcd operating and recovery plan**

**Explanation:**
Direct etcd can be appropriate for a supported separately designed deployment. Kubernetes datastore is simpler for many Kubernetes installations and is required by the current eBPF dataplane. No fixed 5,000-node threshold or universal read-speed comparison determines the choice.

</details>
