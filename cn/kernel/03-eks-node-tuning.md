# EKS 节点内核调优

> **支持版本**：Amazon Linux 2023（kernel 6.1 / 6.12 / 6.18），Kubernetes 1.33+（Amazon EKS）
> **最后更新**：2026 年 9 月 13 日

## 本文涵盖内容

- 在 EKS 节点上哪些内容需要更改、哪些应保持默认值，以及如何判断
- 在 EKS 上应用内核参数的实际路径，以及每条路径的注意事项
- AL2023 内核从 6.1 迁移到 6.18 在运维上意味着什么

## 首先：大部分设置保持不变

这是本文中最重要的建议。

内核默认值旨在**在广泛的工作负载范围内保持合理行为**，许多默认参数还会在负载下由内核自动调整（例如 TCP 缓冲区自动调优）。缺少依据的调优会带来三类代价。

| 问题 | 示例 |
|---|---|
| **配置无法复现** | 每个节点的数值不同，因此无法复现故障 |
| **内核升级后出现故障** | 在 6.1 上有效的参数可能在 6.18 中重命名、移动或删除 |
| **破坏自动调优** | 显式设置套接字的 SO_RCVBUF/SO_SNDBUF 会禁用该套接字的自动调整大小；sysctl 边界是另一种控制方式 |

**调优的前提是测量**。请按以下顺序操作。

1. 识别症状（延迟？丢弃？吞吐量？）
2. **先检查丢弃计数器**：`conntrack -S` 中的 `insert_failed`、`tc -s qdisc` 中的 `dropped`、`ethtool -S` 中的 NIC 丢弃计数
3. 只更改计数器正在增长的位置上的参数
4. 在相同条件下测量修改前后数据
5. 将更改及其理由记录为代码（见下文应用路径）

测量方法见 [Pod 网络基准测试](../networking/06-pod-network-benchmark.md)中的实验装置。

## 应用路径：如何在 EKS 上更改内核参数

有多种方式，**每种方式的作用范围和注意事项都不同**。实际操作中，弄清这些区别至关重要。

| 路径 | 作用范围 | 持久性 | 说明 |
|---|---|---|---|
| **节点引导**（User Data / `nodeadm`） | 整台节点 | 替换节点时重新应用 | AL2023 使用 `nodeadm` 配置。最标准的方式 |
| **Bottlerocket 设置**（`settings.kernel.sysctl`） | 整台节点 | 作为节点设置管理 | Bottlerocket 是不可变系统，因此只能使用此路径 |
| **Pod `securityContext.sysctls`** | **仅 Pod 的 net 命名空间** | Pod 规格 | **仅适用于命名空间级 sysctl**。许多 `net.*` 参数符合条件 |
| **特权 init DaemonSet** | 整台节点 | Pod 重启后重新应用 | 常见用法，但需要特权权限（须进行安全评审） |
| **`kube-proxy-config` ConfigMap** | conntrack 相关参数 | 由 kube-proxy 管理 | **在 EKS 上优先于 CLI 参数生效** |
| **Karpenter `EC2NodeClass`** | 节点组 | 创建节点时应用 | 以声明方式管理 User Data |

### 两个容易忽略的要点

**第一，要区分命名空间级和非命名空间级 sysctl**。许多 `net.*` 值可以按 net 命名空间设置，因此 Pod 的 `securityContext.sysctls` 可以修改它们。相反，`vm.*`、`fs.*` 和**某些值（例如 `net.netfilter.nf_conntrack_max`）是节点全局参数**，不能通过 Pod 规格修改。

此外，kubelet 默认会拒绝“不安全”的 sysctl。如果需要其中某个参数，请通过节点设置 `--allowed-unsafe-sysctls` 显式允许。

**第二，kube-proxy 会覆盖 conntrack 设置。**[容器背后的内核功能](./01-container-primitives.md)中也提到过，但这在实际中是最常遇到的陷阱，因此值得再次说明：EKS 默认提供 `kube-proxy-config` ConfigMap，且**它的设置优先于命令行参数**。启动引导时提高 sysctl 值可能会被 kube-proxy 改回去。

::: warning 需要核实
在 Bottlerocket 上，通过 `settings.kernel.sysctl` 提高 conntrack 上限不会生效（[bottlerocket-os/bottlerocket#4221](https://github.com/bottlerocket-os/bottlerocket/issues/4221)，于 2024 年 9 月提交）。原因是**kube-proxy 配置文件（`/var/lib/kube-proxy-config/config`）优先于命令行参数**。

使用 kube-proxy 配置文件时，如果你有意将限额管理交给节点 sysctl，请修改其中的 **`conntrack.maxPerCore`/`conntrack.min` 字段**。将两者都设为 0，并不代表应该依赖会被 `--config` 忽略的 CLI 参数。推出更改前，请确认托管附加组件会如何协调配置，并核实节点有足够的内存余量。

**无法确认此问题是否已在某个具体的 Bottlerocket 版本中修复**。无论使用哪条路径，应用后都要验证节点上的实际值。

```bash
# Check the actually applied values on the node
cat /proc/sys/net/netfilter/nf_conntrack_max
cat /proc/sys/net/netfilter/nf_conntrack_count
conntrack -S | head
```
:::

## 内核版本：AL2023 从 6.1 迁移到 6.18

这是当前需要了解的变化。

| 日期 | 变化 |
|---|---|
| 2023 年 3 月 | AL2023 发布时使用 kernel **6.1** |
| 2025 年 4 月 | 增加对 kernel **6.12** 的支持 |
| **2026 年 8 月 17 日** | `al2023-ami-kernel-default` AMI 的**默认内核从 6.1 改为 6.18** |

**由此带来两点影响。**

默认内核 **AMI 系列**发生了变化，但节点替换时会使用启动模板或置备策略选定的 AMI。固定的 AMI ID 不会仅因启动了新节点就自动更换内核。刷新“最新/默认”AMI 查询结果时可能会选择新内核；EKS 优化版 AMI 有自己的版本选择方式。

如果必须固定内核，请显式使用**特定内核版本的 AMI**（例如 `al2023-ami-kernel-6.1-*`）。

**内核变化时要检查的项目：**

| 项目 | 原因 |
|---|---|
| 可调参数是否存在及其位置 | 参数名可能改变；参数也可能从 sysctl 移到 debugfs |
| 依赖内核模块的组件 | eBPF 程序、特定 CNI 功能、GPU 驱动、自定义模块 |
| 调度器行为 | 6.6+ 使用 EEVDF（见下文）；可能会影响对延迟敏感的工作负载 |
| 性能回归 | 每个内核版本都要重新测量基准性能 |

**建议**：将内核迁移**视为与 Kubernetes 版本升级同等重要的变更**。在预发布环境中使用相同内核进行验证，重新测量性能基线，然后再推广到生产环境。

## CPU：调度器与节流

### EEVDF：6.6 中的变化

Linux 6.6 将 CFS 的任务选择逻辑替换为 **EEVDF**（最早合格虚拟截止时间优先）。

需要准确理解的是**哪些内容改变了，哪些没有改变**。

| 已改变 | 未改变 |
|---|---|
| **选择下一个任务的方式**（基于虚拟截止时间） | vruntime 机制、权重计算 |
| 唤醒任务时的抢占决策：从启发式参数（`sched_wakeup_granularity_ns`）改为比较**截止时间** | 组调度（cgroup cpu.weight）、负载均衡 |

因此，准确的理解是：**EEVDF 演进并替换了 CFS 的选择逻辑，但并没有整体取代 CFS**。变化位于 `fair_sched_class` 中。

从运维角度看：**对延迟敏感的工作负载，其唤醒延迟特性可能改变**。通常会有所改善，但如果从 kernel 6.1 迁移到 6.18 后 p99 发生变化，这就是一个可能原因。

### 可调参数实际位于何处

根据内核源码（`kernel/sched/debug.c`）核实：

| 项目 | 状态 |
|---|---|
| `sched_latency_ns` | **已移除**：`kernel/sched/fair.c` 中已没有引用 |
| `sched_wakeup_granularity_ns` | **已移除**（同上） |
| **`/sys/kernel/debug/sched/base_slice_ns`** | **当前对应项**。内部变量是 `sysctl_sched_base_slice`，通过 debugfs 暴露为 `base_slice_ns` |

因此，CFS 时代的延迟和抢占启发式可调参数已消失，统一为**一个基础时间片（`base_slice_ns`）**。请注意，名称中没有 `sched_` 前缀；完整路径是 `/sys/kernel/debug/sched/base_slice_ns`。

此外，EEVDF 允许任务通过 `sched_setattr()` 系统调用**请求自己的时间片**。对于延迟敏感型应用，这通常比改动全局可调参数更合适。

**仍然不建议把调度器参数作为常规调优目标**。debugfs 是内核调试接口，生产环境中可能没有挂载；多数情况下，调整应用线程数或 cgroup 限额更合适。

### CPU 限额：何时节流是真正的问题

如[容器背后的内核功能](./01-container-primitives.md)所述，CPU 限额属于带宽限制，因此即使利用率较低，也可能增加延迟。

**诊断：**

```bash
# cgroup v2: from the container's cgroup path
cat cpu.stat
# nr_periods, nr_throttled, throttled_usec
```

如果 `nr_throttled / nr_periods` 占比不可忽略，原因就是限额。

**应对方案的优先顺序**（设计说明见[资源优化](../ops/10-resource-optimization.md)）：

1. **让应用感知到的 CPU 数量与限额匹配**。这是最容易被忽略的根本原因：如果容器中的运行时看到所有节点 CPU 核心并据此创建线程，配额会立即耗尽。将 JVM `-XX:ActiveProcessorCount`、Go `GOMAXPROCS`、Node.js `UV_THREADPOOL_SIZE` 等设置为与限额匹配的值。
2. **提高限额**，同时权衡节点稳定性。
3. **对于对延迟极度敏感的工作负载，可考虑移除限额**；但要通过 requests 和节点隔离控制 noisy-neighbor 风险。
4. 使用 `cpu.pressure` PSI 检查实际停滞时间。

对于延迟敏感型工作负载，CPU Manager 的 static policy（专用核心）是另一种有效机制。它会降低节点利用率，因此需要明确的依据。

## 内存：OOM 与压力

### 哪些参数应调整、哪些应保持原样

| 参数 | 建议 |
|---|---|
| `vm.swappiness` | Kubernetes 传统上假设 swap 已关闭。对 swap 的支持日益成熟，但在 EKS 上启用前**请确认支持状态** |
| `vm.overcommit_memory` | **保留默认值**。更改后很难预测容器内存分配失败的模式 |
| `vm.min_free_kbytes` | 内存回收余量。数值过低时，突发分配可能导致 OOM。**仅考虑用于内存很大且负载突发严重的节点** |
| `vm.max_map_count` | 对 Elasticsearch/OpenSearch 等而言，**确实可能需要调整**；默认值较低，会触及 mmap 限制 |
| `kernel.pid_max` | 高密度节点耗尽 PID 时再考虑 |

`vm.max_map_count` 是经常遇到的真实案例：OpenSearch 系列软件会 mmap 大量文件，使用默认值时无法启动。这是“有依据的调优”的好例子：症状明确，参数是直接原因，而且供应商记录了建议值。

### 先设置 kubelet 预留，再考虑内核参数

对节点稳定性影响比内核调优更大的，是**kubelet 的资源预留**。

| 设置 | 用途 |
|---|---|
| `--system-reserved` | 为操作系统和系统守护进程预留资源 |
| `--kube-reserved` | 为 kubelet 和容器运行时预留资源 |
| `--eviction-hard` | 达到阈值时驱逐 Pod |

预留不足时，Pod 会耗尽节点内存，导致**内核或 kubelet 自身发生 OOM**。节点会变为 `NotReady`，其上的所有 Pod 都会受影响；这比单个 Pod 的 OOM 严重得多。

**驱逐优于 OOM**。驱逐是 Kubernetes 以受控方式迁移 Pod；OOM killer 则是内核突然杀死某个进程。目标是设置 `--eviction-hard`，让 Kubernetes 在内核 OOM 之前介入。

### 使用 PSI 观察压力

cgroup v2 中的 PSI 比使用量更能反映压力。

```bash
# Whole node
cat /proc/pressure/memory
cat /proc/pressure/cpu
cat /proc/pressure/io

# A specific cgroup
: "${KERNEL_CGROUP_PATH:?Set the inspected cgroup directory}"
cat "$KERNEL_CGROUP_PATH/memory.pressure"
```

`some avg10` 表示过去 10 秒内**至少有一个任务因该资源而停滞的时间比例**。如果使用量图表看起来平稳，而该值持续升高，就说明时间花在了回收或资源争用上。

## 网络：有依据的调整

### conntrack

如前文所述，**这是最常引发实际事故的项目**。

| 项目 | 内容 |
|---|---|
| 症状 | 新连接被静默丢弃；应用只能看到超时/拒绝 |
| 需要关联的证据 | `conntrack -S` 中的 **`insert_failed`** 持续上升；仅凭这一项不能证明跟踪表已耗尽 |
| 辅助信号 | `dmesg` 中的 `nf_conntrack: table full`，以及 `nf_conntrack_count` / `nf_conntrack_max` 比率 |
| 调整路径 | **`kube-proxy-config` ConfigMap 中的 `conntrack.maxPerCore` / `conntrack.min`**（在 EKS 上优先于其他设置） |
| 代价 | 每个条目都会占用节点内存，不能无限提高 |
| 根本修复 | 减少连接周转；调查数据平面/映射压力。仅使用 Headless DNS 并不会禁用跟踪 |

需要了解**为什么使用 `maxPerCore`**。它按核心数而非绝对值设置，因此同一配置可以按节点规格比例缩放。固定绝对值（`nf_conntrack_max`）会使小节点配置过量、大节点配置不足。

也可以调整超时：缩短 `nf_conntrack_tcp_timeout_established`（默认值很长）可以更早回收条目。应避免破坏合法的长连接。

### 套接字缓冲区和队列

| 参数 | 使用时机 |
|---|---|
| `net.core.somaxconn` | **accept 队列溢出时**。接收突发连接的服务器常需调整 |
| `net.ipv4.tcp_max_syn_backlog` | SYN 突发流量时 |
| `net.core.netdev_max_backlog` | **接收 softirq 处理跟不上时** |
| `net.ipv4.tcp_rmem` / `tcp_wmem` | TCP 缓冲区大小的边界/默认值；更改本身不会禁用自动调优。只有基于实测 BDP/内存证据时才调整 |
| `net.ipv4.ip_local_port_range` | **源端口耗尽时**。出站流量密集的节点上实际可能发生 |
| `net.ipv4.tcp_tw_reuse` | TIME_WAIT 累积时；先弄清其行为再应用 |

**`somaxconn` 和 `ip_local_port_range` 是有依据的参数调整案例。前者可以通过** `nstat` 中的证据计数器（`TcpExtListenOverflows`）观察，后者则会直接表现为连接失败。

除非测量结果能证明需要更改，否则应保留合理的 `tcp_rmem`/`tcp_wmem` 边界。Linux 文档说明，显式设置套接字的 **SO_RCVBUF/SO_SNDBUF** 会禁用相应的逐套接字自动调优；不要把这一点与设置 sysctl 最小值/默认值/最大值混淆。

### qdisc

如果确认节点内存在丢弃（`tc -s qdisc` 中的 `dropped`），应检查此处。

- **`fq_codel`**：缓解 bufferbloat（延迟是问题时）
- **`fq`**：流量整形/pacing（使用 bbr 时）
- 增大队列长度（`txqueuelen`）可以减少丢弃，但会**增加延迟**。应在了解这一权衡后再决定。

### 中断分布

如果 `/proc/interrupts` 显示中断集中在一个核心上，而 `mpstat -P ALL` 显示该核心的 `%soft` 暴增，请检查 RSS/RPS/RFS。话虽如此，**当前 ENA 驱动和实例类型默认使用多队列与 RSS**，因此这种情况很少成为问题。

### kube-proxy 模式

这不是节点内核参数，但它对数据平面性能的影响最大。

| 情况 | 建议 |
|---|---|
| 大量 Service，使用 iptables 模式 | **考虑改用 nftables 模式**：在 1.33 达到 GA，支持 O(1) 查找和增量更新。需要 kernel 5.13+（AL2023 满足要求） |
| **正在运行 IPVS 模式** | **需要迁移计划**：1.35 已弃用；上游计划在 1.40 默认禁用、1.43 移除。建议替换为 nftables |
| 保持默认设置 | 即使 nftables 已 GA，**默认仍是 iptables**；切换需要显式决定 |

## 存储

| 参数 | 内容 |
|---|---|
| **I/O 调度器** | NVMe 通常使用 `none`（或 `mq-deadline`）。NVMe 上复杂调度器带来的收益很小 |
| `vm.dirty_ratio` / `dirty_background_ratio` | 写缓冲区大小；会影响突发写入时的延迟表现 |
| **临时存储** | 与内核参数相比，真正的问题是 **overlayfs copy-up 开销**；应将大量写入路径迁移到卷上（参见[容器背后的内核功能](./01-container-primitives.md)） |
| **EBS 性能** | 不是内核问题，而是卷类型、IOPS 和吞吐量设置问题（参见 [EBS gp2 与 gp3 基准测试](../storage/01-ebs-gp2-gp3-benchmark.md)） |

## 按工作负载选择

以下表格从症状出发。

| 工作负载 | 常见的必要调整 | 证据计数器 |
|---|---|---|
| **高连接数网关/代理** | conntrack 上限、`somaxconn`、`ip_local_port_range` | `insert_failed`、`TcpExtListenOverflows`、端口耗尽 |
| **对延迟敏感（交易、实时）** | 重新评估 CPU 限额、CPU Manager static policy、`fq_codel` | `cpu.stat` 节流、`cpu.pressure` |
| **高吞吐量（批处理、数据）** | 缓冲区上限（仅限长距离路径）、`netdev_max_backlog` | qdisc `dropped`、softirq 分布不均 |
| **搜索/索引（OpenSearch 等）** | **`vm.max_map_count`**、文件描述符限制 | 启动失败日志 |
| **高密度节点** | `kernel.pid_max`、kubelet 预留、驱逐阈值 | PID 耗尽、节点 `NotReady` |
| **区块链节点** | 文件描述符、磁盘 IOPS、套接字缓冲区 | [区块链节点运维](../blockchain/02-nodes-on-eks.md) |

## 如何管理更改

从长期来看，比具体调优值更重要的是**如何管理这些更改**。

| 原则 | 原因 |
|---|---|
| **以代码管理**（Karpenter `EC2NodeClass`、启动模板、Bottlerocket 设置） | 避免各节点上的值不一致 |
| **在注释中记录原因** | 如果六个月后没人知道“为什么选这个值”，也就没人能安全地撤销 |
| **拆分节点组** | 不同工作负载特征需要不同调优方式；不要强行让所有工作负载共用一种配置 |
| **固定内核版本或规划迁移** | `kernel-default` AMI 会悄然切换内核版本 |
| **应用后验证实际值** | 尤其要检查 conntrack（其他组件可能会覆盖设置） |
| **在相同条件下测量修改前后数据** | 没有测量的调优会变成迷信 |

## 总结

- **大部分设置保持默认值**。内核会在负载下自动调优；缺少依据的调优会造成配置无法复现，并在内核升级时引发故障。
- 调优的前提是测量。**从丢弃计数器开始**：`insert_failed`、qdisc `dropped`、NIC 丢弃计数。
- 确认选定的 AMI 和正在运行的内核。默认 AMI 系列可能会升级；固定的 AMI ID 不会在替换节点时自动改变。
- CPU 节流的根本原因通常是**应用感知到的 CPU 数量与实际配额不一致**。从 `GOMAXPROCS`/`ActiveProcessorCount` 开始检查。
- 为保证节点稳定性，**kubelet 资源预留和驱逐阈值**比内核调优更重要。驱逐优于内核 OOM。
- 有依据的典型调整包括 **conntrack 上限、`somaxconn`、`ip_local_port_range` 和 `vm.max_map_count`**；这些都有直接的证据计数器。
- TCP sysctl 边界和逐套接字自动调优覆盖是两回事；只有在测量有依据时才调整。
- **如果使用 IPVS 模式，就需要迁移计划**（1.35 已弃用；计划在 1.40 默认禁用、在 1.43 移除）。上线前请确认下方链接的 KEP-5495 维护时间表。

## 参考资料

- [Amazon Linux 2023：更新 Linux 内核](https://docs.aws.amazon.com/linux/al2023/ug/kernel-update.html)
- [Amazon EKS 优化版 Amazon Linux 2023 AMI](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
- [提高 EKS 节点上的 nf_conntrack_max 限值](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [在 nftables 模式下运行 kube-proxy：EKS 最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [KEP-5495：弃用 kube-proxy 的 IPVS 模式](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [EEVDF 调度器：Linux 内核文档](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [kernel/sched/debug.c：debugfs 可调参数定义](https://github.com/torvalds/linux/blob/master/kernel/sched/debug.c)
- [bottlerocket-os/bottlerocket#4221：conntrack 限额未应用](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [PSI：压力停滞信息](https://docs.kernel.org/accounting/psi.html)
- [为系统守护进程预留计算资源（Kubernetes）](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [在 Kubernetes 集群中使用 sysctl](https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/)
- [资源优化](../ops/10-resource-optimization.md) / [Pod 网络基准测试](../networking/06-pod-network-benchmark.md)
