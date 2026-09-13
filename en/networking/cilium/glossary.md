# Glossary and Abbreviations

> **Review baseline**: Cilium 1.20.1.
> **Last reviewed**: September 12, 2026.

An alphabetical reference for Cilium, eBPF, Kubernetes and networking. Repeated entries are consolidated.

## A

**API (Application Programming Interface)** - General

- A set of interface definitions that enable communication between applications

**ARP (Address Resolution Protocol)** - Networking

- Resolves an IPv4 address to a link-layer address on the local link, commonly an Ethernet MAC address.
- For a remote destination, a host resolves its next hop. IPv6 uses Neighbor Discovery rather than ARP.

**AWS ENI (Elastic Network Interface)** - Networking

- Virtual network interface provided by Amazon Web Services
- Used in Cilium's AWS ENI IPAM mode

## B

**BGP (Border Gateway Protocol)** - Networking

- An inter-domain routing protocol used to advertise reachability between peers.
- Cilium BGP Control Plane advertises selected prefixes; it is not a native-routing mode and does not program the local datapath routes.

**BPF (Berkeley Packet Filter)** - eBPF

- Technology for packet filtering, predecessor to eBPF
- Originally developed for network packet capture

**BPF Maps** - eBPF

- Kernel-managed data structures used by BPF programs and userspace to share state or events.
- Many types use keys and values; ring buffers, queues and stacks have different operations. A BPF ring buffer does not support map lookup/update/delete.

## C

**CGroup (Control Group)** - Kubernetes

- Linux control groups organize processes and account for or control resources such as CPU and memory.
- Container runtimes use cgroups; they are not, by themselves, process/network namespace isolation.

**CIDR (Classless Inter-Domain Routing)** - Networking

- Method for IP address allocation and routing aggregation
- Example: 192.168.1.0/24 represents IP address range from 192.168.1.0 to 192.168.1.255

**Cilium** - Cilium

- Open source networking, security, and observability solution based on eBPF
- Used as a Kubernetes CNI implementation

**Cilium Agent** - Cilium

- The node-local Cilium component that manages endpoints, BPF programs and policy/datapath state. It runs on Cilium-managed eligible nodes.

**Cilium Operator** - Cilium

- The cluster-level controller for tasks such as CRD registration, mode-dependent IPAM/LB IPAM, garbage collection and enabled Ingress/Gateway controllers.
- Replica count is configurable. Optional identity management and ClusterMesh synchronization depend on enabled features; it is not the node packet-forwarding component.

**ClusterMesh** - Cilium

- Cilium's multi-cluster network metadata/connectivity features for service discovery, load balancing and remote-identity policy.
- Requires compatible addressing, trust and reachable paths; it neither supplies shared storage nor automatically replicates every policy resource.

**CNI (Container Network Interface)** - Kubernetes

- Container Network Interface: a specification and plugins for configuring container network connectivity.
- In current Kubernetes, the CRI container runtime loads/invokes CNI plugins. kubelet's former direct CNI-management flags were removed in Kubernetes 1.24.

**CoreDNS** - Kubernetes

- DNS server commonly used in Kubernetes clusters
- Plays an important role in service discovery

**CRD (Custom Resource Definition)** - Kubernetes

- Method to define custom resources by extending the Kubernetes API
- Cilium uses CRDs to define network policies, etc.

## D

**DaemonSet**

- A Kubernetes controller that runs daemon Pods on eligible nodes selected by its scheduling constraints; it need not cover every node.

**DNAT (Destination Network Address Translation)** - Networking

- NAT type that modifies the destination IP address of packets
- Used for load balancing and port forwarding

**DNS (Domain Name System)** - Networking

- A distributed naming system that publishes records such as A/AAAA addresses, CNAME aliases and SRV service information.
- Cilium DNS policy and learned-IP FQDN policy are related but distinct controls.

## E

**eBPF (extended Berkeley Packet Filter)** - eBPF

- Extended Berkeley Packet Filter: programmable kernel hooks and associated infrastructure used by Cilium.
- The verifier checks program properties before acceptance. It does not guarantee that kernel or verifier implementations are free of vulnerabilities.

**Endpoint** - Cilium

- A Cilium-managed network endpoint, commonly a Pod, with local datapath/policy state.
- Its endpoint ID is local to the agent and is distinct from a security identity shared by multiple endpoints.

**Envoy** - Cilium

- An open-source proxy used by Cilium for configured HTTP/gRPC policy, L7 visibility and proxy-based service routing.
- DNS policy uses Cilium's DNS proxy. Kafka L7 policy is no longer supported; not every L7 rule automatically deploys an Envoy instance.

## F

**FQDN (Fully Qualified Domain Name)**

- Fully Qualified Domain Name: an absolute name identifying its full position in the DNS tree, often written with the final root dot, for example `www.example.com.`.
- Cilium `toFQDNs` permits learned destination IPs. It does not by itself authenticate an HTTPS server or constrain all HTTP Host values on a shared IP.

## G

**GENEVE (Generic Network Virtualization Encapsulation)**

- Encapsulation protocol for network virtualization

**gRPC (gRPC Remote Procedure Call)**

- High-performance RPC (Remote Procedure Call) framework developed by Google

## H

**Hubble** - Cilium

- Cilium's network observability layer: flow events, supported protocol metadata, metrics and query interfaces.
- History is bounded and observations can be lost or filtered. Alerts, durable storage and automated response require configured integrations.

## I

**Identity** - Cilium

- A numeric security identifier derived from security-relevant labels. Multiple endpoints can share it within the applicable allocation scope.
- CiliumIdentity's `security-labels` field is the source of truth in CRD allocation mode. Reserved and node-local identities are not all represented by these cluster-scoped objects.

**IPAM (IP Address Management)** - Networking

- IP Address Management: address allocation, tracking and reclamation.
- Cilium modes have different allocation owners and data sources, including cluster-pool, multi-pool, Kubernetes host-scope and cloud-specific modes. A platform name is not necessarily a separate `ipam.mode` value.

**IPsec** - Networking

- Internet Protocol Security: a suite of mechanisms for IP-layer authentication/integrity and, with the appropriate configuration, confidentiality.
- Cilium uses IPsec for supported inter-node traffic encryption; key management and path-specific limitations still apply.

**Istio**

- Open source platform that implements service mesh

## K

**Kafka**

- A distributed event-streaming platform. It remains a possible workload, but current Cilium does not provide the former Kafka topic L7 policy API.

**kube-proxy** - Kubernetes

- A Kubernetes component that implements Service virtual-IP/port forwarding through supported node networking mechanisms.
- Cilium can replace this function with eBPF; XDP acceleration is optional and the platform must support the chosen configuration.

**Kubernetes**

- Open source platform that automates deployment, scaling, and management of containerized applications

## L

**L2 (Layer 2)**

- Data link layer of OSI model

**L3 (Layer 3)**

- Network layer of OSI model

**L4 (Layer 4)**

- Transport layer of OSI model

**L7 (Layer 7)**

- Application layer of OSI model

**LoadBalancer**

- A traffic-distribution function. Kubernetes `type: LoadBalancer` requests an implementation from a controller/provider; an external load balancer is not guaranteed without one.

## M

**MAC (Media Access Control) Address**

- Media Access Control address: a link-layer address associated with an interface.
- Addresses may be locally administered or changed; uniqueness and authenticity must not be assumed.

**mTLS (mutual TLS)**

- Mutual TLS: TLS in which both peers authenticate, typically by validating each other's certificates.
- Peer authentication is distinct from application authorization. Cilium's out-of-band mutual authentication and Beta ztunnel workload mTLS are separate features with different traffic-protection properties.

**MTU (Maximum Transmission Unit)**

- Maximum Transmission Unit: the largest network-layer packet carried on a link/interface without fragmentation, including its IP header but not the link-layer header.
- Path MTU is constrained by the path; tunnel/encryption overhead affects the usable inner packet size. It is not TCP MSS or application payload size.

## N

**NAT (Network Address Translation)**

- Process of modifying IP address information in IP packets

**NodePort**

- A Kubernetes Service exposure method using an allocated node port on eligible node addresses.
- Address selection, traffic policy, firewall and platform routing determine reachability; declaring a NodePort does not guarantee public access.

## O

**OSI (Open Systems Interconnection) Model**

- Conceptual model that classifies network communication into 7 abstract layers

**Overlay Network**

- Virtual network built on top of an existing network

## P

**Pod**

- Smallest deployable computing unit in Kubernetes

**Proxy**

- A component that mediates communication between peers; it need not be a separate physical server.

## R

**RBAC (Role-Based Access Control)**

- Method for controlling access to system resources based on roles

## S

**Service**

- A Kubernetes abstraction for reaching a logical set of backends, often Pods selected by labels.
- Ordinary ClusterIP Services have a virtual IP; headless Services do not. ExternalName uses DNS aliasing, and selectorless Services can use manually managed EndpointSlices.

**SNAT (Source Network Address Translation)**

- NAT type that modifies the source IP address of packets

**Socket**

- An operating-system communication endpoint used for network or local inter-process communication.

## T

**TCP (Transmission Control Protocol)**

- Connection-oriented transport protocol that provides reliable byte streams

**TLS (Transport Layer Security)**

- Cryptographic protocol that protects communication over networks

## U

**UDP (User Datagram Protocol)**

- Connectionless transport protocol

## V

**VETH (Virtual Ethernet)**

- Virtual ethernet device, typically created in pairs

**VNI (VXLAN Network Identifier)**

- VXLAN Network Identifier: a 24-bit field in the VXLAN header.
- Cilium can carry identity information in overlay metadata; the field width is not a promise of millions of independently configured tenant networks.

**VTEP (VXLAN Tunnel Endpoint)**

- Endpoint responsible for encapsulation and decapsulation of VXLAN packets

**VXLAN (Virtual Extensible LAN)** - Networking

- Network virtualization technology that overlays Layer 2 networks over Layer 3 networks
- One of Cilium's overlay networking modes

## W

**WireGuard** - Networking

- A VPN tunnel protocol used by Cilium for supported cross-node traffic.
- Same-node Pod traffic is not encrypted by its node tunnel; external traffic and optional node encryption have separate limits. Performance relative to IPsec requires a comparable measurement.

## X

**XDP (eXpress Data Path)** - eBPF

- eXpress Data Path: a packet-processing hook; native XDP runs in a supporting network driver's receive path.
- PASS continues into the networking stack; other actions can drop, transmit or redirect. Cilium's supported XDP acceleration is optional, not a universal throughput or DDoS-protection guarantee.

## Primary References

- [Cilium identities](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/internals/security-identities.rst)
- [CiliumIdentity schema](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumidentities.yaml)
- [Cilium Operator](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/internals/cilium_operator.rst)
- [Identity management modes](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/kubernetes/identity-management-mode.rst)
- [WireGuard](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/security/network/encryption-wireguard.rst)
- [BGP](https://raw.githubusercontent.com/cilium/cilium/v1.20.1/Documentation/network/bgp-control-plane/bgp-control-plane.rst)
- [Kubernetes CNI/CRI](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/network-plugins/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)
- [BPF ring buffer](https://docs.kernel.org/bpf/ringbuf.html)
- [ARP / RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)
- [IPv6 Neighbor Discovery / RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)
- [VXLAN / RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)
- [MAC addressing / RFC 7042](https://www.rfc-editor.org/rfc/rfc7042.txt)

## Quiz

[Topic quiz](../../quizzes/networking/cilium/glossary-quiz.md)
