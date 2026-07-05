# Glossary Quiz

This quiz tests your understanding of key terms and concepts related to Cilium, eBPF, Kubernetes, and networking.

## Multiple Choice Questions

1. What is the full name of eBPF?
   * A) Enhanced Berkeley Packet Filter
   * B) Extended Berkeley Packet Filter
   * C) Embedded BPF Filter
   * D) External Berkeley Protocol Filter

<details>

<summary>Show Answer</summary>

**Answer: B) Extended Berkeley Packet Filter**

**Explanation:** eBPF stands for Extended Berkeley Packet Filter, an extended version of BPF (Berkeley Packet Filter) originally developed for network packet capture. eBPF is a technology that allows programs to run safely within the Linux kernel, used for various purposes including network packet processing, system call tracing, and performance monitoring. Cilium leverages eBPF as its core technology to provide high-performance networking, security, and observability features.

</details>

2. What is the basic unit to which network policies are applied in Cilium?
   * A) Pod
   * B) Node
   * C) Endpoint
   * D) Service

<details>

<summary>Show Answer</summary>

**Answer: C) Endpoint**

**Explanation:** In Cilium, an Endpoint refers to a network endpoint to which network policies are applied, typically corresponding to a Kubernetes pod. Each Endpoint has a unique ID, and Cilium applies network policies and controls traffic based on these Endpoints. Endpoints are managed by the Cilium Agent and are automatically created when pods are created. You can check all Endpoints on the current node using the `cilium endpoint list` command.

</details>

3. What is the main characteristic of XDP (eXpress Data Path)?
   * A) L7 protocol analysis
   * B) Packet processing at network driver level
   * C) TLS encryption
   * D) DNS resolution

<details>

<summary>Show Answer</summary>

**Answer: B) Packet processing at network driver level**

**Explanation:** XDP (eXpress Data Path) is an eBPF-based technology that processes packets at the network driver level (interrupt context). This bypasses the kernel network stack to enable very high-performance packet processing (millions of packets per second). XDP can process packets with actions such as DROP, PASS, TX (transmit), and REDIRECT. Cilium uses XDP to implement DDoS protection, high-performance load balancing, and packet filtering.

</details>

4. What is the name of Cilium's network observability platform?
   * A) Prometheus
   * B) Grafana
   * C) Hubble
   * D) Jaeger

<details>

<summary>Show Answer</summary>

**Answer: C) Hubble**

**Explanation:** Hubble is Cilium's network observability platform that uses eBPF to monitor and analyze network flows in real-time. Hubble's main features include network flow monitoring, service dependency map generation, network policy violation detection, performance metrics collection, and security event tracking. Hubble provides both CLI and web-based UI, and can be integrated with Prometheus and Grafana to visualize metrics.

</details>

5. What is the full name and main purpose of VXLAN?
   * A) Virtual Extended LAN - Virtual network creation
   * B) Virtual Extensible LAN - L2 overlay network
   * C) Very Extended LAN - Large-scale network expansion
   * D) Variable Extensible LAN - Dynamic network configuration

<details>

<summary>Show Answer</summary>

**Answer: B) Virtual Extensible LAN - L2 overlay network**

**Explanation:** VXLAN (Virtual Extensible LAN) is a network virtualization technology that overlays Layer 2 (L2) networks on top of Layer 3 (L3) networks. VXLAN uses UDP encapsulation for tunneling and supports up to approximately 16 million network segments with a 24-bit VNI (VXLAN Network Identifier). In Cilium, VXLAN is used as an overlay networking mode for inter-node pod communication. Alternatives include GENEVE or native routing mode.

</details>

6. What is the main role of BPF Maps?
   * A) Network routing table management
   * B) Data sharing and storage between eBPF programs
   * C) DNS record caching
   * D) TLS certificate storage

<details>

<summary>Show Answer</summary>

**Answer: B) Data sharing and storage between eBPF programs**

**Explanation:** BPF Maps are key-value stores used by eBPF programs to store and retrieve data. BPF Maps are also used for data sharing between kernel space and user space. Main types include Hash Map (key-value store), Array Map (index-based array), LRU Map (least recently used cache), and Ring Buffer (circular buffer). Cilium uses BPF Maps to store service maps, backend maps, connection tracking tables, and more.

</details>

7. What is the numeric identifier representing a pod's security identity in Cilium called?
   * A) Pod ID
   * B) Security Context
   * C) Identity
   * D) Endpoint ID

<details>

<summary>Show Answer</summary>

**Answer: C) Identity**

**Explanation:** Cilium Identity is a numeric identifier generated based on a pod's label set. All pods with the same labels share the same Identity. Identity-based policies use Identity instead of IP addresses to apply network policies, so policies remain consistent even when pod IPs change. This approach is highly scalable and works efficiently even in large clusters. Endpoint ID identifies a specific pod instance and is different from Identity.

</details>

8. What is the full name of IPAM and its role in Cilium?
   * A) IP Address Management - IP address allocation and management
   * B) Internet Protocol Access Manager - Internet access management
   * C) IP Assignment Module - IP assignment module
   * D) Internal Protocol Address Mapper - Internal protocol address mapping

<details>

<summary>Show Answer</summary>

**Answer: A) IP Address Management - IP address allocation and management**

**Explanation:** IPAM (IP Address Management) is a system responsible for planning, allocating, tracking, and managing IP addresses. Cilium supports several IPAM modes: Cluster Pool (cluster-wide IP pool management), Kubernetes (using Kubernetes node CIDR), AWS ENI (using AWS Elastic Network Interface), Azure (Azure networking integration), and GKE (Google Kubernetes Engine integration). IPAM mode selection depends on the cluster environment and networking requirements.

</details>

9. What is the main characteristic of WireGuard and its use in Cilium?
   * A) Packet capture tool - Network analysis
   * B) Modern VPN protocol - Inter-node traffic encryption
   * C) Load balancing algorithm - Traffic distribution
   * D) DNS proxy - Name resolution

<details>

<summary>Show Answer</summary>

**Answer: B) Modern VPN protocol - Inter-node traffic encryption**

**Explanation:** WireGuard is a modern, fast, and secure VPN (Virtual Private Network) tunnel protocol. It is simpler and faster than IPsec, with a smaller codebase that makes security auditing easier. In Cilium, WireGuard is used for inter-node traffic encryption. When WireGuard is enabled, all traffic between pods in the cluster is transparently encrypted. Cilium can implement encryption using either IPsec or WireGuard.

</details>

10. What is the full name and role of CNI?
    * A) Container Network Interface - Standard interface for container network plugins
    * B) Cloud Native Infrastructure - Cloud native infrastructure
    * C) Cluster Network Integration - Cluster network integration
    * D) Container Node Interconnect - Container node connection

<details>

<summary>Show Answer</summary>

**Answer: A) Container Network Interface - Standard interface for container network plugins**

**Explanation:** CNI (Container Network Interface) is a CNCF project that defines a standard interface between container runtimes and network plugins. In Kubernetes, kubelet communicates with network plugins (Cilium, Calico, Flannel, etc.) through the CNI interface. CNI defines a standard API for network configuration when containers are added/removed, enabling integration of various networking solutions through a plugin architecture. Cilium is one of the CNI implementations.

</details>

## Short Answer Questions

11. What is the name of the open-source component that provides L7 proxy and service mesh functionality in Cilium?

<details>

<summary>Show Answer</summary>

**Answer:** Envoy

**Explanation:** Envoy is an open-source edge and service proxy used as an L7 proxy and communication bus. Cilium integrates Envoy for L7 network policy implementation. When you define L7 rules (HTTP, gRPC, Kafka, DNS, etc.) in a CiliumNetworkPolicy, Cilium automatically deploys the Envoy proxy transparently. Envoy also provides advanced load balancing, traffic splitting, and metrics collection features.

</details>

12. What is the name of the Cilium component that runs on each node and is responsible for eBPF program loading, network policy implementation, and endpoint management?

<details>

<summary>Show Answer</summary>

**Answer:** Cilium Agent

**Explanation:** Cilium Agent is Cilium's core component that runs as a DaemonSet on each Kubernetes node. The Agent's main responsibilities include loading and managing eBPF programs into the kernel, implementing and applying network policies, performing service load balancing, IP address management (IPAM), network endpoint management, metrics and log collection, and communication with the Kubernetes API server. Local networking operations on each node are handled by that node's Cilium Agent.

</details>

13. What is the name and number of the OSI model layer responsible for packet routing using IP addresses?

<details>

<summary>Show Answer</summary>

**Answer:** L3 (Network Layer)

**Explanation:** L3 (Network Layer) is the 3rd layer of the OSI model, responsible for logical addressing using IP addresses and packet routing. IP (Internet Protocol) and ICMP (Internet Control Message Protocol) operate at this layer. Cilium L3 policies can filter traffic based on IP addresses and CIDR blocks. L2 (Data Link Layer) uses MAC addresses, and L4 (Transport Layer) uses port numbers.

</details>

14. What is the name of the Kubernetes resource that provides stable network endpoints for a set of pods?

<details>

<summary>Show Answer</summary>

**Answer:** Service

**Explanation:** Kubernetes Service is an abstraction that provides stable network endpoints (ClusterIP, DNS name) for a set of pods. Pods are dynamically created/deleted and their IPs can change, but Services provide fixed IPs and DNS names for consistent client access. Cilium implements service load balancing through eBPF, which can replace kube-proxy. Service types include ClusterIP, NodePort, LoadBalancer, and ExternalName.

</details>

15. What is the name of the NAT type that modifies the source IP address of a packet?

<details>

<summary>Show Answer</summary>

**Answer:** SNAT (Source NAT) or Masquerading

**Explanation:** SNAT (Source Network Address Translation) is a NAT type that translates the source IP address of a packet to another IP address. Masquerading is a special form of SNAT that automatically translates the source IP to the outbound interface's IP. In Cilium, masquerading is used to translate the source IP of outbound traffic from pods inside the cluster to the node IP. Conversely, DNAT (Destination NAT) modifies the destination IP.

</details>

## Hands-on Questions

16. Match the following Cilium-related terms with their definitions: Cluster Mesh, CRD, FQDN, mTLS

<details>

<summary>Show Answer</summary>

**Answer:**

* **Cluster Mesh**: Cilium's multi-cluster networking feature. Connects multiple Kubernetes clusters to enable cross-cluster service discovery, load balancing, and network policy enforcement.
* **CRD (Custom Resource Definition)**: A method to extend the Kubernetes API by defining custom resources. Cilium uses CRDs to define CiliumNetworkPolicy, CiliumEndpoint, and more.
* **FQDN (Fully Qualified Domain Name)**: A host's full domain name (e.g., www.example.com). Cilium FQDN policies control access to external services by domain name instead of IP.
* **mTLS (mutual TLS)**: An extension of TLS where both client and server authenticate each other with certificates. Provides stronger security through bidirectional authentication.

**Explanation:** These terms are frequently used in Cilium and Kubernetes networking. Cluster Mesh is useful in hybrid/multi-cloud environments, CRDs are key to Kubernetes extensibility, FQDN policies are essential for access control to external services with dynamic IPs, and mTLS is important for secure service-to-service communication.

</details>

17. Write the command to query all Identities and their labels in the current cluster using Cilium CLI.

<details>

<summary>Show Answer</summary>

**Answer:**

```bash
# Query all Identities
cilium identity list

# Or query CiliumIdentity CRD using kubectl
kubectl get ciliumidentity -A

# Query detailed information for a specific Identity
cilium identity get <identity_id>

# Query detailed information in JSON format
kubectl get ciliumidentity <identity_id> -o json

# Filter Identities with specific labels
kubectl get ciliumidentity -o json | jq '.items[] | select(.metadata.labels."k8s:app" == "frontend")'

# Check Identity from Endpoints
cilium endpoint list
kubectl exec -n kube-system ds/cilium -- cilium endpoint list
```

**Explanation:** Cilium Identity is a numeric identifier generated based on a pod's label set. The `cilium identity list` command displays all Identities and their labels in the current cluster. CiliumIdentity is stored as a CRD, so it can also be queried with kubectl. Identity is the basis for network policies, and all pods with the same labels share the same Identity.

</details>

18. Write commands to query BPF Map contents to check service load balancing maps and connection tracking tables.

<details>

<summary>Show Answer</summary>

**Answer:**

```bash
# Query BPF maps from Cilium Agent pod

# Service map (Service -> Backend mapping)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list

# Backend map (backend pod information)
kubectl exec -n kube-system ds/cilium -- cilium bpf lb list --backends

# Connection Tracking table
kubectl exec -n kube-system ds/cilium -- cilium bpf ct list global

# NAT map (masquerading/SNAT information)
kubectl exec -n kube-system ds/cilium -- cilium bpf nat list

# Policy map (Identity-based policies)
kubectl exec -n kube-system ds/cilium -- cilium bpf policy get --all

# Endpoint map
kubectl exec -n kube-system ds/cilium -- cilium bpf endpoint list

# List all BPF maps
kubectl exec -n kube-system ds/cilium -- cilium bpf map list
```

**Explanation:** BPF Maps are core data structures used in Cilium's data plane. `cilium bpf lb list` shows service load balancing information, allowing you to check the mapping between service IP/port and backend pod IP/port. `cilium bpf ct list` shows the connection tracking table, where you can check the current active connection status. These commands are useful for network troubleshooting and performance analysis.

</details>

19. Write a CiliumNetworkPolicy using FQDN-based network policy that allows a pod to communicate only with `api.example.com` and `*.googleapis.com` domains externally.

<details>

<summary>Show Answer</summary>

**Answer:**

```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "fqdn-egress-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  # Allow DNS queries (required for FQDN policy to work)
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: UDP
      rules:
        dns:
        - matchPattern: "*"
  # Allow HTTPS traffic to specific FQDNs
  - toFQDNs:
    - matchName: "api.example.com"
    - matchPattern: "*.googleapis.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

**Explanation:** FQDN (Fully Qualified Domain Name) based policies control access to external services by domain name instead of IP address. For this policy to work, DNS queries must be allowed (first egress rule). In `toFQDNs`, `matchName` specifies an exact domain name, and `matchPattern` specifies pattern matching with wildcards. `*.googleapis.com` allows all Google API subdomains. FQDN policies are particularly useful for access control to external services with dynamic IPs.

</details>

20. Explain the role of Cilium Operator and its differences from Cilium Agent, and write commands to check the Operator's status.

<details>

<summary>Show Answer</summary>

**Answer:**

```bash
# Check Cilium Operator status
kubectl -n kube-system get deployment cilium-operator

# Check Operator pod status
kubectl -n kube-system get pods -l name=cilium-operator

# Check Operator logs
kubectl -n kube-system logs -l name=cilium-operator

# Check Operator in overall Cilium status
cilium status --verbose

# Check CiliumIdentity resources (managed by Operator)
kubectl get ciliumidentity -A

# Check CiliumEndpoint resources
kubectl get ciliumendpoint -A
```

**Cilium Operator vs Cilium Agent Role Comparison:**

| Component           | Run Location                        | Main Responsibilities                                                                                                                                              |
| ------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Cilium Agent**    | Each node (DaemonSet)               | <p>- eBPF program loading/management<br>- Network policy enforcement<br>- Local endpoint management<br>- Service load balancing<br>- Node-level IPAM</p>           |
| **Cilium Operator** | Cluster (Deployment, 1-2 instances) | <p>- CiliumIdentity CRD management<br>- Cluster-level IPAM<br>- CiliumEndpoint synchronization<br>- Garbage collection<br>- Cluster Mesh connection management</p> |

**Explanation:** Cilium Agent runs on each node and handles networking operations for that node. In contrast, Cilium Operator runs as a single instance (or 2 for HA) across the entire cluster and handles cluster-level coordination tasks. The Operator maintains Identity consistency across the cluster, cleans up unused resources, and manages cluster-level IPAM.

</details>

***

[Return to Learning Materials](../../../networking/cilium/glossary.md) | [Cilium Quiz List](https://github.com/Atom-oh/kubernetes-docs/blob/main/en/quizzes/networking/cilium/README.md)
