# eBPF 数据平面测验

> **相关文档**: [eBPF 数据平面](../../../networking/calico/06-ebpf-dataplane.md)
> **最后更新**: 2026 年 9 月 12 日

## 测验

1. 当前 Calico 3.32 eBPF 指南规定的一般最低 Linux 内核版本是多少？以下不包括 RHEL 回移植例外。
   - A) 4.15+
   - B) 5.0+
   - C) 5.3+
   - D) 5.10+

<details>
<summary>显示答案</summary>

**答案：D) 5.10+**

**说明：**
一般最低要求是 5.10。指南将 RHEL 8.4 的 4.18.0-305 或更新版本列为回移植例外。部分功能要求更高：eBPF Log 规则需要 5.16，指南所述 QoS 带宽控制需要 6.6/TCX。操作系统或内核版本本身不能证明整个平台都兼容。

</details>

2. 如何评估切换到 Calico eBPF 后的性能提升？
   - A) 吞吐量提升 5–10%
   - B) 根据实际工作负载和配置进行测量；不存在普遍适用的百分比
   - C) 吞吐量提升 50–60%
   - D) 吞吐量提升 100%

<details>
<summary>显示答案</summary>

**答案：B) 根据实际工作负载和配置进行测量；不存在普遍适用的百分比**

**说明：**
两种数据平面都在内核中处理数据包。效果取决于流量路径、规则、conntrack、CPU/NIC、日志记录和负载。指南保留了不同的历史报告值，但没有原始证据；这些数值不能视为提升 20–40% 的承诺，也不能据此断言策略成本始终不变。

</details>

3. BTF 是什么的缩写？它为何对 Calico 的 eBPF 数据平面很重要？
   - A) Binary Transfer Format——用于网络数据包编码
   - B) BPF Type Format——用于调试和 CO-RE 支持
   - C) Byte Translation Function——用于地址转换
   - D) Block Transfer Filter——用于速率限制

<details>
<summary>显示答案</summary>

**答案：B) BPF Type Format——用于调试和 CO-RE 支持**

**说明：**
BTF 提供类型元数据，供工具使用并支持 CO-RE 重定位。它不同于 verifier 安全检查，也不能保证每个已编译程序都能在所有内核上运行。Calico 会选择特定版本的对象并检查功能；文件存在本身并不能证明已完全就绪。

</details>

4. 在 Calico eBPF 数据平面中，Direct Server Return（DSR）是什么？
   - A) 让 Pod 直接访问 Kubernetes API server 的方法
   - B) 一种负载均衡优化，使返回流量绕过负载均衡器
   - C) 用于服务发现的 DNS 解析技术
   - D) 持久卷的存储访问模式

<details>
<summary>显示答案</summary>

**答案：B) 一种负载均衡优化，使返回流量绕过负载均衡器**

**说明：**
DSR 允许远端后端节点返回流量，而无需经过最初转发 Service 请求的 Kubernetes 节点。Calico 会执行源地址转换。DSR 需要兼容的网络架构和返回路径；它不会自动绕过所有外部云负载均衡器，也不能保证与其全部兼容。

</details>

5. Calico eBPF 数据平面中的连接时负载均衡是什么？
   - A) 节点加入集群时执行的负载均衡
   - B) 在 TCP 连接建立时转换 Service IP
   - C) 后端 Pod 的健康检查机制
   - D) 连接断开后的自动故障转移

<details>
<summary>显示答案</summary>

**答案：B) 在 TCP 连接建立时转换 Service IP**

**说明：**
对受支持的 TCP 套接字，CTLB 会在数据包处理之前，于 connect() 时转换 Service 目标地址。启用相应模式后也可能包括 UDP 套接字挂钩。它绕过的是该 Service DNAT 路径，并非所有策略、路由、conntrack 或其他 NAT。DSR 是独立的外部返回路径优化。

</details>

6. 关于 Calico eBPF 与 kube-proxy 的协调，哪项说法正确？
   - A) kube-proxy 必须始终保持原样并与 eBPF 并行运行
   - B) Calico 可以处理 Service，但需根据平台协调 kube-proxy
   - C) kube-proxy 会自动升级为使用 eBPF
   - D) kube-proxy 处理 IPv6，eBPF 处理 IPv4

<details>
<summary>显示答案</summary>

**答案：B) Calico 可以处理 Service，但需根据平台协调 kube-proxy**

**说明：**
按照安装资源所有者规定的流程操作。有条件的自动引导流程可以管理 kube-proxy；保留托管代理的平台则需要禁用清理，并设置不冲突的 health-server。单独设置清理标志并不会启用 Service 功能，删除 kube-proxy 也不是通用步骤。

</details>

7. Calico eBPF 数据平面中的 BPF map 有什么用途？
   - A) 存储用于地理路由的位置数据
   - B) 存储内核与用户空间共享的状态和配置数据
   - C) 将 DNS 名称映射到 IP 地址
   - D) 绘制网络拓扑图

<details>
<summary>显示答案</summary>

**答案：B) 存储内核与用户空间共享的状态和配置数据**

**说明：**
Map 保存路由、NAT、conntrack、affinity，以及辅助程序、计数器和 IP 集等数据。不同数据族会使用 hash、LRU hash、LPM trie 或其他类型。策略会被编译到 BPF 程序中；它们并非全部存放在一个通用的、常数时间查找的“元组到动作”map 中。

</details>

8. 原生驱动 XDP 与 TC 挂载点相比有什么特点？
   - A) XDP 在网络栈中比 TC 更早处理数据包
   - B) TC 在网络栈中比 XDP 更早处理数据包
   - C) XDP 仅用于 ingress，TC 仅用于 egress
   - D) 两者没有区别，只是别名

<details>
<summary>显示答案</summary>

**答案：A) XDP 在网络栈中比 TC 更早处理数据包**

**说明：**
原生驱动 XDP 可以在分配 skb 之前处理数据包，而 TC 使用基于 skb 的数据包上下文。通用 XDP 执行得更晚，此时 skb 已存在。驱动、硬件和程序支持都会影响实际行为；挂载点名称不能保证固定的性能优势。

</details>

9. 在 Calico 中，哪个 FelixConfiguration 设置可启用 eBPF 数据平面？
   - A) dataplaneMode: eBPF
   - B) bpfEnabled: true
   - C) useEBPF: yes
   - D) felixBackend: ebpf

<details>
<summary>显示答案</summary>

**答案：B) bpfEnabled: true**

**说明：**
在独立 manifest 流程中，Felix 使用字段 bpfEnabled: true。Operator 安装应设置 Installation.spec.calicoNetwork.linuxDataplane: BPF。还需保留资源所有权、直接 API 访问、代理协调和受支持的集群范围切换流程。

</details>

10. Calico 的 bpfExternalServiceMode 设置控制什么？
    - A) Pod 如何访问集群外部的服务
    - B) 外部客户端如何访问 NodePort 和 LoadBalancer Service
    - C) 服务发现所用的外部 DNS server
    - D) 外部 API 访问的身份验证模式

<details>
<summary>显示答案</summary>

**答案：B) 外部客户端如何访问 NodePort 和 LoadBalancer Service**

**说明：**
对于远端 Service 后端，Tunnel 模式的请求和响应会经过入口节点/隧道路径；DSR 模式会隧道转发请求，但由后端节点直接返回。两种模式都需要相关 VXLAN/MTU 路径。DSR 还受源地址验证和外部负载均衡器限制。

</details>

11. 通常使用哪种工具调试和检查 Calico 的 eBPF 程序及 map？
    - A) tcpdump
    - B) bpftool
    - C) netstat
    - D) iptables-save

<details>
<summary>显示答案</summary>

**答案：B) bpftool**

**说明：**
bpftool 可检查实际的 BPF 程序/map ID、类型和状态。Calico node 镜像也内置 calico-node -bpf；使用其 help 子命令并提供完整参数，例如 `policy dump <interface> <hook>`。仅列出程序或 map 不能证明应用连通性。

</details>

12. Calico 3.32 数据平面迁移应采用哪种方式？
    - A) 立即在所有节点上同时启用 eBPF
    - B) 先禁用 kube-proxy，再启用 eBPF
    - C) 验证兼容性和直接 API 访问，并遵循资源所有者规定的协调迁移与回滚流程
    - D) 从头重装启用了 eBPF 的 Calico

<details>
<summary>显示答案</summary>

**答案：C) 验证兼容性和直接 API 访问，并遵循资源所有者规定的协调迁移与回滚流程**

**说明：**
Operator 自动引导仅适用于受限的前置条件；其他安装方式应采用相应文档规定的手动/平台流程。不要保留长期混合模式 canary，也不要在未经准备的测试前禁用所有 kube-proxy 实例。官方滚动切换可能中断 NodePort 流量，回滚也可能重置连接。

</details>
