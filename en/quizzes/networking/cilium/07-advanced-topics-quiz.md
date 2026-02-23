# Cilium Advanced Quiz

> **Supported Version**: Cilium 1.17
> **Last Updated**: February 22, 2026

## eBPF Technology

1. **Where do eBPF programs run?**
   - A) User Space
   - B) Kernel Space
   - C) Inside containers
   - D) Inside virtual machines

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Kernel Space</p>
   <p><strong>Explanation</strong>: eBPF programs run safely inside the Linux kernel and can extend and modify kernel functionality.</p>
   </details>

2. **What mechanism ensures the safety of eBPF programs?**
   - A) Virtualization
   - B) Containerization
   - C) Static Verifier
   - D) Encryption

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) Static Verifier</p>
   <p><strong>Explanation</strong>: The eBPF verifier checks the safety of programs before they are loaded to prevent infinite loops or kernel crashes.</p>
   </details>

3. **Which is NOT a main benefit of using eBPF in Cilium?**
   - A) Implementing networking features without kernel modules
   - B) High performance and low overhead
   - C) Fine-grained network policy enforcement
   - D) Hardware acceleration required

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: D) Hardware acceleration required</p>
   <p><strong>Explanation</strong>: eBPF can provide high performance on a software basis without requiring hardware acceleration.</p>
   </details>

## Networking Models

4. **Which data path mode is NOT supported by Cilium?**
   - A) VXLAN
   - B) Geneve
   - C) Direct Routing
   - D) MPLS

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: D) MPLS</p>
   <p><strong>Explanation</strong>: Cilium supports VXLAN, Geneve, and Direct Routing, but does not support MPLS.</p>
   </details>

5. **What technology does Cilium use in kube-proxy replacement mode?**
   - A) iptables
   - B) IPVS
   - C) eBPF-based XDP
   - D) netfilter

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) eBPF-based XDP</p>
   <p><strong>Explanation</strong>: Cilium uses eBPF and XDP (eXpress Data Path) to replace kube-proxy and provide higher performance.</p>
   </details>

6. **What feature in Cilium's network model tracks packet paths during Pod-to-Pod communication?**
   - A) tcpdump
   - B) Hubble Flow Monitoring
   - C) Wireshark
   - D) Prometheus

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Hubble Flow Monitoring</p>
   <p><strong>Explanation</strong>: Hubble is Cilium's network flow monitoring tool that can track and visualize Pod-to-Pod communication in real-time.</p>
   </details>

## IPAM and Network Policies

7. **Which IPAM (IP Address Management) mode in Cilium integrates with AWS EKS?**
   - A) Cluster Pool
   - B) Kubernetes Host Scope
   - C) AWS ENI
   - D) CRD-based

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) AWS ENI</p>
   <p><strong>Explanation</strong>: Cilium integrates with EKS through AWS ENI (Elastic Network Interface) mode to directly assign VPC IP addresses to Pods.</p>
   </details>

8. **What does the 'toFQDNs' rule allow in Cilium network policies?**
   - A) Traffic to specific IP addresses
   - B) Traffic to specific ports
   - C) Traffic to specific domain names
   - D) Traffic of specific protocols

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) Traffic to specific domain names</p>
   <p><strong>Explanation</strong>: The toFQDNs rule allows traffic to specific domain names (FQDNs), and Cilium monitors DNS lookups to dynamically allow IP addresses for those domains.</p>
   </details>

9. **Which selector is NOT supported in Cilium CiliumNetworkPolicy?**
   - A) endpointSelector
   - B) nodeSelector
   - C) namespaceSelector
   - D) serviceSelector

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: D) serviceSelector</p>
   <p><strong>Explanation</strong>: Cilium supports endpointSelector, nodeSelector, and namespaceSelector, but does not directly support serviceSelector.</p>
   </details>

## L2-L7 Networking

10. **Which attribute cannot be filtered by Cilium's L7 policies for HTTP requests?**
    - A) Path
    - B) Method
    - C) Headers
    - D) Response Time

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Response Time</p>
    <p><strong>Explanation</strong>: Cilium's L7 policies can filter HTTP request attributes such as path, method, and headers, but response time is not a filtering target.</p>
    </details>

11. **What is NOT provided by Cilium's Service Mesh features?**
    - A) Mutual TLS (mTLS)
    - B) Traffic Splitting
    - C) Service Discovery
    - D) User Authentication

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) User Authentication</p>
    <p><strong>Explanation</strong>: Cilium Service Mesh provides mutual TLS, traffic splitting, and service discovery, but user authentication is typically handled by a separate authentication system.</p>
    </details>

12. **What functionality does Cilium's Envoy integration provide?**
    - A) L7 load balancing
    - B) L7 visibility
    - C) L7 policy enforcement
    - D) All of the above

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) All of the above</p>
    <p><strong>Explanation</strong>: Cilium integrates with the Envoy proxy to provide L7 load balancing, visibility, and policy enforcement.</p>
    </details>

## Security and Visibility

13. **Which feature is NOT provided by Hubble UI?**
    - A) Service dependency map
    - B) Network flow visualization
    - C) Policy violation alerts
    - D) Code deployment management

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Code deployment management</p>
    <p><strong>Explanation</strong>: Hubble UI provides service dependency maps, network flow visualization, and policy violation alerts, but does not provide code deployment management.</p>
    </details>

14. **Which protocols can be used for network traffic encryption in Cilium?**
    - A) IPsec and WireGuard
    - B) TLS and SSH
    - C) SSL and HTTPS
    - D) DTLS and QUIC

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) IPsec and WireGuard</p>
    <p><strong>Explanation</strong>: Cilium can encrypt inter-node network traffic using IPsec and WireGuard protocols.</p>
    </details>

15. **Which Cilium security feature matches this description? "Filters traffic based on specific fields or patterns of specific application layer protocols"**
    - A) Network policies
    - B) L7 policies
    - C) Encryption
    - D) Intrusion detection

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) L7 policies</p>
    <p><strong>Explanation</strong>: L7 (application layer) policies can filter traffic based on specific fields or patterns in protocols such as HTTP, gRPC, and Kafka.</p>
    </details>

## Advanced Topics and Real-World Use Cases

16. **Which is NOT a main feature of Cilium Cluster Mesh?**
    - A) Cross-cluster service discovery
    - B) Cross-cluster network policies
    - C) Cross-cluster load balancing
    - D) Cross-cluster storage sharing

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Cross-cluster storage sharing</p>
    <p><strong>Explanation</strong>: Cilium Cluster Mesh provides cross-cluster service discovery, network policies, and load balancing, but does not provide storage sharing.</p>
    </details>

17. **What does Cilium's Bandwidth Manager feature provide?**
    - A) Network bandwidth monitoring
    - B) Network bandwidth limiting and QoS
    - C) Network bandwidth optimization
    - D) Network bandwidth prediction

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Network bandwidth limiting and QoS</p>
    <p><strong>Explanation</strong>: Cilium's Bandwidth Manager uses eBPF to provide per-Pod network bandwidth limiting and QoS (Quality of Service).</p>
    </details>

18. **What does Cilium's Host Firewall feature protect?**
    - A) Container-to-container communication only
    - B) Node-to-node communication only
    - C) The host's own network interfaces
    - D) External cloud services

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) The host's own network interfaces</p>
    <p><strong>Explanation</strong>: Cilium's Host Firewall protects the host's own network interfaces, enhancing host-level security.</p>
    </details>

19. **What is the main purpose of Cilium's Egress Gateway feature?**
    - A) Preserving the source IP address of external traffic
    - B) Changing the destination IP address of external traffic
    - C) Encrypting external traffic
    - D) Blocking external traffic

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) Preserving the source IP address of external traffic</p>
    <p><strong>Explanation</strong>: Cilium's Egress Gateway SNATs outbound traffic from Pods to outside the cluster to a specific IP, providing a consistent source IP.</p>
    </details>

20. **What is NOT possible through Cilium's BGP support?**
    - A) Route exchange with external routers
    - B) Advertising external IPs for LoadBalancer services
    - C) Direct routing between clusters
    - D) Automatic DNS record creation

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Automatic DNS record creation</p>
    <p><strong>Explanation</strong>: Cilium's BGP support provides route exchange with external routers, advertising external IPs for LoadBalancer services, and direct routing between clusters, but does not provide automatic DNS record creation.</p>
    </details>

## Performance and Troubleshooting

21. **Which Cilium performance optimization technology significantly reduces packet processing latency?**
    - A) TCP BBR
    - B) XDP (eXpress Data Path)
    - C) DPDK
    - D) TSO (TCP Segmentation Offload)

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) XDP (eXpress Data Path)</p>
    <p><strong>Explanation</strong>: XDP processes packets at the network driver level, bypassing the kernel networking stack to significantly reduce latency.</p>
    </details>

22. **What is the command to diagnose network connectivity issues in Cilium?**
    - A) `cilium status`
    - B) `cilium connectivity test`
    - C) `cilium monitor`
    - D) `cilium endpoint list`

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) `cilium connectivity test`</p>
    <p><strong>Explanation</strong>: The `cilium connectivity test` command tests various network connectivity scenarios within the cluster to diagnose issues.</p>
    </details>

23. **What is the command to check the network policy status of a specific Pod in Cilium?**
    - A) `cilium endpoint list`
    - B) `cilium policy get`
    - C) `cilium endpoint get <endpoint-id>`
    - D) `cilium status --all-endpoints`

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) `cilium endpoint get <endpoint-id>`</p>
    <p><strong>Explanation</strong>: The `cilium endpoint get <endpoint-id>` command shows detailed information and applied network policy status for a specific endpoint (Pod).</p>
    </details>

24. **What is the command to check BPF map status in Cilium?**
    - A) `cilium map list`
    - B) `cilium bpf maps`
    - C) `cilium status --maps`
    - D) `cilium bpf map list`

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) `cilium bpf maps`</p>
    <p><strong>Explanation</strong>: The `cilium bpf maps` command shows a list and status of all BPF maps used by Cilium.</p>
    </details>

25. **What is the command for network packet capture and analysis in Cilium?**
    - A) `cilium tcpdump`
    - B) `cilium capture`
    - C) `cilium monitor`
    - D) `cilium packet-capture`

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) `cilium monitor`</p>
    <p><strong>Explanation</strong>: The `cilium monitor` command can capture and analyze packets passing through Cilium's eBPF data path in real-time.</p>
    </details>
