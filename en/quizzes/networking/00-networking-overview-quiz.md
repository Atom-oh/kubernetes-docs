# Kubernetes Networking Overview Quiz

This quiz tests your understanding of Kubernetes networking fundamentals, CNI (Container Network Interface), and various CNI solutions.

## Quiz Questions

### 1. Which is NOT a core requirement of the Kubernetes networking model?

A. Every Pod can communicate with every other Pod without NAT
B. Every Node can communicate with every Pod without NAT
C. The IP that a Pod sees itself as is the same IP that others see it as
D. Every Pod must have a static IP address that persists after restarts

<details>
<summary>Show Answer</summary>

**Answer: D. Every Pod must have a static IP address that persists after restarts**

**Explanation:**
The core requirements of the Kubernetes networking model are these three:
1. Every Pod can communicate with every other Pod without NAT
2. Every Node can communicate with every Pod without NAT
3. The IP that a Pod sees itself as is the same IP that others see it as

Pod IP addresses are ephemeral - when a Pod restarts, it gets a new IP. This is exactly why Services are needed.

</details>

### 2. What is the primary role of CNI (Container Network Interface)?

A. Communicating with the Kubernetes API server to make Pod scheduling decisions
B. Creating container network interfaces and assigning IP addresses
C. Implementing load balancing for Kubernetes Services
D. Downloading and caching container images

<details>
<summary>Show Answer</summary>

**Answer: B. Creating container network interfaces and assigning IP addresses**

**Explanation:**
CNI is a standard interface for container network connectivity. Its primary roles are:
- Creating network interfaces when containers are created (veth pairs)
- Assigning IP addresses (IPAM)
- Setting up routing rules
- Cleaning up network resources when containers are deleted

Kubelet calls the CNI plugin to set up Pod networking.

</details>

### 3. What is the correct difference between Overlay and Underlay (Native Routing) networks?

A. Overlay provides higher performance, while Underlay incurs more overhead
B. Overlay builds a virtual network on top of existing network, while Underlay routes directly on physical network
C. Overlay uses BGP, while Underlay uses VXLAN
D. Overlay is only available on AWS, while Underlay is only for on-premises

<details>
<summary>Show Answer</summary>

**Answer: B. Overlay builds a virtual network on top of existing network, while Underlay routes directly on physical network**

**Explanation:**
- **Overlay Network**: Uses encapsulation like VXLAN, IPIP to build a virtual network on top of existing network. Simple to set up but has encapsulation overhead.
- **Underlay (Native Routing)**: Routes directly on physical network for higher performance. Uses BGP etc., requires integration with network infrastructure.

</details>

### 4. Which Kubernetes Service type is only accessible from within the cluster?

A. NodePort
B. LoadBalancer
C. ClusterIP
D. ExternalName

<details>
<summary>Show Answer</summary>

**Answer: C. ClusterIP**

**Explanation:**
Kubernetes Service type characteristics:
- **ClusterIP**: Assigns a virtual IP accessible only within the cluster (default)
- **NodePort**: External access via specific ports (30000-32767) on all nodes
- **LoadBalancer**: Provisions cloud load balancer for external access
- **ExternalName**: Creates CNAME record for external DNS name

</details>

### 5. Which CNI uses eBPF technology as its core?

A. Flannel
B. Weave Net
C. Cilium
D. AWS VPC CNI

<details>
<summary>Show Answer</summary>

**Answer: C. Cilium**

**Explanation:**
Cilium is a CNI that uses eBPF (extended Berkeley Packet Filter) as its core technology. Benefits of eBPF:
- High performance with kernel-level network processing
- More efficient packet processing compared to iptables
- L7 visibility and policy enforcement
- Can replace kube-proxy

While Calico also supports eBPF mode, Cilium was designed with eBPF at its core from the beginning.

</details>

### 6. Which is NOT a characteristic of AWS VPC CNI?

A. Assigns actual VPC IP addresses to each Pod
B. Utilizes EC2 instance ENIs (Elastic Network Interfaces)
C. The number of IPs assignable per Pod is limited by instance type
D. Natively supports L7 Network Policy

<details>
<summary>Show Answer</summary>

**Answer: D. Natively supports L7 Network Policy**

**Explanation:**
AWS VPC CNI characteristics:
- Assigns actual VPC IP addresses to Pods (VPC native)
- Uses Secondary IPs from EC2 ENIs
- Max Pod count limited by instance type (ENI count × IPs per ENI)
- Only supports L3-L4 Network Policy by default (L7 requires Calico or Cilium)

For L7 Network Policy, you need additional solutions like Cilium.

</details>

### 7. Which combination of CNIs supports BGP (Border Gateway Protocol)?

A. Flannel, Weave Net
B. Calico, Cilium
C. AWS VPC CNI, Flannel
D. Weave Net, AWS VPC CNI

<details>
<summary>Show Answer</summary>

**Answer: B. Calico, Cilium**

**Explanation:**
CNIs that support BGP:
- **Calico**: BGP is a core feature, supports ToR switch peering, Route Reflector
- **Cilium**: BGP support (v1.10+), useful in multi-cluster environments

CNIs that don't support BGP:
- **Flannel**: Simple overlay network, no BGP support
- **Weave Net**: Uses its own routing protocol, no BGP support
- **AWS VPC CNI**: Uses VPC native routing, no BGP support

</details>

### 8. Which type of traffic is NOT subject to Kubernetes Network Policy?

A. Traffic from Pod to another Pod
B. Traffic from Pod to external internet
C. Localhost traffic between containers in the same Pod
D. Traffic coming into Pod from external sources

<details>
<summary>Show Answer</summary>

**Answer: C. Localhost traffic between containers in the same Pod**

**Explanation:**
Network Policy controls traffic between Pods. Containers within the same Pod:
- Share the same network namespace
- Communicate via localhost (127.0.0.1)
- Are not subject to Network Policy

Traffic subject to Network Policy:
- Ingress/Egress traffic between Pods
- Egress traffic from Pod to external
- Ingress traffic from external to Pod

</details>

### 9. What is the most important consideration when choosing a CNI for large-scale Kubernetes clusters (500+ nodes)?

A. Whether UI dashboard is provided
B. Control plane scalability and data synchronization efficiency
C. Logo design and documentation quality
D. Frequency of new version releases

<details>
<summary>Show Answer</summary>

**Answer: B. Control plane scalability and data synchronization efficiency**

**Explanation:**
Considerations when selecting CNI for large clusters:

1. **Control Plane Scalability**:
   - Calico: Typha component reduces API server load
   - Cilium: Efficient synchronization with Operator mode

2. **Data Synchronization**:
   - Resource usage per node agent
   - Policy update propagation time

3. **Performance**:
   - eBPF-based solutions scale better than iptables-based
   - Performance degradation as rule count increases

</details>

### 10. What is the correct difference between Ingress and Service?

A. Ingress operates at L4, while Service operates at L7
B. Ingress defines HTTP/HTTPS routing rules, while Service provides network endpoints for a set of Pods
C. Ingress only supports internal cluster communication, while Service only supports external communication
D. Ingress only supports TCP, while Service only supports UDP

<details>
<summary>Show Answer</summary>

**Answer: B. Ingress defines HTTP/HTTPS routing rules, while Service provides network endpoints for a set of Pods**

**Explanation:**
- **Service**: Provides stable network endpoints for a set of Pods (L4)
  - ClusterIP, NodePort, LoadBalancer types
  - Supports TCP/UDP protocols

- **Ingress**: Defines HTTP/HTTPS traffic routing rules (L7)
  - Host-based routing
  - Path-based routing
  - TLS termination
  - Ingress Controller provides actual implementation

Ingress ultimately forwards traffic to backend Services.

</details>

---

## Additional Learning Resources

- [Kubernetes Networking Model](https://kubernetes.io/docs/concepts/cluster-administration/networking/)
- [CNI Specification](https://github.com/containernetworking/cni/blob/master/SPEC.md)
- [Network Policy Guide](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
