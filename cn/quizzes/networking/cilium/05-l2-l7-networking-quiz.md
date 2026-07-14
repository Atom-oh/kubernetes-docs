# Cilium L2-L7 网络与负载均衡测验

本测验用于测试你对 Cilium 的 L2-L7 网络功能、负载均衡架构、伪装（masquerading）、Service Mesh 集成等方面的理解。

## 选择题

1. 在 OSI 模型中，HTTP、gRPC 和 DNS 等协议工作在哪一层？
   - A) L3（网络层）
   - B) L4（传输层）
   - C) L5（会话层）
   - D) L7（应用层）

<details>

<summary>显示答案</summary>

**答案：D) L7（应用层）**

**说明：**
在 OSI 模型中，L7（应用层）是最接近用户的一层，HTTP、HTTPS、gRPC、DNS、FTP 和 Kafka 等应用协议都在此层工作。Cilium 在 L7 层提供 API 感知过滤，可基于 HTTP 方法/路径/请求头、gRPC 方法、Kafka 主题等实现细粒度的网络策略。这对于在微服务架构中精细控制服务间通信至关重要。
</details>

2. Cilium 的 DSR（Direct Server Return）模式的主要优势是什么？
   - A) 可以隐藏客户端 IP
   - B) 响应流量绕过负载均衡器，从而提升性能
   - C) 对所有流量进行加密
   - D) 自动应用 L7 策略

<details>

<summary>显示答案</summary>

**答案：B) 响应流量绕过负载均衡器，从而提升性能**

**说明：**
在 DSR（Direct Server Return）模式下，只有客户端请求经过负载均衡器，而服务器响应会绕过负载均衡器直接发送给客户端。这消除了负载均衡器瓶颈，节省网络带宽，并降低响应延迟。它在处理大型响应（文件下载、流式传输等）时尤其有效。即使在外部负载均衡器之后，DSR 模式也能保留客户端 IP。
</details>

3. Cilium 中哪个组件提供 L7 代理功能？
   - A) kube-proxy
   - B) Hubble
   - C) Envoy
   - D) CoreDNS

<details>

<summary>显示答案</summary>

**答案：C) Envoy**

**说明：**
Cilium 集成 Envoy 代理来提供 L7 代理功能。当你在 CiliumNetworkPolicy 中定义 L7 规则（HTTP、gRPC、Kafka、DNS 等）时，Cilium 会自动以透明方式部署 Envoy 代理，无需 sidecar。Envoy 提供 HTTP/gRPC 流量处理、高级负载均衡、流量拆分和指标收集。由于不需要部署独立的 sidecar 代理，这种方法可降低资源开销。
</details>

4. 以下哪项不是 Cilium 支持的负载均衡算法？
   - A) Round Robin
   - B) Maglev Consistent Hashing
   - C) Source IP Hash
   - D) Weighted Response Time

<details>

<summary>显示答案</summary>

**答案：D) Weighted Response Time**

**说明：**
Cilium 支持 Round Robin、Least Connection、Source IP Hash、Random 和 Maglev Consistent Hashing 等负载均衡算法。Maglev 是 Google 开发的一种一致性哈希算法，即使添加或移除后端服务器也能保持连接一致性。Weighted Response Time 不是 Cilium 直接支持的算法。不过，可以通过 Envoy 代理实现更高级的负载均衡策略。
</details>

5. 以下哪项不是 Cilium 基于 eBPF 实现伪装的优势？
   - A) 处理速度快于 iptables
   - B) 更好的可扩展性
   - C) 支持所有 Linux kernel 版本
   - D) 在 kernel space 中直接处理

<details>

<summary>显示答案</summary>

**答案：C) 支持所有 Linux kernel 版本**

**说明：**
基于 eBPF 的伪装比 iptables 更快、可扩展性更好，并且由于直接在 kernel space 中处理而更加高效。但是，基于 eBPF 的伪装仅在较新的 Linux kernel（4.19 及以上）中得到完全支持。在较旧的 kernel 上，你需要回退到基于 iptables 的伪装。你可以在 Cilium 设置中使用 `enable-bpf-masquerade: true` 选项启用基于 eBPF 的伪装。
</details>

6. Cilium 中哪种模式可完全替代 Kubernetes Service 的 kube-proxy？
   - A) kube-proxy-replacement: partial
   - B) kube-proxy-replacement: strict
   - C) kube-proxy-replacement: hybrid
   - D) kube-proxy-replacement: disabled

<details>

<summary>显示答案</summary>

**答案：B) kube-proxy-replacement: strict**

**说明：**
`kube-proxy-replacement: strict` 设置使 Cilium 完全替代所有 kube-proxy 功能。在此模式下，Cilium 处理所有 ClusterIP、NodePort、LoadBalancer 和 ExternalIP Service。严格模式下，必须移除或禁用 kube-proxy。`partial` 模式仅替代部分功能，而 `disabled` 会禁用 kube-proxy 替代功能。使用 DSR、Maglev 哈希和 socket-level load balancing 等高级功能时，需要严格模式。
</details>

7. 以下哪项不能用于在 Cilium L7 策略中过滤 HTTP 请求？
   - A) HTTP 方法（GET、POST 等）
   - B) URL 路径
   - C) HTTP 请求头
   - D) 请求正文

<details>

<summary>显示答案</summary>

**答案：D) 请求正文**

**说明：**
Cilium L7 HTTP 策略可基于 HTTP 方法（GET、POST、PUT、DELETE 等）、URL 路径（支持正则表达式）和 HTTP 请求头（支持正则表达式）进行过滤。但是，由于显著的性能开销和复杂性，Cilium 不直接支持检查请求正文。如果需要检查请求正文，应使用 WAF（Web Application Firewall）或独立的应用层安全解决方案。
</details>

8. 将 Cilium 与 Istio 集成的主要好处是什么？
   - A) 完全替代所有 Istio 功能
   - B) 通过基于 eBPF 的数据平面减少 sidecar 开销
   - C) 自动禁用 mTLS
   - D) 无需 Istio 即可实现 Service Mesh

<details>

<summary>显示答案</summary>

**答案：B) 通过基于 eBPF 的数据平面减少 sidecar 开销**

**说明：**
将 Cilium 与 Istio 集成后，可以通过基于 eBPF 的数据平面替代部分 Envoy sidecar 功能，从而降低资源开销。Cilium 使用 eBPF 处理 L3/L4 流量和网络策略，只将必要的 L7 流量转发给 Envoy。这可提升性能并降低延迟。但是，Cilium 不会替代所有 Istio 功能，mTLS 等高级 Istio 功能仍由 Istio 处理。
</details>

9. Cilium 中 socket-level load balancing 的好处是什么？
   - A) 在数据包处理前，在 kernel 中将 Service IP 转换为后端 IP
   - B) 自动应用 L7 策略
   - C) 仅处理加密流量
   - D) 需要外部负载均衡器

<details>

<summary>显示答案</summary>

**答案：A) 在数据包处理前，在 kernel 中将 Service IP 转换为后端 IP**

**说明：**
Socket-level load balancing 会在发送数据包之前的 connect() 系统调用中，将 Service IP 转换为后端 Pod IP。这比传统的基于数据包的 NAT（Network Address Translation）高效得多。其优势包括减少 conntrack（连接跟踪）开销、保留源 IP、降低延迟以及更好的可扩展性。Socket-level LB 从应用程序的角度来看是透明的，使应用程序看起来像是直接与后端 Pod 通信。
</details>

10. 关于 Cilium 中 IPv4 分片处理，推荐的最佳实践是什么？
    - A) 始终禁用分片跟踪
    - B) 一致地配置 MTU 以防止分片
    - C) 阻止所有分片
    - D) 将分片大小设为最大值

<details>

<summary>显示答案</summary>

**答案：B) 一致地配置 MTU 以防止分片**

**说明：**
IPv4 分片可能导致性能下降和安全问题，因此应尽可能避免。为此，应在整个网络中一致地配置 MTU（Maximum Transmission Unit）；使用 overlay network（VXLAN 等）时，应调整 MTU 以计入封装开销（约 50 字节）。启用 Path MTU Discovery（PMTUD）可以自动检测最佳 MTU。启用分片跟踪（`enable-ipv4-fragment-tracking`）可防止基于分片的攻击。
</details>

## 简答题

11. 列出 Cilium 支持用于 L7 网络策略的 4 种协议。

<details>

<summary>显示答案</summary>

**答案：** HTTP、gRPC、Kafka、DNS

**说明：**
Cilium L7 策略支持的主要协议包括：
- **HTTP/HTTPS**：REST API 和 Web 流量，支持基于方法/路径/请求头的过滤
- **gRPC**：微服务之间的 RPC 通信，支持基于 Service/方法的过滤
- **Kafka**：消息队列协议，支持基于主题/clientID/API key 的过滤
- **DNS**：DNS 查询和响应过滤，支持基于 FQDN 的策略
此外，还可以通过 Envoy filter 支持自定义协议。
</details>

12. Cilium 负载均衡器中用于检查后端服务器健康状况的机制叫什么？

<details>

<summary>显示答案</summary>

**答案：** Health Check

**说明：**
Cilium 负载均衡器支持多种健康检查机制：
- **TCP health checks**：验证端口连通性
- **HTTP health checks**：验证 HTTP 响应代码（200 OK 等）
- **Kubernetes Readiness/Liveness Probe 集成**：利用 Pod 状态探针结果
不健康的后端会自动从负载均衡池中移除，并在恢复后重新添加。这可确保 Service 的高可用性。
</details>

13. Cilium 中将外部流量的源 IP 转换为内部 IP 的功能叫什么？

<details>

<summary>显示答案</summary>

**答案：** Masquerading 或 SNAT（Source NAT）

**说明：**
Masquerading 是将集群内 Pod 发出的出站流量的源 IP 转换为节点 IP 的功能。这是 SNAT（Source Network Address Translation）的一种形式。伪装的目的是向外部网络隐藏内部集群 IP，并允许访问集群外的 Service。Cilium 同时支持基于 iptables 和基于 eBPF 的伪装，其中基于 eBPF 的伪装性能更高。
</details>

14. 当 Cilium 替代 kube-proxy 时，用于会话持久性的哈希算法叫什么？

<details>

<summary>显示答案</summary>

**答案：** Maglev（一致性哈希）

**说明：**
Maglev 是 Google 开发的一种一致性哈希算法。在 Cilium 中使用 Maglev 时，即使添加或移除后端服务器，大多数现有连接仍会保持连接到同一后端。这对于需要 session affinity 的应用程序非常重要。Maglev 具有较高的负载分布均匀性和较低的连接重新分配率，因此在大规模负载均衡环境中非常有效。
</details>

15. TCP 和 UDP 协议在 OSI 模型中工作在哪一层？请给出该层的名称和编号。

<details>

<summary>显示答案</summary>

**答案：** L4（传输层）

**说明：**
L4（传输层）是 OSI 模型的第 4 层，负责端到端连接和可靠性。TCP（Transmission Control Protocol）和 UDP（User Datagram Protocol）在这一层工作。TCP 是面向连接的，提供可靠通信；UDP 是无连接的，速度快但不保证可靠性。Cilium L4 策略可基于端口号和协议（TCP/UDP）过滤流量。
</details>

## 实操题

16. 编写一个 CiliumNetworkPolicy：仅允许访问 `/api/v1/users` 路径的 HTTP GET 请求，并且仅当存在 `X-Auth-Token` 请求头时，才允许访问 `/api/v1/data` 路径的 POST 请求。

<details>

<summary>显示答案</summary>

**答案：**
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

**说明：**
此 CiliumNetworkPolicy 使用 L7 HTTP 规则实现细粒度访问控制。`rules.http` 部分定义了两条规则：第一条允许对 `/api/v1/users` 路径使用 GET 方法，第二条仅在存在 `X-Auth-Token` 请求头时允许对 `/api/v1/data` 路径使用 POST 方法。请求头值可以使用正则表达式指定，因此 `.*` 允许任何值。应用此策略时，Cilium 会自动以透明方式部署 Envoy 代理来检查 L7 流量。
</details>

17. 编写一条 Helm 命令，以启用 DSR 模式和 Maglev 哈希的 kube-proxy 替代模式安装 Cilium。

<details>

<summary>显示答案</summary>

**答案：**
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

**说明：**
`kubeProxyReplacement=true` 将 Cilium 配置为替代 kube-proxy 功能。`k8sServiceHost` 和 `k8sServicePort` 指定 API server 地址（无需 kube-proxy 即可访问 API server 时必需）。`loadBalancer.mode=dsr` 启用 Direct Server Return 模式，`loadBalancer.algorithm=maglev` 使用 Maglev 一致性哈希。`maglev.tableSize` 设置哈希表大小（建议使用质数）。`bpf.masquerade=true` 启用基于 eBPF 的伪装。
</details>

18. 编写一个 CiliumNetworkPolicy，对 Kafka 流量应用 L7 策略：仅允许向 `orders` 主题执行 produce 操作，并且仅允许从 `payments` 主题执行 consume 操作。

<details>

<summary>显示答案</summary>

**答案：**
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

**说明：**
此 CiliumNetworkPolicy 使用 Kafka L7 规则实现细粒度访问控制。第一条 ingress 规则仅允许 `order-service` Pod 对 `orders` 主题执行 produce（`apiKey: produce`）操作。第二条规则仅允许 `payment-processor` Pod 对 `payments` 主题执行 consume（`apiKey: fetch`）操作。Kafka API key 包括 `produce`、`fetch`、`metadata`、`offsets` 等；还可以添加 `clientID`，以仅允许特定客户端。
</details>

19. 编写一个配置，在 Cilium 中启用基于 eBPF 的伪装，同时对特定 CIDR 范围（10.0.0.0/8）排除伪装。

<details>

<summary>显示答案</summary>

**答案：**
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

**说明：**
`enable-bpf-masquerade: true` 启用基于 eBPF 的伪装。`ipv4-native-routing-cidr: 10.0.0.0/8` 将到此 CIDR 范围的流量配置为使用原生路由而不进行伪装。当需要为集群内通信或 VPC 内通信保留源 IP 时，这非常有用。如果集群 Pod CIDR 和 Service CIDR 包含在此范围内，则不会对内部流量应用伪装。
</details>

20. 编写在 Cilium 中诊断 L7 策略未按预期工作的问题所需的命令。应包括 Envoy 代理状态、策略应用状态和实时流量监控。

<details>

<summary>显示答案</summary>

**答案：**
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

**说明：**
排查 L7 策略问题需要采用系统化方法。首先，使用 `cilium status` 检查整体系统状态，并确认 Envoy 代理正常运行。使用 `cilium policy get` 检查已应用的策略，并使用 `cilium endpoint get` 验证策略是否正确应用到特定 Pod。使用 `cilium monitor` 和 `hubble observe` 监控实时流量和策略判定。`policy trace` 命令会模拟特定流量流的策略决策过程。
</details>

---

[返回学习资料](../../../networking/cilium/05-l2-l7-networking.md) | [下一测验：安全与可观测性](./06-security-visibility-quiz.md)
