# Network Fundamentals Part 4 — A Request's Journey and the Cloud Mapping

> **Last Updated**: September 11, 2026

::: tip This is a four-part series
[Part 1: The Layer Model, Link and Routing Layers](./06-network-fundamentals-part1.md) ·
[Part 2: The Transport Layer and TLS](./06-network-fundamentals-part2.md) ·
[Part 3: Application Protocols](./06-network-fundamentals-part3.md) ·
**Part 4: A Request's Journey and the Cloud** *(this document)*
:::

This part connects the series’ 25 protocols and mechanisms through an illustrative request, then maps related responsibilities in AWS and Kubernetes. These are functional comparisons, not one-to-one replacements.

![Illustrative request path: address configuration and DNS, local delivery and routing, optional NAT, then TCP plus TLS for HTTP/1.1 or HTTP/2, or QUIC with integrated TLS for HTTP/3. Cache reuse and network configuration can skip steps.](../.gitbook/assets/en-basics-06-network-fundamentals-part4-0.png)

[🔍 View interactive diagram](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part4-0.html)

---

## 6. Following One Request All the Way Through

For a new connection to `https://example.com`, the following is a conceptual dependency guide. It is not a packet trace: DNS queries and handshake packets themselves use the link and routing layers, and cached state or an existing connection can skip work.

1. **Address configuration** — the host already has addresses, routes and resolver settings, from DHCP, static configuration, IPv6 SLAAC/Router Advertisements or another managed mechanism.
2. **DNS (or DoH)** — resolve the destination when needed. A recursive resolver can use its cache, follow delegations or forward queries; the application need not contact the root. HTTPS records may also advertise connection parameters.
3. **Neighbor resolution** — for IPv4 over Ethernet, resolve the selected next hop’s MAC with ARP if it is not cached; IPv6 uses Neighbor Discovery. The next hop can be a local destination or a router.
4. **Ethernet / Wi-Fi** — send frames to that next hop. A default gateway is used only when the selected route calls for it.
5. **IP routing** — routers forward using their forwarding tables. Routes may be static, connected or learned through BGP, OSPF or another control plane; routing protocols do not run a fresh negotiation for every request.
6. **Optional NAT** — an IPv4 internet egress path may translate a private address to a public address. Many internal and IPv6 paths do not use NAT; private-to-private NAT also exists.
7. **TCP or QUIC** — establish or reuse transport. HTTP/1.1 and HTTP/2 commonly use TCP; HTTP/3 uses QUIC over UDP.
8. **TLS** — authenticate the peer and establish traffic keys according to the handshake mode. For QUIC, TLS 1.3 is integrated with step 7; resumption differs from a fresh certificate-based handshake.
9. **HTTP** — exchange the request and response using the negotiated version. HTTP/3 requires the QUIC branch; it does not run over the TCP branch.
10. **Optional application features** — WebSocket, browser-compatible gRPC or WebRTC may create additional connections or reuse/multiplex existing transports, depending on implementation.

**ICMP** can report certain IP-layer errors, such as an unreachable destination or a packet too large for a path. It does not report every failure: packets or ICMP errors can be filtered, and TLS/application failures use their own mechanisms. Combine allowed, relevant ICMP with transport/application logs and measurements; absence of an ICMP error is not proof of success.

---

## 7. Where These Concepts Go in the Cloud

Cloud networking retains addressing, routing, filtering and transport responsibilities, but the boundaries differ from traditional appliances. In AWS:

| Traditional concept | AWS counterpart |
|---|---|
| Segmentation and filtering | VPC/subnets for logical network boundaries; security groups and NACLs for filtering, not VLAN equivalents |
| Routing tables | VPC route tables, Transit Gateway |
| BGP peering | Direct Connect virtual interfaces; dynamically routed Site-to-Site VPN (static VPN routing is also possible) |
| NAT / private service access | NAT Gateway translates addresses; VPC endpoints provide private paths to supported services |
| DNS servers | Route 53, Resolver endpoints |
| DHCP | VPC DHCP option sets |
| TLS termination / certificates | ALB HTTPS listeners, NLB TLS listeners or CloudFront; ACM manages supported certificates rather than forwarding traffic |
| L7 load balancing | ALB; application proxies such as Istio/Envoy in a separately managed service mesh |
| SSH access | Systems Manager Session Manager |
| Internal-segment encryption | TLS/mTLS in applications or proxies; network-layer encryption is a separate design option |

AWS App Mesh is a historical example, not a new-design default: AWS has announced support ends on **September 30, 2026**. Plan migration for existing deployments.

**Three decisions to make first** when designing:

1. **IP address plan** — plan CIDRs for networks that must interconnect, including on-premises, Pod and Service ranges. Overlap can require translation or redesign; renumbering has operational cost, but no universal cost ranking applies.
2. **Outbound path** — match each destination to an internet or private-service path. Compare NAT hourly/data charges, interface-endpoint hourly/data charges, cross-AZ transfer and availability requirements. S3/DynamoDB gateway endpoints have no additional endpoint charge, but endpoints do not replace every internet destination.
3. **Encryption termination point** — document encryption and authentication on each hop, including the backend connection after a load balancer. Check the workload’s requirements and applicable policy; TLS termination alone does not secure the next hop.

---

## 8. Who Does This Work in Kubernetes

Inside a cluster the same concepts repeat with new component names. This table is the bridge from this series to the deep-dive documents that follow.

| Traditional concept | Kubernetes counterpart |
|---|---|
| Pod IP assignment | CNI/IPAM integration (VPC CNI, Cilium, …); this does not necessarily use DHCP per Pod |
| Local delivery / forwarding | Host interfaces, neighbor handling and CNI datapath; implementation may use veth, routes, tunnels or eBPF |
| DNS | Cluster DNS, often CoreDNS; `service.namespace.svc.<cluster-domain>` (`cluster.local` is a common configured domain) |
| Service virtual IP / L4 balancing | kube-proxy on Linux: iptables or nftables; IPVS is deprecated since 1.35. An eBPF implementation can replace kube-proxy; it is not a kube-proxy mode |
| Pod traffic policy | NetworkPolicy, enforced only by a networking controller/plugin that supports it |
| L7 routing / TLS termination | Ingress/Gateway API resources plus an implementing controller and dataplane |
| Service-to-service mTLS | Application TLS or a configured mesh such as Istio/Linkerd; not enabled merely by installing any CNI |
| BGP routing / advertisement | For example, Calico BGP routes or MetalLB BGP advertisement of Service addresses; roles differ |

For an ordinary ClusterIP Service backed by Pods, cluster DNS usually resolves the Service IP, then kube-proxy or its replacement selects an eligible endpoint using Service/EndpointSlice state. The datapath forwards to that endpoint on the same or another node. Headless Services instead expose endpoint addresses through DNS, and ExternalName Services return a CNAME. mTLS applies only when the relevant peers and policies are configured. These variations are why “every layer always runs” is not a valid packet-flow assumption.

---

## Wrapping Up

After walking through these 25 protocols and mechanisms, examine the trade-offs and the scope of each guarantee.

TCP supplies ordered, reliable delivery with recovery and ordering costs. UDP leaves these functions to higher layers. QUIC supplies reliable streams and integrated security over UDP. NAT conserves public IPv4 addresses while complicating unsolicited reachability, which ICE/STUN/TURN help address. DoH protects a resolver hop; organizational visibility depends on the resolver and endpoint policy.

When investigating a failure, use each layer’s actual guarantees and observable evidence to narrow the fault domain. A plausible protocol-level explanation is a hypothesis until logs, traces or measurements distinguish it from alternatives.

---

## Next Documents

From this foundation, move on to cluster networking:

- [eBPF Fundamentals](./05-ebpf-fundamentals.md) — how packets are processed in the kernel
- [Cilium Networking](../networking/cilium/03-networking.md) — the eBPF-based CNI
- [Calico BGP Deep Dive](../networking/calico/04-bgp-deep-dive.md) — BGP routing inside the cluster
- [Amazon VPC CNI](../networking/01-vpc-cni.md) — the VPC CNI and IP allocation

## References

The protocol list was seeded by ByteByteGo's "What Keeps the Internet Running?"
infographic; the explanations and practical commentary were written independently.

Primary references: [Kubernetes Service proxy modes](https://kubernetes.io/docs/reference/networking/virtual-ips/), [Service DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/), [NAT Gateway cost guidance](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html), [ECR VPC endpoints](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html), [App Mesh lifecycle](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html).
