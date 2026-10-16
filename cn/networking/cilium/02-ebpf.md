# eBPF 技术深度解析

> **审核基线**：Cilium 1.20.2、Linux 5.10+ 或有文档记录的等效回移版本（例如 RHEL 8.10 的 4.18 内核），已测试 Kubernetes 1.33–1.36。各项 BPF 功能具有各自的要求。
> **最后更新**：October 15, 2026

## 实验环境设置

使用一次性的 Linux 开发 VM，其中应运行受维护的发行版、具备下方使用的 tracepoint，并且允许加载 tracing 程序。这与安装 Cilium 无关；不要在集群节点上加载实验性程序。Linux 6.12 是下述 verifier 讨论的源码参考，并不代表所有 6.12 发行版都启用了每项功能。

必需工具包括带 BPF 后端的 Clang、目标架构 UAPI 头文件、libbpf 1.x 开发头文件/库、libelf、zlib、C 编译器和 bpftool。BCC 和 bpftrace 是可选替代方案。Debian/Ubuntu 常见的软件包名包括 `clang`、`libbpf-dev`、`libelf-dev`、`zlib1g-dev`、`build-essential` 和 `pkg-config`；bpftool 的打包方式取决于发行版/内核。不要假设每个 Debian 系统都有 `linux-tools-generic` 或其适用。Cilium 的文档说明支持 AMD64/AArch64 主机；在其容器镜像外原生运行 Cilium 还需要 Clang/LLVM 18.1+，这与这个小型 tracing 实验室是独立要求。

```bash
uname -r
clang --version
clang --print-targets
pkg-config --modversion libbpf
bpftool version
test -r /sys/kernel/tracing/events/syscalls/sys_enter_execve/format
test -r /sys/kernel/tracing/events/sched/sched_process_exec/format
# Active feature probing: run only on the prepared lab VM.
sudo bpftool feature probe kernel
```

必须挂载且可访问 Tracefs；某些系统将其暴露在 `/sys/kernel/debug/tracing` 下。即使作为容器 root，内核配置、capability、lockdown/LSM 策略和容器限制也可能阻止加载或附加。`CAP_BPF` 并不是通用的 tracing 权限；要求取决于内核、程序类型和 BPF token 委派。

**验证边界：**这些示例已通过针对 libbpf 1.7 的主机 C 语法检查、用户空间链接和确定性的 helper 模拟。Clang BPF 目标编译、运行中的内核 verifier 和实时 tracepoint 附加仍需在准备好的 VM 中验证。它们并非经过生产测试或无丢失 tracing 的方案。

## eBPF 技术简介和历史背景

eBPF 允许获批准的程序在受支持的 Linux hook 上执行，以观察或影响内核行为。验证会限制内存访问和执行，但内核、verifier、JIT 和 helper 中的 bug 仍然可能存在。被接受并不能证明主机不会崩溃，也不能证明程序实现了预期策略。

### 从 BPF 到 eBPF：演进历史

McCanne 和 Jacobson 的 *The BSD Packet Filter: A New Architecture for User-level Packet Capture* 的预印本日期为 1992 年 12 月 19 日，并标明其在 1993 年 1 月 25–29 日的 Winter USENIX 上发表。引用年份时应保留这一差异。经典 BPF 使用 32 位 A/X 寄存器和暂存内存进行过滤，避免不必要地将数据包复制到用户空间。其受限指令集并不意味着它不能在现代 CPU 上执行。

扩展 BPF 添加了带 R0–R10 共十一个寄存器的 64 位指令集（R10 是只读帧指针）、通常限制为 512 字节的栈、map 和更多程序类型。这不是从十个到十一个通用寄存器的历史变化。函数/tail-call 组合可能施加额外的栈限制。

### eBPF 的技术演进：按内核版本划分的关键功能

以下选定的上游里程碑已根据带版本的源码核查。它们不是发行版支持矩阵；回移、构建选项、架构和 helper 各不相同。

| 内核 | 选定里程碑 |
|---|---|
| [3.15](https://github.com/torvalds/linux/blob/v3.15/include/linux/filter.h) | 扩展指令集；内部经典 BPF 转换 |
| [3.16](https://github.com/torvalds/linux/blob/v3.16/arch/x86/net/bpf_jit_comp.c) | x86 扩展 BPF JIT |
| [3.18](https://github.com/torvalds/linux/blob/v3.18/include/uapi/linux/bpf.h) | BPF syscall/验证基础设施；尚无可用的 HASH/ARRAY map 类型 |
| [3.19](https://github.com/torvalds/linux/blob/v3.19/include/uapi/linux/bpf.h) | HASH/ARRAY map 和 socket-filter 程序类型 |
| [4.1](https://github.com/torvalds/linux/blob/v4.1/include/uapi/linux/bpf.h) | KPROBE 和 TC SCHED_CLS/SCHED_ACT |
| [4.2](https://github.com/torvalds/linux/blob/v4.2/include/uapi/linux/bpf.h) | PROG_ARRAY 和 tail call |
| [4.8](https://github.com/torvalds/linux/blob/v4.8/include/uapi/linux/bpf.h) | XDP 程序类型 |
| [4.10](https://github.com/torvalds/linux/blob/v4.10/include/uapi/linux/bpf.h) | LRU hash map |
| [4.16](https://github.com/torvalds/linux/blob/v4.16/include/uapi/linux/bpf.h) | BPF 到 BPF 的函数调用 |
| [4.17](https://github.com/torvalds/linux/blob/v4.17/include/uapi/linux/bpf.h) | 原始 tracepoint |
| [4.18](https://github.com/torvalds/linux/blob/v4.18/include/uapi/linux/bpf.h) | BTF 加载 API |
| [5.2](https://github.com/torvalds/linux/blob/v5.2/include/uapi/linux/bpf.h) | 用于全局数据的直接 map value 访问 |
| [5.7](https://github.com/torvalds/linux/blob/v5.7/include/uapi/linux/bpf.h) | BPF link API 和 BPF LSM |
| [5.8](https://github.com/torvalds/linux/blob/v5.8/include/uapi/linux/bpf.h) | BPF ring buffer |
| [5.10](https://github.com/torvalds/linux/blob/v5.10/include/uapi/linux/bpf.h) | 适用于受支持附加类型的可休眠程序 |
| [5.15](https://github.com/torvalds/linux/blob/v5.15/include/uapi/linux/bpf.h) | BPF timer helper |
| [5.19](https://github.com/torvalds/linux/blob/v5.19/include/uapi/linux/bpf.h) | 动态指针 helper |
| [6.2](https://github.com/torvalds/linux/blob/v6.2/kernel/bpf/helpers.c) | 类型化对象分配 kfunc，而非不受限制的 malloc |

有界循环于 Linux 5.3 引入；[上游 verifier 变更](https://github.com/torvalds/linux/commit/2589726d12a1b12eaaa93c7f1ea64287e383c7a5)解释了循环分析和状态裁剪。设计 FAQ 中仍保留的旧版“未实现循环”段落并非当前功能指引。有界循环仍可能超出 verifier 的复杂度限制。

### 发展与应用领域

Cilium 的公共仓库创建于 2015 年 12 月；“项目始于 2017 年”的说法不准确。仓库创建不是精确的产品发布日期，也不能证明其是“首个主要项目”。

| 领域 | 示例和边界 |
|---|---|
| 网络 | Cilium/Calico datapath、Katran 负载均衡和 XDP 过滤 |
| 运行时安全 | Falco、Tracee 和 Tetragon 使用内核事件；强制执行取决于产品和 hook |
| Tracing | BCC（包括 Python/Lua 前端）、bpftrace、存储和 block-I/O tracing |
| 网络可观测性 | Hubble 流/proxy 事件；流图并非分布式应用 span tracing |
| Service mesh | Cilium 将内核转发与用户空间 proxy 结合，以提供受支持的 L7 功能 |
| 社区 | eBPF Foundation 支持该生态系统；资金和项目成熟度不是兼容性标准 |

`seccomp-bpf` 使用经典 BPF 过滤器接口来做 syscall 决策。Linux 可能在内部转换经典过滤器，但这不是通用的 eBPF 程序/map/helper API。

### eBPF 与传统内核模块：范式转变

| 特性 | eBPF | 内核模块 |
|---|---|---|
| 安全性 | 受 verifier 约束；实现 bug 和操作风险仍然存在 | 更广泛的原生内核访问；bug 可能使主机不稳定 |
| 部署 | 受支持的程序可在无需重启的情况下加载/附加 | 当依赖和使用情况允许时，许多模块同样可在无需重启的情况下加载/卸载 |
| 兼容性 | 指令/helper ABI 和功能要求；CO-RE 可重定位受支持的类型访问 | 内核/模块 ABI、配置和发行版支持 |
| 性能 | 通常 JIT 编译；hook、程序和工作负载决定开销 | 原生执行的成本同样取决于工作负载 |
| 开发 | 受限的上下文、helper/kfunc 和 verifier 限制 | 内核 API 和常规内核开发约束 |
| 权限 | 加载/附加所需的适当权限或委派 | 特权加载；签名/lockdown 可能限制它 |

两者都需要操作测试。模块并不限于供应商实现，eBPF 也不会天然地使生产部署安全。

## 内核内部 eBPF 架构深度分析

### eBPF 架构组件详细说明

在用户空间中，Clang 将 C 编译为 BPF ELF；Rust 使用其自身的编译器/toolchain 生态系统。libbpf 处理 ELF section、map、重定位、加载和受支持的附加 API。BCC 提供更高级的 API；bpftrace 提供 tracing 语言。

CO-RE 使用 BTF 和重定位来适配受支持的类型/字段访问。它不会提供缺失的 helper、程序类型或内核配置，也不保证任意跨架构/内核的兼容性。内核内部结构、tracepoint 格式和 kfunc 并不会仅因程序使用 BTF 就成为稳定 ABI。

在内核中，verifier 针对程序类型、上下文、helper 和权限检查程序。JIT 可将被接受的 BPF 转换为原生指令；在受支持的情况下，解释器是另一种执行机制。JIT 输出不会再通过强制的第二个 VM 阶段。附加会将已加载的程序连接到 hook；仅加载并不会订阅 tracepoint。

### eBPF 程序生命周期详细分析

1. **开发：**选择 hook/上下文，并定义 map/license 元数据。并非所有程序都需要 GPL 兼容性，但仅 GPL 的 helper 和某些类型/kfunc 会施加限制。这些 tracing 示例为所使用的 helper 采用 GPL 元数据。
2. **编译：**使用目标 toolchain 和头文件创建 BPF ELF 以及所需的 debug/BTF 信息。
3. **打开/加载：**解析 ELF、创建或显式复用 map、重定位并调用 BPF 加载 API。验证和可选的 JIT 在加载期间发生。
4. **附加：**使用适当的 API。libbpf 可从 `SEC("tracepoint/...")` 推断这些 tracepoint。保持 link/attachment 存活。
5. **运行/观察：**事件调用程序；用户空间读取 map/buffer。采样和容量限制可能丢失观察结果。
6. **更新/卸载：**仅在有意时保留兼容的 map/link/pin。销毁此实验室的 link 并关闭其 object 以释放资源。

在 Linux 6.12 中，BPF 能力加载路径的程序长度最多限制为 1,000,000 条指令，非特权路径为 4,096 条。verifier 还具有 1,000,000 条指令的独立**分析复杂度**限制。较小的程序也可能无法通过验证。非特权 BPF 通常被禁用；token/capability 和程序类型检查仍然适用。

### eBPF 程序类型和特性

| Hook / 程序类型 | 目的和返回值边界 |
|---|---|
| XDP / `BPF_PROG_TYPE_XDP` | 原生驱动 XDP 在 skb 分配之前运行；通用/卸载模式不同。`XDP_DROP`、`PASS`、`TX`、`REDIRECT` 是动作，并非吞吐量保证 |
| TC / `SCHED_CLS`, `SCHED_ACT` | 入站/出站数据包分类/动作。classifier 的 `TC_ACT_*` 语义需要合适的 direct-action 设置 |
| Socket filter / `SOCKET_FILTER` | Socket 数据包交付：零表示丢弃，正的捕获长度可能截断。创建/连接策略使用其他 hook |
| kprobe/uprobe / `KPROBE` | 内核/用户空间 probe；没有单独的 `BPF_PROG_TYPE_UPROBE`。内联、黑名单和符号可用性会限制附加 |
| Tracepoint / `TRACEPOINT` | 静态声明的事件上下文；检查目标格式。并非保证稳定的内核 ABI |
| Perf event / `PERF_EVENT` | 性能采样；返回行为取决于其 perf-event 集成 |
| cgroup / `CGROUP_SKB`, `CGROUP_SOCK`, `CGROUP_SOCK_ADDR`, etc. | 网络/socket 控制；上下文以及允许/拒绝约定各不相同 |
| LSM / `LSM` | MAC 风格的程序通常保留较早错误并返回零/错误；cgroup-LSM 具有不同的授权语义 |
| Socket operations / `SOCK_OPS` | TCP callback；操作、reply 字段和 helper 支持很重要 |
| fentry/fexit / `TRACING` | 在受支持情况下基于 BTF 的函数 tracing；目标和附加约束仍然存在 |

按可见性/控制需求选择 hook。XDP 缺少某些后续协议栈上下文；TC 处理由 skb 支撑的流量；tracepoint/probe 观察不会自动强制执行网络策略。不要跨程序类型复制上下文 struct 或返回码。

### eBPF Map：数据共享和状态存储的核心

Map 在引用仍存在时保持存活，例如 FD、已加载程序或显式 bpffs pin。Pin 不是磁盘持久化，也不会在重启后保留 map 内容。重新加载不会自动复用旧 map。

| 类型 | 用途和约束 |
|---|---|
| `HASH` | 有界键/值表；满时插入可能失败。预期的常数时间查找并非延迟保证 |
| `ARRAY` | 有效索引处预分配、零初始化的值；零不是缺失的 hash entry |
| `LRU_HASH` | 带 LRU 风格驱逐的有界缓存，而非无丢失的累计计数器 |
| `RINGBUF` | 跨 CPU 的多生产者/单消费者；键/值大小为零，字节容量为二的幂；失败的 reservation 不会阻塞 |
| `PERF_EVENT_ARRAY` | 每 CPU perf channel；用户空间必须配置/消费事件并跟踪丢失的 record |
| `PROG_ARRAY` | Tail-call 程序引用；适用兼容目标和调用限制 |
| `PERCPU_HASH` / `PERCPU_ARRAY` | 减少跨 CPU 争用，但并非在所有情况下无竞争。用户空间读取所有 possible-CPU slot 时需使用所需的 padding |
| `SOCKMAP` / `SOCKHASH` | 用于受支持重定向/程序的 socket 引用，并非任意 socket-operation hook |

libbpf 1.x 移除了 `struct bpf_map_def SEC("maps")`。这些 BTF 风格定义使用真实类型展示八种 map 类别。将所需 map 与合适程序组合；这些声明本身并非事件 pipeline。

**`map_types.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

/* Definitions only; combine the needed maps with a suitable program. */
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} hash_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} total SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u64);
} cache SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __type(key, __u32);
    __type(value, __u32);
    /* libbpf determines max_entries from the number of possible CPUs. */
} perf_events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PROG_ARRAY);
    __uint(max_entries, 10);
    __type(key, __u32);
    __type(value, __u32);
} jump_table SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} cpu_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_SOCKMAP);
    __uint(max_entries, 1024);
    __type(key, __u32);
    __type(value, __u32);
} sockets SEC(".maps");
```

共享计数器需要原子递增。新 hash key 需要通过 `BPF_NOEXIST` 插入，然后查找/递增获胜 entry；`BPF_ANY` 初始化可能覆盖另一 CPU 的计数。Array entry 在有效索引处已存在。

## 在 Cilium 中使用 eBPF：容器网络创新

### Cilium 架构和 eBPF 的作用

![Cilium 逻辑角色：Kubernetes 状态和 Operator、每节点 agent、内核程序/map，以及 Hubble 流观察。](../../.gitbook/assets/en-networking-cilium-02-ebpf-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-02-ebpf-1.html)

该图展示逻辑职责，而非强制位置或单一编译 pipeline。CLI 可在集群外运行；agent 在符合条件的受管节点上运行。程序构建/加载细节因版本/功能而异。Hubble Relay 聚合流；Prometheus 指标使用独立端点。

agent 协调 endpoint、identity、policy 和 datapath 状态。Operator 处理已配置的集群范围任务，例如 identity/IPAM 生命周期；它不在数据包转发路径上。Hubble 将 BPF 流信息与用户空间 proxy 事件结合。

### Cilium eBPF Datapath 的详细分析

这些是相互协作的功能，并非每个数据包的固定顺序：

1. **入口：**socket hook 可在数据包存在前解析 Service backend；TC 处理数据包路径；可选的 XDP 加速处理受支持的外部流量。
2. **Identity/policy：**IP/identity 和 endpoint policy 控制 L3/L4 访问。受支持的 HTTP/gRPC policy 使用 Envoy，DNS policy 使用 DNS proxy；L7 解析/强制执行并不完全由 BPF 完成。
3. **状态/转换：**conntrack、service/backend、reverse-NAT 和 affinity map 有不同作用。不是每个数据包都会重复 backend 选择。
4. **转发：**原生路由或已配置 overlay 承载流量。DSR 分发/返回路径需要所选模式的网络前提条件。
5. **观察：**datapath counter/event 和 proxy event 受到配置和收集丢失的限制。

Backend 就绪状态来自 control-plane 状态和适用的健康机制，而非通用 BPF 应用探针。Maglev、affinity、DSR 和加速是功能选项，并非通用默认值。

### Cilium 主要 eBPF 程序详细说明

| Cilium 1.20.2 源码 | 作用 |
|---|---|
| `bpf/bpf_lxc.c` | Endpoint 数据包路径、policy、conntrack 和转发 |
| `bpf/bpf_overlay.c` | Overlay 数据包路径 |
| `bpf/bpf_host.c` | Host/device 路径和受支持的 host-firewall 处理 |
| `bpf/bpf_xdp.c` | XDP 路径，包括已配置的 load-balancer 加速 |
| `bpf/bpf_sock.c` | cgroup socket-address hook（IPv4 和 IPv6）：connect、sendmsg、recvmsg、getpeername、bind/post_bind 和 sock_release，用于 socket 级 service 转换 |
| `bpf/bpf_wireguard.c` | `cilium_wg0` device 程序（`cil_from_wireguard`/`cil_to_wireguard`），用于标记经 WireGuard 解密的流量 |
| `bpf/bpf_sock_term.c` | BPF iterator（TCP/UDP），销毁连接到已删除 Service backend 的 socket |
| `bpf/bpf_probes.c`, `bpf/bpf_alignchecker.c` | 并非 datapath 程序：内核功能 probe 在 agent 启动时运行，以及 C/Go struct-layout 检查 |
| `bpf/lib/lb.h` | 共享的 load-balancing helper |
| `bpf/lib/policy.h` | 共享的 policy helper |

有关 loader、attach point、tail call 和每个程序的演练，请参阅 [eBPF datapath internals](08-ebpf-datapath-internals.md)。

此版本没有顶层 `bpf_lb.c` 或 `bpf_network.c` 文件。函数名和功能 gate 会变化；应检查确切版本，而不是将概念名称视为源码文件。

### Cilium 的 eBPF Map 使用方式

以下示例不是稳定的 map-layout API：

| 名称 / 系列 | 键和作用 |
|---|---|
| `cilium_lxc` | 地址/地址族 → endpoint 转发元数据；并非仅 endpoint ID |
| `cilium_ipcache_v2` | 前缀、地址族、集群上下文 → identity/tunnel 元数据 |
| `cilium_policy_v3_<endpoint>` | Identity、方向、协议、目标端口和前缀 → policy entry |
| `cilium_ct4_global`, `cilium_ct6_global`, `cilium_ct_any4_global`, etc. | Connection-tuple 状态；实际 map 取决于协议/地址族/配置 |
| `cilium_lb4_services_v2` / `cilium_lb6_services_v2` | 地址/端口、协议、scope 和 backend slot → service 元数据/backend 引用；backend record 位于独立 map |
| `cilium_metrics` | 原因、方向和 source-location key → 数据包/字节计数器 |

`cilium-dbg map get` 显示用户空间缓存的内容，不一定是最新内核转储。对于受支持的内核视图，请使用匹配的 `cilium-dbg bpf ...` decoder 或 bpftool。不要将原始字节写入 Cilium map 作为故障排查捷径。

### 基于 eBPF 的功能及其边界

- **Policy：**Kubernetes NetworkPolicy 具有 L3/L4 语义；Cilium resource 添加了受支持功能。不受限制的 L4 allow 可以绕过重叠的 L7-restricted allow；检查组合 policy。
- **加密：**在 WireGuard/IPsec 模式中，BPF 将流量导向这些内核设施；加密学并非仅由 BPF 指令完成。为所选模式配置 key、port、MTU 和流量覆盖范围。IPsec 和 WireGuard key 操作不同。
- **Service mesh：**用户空间 proxy 提供受支持的 L7 处理。Kafka L7 policy 已移除。Beta workload mTLS/ztunnel 有独立前提条件，并不意味着启用了节点加密。
- **带宽：**EDT/bandwidth-manager 和 congestion control 不保证端到端 QoS 或吞吐量。
- **多集群：**Cluster Mesh 需要连接性、identity、地址分配和兼容配置；它不会自动同步每个 policy object 或解决路由问题。

## 实验室：eBPF 程序开发和调试

### 1. 基本 eBPF 程序开发

将命名文件保存到新的实验室目录。此程序记录 `execve` **尝试**，包括后续失败。`execveat` 具有不同的 syscall-entry tracepoint。Debug print 是共享且嘈杂的，并非生产事件传输方式。`SEC()` 提供预期的类型/hook；GPL 元数据适合这里使用的 helper。

**`hello.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

SEC("tracepoint/syscalls/sys_enter_execve")
int hello_execve(void *ctx)
{
    (void)ctx;
    char message[] = "execve attempt\n";
    bpf_trace_printk(message, sizeof(message));
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

### 2. 使用 Map 的高级 eBPF 程序

在参考内核中，`sched_process_exec` 在成功执行转换后发出。按 `comm` 计数；它是最多 16 字节（含结尾）的短任务名，而非唯一的可执行文件路径/进程 identity。名称可能冲突/改变。这观察的是主机，不会自动观察某个 Pod。

该 map 最多容纳 1,024 个名称。`lost_events[0]` 计数名称读取失败，`[1]` 计数没有可用 counter entry 的事件，包括容量耗尽。这些不覆盖每一种可能的收集失败；64 位计数器可能回绕。该实验室在计数期间不删除 entry。

**`exec_shared.h`**

```c
#ifndef EXEC_SHARED_H
#define EXEC_SHARED_H
#define COMM_BYTES 16
#define MAX_COMMANDS 1024
struct comm_key {
    char comm[COMM_BYTES];
};
#endif
```

**`exec_count.bpf.c`**

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include "exec_shared.h"

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_COMMANDS);
    __type(key, struct comm_key);
    __type(value, __u64);
} exec_counts SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 2);
    __type(key, __u32);
    __type(value, __u64);
} lost_events SEC(".maps");

static __always_inline void record_loss(__u32 reason)
{
    __u64 *lost = bpf_map_lookup_elem(&lost_events, &reason);
    if (lost)
        __sync_fetch_and_add(lost, 1);
}

SEC("tracepoint/sched/sched_process_exec")
int count_exec(void *ctx)
{
    (void)ctx;
    struct comm_key key = {};
    __u64 zero = 0;
    if (bpf_get_current_comm(key.comm, sizeof(key.comm)) != 0) {
        record_loss(0);
        return 0;
    }

    __u64 *count = bpf_map_lookup_elem(&exec_counts, &key);
    if (!count) {
        /* A competing CPU may insert first; never overwrite its count. */
        bpf_map_update_elem(&exec_counts, &key, &zero, BPF_NOEXIST);
        count = bpf_map_lookup_elem(&exec_counts, &key);
    }
    if (count)
        __sync_fetch_and_add(count, 1);
    else
        record_loss(1);
    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

#### 用户空间应用程序和附加生命周期

此 loader 接受任一样本 object，加载恰好一个程序，附加它并保留 link 直到 Ctrl-C/SIGTERM。它从同一 object 读取 counter map FD，而不是假设 pin 存在。迭代从 NULL 开始，并生成有界、非原子的实时样本。

**`run_bpf.c`**

```c
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include <bpf/bpf.h>
#include <bpf/libbpf.h>
#include "exec_shared.h"

static volatile sig_atomic_t stopping;

static void stop(int signal_number)
{
    (void)signal_number;
    stopping = 1;
}

static int dump_counts(int map_fd, int lost_fd)
{
    struct comm_key current, next;
    const struct comm_key *previous = NULL;
    unsigned int seen = 0;

    while (seen < MAX_COMMANDS) {
        if (bpf_map_get_next_key(map_fd, previous, &next) != 0) {
            if (errno == ENOENT)
                break;
            perror("get next key");
            return -1;
        }
        __u64 value;
        if (bpf_map_lookup_elem(map_fd, &next, &value) == 0)
            printf("%.*s: %" PRIu64 "\n", COMM_BYTES, next.comm,
                   (uint64_t)value);
        else if (errno != ENOENT) {
            perror("lookup count");
            return -1;
        }
        current = next;
        previous = &current;
        seen++;
    }
    for (__u32 reason = 0; reason < 2; reason++) {
        __u64 value;
        if (bpf_map_lookup_elem(lost_fd, &reason, &value) != 0) {
            perror("lookup loss");
            return -1;
        }
        printf("lost[%u]: %" PRIu64 "\n", reason, (uint64_t)value);
    }
    if (fflush(stdout) != 0) {
        perror("flush output");
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    struct bpf_object *object = NULL;
    struct bpf_link *link = NULL;
    int result = 1;
    if (argc != 2) {
        fprintf(stderr, "usage: %s OBJECT.bpf.o\n", argv[0]);
        return 2;
    }
    struct sigaction action = {.sa_handler = stop};
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, NULL) || sigaction(SIGTERM, &action, NULL)) {
        perror("sigaction");
        return 1;
    }
    object = bpf_object__open_file(argv[1], NULL);
    if (!object) {
        perror("open BPF object");
        return 1;
    }
    struct bpf_program *program = bpf_object__next_program(object, NULL);
    if (!program || bpf_object__next_program(object, program)) {
        fprintf(stderr, "expected exactly one program\n");
        goto cleanup;
    }
    if (bpf_object__load(object) != 0) {
        fprintf(stderr, "load failed; inspect libbpf/verifier diagnostics\n");
        goto cleanup;
    }
    int counts = bpf_object__find_map_fd_by_name(object, "exec_counts");
    int losses = bpf_object__find_map_fd_by_name(object, "lost_events");
    if (counts >= 0 && losses < 0) {
        fprintf(stderr, "counter object is missing lost_events\n");
        goto cleanup;
    }
    link = bpf_program__attach(program);
    if (!link) {
        perror("attach tracepoint");
        goto cleanup;
    }
    fprintf(stderr, "Attached; Ctrl-C detaches. Counts are live samples.\n");
    result = 0;
    while (!stopping) {
        if (counts >= 0 && dump_counts(counts, losses) != 0) {
            result = 1;
            break;
        }
        sleep(2);
    }
cleanup:
    bpf_link__destroy(link);
    bpf_object__close(object);
    return result;
}
```

#### 编译和运行

在 Debian/Ubuntu multiarch 安装中，GCC 的 multiarch 目录提供 UAPI `asm/` 头文件；其他发行版请调整路径。`-g` 为 `.maps` 提供 BTF。在准备好的 VM 的终端 A 中编译并启动 loader：

```bash
MULTIARCH=$(gcc -print-multiarch)
test -n "$MULTIARCH"
clang -O2 -g -target bpf -I"/usr/include/$MULTIARCH" \
  -c hello.bpf.c -o hello.bpf.o
clang -O2 -g -target bpf -I"/usr/include/$MULTIARCH" \
  -c exec_count.bpf.c -o exec_count.bpf.o
cc -O2 -Wall -Wextra run_bpf.c -o run_bpf \
  $(pkg-config --cflags --libs libbpf)
sudo ./run_bpf hello.bpf.o
```

在终端 B 中读取 `sudo cat /sys/kernel/tracing/trace_pipe`；在终端 C 中运行诸如 `/usr/bin/true` 的外部可执行文件。使用 Ctrl-C 停止 hello loader，然后运行 `sudo ./run_bpf exec_count.bpf.o`。在另一终端执行命令时，观察名称/计数对的变化。观察器和其他主机活动也会生成事件，因此不保证固定的总数/PID。失败的 `execve` 尝试可能出现在 hello 输出中，但不应发出 `sched_process_exec`。

仅执行 `bpftool prog load OBJECT PIN` 不会附加此 tracepoint。示例有意拥有一个 link。显式 pin/reuse 是独立的生命周期决策：`pinmaps` 和 `map ... pinned ...` 不是可互换的语法。关闭此 loader 会释放其未 pin 的资源。

### 3. 探索和调试 Cilium eBPF 程序

使用已准备好的集群和正确的 kubeconfig context。在受影响 Pod 所在节点上选择 agent；endpoint ID 是节点本地的。替换显式占位符：

```bash
kubectl config current-context
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
export CILIUM_POD=cilium-REPLACE-WITH-ACTUAL-POD
export ENDPOINT_ID=REPLACE-WITH-NODE-LOCAL-ID
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg status --verbose
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg endpoint get "$ENDPOINT_ID"
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg map list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg service list
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --frontends
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- cilium-dbg bpf lb list --backends
```

使用 `kubectl get networkpolicy,ciliumnetworkpolicy -n YOUR_NAMESPACE` 检查所需 policy，并单独检查适用的集群范围 policy。将 endpoint 实现状态与实际流量比较。已移除的 `policy trace` 和已弃用的 `policy get` 不是替代品。

一次运行一个 monitor，使用 Ctrl-C 停止：

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent --   cilium-dbg monitor --related-to "$ENDPOINT_ID" --type drop
```

对发出的 policy 决策使用 `--type policy-verdict`，或对可用 proxy 事件使用 `--type l7`。可见性取决于配置。HTTP 拒绝可能是 HTTP 403，而不是网络 DROPPED verdict。

对于启用的 Hubble Relay，请保持 `cilium hubble port-forward` 运行，然后使用：

```bash
hubble status
hubble observe --namespace default --last 20
hubble observe --protocol http --last 20
hubble observe --namespace default --last 20 --output json
```

通过管道传递给 `jq` 的 JSON 并非服务依赖关系图。启用的 Hubble UI 提供 service map（`cilium hubble ui`）。HTTP 可见性需要受支持的 proxy/L7 路径；加密的应用内容不会自动解码。

### 4. 性能分析和优化

在具有 profiling 权限/支持的受控节点上，检查实际程序 ID。这些命令针对本地内核状态，且未由本审计执行：

```bash
sudo bpftool prog show
export PROG_ID=REPLACE-WITH-ACTUAL-ID
sudo bpftool prog show id "$PROG_ID"
sudo bpftool prog dump xlated id "$PROG_ID"
sudo bpftool prog profile id "$PROG_ID" duration 10 cycles instructions
```

Profiling 需要 metric 名称和适当的内核/PMU 支持。`bpftool -p map dump ...` 会美化打印内容，而不是查找延迟。`perf`/bpftrace 可以对工作负载进行 profiling，但应验证目标 symbol、probe 可用性和参数。kretprobe 无法在没有显式关联的情况下可靠地暴露入口 `arg0`。

在测量完整工作负载时，记录协议、数据包大小、并发性、policy、加密、proxy 和路由。在更改 XDP/native routing 前，检查已安装 Helm value 和 `cilium-dbg status --verbose`。更快的 hook 或合成结果并不能证明应用延迟更低。

### 5. 故障排查提示

| 症状 | 检查项 |
|---|---|
| C 构建失败 | 正确的 UAPI/libbpf 头文件、BPF 编译器目标、`__u32`/`__u64`、用于 BTF 的 `-g` |
| Verifier 拒绝 | Loader stderr/verifier log、边界、栈初始化、helper、license 和复杂度 |
| 已加载但无事件 | Attachment/link 生命周期、精确 tracepoint、触发条件和权限 |
| 缺少 map 数据 | 相同 map 实例、插入错误/容量、键含义、引用/pin 生命周期 |
| 错误的 Cilium 流 | 正确的节点/endpoint、组合的所需/实现 policy、route/backend 状态、L7 proxy 行为 |
| 缺少 Hubble record | Relay、filter、已配置可见性和 lost-event 报告 |

`trace_pipe` 包含 trace 输出，而非 verifier 诊断信息。对于隔离 VM 中有意进行的加载测试，bpftool `-d` 提供 loader/verifier 诊断；加载仍不能证明附加或行为。不要为了让测试通过而禁用 policy、扩展生产权限或重写 map。

## 来源

- [原始 BPF 论文](https://www.tcpdump.org/papers/bpf-usenix93.pdf), [Linux BPF 设计问答](https://docs.kernel.org/bpf/bpf_design_QA.html), [verifier](https://docs.kernel.org/bpf/verifier.html), [ring buffer](https://docs.kernel.org/bpf/ringbuf.html), [licensing](https://docs.kernel.org/bpf/bpf_licensing.html), [seccomp](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [Linux 6.12 BPF 加载](https://github.com/torvalds/linux/blob/v6.12/kernel/bpf/syscall.c), [exec 事件位置](https://github.com/torvalds/linux/blob/v6.12/fs/exec.c), [libbpf 1.7](https://github.com/libbpf/libbpf/tree/v1.7.0), [bpftool 7.7](https://github.com/libbpf/bpftool/releases/tag/v7.7.0)
- [Cilium 1.20.2 BPF 源码](https://github.com/cilium/cilium/tree/v1.20.2/bpf), [map](https://github.com/cilium/cilium/tree/v1.20.2/pkg/maps), [load-balancer map](https://github.com/cilium/cilium/tree/v1.20.2/pkg/loadbalancer/maps), [命令参考](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/cmdref)
- [Cilium 系统要求](https://docs.cilium.io/en/v1.20/operations/system_requirements/), [Kubernetes 兼容性](https://docs.cilium.io/en/v1.20/network/kubernetes/compatibility/), [kube-proxy replacement](https://docs.cilium.io/en/v1.20/network/kubernetes/kubeproxy-free/), [加密](https://docs.cilium.io/en/v1.20/security/network/encryption/)

## 测验

[检查你的理解](../../quizzes/networking/cilium/02-ebpf-quiz.md)。
