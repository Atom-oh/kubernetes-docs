# Calico Glossary

> **Reviewed baseline**: Calico 3.32.2; comparison terminology checked against Cilium 1.20.1.
> **Last Updated**: September 12, 2026

This document provides definitions of key terms and concepts related to Calico networking and security. Understanding these terms is essential for effectively deploying and operating Calico in Kubernetes environments.

## Term Categories

Terms are organized into the following categories:
- **Networking Terms** - General networking concepts
- **Calico Components** - Calico-specific components and services
- **Policy Terms** - Network policy and security concepts
- **Operations Terms** - Operational and management concepts

---

## Networking Terms

### A

**AS (Autonomous System)**
- A collection of IP networks and routers under the control of a single organization that presents a common routing policy to the Internet. In Calico, AS numbers are used for BGP peering configuration.

**ASN (Autonomous System Number)**
- An identifier used by BGP. RFC 6996 reserves private-use ranges **64512–65534** and **4200000000–4294967294**. Private ASNs are reusable within administrative domains and must not be treated as globally unique public assignments.

### B

**BGP (Border Gateway Protocol)**
- A routing protocol used both between autonomous systems (eBGP) and within one AS (iBGP). Calico can use BGP to distribute Pod/Service routes; it is not required by every Calico dataplane or overlay profile.

**Block Affinity**
- An association between an IPAM block and its owner, commonly a node. Without strict affinity, eligible allocations can borrow from another node’s block. Affinity does not guarantee that every local Pod address comes from a locally owned block; inspect the resource type/state and actual allocator.

### C

**CIDR (Classless Inter-Domain Routing)**
- A method for allocating IP addresses and IP routing. Example: 10.244.0.0/16 represents a range of 65,536 IP addresses.

**CNI (Container Network Interface)**
- A specification for configuring container network connectivity and associated plugins. Calico provides CNI implementations; behavior differs between Linux networking and supported Windows HNS configurations.

**Conntrack (Connection Tracking)**
- State used to track flows for stateful policy/NAT. The standard Linux dataplane uses kernel connection tracking, while Calico’s BPF dataplane also maintains BPF conntrack maps; they are not interchangeable tuning targets.

### D

**DNAT (Destination NAT)**
- Network address translation that modifies the destination IP address of packets. Used in Kubernetes for Service load balancing.

**Direct Routing**
- A networking mode where traffic between pods on different nodes is routed directly without encapsulation. Requires underlying network to support pod CIDR routing.

**DSR (Direct Server Return)**
- A Service load-balancing mode where the backend returns traffic without traversing the original forwarding node. Calico BPF supports it under specific network/source-address constraints; it is not universally compatible with cloud load balancers.

### E

**eBPF (extended Berkeley Packet Filter)**
- Linux kernel programmability used by Calico’s BPF dataplane for networking, policy and Service handling. Compatibility and performance depend on the kernel, platform and workload; it is not a guarantee of lower overhead for every deployment.

**Encapsulation**
- The process of wrapping network packets inside other packets. Calico supports IPIP and VXLAN encapsulation for overlay networking.

### F

**FQDN (Fully Qualified Domain Name)**
- A complete DNS name. The documented Calico domain-based egress policy feature requires a commercial edition; OSS NetworkSet CIDR entries do not become DNS rules. Do not confuse this with separately integrated HTTP application-layer policy.

**Full Mesh**
- A BGP topology in which each of N participating nodes peers with every other node: N(N−1)/2 sessions. Capacity depends on churn, routes and hardware; 100 nodes is not a universal protocol limit.

### I

**IPAM (IP Address Management)**
- The system responsible for allocating, tracking, and managing IP addresses. Calico includes a built-in IPAM system with block-based allocation.

**IPIP (IP-in-IP)**
- IP encapsulation. Calico’s IPv4 IP-in-IP mode adds a 20-byte outer IPv4 header and requires an underlay that permits IP protocol 4; it is not a UDP port.

**IPset**
- A Linux kernel feature for storing sets of IP addresses, networks, or ports. Calico uses ipsets to efficiently match traffic against multiple addresses.

**iptables**
- A userspace interface to Linux Netfilter packet-filtering/NAT rules. The iptables legacy and nft backends differ from Calico’s separate native Nftables dataplane; changing the iptables backend does not select that dataplane.

### M

**MTU (Maximum Transmission Unit)**
- The maximum packet size for a link/path. With a 1500-byte effective underlay, example Calico MTUs are 1480 for IPv4 IPIP, 1450/1430 for IPv4/IPv6 VXLAN and 1440/1420 for IPv4/IPv6 WireGuard. Use the actual minimum path MTU and chosen mode, including platform-specific restrictions; these are calculations, not measured performance.

### N

**NAT (Network Address Translation)**
- The process of modifying IP address information in packet headers. Calico uses NAT for pod egress and Service implementation.

**nftables**
- The Linux packet-filtering framework used by Calico’s native Nftables mode. This is a distinct Installation dataplane choice from Iptables with its NFT backend.

### O

**Overlay Network**
- A virtual network built on top of an existing physical network. Calico supports IPIP and VXLAN overlay modes for environments where direct routing isn't possible.

### R

**Route Reflector**
- A BGP speaker that reflects routes to clients. With N total nodes including r fully-meshed reflectors and each client peering with all r, the topology has r(N−r)+r(r−1)/2 sessions. N=100/r=2 gives 197 rather than 4950 full-mesh sessions; one reflector gives 99 sessions without reflector redundancy.

**Routing Table**
- A data structure that stores routes to network destinations. Calico programs routes for pod CIDRs into the Linux kernel routing table.

### S

**SNAT (Source NAT)**
- Network address translation that modifies the source IP address of packets. Used for pod egress traffic and masquerading.

### V

**veth (Virtual Ethernet)**
- A paired Linux virtual interface commonly created by the CNI plugin to connect a Pod network namespace to the host. It is not created by Felix for every Pod; hostNetwork Pods, Windows and other network attachment types differ.

**VXLAN (Virtual Extensible LAN)**
- An encapsulation protocol that extends Layer 2 networks over Layer 3 infrastructure. Provides better cloud compatibility than IPIP but with higher overhead.

### W

**WireGuard**
- An encrypted tunnel protocol used by Calico for supported traffic between configured, capable node peers. It does not automatically encrypt same-node, unsupported-peer or all external traffic, and it is distinct from application mTLS.

**Workload Endpoint**
- A namespaced Calico representation of a workload interface, with addresses, labels and profile references used in policy calculation. It is normally orchestrator/plugin-managed and is not a stored list of every effective policy decision.

---

## Calico Components

### B

**BIRD (BIRD Internet Routing Daemon)**
- The routing daemon in Calico profiles that use BGP. The Calico 3.32.2 release uses its patched BIRD 1.6.8 lineage; an arbitrary upstream BIRD 2 configuration is not equivalent.

### C

**calicoctl**
- The command-line tool for managing Calico resources. Used for viewing status, configuring policies, managing IPAM, and troubleshooting.

**Calico API Server**
- Calico API integration, distinct from the Kubernetes API server and available in OSS. The user-facing projectcalico.org/v3 API and backing CRDs/native-API mode depend on the configured installation; follow the maintained installation guide rather than treating all API groups as aliases.

**CNI Plugin**
- The binary that implements the CNI specification for Calico. Responsible for setting up pod networking (veth pairs, routes, IP assignment).

**confd**
- A configuration management tool that generates BIRD configuration files from the Calico datastore. Watches for changes and updates BIRD dynamically.

### D

**Dikastes**
- An application-layer policy decision component used with Istio/Envoy. Envoy handles the traffic and requests authorization from Dikastes; Dikastes is not itself the forwarding proxy. This integration is documented for Calico OSS, with version-specific prerequisites.

### F

**Felix**
- The per-node agent that programs the selected dataplane, policy and relevant routes. The CNI plugin sets up Pod interfaces/IPAM; Felix is not the per-packet userspace forwarding path.

### G

**Goldmane / Whisker**
- The OSS flow aggregation API and web UI respectively. Their deployment, access controls and preview status are separate from basic Felix metrics.

### K

**kube-controllers**
- Controllers for Kubernetes/Calico reconciliation, including node/IPAM work and datastore-dependent synchronization. The enabled controller set differs by installation/datastore; listing controller types does not mean all run in every Kubernetes-datastore deployment.

### T

**Tigera Operator**
- A Kubernetes operator that manages Calico installation and lifecycle. Provides declarative configuration through CRDs.

**Typha**
- A datastore-update fan-out and cache service that reduces per-Felix watch load. It can use multiple watches/syncer types and replicas; it is not one universal cluster-wide watch or an automatic policy-federation service. Operator scaling is described in the advanced chapter.

---

## Policy Terms

### A

**Action**
- A Calico rule result: Allow and Deny terminate policy evaluation for that path; Log continues; Pass delegates to the next applicable tier and eventually profiles. Log is not itself an allow decision.

**applyOnForward**
- A GlobalNetworkPolicy option for forwarded traffic through host endpoints. It does not create host endpoints and is required with preDNAT/doNotTrack policies. Workload policy and host-forwarding policy have different scopes.

### D

**Default Deny**
- A posture that denies traffic in a selected scope unless the effective policy set permits it. Introduce it with explicit dependencies and tested namespace scope, not an unqualified empty cluster-wide policy.

**DoNotTrack**
- The doNotTrack GlobalNetworkPolicy setting applies before connection tracking to host endpoint traffic and requires applyOnForward. Stateless return paths need explicit rules; it cannot be combined with preDNAT.

### E

**Egress**
- Outbound network traffic from a pod. Egress policies control what destinations a pod can communicate with.

### G

**GlobalNetworkPolicy**
- A cluster-scoped Calico policy that can select workloads across namespaces or host endpoints. Its selectors determine the actual scope; cluster-scoped does not mean it automatically affects every Pod.

**GlobalNetworkSet**
- A cluster-scoped labeled collection of IP addresses/CIDRs. Policy selectors can match it, including from namespaced Calico policies with the appropriate global namespace selection. It is not restricted to GlobalNetworkPolicy references.

### H

**Host Endpoint**
- A representation of a host interface used for host policy and, when configured, forwarded-traffic policy. Creating one can change traffic handling; review policies, profiles, failsafes and management access first.

### I

**Ingress**
- Inbound network traffic to a pod. Ingress policies control what sources can communicate with a pod.

### N

**NetworkPolicy**
- Two distinct APIs: Kubernetes networking.k8s.io/v1 NetworkPolicy and Calico projectcalico.org/v3 NetworkPolicy. Calico adds actions/order/tiers and selectors; HTTP rules require a separate supported application-layer integration, including OSS Dikastes, while domain-based rules have edition constraints.

**NetworkSet**
- A namespace-scoped set of IP addresses or CIDRs. Provides a way to group external endpoints for use in network policies.

### O

**Order**
- A numeric evaluation priority: lower tier order first, then policy order within that tier. Use explicit distinct priorities when ordering matters rather than relying on ties; an earlier terminal action can make later policies irrelevant.

### P

**Pass**
- Skip the remaining policies in the current tier and continue at the next applicable tier; after the last applicable tier, evaluate endpoint profiles. It is not a final allow.

**Profile**
- Shared labels inherited by endpoints. Profiles can contain legacy policy rules, but that use is deprecated in favor of NetworkPolicy/GlobalNetworkPolicy; do not treat profiles as Kubernetes RBAC.

**Policy Selector**
- A label-based expression that determines which endpoints a policy applies to. Uses Calico's selector syntax (e.g., `app == 'web'`).

**PreDNAT**
- The preDNAT GlobalNetworkPolicy setting evaluates ingress host endpoint traffic before destination NAT. It requires applyOnForward and cannot be combined with doNotTrack or an egress policy direction.

### S

**Staged Policy**
- A non-enforcing policy resource used to assess proposed changes. Staged policies are available in OSS with the documented resource/observability prerequisites; creating one does not by itself guarantee a complete decision log.

**Selector**
- An expression that matches resources based on labels. Calico uses selectors for both policy targets and source/destination matching.

### T

**Tier**
- An ordered group of policies. Lower numeric order has precedence. Allow/Deny is terminal, Pass delegates, and a selected tier with no matching rule uses its defaultAction, normally Deny.

---

## Operations Terms

### A

**APIServer (Calico)**
- The operator resource configuring Calico API integration. It is not the Kubernetes control plane and is not an Enterprise-only feature; API access still requires the correct configured API path and RBAC.

### B

**Block**
- An allocation unit in Calico IPAM. Default sizes are IPv4 /26 and IPv6 /122, each containing 64 addresses. Reservations and allocation constraints can reduce usable workload capacity, notably on Windows.

**Block Affinity**
- An association between an IPAM block and its owner, commonly a node. Without strict affinity, eligible allocations can borrow from another node’s block. Affinity does not guarantee that every local Pod address comes from a locally owned block; inspect the resource type/state and actual allocator.

### D

**Dataplane**
- The packet-processing implementation. Calico provides Linux Iptables, Nftables and BPF choices, and supported Windows HNS configurations; other integrations have their own requirements.

**Datastore**
- Storage/API access for Calico configuration and state, using the Kubernetes API datastore or supported direct etcdv3 deployments. Kubernetes datastore is recommended; features such as BPF have additional datastore constraints.

### F

**FelixConfiguration**
- The API resource for Felix settings, including cluster defaults and supported per-node overrides. It controls metrics/logging/dataplane options; it is not a substitute for the operator Installation API.

**Flow Logs**
- Aggregated connection-flow records, distinct from packet captures or process logs. Current OSS operator/Helm installations can use Goldmane and Whisker; the flow-log guide marks the feature tech preview.

### H

**Health Check**
- Component liveness/readiness reporting. Felix can expose health endpoints on its configured port (default 9099); component health does not prove correct application reachability or policy enforcement.

### I

**IPPool**
- A separate Calico resource defining an address range, encapsulation/NAT and allocation eligibility. Calico IPAM can allocate for supported Workload/Tunnel/LoadBalancer uses; the pool is not an alias of a Kubernetes Node PodCIDR. CIDR and blockSize are immutable.

**Installation**
- The Tigera Operator CRD that defines Calico deployment configuration. Specifies networking mode, resources, and component settings.

### M

**Metrics**
- Prometheus statistics with component-specific activation and ports. Felix defaults to 9091; Typha defaults to 9091 but is commonly explicitly configured to 9093; kube-controllers defaults to 9094. Read the actual settings and metric types.

### P

**Pod CIDR**
- A Pod address range, which may describe the cluster range or a Kubernetes Node assignment. A Calico IPPool is a separate object; its relationship to Node PodCIDRs depends on IPAM. With VPC CNI, Calico policy-only does not allocate Pod IPs.

### R

**Rollout**
- A controlled component update. Operator reconciliation and rolling update settings help manage availability but do not guarantee uninterrupted traffic or reversible schema/data changes.

### T

**TigeraStatus**
- A CRD that reports the status of Calico components. Shows deployment health and configuration state.

---

## Calico vs Kubernetes Terminology

| Kubernetes Term | Calico Equivalent | Notes |
|-----------------|-------------------|-------|
| NetworkPolicy | Calico NetworkPolicy | Separate API groups/resources with different rule semantics |
| - | GlobalNetworkPolicy | Cluster-wide policy (Calico-specific) |
| - | Tier | Policy hierarchy (Calico-specific) |
| Service CIDR | N/A | Calico respects K8s Service CIDR |
| Pod CIDR | IPPool when using Calico IPAM | Not an alias or automatic match to Node PodCIDRs |
| Node | Calico Node | Related node data; lifecycle and representation depend on the datastore |
| Namespace | Namespace | Calico policies can select by namespace |
| Labels | Labels | Same label syntax, used in selectors |
| Pod network interface | WorkloadEndpoint | Not a Service Endpoint/EndpointSlice or a full list of applied policies |
| - | HostEndpoint | Host interface policies (Calico-specific) |

---

## Calico vs Cilium Terminology

These are functional comparisons, not interchangeable resources or feature guarantees. Check the mode, platform and installed version before migrating policies.

| Concept | Calico | Cilium 1.20.1 comparison |
| --- | --- | --- |
| Node agent | Felix | Cilium Agent |
| BGP | BIRD in BGP-enabled profiles | Built-in BGP Control Plane advertises reachability; it does not program the datapath or establish internal routing |
| Datastore fan-out | Typha | No identical Typha component/API |
| Pod IP allocation | IPPool + selected IPAM | Depends on Cilium IPAM mode; not one universal pool API |
| Namespaced policy | Calico NetworkPolicy | CiliumNetworkPolicy; both differ from standard Kubernetes NetworkPolicy |
| Cluster policy | GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy; rule/ordering semantics differ |
| Reusable external CIDRs | NetworkSet / GlobalNetworkSet | Cluster-scoped CiliumCIDRGroup, referenced by cidrGroupRef or cidrGroupSelector in CIDR rules; not CiliumIPSet |
| Policy tiers | Calico Tier | No identical Calico Tier API; other policy APIs have their own ordering rules |
| Workload interface | WorkloadEndpoint | CiliumEndpoint, with different lifecycle/status semantics |
| Host protection | HostEndpoint policies, including configured forwarding rules | Linux host firewall with nodeSelector policies; not identical forwarding scope |
| Dataplane | Linux Iptables/Nftables/BPF; Windows HNS | Linux eBPF requirements; do not describe Windows as a supported beta from this comparison |
| Encryption | OSS WireGuard for supported peer paths | WireGuard or IPsec, with mode/platform-specific limits |
| L7 policy | Separate Istio/Envoy/Dikastes integration documented for OSS | Envoy-based policy features with their own prerequisites |
| Flow visibility | Goldmane/Whisker and component metrics | Hubble and component metrics |
| Controllers | kube-controllers / Tigera Operator | Cilium Operator; responsibilities do not map one-to-one |
| CLI | calicoctl | cilium and agent-side cilium-dbg have distinct roles |

Calico's supported Windows feature set is narrower than Linux: for example, IPv4 HNS with the documented VXLAN/BGP limits, not WireGuard/eBPF/host endpoint parity. There is no evidence here for unconditional performance, maturity or community-size rankings. Compare a specific workload and operational requirement instead.

---

## Cross-References

### Architecture Deep Dive
- **Felix**: See [Part 2: Architecture](02-architecture.md)
- **BGP Configuration**: See [Part 4: BGP Deep Dive](04-bgp-deep-dive.md)
- **Typha Scaling**: See [Part 7: Advanced Topics](07-advanced-topics.md)

### Network Policy
- **Kubernetes NetworkPolicy**: See [Part 5: Network Policy](05-network-policy.md)
- **GlobalNetworkPolicy**: See [Part 5: Network Policy](05-network-policy.md)
- **Tier-Based Policies**: See [Part 5: Network Policy](05-network-policy.md)

### Operations
- **Installation Methods**: See [Part 9: Operations](09-operations.md)
- **calicoctl Commands**: See [Part 9: Operations](09-operations.md)
- **Troubleshooting**: See [Part 9: Operations](09-operations.md)

### EKS Integration
- **VPC CNI + Calico**: See [Part 8: EKS Integration](08-eks-integration.md)
- **Installation Methods**: See [Part 8: EKS Integration](08-eks-integration.md)

---

## Primary References

- [Calico resource reference](https://docs.tigera.io/calico/latest/reference/resources/)
- [Calico tiers](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico MTU](https://docs.tigera.io/calico/latest/networking/configuring/mtu)
- [RFC 6996 private ASNs](https://www.rfc-editor.org/rfc/rfc6996.txt)
- [Cilium CIDR group API](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/v2/cidrgroups_types.go)
- [Cilium BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Cilium host firewall](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/security/host-firewall.rst)

## Quiz

To test what you learned in this chapter, try the [Glossary Quiz](../../quizzes/networking/calico/glossary-quiz.md).
