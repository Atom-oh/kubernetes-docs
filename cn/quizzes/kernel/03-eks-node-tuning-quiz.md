# EKS 节点内核调优测验

本测验检查你对参数应用路径、内核版本变更和有依据的调优的理解。

## 选择题

1. 缺乏依据的内核调优会造成哪三类问题？
   - A) 安全漏洞、许可证违规、失去支持
   - B) 配置无法复现、内核升级时出现故障、破坏内核自动调优
   - C) 网络带宽降低、磁盘使用量增加、内存泄漏
   - D) Pod 调度失败、镜像拉取失败、身份验证失败

<details>

<summary>显示答案</summary>

**答案：B) 配置无法复现、内核升级时出现故障、破坏内核自动调优**

**说明：**
每个节点上的参数值不同，会让故障难以复现。可调参数名称及其位置会随内核版本变更（例如从 sysctl 移到 debugfs），因此在 6.1 上有效的设置可能会在 6.18 上失效。显式设置每个 socket 的 `SO_RCVBUF`/`SO_SNDBUF` 会禁用相应 socket 的自动大小调整；仅更改 `tcp_rmem`/`tcp_wmem` 的范围本身并不会禁用自动调优。因此，调优的前提是先测量：将症状与相关计数器关联，并且只调整有这些证据支持的设置。
</details>

2. 截至 2026 年，对于 AL2023 的内核版本变更，必须了解什么？
   - A) AL2023 只提供内核 6.1
   - B) 更新的默认/最新 AMI 可能会选择新内核，而固定的 AMI ID 不会变化
   - C) 内核版本由 EKS 控制平面版本自动决定
   - D) AL2023 不支持内核升级

<details>

<summary>显示答案</summary>

**答案：B) 更新的默认/最新 AMI 可能会选择新内核，而固定的 AMI ID 不会变化**

**说明：**
应验证启动模板/置备程序选用的 AMI，以及正在运行的内核。EKS 优化型 AMI 版本有各自的选择方式；仅仅替换节点并不能证明内核已升级。
</details>

3. CPU throttling 最常见的根本原因是什么，首先应如何应对？
   - A) 节点 CPU 不足：改用更大的实例类型
   - B) 应用程序感知到的 CPU 数量与其配额不匹配：使 `GOMAXPROCS`、`-XX:ActiveProcessorCount` 等设置与限制对齐
   - C) 内核调度器错误：升级内核
   - D) cgroup v2 迁移问题：回退到 v1

<details>

<summary>显示答案</summary>

**答案：B) 应用程序感知到的 CPU 数量与其配额不匹配：使 `GOMAXPROCS`、`-XX:ActiveProcessorCount` 等设置与限制对齐**

**说明：**
如果容器内的运行时看到节点的所有核心并据此创建线程，就会立即耗尽 CPU 限额。若 4 个线程并发运行，20 毫秒的配额会在 5 毫秒的实际时间内耗尽，之后 95 毫秒都只能等待。因此，首先应让应用程序感知到的 CPU 数量与限制对齐，然后提高限制，最后再考虑对极度敏感的情况移除限制。
</details>

4. 什么方法比内核调优更能提升节点稳定性，为什么？
   - A) 限制 Pod 数量：降低密度可避免问题
   - B) 配置 kubelet 资源预留和驱逐阈值：预留不足会导致内核或 kubelet 自身遇到 OOM，使整个节点变为 `NotReady`；驱逐优于内核 OOM
   - C) 安排节点重启：定期重启以清理内存
   - D) 使用更小的镜像：释放磁盘空间

<details>

<summary>显示答案</summary>

**答案：B) 配置 kubelet 资源预留和驱逐阈值：预留不足会导致内核或 kubelet 自身遇到 OOM，使整个节点变为 `NotReady`；驱逐优于内核 OOM**

**说明：**
如果 `--system-reserved` 和 `--kube-reserved` 设置不足，Pod 就会耗尽节点内存，导致内核或 kubelet 遇到 OOM。节点会变为 `NotReady`，其上的所有 Pod 都会受到影响，远比单个 Pod 遇到 OOM 严重。驱逐是 Kubernetes 有序地迁移 Pod；而 OOM killer 会突然终止进程，因此应设置 `--eviction-hard`，让 Kubernetes 在内核 OOM 发生前介入。
</details>

5. 为什么 PSI（Pressure Stall Information）比使用率指标提供更好的信号？
   - A) 它能更准确地测量使用量
   - B) 它报告资源造成停滞的时间比例，而不是使用量，因此即使使用率图表看似平静，也能显示回收或争用耗费的时间
   - C) 它由硬件而非内核采集
   - D) 它会自动保留历史数据

<details>

<summary>显示答案</summary>

**答案：B) 它报告资源造成停滞的时间比例，而不是使用量，因此即使使用率图表看似平静，也能显示回收或争用耗费的时间**

**说明：**
`memory.pressure` 中的 `some avg10` 表示过去 10 秒内至少有一个任务因该资源而停滞的时间比例。即使内存使用量看起来平稳且低于限制，数值持续上升也说明时间耗费在页缓存回收上，这是单靠使用率图表无法显示的。该信息由 cgroup v2 提供：节点级数据位于 `/proc/pressure/*`，每个 cgroup 的数据位于 `<cgroup>/memory.pressure`。
</details>

6. 以下哪项不属于“有依据的调优”的典型案例？
   - A) `vm.max_map_count`：OpenSearch 系列软件在默认值下无法启动
   - B) `net.core.somaxconn`：有来自 accept 队列溢出计数器的证据
   - C) 没有测得 BDP/内存问题，也不了解每个 socket 的覆盖行为，就更改 TCP 缓冲区设置
   - D) `net.ipv4.ip_local_port_range`：源端口耗尽直接表现为连接失败

<details>

<summary>显示答案</summary>

**答案：C) 没有测得 BDP/内存问题，也不了解每个 socket 的覆盖行为，就更改 TCP 缓冲区设置**

**说明：**
`tcp_rmem`/`tcp_wmem` 定义大小范围/默认值；更改它们本身不会禁用自动调优。显式设置 `SO_RCVBUF`/`SO_SNDBUF` 会禁用相应 socket 的自动大小调整。
</details>

7. 哪项值不能通过 Pod 的 `securityContext.sysctls` 更改？
   - A) 许多可在每个网络命名空间中设置的 `net.*` 值
   - B) 属于节点全局设置的 `net.netfilter.nf_conntrack_max`
   - C) 属于 Pod 网络命名空间的 TCP 相关值
   - D) 以上值都可以更改

<details>

<summary>显示答案</summary>

**答案：B) 属于节点全局设置的 `net.netfilter.nf_conntrack_max`**

**说明：**
许多 `net.*` 值可以按网络命名空间设置，并可通过 Pod 的 `securityContext.sysctls` 更改。相比之下，`vm.*`、`fs.*` 以及 `net.netfilter.nf_conntrack_max` 等部分值属于节点全局设置，需要通过节点 bootstrap 或 Bottlerocket 设置路径配置。此外，kubelet 默认会拒绝“不安全”的 sysctl；允许使用某个值需要设置 `--allowed-unsafe-sysctls`，而这本身也是节点设置。
</details>

8. 长期管理内核参数变更时，最重要的是什么？
   - A) 始终升级到最新内核
   - B) 将配置作为代码管理、在注释中记录原因，并按工作负载特点划分节点组
   - C) 强制所有节点使用完全相同的调优配置
   - D) 立即在生产环境中应用变更

<details>

<summary>显示答案</summary>

**答案：B) 将配置作为代码管理、在注释中记录原因，并按工作负载特点划分节点组**

**说明：**
使用 Karpenter `EC2NodeClass`、启动模板或 Bottlerocket 设置将参数配置为代码，可避免各节点的值不一致。如果没有注释说明“为何使用此值”，六个月后就没人知道是否能回退。不同的工作负载特点需要不同的调优，因此应划分节点组，而不是强制使用同一配置。此外，还应固定内核版本或规划版本迁移、应用后验证实际值（尤其是 conntrack），并在相同条件下进行前后测量。
</details>
