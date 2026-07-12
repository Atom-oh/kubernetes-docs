# eBPF 基础测验

> **支持版本**: Linux Kernel 4.18+, Kubernetes 1.25+
> **最后更新**: February 23, 2026

本测验测试你对 eBPF (extended Berkeley Packet Filter) 的整体理解，涵盖从基本概念到其在 Kubernetes 环境中的应用。

## 选择题

1. eBPF verifier 不检查什么？
   - A) 没有无限循环
   - B) 没有越界内存访问
   - C) 程序执行速度
   - D) 不使用未初始化变量

<details>
<summary>查看答案</summary>

**答案：C) 程序执行速度**

**解释：**
eBPF verifier 会检查没有无限循环（DAG 结构验证）、没有越界内存访问、不使用未初始化变量、helper function 调用正确，以及保证程序终止，以确保程序安全。程序执行速度不是 verifier 的验证项。

</details>

2. 哪个 XDP (eXpress Data Path) program 返回值会将 packet 发送回同一个 NIC？
   - A) XDP_DROP
   - B) XDP_PASS
   - C) XDP_TX
   - D) XDP_REDIRECT

<details>
<summary>查看答案</summary>

**答案：C) XDP_TX**

**解释：**
XDP program 返回值的含义如下：
- `XDP_DROP`: 丢弃 packet
- `XDP_PASS`: 传递给 kernel stack
- `XDP_TX`: 将 packet 返回到同一个 NIC
- `XDP_REDIRECT`: 转发到另一个 interface
- `XDP_ABORTED`: 错误处理

当你想把 packet 发送回接收它的网络 interface 时，会使用 XDP_TX。

</details>

3. 哪一项不是 eBPF Maps 的主要作用？
   - A) 在 kernel 和 user space 之间共享数据
   - B) 状态存储
   - C) 编译 eBPF programs
   - D) 事件数据传输

<details>
<summary>查看答案</summary>

**答案：C) 编译 eBPF programs**

**解释：**
eBPF maps 是用于在 kernel 和 user space 之间共享数据以及存储状态的数据结构。Maps 可用于事件数据传输（PERF_EVENT_ARRAY、RINGBUF）、key-value 存储（HASH）、统计信息收集（PERCPU_ARRAY）等。编译 eBPF programs 由 Clang/LLVM 处理，并不是 maps 的作用。

</details>

4. 当 Cilium 替代 kube-proxy 时，eBPF 提供的主要优势是什么？
   - A) 与 services 数量成正比的 O(n) 性能
   - B) 需要 iptables rule 评估
   - C) 通过 map lookup 实现 O(1) 性能
   - D) 使用 Netfilter

<details>
<summary>查看答案</summary>

**答案：C) 通过 map lookup 实现 O(1) 性能**

**解释：**
传统的 kube-proxy（iptables mode）会随着 services 数量增加出现 O(n) 性能下降。Cilium 使用 eBPF maps 提供恒定的 O(1) lookup 性能。这在连接建立时间、CPU 使用率和每秒连接数等各方面都带来了显著的性能提升。

</details>

5. bpftrace 的主要用途是什么？
   - A) 将 eBPF programs 编译为 C
   - B) 加载 kernel modules
   - C) DTrace 风格的高级 tracing
   - D) 构建 container images

<details>
<summary>查看答案</summary>

**答案：C) DTrace 风格的高级 tracing**

**解释：**
bpftrace 是一种 DTrace 风格的高级 tracing language，可让你用简单的单行命令对系统进行 trace。例如，你可以轻松执行统计 system calls、跟踪每个 process 读取的 bytes、trace 文件打开以及跟踪 TCP 连接等任务。

</details>

6. 在 Tetragon 的 TracingPolicy 中，检测到恶意文件访问时，哪个 action 会立即终止 process？
   - A) action: Block
   - B) action: Sigkill
   - C) action: Deny
   - D) action: Terminate

<details>
<summary>查看答案</summary>

**答案：B) action: Sigkill**

**解释：**
在 Tetragon 的 TracingPolicy 中，当发生与 policy 匹配的事件时，`matchActions` 中的 `action: Sigkill` 会用 SIGKILL signal 立即终止 process。这用于实时阻止敏感文件访问或恶意网络连接。

</details>

7. 哪一项不是 Hubble 的主要功能？
   - A) 网络 flow 观察
   - B) DNS query 跟踪
   - C) 编译 eBPF programs
   - D) Policy decision 监控

<details>
<summary>查看答案</summary>

**答案：C) 编译 eBPF programs**

**解释：**
Hubble 是内置于 Cilium 的网络 observability platform，用于收集和监控网络 flows、DNS queries、HTTP requests、policy decisions 等。Hubble 是一个 observability tool，不提供 eBPF program 编译功能。

</details>

8. CO-RE (Compile Once, Run Everywhere) 解决了什么问题？
   - A) 提高 eBPF program 执行速度
   - B) 跨不同 kernel 版本的可移植性
   - C) 降低内存使用量
   - D) 降低网络延迟

<details>
<summary>查看答案</summary>

**答案：B) 跨不同 kernel 版本的可移植性**

**解释：**
CO-RE 使用 libbpf 和 BTF (BPF Type Format)，使编译一次的 eBPF programs 能够在各种 kernel 版本上运行。这减少了对 kernel headers 的依赖，并自动处理 struct relocation，从而无需针对每个 kernel 版本重新编译。

</details>

9. Falco 使用 eBPF 检测什么？
   - A) 网络带宽使用量
   - B) 运行时异常行为
   - C) 磁盘容量
   - D) CPU 温度

<details>
<summary>查看答案</summary>

**答案：B) 运行时异常行为**

**解释：**
Falco 是一个 CNCF project，使用 eBPF 检测运行时异常行为。它基于 rules 检测敏感文件读取、在 containers 中执行 shells、提权尝试等安全威胁并发出警报。

</details>

10. eBPF programs 的 stack size 限制是多少？
    - A) 128 bytes
    - B) 256 bytes
    - C) 512 bytes
    - D) 1024 bytes

<details>
<summary>查看答案</summary>

**答案：C) 512 bytes**

**解释：**
eBPF programs 有 512 byte 的 stack size 限制。要绕过此限制，需要使用 PERCPU_ARRAY 等 maps 来分配更大的 buffers。此限制是为了确保 kernel 安全。

</details>

## 简答题

11. 将 eBPF bytecode 转换为 native machine code 的 compiler 叫什么？

<details>
<summary>查看答案</summary>

**答案：JIT compiler (Just-In-Time compiler)**

**解释：**
JIT compiler 将 eBPF bytecode 转换为 native machine code。与 interpreter 相比，这可提供 4-5 倍性能提升，并应用特定于架构的优化。可以通过将 `/proc/sys/net/core/bpf_jit_enable` 设置为 1 来启用它。

</details>

12. 动态 trace kernel function calls 的 eBPF program type 叫什么？

<details>
<summary>查看答案</summary>

**答案：Kprobes（或 Kprobe）**

**解释：**
Kprobes 是一种 eBPF program type，用于动态 trace kernel function calls。与 trace user space functions 的 Uprobes 不同，Kprobes trace kernel 内部的 functions。例如，你可以 trace `tcp_connect` function 来收集 TCP 连接信息。

</details>

13. 内置于 Cilium 的网络 observability platform 叫什么？

<details>
<summary>查看答案</summary>

**答案：Hubble**

**解释：**
Hubble 是内置于 Cilium 的网络 observability platform，它从 eBPF dataplane 收集数据，包括网络 flows、DNS queries、HTTP requests 和 policy decisions。你可以通过 Hubble CLI、Hubble UI 和 Hubble Relay 实时观察 cluster 的网络流量。

</details>

14. 加载 eBPF programs 需要什么 Linux capability？（kernel 5.8 及以上）

<details>
<summary>查看答案</summary>

**答案：CAP_BPF**

**解释：**
在 kernel 5.8 及以上版本中，加载 eBPF programs 需要 `CAP_BPF` capability。在更早版本中，需要 `CAP_SYS_ADMIN`。此外，附加到 performance monitoring events 需要 `CAP_PERFMON`，附加 XDP/TC programs 需要 `CAP_NET_ADMIN`。

</details>

15. 使用 eBPF 监控 container 能耗的 CNCF project 叫什么？

<details>
<summary>查看答案</summary>

**答案：Kepler (Kubernetes-based Efficient Power Level Exporter)**

**解释：**
Kepler 是一个使用 eBPF 监控 container 能耗的 project。它提供 Prometheus 格式的 metrics，例如 `kepler_container_joules_total`（每个 container 的能耗）和 `kepler_container_gpu_joules_total`（GPU 能耗）。

</details>

## 实操题

16. 编写使用 bpftool 列出系统当前加载的 eBPF programs，并查询特定 program 详细信息的 commands。

<details>
<summary>查看答案</summary>

**答案：**
```bash
# List loaded eBPF programs
sudo bpftool prog list

# Query detailed information for a specific program (ID: 123)
sudo bpftool prog show id 123

# Dump program bytecode
sudo bpftool prog dump xlated id 123

# Dump JIT compiled code
sudo bpftool prog dump jited id 123
```

**解释：**
`bpftool prog list` 显示当前加载的所有 eBPF programs 列表。你可以查看每个 program 的 ID、type、name、attachment location 等。使用 `bpftool prog show id <ID>` 查询特定 program 的详细信息，并使用 `dump xlated` 和 `dump jited` 查看 bytecode 和 JIT 编译后的 native code。

</details>

17. 编写一个 bpftrace one-liner command，用于实时 trace 系统上所有 processes 发生的 TCP 连接。

<details>
<summary>查看答案</summary>

**答案：**
```bash
# TCP connection tracing (Method 1: using kprobe)
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s (PID: %d) connecting...\n", comm, pid); }'

# TCP connection tracing (Method 2: using tracepoint, more detailed info)
sudo bpftrace -e 'tracepoint:tcp:tcp_connect { printf("%s -> %s:%d\n", ntop(args->saddr), ntop(args->daddr), args->dport); }'

# Count TCP connections by process
sudo bpftrace -e 'kprobe:tcp_connect { @[comm] = count(); }'
```

**解释：**
bpftrace 是一种 DTrace 风格的高级 tracing language，可让你用简单的 one-liners 对系统进行 trace。`kprobe:tcp_connect` 会在 kernel 的 `tcp_connect` function 被调用时触发。`comm` 表示 process name，`pid` 表示 process ID。使用 tracepoints 还可以获取 source/destination IP addresses 和 port information。

</details>

18. 编写使用 Hubble CLI 仅观察来自特定 namespace 的 dropped packets 的 command。

<details>
<summary>查看答案</summary>

**答案：**
```bash
# Observe dropped packets in a specific namespace
hubble observe --namespace production --verdict DROPPED

# Observe dropped packets with real-time streaming
hubble observe --namespace production --verdict DROPPED -f

# Output detailed information of dropped packets in JSON format
hubble observe --namespace production --verdict DROPPED -o json

# Observe dropped packets from a specific Pod
hubble observe --from-pod production/frontend --verdict DROPPED
```

**解释：**
Hubble 是内置于 Cilium 的网络 observability tool。`--namespace` option 按特定 namespace 过滤，`--verdict DROPPED` 只过滤 dropped packets。`-f` option 提供实时 streaming，`-o json` 提供 JSON 格式输出。分析 dropped packets 有助于诊断 network policy 问题或配置错误。

</details>

## 进阶题

19. 解释 eBPF 相比 kernel modules 的三个主要优势，并具体说明每个优势在 Kubernetes 环境中提供什么好处。

<details>
<summary>查看答案</summary>

**答案：**

eBPF 相比 kernel modules 的主要优势及其在 Kubernetes 环境中的好处：

**1. 安全性（通过 verifier 保证安全）**
- **优势**：eBPF verifier 会在加载 program 前检查无限循环、内存访问违规、未初始化变量等，以防止 kernel crashes。
- **Kubernetes 好处**：CNI plugins（Cilium）和安全工具（Tetragon、Falco）可以在 production clusters 中安全运行。与 kernel modules 不同，即使存在 bugs，整个系统也不会 crash，从而保持高可用性。

**2. 可移植性（通过 CO-RE 实现 kernel version independence）**
- **优势**：使用 CO-RE (Compile Once, Run Everywhere) 和 BTF，编译一次的 eBPF programs 可以在各种 kernel 版本上运行。无需针对每个 kernel 版本重新编译。
- **Kubernetes 好处**：同样的 networking 和 security solutions 可以部署到异构 node environments（具有不同 kernel 版本的 nodes）中。在 cluster upgrades 或添加 nodes 期间，兼容性问题会大幅减少。

**3. 动态加载（无需重启即可加载/卸载 program）**
- **优势**：eBPF programs 可以在不重启系统的情况下动态加载和卸载。可以在 runtime 添加或更改功能。
- **Kubernetes 好处**：Network policies、security rules 和 observability settings 可以在不重启 nodes 的情况下立即应用。Cilium NetworkPolicy 或 Tetragon TracingPolicy 的变更会实时反映，从而在不中断运营的情况下增强安全性。

**其他优势：**
- **性能**：JIT compilation 提供 native code 级别的性能，在替代 kube-proxy 时可实现 O(1) service lookup。
- **开发难度**：相对 kernel module 开发更容易，支持快速功能开发和部署。

</details>

20. 设计一种方法，在 Kubernetes cluster 中使用基于 eBPF 的安全解决方案（Tetragon 或 Falco）检测并阻止 containers 内的敏感文件访问。在说明中包含 TracingPolicy 或 Falco rule 示例。

<details>
<summary>查看答案</summary>

**答案：**

**基于 eBPF 的敏感文件访问安全设计**

**1. 安全需求定义**
- 检测目标：`/etc/shadow`、`/etc/passwd`、`/etc/sudoers`、`/var/run/secrets/`（Kubernetes secrets）
- 响应方式：检测时告警，严重情况下终止 process

**2. Tetragon TracingPolicy 实现**

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: sensitive-file-protection
spec:
  kprobes:
    # Monitor sensitive file opens
    - call: security_file_open
      syscall: false
      args:
        - index: 0
          type: file
      selectors:
        # Detect and log Kubernetes secret access
        - matchArgs:
            - index: 0
              operator: Prefix
              values:
                - /var/run/secrets/kubernetes.io/
          matchActions:
            - action: Post  # Event logging

        # Block system authentication file access
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
            - action: Sigkill  # Immediately terminate process
```

**3. Falco Rules 实现**

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
# Install Tetragon and apply policy
helm install tetragon cilium/tetragon -n kube-system
kubectl apply -f sensitive-file-protection.yaml

# Monitor events
kubectl logs -n kube-system -l app.kubernetes.io/name=tetragon \
  -c export-stdout -f | tetra getevents -o compact

# Install Falco (eBPF driver)
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf

# Check Falco alerts
kubectl logs -n falco -l app.kubernetes.io/name=falco -f
```

**5. 架构说明**

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

此设计利用 eBPF 的 kernel-level visibility，在无需修改应用程序的情况下实时检测并响应敏感文件访问。

</details>

---

[返回学习资料](../../basics/05-ebpf-fundamentals.md) | [下一个测验：Container Technology](./03-container-technology-quiz.md)
