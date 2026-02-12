# Cilium Quiz

This quiz tests your understanding of Cilium's eBPF-based networking, security policies, Hubble observability, service mesh, and Amazon EKS integration.

## Multiple Choice Questions

1. What is the core Linux kernel technology that Cilium uses to provide high-performance networking?
   - A) iptables
   - B) netfilter
   - C) eBPF (extended Berkeley Packet Filter)
   - D) nftables

<details>

<summary>Show Answer</summary>

**Answer: C) eBPF (extended Berkeley Packet Filter)**

**Explanation:**
Cilium is based on eBPF (extended Berkeley Packet Filter) technology. eBPF operates like a sandboxed virtual machine within the Linux kernel, allowing programs to run safely inside the kernel without modifying kernel code. This enables network packet processing, policy enforcement, and monitoring to be performed much more efficiently than traditional iptables-based approaches.
</details>

2. What mode in Cilium completely replaces the existing kube-proxy?
   - A) kubeProxyReplacement=partial
   - B) kubeProxyReplacement=strict
   - C) kubeProxyReplacement=disabled
   - D) kubeProxyReplacement=full

<details>

<summary>Show Answer</summary>

**Answer: B) kubeProxyReplacement=strict**

**Explanation:**
Cilium can replace kube-proxy by handling service load balancing with eBPF. `kubeProxyReplacement=strict` mode completely replaces kube-proxy with Cilium handling all service load balancing. In this mode, kube-proxy should not be running, and Cilium handles all ClusterIP, NodePort, and LoadBalancer services. `partial` mode only replaces some features.
</details>

3. What is the observability tool in Cilium for visualizing and monitoring network flows?
   - A) Prometheus
   - B) Grafana
   - C) Hubble
   - D) Jaeger

<details>

<summary>Show Answer</summary>

**Answer: C) Hubble**

**Explanation:**
Hubble is Cilium's native observability layer that enables visualization and analysis of network flow data collected through eBPF. Hubble provides CLI, UI, and Relay components supporting real-time network flow observation, service map visualization, and policy decision monitoring. While Prometheus and Grafana are metrics collection and visualization tools, Hubble is a Cilium-specific observability solution.
</details>

4. What CRD is used in Cilium network policies to control L7 (application layer) HTTP traffic?
   - A) NetworkPolicy
   - B) CiliumNetworkPolicy
   - C) IngressPolicy
   - D) HTTPPolicy

<details>

<summary>Show Answer</summary>

**Answer: B) CiliumNetworkPolicy**

**Explanation:**
CiliumNetworkPolicy is Cilium's custom resource that supports much more powerful L3-L7 network policies than standard Kubernetes NetworkPolicy. It enables detailed application-layer traffic control including HTTP methods, paths, and headers. Standard NetworkPolicy only supports L3/L4 (IP, port) level policies, while CiliumNetworkPolicy supports various L7 protocols including HTTP, gRPC, and Kafka.
</details>

5. What protocols does Cilium support for node-to-node traffic encryption?
   - A) SSL/TLS only
   - B) IPsec and WireGuard
   - C) SSH tunneling only
   - D) mTLS only

<details>

<summary>Show Answer</summary>

**Answer: B) IPsec and WireGuard**

**Explanation:**
Cilium supports both IPsec and WireGuard protocols for transparent node-to-node encryption. WireGuard is a modern encryption protocol offering better performance, while IPsec provides broader compatibility. Encryption can be enabled with `--set encryption.enabled=true --set encryption.type=wireguard` (or ipsec) settings. This applies encryption at the network layer without application modifications.
</details>

6. What field is used in Cilium policies to allow egress traffic only to specific FQDNs (domain names)?
   - A) toEndpoints
   - B) toEntities
   - C) toFQDNs
   - D) toDomains

<details>

<summary>Show Answer</summary>

**Answer: C) toFQDNs**

**Explanation:**
In CiliumNetworkPolicy, the `toFQDNs` field allows egress traffic to specific domain names. Use `matchName` to specify exact domains or `matchPattern` for wildcard patterns. For example, `matchPattern: "*.amazonaws.com"` allows traffic to all AWS services. This feature enables DNS-based access control, making it easy to manage policies for external services with dynamic IPs.
</details>

7. What IPAM setting is required when installing Cilium in AWS ENI mode on Amazon EKS?
   - A) ipam.mode=kubernetes
   - B) ipam.mode=cluster-pool
   - C) ipam.mode=eni
   - D) ipam.mode=aws

<details>

<summary>Show Answer</summary>

**Answer: C) ipam.mode=eni**

**Explanation:**
When using Cilium on Amazon EKS, the `ipam.mode=eni` setting leverages AWS Elastic Network Interface (ENI) for native AWS networking performance. In this mode, pod IPs are allocated directly from VPC subnets, providing full integration with AWS networking. Also set `eni.enabled=true` and `tunnel=disabled` together to use direct routing without overlay networking.
</details>

8. What CRD is used in Cilium to define network policies that apply cluster-wide?
   - A) CiliumGlobalPolicy
   - B) CiliumClusterwideNetworkPolicy
   - C) CiliumClusterPolicy
   - D) ClusterNetworkPolicy

<details>

<summary>Show Answer</summary>

**Answer: B) CiliumClusterwideNetworkPolicy**

**Explanation:**
CiliumClusterwideNetworkPolicy (CCNP) is a CRD for defining network policies that apply cluster-wide regardless of namespace. It enables implementation of cluster-level default deny policies, DNS allow policies, or global access controls for specific entities (e.g., world, cluster). Regular CiliumNetworkPolicy only applies to specific namespaces, while CCNP applies to all namespaces.
</details>

## Short Answer Questions

9. What type of eBPF program in Cilium performs initial processing (DDoS defense, load balancing, etc.) in kernel space as soon as packets arrive at network interfaces?

<details>

<summary>Show Answer</summary>

**Answer: XDP (eXpress Data Path)**

**Explanation:**
XDP (eXpress Data Path) is a type of eBPF program that processes packets at the network interface driver level. Since packets are processed before reaching the kernel networking stack, it provides very low latency and high throughput. Cilium uses XDP for DDoS attack defense, high-speed load balancing, and packet filtering. Enable XDP acceleration with `--set loadBalancer.acceleration=native`.
</details>

10. What feature in Cilium connects multiple Kubernetes clusters to enable direct pod-to-pod communication?

<details>

<summary>Show Answer</summary>

**Answer: Cluster Mesh**

**Explanation:**
Cluster Mesh is Cilium's multi-cluster feature that connects multiple Kubernetes clusters to enable cross-cluster pod-to-pod communication, service discovery, and network policy enforcement. Enable it on each cluster with `cilium clustermesh enable` and connect clusters with `cilium clustermesh connect`. This provides a consistent networking experience in hybrid cloud or multi-region environments.
</details>

11. What is the name of the official command-line tool for Cilium installation, status verification, and connectivity testing?

<details>

<summary>Show Answer</summary>

**Answer: Cilium CLI (cilium command)**

**Explanation:**
Cilium CLI is Cilium's official command-line tool that provides commands like `cilium install`, `cilium status`, and `cilium connectivity test`. It can perform all tasks needed for Cilium operations including installation, upgrades, status checks, connectivity testing, and Hubble management. For example, check detailed status with `cilium status --verbose` and verify network connectivity with `cilium connectivity test`.
</details>

12. What feature in Cilium provides L7 traffic management (traffic splitting, canary deployments, etc.) without sidecar proxies?

<details>

<summary>Show Answer</summary>

**Answer: Cilium Service Mesh (sidecar-less service mesh)**

**Explanation:**
Cilium Service Mesh leverages eBPF to provide L7 traffic management without sidecar proxies, unlike existing service mesh solutions like Istio and Linkerd. This enables service mesh features like HTTP routing, traffic splitting, canary deployments, and mTLS with lower resource overhead and latency. Enable with `--set serviceMesh.enabled=true`.
</details>

## Hands-on Questions

13. Write a Cilium L7 network policy that allows only GET /api/v1/products requests from pods with frontend label to port 8080 on pods with backend label.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-frontend-to-backend-api
  namespace: app
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
      rules:
        http:
        - method: "GET"
          path: "/api/v1/products"
```

**Explanation:**
CiliumNetworkPolicy is used to control L7 HTTP traffic. `endpointSelector` selects the target pods (backend) where the policy applies. `fromEndpoints` specifies source pods (frontend), and `toPorts` defines port and HTTP rules. In `rules.http`, specify allowed HTTP methods and paths. This policy restricts frontend pods to only making GET requests to the /api/v1/products path on backend pods.
</details>

14. Write commands to enable Hubble and observe denied traffic in real-time from a specific namespace.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# 1. Enable Hubble with UI
cilium hubble enable --ui

# 2. Check Hubble status
cilium hubble status

# 3. Hubble port forwarding (in separate terminal)
cilium hubble port-forward &

# 4. Observe denied traffic in specific namespace
hubble observe --namespace app --verdict DROPPED

# 5. Real-time observation with more detail
hubble observe --namespace app --verdict DROPPED --follow

# 6. Filter and observe HTTP protocol traffic only
hubble observe --namespace app --verdict DROPPED --protocol http

# 7. Observe denied traffic from specific pod
hubble observe --from-pod app/frontend --verdict DROPPED
```

**Explanation:**
Enabling Hubble allows you to observe all network flows processed by Cilium. The `--verdict DROPPED` flag filters only traffic denied by network policies. Enable real-time streaming with `--follow`, and use `--namespace`, `--protocol`, `--from-pod` for detailed filtering. This helps debug whether network policies are working as expected and what traffic is being blocked.
</details>

15. Write commands to remove the existing AWS VPC CNI and install Cilium in ENI mode on an Amazon EKS cluster.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# 1. Remove existing AWS VPC CNI DaemonSet
kubectl delete daemonset -n kube-system aws-node

# 2. Install Cilium CLI (if not already installed)
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
curl -L --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin

# 3. Install Cilium in ENI mode
cilium install \
  --set eni.enabled=true \
  --set ipam.mode=eni \
  --set egressMasqueradeInterfaces=eth0 \
  --set tunnel=disabled \
  --set kubeProxyReplacement=strict

# 4. Verify installation status
cilium status --wait

# 5. Run connectivity test
cilium connectivity test
```

**Explanation:**
First remove the existing AWS VPC CNI (aws-node DaemonSet). Then install Cilium in ENI mode where `eni.enabled=true` enables ENI integration and `ipam.mode=eni` uses AWS ENI IPAM. `tunnel=disabled` disables overlay networking to use native AWS routing. You can also replace kube-proxy with `kubeProxyReplacement=strict`. After installation, verify network connectivity with `cilium connectivity test`.
</details>

---

**Scoring:**
- 13-15 correct: Excellent (Cilium expert level)
- 10-12 correct: Good (practical application capable)
- 7-9 correct: Average (additional learning recommended)
- 0-6 correct: Insufficient (basic concepts review needed)

[Return to Learning Materials](../../tools/04-cilium.md)
