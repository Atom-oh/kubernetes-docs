# Cilium Advanced Quiz

> **Review baseline**: Cilium 1.20.1; Cilium CLI 0.20.0; Hubble CLI 1.19.4.
> **Last reviewed**: September 12, 2026.

[Return to the guide](../../../networking/cilium/07-advanced-topics.md)

## eBPF Technology

1. **Where do the Linux eBPF datapath programs discussed in this course execute?**

   - A) Only in a browser
   - B) At supported hooks in the Linux kernel
   - C) Only inside Envoy
   - D) In the Kubernetes API server

   <details>
   <summary>Show Answer</summary>

   **Answer: B) At supported hooks in the Linux kernel**

   Cilium attaches eBPF programs to kernel hooks. Userspace components load and manage them.

   </details>

2. **Which mechanism checks an eBPF program before the kernel accepts it?**

   - A) Encryption
   - B) Container scheduling
   - C) The verifier
   - D) DNS

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The verifier**

   The verifier checks properties such as memory access and bounded execution. It is not an absolute guarantee against implementation vulnerabilities or every kernel failure.

   </details>

3. **Which is not a general requirement for Cilium's software eBPF datapath?**

   - A) Supported kernel features
   - B) Appropriate privileges
   - C) Compatible networking configuration
   - D) Dedicated hardware offload

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Dedicated hardware offload**

   Hardware offload is not mandatory. Performance depends on the actual path, workload, kernel and hardware.

   </details>

## Networking Models

4. **Which is not one of the Cilium native/tunnel choices described in this course?**

   - A) VXLAN
   - B) Geneve
   - C) Native routing
   - D) An MPLS datapath mode

   <details>
   <summary>Show Answer</summary>

   **Answer: D) An MPLS datapath mode**

   This describes Cilium's configuration choices, not a ban on using an MPLS-based external underlay.

   </details>

5. **What implements Cilium kube-proxy replacement?**

   - A) Only iptables chains
   - B) Only IPVS rules
   - C) eBPF service handling, with optional XDP acceleration
   - D) A mandatory external hardware switch

   <details>
   <summary>Show Answer</summary>

   **Answer: C) eBPF service handling, with optional XDP acceleration**

   Socket and packet-path eBPF implement service handling. XDP accelerates qualifying external forwarding paths; it is not required for every Service.

   </details>

6. **Which Cilium observability component exposes Kubernetes-aware flow records?**

   - A) Helm
   - B) Hubble
   - C) kube-scheduler
   - D) etcdctl

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Hubble**

   Hubble exposes bounded observations, not a lossless capture of every packet. Other packet-analysis tools have different roles.

   </details>

## IPAM and Network Policies

7. **Which Cilium IPAM mode uses EC2 ENIs to allocate VPC addresses?**

   - A) Cluster pool
   - B) Kubernetes host scope
   - C) ENI
   - D) Generic CRD-backed

   <details>
   <summary>Show Answer</summary>

   **Answer: C) ENI**

   ENI mode uses AWS network interfaces/address allocation. This does not mean every EKS compute mode supports an alternate CNI; check the platform prerequisites.

   </details>

8. **What does toFQDNs use to allow outbound connections?**

   - A) A verified JWT
   - B) A fixed Service port only
   - C) Destination IPs learned for matching DNS names
   - D) Automatic TLS decryption

   <details>
   <summary>Show Answer</summary>

   **Answer: C) Destination IPs learned for matching DNS names**

   DNS query allowance/proxy observation and subsequent IP connectivity are distinct. The rule does not authenticate the remote application.

   </details>

9. **Which selector is used for node host policy in a CiliumClusterwideNetworkPolicy?**

   - A) endpointSelector for all nodes
   - B) nodeSelector
   - C) A top-level serviceSelector
   - D) A top-level namespaceSelector

   <details>
   <summary>Show Answer</summary>

   **Answer: B) nodeSelector**

   nodeSelector is a clusterwide host-policy field. Do not describe all Kubernetes selector forms as interchangeable top-level CiliumNetworkPolicy fields.

   </details>

## L2–L7 Networking

10. **Which is not a request match field in Cilium HTTP policy?**

   - A) Path
   - B) Method
   - C) Headers
   - D) Response latency

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Response latency**

   HTTP rules inspect supported request fields when HTTP is visible. Measuring latency does not create a latency-based allow-rule field.

   </details>

11. **What does an identity-based network policy alone not provide?**

   - A) Endpoint selection
   - B) Network access restrictions
   - C) Direction-specific rules
   - D) End-user token authentication

   <details>
   <summary>Show Answer</summary>

   **Answer: D) End-user token authentication**

   User authentication requires appropriate application/gateway logic. SPIRE mutual authentication and Beta ztunnel workload mTLS are separately configured features with their own limits.

   </details>

12. **What can Cilium's Envoy integration provide when configured on the appropriate path?**

   - A) HTTP load balancing
   - B) HTTP visibility
   - C) HTTP policy enforcement
   - D) All of the above

   <details>
   <summary>Show Answer</summary>

   **Answer: D) All of the above**

   These capabilities depend on the selected proxy path and configuration; enabling an unrelated network feature does not activate every L7 capability.

   </details>

## Security and Visibility

13. **Which is a Hubble UI feature?**

   - A) Automatic Slack incident creation
   - B) Service dependency maps and flow exploration
   - C) Source-code deployment management
   - D) JWT signing-key rotation

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Service dependency maps and flow exploration**

   Notifications and automated responses need separate integrations. The UI visualizes the observed network flows.

   </details>

14. **Which are alternative Cilium node transport encryption modes?**

   - A) IPsec and WireGuard
   - B) HTTP and DNS
   - C) Relay and Prometheus
   - D) TCP and UDP

   <details>
   <summary>Show Answer</summary>

   **Answer: A) IPsec and WireGuard**

   Their coverage and prerequisites must be checked. Same-node traffic is not encrypted by node tunnels, and workload mTLS is a distinct feature.

   </details>

15. **Which policy layer matches HTTP methods and paths?**

   - A) L2 address matching only
   - B) L7 policy
   - C) L3 CIDR matching only
   - D) Transport encryption

   <details>
   <summary>Show Answer</summary>

   **Answer: B) L7 policy**

   Current Cilium HTTP policy can inspect these fields; Kafka topic rules were removed. Header matching is not token authentication.

   </details>

## Advanced Topics and Use Cases

16. **Which is not a ClusterMesh capability?**

   - A) Cross-cluster service discovery
   - B) Policy use of remote endpoint identities
   - C) Cross-cluster service load balancing
   - D) Shared persistent storage

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Shared persistent storage**

   ClusterMesh handles network metadata/connectivity. It does not supply shared storage or automatically replicate every policy resource.

   </details>

17. **Which description of Bandwidth Manager is correct?**

   - A) It only graphs bandwidth
   - B) It enforces configured per-Pod bandwidth limits
   - C) It guarantees each Pod a physical-link reservation
   - D) It predicts future traffic with machine learning

   <details>
   <summary>Show Answer</summary>

   **Answer: B) It enforces configured per-Pod bandwidth limits**

   Egress uses EDT and ingress uses an eBPF token bucket. Limits are per Pod, with documented egress-L7 and kind limitations; they are not guaranteed capacity reservations.

   </details>

18. **What is the scope of Cilium Host Firewall?**

   - A) Only container-to-container HTTP
   - B) Only storage encryption
   - C) The host's network traffic
   - D) External SaaS authorization

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The host's network traffic**

   Host firewall is network policy for the node/host, not a general runtime syscall-control system.

   </details>

19. **What does Egress Gateway do to matching outbound traffic?**

   - A) SNAT to a selected, predictable gateway IP
   - B) Always preserve the original Pod source IP
   - C) Automatically encrypt every external connection
   - D) Create a public IP in every cloud without prerequisites

   <details>
   <summary>Show Answer</summary>

   **Answer: A) SNAT to a selected, predictable gateway IP**

   Gateway IPs/interfaces/routing must be provisioned. New Pods can send traffic before policy enforcement; ClusterMesh and CiliumEndpointSlice incompatibilities also apply.

   </details>

20. **Which action is performed by Cilium BGP Control Plane?**

   - A) Installing every learned route into the local Linux datapath
   - B) Advertising selected Pod or Service prefixes to peers
   - C) Creating DNS records for all Services
   - D) Allocating external router interfaces

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Advertising selected Pod or Service prefixes to peers**

   BGP advertisement is separate from local datapath routing, address allocation and DNS. Verify the external router and the actual forward/return path.

   </details>

## Performance and Troubleshooting

21. **Which mechanism can handle supported external service forwarding at the native driver hook?**

   - A) A Grafana dashboard
   - B) XDP acceleration
   - C) A DNS search suffix
   - D) A larger application log file

   <details>
   <summary>Show Answer</summary>

   **Answer: B) XDP acceleration**

   XDP requires a supported NIC/driver and path. A fixed latency or throughput improvement cannot be assumed for arbitrary workloads.

   </details>

22. **Which standalone Cilium CLI command actively creates workloads to test connectivity scenarios?**

   - A) `cilium status`
   - B) `cilium connectivity test`
   - C) `hubble status`
   - D) `kubectl get nodes`

   <details>
   <summary>Show Answer</summary>

   **Answer: B) `cilium connectivity test`**

   It is an active test with resource creation and traffic, not a read-only status query. Use an isolated test scope and review cleanup.

   </details>

23. **Inside the owning Cilium agent, which command inspects one endpoint's details?**

   - A) `cilium endpoint list`
   - B) `cilium policy get`
   - C) `cilium-dbg endpoint get ENDPOINT_ID`
   - D) `cilium status --all-endpoints`

   <details>
   <summary>Show Answer</summary>

   **Answer: C) `cilium-dbg endpoint get ENDPOINT_ID`**

   Get the node-local endpoint ID from that agent's list. An ID from another agent need not identify the same workload.

   </details>

24. **Which agent-local command lists open BPF maps known to the map manager?**

   - A) `cilium-dbg map list`
   - B) `cilium bpf maps`
   - C) `cilium status --maps`
   - D) `cilium bpf map list`

   <details>
   <summary>Show Answer</summary>

   **Answer: A) `cilium-dbg map list`**

   This is not an inventory of every BPF map in the kernel. The earlier cilium bpf maps answer was not a valid command.

   </details>

25. **Which command displays local events emitted by Cilium BPF programs?**

   - A) `cilium tcpdump`
   - B) `cilium capture`
   - C) `cilium-dbg monitor`
   - D) `cilium packet-capture`

   <details>
   <summary>Show Answer</summary>

   **Answer: C) `cilium-dbg monitor`**

   It displays supported event/trace types. Aggregation, suppression and buffers affect visibility; it is not a guaranteed capture of every packet.

   </details>
