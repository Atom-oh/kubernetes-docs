# eBPF Dataplane Quiz

> **Related Document**: [eBPF Dataplane](../../../networking/calico/06-ebpf-dataplane.md)
> **Last Updated**: September 12, 2026

## Quiz

1. What is the generic minimum Linux kernel in the current Calico 3.32 eBPF guide, excluding its RHEL backport exception?
   - A) 4.15+
   - B) 5.0+
   - C) 5.3+
   - D) 5.10+

<details>
<summary>Show Answer</summary>

**Answer: D) 5.10+**

**Explanation:**
The generic baseline is 5.10. The guide documents RHEL 8.4 with kernel 4.18.0-305 or newer as a backport exception. Some features need more: eBPF Log rules require 5.16 and documented QoS bandwidth controls require 6.6/TCX. An OS or kernel version alone does not establish full platform compatibility.

</details>

2. How should performance improvement from switching to Calico eBPF be assessed?
   - A) 5-10% throughput increase
   - B) Measure the actual workload and configuration; there is no universal percentage
   - C) 50-60% throughput increase
   - D) 100% throughput increase

<details>
<summary>Show Answer</summary>

**Answer: B) Measure the actual workload and configuration; there is no universal percentage**

**Explanation:**
Both dataplanes process packets in the kernel. Improvement depends on traffic path, rules, conntrack, CPU/NIC, logging and load. The guide preserves different historical reported values without raw evidence; they are not a promise of 20–40% improvement or constant policy cost.

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
BTF provides type metadata used by tools and CO-RE relocation. It is distinct from verifier safety checks and does not guarantee that every compiled program works on every kernel. Calico includes version-specific object selection and feature checks; file existence alone is not a complete readiness test.

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
DSR lets a remote backend node return traffic without the Kubernetes node that initially forwarded the Service request. Calico performs source translation. It requires a compatible fabric and return path; it does not automatically bypass or work with every external cloud load balancer.

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
For supported TCP sockets, CTLB translates the Service destination during connect(), before packet processing. Enabled mode can also include UDP socket hooks. It avoids that Service DNAT path, not all policy/routing/conntrack or other NAT. DSR is a separate external-return-path optimization.

</details>

6. Which statement correctly describes kube-proxy coordination with Calico eBPF?
   - A) kube-proxy must always remain unchanged alongside eBPF
   - B) Calico can handle Services with platform-specific coordination of kube-proxy
   - C) kube-proxy is automatically upgraded to use eBPF
   - D) kube-proxy handles IPv6 while eBPF handles IPv4

<details>
<summary>Show Answer</summary>

**Answer: B) Calico can handle Services with platform-specific coordination of kube-proxy**

**Explanation:**
Use the installation owner’s workflow. Conditional automatic bootstrap can manage kube-proxy, while platforms that retain a managed proxy require cleanup disabled and a non-conflicting health-server setting. A cleanup flag alone is not a Service-enable switch, and deleting kube-proxy is not a universal procedure.

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
Maps hold route, NAT, conntrack, affinity and supporting program/counter/IP-set data. Different families use hash, LRU hash, LPM trie or other types. Policies are compiled into BPF programs; they are not all stored in a universal constant-time tuple-to-action map.

</details>

8. How does native driver XDP compare with TC attachment points?
   - A) XDP processes packets earlier in the network stack than TC
   - B) TC processes packets earlier in the network stack than XDP
   - C) XDP is for ingress only, TC is for egress only
   - D) There is no difference; they are aliases

<details>
<summary>Show Answer</summary>

**Answer: A) XDP processes packets earlier in the network stack than TC**

**Explanation:**
Native driver XDP can act before skb allocation, whereas TC operates on skb-based packet context. Generic XDP runs later and already has an skb. Driver, hardware and program support matter; the hook name does not guarantee a fixed performance advantage.

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
bpfEnabled: true is the Felix field used in the standalone manifest workflow. Operator installations select Installation.spec.calicoNetwork.linuxDataplane: BPF. Preserve ownership, direct API access, proxy coordination and the supported cluster-wide transition.

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
For remote Service backends, Tunnel uses the ingress-node/tunnel path for request and reply; DSR tunnels the request but returns directly from the backend node. Both modes require the relevant VXLAN/MTU path. DSR adds source-validation and external-load-balancer restrictions.

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
bpftool inspects real BPF program/map IDs, types and state. The Calico node image also embeds calico-node -bpf; use its help subcommand and complete arguments such as `policy dump <interface> <hook>`. A listing alone does not prove application connectivity.

</details>

12. Which approach is appropriate for a Calico 3.32 dataplane migration?
    - A) Enable eBPF immediately on all nodes simultaneously
    - B) Disable kube-proxy first, then enable eBPF
    - C) Verify compatibility/direct API access and follow the owner’s coordinated migration and rollback workflow
    - D) Reinstall Calico from scratch with eBPF enabled

<details>
<summary>Show Answer</summary>

**Answer: C) Verify compatibility/direct API access and follow the owner’s coordinated migration and rollback workflow**

**Explanation:**
Automatic operator bootstrap has restricted prerequisites; other installations need their documented manual/platform workflow. Do not leave a persistent mixed-mode canary or disable all kube-proxy instances before an unprepared test. The official rolling transition can disrupt NodePort traffic, and rollback can reset connections.

</details>
