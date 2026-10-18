# eBPF 技术深入探究

> **审查基线**：Cilium 1.20.3、Linux 5.10+ 或有文档记录的等效回移版本（例如 RHEL 8.10 的 4.18 内核），已在 Kubernetes 1.33–1.36 上测试。各项 BPF 功能的要求各不相同。
> **最近审阅日期**：October 16, 2026

## 实验环境设置

使用一次性 Linux 开发 VM，运行受维护的发行版，支持下文使用的 tracepoint，并具有加载跟踪程序的权限。此环境与安装 Cilium 分开；不要在集群节点上加载实验性程序。Linux 6.12 是 verifier 讨论的参考版本，并不意味着所有 6.12 发行版都启用了每项功能。

必需工具包括带有 BPF 后端的 Clang、目标架构的 UAPI 头文件、libbpf 1.x 开发头文件/库、libelf、zlib、C 编译器和 bpftool。BCC 和 bpftrace 是可选的替代工具。Debian/Ubuntu 软件包名称通常包括 `clang`、`libbpf-dev`、`libelf-dev`、`zlib1g-dev`、`build-essential` 和 `pkg-config`；bpftool 的打包方式取决于发行版/内核。不要假设每个 Debian 系统都提供或适合使用 `linux-tools-generic`。Cilium 说明支持 AMD64/AArch64 主机；在其容器镜像之外原生运行 Cilium，还需要 Clang/LLVM 18.1+，这是与此小型跟踪实验不同的一项要求。

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

必须挂载并能够访问 Tracefs；某些系统会在 `/sys/kernel/debug/tracing` 下提供它。即使以容器 root 身份运行，内核配置、能力、lockdown/LSM 策略和容器限制也可能阻止程序加载或附加。`CAP_BPF` 并不是通用的跟踪权限；具体要求取决于内核、程序类型和 BPF token 委派方式。

**验证范围：**这些示例已通过针对 libbpf 1.7 的主机 C 语法检查、用户空间链接检查和确定性 helper 模拟。Clang BPF 目标编译、运行中内核的 verifier 检查和实时 tracepoint 附加仍需在准备好的 VM 中验证。这些示例并未经过生产环境测试，也不是无损跟踪方案。

## eBPF 技术简介与历史背景

eBPF 允许获准的程序在受支持的 Linux hook 上执行，以观察或影响内核行为。验证机制会限制内存访问和程序执行，但内核、verifier、JIT 和 helper 中仍可能存在缺陷。程序被接受并不能证明主机不会崩溃，也不能证明程序实现了预期策略。

### 从 BPF 到 eBPF：演进历史

McCanne 和 Jacobson 的论文 *The BSD Packet Filter: A New Architecture for User-level Packet Capture* 的预印本日期为 1992 年 12 月 19 日，并注明其于 1993 年 1 月 25–29 日在 Winter USENIX 上发表。引用年份时应保留这一区别。经典 BPF 使用 32 位 A/X 寄存器和暂存内存进行过滤，避免不必要地将数据包复制到用户空间。其受限指令集并不意味着它无法在现代 CPU 上运行。

扩展 BPF 增加了 64 位指令集，其中有十一个寄存器 R0–R10（R10 是只读帧指针）、通常限制为 512 字节的栈、maps 和更多程序类型。这并不是一次从十个通用寄存器变为十一个通用寄存器的历史变化。函数调用和尾调用的组合可能会施加额外的栈限制。

### eBPF 技术演进：按内核版本划分的主要功能

以下选取的上游里程碑已对照带版本号的源码核实。它们不是发行版支持矩阵；回移补丁、构建选项、架构和 helper 各不相同。

| 内核 | 选取的里程碑 |
|---|---|
| [3.15](https://github.com/torvalds/linux/blob/v3.15/include/linux/filter.h) | 扩展指令集；内部经典 BPF 转换 |
| [3.16](https://github.com/torvalds/linux/blob/v3.16/arch/x86/net/bpf_jit_comp.c) | x86 扩展 BPF JIT |
| [3.18](https://github.com/torvalds/linux/blob/v3.18/include/uapi/linux/bpf.h) | BPF syscall/验证基础设施；尚无可用的 HASH/ARRAY map 类型 |
| [3.19](https://github.com/torvalds/linux/blob/v3.19/include/uapi/linux/bpf.h) | HASH/ARRAY maps 和 socket-filter 程序类型 |
| [4.1](https://github.com/torvalds/linux/blob/v4.1/include/uapi/linux/bpf.h) | KPROBE 和 TC SCHED_CLS/SCHED_ACT |
| [4.2](https://github.com/torvalds/linux/blob/v4.2/include/uapi/linux/bpf.h) | PROG_ARRAY 和尾调用 |
| [4.8](https://github.com/torvalds/linux/blob/v4.8/include/uapi/linux/bpf.h) | XDP 程序类型 |
| [4.10](https://github.com/torvalds/linux/blob/v4.10/include/uapi/linux/bpf.h) | LRU hash maps |
| [4.16](https://github.com/torvalds/linux/blob/v4.16/include/uapi/linux/bpf.h) | BPF 到 BPF 函数调用 |
| [4.17](https://github.com/torvalds/linux/blob/v4.17/include/uapi/linux/bpf.h) | 原始 tracepoint |
| [4.18](https://github.com/torvalds/linux/blob/v4.18/include/uapi/linux/bpf.h) | BTF 加载 API |
| [5.2](https://github.com/torvalds/linux/blob/v5.2/include/uapi/linux/bpf.h) | 用于全局数据的直接 map-value 访问 |
| [5.7](https://github.com/torvalds/linux/blob/v5.7/include/uapi/linux/bpf.h) | BPF link API 和 BPF LSM |
| [5.8](https://github.com/torvalds/linux/blob/v5.8/include/uapi/linux/bpf.h) | BPF ring buffer |
| [5.10](https://github.com/torvalds/linux/blob/v5.10/include/uapi/linux/bpf.h) | 支持的附加类型可使用可睡眠程序 |
| [5.15](https://github.com/torvalds/linux/blob/v5.15/include/uapi/linux/bpf.h) | BPF timer helper |
| [5.19](https://github.com/torvalds/linux/blob/v5.19/include/uapi/linux/bpf.h) | 动态指针 helper |
| [6.2](https://github.com/torvalds/linux/blob/v6.2/kernel/bpf/helpers.c) | 类型化对象分配 kfunc，而非无限制的 malloc |

有界循环于 Linux 5.3 引入；[上游 verifier 变更](https://github.com/torvalds/linux/commit/2589726d12a1b12eaaa93c7f1ea64287e383c7a5)解释了循环分析和状态剪枝。设计 FAQ 中仍保留的“尚未实现循环”旧段落并不是当前功能指南。有界循环仍可能超出 verifier 的复杂度限制。

### 发展与应用领域

Cilium 的公开代码仓库于 2015 年 12 月创建；“项目于 2017 年启动”这一说法并不准确。仓库创建日期并不等同于确切的产品发布日期，也不能证明其属于“首批大型项目”。

| 领域 | 示例与界限 |
|---|---|
| 网络 | Cilium/Calico 数据路径、Katran 负载均衡和 XDP 过滤 |
| 运行时安全 | Falco、Tracee 和 Tetragon 使用内核事件；是否实施强制控制取决于产品和 hook |
| 跟踪 | BCC（包括 Python/Lua 前端）、bpftrace、存储和块 I/O 跟踪 |
| 网络可观测性 | Hubble flow/proxy 事件；flow 图并非分布式应用 span 跟踪 |
| Service mesh | Cilium 将内核转发与用户空间代理结合，用于支持的 L7 功能 |
| 社区 | eBPF Foundation 为生态系统提供支持；资金和项目成熟度并非兼容性标准 |

`seccomp-bpf` 使用经典 BPF 过滤器接口来决定系统调用。Linux 可能会在内部转换经典过滤器，但这并不是通用的 eBPF 程序/map/helper API。

### eBPF 与传统内核模块：范式转变

| 特征 | eBPF | 内核模块 |
|---|---|---|
| 安全性 | 受 verifier 约束；实现缺陷和运维风险仍然存在 | 可访问范围更广的原生内核功能；缺陷可能导致主机不稳定 |
| 部署 | 在支持的情况下，可加载/附加程序而无需重启 | 满足依赖条件且使用情况允许时，许多模块也可以在不重启的情况下加载/卸载 |
| 兼容性 | 指令/helper ABI 和功能要求；CO-RE 可重定位受支持的类型访问 | 内核/模块 ABI、配置和发行版支持 |
| 性能 | 通常由 JIT 编译；开销取决于 hook、程序和工作负载 | 原生执行同样会产生依赖工作负载的开销 |
| 开发 | 受限的执行上下文、helper/kfunc 和 verifier 限制 | 内核 API 和常规内核开发约束 |
| 权限 | 加载/附加需要适当权限或委派 | 需要特权才能加载；签名/lockdown 可能会限制加载 |

两者都需要进行运维测试。模块并非仅限于供应商实现，eBPF 也不会天然保证生产环境部署安全。

## 深入分析内核内部的 eBPF 架构

### eBPF 架构组件详解

在用户空间中，Clang 将 C 编译为 BPF ELF；Rust 使用自己的编译器/工具链生态系统。libbpf 负责 ELF section、maps、重定位、加载和受支持的附加 API。BCC 提供更高级的 API；bpftrace 提供跟踪语言。

CO-RE 使用 BTF 和重定位来适配受支持的类型/字段访问。它不会提供缺失的 helper、程序类型或内核配置，也不保证任意跨架构/跨内核兼容性。即使程序使用了 BTF，内核内部结构、tracepoint 格式和 kfunc 也不是稳定 ABI。

在内核中，verifier 会根据程序类型、上下文、helper 和权限检查程序。JIT 可以将已接受的 BPF 转换为原生指令；在受支持的情况下，解释器也是一种执行机制。JIT 输出之后不会再经过一个强制的第二阶段 VM。附加操作会将已加载的程序连接到 hook；仅加载程序并不会订阅 tracepoint。

### eBPF 程序生命周期详解

1. **开发：**选择 hook/上下文并定义 maps/license 元数据。并非所有程序都需要 GPL 兼容性，但 GPL-only helper 和某些类型/kfunc 会施加限制。这些跟踪示例使用 GPL 元数据以适配所用 helper。
2. **编译：**使用目标工具链和头文件生成 BPF ELF 以及所需的调试/BTF 信息。
3. **打开/加载：**解析 ELF、创建或显式复用 maps、进行重定位并调用 BPF 加载 API。验证和可选的 JIT 会在加载期间进行。
4. **附加：**使用相应的 API。libbpf 可以根据 `SEC("tracepoint/...")` 推断这些 tracepoint。保持 link/附加状态处于活动状态。
5. **运行/观察：**事件会调用程序；用户空间读取 maps/buffers。采样和容量限制可能导致观测数据丢失。
6. **更新/卸载：**只有在明确需要时才保留兼容的 maps/links/pins。销毁此实验的 link 并关闭其对象以释放资源。

在 Linux 6.12 中，具备 BPF 能力的加载路径最多允许 1,000,000 条指令，非特权路径则最多允许 4,096 条指令。verifier 另有 1,000,000 条指令的**分析复杂度**限制。较小的程序也可能无法通过验证。非特权 BPF 通常处于禁用状态；token/能力和程序类型检查仍然适用。

### eBPF 程序类型及其特征

| Hook / 程序类型 | 用途与返回值界限 |
|---|---|
| XDP / `BPF_PROG_TYPE_XDP` | 原生驱动 XDP 在分配 skb 前运行；通用/卸载模式各不相同。`XDP_DROP`、`PASS`、`TX`、`REDIRECT` 是动作，并不保证吞吐量 |
| TC / `SCHED_CLS`、`SCHED_ACT` | 入站/出站数据包分类/动作。分类器的 `TC_ACT_*` 语义需要适当的 direct-action 设置 |
| Socket filter / `SOCKET_FILTER` | socket 数据包交付：返回零表示丢弃，正数表示捕获长度，可能会截断。创建/连接策略使用其他 hook |
| kprobe/uprobe / `KPROBE` | 内核/用户空间探针；不存在单独的 `BPF_PROG_TYPE_UPROBE`。内联、黑名单和符号可用性会限制附加 |
| Tracepoint / `TRACEPOINT` | 静态声明的事件上下文；检查目标格式。它不是保证稳定的内核 ABI |
| Perf event / `PERF_EVENT` | 性能采样；返回行为取决于其 perf-event 集成方式 |
| cgroup / `CGROUP_SKB`、`CGROUP_SOCK`、`CGROUP_SOCK_ADDR` 等 | 网络/socket 控制；上下文和允许/拒绝约定各不相同 |
| LSM / `LSM` | MAC 风格程序通常会保留之前的错误，并返回零/错误；cgroup-LSM 的授权语义有所不同 |
| Socket operations / `SOCK_OPS` | TCP 回调；具体操作、reply 字段和 helper 支持都很重要 |
| fentry/fexit / `TRACING` | 在支持的情况下进行基于 BTF 的函数跟踪；目标和附加限制仍然适用 |

应根据可见性/控制需求选择 hook。XDP 缺少一些较后续协议栈阶段的上下文；TC 处理基于 skb 的流量；tracepoint/probe 观测不会自动实施网络策略。不要在不同程序类型之间照搬上下文结构体或返回码。

### eBPF Maps：数据共享与状态存储的核心

只要仍有引用（例如 FD、已加载的程序或显式 bpffs pin），maps 就会继续存在。Pin 并不等于磁盘持久化，也不会在重启后保留 map 内容。重新加载不会自动复用旧 map。

| 类型 | 用途与限制 |
|---|---|
| `HASH` | 有界键/值表；表满时插入可能失败。预期的常数时间查找并不保证延迟 |
| `ARRAY` | 在有效索引处预分配并初始化为零的值；零值不等于 hash 条目缺失 |
| `LRU_HASH` | 带 LRU 风格淘汰的有界缓存，并非无损的累计计数器 |
| `RINGBUF` | 多生产者/单消费者，可跨 CPU 使用；键/值大小为零，容量必须是 2 的幂字节数；预留失败不会阻塞 |
| `PERF_EVENT_ARRAY` | 每 CPU 的 perf 通道；用户空间必须配置/消费事件并跟踪丢失记录 |
| `PROG_ARRAY` | 尾调用程序引用；目标兼容性和调用次数限制均适用 |
| `PERCPU_HASH` / `PERCPU_ARRAY` | 减少跨 CPU 竞争，但并非在所有情况下都没有竞争。用户空间读取所有可能 CPU 的槽位时必须使用所需填充 |
| `SOCKMAP` / `SOCKHASH` | 用于支持的重定向/程序的 socket 引用，并非任意 socket 操作 hook |

libbpf 1.x 已移除 `struct bpf_map_def SEC("maps")`。以下基于 BTF 的定义使用实际类型展示八类 maps。请将所需 maps 与合适的程序组合使用；仅有这些声明并不会形成事件处理管道。

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

共享计数器需要原子递增。新的 hash 键需要通过 `BPF_NOEXIST` 插入，然后查找/递增成功插入的条目；使用 `BPF_ANY` 初始化可能会覆盖另一个 CPU 的计数。有效索引处的 array 条目已经存在。

## 在 Cilium 中使用 eBPF：容器网络的创新

### Cilium 架构与 eBPF 的作用

![Cilium 逻辑职责：Kubernetes 状态和 Operator、每节点 agent、内核程序/maps 以及 Hubble flow 观测。](../../.gitbook/assets/en-networking-cilium-02-ebpf-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-cilium-02-ebpf-1.html)

该图展示的是逻辑职责，而非强制的位置安排或单一编译管线。CLI 可以在集群外运行；agent 在符合条件的受管理节点上运行。程序构建/加载的具体细节因版本/功能而异。Hubble Relay 会汇总 flows；Prometheus metrics 使用独立的端点。

agent 会协调 endpoints、身份、策略和数据路径状态。Operator 负责身份/IPAM 生命周期等已配置的集群范围任务；它不属于数据包转发路径。Hubble 会结合 BPF flow 信息和用户空间代理事件。

### 深入分析 Cilium 的 eBPF 数据路径

以下是相互配合的功能，并非每个数据包都遵循的固定顺序：

1. **入口：**socket hook 可以在数据包产生前解析 Service 后端；TC 处理数据包路径；可选的 XDP 加速可处理受支持的外部流量。
2. **身份/策略：**IP/身份和 endpoint 策略控制 L3/L4 访问。受支持的 HTTP/gRPC 策略使用 Envoy，DNS 策略使用 DNS 代理；L7 解析/强制执行并非完全由 BPF 完成。
3. **状态/转换：**conntrack、service/backend、reverse-NAT 和 affinity maps 各有不同用途。并非每个数据包都会重新选择后端。
4. **转发：**原生路由或配置的 overlay 会承载流量。DSR 分发/返回路径需要满足所选模式的网络前提条件。
5. **观测：**数据路径计数器/事件和代理事件存在配置要求和采集丢失限制。

后端就绪状态来自控制平面状态和适用的健康检查机制，而不是通用的 BPF 应用探测。Maglev、affinity、DSR 和加速都是可选功能，并非通用默认设置。

### Cilium 主要 eBPF 程序详解

| Cilium 1.20.3 源码 | 作用 |
|---|---|
| `bpf/bpf_lxc.c` | Endpoint 数据包路径、策略、conntrack 和转发 |
| `bpf/bpf_overlay.c` | Overlay 数据包路径 |
| `bpf/bpf_host.c` | 主机/设备路径和受支持的 host-firewall 处理 |
| `bpf/bpf_xdp.c` | XDP 路径，包括已配置的负载均衡加速 |
| `bpf/bpf_sock.c` | cgroup socket-address hook（IPv4 和 IPv6）：connect、sendmsg、recvmsg、getpeername、bind/post_bind 和 sock_release，用于 socket 层级的 service 转换 |
| `bpf/bpf_wireguard.c` | `cilium_wg0` 设备程序（`cil_from_wireguard`/`cil_to_wireguard`），用于标记经过 WireGuard 解密的流量 |
| `bpf/bpf_sock_term.c` | BPF 迭代器（TCP/UDP），用于销毁连接到已删除 Service 后端的 sockets |
| `bpf/bpf_probes.c`、`bpf/bpf_alignchecker.c` | 非数据路径程序：在 agent 启动时运行内核功能探测，并检查 C/Go 结构体布局 |
| `bpf/lib/lb.h` | 共享负载均衡 helper |
| `bpf/lib/policy.h` | 共享策略 helper |

有关加载器、附加点、尾调用和逐程序说明，请参阅 [eBPF 数据路径内部机制](08-ebpf-datapath-internals.md)。

此版本中不存在顶层的 `bpf_lb.c` 或 `bpf_network.c` 文件。函数名称和功能门控会变化；请检查确切版本，不要把概念名称当成源文件。

### Cilium 对 eBPF Map 的使用

以下示例并非稳定的 map 布局 API：

| 名称 / 系列 | 键与用途 |
|---|---|
| `cilium_lxc` | 地址/地址族 → endpoint 转发元数据；并非简单的 endpoint ID |
| `cilium_ipcache_v2` | 前缀、地址族、集群上下文 → 身份/隧道元数据 |
| `cilium_policy_v3_<endpoint>` | 身份、方向、协议、目标端口和前缀 → 策略条目 |
| `cilium_ct4_global`、`cilium_ct6_global`、`cilium_ct_any4_global` 等 | 连接元组状态；实际 maps 取决于协议/地址族/配置 |
| `cilium_lb4_services_v2` / `cilium_lb6_services_v2` | 地址/端口、协议、范围和后端槽位 → service 元数据/后端引用；后端记录存放在独立 maps 中 |
| `cilium_metrics` | 原因、方向和源位置键 → 数据包/字节计数器 |

`cilium-dbg map get` 显示的是用户空间缓存的内容，不一定是最新的内核转储。请使用匹配的 `cilium-dbg bpf ...` 解码器或 bpftool 查看其支持的内核视图。不要将原始字节写入 Cilium maps 作为故障排查捷径。

### 基于 eBPF 的功能及其边界

- **策略：**Kubernetes NetworkPolicy 具有 L3/L4 语义；Cilium 资源会增加受支持的功能。无限制的 L4 allow 可能绕过重叠的 L7 限制型 allow；请检查组合策略。
- **加密：**在 WireGuard/IPsec 模式下，BPF 会将流量导向这些内核功能；加密并非完全由 BPF 指令完成。请为所选模式配置密钥、端口、MTU 和流量覆盖范围。IPsec 和 WireGuard 的密钥操作各不相同。
- **Service mesh：**用户空间代理提供受支持的 L7 处理。Kafka L7 策略已移除。Beta 工作负载 mTLS/ztunnel 有独立的前提条件，不能由节点加密功能推定已启用。
- **带宽：**EDT/bandwidth-manager 和拥塞控制无法保证端到端 QoS 或吞吐量。
- **多集群：**Cluster Mesh 需要连通性、身份、地址和兼容配置；它不会自动同步所有策略对象，也不能解决路由问题。

## 实验：eBPF 程序开发与调试

### 1. 基本 eBPF 程序开发

将具名文件保存到新的实验目录中。此程序会记录 `execve` **尝试**，包括之后失败的尝试。`execveat` 使用不同的 syscall-entry tracepoint。调试打印是共享的、噪声较大的输出，不是生产环境事件传输方式。`SEC()` 用于指定预期的类型/hook；这里使用的 GPL 元数据适用于所用 helper。

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

### 2. 使用 Maps 的进阶 eBPF 程序

在所引用的内核中，`sched_process_exec` 会在成功的执行转换后发出。程序按 `comm` 计数；这是最多 16 字节（包括终止符）的短任务名称，不是唯一的可执行文件路径/进程身份。名称可能冲突/变化。此程序观测的是主机，并不会自动限定到某个 Pod。

该 map 最多容纳 1,024 个名称。`lost_events[0]` 统计名称读取失败，`[1]` 统计没有可用计数器条目的事件，包括容量耗尽。这些计数并未涵盖所有可能的采集故障；64 位计数器可能溢出。实验在计数期间不会删除条目。

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

#### 用户空间应用与附加生命周期

此加载器接受任一示例对象，只加载一个程序，将其附加，并保留 link 直到 Ctrl-C/SIGTERM。它从同一个对象中读取计数器 map FD，而不假设 pin 已存在。迭代从 NULL 开始，生成有界的非原子实时样本。

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

#### 编译与运行

在 Debian/Ubuntu 多架构安装中，GCC 的多架构目录会提供 UAPI `asm/` 头文件；其他发行版请相应调整路径。`-g` 会为 `.maps` 提供 BTF。在准备好的 VM 上的终端 A 中编译并启动加载器：

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

在终端 B 中读取 `sudo cat /sys/kernel/tracing/trace_pipe`；在终端 C 中运行 `/usr/bin/true` 等外部可执行文件。按 Ctrl-C 停止 hello 加载器，然后运行 `sudo ./run_bpf exec_count.bpf.o`。在另一个终端中执行命令时，观察名称/计数对不断变化。观察程序和主机上的其他活动也会生成事件，因此不会保证固定的总数/PID。失败的 `execve` 尝试可能出现在 hello 输出中，但不应触发 `sched_process_exec`。

仅运行 `bpftool prog load OBJECT PIN` 并不会附加此 tracepoint。此示例有意持有一个 link。显式 pin/复用属于单独的生命周期决策：`pinmaps` 和 `map ... pinned ...` 不是可以互换的语法。关闭此加载器会释放其未 pin 的资源。

### 3. 探索和调试 Cilium eBPF 程序

使用已准备好的集群和正确的 kubeconfig context。选择受影响 Pod 所在节点上的 agent；endpoint ID 在节点本地有效。替换明确标出的占位符：

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

使用 `kubectl get networkpolicy,ciliumnetworkpolicy -n YOUR_NAMESPACE` 检查期望策略，并单独检查适用的集群范围策略。将 endpoint 的已生效状态与实际 flows 进行比较。已移除的 `policy trace` 和已弃用的 `policy get` 不能替代这些检查。

每次运行一个 monitor，并按 Ctrl-C 停止：

```bash
kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent --   cilium-dbg monitor --related-to "$ENDPOINT_ID" --type drop
```

使用 `--type policy-verdict` 查看发出的策略判定，或使用 `--type l7` 查看可用的代理事件。可见性取决于配置。HTTP 拒绝可能返回 HTTP 403，而非网络 DROPPED 判定。

对于已启用的 Hubble Relay，请保持 `cilium hubble port-forward` 运行，然后使用：

```bash
hubble status
hubble observe --namespace default --last 20
hubble observe --protocol http --last 20
hubble observe --namespace default --last 20 --output json
```

将 JSON 管道传递给 `jq` 并不会生成服务依赖图。已启用的 Hubble UI 会提供服务映射（`cilium hubble ui`）。HTTP 可见性需要受支持的代理/L7 路径；应用内容加密后不会自动解码。

### 4. 性能分析与优化

在具有分析权限/支持的受控节点上，检查实际程序 ID。这些命令针对本地内核状态，本次审计未执行：

```bash
sudo bpftool prog show
export PROG_ID=REPLACE-WITH-ACTUAL-ID
sudo bpftool prog show id "$PROG_ID"
sudo bpftool prog dump xlated id "$PROG_ID"
sudo bpftool prog profile id "$PROG_ID" duration 10 cycles instructions
```

性能分析需要指定指标名称，并需要适当的内核/PMU 支持。`bpftool -p map dump ...` 会美化打印内容，并不会测量查找延迟。`perf`/bpftrace 可以分析工作负载，但请确认目标符号、探针可用性和参数。若没有显式关联，kretprobe 无法可靠地获取入口处的 `arg0`。

测量完整工作负载时，请记录协议、数据包大小、并发度、策略、加密、代理和路由情况。在更改 XDP/原生路由之前，请检查已安装的 Helm 值和 `cilium-dbg status --verbose`。hook 更快或合成测试结果更好，并不能证明应用延迟更低。

### 5. 故障排查提示

| 症状 | 检查项 |
|---|---|
| C 构建失败 | 检查 UAPI/libbpf 头文件、BPF 编译器目标、`__u32`/`__u64` 和用于 BTF 的 `-g` |
| Verifier 拒绝 | 检查加载器 stderr/verifier 日志、边界、栈初始化、helpers、license 和复杂度 |
| 已加载但没有事件 | 检查附加/link 生命周期、确切的 tracepoint、触发条件和权限 |
| Map 数据缺失 | 检查是否为同一个 map 实例、插入错误/容量、键的含义、引用/pin 生命周期 |
| Cilium flow 异常 | 检查节点/endpoint 是否正确、期望/已生效的组合策略、路由/后端状态和 L7 代理行为 |
| Hubble 记录缺失 | 检查 Relay、过滤器、已配置的可见性和丢失事件报告 |

`trace_pipe` 包含跟踪输出，而非 verifier 诊断信息。在隔离 VM 中进行有意的加载测试时，bpftool `-d` 可以提供加载器/verifier 诊断；但加载成功仍不能证明程序已附加或行为正确。不要为了让测试通过而禁用策略、扩大生产权限或改写 maps。

## 来源

- [BPF 原始论文](https://www.tcpdump.org/papers/bpf-usenix93.pdf)、[Linux BPF 设计问答](https://docs.kernel.org/bpf/bpf_design_QA.html)、[verifier](https://docs.kernel.org/bpf/verifier.html)、[ring buffer](https://docs.kernel.org/bpf/ringbuf.html)、[许可](https://docs.kernel.org/bpf/bpf_licensing.html)、[seccomp](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [Linux 6.12 BPF 加载](https://github.com/torvalds/linux/blob/v6.12/kernel/bpf/syscall.c)、[exec 事件位置](https://github.com/torvalds/linux/blob/v6.12/fs/exec.c)、[libbpf 1.7](https://github.com/libbpf/libbpf/tree/v1.7.0)、[bpftool 7.7](https://github.com/libbpf/bpftool/releases/tag/v7.7.0)
- [Cilium 1.20.3 BPF 源码](https://github.com/cilium/cilium/tree/v1.20.3/bpf)、[maps](https://github.com/cilium/cilium/tree/v1.20.3/pkg/maps)、[负载均衡 maps](https://github.com/cilium/cilium/tree/v1.20.3/pkg/loadbalancer/maps)、[命令参考](https://github.com/cilium/cilium/tree/v1.20.3/Documentation/cmdref)
- [Cilium 系统要求](https://docs.cilium.io/en/v1.20/operations/system_requirements/)、[Kubernetes 兼容性](https://docs.cilium.io/en/v1.20/network/kubernetes/compatibility/)、[kube-proxy 替代](https://docs.cilium.io/en/v1.20/network/kubernetes/kubeproxy-free/)、[加密](https://docs.cilium.io/en/v1.20/security/network/encryption/)

## 测验

[检查你的理解情况](../../quizzes/networking/cilium/02-ebpf-quiz.md).
