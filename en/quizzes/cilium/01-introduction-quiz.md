# Cilium Introduction and Basic Concepts Quiz

This quiz tests your understanding of Cilium's basic concepts, eBPF technology, architecture, key components, and CNI comparisons.

## Multiple Choice Questions

1. What is Cilium's core technology that provides a programmable data path within the kernel?
   - A) iptables
   - B) eBPF
   - C) VXLAN
   - D) IPsec

<details>

<summary>Show Answer</summary>

**Answer: B) eBPF**

**Explanation:**
eBPF (extended Berkeley Packet Filter) is a technology that allows programs to run safely within the Linux kernel. Cilium leverages eBPF to implement networking, security, and observability features at the kernel level. This provides much higher performance and flexibility than iptables-based solutions, and allows network policies to be applied dynamically without recompiling the kernel.
</details>

2. What layer does Cilium's network policy support?
   - A) L3 (Network Layer) only
   - B) L3-L4 (Network and Transport Layer)
   - C) L3-L7 (Network to Application Layer)
   - D) L2-L3 (Data Link and Network Layer)

<details>

<summary>Show Answer</summary>

**Answer: C) L3-L7 (Network to Application Layer)**

**Explanation:**
Cilium supports network policies from L3 (IP), L4 (TCP/UDP ports), and up to L7 (Application Layer). This means it can filter application-level traffic such as HTTP methods, paths, headers, gRPC methods, Kafka topics, and more. This API-aware networking is very useful for implementing fine-grained security policies in microservices architectures.
</details>

3. What tool provides network visibility and monitoring in Cilium?
   - A) Prometheus
   - B) Hubble
   - C) Grafana
   - D) Jaeger

<details>

<summary>Show Answer</summary>

**Answer: B) Hubble**

**Explanation:**
Hubble is Cilium's network observability layer that uses eBPF to monitor and analyze network flows in real-time. Hubble provides features such as service dependency map generation, network policy violation detection, HTTP/gRPC/DNS request tracing, and network latency measurement. Prometheus and Grafana are metric collection and visualization tools, while Jaeger is a distributed tracing tool.
</details>

4. Which Kubernetes component can Cilium's distributed load balancing feature replace?
   - A) CoreDNS
   - B) kube-proxy
   - C) etcd
   - D) kubelet

<details>

<summary>Show Answer</summary>

**Answer: B) kube-proxy**

**Explanation:**
Cilium provides eBPF-based service load balancing that can completely replace kube-proxy. While kube-proxy uses iptables or IPVS to route service traffic to backend pods, Cilium uses eBPF to provide higher performance and scalability. When Cilium's kube-proxy replacement mode is enabled, advanced features such as DSR (Direct Server Return), Maglev hashing, and socket-level load balancing are also available.
</details>

5. Which is NOT a node-to-node traffic encryption method supported by Cilium?
   - A) IPsec
   - B) WireGuard
   - C) TLS
   - D) Both are supported (A and B)

<details>

<summary>Show Answer</summary>

**Answer: C) TLS**

**Explanation:**
Cilium supports two methods for node-to-node traffic encryption: IPsec and WireGuard. IPsec is a traditional VPN protocol suite that is widely used, while WireGuard is a more modern, simpler, and faster VPN protocol. TLS is an application layer encryption protocol used for different purposes than Cilium's network layer encryption. In Cilium, you can choose either IPsec or WireGuard through configuration options to implement transparent network encryption.
</details>

6. What is Cilium's multi-cluster networking feature called?
   - A) Cluster Federation
   - B) Cluster Mesh
   - C) Multi-Cluster Network
   - D) Global Cluster

<details>

<summary>Show Answer</summary>

**Answer: B) Cluster Mesh**

**Explanation:**
Cluster Mesh is Cilium's multi-cluster networking feature that connects multiple Kubernetes clusters to operate as a single network. With Cluster Mesh, cross-cluster service discovery, load balancing, and network policy enforcement are possible. This feature is useful for hybrid cloud, multi-cloud, and disaster recovery scenarios, allowing pods in each cluster to directly access services in other clusters.
</details>

7. What technology does Cilium use to optimize packet processing performance?
   - A) DPDK
   - B) XDP (eXpress Data Path)
   - C) RDMA
   - D) SR-IOV

<details>

<summary>Show Answer</summary>

**Answer: B) XDP (eXpress Data Path)**

**Explanation:**
XDP (eXpress Data Path) is an eBPF-based technology that allows packet processing at the network driver level. XDP bypasses the kernel network stack to enable very high-performance packet processing (millions of packets per second). Cilium uses XDP to implement DDoS defense, high-performance load balancing, and packet filtering. DPDK, RDMA, and SR-IOV are also high-performance networking technologies, but Cilium's core technology is eBPF/XDP.
</details>

8. What is the minimum Linux kernel version supported by Cilium 1.18?
   - A) 3.10
   - B) 4.9
   - C) 4.19
   - D) 5.10

<details>

<summary>Show Answer</summary>

**Answer: C) 4.19**

**Explanation:**
Cilium 1.18 requires Linux kernel 4.19 or higher. This is because the eBPF features used by Cilium are fully supported in this version and above. Using a more recent kernel version (5.x and above) provides additional eBPF features and better performance. For example, advanced features such as XDP native mode, BPF-to-BPF function calls, and BTF (BPF Type Format) are better supported in newer kernels.
</details>

9. Which of the following CNI plugins is NOT eBPF-based?
   - A) Cilium
   - B) Calico (eBPF mode)
   - C) Flannel
   - D) Both are not eBPF-based (only C)

<details>

<summary>Show Answer</summary>

**Answer: C) Flannel**

**Explanation:**
Flannel is a simple overlay network solution using VXLAN or host-gw that does not use eBPF. In contrast, Cilium was designed from the ground up to be eBPF-based, and Calico also supports eBPF data plane mode in recent versions. Flannel is simple to configure and has low resource usage, but does not provide L7 network policies or advanced observability features.
</details>

10. What is the API version of Cilium Network Policy?
    - A) networking.k8s.io/v1
    - B) cilium.io/v1
    - C) cilium.io/v2
    - D) policy.cilium.io/v1

<details>

<summary>Show Answer</summary>

**Answer: C) cilium.io/v2**

**Explanation:**
CiliumNetworkPolicy uses the `cilium.io/v2` API version. This is a CRD (Custom Resource Definition) separate from the standard Kubernetes NetworkPolicy (`networking.k8s.io/v1`) to support Cilium's advanced features (L7 policies, DNS-based policies, endpoint selectors, etc.). Cilium also supports standard Kubernetes NetworkPolicy, but using CiliumNetworkPolicy allows for more fine-grained control.
</details>

## Short Answer Questions

11. What is the name of the core component that runs on each node in Cilium, loads eBPF programs, and implements network policies?

<details>

<summary>Show Answer</summary>

**Answer: Cilium Agent**

**Explanation:**
Cilium Agent is the core component of Cilium that runs as a DaemonSet on each Kubernetes node. The Agent's main responsibilities include loading and managing eBPF programs in the kernel, implementing and enforcing network policies, performing service load balancing, IP address management (IPAM), network endpoint management, metric and log collection, and communication with the API server. The Cilium Agent handles all networking operations on the local node.
</details>

12. What component in Cilium runs cluster-wide and performs tasks such as CRD synchronization and IP allocation coordination?

<details>

<summary>Show Answer</summary>

**Answer: Cilium Operator**

**Explanation:**
Cilium Operator is a Kubernetes Operator that runs as a single instance across the cluster. While the Agent handles local operations on each node, the Operator handles cluster-wide level operations. Key functions include CiliumIdentity and CiliumEndpoint CRD management, cluster-level IPAM management, inter-node CIDR allocation coordination, garbage collection (cleaning up unused resources), and Cluster Mesh connection management.
</details>

13. What CLI command is used to diagnose connectivity issues in Cilium?

<details>

<summary>Show Answer</summary>

**Answer: cilium connectivity test**

**Explanation:**
The `cilium connectivity test` command comprehensively tests network connectivity in a Cilium cluster. This command automatically tests various scenarios including pod-to-pod communication, service connectivity, external connectivity, and network policy enforcement. Test results are displayed as success/failure, with detailed information provided for failed tests. Additionally, you can check Cilium status with `cilium status` and monitor real-time traffic with `cilium monitor`.
</details>

14. What is the numeric identifier that represents a pod's security identity in Cilium?

<details>

<summary>Show Answer</summary>

**Answer: Identity (or Security Identity, Cilium Identity)**

**Explanation:**
Cilium Identity is a numeric identifier generated based on a pod's label set. All pods with the same labels share the same Identity. This approach allows network policies to be applied using Identity instead of IP addresses, so policies remain consistent even when pod IPs change. Identity-based policies are highly scalable and operate efficiently even in large clusters.
</details>

15. What is the abbreviation for the CNCF project that defines the standard interface between container runtimes and network plugins?

<details>

<summary>Show Answer</summary>

**Answer: CNI (Container Network Interface)**

**Explanation:**
CNI (Container Network Interface) is a CNCF project that defines the standard interface between container runtimes and network plugins. In Kubernetes, kubelet communicates with network plugins (Cilium, Calico, Flannel, etc.) through the CNI interface. CNI defines a standard API for network configuration when containers are added/removed, and various networking solutions can be integrated through a plugin architecture.
</details>

## Hands-on Questions

16. Write the command to install Cilium 1.18.0 on a Kubernetes cluster using the Cilium CLI.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Install Cilium CLI
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/latest/download/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz

# Install Cilium
cilium install --version 1.18.0

# Check installation status
cilium status

# Connectivity test
cilium connectivity test
```

**Explanation:**
The above commands first download and install the Cilium CLI binary to `/usr/local/bin`. Then the `cilium install` command installs the specified version of Cilium on the Kubernetes cluster. After installation, verify that all components are running properly with `cilium status`, and validate network connectivity with `cilium connectivity test`. Installation using Helm is also possible, which allows for more fine-grained configuration options.
</details>

17. Write a CiliumNetworkPolicy that allows only TCP traffic from the frontend pod to port 8080 of the backend pod.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "allow-frontend-backend"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "8080"
        protocol: TCP
```

**Explanation:**
This CiliumNetworkPolicy allows only TCP port 8080 ingress traffic from pods with the `app: frontend` label to pods with the `app: backend` label. The `endpointSelector` selects the target pods to which the policy applies, and the `ingress` section defines the allowed incoming traffic. `fromEndpoints` specifies the source pods, and `toPorts` specifies the allowed ports and protocols. When this policy is applied, traffic from other pods to the backend will be blocked.
</details>

18. Write the command to install Cilium with kube-proxy replacement mode enabled and the configuration to enable DSR (Direct Server Return) mode.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Install Cilium with kube-proxy replacement and DSR mode
cilium install --version 1.18.0 \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr

# Or installation using Helm
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set loadBalancer.mode=dsr \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=<API_SERVER_PORT>

# Verify installation
cilium status --verbose
```

**Explanation:**
The `kubeProxyReplacement=true` option configures Cilium to replace all kube-proxy functionality. In this mode, the existing kube-proxy must be removed or disabled. `loadBalancer.mode=dsr` enables Direct Server Return mode, so response traffic is sent directly to the client without going through the load balancer. DSR mode eliminates load balancer bottlenecks and saves bandwidth, which is particularly effective when handling large responses.
</details>

19. Write the commands to check Cilium's status, query specific pod endpoint information, and view applied network policies.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Check overall Cilium status
cilium status

# Check detailed status (all components)
cilium status --verbose

# List all endpoints
cilium endpoint list

# Get detailed information for a specific endpoint (using endpoint ID)
cilium endpoint get <endpoint_id>

# Query endpoint by pod name
kubectl exec -n kube-system <cilium-agent-pod> -- cilium endpoint list | grep <pod-name>

# Query applied network policies
cilium policy get

# Query policies applied to a specific endpoint
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# Real-time traffic monitoring
cilium monitor
```

**Explanation:**
`cilium status` shows the status of all components including Cilium Agent, Operator, and Hubble. `cilium endpoint list` lists all endpoints (pods) on the current node, where you can check each endpoint's ID, status, labels, and Identity. `cilium policy get` queries all network policies applied in the cluster. `cilium monitor` monitors network traffic in real-time to check packet flows, policy application, and dropped packets.
</details>

20. Write the commands to enable Hubble and observe network flows using the Hubble CLI.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Install Cilium with Hubble enabled
cilium install --version 1.18.0 \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true

# Enable Hubble on existing Cilium
cilium hubble enable

# Install Hubble CLI
export HUBBLE_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/hubble/master/stable.txt)
curl -L --remote-name-all https://github.com/cilium/hubble/releases/download/$HUBBLE_VERSION/hubble-linux-amd64.tar.gz
sudo tar xzvfC hubble-linux-amd64.tar.gz /usr/local/bin
rm hubble-linux-amd64.tar.gz

# Hubble port forwarding
cilium hubble port-forward &

# Observe network flows
hubble observe

# Observe flows in a specific namespace
hubble observe --namespace default

# Observe flows for a specific pod
hubble observe --pod default/frontend

# Filter HTTP traffic only
hubble observe --protocol http

# Observe only dropped packets
hubble observe --verdict DROPPED

# Access Hubble UI (separate terminal)
cilium hubble ui
```

**Explanation:**
Hubble is Cilium's observability layer that uses eBPF to monitor network flows in real-time. `hubble.enabled=true` enables Hubble, and `hubble.relay.enabled=true` enables Hubble Relay to collect flows from across the cluster. `hubble.ui.enabled=true` enables the web-based UI. The `hubble observe` command provides various filter options to filter traffic by specific namespace, pod, protocol, verdict, and more.
</details>

---

[Return to Learning Materials](../../cilium/01-introduction.md) | [Next Quiz: eBPF Basics](./02-ebpf-quiz.md)
