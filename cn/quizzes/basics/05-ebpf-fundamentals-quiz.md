# eBPF 基础知识测验

> **支持版本**: Linux Kernel 4.18+, Kubernetes 1.25+
> **最后更新**: February 23, 2026

本测验测试你对 eBPF（扩展伯克利数据包过滤器，extended Berkeley Packet Filter）的整体理解，从基本概念到在 Kubernetes 环境中的应用。

## 多选题

1. eBPF 验证器不检查什么？
   - A) 没有无限循环
   - B) 没有越界内存访问
   - C) 程序执行速度
   - D) 没有使用未初始化变量

<details>
<summary>显示答案</summary>

**答案: C) 程序执行速度**

**解释:**
eBPF 验证器会检查没有无限循环（DAG 结构验证）、没有越界内存访问、没有使用未初始化变量、正确的辅助函数调用以及保证程序终止，以确保程序安全性。程序执行速度不是验证器的验证项目。

</details>

2. 哪个 XDP（eXpress Data Path）程序返回值将数据包发送回同一 NIC？
   - A) XDP_DROP
   - B) XDP_PASS
   - C) XDP_TX
   - D) XDP_REDIRECT

<details>
<summary>显示答案</summary>

**答案: C) XDP_TX**

**解释:**
XDP 程序返回值的含义如下：
- `XDP_DROP`：丢弃数据包
- `XDP_PASS`：传递给内核栈
- `XDP_TX`：将数据包返回到同一 NIC
- `XDP_REDIRECT`：转发到另一个接口
- `XDP_ABORTED`：错误处理

当你想将数据包发送回接收它的网络接口时，使用 XDP_TX。

</details>

3. eBPF Maps 的主要作用中，哪个不是？
   - A) 内核和用户空间之间的数据共享
   - B) 状态存储
   - C) 编译 eBPF 程序
   - D) 事件数据传输

<details>
<summary>显示答案</summary>

**答案: C) 编译 eBPF 程序**

**解释:**
eBPF Maps 是用于在内核和用户空间之间共享数据以及存储状态的数据结构。Maps 用于事件数据传输（PERF_EVENT_ARRAY、RINGBUF）、键值存储（HASH）、统计数据收集（PERCPU_ARRAY）等。编译 eBPF 程序由 Clang/LLVM 处理，不是 Maps 的作用。

</details>

4. 当 Cilium 替换 kube-proxy 时，eBPF 提供的主要优势是什么？
   - A) O(n) 性能，与服务数量成正比
   - B) 需要 iptables 规则评估
   - C) 通过 Map 查询实现 O(1) 性能
   - D) 使用 Netfilter

<details>
<summary>显示答案</summary>

**答案: C) 通过 Map 查询实现 O(1) 性能**

**解释:**
传统的 kube-proxy（iptables 模式）随着服务数量增加，性能会以 O(n) 方式下降。Cilium 使用 eBPF Maps 提供恒定的 O(1) 查询性能。这在连接建立时间、CPU 使用率和每秒连接数等所有方面都提供了显著的性能改进。

</details>

5. bpftrace 的主要目的是什么？
   - A) 将 eBPF 程序编译为 C
   - B) 加载内核模块
   - C) DTrace 风格的高级追踪
   - D) 构建容器镜像

<details>
<summary>显示答案</summary>

**答案: C) DTrace 风格的高级追踪**

**解释:**
bpftrace 是一种 DTrace 风格的高级追踪语言，允许你使用简单的单行命令对系统进行追踪。例如，你可以轻松执行如计数系统调用、追踪每个进程读取的字节数、追踪文件打开以及追踪 TCP 连接等任务。

</details>

6. 在 Tetragon 的 TracingPolicy 中，当检测到恶意文件访问时，哪个操作会立即终止进程？
   - A) action: Block
   - B) action: Sigkill
   - C) action: Deny
   - D) action: Terminate

<details>
<summary>显示答案</summary>

**答案: B) action: Sigkill**

**解释:**
在 Tetragon 的 TracingPolicy 中，`matchActions` 中的 `action: Sigkill` 会在发生与策略匹配的事件时立即用 SIGKILL 信号终止进程。这用于实时阻止敏感文件访问或恶意网络连接。

</details>

7. Hubble 的主要功能中，哪个不是？
   - A) 网络流观察
   - B) DNS 查询追踪
   - C) 编译 eBPF 程序
   - D) 策略决策监控

<details>
<summary>显示答案</summary>

**答案: C) 编译 eBPF 程序**

**解释:**
Hubble 是内置于 Cilium 中的网络可观测性平台，收集和监控网络流、DNS 查询、HTTP 请求、策略决策等。Hubble 是一个可观测性工具，不提供 eBPF 程序编译功能。

</details>

8. CO-RE（Compile Once, Run Everywhere）解决了什么问题？
   - A) 改进 eBPF 程序执行速度
   - B) 跨不同内核版本的可移植性
   - C) 减少内存使用
   - D) 降低网络延迟

<details>
<summary>显示答案</summary>

**答案: B) 跨不同内核版本的可移植性**

**解释:**
CO-RE 使用 libbpf 和 BTF（BPF Type Format）允许编译一次的 eBPF 程序在各种内核版本上运行。这减少了内核头文件依赖，自动处理结构体重定位，消除了为每个内核版本重新编译的需要。

</details>

9. Falco 使用 eBPF 检测什么？
   - A) 网络带宽使用情况
   - B) 运行时异常行为
   - C) 磁盘容量
   - D) CPU 温度

<details>
<summary>显示答案</summary>

**答案: B) 运行时异常行为**

**解释:**
Falco 是一个 CNCF 项目，使用 eBPF 检测运行时异常行为。它检测并警报安全威胁，如读取敏感文件、在容器中执行 shell 以及权限提升尝试，这些都是基于规则的。

</details>

10. eBPF 程序的栈大小限制是多少？
    - A) 128 字节
    - B) 256 字节
    - C) 512 字节
    - D) 1024 字节

<details>
<summary>显示答案</summary>

**答案: C) 512 字节**

**解释:**
eBPF 程序的栈大小限制为 512 字节。要解决这个限制，你需要使用 PERCPU_ARRAY 等 Maps 来分配更大的缓冲区。这个限制存在是为了确保内核安全。

</details>

## 简答题

11. 将 eBPF 字节码转换为本机机器码的编译器的名称是什么？

<details>
<summary>显示答案</summary>

**答案: JIT 编译器（Just-In-Time 编译器）**

**解释:**
JIT 编译器将 eBPF 字节码转换为本机机器码。这相比解释器提供了 4-5 倍的性能提升，并应用了架构特定的优化。它可以通过将 `/proc/sys/net/core/bpf_jit_enable` 设置为 1 来启用。

</details>

12. 动态追踪内核函数调用的 eBPF 程序类型的名称是什么？

<details>
<summary>显示答案</summary>

**答案: Kprobes（或 Kprobe）**

**解释:**
Kprobes 是一种 eBPF 程序类型，用于动态追踪内核函数调用。与追踪用户空间函数的 Uprobes 不同，Kprobes 追踪内核内的函数。例如，你可以追踪 `tcp_connect` 函数来收集 TCP 连接信息。

</details>

13. 内置于 Cilium 中的网络可观测性平台的名称是什么？

<details>
<summary>显示答案</summary>

**答案: Hubble**

**解释:**
Hubble 是内置于 Cilium 中的网络可观测性平台，从 eBPF 数据平面收集数据，包括网络流、DNS 查询、HTTP 请求和策略决策。你可以通过 Hubble CLI、Hubble UI 和 Hubble Relay 实时观察集群的网络流量。

</details>

14. 加载 eBPF 程序需要哪个 Linux 能力？（内核 5.8 及以上）

<details>
<summary>显示答案</summary>

**答案: CAP_BPF**

**解释:**
在内核 5.8 及以上，需要 `CAP_BPF` 能力来加载 eBPF 程序。在早期版本中，需要 `CAP_SYS_ADMIN`。此外，附加到性能监控事件需要 `CAP_PERFMON`，附加 XDP/TC 程序需要 `CAP_NET_ADMIN`。

</details>

15. 使用 eBPF 监控容器能耗的 CNCF 项目的名称是什么？

<details>
<summary>显示答案</summary>

**答案: Kepler（Kubernetes-based Efficient Power Level Exporter）**

**解释:**
Kepler 是一个使用 eBPF 监控容器能耗的项目。它提供 Prometheus 格式的指标，如 `kepler_container_joules_total`（每个容器的能耗）和 `kepler_container_gpu_joules_total`（GPU 能耗）。

</details>

## 动手题

16. 写出使用 bpftool 列出系统中当前加载的 eBPF 程序和查询特定程序详细信息的命令。

<details>
<summary>显示答案</summary>

**答案:**
```bash
# 列出加载的 eBPF 程序
sudo bpftool prog list

# 查询特定程序的详细信息（ID: 123）
sudo bpftool prog show id 123

# 转储程序字节码
sudo bpftool prog dump xlated id 123

# 转储 JIT 编译代码
sudo bpftool prog dump jited id 123
```

**解释:**
`bpftool prog list` 显示当前加载的所有 eBPF 程序列表。你可以检查每个程序的 ID、类型、名称、附加位置等。使用 `bpftool prog show id <ID>` 查询特定程序的详细信息，使用 `dump xlated` 和 `dump jited` 查看字节码和 JIT 编译的本机代码。

</details>

17. 写出一个 bpftrace 单行命令来实时追踪系统上所有进程发生的 TCP 连接。

<details>
<summary>显示答案</summary>

**答案:**
```bash
# TCP 连接追踪（方法 1：使用 kprobe）
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s (PID: %d) connecting...\n", comm, pid); }'

# TCP 连接追踪（方法 2：使用 tracepoint，更详细的信息）
sudo bpftrace -e 'tracepoint:tcp:tcp_connect { printf("%s -> %s:%d\n", ntop(args->saddr), ntop(args->daddr), args->dport); }'

# 按进程计算 TCP 连接
sudo bpftrace -e 'kprobe:tcp_connect { @[comm] = count(); }'
```

**解释:**
bpftrace 是一种 DTrace 风格的高级追踪语言，允许你使用简单的单行命令对系统进行追踪。`kprobe:tcp_connect` 在内核的 `tcp_connect` 函数被调用时触发。`comm` 表示进程名称，`pid` 表示进程 ID。使用 tracepoints 还允许你获取源/目标 IP 地址和端口信息。

</details>

18. 写出使用 Hubble CLI 观察来自特定命名空间的仅丢弃的数据包的命令。

<details>
<summary>显示答案</summary>

**答案:**
```bash
# 观察特定命名空间中的丢弃数据包
hubble observe --namespace production --verdict DROPPED

# 使用实时流式观察丢弃数据包
hubble observe --namespace production --verdict DROPPED -f

# 以 JSON 格式输出丢弃数据包的详细信息
hubble observe --namespace production --verdict DROPPED -o json

# 观察来自特定 Pod 的丢弃数据包
hubble observe --from-pod production/frontend --verdict DROPPED
```

**解释:**
Hubble 是内置于 Cilium 中的网络可观测性工具。`--namespace` 选项按特定命名空间过滤，`--verdict DROPPED` 只过滤丢弃的数据包。`-f` 选项提供实时流式传输，`-o json` 提供 JSON 格式输出。分析丢弃的数据包有助于诊断网络策略问题或配置错误。

</details>

## 高级题

19. 解释 eBPF 相比内核模块的三个主要优势，并具体说明每个优势在 Kubernetes 环境中提供的好处。

<details>
<summary>显示答案</summary>

**答案:**

eBPF 相比内核模块的主要优势及其在 Kubernetes 环境中的好处：

**1. 安全性（通过验证器保证安全）**
- **优势**: eBPF 验证器在加载程序前检查无限循环、内存访问违规、未初始化变量等，以防止内核崩溃。
- **Kubernetes 好处**: CNI 插件（Cilium）和安全工具（Tetragon、Falco）可以安全地在生产集群中运行。与内核模块不同，即使存在错误，整个系统也不会崩溃，维持高可用性。

**2. 可移植性（通过 CO-RE 实现内核版本独立）**
- **优势**: 使用 CO-RE（Compile Once, Run Everywhere）和 BTF，编译一次的 eBPF 程序可以在各种内核版本上运行。不需要为每个内核版本重新编译。
- **Kubernetes 好处**: 相同的网络和安全解决方案可以部署到异构节点环境（不同内核版本的节点）。集群升级或添加节点时，兼容性问题大大减少。

**3. 动态加载（无需重启即可加载/卸载程序）**
- **优势**: eBPF 程序可以动态加载和卸载，无需系统重启。功能可以在运行时添加或更改。
- **Kubernetes 好处**: 网络策略、安全规则和可观测性设置可以立即应用，无需节点重启。对 Cilium NetworkPolicy 或 Tetragon TracingPolicy 的更改实时反映，实现安全增强而无需操作中断。

**其他优势:**
- **性能**: JIT 编译提供本机代码级别的性能，在替换 kube-proxy 时实现 O(1) 服务查询。
- **开发难度**: 相比内核模块开发相对容易，实现快速功能开发和部署。

</details>

20. 设计一个方法，在 Kubernetes 集群中使用基于 eBPF 的安全解决方案（Tetragon 或 Falco）检测和阻止容器内的敏感文件访问。在你的解释中包括 TracingPolicy 或 Falco 规则示例。

<details>
<summary>显示答案</summary>

**答案:**

**基于 eBPF 的敏感文件访问安全设计**

**1. 安全需求定义**
- 检测目标：`/etc/shadow`、`/etc/passwd`、`/etc/sudoers`、`/var/run/secrets/`（Kubernetes 秘密）
- 响应方法：检测时警报，严重情况下终止进程

**2. Tetragon TracingPolicy 实现**

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: sensitive-file-protection
spec:
  kprobes:
    # 监控敏感文件打开
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        # 检测和记录 Kubernetes 秘密访问
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /var/run/secrets/kubernetes.io/
          matchActions:
            - action: Post  # 事件记录

        # 阻止系统认证文件访问
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /etc/shadow
                - /etc/sudoers
          matchNamespaces:
            - namespace: default
              operator: In
          matchActions:
            - action: Sigkill  # 立即终止进程
```

**3. Falco 规则实现**

```yaml
# /etc/falco/rules.d/sensitive-files.yaml
- rule: Read Kubernetes Secrets
  desc: Detect reading of Kubernetes secret files in containers
  condition: >
    open_read and
    container and
    (fd.name startswith /var/run/secrets/kubernetes.io/ or
     fd.name startswith /etc/shadow or
     fd.name startswith /etc/sudoers) and
    not proc.name in (kubelet, containerd)
  output: >
    Sensitive file access detected
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name namespace=%k8s.ns.name
     pod=%k8s.pod.name)
  priority: WARNING
  tags: [security, filesystem]

- rule: Write to Sensitive System Files
  desc: Detect writing to sensitive system files
  condition: >
    open_write and
    container and
    fd.name in (/etc/passwd, /etc/shadow, /etc/sudoers)
  output: >
    Attempt to modify sensitive file
    (file=%fd.name user=%user.name process=%proc.name
     container=%container.name)
  priority: CRITICAL
  tags: [security, filesystem]
```

**4. 部署和监控**

```bash
# 安装 Tetragon 并应用策略
helm install tetragon cilium/tetragon -n kube-system
kubectl apply -f sensitive-file-protection.yaml

# 监控事件
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon \
  -c export-stdout -f | tetra getevents -o compact

# 安装 Falco（eBPF 驱动）
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf

# 检查 Falco 警报
kubectl logs -n falco -l app.kubernetes.io/name=falco -f
```

**5. 架构解释**

```
┌─────────────────────────────────────────────────┐
│              Kubernetes Cluster                 │
│  ┌─────────────────┐    ┌─────────────────┐    │
│  │   Application   │    │   Application   │    │
│  │      Pod        │    │      Pod        │    │
│  └────────┬────────┘    └────────┬────────┘    │
│           │                      │             │
│  ┌────────▼──────────────────────▼────────┐   │
│  │              eBPF Layer                 │   │
│  │  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ Tetragon    │  │  Falco      │     │   │
│  │  │ TracingPol. │  │  Rules      │     │   │
│  │  └──────┬──────┘  └──────┬──────┘     │   │
│  │         │                 │            │   │
│  │         ▼                 ▼            │   │
│  │   [File Access Event Capture]          │   │
│  └────────────────────────────────────────┘   │
│                      │                         │
│  ┌───────────────────▼───────────────────┐   │
│  │           Security Response            │   │
│  │  • Event logging (Post)               │   │
│  │  • Process termination (Sigkill)      │   │
│  │  • SIEM alert forwarding              │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

这个设计利用 eBPF 的内核级可见性实时检测和响应敏感文件访问，无需修改应用程序。

</details>

---

[返回学习材料](../../basics/05-ebpf-fundamentals.md) | [下一个测验：容器技术](./03-container-technology-quiz.md)
