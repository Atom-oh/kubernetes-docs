# Cilium L2-L7 Networking and Load Balancing Quiz

This quiz tests your understanding of Cilium's L2-L7 networking features, load balancing architecture, masquerading, service mesh integration, and more.

## Multiple Choice Questions

1. In the OSI model, which layer do protocols like HTTP, gRPC, and DNS operate at?
   - A) L3 (Network Layer)
   - B) L4 (Transport Layer)
   - C) L5 (Session Layer)
   - D) L7 (Application Layer)

<details>

<summary>Show Answer</summary>

**Answer: D) L7 (Application Layer)**

**Explanation:**
In the OSI model, L7 (Application Layer) is the layer closest to the user, where application protocols like HTTP, HTTPS, gRPC, DNS, FTP, and Kafka operate. Cilium provides API-aware filtering at the L7 layer, enabling fine-grained network policies based on HTTP methods/paths/headers, gRPC methods, Kafka topics, and more. This is essential for fine-grained control of service-to-service communication in microservices architectures.
</details>

2. What is the main advantage of Cilium's DSR (Direct Server Return) mode?
   - A) It can hide client IPs
   - B) Response traffic bypasses the load balancer, improving performance
   - C) It encrypts all traffic
   - D) It automatically applies L7 policies

<details>

<summary>Show Answer</summary>

**Answer: B) Response traffic bypasses the load balancer, improving performance**

**Explanation:**
In DSR (Direct Server Return) mode, only client requests pass through the load balancer, while server responses bypass the load balancer and are sent directly to the client. This eliminates load balancer bottlenecks, saves network bandwidth, and reduces response latency. It is particularly effective when handling large responses (file downloads, streaming, etc.). DSR mode also preserves client IPs even behind external load balancers.
</details>

3. Which component provides L7 proxy functionality in Cilium?
   - A) kube-proxy
   - B) Hubble
   - C) Envoy
   - D) CoreDNS

<details>

<summary>Show Answer</summary>

**Answer: C) Envoy**

**Explanation:**
Cilium integrates Envoy proxy for L7 proxy functionality. When you define L7 rules (HTTP, gRPC, Kafka, DNS, etc.) in a CiliumNetworkPolicy, Cilium automatically deploys the Envoy proxy transparently without sidecars. Envoy provides HTTP/gRPC traffic handling, advanced load balancing, traffic splitting, and metrics collection. This approach reduces resource overhead since no separate sidecar proxies need to be deployed.
</details>

4. Which of the following is NOT a load balancing algorithm supported by Cilium?
   - A) Round Robin
   - B) Maglev Consistent Hashing
   - C) Source IP Hash
   - D) Weighted Response Time

<details>

<summary>Show Answer</summary>

**Answer: D) Weighted Response Time**

**Explanation:**
Cilium supports load balancing algorithms such as Round Robin, Least Connection, Source IP Hash, Random, and Maglev Consistent Hashing. Maglev is a consistent hashing algorithm developed by Google that maintains connection consistency even when backend servers are added or removed. Weighted Response Time is not a directly supported algorithm in Cilium. However, more advanced load balancing strategies can be implemented through the Envoy proxy.
</details>

5. Which is NOT an advantage of eBPF-based implementation for Cilium's masquerading?
   - A) Faster processing than iptables
   - B) Better scalability
   - C) Supported on all Linux kernel versions
   - D) Direct processing in kernel space

<details>

<summary>Show Answer</summary>

**Answer: C) Supported on all Linux kernel versions**

**Explanation:**
eBPF-based masquerading is faster than iptables, more scalable, and more efficient as it processes directly in kernel space. However, eBPF-based masquerading is only fully supported on recent Linux kernels (4.19 and above). On older kernels, you need to fall back to iptables-based masquerading. You can enable eBPF-based masquerading with the `enable-bpf-masquerade: true` option in Cilium settings.
</details>

6. What mode in Cilium completely replaces kube-proxy for Kubernetes services?
   - A) kube-proxy-replacement: partial
   - B) kube-proxy-replacement: strict
   - C) kube-proxy-replacement: hybrid
   - D) kube-proxy-replacement: disabled

<details>

<summary>Show Answer</summary>

**Answer: B) kube-proxy-replacement: strict**

**Explanation:**
The `kube-proxy-replacement: strict` setting makes Cilium completely replace all kube-proxy functionality. In this mode, Cilium handles all ClusterIP, NodePort, LoadBalancer, and ExternalIP services. In strict mode, kube-proxy must be removed or disabled. `partial` mode replaces only some features, and `disabled` disables kube-proxy replacement. Strict mode is required when using advanced features like DSR, Maglev hashing, and socket-level load balancing.
</details>

7. Which is NOT a condition that can be used to filter HTTP requests in Cilium L7 policies?
   - A) HTTP method (GET, POST, etc.)
   - B) URL path
   - C) HTTP headers
   - D) Request Body

<details>

<summary>Show Answer</summary>

**Answer: D) Request Body**

**Explanation:**
Cilium L7 HTTP policies can filter based on HTTP methods (GET, POST, PUT, DELETE, etc.), URL paths (with regex support), and HTTP headers (with regex support). However, inspecting the request body is not directly supported by Cilium due to significant performance overhead and complexity. If request body inspection is required, you should use a WAF (Web Application Firewall) or separate application-layer security solutions.
</details>

8. What is the main benefit of integrating Cilium with Istio?
   - A) It completely replaces all Istio functionality
   - B) It reduces sidecar overhead through eBPF-based data plane
   - C) It automatically disables mTLS
   - D) It implements service mesh without Istio

<details>

<summary>Show Answer</summary>

**Answer: B) It reduces sidecar overhead through eBPF-based data plane**

**Explanation:**
Integrating Cilium with Istio allows some Envoy sidecar functionality to be replaced by the eBPF-based data plane, reducing resource overhead. Cilium handles L3/L4 traffic processing and network policies with eBPF, forwarding only necessary L7 traffic to Envoy. This improves performance and reduces latency. However, Cilium does not replace all Istio functionality, and advanced Istio features like mTLS are still handled by Istio.
</details>

9. What is the benefit of socket-level load balancing in Cilium?
   - A) It translates service IP to backend IP in the kernel before packet processing
   - B) It automatically applies L7 policies
   - C) It only handles encrypted traffic
   - D) It requires an external load balancer

<details>

<summary>Show Answer</summary>

**Answer: A) It translates service IP to backend IP in the kernel before packet processing**

**Explanation:**
Socket-level load balancing translates service IPs to backend pod IPs at the connect() system call before packets are sent. This is much more efficient than traditional packet-based NAT (Network Address Translation). Benefits include reduced conntrack (connection tracking) overhead, source IP preservation, lower latency, and better scalability. Socket-level LB operates transparently from the application's perspective, making applications appear to communicate directly with backend pods.
</details>

10. What is the recommended best practice regarding IPv4 fragment handling in Cilium?
    - A) Always disable fragment tracking
    - B) Configure MTU consistently to prevent fragmentation
    - C) Block all fragments
    - D) Set fragment size to maximum

<details>

<summary>Show Answer</summary>

**Answer: B) Configure MTU consistently to prevent fragmentation**

**Explanation:**
IPv4 fragmentation can cause performance degradation and security issues, so it should be prevented when possible. To achieve this, configure the MTU (Maximum Transmission Unit) consistently across the network, and when using overlay networks (VXLAN, etc.), adjust the MTU to account for encapsulation overhead (approximately 50 bytes). Enabling Path MTU Discovery (PMTUD) can automatically detect the optimal MTU. Enabling fragment tracking (`enable-ipv4-fragment-tracking`) can prevent fragment-based attacks.
</details>

## Short Answer Questions

11. List 4 protocols supported by Cilium for L7 network policies.

<details>

<summary>Show Answer</summary>

**Answer:** HTTP, gRPC, Kafka, DNS

**Explanation:**
The main protocols supported by Cilium L7 policies are:
- **HTTP/HTTPS**: REST APIs and web traffic, with method/path/header-based filtering support
- **gRPC**: RPC communication between microservices, with service/method-based filtering support
- **Kafka**: Message queue protocol, with topic/clientID/API key-based filtering support
- **DNS**: DNS query and response filtering, with FQDN-based policy support
Additionally, custom protocols can be supported through Envoy filters.
</details>

12. What is the name of the mechanism in Cilium load balancers that checks the health of backend servers?

<details>

<summary>Show Answer</summary>

**Answer:** Health Check

**Explanation:**
Cilium load balancers support several health check mechanisms:
- **TCP health checks**: Verify port connectivity
- **HTTP health checks**: Verify HTTP response codes (200 OK, etc.)
- **Kubernetes Readiness/Liveness Probe integration**: Utilize pod status probe results
Unhealthy backends are automatically removed from the load balancing pool and re-added when recovered. This ensures high availability of services.
</details>

13. What is the name of the feature in Cilium that translates the source IP of external traffic to an internal IP?

<details>

<summary>Show Answer</summary>

**Answer:** Masquerading or SNAT (Source NAT)

**Explanation:**
Masquerading is the feature that translates the source IP of outbound traffic from pods inside the cluster to the node's IP. This is a form of SNAT (Source Network Address Translation). The purpose of masquerading is to hide internal cluster IPs from external networks and enable access to services outside the cluster. Cilium supports both iptables-based and eBPF-based masquerading, with eBPF-based providing higher performance.
</details>

14. What is the name of the hashing algorithm used for session persistence when Cilium replaces kube-proxy?

<details>

<summary>Show Answer</summary>

**Answer:** Maglev (Consistent Hashing)

**Explanation:**
Maglev is a consistent hashing algorithm developed by Google. When using Maglev in Cilium, most existing connections are maintained to the same backend even when backend servers are added or removed. This is important for applications that require session affinity. Maglev provides high load distribution uniformity and low connection redistribution rates, making it effective in large-scale load balancing environments.
</details>

15. What is the name and number of the layer in the OSI model where TCP and UDP protocols operate?

<details>

<summary>Show Answer</summary>

**Answer:** L4 (Transport Layer)

**Explanation:**
L4 (Transport Layer) is the 4th layer of the OSI model, responsible for end-to-end connection and reliability. TCP (Transmission Control Protocol) and UDP (User Datagram Protocol) operate at this layer. TCP is connection-oriented and provides reliable communication, while UDP is connectionless and fast but does not guarantee reliability. Cilium L4 policies can filter traffic based on port numbers and protocols (TCP/UDP).
</details>

## Hands-on Questions

16. Write a CiliumNetworkPolicy that allows only HTTP GET requests to the `/api/v1/users` path, and allows POST requests to the `/api/v1/data` path only when the `X-Auth-Token` header is present.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "l7-http-policy"
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: frontend
    toPorts:
    - ports:
      - port: "80"
        protocol: TCP
      rules:
        http:
        - method: "GET"
          path: "/api/v1/users"
        - method: "POST"
          path: "/api/v1/data"
          headers:
          - "X-Auth-Token: .*"
```

**Explanation:**
This CiliumNetworkPolicy implements fine-grained access control using L7 HTTP rules. The `rules.http` section defines two rules: the first allows GET method to the `/api/v1/users` path, and the second allows POST method to the `/api/v1/data` path only when the `X-Auth-Token` header is present. Header values can be specified with regex, so `.*` allows any value. When this policy is applied, Cilium automatically deploys the Envoy proxy transparently to inspect L7 traffic.
</details>

17. Write a Helm command to install Cilium in kube-proxy replacement mode with DSR mode and Maglev hashing enabled.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# Add Helm repo
helm repo add cilium https://helm.cilium.io/
helm repo update

# Install Cilium with kube-proxy replacement + DSR + Maglev settings
helm install cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=<API_SERVER_IP> \
  --set k8sServicePort=6443 \
  --set loadBalancer.mode=dsr \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set bpf.masquerade=true

# Disable existing kube-proxy (delete or scale down DaemonSet)
kubectl -n kube-system delete ds kube-proxy
# Or modify kube-proxy ConfigMap to disable

# Verify installation
cilium status --verbose
kubectl -n kube-system exec ds/cilium -- cilium status | grep KubeProxyReplacement
```

**Explanation:**
`kubeProxyReplacement=true` configures Cilium to replace kube-proxy functionality. `k8sServiceHost` and `k8sServicePort` specify the API server address (required to access the API server without kube-proxy). `loadBalancer.mode=dsr` enables Direct Server Return mode, and `loadBalancer.algorithm=maglev` uses Maglev consistent hashing. `maglev.tableSize` sets the hash table size (prime numbers recommended). `bpf.masquerade=true` enables eBPF-based masquerading.
</details>

18. Write a CiliumNetworkPolicy that applies L7 policies to Kafka traffic, allowing only produce operations to the `orders` topic and only consume operations to the `payments` topic.

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
apiVersion: "cilium.io/v2"
kind: CiliumNetworkPolicy
metadata:
  name: "kafka-l7-policy"
  namespace: messaging
spec:
  endpointSelector:
    matchLabels:
      app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: order-service
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "produce"
          topic: "orders"
  - fromEndpoints:
    - matchLabels:
        app: payment-processor
    toPorts:
    - ports:
      - port: "9092"
        protocol: TCP
      rules:
        kafka:
        - apiKey: "fetch"
          topic: "payments"
```

**Explanation:**
This CiliumNetworkPolicy implements fine-grained access control using Kafka L7 rules. The first ingress rule allows `order-service` pods to only perform produce (`apiKey: produce`) operations to the `orders` topic. The second rule allows `payment-processor` pods to only perform consume (`apiKey: fetch`) operations to the `payments` topic. Kafka API keys include `produce`, `fetch`, `metadata`, `offsets`, etc., and you can also add `clientID` to allow only specific clients.
</details>

19. Write a configuration to enable eBPF-based masquerading in Cilium while excluding masquerading for a specific CIDR range (10.0.0.0/8).

<details>

<summary>Show Answer</summary>

**Answer:**
```yaml
# ConfigMap settings
apiVersion: v1
kind: ConfigMap
metadata:
  name: cilium-config
  namespace: kube-system
data:
  enable-ipv4-masquerade: "true"
  enable-bpf-masquerade: "true"
  ipv4-native-routing-cidr: "10.0.0.0/8"
  enable-ipv6-masquerade: "false"
```

```bash
# Install/upgrade using Helm
helm upgrade cilium cilium/cilium --version 1.18.0 \
  --namespace kube-system \
  --set ipv4NativeRoutingCIDR=10.0.0.0/8 \
  --set bpf.masquerade=true \
  --set enableIPv4Masquerade=true

# Verify settings
kubectl -n kube-system exec ds/cilium -- cilium status --verbose | grep -i masquerade

# Check masquerading rules
kubectl -n kube-system exec ds/cilium -- cilium bpf nat list
```

**Explanation:**
`enable-bpf-masquerade: true` enables eBPF-based masquerading. `ipv4-native-routing-cidr: 10.0.0.0/8` configures traffic to this CIDR range to use native routing without masquerading. This is useful when source IP needs to be preserved for intra-cluster communication or intra-VPC communication. If the cluster pod CIDR and service CIDR are included in this range, masquerading will not be applied to internal traffic.
</details>

20. Write the commands to diagnose issues when L7 policies are not working as expected in Cilium. Include Envoy proxy status, policy application status, and real-time traffic monitoring.

<details>

<summary>Show Answer</summary>

**Answer:**
```bash
# 1. Check overall Cilium status
cilium status --verbose

# 2. Check Envoy proxy status
kubectl -n kube-system exec ds/cilium -- cilium status | grep -i proxy
kubectl -n kube-system exec ds/cilium -- cilium bpf proxy list

# 3. Check policy application status
cilium policy get
kubectl get cnp -A -o wide
kubectl get ccnp -A -o wide

# 4. Check policy status for a specific endpoint
cilium endpoint list
cilium endpoint get <endpoint_id> -o json | jq '.status.policy'

# 5. Real-time traffic monitoring (including L7)
cilium monitor --type l7
cilium monitor --type policy-verdict
cilium monitor --type drop

# 6. Observe L7 flows through Hubble
hubble observe --protocol http
hubble observe --verdict DROPPED
hubble observe --pod <namespace>/<pod-name>

# 7. Check Envoy logs
kubectl -n kube-system logs ds/cilium | grep -i envoy
kubectl -n kube-system logs ds/cilium | grep -i proxy

# 8. Regenerate endpoint (reapply policy)
kubectl -n kube-system exec ds/cilium -- cilium endpoint regenerate <endpoint_id>

# 9. Network policy troubleshooting
cilium policy trace --src-identity <src_id> --dst-identity <dst_id> --dport <port>
```

**Explanation:**
A systematic approach is needed when troubleshooting L7 policy issues. First, check the overall system status with `cilium status` and verify that the Envoy proxy is running normally. Check applied policies with `cilium policy get` and verify that policies are correctly applied to specific pods with `cilium endpoint get`. Monitor real-time traffic and policy verdicts with `cilium monitor` and `hubble observe`. The `policy trace` command simulates the policy decision process for specific traffic flows.
</details>

---

[Return to Learning Materials](../../../networking/cilium/05-l2-l7-networking.md) | [Next Quiz: Security and Visibility](./06-security-visibility-quiz.md)
