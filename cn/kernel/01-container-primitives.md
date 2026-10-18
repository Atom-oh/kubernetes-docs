# 容器背后的内核功能

> **支持版本**：Linux 6.1 / 6.12 / 6.18（Amazon Linux 2023），Kubernetes 1.25+（cgroup v2）
> **最后更新**：2026 年 10 月 16 日

## 本文涵盖内容

- 哪些内核功能组合起来构成容器，以及内核中不存在“container”对象这一事实
- 从 cgroup v1 迁移到 v2 后，运维层面实际发生了哪些变化（尤其是 OOM 诊断）
- netfilter 和 conntrack 在 Kubernetes 网络中的位置

## 首先：内核中没有“容器”

这是理解容器的起点。内核中没有 `struct container`，也没有一个创建容器的系统调用。

容器是**多种独立内核功能组合而成的一种约定**。运行时（containerd、runc）启动进程时，会同时应用这些功能。

| 目的 | 内核功能 |
|---|---|
| **它可以看到什么**（隔离） | 命名空间 |
| **它可以使用多少资源**（限制） | cgroups |
| **它可以执行哪些操作**（权限） | capabilities、seccomp、LSM（AppArmor/SELinux） |
| **文件系统如何组合** | overlayfs（联合挂载） |
| **流量如何传输** | veth、bridge/route、netfilter |

由此可以得出两个实际结论。

**第一，隔离并非非黑即白**。某些命名空间可以共享，而其他命名空间彼此隔离。Kubernetes Pod 正是如此：同一 Pod 中的容器**共享**网络和 IPC 命名空间，而挂载和 PID 命名空间通常**彼此独立**。因此，同一 Pod 中的容器可以通过 `localhost` 互相访问（共享网络），却看不到彼此的文件系统（挂载点独立）。

**第二，忘记设置的隔离会形成隐蔽缺口**。内核并不知道“创建一个容器”这回事；如果运行时没有应用 seccomp 配置文件，工作负载就会在没有该配置的情况下运行。这就是容器安全需要通过运行时和策略配置来实现的原因。

## 命名空间：它可以看到什么

命名空间会**隔离内核资源的“名称空间”**，因此相同的名称或编号在不同命名空间中可能代表不同对象。

| 命名空间 | 隔离内容 | 在 Pod 中的情况 |
|---|---|---|
| **mnt** | 挂载点 | 每个容器独立 |
| **pid** | 进程 ID | 每个容器独立（`shareProcessNamespace: true` 时 Pod 内共享） |
| **net** | 接口、路由表、netfilter 规则、套接字、端口 | **每个 Pod 内共享** |
| **ipc** | System V IPC、POSIX 消息队列 | 每个 Pod 内共享 |
| **uts** | hostname、domainname | 每个 Pod 内共享 |
| **user** | UID/GID 映射 | 默认不使用（见下文） |
| **cgroup** | cgroup 根路径 | 每个容器独立 |
| **time** | 启动时间、单调时钟（5.6+） | 不使用 |

### 为什么 net 命名空间构成 Pod 边界

Pod 的网络身份由此决定。Kubernetes 会为每个 Pod 创建一个 net 命名空间（由 pause 容器持有），并将**该 Pod 的所有容器放入同一个 net 命名空间**。

由此可知：

- Pod 中的容器共享**同一个 IP 和同一套端口空间** → 同一 Pod 中的两个容器不能同时绑定 8080
- 可以通过 `localhost` 通信 → 这是 Sidecar 模式的基础
- **netfilter 规则也按 net 命名空间隔离** → 因此 Sidecar 网格的 init 容器可以在 Pod 的 net 命名空间中安装 iptables 规则，而这些规则不会影响整台节点（参见 [VPC Lattice 内核数据路径](../service-mesh/vpc-lattice/07-kernel-datapath.md)）
- 路由表同样相互独立 → Pod 内的 `ip route` 不是节点的路由表

### user 命名空间：为什么它长期以来都不是默认选项

user 命名空间会将容器的 UID/GID 映射到主机上的另一组范围。这样可以降低许多逃逸操作所具有的权限，但**不能保证**容器不受内核漏洞或其他权限提升路径影响。

但 user 命名空间长期以来并非默认选项，原因是**文件所有权**。卷上的文件以主机 UID 记录；如果容器看到的 UID 不同，权限就无法匹配。要解决此问题，需要在挂载时转换 UID（idmapped mounts，内核 5.12+），而且存储驱动和 CSI 也必须支持该功能。

### Kubernetes user 命名空间支持状态

根据 [Kubernetes 功能门控参考](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)和 [v1.36 GA 公告](https://kubernetes.io/blog/2026/04/23/kubernetes-v1-36-userns-ga/)，各成熟阶段如下（设计文档：[KEP-127](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/kep.yaml)）：

| 阶段 | 版本 |
|---|---|
| alpha | v1.25 |
| beta | v1.30（从 v1.33 起默认启用） |
| **稳定（GA）** | **v1.36** |

功能门控为 `UserNamespacesSupport`，适用于 kubelet 和 kube-apiserver。**从 1.36 开始，该功能已 GA，因此无需启用功能门控即可使用 `hostUsers: false`。**

::: warning 需要核实
这些成熟阶段针对上游 Kubernetes。**EKS 是否提供相应版本，以及你的容器运行时和 CSI 驱动是否支持 idmapped mounts，是另外两个问题**。采用之前，请确认 EKS 支持的版本以及你的运行时/存储组合。
:::

## cgroups：它可以使用多少资源

cgroups（控制组）**用于衡量并限制一组进程的资源使用量**。Kubernetes 的 `requests`/`limits` 最终会落实到这里。

### v1 与 v2 的结构差异

| 项目 | cgroup v1 | cgroup v2 |
|---|---|---|
| **层级结构** | **每个控制器各有一棵树**（cpu、memory、blkio 等） | **一棵统一的树** |
| **进程归属** | 可在不同控制器中属于不同组 | 恰好属于一个组 |
| **内存与 IO 协同** | 较困难（不同树无法协调） | 可以协同（同一棵树） |
| **压力信息** | 无 | **PSI**（`cpu.pressure`、`memory.pressure`、`io.pressure`） |
| **CPU 限额表示** | `cpu.cfs_quota_us` / `cpu.cfs_period_us` | `cpu.max`（一个文件：“quota period”） |
| **内存限制表示** | `memory.limit_in_bytes` | `memory.max`，以及表示软压力的 `memory.high` |
| **AL2023 EKS AMI** | - | **默认使用** |

v1 的“每个控制器一棵独立树”实际上会影响**内存回收与 IO 的协调**。内存不足时必须丢弃页缓存，而这一回收过程本身会产生磁盘 IO；在 v1 中，内存和 IO 两个控制器彼此不了解。v2 的统一层级可以同时处理两者。

### 2026 年 10 月更新：cgroup v1 弃用进程

Kubernetes 博客总结了 cgroup v1 向 v2 迁移的现状（[Kubernetes 转向 cgroup v2](https://kubernetes.io/blog/2026/10/06/kubernetes-cgroups-v2-shift/)，2026-10-06）。从 v1.25 起，cgroup v2 管理已稳定；从 v1.31 起，cgroup v1 支持进入维护模式；**从 v1.35 起，kubelet 的 `failCgroupV1` 默认值为 `true`，因此默认情况下 kubelet 不再于 cgroup v1 节点上启动。在** kubelet 配置中设为 `failCgroupV1: false` 是临时覆盖；完全移除该支持的工作由 KEP-5573 跟踪。在 kubeadm 集群上，使用 v1.35 或更高版本 kubelet 时，SystemVerification 预检会将 cgroup v1 判定为错误；较旧的 kubelet 则会发出警告。如果当前版本早于 v1.35，请在升级前将所有 Linux 节点迁移到 cgroup v2。

### 最大的运维变化：OOM 诊断

你必须了解 cgroup v2 的这一点：

> **`memory.current` 包括页缓存。**

因此，即使应用实际持有的内存（anon/RSS）远低于限制，读取大量文件也会积累页缓存，并使 `memory.current` 达到限制。

这里有一个重要区别。**页缓存可以回收**。在正常情况下，内核达到限制后会丢弃页缓存以腾出空间，不会发生 OOM。问题出现在**回收速度跟不上内存分配速度**时；此时 OOM killer 才会介入。

实际影响：

| 误解 | 实际情况 |
|---|---|
| “`memory.current` 接近限制就表示即将发生 OOM” | 其中可能包含可回收的文件缓存；应检查 anon/file/kernel 使用量和压力，不要假定其组成 |
| “只看 RSS 就够了” | 即使 RSS 较低也可能发生 OOM（回收速度跟不上时） |
| “提高限制就能解决问题” | 如果原因是回收速度慢，问题还会再次出现 |

**诊断时要查看的值：**

| 文件/数值 | 含义 |
|---|---|
| `memory.current` | 当前使用量（包括页缓存） |
| `memory.stat` → `anon` | 匿名内存（应用实际持有的内存） |
| `memory.stat` → `file` | 页缓存 |
| `memory.events` → `oom` / `oom_kill` | OOM 发生次数 / OOM 终止次数 |
| `memory.events` → `high` / `max` | 命中软/硬限制的次数 |
| `memory.pressure`（PSI） | 内存压力导致**停滞的时间比例** |

**PSI 尤其有用**，因为它报告的是**压力（因此等待了多长时间）**，而不是使用量（正在使用多少资源）。`memory.pressure` 中的 `some avg10` 持续升高，意味着时间消耗在内存回收上；仅看使用量图表不会发现这一点。

### CPU 限制与节流：为什么利用率低仍可能很慢

CPU 限制是一种**带宽限制**。`cpu.max` 为 `20000 100000` 表示“每 100ms 周期最多使用 20ms”。

接下来会出现一个反直觉的现象：如果应用通过多个线程在短时间内集中完成工作，它会**在周期开始后很快用完整个配额，然后被强制暂停，直到周期结束**。平均利用率看起来只有 20%，延迟却会突然升高。

多线程时情况更明显。4 个线程并发运行时，20ms 配额只需 5ms 墙上时间就会用完；剩余 95ms 都在等待。

**诊断**：查看 `cpu.stat` 中的 `nr_throttled`（发生节流的周期数）和 `throttled_usec`（累计节流时间）。如果 `nr_throttled` 占 `nr_periods` 的比例不可忽略，原因就是限额。

**应对方向**（请求/限额设计见[资源优化](../ops/10-resource-optimization.md)）：

- 提高或移除限额（需要权衡节点稳定性）
- 使应用线程数与限额相匹配（JVM `-XX:ActiveProcessorCount`、Go `GOMAXPROCS` 等）；**容器感知到的 CPU 数量与实际配额不一致，往往是根本原因**
- 使用 `cpu.pressure` PSI 检查实际停滞时间

## 权限：它可以做什么

即使命名空间隔离和 cgroups 限额都已设置，限制进程可以执行的**操作**仍是独立的一层。

| 功能 | 作用 | 在 Kubernetes 中的配置 |
|---|---|---|
| **capabilities** | 将 root 权限细分后授予/移除（`CAP_NET_ADMIN`、`CAP_SYS_ADMIN` 等） | `securityContext.capabilities.add/drop` |
| **seccomp** | 限制可用的**系统调用**集合 | `securityContext.seccompProfile`（推荐 `RuntimeDefault`） |
| **LSM**（AppArmor/SELinux） | 按策略控制文件和网络访问 | `securityContext.appArmorProfile` 等 |
| **no_new_privs** | 阻止通过 setuid 二进制文件提升权限 | `allowPrivilegeEscalation: false` |

这三层回答不同的问题：capabilities 检查“是否持有此权限”，seccomp 检查“是否允许调用此系统调用”，LSM 检查“是否允许访问此对象”。**单独使用任何一层都不够；通常要叠加使用。**

值得单独说明 `CAP_NET_ADMIN`。Sidecar 网格的 init 容器需要它来安装 iptables 规则，因此采用网格后，安全评审会提出“这个 Pod 为什么持有 NET_ADMIN？”

## netfilter 和 conntrack：Kubernetes 网络的实际情况

### netfilter

netfilter 是一个框架，在内核网络栈的特定位置提供**钩子**。`iptables`、`nftables` 和 `ipvs` 都是使用这些钩子的用户空间工具，或构建在其上的实现。

主要钩子位置：

| 钩子 | 时机 |
|---|---|
| `PREROUTING` | 数据包到达时，路由决策**之前**（DNAT 位置） |
| `INPUT` | 发往本地进程的数据包 |
| `FORWARD` | 正在经过本机转发的数据包 |
| `OUTPUT` | 从本机发出的数据包 |
| `POSTROUTING` | 路由之后、发出之前（SNAT/MASQUERADE 位置） |

这些钩子在 Kubernetes 中的用途：

- **Service ClusterIP → Pod IP 地址转换**：在 `PREROUTING`/`OUTPUT` 执行 DNAT
- **Pod → 外部流量的源地址转换**：在 `POSTROUTING` 执行 MASQUERADE
- **NetworkPolicy**：CNI 在 `FORWARD` 等位置插入规则（Calico 的 iptables 数据平面）
- **Sidecar 网格流量截获**：在 Pod net 命名空间内部的 `OUTPUT`/`PREROUTING` 执行 REDIRECT

### kube-proxy 模式：iptables、IPVS、nftables

Service 有三种实现模式，**而且 2025–2026 年间的格局发生了变化**。

| 模式 | 规则评估 | 状态 |
|---|---|---|
| **iptables** | 规则链查询成本取决于规则布局；当前 kube-proxy 会优化更新过程 | 未明确更改时的默认模式；请确认实际安装的实现 |
| **IPVS** | 内核 L4 负载均衡器，基于哈希的 O(1) | **已于 Kubernetes 1.35（2025 年 12 月）弃用**；计划在 1.40 默认禁用、在 1.43 移除 |
| **nftables** | O(1) 查找，且支持**增量更新规则** | **在 Kubernetes 1.33 达到 GA**（1.29 alpha → 1.31 beta）。工作节点需要 **kernel 5.13+** |

解读方式：

- **大型集群中，iptables 模式的瓶颈是规则数量和更新开销**。Service 和 Endpoint 越多，kube-proxy 同步所需时间就越长；在同步期间规则不是最新状态。
- **如果使用 IPVS，就需要迁移计划**。上游计划在 1.40 默认禁用，并在 1.43 移除；规划时请确认维护中的 [KEP-5495 时间表](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)。建议替换为 nftables 模式。
- AL2023 节点运行 6.x 内核，因此满足 nftables 模式的内核要求。
- 即使 nftables 已达到 GA，**默认模式仍是 iptables**；必须显式切换。

### conntrack：最常见的故障来源

netfilter 要执行 NAT，就必须**记住连接状态**。如果在出站时重写了地址，返回时就必须撤销重写。用于保存这些状态的内核表就是 `nf_conntrack`。

在 kube-proxy 的 netfilter 模式中，Service NAT 依赖连接跟踪。不过，**非 NAT 流量也可能被跟踪**；headless Service、外部 Endpoint 和 eBPF 实现也会使用不同路径。不要把每个 Kubernetes Service 都等同于一个必然经过的 DNAT 路径。

**表耗尽时会发生什么，这是问题的关键**。不会出现醒目的错误。新连接会被**静默丢弃**，应用看到的则是连接超时或拒绝。仅从应用一侧无法得知原因。

| 观察位置 | 含义 |
|---|---|
| `/proc/sys/net/netfilter/nf_conntrack_count` | 当前条目数 |
| `/proc/sys/net/netfilter/nf_conntrack_max` | 上限 |
| `conntrack -S` → `insert_failed` | 插入失败数；应与当前条目数/上限、丢弃数和内核日志关联，不能单独据此认定表已耗尽 |
| `conntrack -S` → `drop` | 丢弃的数据包数 |
| `dmesg` → `nf_conntrack: table full, dropping packet` | 内核警告 |

**一项 EKS 专属注意事项**。kube-proxy 也会管理 conntrack 数值，而且 **EKS 默认提供 `kube-proxy-config` ConfigMap，其设置优先于命令行参数**。因此，即使提高节点上的 sysctl，kube-proxy 也可能再将其改回去。正确的做法是在 ConfigMap 中调整 `conntrack.maxPerCore`/`conntrack.min`，然后重启 kube-proxy DaemonSet。

提高 `nf_conntrack_max` **会增加节点内存使用量**。每个条目都占用内存，因此不能无限提高；其值必须与节点规格相符。具体设置见 [EKS 节点内核调优](./03-eks-node-tuning.md)。

::: warning 验证实际生效的 kube-proxy 配置
一份历史 Bottlerocket 报告显示，节点 sysctl 值可能被 kube-proxy 覆盖。使用 `--config` 时，应修改**生效配置**（`conntrack.maxPerCore` 和 `conntrack.min`），而不是会被其覆盖的 CLI 标志。将两者都设为 0 表示有意让节点 sysctl 决定上限；请根据已部署的附加组件/版本确认行为，并验证最终的节点值。务必保留节点内存预算。
:::

这项历史问题不能证明所有当前 Bottlerocket 版本都会有相同表现。推出更改后，请检查生效配置和实际 sysctl。

### 降低 conntrack 压力

以下方法可以降低其负载。

- Headless Service 会避开 Service VIP DNAT，但**不会自动绕过 conntrack**。
- Cilium 可以用 eBPF 映射替代 kube-proxy/netfilter 功能；应测量其自身的跟踪/映射压力，并检查是否仍有 netfilter 路径。
- 重用连接可以减少连接周转；同时验证已建立连接的容量和超时行为。

## overlayfs：镜像层如何组合

容器镜像中的层最终呈现为一个文件系统，这种做法属于**联合挂载**，具体实现是 `overlayfs`。

主要有三个部分：

| 层 | 作用 |
|---|---|
| **lowerdir** | 只读：镜像层（可以叠加多个镜像层） |
| **upperdir** | 可写：容器所做的更改 |
| **merged** | 容器看到的组合视图 |

运维上重要的特性是 **copy-up**。修改 lowerdir 中的文件前，系统会先将**整个文件复制到 upperdir**，然后才修改。因此：

- **即使只稍微修改大型文件，也要承担完整的复制成本**。修改 1GB 文件中的一个字节也会复制 1GB
- 在容器中大量写入会消耗节点磁盘（临时存储）
- **大量写入的路径应放在卷上**（例如 emptyDir、PVC 等）

## 总结

- 内核中没有“容器”对象。容器是命名空间（隔离）+ cgroups（限制）+ capabilities/seccomp/LSM（权限）+ overlayfs（文件系统）+ netfilter（网络）的**组合**。因此隔离可以按需选择，而遗漏的隔离会形成隐蔽缺口。
- **net 命名空间构成 Pod 边界**。共享 IP/端口空间、`localhost` 通信和 Pod 范围的 netfilter 规则都由此而来。
- 在 cgroup v2 中，**`memory.current` 包括页缓存**。OOM 诊断需要结合 `memory.stat` → `anon`、`memory.events` 和 **PSI（`memory.pressure`）**。
- CPU 限制属于**带宽限制**，因此即使利用率低，节流也会导致延迟激增。证据可查看 `cpu.stat` → `nr_throttled`。
- 对于 kube-proxy，**nftables 在 1.33 达到 GA，IPVS 在 1.35 弃用**；上游计划于 1.40 默认禁用 IPVS、于 1.43 移除。默认仍为 iptables。
- conntrack 耗尽时可能丢弃新连接。应结合条目数/上限、drop/insert 计数器和日志进行诊断；调整限额之前，先检查生效的 kube-proxy 配置。

下一篇：[内核网络栈](./02-network-stack.md)将介绍数据包经过的完整路径。

## 参考资料

- [控制组 v2：Linux 内核文档](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [PSI：压力停滞信息](https://docs.kernel.org/accounting/psi.html)
- [namespaces(7)：Linux 手册](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [KEP-127：支持 User Namespaces](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/README.md)
- [bottlerocket-os/bottlerocket#4221：conntrack 限额未应用](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [kube-proxy 的 NFTables 模式（Kubernetes 博客）](https://kubernetes.io/blog/2025/02/28/nftables-kube-proxy/)
- [KEP-5495：弃用 kube-proxy 的 IPVS 模式](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [在 nftables 模式下运行 kube-proxy：EKS 最佳实践](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [提高 EKS 节点上的 nf_conntrack_max 限值](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [Amazon EKS 优化版 Amazon Linux 2023 AMI](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
