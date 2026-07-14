# eBPF 数据平面测验

> **相关文档**: [eBPF 数据平面](../../../networking/calico/06-ebpf-dataplane.md)
> **最后更新**: February 22, 2026

## 测验

1. Calico 的 eBPF 数据平面所需的最低 Linux kernel 版本是多少？
   - A) 4.15+
   - B) 5.0+
   - C) 5.3+
   - D) 5.10+

<details>
<summary>显示答案</summary>

**答案: C) 5.3+**

**说明:**
Calico 的 eBPF 数据平面要求最低 kernel 版本为 5.3。不过，建议使用 kernel 5.8+，以获得最佳性能和完整的功能支持，其中包括可实现更好调试和内省功能的 BTF (BPF Type Format)。

</details>

2. 在 Calico 中从 iptables 切换到 eBPF 数据平面时，通常可以预期获得怎样的性能提升？
   - A) 吞吐量提升 5-10%
   - B) 吞吐量提升 20-40%
   - C) 吞吐量提升 50-60%
   - D) 吞吐量提升 100%

<details>
<summary>显示答案</summary>

**答案: B) 吞吐量提升 20-40%**

**说明:**
eBPF 数据平面相较于 iptables 通常可提供 20-40% 的吞吐量提升。这是因为 eBPF 直接在 kernel 中处理数据包，无需承担遍历 iptables 链的开销；随着规则数量增加，这种开销会变得显著。

</details>

3. BTF 代表什么，它为何对 Calico 的 eBPF 数据平面很重要？
   - A) Binary Transfer Format - 用于网络数据包编码
   - B) BPF Type Format - 用于调试和 CO-RE 支持
   - C) Byte Translation Function - 用于地址转换
   - D) Block Transfer Filter - 用于速率限制

<details>
<summary>显示答案</summary>

**答案: B) BPF Type Format - 用于调试和 CO-RE 支持**

**说明:**
BTF (BPF Type Format) 为 BPF 程序提供类型信息。它支持 CO-RE (Compile Once, Run Everywhere)，使 eBPF 程序无需重新编译即可在不同的 kernel 版本上运行。BTF 还可通过 bpftool 等工具提供更好的调试功能。

</details>

4. 在 Calico 的 eBPF 数据平面中，什么是 Direct Server Return (DSR)？
   - A) 一种让 pods 直接联系 Kubernetes API server 的方法
   - B) 一种负载均衡优化，返回流量绕过 load balancer
   - C) 一种用于 Service discovery 的 DNS 解析技术
   - D) 一种用于 persistent volumes 的存储访问模式

<details>
<summary>显示答案</summary>

**答案: B) 一种负载均衡优化，返回流量绕过 load balancer**

**说明:**
Direct Server Return (DSR) 是一种负载均衡优化，backend server 的响应流量会直接发送给客户端，绕过 load balancer node。这可降低延迟和 load balancer 带宽消耗，从而提升整体 Service 性能。

</details>

5. Calico 的 eBPF 数据平面中的连接时负载均衡是什么？
   - A) 在 node 加入 cluster 时进行的负载均衡
   - B) 在建立 TCP connection 时执行的 Service IP 转换
   - C) 一种用于 backend pods 的 health check 机制
   - D) 在连接中断时进行的自动故障转移

<details>
<summary>显示答案</summary>

**答案: B) 在建立 TCP connection 时执行的 Service IP 转换**

**说明:**
连接时负载均衡会在建立 TCP connection 的瞬间将 Service IP 转换为 pod IP，而不是在每个数据包上执行转换。这可提供更高效的负载均衡，并支持 DSR 等功能，因为客户端 socket 会直接连接到选定的 backend。

</details>

6. 启用 Calico 的 eBPF 数据平面后，kube-proxy 会如何？
   - A) kube-proxy 继续与 eBPF 一起运行
   - B) eBPF 提供等效功能，因此可以禁用 kube-proxy
   - C) kube-proxy 自动升级为使用 eBPF
   - D) kube-proxy 处理 IPv6，而 eBPF 处理 IPv4

<details>
<summary>显示答案</summary>

**答案: B) eBPF 提供等效功能，因此可以禁用 kube-proxy**

**说明:**
Calico 的 eBPF 数据平面可以完全替代 kube-proxy 来进行 Service 负载均衡。启用 eBPF 模式后，可以禁用 kube-proxy，以避免冗余处理和潜在冲突。eBPF 数据平面会直接处理 ClusterIP、NodePort 和 LoadBalancer Service。

</details>

7. BPF maps 在 Calico 的 eBPF 数据平面中有什么用途？
   - A) 为地理路由存储地理位置数据
   - B) 存储在 kernel 和 userspace 之间共享的状态和配置数据
   - C) 将 DNS 名称映射到 IP 地址
   - D) 创建网络拓扑图

<details>
<summary>显示答案</summary>

**答案: B) 存储在 kernel 和 userspace 之间共享的状态和配置数据**

**说明:**
BPF maps 是键值数据结构，用于存储可由运行在 kernel 中的 eBPF 程序和 userspace 应用程序访问的状态及配置数据。Calico 使用 BPF maps 存储 connection tracking 状态、策略规则、Service endpoints 以及其他网络元数据。

</details>

8. eBPF 程序的 XDP 和 TC 挂载点有什么区别？
   - A) XDP 在网络栈中比 TC 更早处理数据包
   - B) TC 在网络栈中比 XDP 更早处理数据包
   - C) XDP 仅用于 ingress，TC 仅用于 egress
   - D) 没有区别；它们是别名

<details>
<summary>显示答案</summary>

**答案: A) XDP 在网络栈中比 TC 更早处理数据包**

**说明:**
XDP (eXpress Data Path) 在网络栈中尽可能早的位置处理数据包，甚至早于 kernel 分配 sk_buff。TC (Traffic Control) hooks 会在 sk_buff 分配后较晚处理数据包。XDP 可提供最高性能，但功能有限；TC 则以略微的性能代价提供更多功能。

</details>

9. 哪项 FelixConfiguration 设置可在 Calico 中启用 eBPF 数据平面？
   - A) dataplaneMode: eBPF
   - B) bpfEnabled: true
   - C) useEBPF: yes
   - D) felixBackend: ebpf

<details>
<summary>显示答案</summary>

**答案: B) bpfEnabled: true**

**说明:**
在 FelixConfiguration resource 中设置 `bpfEnabled: true` 即可启用 eBPF 数据平面。还可以在同一 resource 中配置 `bpfExternalServiceMode`、`bpfKubeProxyIptablesCleanupEnabled` 等其他 eBPF 专用设置。

</details>

10. Calico 中的 bpfExternalServiceMode 设置控制什么？
    - A) pods 如何访问 cluster 外部的 Service
    - B) 外部客户端如何访问 NodePort 和 LoadBalancer Service
    - C) 用于 Service discovery 的外部 DNS server
    - D) 外部 API 访问的身份验证模式

<details>
<summary>显示答案</summary>

**答案: B) 外部客户端如何访问 NodePort 和 LoadBalancer Service**

**说明:**
`bpfExternalServiceMode` 设置控制 Calico 如何处理来自外部源、面向 NodePort 和 LoadBalancer Service 的流量。选项包括 "Tunnel"（默认，通过封装保留源 IP）和 "DSR"（Direct Server Return，以提升性能）。

</details>

11. 通常使用哪种工具来调试和检查 Calico 的 eBPF 程序及 maps？
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables-save

<details>
<summary>显示答案</summary>

**答案: B) bpftool**

**说明:**
bpftool 是用于检查和调试 eBPF 程序及 maps 的标准实用工具。它可以列出已加载的 BPF 程序、转储 map 内容、显示程序统计信息以及显示 BTF 信息。这对于排查 Calico eBPF 数据平面的问题至关重要。

</details>

12. 在 Calico 中从 iptables 迁移到 eBPF 数据平面的推荐顺序是什么？
    - A) 立即在所有 nodes 上同时启用 eBPF
    - B) 先禁用 kube-proxy，然后启用 eBPF
    - C) 在 Calico 上启用 eBPF，验证运行情况，然后禁用 kube-proxy
    - D) 从头重新安装启用了 eBPF 的 Calico

<details>
<summary>显示答案</summary>

**答案: C) 在 Calico 上启用 eBPF，验证运行情况，然后禁用 kube-proxy**

**说明:**
推荐的迁移路径是：1) 在 FelixConfiguration 中启用 eBPF 数据平面，2) 验证网络和 Service 是否正常工作，3) 在确认 eBPF 正常运行后禁用 kube-proxy。这样，如果在迁移期间发现问题，可以安全回滚。

</details>
