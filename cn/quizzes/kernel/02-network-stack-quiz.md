# 内核网络栈测验

本测验检查你对 socket / VFS 入口路径、TCP 缓冲区和窗口、依赖状态的队列观测、hook 点，以及 Pod 到 Pod 路由的理解。

## 单项选择题

1. 哪个组件会在网卡之前排队等待发送的数据包，并通过 `tc -s qdisc` 显示丢包？
   - A) 网卡的物理层
   - B) qdisc：节点内部发生的丢弃会显示为 `tc -s qdisc` 中的 `dropped`
   - C) VPC 网络
   - D) 应用的 socket buffer

<details>

<summary>显示答案</summary>

**答案：B) qdisc：节点内部发生的丢弃会显示为 `tc -s qdisc` 中的 `dropped`**

**解释：**
qdisc 可以对出站数据包进行排队和调度，也可能因队列上限或主动队列管理而丢弃数据包。`dropped` 计数器上升可将丢弃归因于该 qdisc，但不能说明路径上的所有丢包都发生在这里。应根据受影响的时间区间和流量，将其与接口、驱动程序、协议栈和远端证据关联起来。`overlimits` 可能表示发生了流量整形，但并未丢包；它不能与 `dropped` 互换使用。
</details>

2. 讨论早期丢包性能时，XDP 的哪种模式区别很重要？
   - A) 它运行在硬件中，而不是作为内核模块运行
   - B) Native / driver XDP 在分配 skb 之前运行；generic XDP 已经会使用 skb
   - C) 它通过 JIT 编译
   - D) 它不需要查询 conntrack

<details>

<summary>显示答案</summary>

**答案：B) Native / driver XDP 在分配 skb 之前运行；generic XDP 已经会使用 skb**

**解释：**
早期丢包优势取决于具体模式。BPF map 可以维护状态；性能取决于内核、程序、驱动和硬件，不能保证某条路径在所有情况下都最快。
</details>

3. 接收流量很大时，只有一个 CPU 达到 100%，其他 CPU 处于空闲状态。应该调查哪个可能原因及相关机制？
   - A) qdisc 队列容量不足：增大队列长度
   - B) 接收处理负载集中：检查 RSS 队列 / IRQ 分布、RPS 软件导流和 RFS 缓存局部性
   - C) socket buffer 不足：增大 `tcp_rmem`
   - D) TCP 拥塞控制不匹配：切换到 bbr

<details>

<summary>显示答案</summary>

**答案：B) 接收处理负载集中：检查 RSS 队列 / IRQ 分布、RPS 软件导流和 RFS 缓存局部性**

**解释：**
RSS 会将流哈希到接收队列；IRQ 亲和性会影响由哪些 CPU 处理这些队列。RPS 会在后续阶段通过软件导流接收处理，RFS 则会尝试将处理放在更靠近消费应用的位置。它们并非都会移动硬件中断；单个流也可能仍留在一个队列中。在判断原因之前，应检查 `/proc/interrupts`、`mpstat -P ALL` 中每个 CPU 的 `%soft`，以及应用 CPU 使用情况。
</details>

4. 普通的中断驱动型 NAPI 如何降低每个数据包的开销？
   - A) 内核会自动提高 CPU 频率
   - B) 驱动会屏蔽相关队列中断并安排有工作量上限的轮询，将多个数据包合并处理以摊薄开销
   - C) 它会在处理前压缩数据包
   - D) 它会自动启用 GRO

<details>

<summary>显示答案</summary>

**答案：B) 驱动会屏蔽相关队列中断并安排有工作量上限的轮询，将多个数据包合并处理以摊薄开销**

**解释：**
批量处理可以摊薄中断和处理开销。安排轮询后，驱动会屏蔽相关中断；轮询结束后可以取消屏蔽。它不会关闭所有 CPU 中断。轮询有工作预算；负载过高时，延迟和丢包仍可能增加。忙轮询和线程化 NAPI 使用其他执行方式。
</details>

5. 为什么在单条流受 CPU 瓶颈限制时，同节点 Pod 到 Pod 流量可以达到 29.97 Gbps？
   - A) 节点内部有专用的高速网络
   - B) 在图示的普通 veth / 路由式同节点路径中，数据包可能只在内核内存中传递，不经过物理网卡
   - C) 内核会压缩数据包
   - D) 同节点流量不使用 TCP

<details>

<summary>显示答案</summary>

**答案：B) 在图示的普通 veth / 路由式同节点路径中，数据包可能只在内核内存中传递，不经过物理网卡**

**解释：**
虚拟设备仍然需要驱动处理。不同的 CNI、SR-IOV、overlay 或服务 / 策略转发路径会改变实际路径，因此应根据当前配置限定这一结论。
</details>

6. 小型握手数据包可以通过，但带 DF 标志的大型 IPv4 数据包在较低 MTU 的跳点被丢弃，返回的 ICMP 又遭到阻止。哪种机制可以解释该停滞现象？
   - A) conntrack 耗尽
   - B) PMTUD 失败：报告路径 MTU 的 ICMP 被阻止，因此只有大型数据包会被丢弃
   - C) TCP 拥塞控制不匹配
   - D) socket 接收缓冲区不足

<details>

<summary>显示答案</summary>

**答案：B) PMTUD 失败：报告路径 MTU 的 ICMP 被阻止，因此只有大型数据包会被丢弃**

**解释：**
设置 DF 后，IPv4 路由器不能对超大数据包进行分片，通常会返回 ICMP “fragmentation needed”消息。阻止该反馈可能会破坏 PMTUD 并形成黑洞。IPv6 路由器不会对数据包分片，而是使用 ICMPv6 “Packet Too Big”消息。如果题目未给出这些证据，握手成功后停滞只能算线索，不能当作证明；探测也可能使连接恢复。
</details>

7. 诊断网络问题时，建议按什么顺序进行？
   - A) 从应用层开始，逐层向下检查到网卡
   - B) 从丢弃计数器开始：检查 `conntrack -S` 中的 `insert_failed`、`tc -s qdisc` 中的 `dropped`，以及 `ethtool -S` 中的网卡丢弃
   - C) 始终先用 `tcpdump` 抓包
   - D) 从 CPU 利用率开始

<details>

<summary>显示答案</summary>

**答案：B) 从丢弃计数器开始：检查 `conntrack -S` 中的 `insert_failed`、`tc -s qdisc` 中的 `dropped`，以及 `ethtool -S` 中的网卡丢弃**

**解释：**
这些计数器可帮助找出调查方向，并不构成完整诊断。应将变化与受影响流量和时间窗口关联；对于 conntrack，还应检查 count / max 和内核日志，因为 `insert_failed` 不只是耗尽时才会出现。聚合计数器可能包含无关流量。本地计数器没有变化，也不能排除远端丢弃、身份验证或应用问题。应根据症状继续检查，例如使用 `ss -tin` 查看 RTT 和 cwnd、检查返回错误，并收集路径其他部分的证据。
</details>

8. 在没有工作负载基准测试的情况下，关于 `cubic` 与 `bbr`，哪种比较有依据？
   - A) cubic 用于 UDP，bbr 用于 TCP
   - B) cubic 会根据丢包 / ECN 等事件调整拥塞窗口；bbr 使用交付速率和 RTT 估算值，实际结果取决于实现和路径
   - C) bbr 总是比 cubic 快
   - D) cubic 已从内核 6.x 移除

<details>

<summary>显示答案</summary>

**答案：B) cubic 会根据丢包 / ECN 等事件调整拥塞窗口；bbr 使用交付速率和 RTT 估算值，实际结果取决于实现和路径**

**解释：**
这些模型解释的是不同的控制行为，并不保证性能排名。BBR 仍具有丢包 / 恢复行为，两种算法都不能消除接收窗口或应用限制。解释对比前，应确认内核实现、当前启用的算法、RTT / cwnd、工作负载和路径。
</details>

9. 一个进程在 TCP socket 上同时使用 `write(fd, ...)` 和 `send(fd, ...)`。哪种说法符合 Linux socket / VFS 桥接方式？
   - A) 两个调用都必须先进入磁盘文件系统，然后才进入 TCP
   - B) `send()` 总是调用 `vfs_write()`，而 socket 是磁盘文件
   - C) FD 指向与 socket 关联的 `struct file`；`write()` 使用 VFS socket file operations，而 `send()` 使用 socket 专用入口路径
   - D) socket 在文件描述符表中没有条目

<details>

<summary>显示答案</summary>

**答案：C) FD 指向与 socket 关联的 `struct file`；`write()` 使用 VFS socket file operations，而 `send()` 使用 socket 专用入口路径**

**解释：**
在本题引用的特定版本 Linux 中，`file->private_data` 会关联到 `struct socket`。VFS 的 `write()` 会经由 `socket_file_ops.write_iter` 分派到 `sock_write_iter`；`send()` 会通过自身的系统调用路径，从 FD 查找 socket。两者最终都会到达 socket / 协议操作。共用 file 抽象并不意味着会发生磁盘 I/O；发送成功也不代表对端应用已消费数据。请查看 [VFS 桥接](../../kernel/02-network-stack.md#socket-vfs-bridge)。
</details>

10. 一个已建立的 TCP 连接中有未读取的有效载荷，而 `ss -m` 显示的接收内存比 `Recv-Q` 大。哪种解释成立？
   - A) 内存记账包括分配开销以及可能的乱序数据；`Recv-Q` 统计尚未读取、按序排列的流字节数
   - B) 每个 `sk_buff` 就是整个 socket 接收缓冲区
   - C) 接收内存、`Recv-Q`、`rwnd` 和 `cwnd` 始终相等
   - D) 每个 skb 必须恰好代表一个线上数据包

<details>

<summary>显示答案</summary>

**答案：A) 内存记账包括分配开销以及可能的乱序数据；`Recv-Q` 统计尚未读取、按序排列的流字节数**

**解释：**
skb 用于描述数据包数据和元数据；它可能引用分片、被克隆，也可能表示合并 / 分段后的数据。socket 内存预算、应用有效载荷、接收方通告的窗口以及发送方拥塞窗口描述的是不同的限制或数量。不能用 `ss -m` 的内存值替代 `rwnd`；增大本地缓冲区也不会直接增大 `cwnd`。请查看[队列观测](../../kernel/02-network-stack.md#ss-tcp-queues)。
</details>

11. `ss` 对 `LISTEN` 显示 `Recv-Q=3, Send-Q=128`，对 `ESTABLISHED` 显示 `Recv-Q=4096, Send-Q=8192`。这些值表示什么？
   - A) 两行都统计网卡环形队列中当前的数据包
   - B) 侦听器收到了 3 字节并发送了 128 字节
   - C) 侦听器有 3 个未完成的 SYN，且可以确定已建立连接的 8192 字节都在线路上
   - D) 侦听器有 3 个等待 accept 的连接，最大 backlog 为 128；已建立连接的 socket 有 4096 个尚未读取且按序排列的字节，以及 8192 个已写入但尚未被累计确认的字节

<details>

<summary>显示答案</summary>

**答案：D) 侦听器有 3 个等待 accept 的连接，最大 backlog 为 128；已建立连接的 socket 有 4096 个尚未读取且按序排列的字节，以及 8192 个已写入但尚未被累计确认的字节**

**解释：**
对于侦听器，这两列统计连接数，不报告 SYN 队列占用量。对于已建立的 TCP 连接，它们统计流字节；`Send-Q` 可能同时包括尚未发送及已发送但未确认的字节。这些值既不是配置的 socket 内存预算，也不能证明发生了丢包。请查看[依状态变化的 TCP 队列](../../kernel/02-network-stack.md#ss-tcp-queues)。
</details>

12. 应用显式设置了 `SO_RCVBUF` 和 `SO_SNDBUF`。之后，操作员只增大了 `tcp_rmem[2]` 和 `tcp_wmem[2]`。哪种预期正确？
   - A) 所有现有 socket 都会立即分配两个新的最大值
   - B) 在各自方向上，显式 socket 设置仍会阻止常规自动调整
   - C) Linux 会将 `tcp_rmem[2]` 加倍，并直接将其通告为 `rwnd`
   - D) 更改发送缓冲策略会直接增大对端接收窗口

<details>

<summary>显示答案</summary>

**答案：B) 在各自方向上，显式 socket 设置仍会阻止常规自动调整**

**解释：**
socket 选项会设置 `SOCK_RCVBUF_LOCK` 和 `SOCK_SNDBUF_LOCK`；这些是策略标志，不是互斥锁。常规选项请求会受到 `net.core.rmem_max` / `wmem_max` 的限制。Linux 通常会将接受的请求值加倍用于记账，并通过 `getsockopt()` 报告该值；但这并不意味着相应内存已全部分配，也不意味着它都可用作有效载荷。sysctl 自动调优最大值和显式 socket 选项限制是不同的控制项。请查看 [TCP 缓冲策略](../../kernel/02-network-stack.md#tcp-buffer-policy)。
</details>

13. 假设一条路径提供 1 Gbit/s 带宽且 RTT 为 40 ms。哪种 BDP 计算和结论合理？
   - A) 40 MB；将每个 socket 的发送缓冲区都设置为这个准确数值
   - B) 5 字节；延迟的毫秒数可以直接乘以每秒 bit 数
   - C) 5,000,000 字节（约 4.77 MiB）；将此数量级与换算为字节的窗口、应用处理进度和内存开销进行比较
   - D) 5 MB；因此已证明每台主机都存在缓冲区瓶颈

<details>

<summary>显示答案</summary>

**答案：C) 5,000,000 字节（约 4.77 MiB）；将此数量级与换算为字节的窗口、应用处理进度和内存开销进行比较**

**解释：**
`1,000,000,000 bit/s × 0.040 s ÷ 8 bit/byte = 5,000,000 bytes`。此计算使用 RTT，并在理想化的稳定状态模型中估计线路中的有效载荷。`ss` 通常以 segment 为单位报告 `cwnd`，因此应使用 MSS 将数量换算为字节后再比较。接收窗口限制、pacing、丢包、CPU 和应用行为仍然重要；BDP 并不是通用调优指令。请参阅 [BDP 推理](../../kernel/02-network-stack.md#tcp-bdp-reasoning)和 [TCP buffer 实验](../../networking/07-linux-network-diagnostics.md#tcp-buffer-lab)。
</details>

14. 接口 IP MTU 为 1500，但主机抓包显示一个大于 1500 字节的 TCP 单元，并且发送校验和看起来错误。首先应得出什么结论？
   - A) 检查抓包位置和 offload；不含选项时，IPv4 TCP 有效载荷最多为 1460 字节，但主机侧 GSO / GRO 单元和未完成的校验和可能与线上数据包不同
   - B) TCP MSS 必须是 1500 字节，因为它包含 IP 标头
   - C) 远端 IPv6 路由器一定对数据包进行了分片
   - D) 抓包证明线上数据损坏，并否定 PMTUD

<details>

<summary>显示答案</summary>

**答案：A) 检查抓包位置和 offload；不含选项时，IPv4 TCP 有效载荷最多为 1460 字节，但主机侧 GSO / GRO 单元和未完成的校验和可能与线上数据包不同**

**解释：**
MSS 不包含 IP / TCP 标头，PMTU 则取决于完整路径。在不含选项时，IPv4 计算为 `1500 - 20 - 20 = 1460`；IPv6 基本标头下则剩余 1440。Offload 可能会延迟分段 / 校验和的计算，或合并接收数据包。单独的主机抓包不能确定线上数据包的大小，也不能证明数据已损坏。继续查看 [MTU / MSS 实验](../../networking/07-linux-network-diagnostics.md#mtu-mss-lab)。
</details>
