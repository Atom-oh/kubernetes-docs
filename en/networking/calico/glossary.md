# Calico Glossary

> **Last Updated**: February 22, 2025

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
- A unique identifier assigned to an Autonomous System. Calico nodes can be configured with private ASNs (64512-65534) for internal BGP routing.

### B

**BGP (Border Gateway Protocol)**
- The standard exterior gateway protocol used to exchange routing information between autonomous systems. Calico uses BGP to distribute routes for pod IP addresses across nodes and to external networks.

**Block Affinity**
- The association between an IP address block and a specific node. Calico assigns IP blocks to nodes to improve routing efficiency and reduce the number of routes in the cluster.

### C

**CIDR (Classless Inter-Domain Routing)**
- A method for allocating IP addresses and IP routing. Example: 10.244.0.0/16 represents a range of 65,536 IP addresses.

**CNI (Container Network Interface)**
- A specification and set of libraries for configuring network interfaces in Linux containers. Calico implements the CNI specification to provide networking for Kubernetes pods.

**Conntrack (Connection Tracking)**
- A Linux kernel feature that tracks network connections for stateful packet inspection. Calico uses conntrack for implementing network policies and NAT.

### D

**DNAT (Destination NAT)**
- Network address translation that modifies the destination IP address of packets. Used in Kubernetes for Service load balancing.

**Direct Routing**
- A networking mode where traffic between pods on different nodes is routed directly without encapsulation. Requires underlying network to support pod CIDR routing.

**DSR (Direct Server Return)**
- A load balancing technique where response traffic bypasses the load balancer and goes directly from the server to the client. Calico's eBPF dataplane supports DSR for improved performance.

### E

**eBPF (extended Berkeley Packet Filter)**
- A Linux kernel technology that allows running sandboxed programs in kernel space. Calico uses eBPF as an alternative dataplane to iptables for improved performance.

**Encapsulation**
- The process of wrapping network packets inside other packets. Calico supports IPIP and VXLAN encapsulation for overlay networking.

### F

**FQDN (Fully Qualified Domain Name)**
- A complete domain name that specifies the exact location of a host in the DNS hierarchy. Calico supports FQDN-based network policies for egress control.

**Full Mesh**
- A BGP topology where every node peers with every other node. Suitable for small clusters but doesn't scale well beyond 100 nodes.

### I

**IPAM (IP Address Management)**
- The system responsible for allocating, tracking, and managing IP addresses. Calico includes a built-in IPAM system with block-based allocation.

**IPIP (IP-in-IP)**
- An encapsulation protocol that wraps IP packets inside other IP packets. Has lower overhead than VXLAN but limited cloud provider support.

**IPset**
- A Linux kernel feature for storing sets of IP addresses, networks, or ports. Calico uses ipsets to efficiently match traffic against multiple addresses.

**iptables**
- A Linux kernel firewall that operates at the network layer. Calico uses iptables (or nftables) for packet filtering and NAT in the standard dataplane.

### M

**MTU (Maximum Transmission Unit)**
- The largest packet size that can be transmitted on a network segment. Encapsulation reduces effective MTU (IPIP: -20 bytes, VXLAN: -50 bytes).

### N

**NAT (Network Address Translation)**
- The process of modifying IP address information in packet headers. Calico uses NAT for pod egress and Service implementation.

**nftables**
- The successor to iptables, providing a modern framework for packet classification. Calico supports nftables as an alternative to iptables.

### O

**Overlay Network**
- A virtual network built on top of an existing physical network. Calico supports IPIP and VXLAN overlay modes for environments where direct routing isn't possible.

### R

**Route Reflector**
- A BGP router that reflects routes between clients, eliminating the need for full-mesh peering. Essential for scaling BGP in large Calico clusters.

**Routing Table**
- A data structure that stores routes to network destinations. Calico programs routes for pod CIDRs into the Linux kernel routing table.

### S

**SNAT (Source NAT)**
- Network address translation that modifies the source IP address of packets. Used for pod egress traffic and masquerading.

### V

**veth (Virtual Ethernet)**
- A pair of virtual network interfaces used to connect network namespaces. Each Calico pod has a veth pair connecting it to the host network.

**VXLAN (Virtual Extensible LAN)**
- An encapsulation protocol that extends Layer 2 networks over Layer 3 infrastructure. Provides better cloud compatibility than IPIP but with higher overhead.

### W

**WireGuard**
- A modern VPN protocol providing fast and secure encryption. Calico uses WireGuard for encrypting pod-to-pod traffic between nodes.

**Workload Endpoint**
- Calico's representation of a network interface for a workload (pod, VM, or container). Stores IP addresses, labels, and policy associations.

---

## Calico Components

### B

**BIRD (BIRD Internet Routing Daemon)**
- The BGP daemon used by Calico for route distribution. BIRD manages BGP peering, route advertisement, and Route Reflector functionality.

### C

**calicoctl**
- The command-line tool for managing Calico resources. Used for viewing status, configuring policies, managing IPAM, and troubleshooting.

**Calico API Server**
- An optional component that provides a Kubernetes API extension for Calico resources. Enables kubectl access to Calico CRDs.

**CNI Plugin**
- The binary that implements the CNI specification for Calico. Responsible for setting up pod networking (veth pairs, routes, IP assignment).

**confd**
- A configuration management tool that generates BIRD configuration files from the Calico datastore. Watches for changes and updates BIRD dynamically.

### D

**Dikastes**
- A sidecar proxy used for L7 policy enforcement in Calico (primarily in Calico Enterprise). Provides application-layer visibility and control.

### F

**Felix**
- The primary Calico agent running on each node. Responsible for programming routes, iptables/eBPF rules, and enforcing network policies.

### K

**kube-controllers**
- A set of controllers that sync data between Kubernetes and the Calico datastore. Includes policy, namespace, serviceaccount, workloadendpoint, and node controllers.

### T

**Tigera Operator**
- A Kubernetes operator that manages Calico installation and lifecycle. Provides declarative configuration through CRDs.

**Typha**
- A fan-out proxy that sits between Felix and the datastore. Reduces load on the API server by caching and multiplexing connections.

---

## Policy Terms

### A

**Action**
- The result of a policy rule evaluation: Allow, Deny, Log, or Pass. Determines how matching traffic is handled.

**applyOnForward**
- A policy setting that applies rules to forwarded traffic (traffic passing through the host). Used for controlling traffic between pods and external networks.

### D

**Default Deny**
- A security posture where all traffic is blocked unless explicitly allowed. Implemented using a catch-all policy with no allow rules.

**DoNotTrack**
- A policy option that bypasses connection tracking for matched traffic. Useful for high-throughput scenarios where stateless handling is acceptable.

### E

**Egress**
- Outbound network traffic from a pod. Egress policies control what destinations a pod can communicate with.

### G

**GlobalNetworkPolicy**
- A Calico policy resource that applies across all namespaces in a cluster. Used for cluster-wide security rules.

**GlobalNetworkSet**
- A cluster-scoped set of IP addresses or CIDRs. Referenced by GlobalNetworkPolicies for consistent external endpoint definitions.

### H

**Host Endpoint**
- A Calico resource representing a host's network interface. Enables applying network policies to host-level traffic.

### I

**Ingress**
- Inbound network traffic to a pod. Ingress policies control what sources can communicate with a pod.

### N

**NetworkPolicy**
- A Kubernetes or Calico resource that specifies how pods are allowed to communicate. Operates at L3-L4 (and L7 with Calico Enterprise).

**NetworkSet**
- A namespace-scoped set of IP addresses or CIDRs. Provides a way to group external endpoints for use in network policies.

### O

**Order**
- A numeric value that determines the evaluation sequence of policies. Lower numbers are evaluated first. Policies with the same order are evaluated alphabetically.

### P

**Pass**
- A policy action that skips to the next tier without making a decision. Used in tiered policy models to delegate decisions.

**Policy Selector**
- A label-based expression that determines which endpoints a policy applies to. Uses Calico's selector syntax (e.g., `app == 'web'`).

**PreDNAT**
- A policy type that is applied before destination NAT. Used for controlling access to NodePort and LoadBalancer services.

### S

**Staged Policy**
- A policy in preview mode that logs what would happen without actually enforcing. Available in Calico Enterprise for policy testing.

**Selector**
- An expression that matches resources based on labels. Calico uses selectors for both policy targets and source/destination matching.

### T

**Tier**
- A policy grouping mechanism that provides hierarchical policy evaluation. Policies in lower-order tiers are evaluated first.

---

## Operations Terms

### A

**APIServer (Calico)**
- The component that provides API access to Calico resources. Can be enabled for kubectl integration.

### B

**Block**
- A unit of IP address allocation in Calico IPAM. Default size is /26 (64 addresses). Blocks are assigned to nodes for efficient routing.

**Block Affinity**
- The binding between an IP block and a node. Ensures pods on a node receive IPs from blocks assigned to that node.

### D

**Dataplane**
- The component responsible for packet forwarding and policy enforcement. Calico supports iptables and eBPF dataplanes.

**Datastore**
- The backend storage for Calico configuration. Supports Kubernetes API (default) or etcd.

### F

**FelixConfiguration**
- The CRD that configures Felix behavior across the cluster. Controls logging, metrics, dataplane settings, and more.

**Flow Logs**
- Records of network connections processed by Calico. Includes source, destination, action, and metadata.

### H

**Health Check**
- Liveness and readiness probes for Calico components. Felix exposes health endpoints on port 9099.

### I

**Installation**
- The Tigera Operator CRD that defines Calico deployment configuration. Specifies networking mode, resources, and component settings.

### M

**Metrics**
- Prometheus-format statistics exposed by Calico components. Felix (9091), Typha (9093), and kube-controllers expose operational metrics.

### P

**Pod CIDR**
- The IP address range allocated for pods in a cluster. Configured in Calico's IPPool resources.

### R

**Rollout**
- The process of updating Calico components. The operator manages rolling updates to minimize disruption.

### T

**TigeraStatus**
- A CRD that reports the status of Calico components. Shows deployment health and configuration state.

---

## Calico vs Kubernetes Terminology

| Kubernetes Term | Calico Equivalent | Notes |
|-----------------|-------------------|-------|
| NetworkPolicy | NetworkPolicy | Calico extends K8s NetworkPolicy with additional features |
| - | GlobalNetworkPolicy | Cluster-wide policy (Calico-specific) |
| - | Tier | Policy hierarchy (Calico-specific) |
| Service CIDR | N/A | Calico respects K8s Service CIDR |
| Pod CIDR | IPPool | Calico manages pod IP allocation |
| Node | Node | Calico mirrors K8s Node resources |
| Namespace | Namespace | Calico policies can select by namespace |
| Labels | Labels | Same label syntax, used in selectors |
| Endpoint | WorkloadEndpoint | Calico's internal endpoint representation |
| - | HostEndpoint | Host interface policies (Calico-specific) |

---

## Calico vs Cilium Terminology

| Calico Term | Cilium Equivalent | Description |
|-------------|-------------------|-------------|
| Felix | Cilium Agent | Primary node agent |
| BIRD | BGP Control Plane | BGP routing daemon |
| Typha | - | Connection fan-out proxy (Calico-specific) |
| IPPool | IPAM Pool | IP address allocation pool |
| NetworkPolicy | CiliumNetworkPolicy | Namespace-scoped policy |
| GlobalNetworkPolicy | CiliumClusterwideNetworkPolicy | Cluster-wide policy |
| NetworkSet | CiliumIPSet | IP address groupings |
| Tier | - | Policy hierarchy (Calico-specific) |
| WorkloadEndpoint | CiliumEndpoint | Pod network endpoint |
| HostEndpoint | - | Host policy (Calico-specific) |
| eBPF Dataplane | eBPF Dataplane | High-performance packet processing |
| WireGuard | WireGuard | Encryption between nodes |
| - | Hubble | Observability platform (Cilium-specific) |
| Flow Logs | Hubble Flows | Network flow visibility |
| kube-controllers | Cilium Operator | Kubernetes synchronization |
| calicoctl | cilium CLI | Management command-line tool |

---

## Cross-References

### Architecture Deep Dive
- **Felix**: See [Part 2: Architecture](02-architecture.md)
- **BGP Configuration**: See [Part 4: BGP Deep Dive](04-bgp-deep-dive.md)
- **Typha Scaling**: See [Part 7: Advanced Topics](07-advanced-topics.md#typha-sizing-formula)

### Network Policy
- **Kubernetes NetworkPolicy**: See [Part 5: Network Policy](05-network-policy.md)
- **GlobalNetworkPolicy**: See [Part 5: Network Policy](05-network-policy.md)
- **Tier-Based Policies**: See [Part 5: Network Policy](05-network-policy.md)

### Operations
- **Installation Methods**: See [Part 9: Operations](09-operations.md#installation-guide)
- **calicoctl Commands**: See [Part 9: Operations](09-operations.md#calicoctl-command-reference)
- **Troubleshooting**: See [Part 9: Operations](09-operations.md#troubleshooting)

### EKS Integration
- **VPC CNI + Calico**: See [Part 8: EKS Integration](08-eks-integration.md#vpc-cni--calico-architecture)
- **Installation Methods**: See [Part 8: EKS Integration](08-eks-integration.md#installation-methods-comparison)

---

## Quiz

To test what you learned in this chapter, try the [Glossary Quiz](../../quizzes/networking/calico/glossary-quiz.md).
