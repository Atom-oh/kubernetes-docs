# 术语测验

> **复习基线**：Cilium 1.20.3。
> **上次审核日期**：2026年10月16日。

本测验用于检验你对 Cilium、eBPF、Kubernetes 和网络相关关键术语与概念的理解。

## 选择题

1. eBPF 的全称是什么？

   - A) 增强型 Berkeley 数据包过滤器
   - B) 扩展型 Berkeley 数据包过滤器
   - C) 嵌入式 BPF 过滤器
   - D) 外部 Berkeley 协议过滤器

<details>

<summary>显示答案</summary>

**答案：B) 扩展型 Berkeley 数据包过滤器**

**说明**：eBPF 扩展了经典 BPF，可用于网络、跟踪和其他内核钩子。验证器会检查程序属性；但这并不意味着内核或验证器能够免受实现缺陷的影响。

</details>

2. 在 Cilium 中，应用网络策略的基本单元是什么？

   - A) Pod
   - B) 节点
   - C) Endpoint
   - D) Service

<details>

<summary>显示答案</summary>

**答案：C) Endpoint**

**说明**：Cilium Endpoint 通常对应一个受管理的 Pod。其 Endpoint ID 在本地 Agent 范围内有效；安全身份可以共享。在所属 Agent 中使用 `cilium-dbg endpoint list`。

</details>

3. 在支持该功能的网络设备上，原生 XDP 在哪里执行？

   - A) L7 协议分析
   - B) 网络驱动程序级别的数据包处理
   - C) TLS 加密
   - D) DNS 解析

<details>

<summary>显示答案</summary>

**答案：B) 网络驱动程序级别的数据包处理**

**说明**：原生 XDP 在支持该功能的驱动程序的接收路径上执行。PASS 会继续进入协议栈；DROP、TX 和 REDIRECT 则会执行其他操作。通用模式和卸载模式有所不同。Cilium 的 Service 加速有条件限制，并不保证适用于所有情况的数据包速率，也不保证内置 DDoS 防护。

</details>

4. Cilium 的网络可观测性平台叫什么？

   - A) Prometheus
   - B) Grafana
   - C) Hubble
   - D) Jaeger

<details>

<summary>显示答案</summary>

**答案：C) Hubble**

**说明**：Hubble 通过 CLI/UI 和已配置的集成提供流记录、判定结果及受支持的协议指标。Relay 并非持久化存储；外部告警和数据保留需要进行配置，而且事件可能丢失。

</details>

5. VXLAN 的全称和主要用途是什么？

   - A) 虚拟扩展 LAN——创建虚拟网络
   - B) 虚拟可扩展 LAN——L2 覆盖网络
   - C) 超级扩展 LAN——大规模网络扩展
   - D) 可变可扩展 LAN——动态网络配置

<details>

<summary>显示答案</summary>

**答案：B) 虚拟可扩展 LAN——L2 覆盖网络**

**说明**：VXLAN 使用 UDP 和 24 位 VNI，在 IP 底层网络之上承载 L2 覆盖网络。该字段有约 1600 万个可能值；这并非 Cilium 对容量的承诺。Cilium 还会在覆盖网络元数据中承载身份信息。

</details>

6. BPF Maps 的主要作用是什么？

   - A) 管理网络路由表
   - B) 在 eBPF 程序之间共享和存储数据
   - C) 缓存 DNS 记录
   - D) 存储 TLS 证书

<details>

<summary>显示答案</summary>

**答案：B) 在 eBPF 程序之间共享和存储数据**

**说明**：BPF Maps 用于在程序和用户空间之间共享由内核管理的状态或事件。Hash/array map 使用键，而 ring buffer 和其他一些 map 类型不支持常规的查找/更新/删除操作。

</details>

7. Cilium 中表示 Pod 安全身份的数字标识符叫什么？

   - A) Pod ID
   - B) 安全上下文
   - C) Identity
   - D) Endpoint ID

<details>

<summary>显示答案</summary>

**答案：C) Identity**

**说明**：与安全相关的标签决定身份；并非所有元数据标签都会参与其中。在其分配范围内，多个 Endpoint 可以共享一个 Identity。数字 Endpoint ID 仅在 Agent 本地有效，是另一种标识符。

</details>

8. IPAM 的全称是什么？它在 Cilium 中起什么作用？

   - A) IP 地址管理——分配和管理 IP 地址
   - B) 互联网协议访问管理器——管理互联网访问
   - C) IP 分配模块——IP 分配模块
   - D) 内部协议地址映射器——内部协议地址映射

<details>

<summary>显示答案</summary>

**答案：A) IP 地址管理——分配和管理 IP 地址**

**说明**：IPAM 会分配和跟踪地址。Cilium 支持特定模式下的所有权管理，例如 cluster-pool、multi-pool、Kubernetes host-scope 和 ENI。GKE 是一个平台，并非通用的独立 ipam.mode 值；请检查托管平台集成。

</details>

9. WireGuard 的主要特性是什么？它在 Cilium 中有什么用途？

   - A) 数据包捕获工具——网络分析
   - B) 现代 VPN 协议——节点间流量加密
   - C) 负载均衡算法——流量分发
   - D) DNS 代理——名称解析

<details>

<summary>显示答案</summary>

**答案：B) 现代 VPN 协议——节点间流量加密**

**说明**：Cilium WireGuard 可保护受支持的跨节点流量。同节点 Pod 流量不会经过节点隧道，外部流量和节点流量则有各自的适用条件。它并不总是比 IPsec 更快；请在工作负载和保护设置相同的情况下进行比较。

</details>

10. CNI 的全称和作用是什么？

    - A) 容器网络接口——容器网络插件的标准接口
    - B) 云原生基础设施——云原生基础设施
    - C) 集群网络集成——集群网络集成
    - D) 容器节点互连——容器节点连接

<details>

<summary>显示答案</summary>

**答案：A) 容器网络接口——容器网络插件的标准接口**

**说明**：CNI 规定了运行时与网络插件之间的接口。在当前版本的 Kubernetes 中，kubelet 使用 CRI，由容器运行时负责管理 CNI 调用。Kubernetes 1.24 移除了 kubelet 直接管理 CNI 的相关标志。

</details>

## 简答题

11. 在 Cilium 中提供 L7 代理和服务网格功能的开源组件叫什么？

<details>

<summary>显示答案</summary>

**答案**：Envoy

**说明**：Envoy 提供已配置的 HTTP/gRPC 代理功能。DNS 策略使用 Cilium 的 DNS 代理，Kafka L7 规则已被移除。代理的部署和生命周期取决于安装配置，而不是每条任意的 L7 规则都会自动部署一个代理。

</details>

12. 在每个节点上运行、负责加载 eBPF 程序、实施网络策略并管理 Endpoint 的 Cilium 组件叫什么？

<details>

<summary>显示答案</summary>

**答案**：Cilium Agent

**说明**：对于符合条件且由 Cilium 管理的节点，Agent 会管理节点本地的 Endpoint、BPF 程序以及策略/数据路径状态。根据所用模式，IPAM 职责由 Agent、Operator 和/或平台共同承担。

</details>

13. 使用 IP 地址进行数据包路由的 OSI 模型层叫什么？它是第几层？

<details>

<summary>显示答案</summary>

**答案**：L3（网络层）

**说明**：L3（网络层）是 OSI 模型的第 3 层，负责使用 IP 地址进行逻辑寻址和数据包路由。IP（互联网协议）和 ICMP（互联网控制消息协议）都在此层运行。Cilium L3 策略可以根据 IP 地址和 CIDR 块筛选流量。L2（数据链路层）使用 MAC 地址，L4（传输层）使用端口号。

</details>

14. 为一组 Pod 提供稳定网络端点的 Kubernetes 资源叫什么？

<details>

<summary>显示答案</summary>

**答案**：Service

**说明**：Service 提供逻辑后端访问抽象。普通 ClusterIP Service 有虚拟 IP，headless Service 则没有；ExternalName 使用 DNS 别名。没有 selector 的 Service 可以表示由手动管理的端点或外部端点。

</details>

15. 修改数据包源 IP 地址的 NAT 类型叫什么？

<details>

<summary>显示答案</summary>

**答案**：SNAT（源网络地址转换）

**说明**：SNAT 会修改源地址。伪装会选择与出站路径/接口关联的地址；排除规则和指定的网关 IP 也会产生影响。并非所有出站 Pod 数据包都会被转换。DNAT 修改的是目标地址。

</details>

## 实践题

16. 将 ClusterMesh、CRD、FQDN 和 mTLS 与其定义配对。

<details>

<summary>显示答案</summary>

**答案：**

- **ClusterMesh**：跨集群网络元数据/连接能力；它不会自动复制所有策略资源。
- **CRD**：向 Kubernetes API 添加自定义资源类型的定义。
- **FQDN**：DNS 树中的绝对名称。toFQDNs 允许已学习的 IP。
- **mTLS**：带有对等方双向身份验证的 TLS。身份验证与应用授权是两个不同的概念。

</details>


17. 查询由 CRD 分配的身份并筛选实际的安全标签；同时区分 Agent 的本地视图。

<details>

<summary>显示答案</summary>

**答案：**

```bash
set -euo pipefail
kubectl get ciliumidentities -o json > identities.json
jq '.items[]
| select(.["security-labels"]["k8s:app"] == "frontend")
| {id: .metadata.name, labels: .["security-labels"]}' identities.json
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg identity list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
```

此操作假定使用 CRD 分配模式。CiliumIdentity 的作用域为集群，`security-labels` 是事实来源，与 `metadata.labels` 不同。并非所有保留/节点本地身份都会以 CRD 表示。Agent 视图的作用范围不同。按照[目标节点选择流程](../../../networking/cilium/07-advanced-topics.md)设置 `CILIUM_POD`。

</details>


18. 检查所选 Agent 的 Service、CT、NAT、策略和 Endpoint maps。

<details>

<summary>显示答案</summary>

**答案：**

```bash
set -eu
: "${CILIUM_POD:?Select the Cilium agent Pod on the node being inspected}"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf ct list global
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf nat list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf policy get --all
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
```

先选择所属节点上的 Agent。`--backends` 和策略 map 的 `--all` 都是有效标志。完整的 CT/策略转储可能很大，因此请在受影响的节点上谨慎使用。`map list` 会列出 Agent 打开的 maps；它并非完整的内核 map 清单，也不能证明所有活动应用连接都在其中。

</details>


19. 编写一个策略，允许访问为 api.example.com 和单层级 *.googleapis.com 名称学习到的 IP 的 TCP 443 流量，并设置 DNS 例外。说明其限制。

<details>

<summary>显示答案</summary>

**答案：**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: fqdn-egress-policy
  namespace: cilium-glossary-demo
spec:
  endpointSelector:
    matchLabels:
      app: external-client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*'
  - toFQDNs:
    - matchName: api.example.com
    - matchPattern: '*.googleapis.com'
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

这只是一个策略练习。请另外准备命名空间、带标签的客户端以及实际的 CoreDNS 路径。它允许 TCP/UDP DNS 流量，并启用 DNS 代理观测。`*.googleapis.com` 匹配一个子域层级，不匹配根域或 `a.b.googleapis.com`。DNS `*` 允许查询所有名称。toFQDNs 会生成 IP 放行规则，并不会对共享 IP 上的 HTTPS Host 进行限制，也不提供远程服务器身份验证。请检查重叠的允许策略和 TLS 验证设置。

</details>


20. 比较 Operator 和 Agent 的职责，并检查 Operator 状态。

<details>

<summary>显示答案</summary>

**答案：**

```bash
kubectl -n kube-system get deployment cilium-operator
kubectl -n kube-system get pods -l name=cilium-operator
kubectl -n kube-system logs -l name=cilium-operator -c cilium-operator --prefix --since=10m --tail=100
cilium status --verbose
kubectl get ciliumidentities
kubectl get ciliumendpoints --all-namespaces
```

| 组件 | 作用范围和职责 |
| --- | --- |
| Agent | 受管理节点上的 Endpoint、BPF 程序、策略/数据路径状态，以及取决于模式的本地 IPAM 工作。 |
| Operator | 集群级 CRD 注册、取决于模式的 IPAM/LB IPAM、孤立资源/身份回收，以及启用后的 Ingress/Gateway 转换。 |

`name=cilium-operator` 在当前 chart 中有效。`operator.replicas` 可以配置为一个或两个以上的实例。默认情况下由 Agent 创建身份；Operator 身份管理是独立的 Beta 模式。启用的功能还可能增加 ClusterMesh EndpointSlice/MCS 同步等职责，因此不应将这些职责视为无条件适用的固定清单。

</details>


***

[返回学习资料](../../../networking/cilium/glossary.md) | [Cilium 测验列表](../../README.md#cilium)
