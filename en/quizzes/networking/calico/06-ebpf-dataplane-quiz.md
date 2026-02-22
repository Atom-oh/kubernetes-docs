# eBPF Dataplane Quiz

> **Related Document**: [eBPF Dataplane](../../../networking/calico/06-ebpf-dataplane.md)
> **Last Updated**: February 22, 2025

## Quiz

1. What is the minimum Linux kernel version required for Calico's eBPF dataplane?
   - A) 4.15+
   - B) 5.0+
   - C) 5.3+
   - D) 5.10+

<details>
<summary>Show Answer</summary>

**Answer: C) 5.3+**

**Explanation:**
Calico's eBPF dataplane requires a minimum kernel version of 5.3. However, kernel 5.8+ is recommended for optimal performance and full feature support including BTF (BPF Type Format) which enables better debugging and introspection capabilities.

</details>

2. What performance improvement can typically be expected when switching from iptables to eBPF dataplane in Calico?
   - A) 5-10% throughput increase
   - B) 20-40% throughput increase
   - C) 50-60% throughput increase
   - D) 100% throughput increase

<details>
<summary>Show Answer</summary>

**Answer: B) 20-40% throughput increase**

**Explanation:**
The eBPF dataplane typically provides 20-40% throughput improvement over iptables. This is because eBPF processes packets directly in the kernel without the overhead of traversing iptables chains, which can become significant as the number of rules grows.

</details>

3. What does BTF stand for, and why is it important for Calico's eBPF dataplane?
   - A) Binary Transfer Format - for network packet encoding
   - B) BPF Type Format - for debugging and CO-RE support
   - C) Byte Translation Function - for address conversion
   - D) Block Transfer Filter - for rate limiting

<details>
<summary>Show Answer</summary>

**Answer: B) BPF Type Format - for debugging and CO-RE support**

**Explanation:**
BTF (BPF Type Format) provides type information for BPF programs. It enables CO-RE (Compile Once, Run Everywhere) support, allowing eBPF programs to run across different kernel versions without recompilation. BTF also enables better debugging capabilities with tools like bpftool.

</details>

4. What is Direct Server Return (DSR) in the context of Calico's eBPF dataplane?
   - A) A method for pods to directly contact the Kubernetes API server
   - B) A load balancing optimization where return traffic bypasses the load balancer
   - C) A DNS resolution technique for service discovery
   - D) A storage access pattern for persistent volumes

<details>
<summary>Show Answer</summary>

**Answer: B) A load balancing optimization where return traffic bypasses the load balancer**

**Explanation:**
Direct Server Return (DSR) is a load balancing optimization where response traffic from the backend server goes directly to the client, bypassing the load balancer node. This reduces latency and load balancer bandwidth consumption, improving overall service performance.

</details>

5. What is connect-time load balancing in Calico's eBPF dataplane?
   - A) Load balancing that occurs when a node joins the cluster
   - B) Service IP translation performed at TCP connection establishment
   - C) A health check mechanism for backend pods
   - D) Automatic failover when connections drop

<details>
<summary>Show Answer</summary>

**Answer: B) Service IP translation performed at TCP connection establishment**

**Explanation:**
Connect-time load balancing performs service IP to pod IP translation at the moment a TCP connection is established, rather than on every packet. This provides more efficient load balancing and allows for features like DSR, as the client socket connects directly to the chosen backend.

</details>

6. When Calico's eBPF dataplane is enabled, what happens to kube-proxy?
   - A) kube-proxy continues to run alongside eBPF
   - B) kube-proxy can be disabled as eBPF provides equivalent functionality
   - C) kube-proxy is automatically upgraded to use eBPF
   - D) kube-proxy handles IPv6 while eBPF handles IPv4

<details>
<summary>Show Answer</summary>

**Answer: B) kube-proxy can be disabled as eBPF provides equivalent functionality**

**Explanation:**
Calico's eBPF dataplane can fully replace kube-proxy for service load balancing. When eBPF mode is enabled, kube-proxy can be disabled to avoid redundant processing and potential conflicts. The eBPF dataplane handles ClusterIP, NodePort, and LoadBalancer services directly.

</details>

7. What are BPF maps used for in Calico's eBPF dataplane?
   - A) Storing geographical location data for geo-routing
   - B) Storing state and configuration data shared between kernel and userspace
   - C) Mapping DNS names to IP addresses
   - D) Creating network topology diagrams

<details>
<summary>Show Answer</summary>

**Answer: B) Storing state and configuration data shared between kernel and userspace**

**Explanation:**
BPF maps are key-value data structures that store state and configuration data accessible by both eBPF programs running in the kernel and userspace applications. Calico uses BPF maps to store connection tracking state, policy rules, service endpoints, and other networking metadata.

</details>

8. What is the difference between XDP and TC attachment points for eBPF programs?
   - A) XDP processes packets earlier in the network stack than TC
   - B) TC processes packets earlier in the network stack than XDP
   - C) XDP is for ingress only, TC is for egress only
   - D) There is no difference; they are aliases

<details>
<summary>Show Answer</summary>

**Answer: A) XDP processes packets earlier in the network stack than TC**

**Explanation:**
XDP (eXpress Data Path) processes packets at the earliest possible point in the network stack, even before the kernel allocates an sk_buff. TC (Traffic Control) hooks process packets later, after the sk_buff is allocated. XDP provides maximum performance but has limited functionality, while TC offers more features at a slight performance cost.

</details>

9. Which FelixConfiguration setting enables the eBPF dataplane in Calico?
   - A) dataplaneMode: eBPF
   - B) bpfEnabled: true
   - C) useEBPF: yes
   - D) felixBackend: ebpf

<details>
<summary>Show Answer</summary>

**Answer: B) bpfEnabled: true**

**Explanation:**
The eBPF dataplane is enabled by setting `bpfEnabled: true` in the FelixConfiguration resource. Additional eBPF-specific settings like `bpfExternalServiceMode`, `bpfKubeProxyIptablesCleanupEnabled`, and others can be configured in the same resource.

</details>

10. What does the bpfExternalServiceMode setting control in Calico?
    - A) How pods access external services outside the cluster
    - B) How external clients access NodePort and LoadBalancer services
    - C) Which external DNS servers are used for service discovery
    - D) Authentication mode for external API access

<details>
<summary>Show Answer</summary>

**Answer: B) How external clients access NodePort and LoadBalancer services**

**Explanation:**
The `bpfExternalServiceMode` setting controls how Calico handles traffic from external sources to NodePort and LoadBalancer services. Options include "Tunnel" (default, preserves source IP through encapsulation) and "DSR" (Direct Server Return for improved performance).

</details>

11. Which tool is commonly used to debug and inspect Calico's eBPF programs and maps?
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables-save

<details>
<summary>Show Answer</summary>

**Answer: B) bpftool**

**Explanation:**
bpftool is the standard utility for inspecting and debugging eBPF programs and maps. It can list loaded BPF programs, dump map contents, show program statistics, and display BTF information. This is essential for troubleshooting Calico's eBPF dataplane.

</details>

12. What is the recommended sequence for migrating from iptables to eBPF dataplane in Calico?
    - A) Enable eBPF immediately on all nodes simultaneously
    - B) Disable kube-proxy first, then enable eBPF
    - C) Enable eBPF on Calico, verify operation, then disable kube-proxy
    - D) Reinstall Calico from scratch with eBPF enabled

<details>
<summary>Show Answer</summary>

**Answer: C) Enable eBPF on Calico, verify operation, then disable kube-proxy**

**Explanation:**
The recommended migration path is: 1) Enable eBPF dataplane in FelixConfiguration, 2) Verify that networking and services work correctly, 3) Disable kube-proxy once eBPF operation is confirmed. This allows for safe rollback if issues are discovered during migration.

</details>
