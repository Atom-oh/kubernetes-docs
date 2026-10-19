# 容器背后的内核机制测验

本测验检查你对命名空间、cgroup v2、netfilter 和 conntrack 的理解。

## 选择题

1. “内核中没有容器”是什么意思？由此得出什么实际结论？
   - A) 容器是一种虚拟机，与内核无关
   - B) 容器是一种结合命名空间、cgroup、能力等机制的约定，因此隔离是选择性的；运行时遗漏的隔离会形成隐蔽缺口
   - C) 容器完全由用户空间库实现
   - D) 内核 6.x 新增了 `struct container`

<details>

<summary>显示答案</summary>

**答案：B) 容器是一种结合命名空间、cgroup、能力等机制的约定，因此隔离是选择性的；运行时遗漏的隔离会形成隐蔽缺口**

**说明：**
内核中不存在 `struct container`，也没有一个创建容器的系统调用。运行时会启动进程，同时应用命名空间（隔离）、cgroup（限制）、capabilities/seccomp/LSM（权限）、overlayfs（文件系统）和 netfilter（网络）等机制。容器由多种机制组合而成，因此有两个结论：隔离不是非黑即白，而是选择性的（例如 Pod 共享网络命名空间但隔离挂载）；并且内核无法理解“创建容器”这一指令，如果运行时未应用 seccomp 配置文件，进程就会在没有该配置文件的情况下运行。
</details>

2. 为什么 Pod 中的两个容器可以通过 `localhost` 相互访问，却无法绑定到同一个端口？
   - A) Kubernetes 会自动创建容器间代理
   - B) 每个 Pod 共用一个网络命名空间，因此使用同一个 IP 和端口空间
   - C) CNI 会为每个容器分别连接一个 loopback
   - D) kube-proxy 会路由 Pod 内部流量

<details>

<summary>显示答案</summary>

**答案：B) 每个 Pod 共用一个网络命名空间，因此使用同一个 IP 和端口空间**

**说明：**
Kubernetes 会为每个 Pod 创建一个网络命名空间（由 pause 容器持有），并将该 Pod 中的所有容器放入其中。因此，它们共享同一 IP 和端口空间，可以通过 `localhost` 通信，且两个容器不能同时绑定 8080。这是 sidecar 模式的基础。此外，netfilter 规则按网络命名空间隔离，因此 sidecar 服务网格的 init 容器可以在 Pod 内安装 iptables 规则，而不会影响整个节点。
</details>

3. 为什么 cgroup v2 中的 `memory.current` 接近限制值仍可能完全正常？
   - A) `memory.current` 是估算值，因此不准确
   - B) `memory.current` 包含页缓存，而页缓存可回收：达到限制时内核会丢弃页缓存以腾出空间
   - C) cgroup v2 不会强制执行限制
   - D) `memory.current` 显示的是整个节点的内存

<details>

<summary>显示答案</summary>

**答案：B) `memory.current` 包含页缓存，而页缓存可回收：达到限制时内核会丢弃页缓存以腾出空间**

**说明：**
即使应用实际持有的内存（anon/RSS）远低于限制，读取大量文件也会积累页缓存，使 `memory.current` 达到限制。但页缓存可以回收，因此正常情况下内核会丢弃它以腾出空间，不会发生 OOM。问题出现在**内存回收跟不上内存分配时**，这时 OOM killer 才会采取行动。因此，诊断时需要结合 `memory.stat` → `anon`、`memory.events` → `oom` 和 PSI（`memory.pressure`）。
</details>

4. CPU 使用率只有 20%，但 p99 延迟突然升高。如何确认原因是 CPU 限制？
   - A) 用 `top` 再次检查使用率
   - B) 检查 `cpu.stat` 中 `nr_throttled` 与 `nr_periods` 的比值
   - C) 检查 `memory.pressure`
   - D) 检查节点的 `/proc/loadavg`

<details>

<summary>显示答案</summary>

**答案：B) 检查 `cpu.stat` 中 `nr_throttled` 与 `nr_periods` 的比值**

**说明：**
CPU 限制是带宽限制。`cpu.max` 为 `20000 100000` 表示“每 100 毫秒的周期最多使用 20 毫秒”，因此应用程序如果通过多个线程进行短时间突发工作，会很快耗尽配额，并被强制暂停，直到周期结束。平均使用率看起来是 20%，延迟却会飙升。`nr_throttled / nr_periods` 的比值有实际意义时，说明限制是原因。根本原因通常是应用程序感知到的 CPU 数量与配额不匹配，因此应先对齐 `GOMAXPROCS` 或 `-XX:ActiveProcessorCount`。
</details>

5. 截至 2026 年，关于 kube-proxy 模式，哪项说法正确？
   - A) nftables 是默认模式，iptables 已移除
   - B) nftables 在 1.33 中成为 GA；IPVS 在 1.35 中弃用（计划在 1.40 默认禁用、1.43 移除），当前默认模式仍是 iptables
   - C) IPVS 是默认模式，nftables 仍为 alpha
   - D) 三种模式的性能特征完全相同

<details>

<summary>显示答案</summary>

**答案：B) nftables 在 1.33 中成为 GA；IPVS 在 1.35 中弃用（计划在 1.40 默认禁用、1.43 移除），当前默认模式仍是 iptables**

**说明：**
nftables 模式从 alpha 1.29 → beta 1.31 → **GA 1.33** 逐步成熟，可提供 O(1) 查找和增量规则更新（工作节点要求内核 5.13+；AL2023 满足这一条件）。IPVS 模式已在 **1.35（2025 年 12 月）弃用**；上游计划在 1.40 默认禁用，并在 1.43 移除。其中，1.40 默认禁用和 1.43 移除仍是未来目标：请查看[持续维护的 KEP-5495 时间表](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)。建议替换为 nftables，但**当前默认模式仍是 iptables**，因此切换需要明确决策。
</details>

6. 如何验证是否发生 conntrack 耗尽？
   - A) 内核立即出现明显崩溃，并能在 `dmesg` 中看到
   - B) 关联 conntrack 数量/上限、插入/丢弃计数器和内核日志；仅凭 `insert_failed` 不能唯一证明发生了耗尽
   - C) 所有现有连接都会立即断开
   - D) CPU 使用率会上升到 100%

<details>

<summary>显示答案</summary>

**答案：B) 关联 conntrack 数量/上限、插入/丢弃计数器和内核日志；仅凭 `insert_failed` 不能唯一证明发生了耗尽**

**说明：**
非 NAT 流量也可能使用连接跟踪。Headless Service DNS 会避开 VIP DNAT，但本身并不会绕过连接跟踪。
</details>

7. 在 EKS 上调整 conntrack 值时要注意什么？
   - A) 在节点 bootstrap 中设置 sysctl 就足够了
   - B) EKS 默认提供的 `kube-proxy-config` ConfigMap 优先于命令行参数，因此只提高 sysctl 值可能会被 kube-proxy 改回
   - C) conntrack 是固定值，无法调整
   - D) Pod 的 `securityContext.sysctls` 可以更改节点全局值

<details>

<summary>显示答案</summary>

**答案：B) EKS 默认提供的 `kube-proxy-config` ConfigMap 优先于命令行参数，因此只提高 sysctl 值可能会被 kube-proxy 改回**

**说明：**
kube-proxy 也会管理 conntrack 值，而且 EKS 默认提供的 `kube-proxy-config` ConfigMap 优先于 CLI 参数。正确做法是在 ConfigMap 中调整 `conntrack.maxPerCore`/`conntrack.min`，然后重启 kube-proxy DaemonSet。使用 `maxPerCore` 是因为它按核心而不是绝对值设置，会随节点大小成比例扩展。D 错误：`nf_conntrack_max` 是节点全局值，无法从 Pod 规范中更改。
</details>

8. overlayfs copy-up 会带来什么运维问题？
   - A) 镜像层会重复存储，使镜像仓库变大
   - B) 修改 lowerdir 中的文件时，必须将整个文件复制到 upperdir，因此即使只修改大文件的一小部分，也要付出完整复制的成本
   - C) 容器启动时间会随层数增加
   - D) 读取性能会按层数成比例下降

<details>

<summary>显示答案</summary>

**答案：B) 修改 lowerdir 中的文件时，必须将整个文件复制到 upperdir，因此即使只修改大文件的一小部分，也要付出完整复制的成本**

**说明：**
overlayfs 会将只读 lowerdir（镜像层）与可写 upperdir（变更）合并。修改 lowerdir 中的文件前，必须先将其复制到 upperdir，且这是**完整文件复制**：修改 1GB 文件中的一个字节也要复制 1GB。因此，容器内的大量写入会消耗节点临时存储，**高写入量路径应放在卷上**，例如 emptyDir 或 PVC。
</details>
