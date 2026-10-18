# Cilium eBPF 测验

> **审阅基线**：Cilium 1.20.3；Linux 5.10+ 或有文档记录的等效回移植版本；限制示例使用 Linux 6.12。
> **2026-10-16**


## eBPF 基本概念

1. **eBPF 代表什么？**
   - A) 扩展伯克利包过滤器
   - B) 增强型伯克利进程过滤器
   - C) 扩展二进制处理框架
   - D) 增强型后端处理函数

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>：A) 扩展伯克利包过滤器</p>
   <p><strong>解释</strong>：eBPF 代表扩展伯克利包过滤器，是对原始 BPF 技术的扩展。</p>
   </details>

2. **本指南中的 Linux eBPF 程序在其 hook 触发时在哪里执行？**
   - A) 仅在用户空间
   - B) 在内核中
   - C) 在 Hubble Relay 中
   - D) 在容器运行时进程中

   <details>
   <summary>显示答案</summary>

   **答案：B) 在内核中**

   这些程序通过内核支持的解释器或 JIT 路径在内核中执行。加载器和观察程序在用户空间运行。在内核中执行并不意味着绝对安全。

   </details>

3. **通过 BPF 验证器意味着什么？**
   - A) 不可能发生内核崩溃
   - B) 预期的应用程序策略已被证明正确
   - C) 程序通过了针对其类型、内存访问和执行约束的检查
   - D) 不再需要进一步测试

   <details>
   <summary>显示答案</summary>

   **答案：C) 程序通过了针对其类型、内存访问和执行约束的检查**

   验证器会限制程序执行；验证器、JIT、helper 和内核中的 bug，以及错误的程序逻辑仍然可能存在。

   </details>

4. **eBPF 程序可以附加到的内核事件称为什么？**
   - A) 触发器
   - B) Hook
   - C) 事件侦听器
   - D) 回调

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>：B) Hook</p>
   <p><strong>解释</strong>：eBPF 程序会附加到内核中的各种 hook 点，并在事件发生时执行。</p>
   </details>

5. **什么机制可在 BPF 程序与用户空间之间共享状态或事件？**
   - A) 环境变量
   - B) 仅普通磁盘文件
   - C) BPF maps
   - D) Kubernetes 注解

   <details>
   <summary>显示答案</summary>

   **答案：C) BPF maps**

   Map 包括键值结构、事件缓冲区和引用容器。Pin 会保留引用，但不会在重启后保留 map 内容；重新加载不会自动复用 map。

   </details>

## eBPF 与 Cilium

6. **为什么 eBPF 有助于实现 Cilium 的数据路径？**
   - A) 可编程内核 hook 和 map 无需为每项数据路径变更都新增自定义模块
   - B) 它消除了对所有内核模块的依赖
   - C) 它会自动配置任何云网络
   - D) 它保证降低内存用量

   <details>
   <summary>显示答案</summary>

   **答案：A) 可编程内核 hook 和 map 无需为每项数据路径变更都新增自定义模块**

   Cilium 使用受支持的内核设施来进行转发、策略处理和 Service 转换。仍然需要所需的内核功能，并针对具体工作负载进行测试。

   </details>

7. **哪项陈述正确描述了 Cilium 的 WireGuard/IPsec 加密模式？**
   - A) 每项加密操作都是一条 BPF 指令
   - B) 无需任何配置或密钥操作
   - C) 所有流量路径始终都会加密
   - D) BPF 将流量与内核 WireGuard/IPsec 设施集成；覆盖范围和密钥管理取决于模式

   <details>
   <summary>显示答案</summary>

   **答案：D) BPF 将流量与内核 WireGuard/IPsec 设施集成；覆盖范围和密钥管理取决于模式**

   BPF 流量引导和内核加密属于不同职责。节点加密不会自动启用工作负载 mTLS。

   </details>

8. **Cilium 可以使用哪些 hook 来替代 kube-proxy？**
   - A) 仅 XDP
   - B) 仅 TC
   - C) 仅跟踪探针
   - D) Socket hook、TC 数据包路径以及可选的 XDP 加速

   <details>
   <summary>显示答案</summary>

   **答案：D) Socket hook、TC 数据包路径以及可选的 XDP 加速**

   路径取决于流量和配置。Service 转换可以在 socket hook 处、数据包路径中，或通过受支持的 XDP 加速，在数据包生成前发生。

   </details>

9. **应如何评估关于某项 Cilium 配置更快的说法？**
   - A) 假设所有 BPF map 查找都具有有保证的延迟
   - B) 记录协议、路由、策略、加密和代理设置，并对工作负载进行测量
   - C) 仅凭内核执行就认定该说法成立
   - D) 只比较产品名称

   <details>
   <summary>显示答案</summary>

   **答案：B) 记录协议、路由、策略、加密和代理设置，并对工作负载进行测量**

   内核和用户空间组件的开销取决于工作负载。合成测试结果和 hook 选择都不能保证应用程序延迟。

   </details>

10. **Hubble 的 HTTP 观察结果可能来自哪里？**
    - A) 自动解密的任意流量
    - B) 仅 CPU 硬件计数器
    - C) 受支持的 L7 代理路径与网络流信息相结合
    - D) 无论设置如何，都会捕获每个数据包

    <details>
    <summary>显示答案</summary>

    **答案：C) 受支持的 L7 代理路径与网络流信息相结合**

    L7 可见性取决于代理、策略和可见性设置。流记录不会自动成为应用程序 span 或任意业务指标。

    </details>

## eBPF 编程

11. **哪项关于编译器/工具链的陈述正确？**
    - A) Clang 可以直接编译 C 和 Rust 源代码
    - B) C 通常使用 Clang 的 BPF 后端；Rust 使用自己的工具链生态系统
    - C) 主机端语法检查可以证明程序通过了内核验证器检查
    - D) BTF 可以补上缺失的内核功能

    <details>
    <summary>显示答案</summary>

    **答案：B) C 通常使用 Clang 的 BPF 后端；Rust 使用自己的工具链生态系统**

    主机端语法检查、面向 BPF 的编译、内核验证和实时行为是不同的检查环节。CO-RE 不会创建缺失的 helper 或配置。

    </details>

12. **以下哪项不是 eBPF 程序开发框架？**
    - A) BCC (BPF Compiler Collection)
    - B) libbpf
    - C) bpftrace
    - D) libpcap

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>：D) libpcap</p>
    <p><strong>解释</strong>：libpcap 是一个数据包捕获库，并非 eBPF 程序开发框架。BCC、libbpf 和 bpftrace 都是 eBPF 程序开发框架。</p>
    </details>

13. **以下哪项不是 eBPF map 类型？**
    - A) 哈希 Map
    - B) 数组 Map
    - C) LRU Map
    - D) 图 Map

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>：D) 图 Map</p>
    <p><strong>解释</strong>：eBPF 支持多种 map 类型，包括哈希 map、数组 map 和 LRU map，但不支持图 map。</p>
    </details>

14. **哪项陈述符合本指南所述的 Linux 6.12 限制？**
    - A) 所有程序的限制都是 4,096 条指令
    - B) 所有低于一百万条指令的程序都会被接受
    - C) 程序或分析都没有任何限制
    - D) 支持 BPF 的加载路径允许最多一百万条指令，非特权路径允许 4,096 条指令，验证器复杂度则是另一项独立限制

    <details>
    <summary>显示答案</summary>

    **答案：D) 支持 BPF 的加载路径允许最多一百万条指令，非特权路径允许 4,096 条指令，验证器复杂度则是另一项独立限制**

    程序长度和验证器探索是不同的约束。能力/令牌、程序类型和其他检查都可能拒绝加载；非特权 BPF 通常处于禁用状态。

    </details>

15. **使用哪个系统调用将 eBPF 程序加载到内核中？**
    - A) bpf()
    - B) ebpf()
    - C) sysfs()
    - D) ioctl()

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>：A) bpf()</p>
    <p><strong>解释</strong>：bpf() 系统调用用于将 eBPF 程序加载到内核中，以及创建和访问 eBPF map。</p>
    </details>

## eBPF 性能与监控

16. **原生驱动 XDP 与后续基于 skb 的处理有何区别？**
    - A) 它始终绕过所有内核子系统
    - B) 它保证固定的数据包速率
    - C) 它可以在分配 skb 之前处理数据包
    - D) 它在所有 NIC 和通用模式下的工作方式都完全相同

    <details>
    <summary>显示答案</summary>

    **答案：C) 它可以在分配 skb 之前处理数据包**

    原生 XDP 在接收处理的早期阶段运行。通用模式、卸载模式和驱动支持各不相同；实际性能需要测量。

    </details>

17. **哪个 bpftool 命令具有所述含义？**
    - A) bpftool -p map dump 用于测量查找延迟
    - B) bpftool prog profile id ID duration 10 cycles instructions 用于请求性能分析指标
    - C) bpftool prog load 始终会附加跟踪点
    - D) bpftool prog show 会启用缺失的内核功能

    <details>
    <summary>显示答案</summary>

    **答案：B) bpftool prog profile id ID duration 10 cycles instructions 用于请求性能分析指标**

    性能分析需要指定指标名称、权限以及内核/PMU 支持。格式化输出、加载和附加是不同的操作。

    </details>

18. **在此上下文中，Hubble 是什么？**
    - A) 内核编译器
    - B) 所有应用程序跟踪 SDK 的替代品
    - C) 利用数据路径和可用代理事件实现的 Cilium 网络可观测性
    - D) 自动策略同步器

    <details>
    <summary>显示答案</summary>

    **答案：C) 利用数据路径和可用代理事件实现的 Cilium 网络可观测性**

    Hubble 可观测网络流和受支持的 L7 事件。采集限制和过滤器会影响结果；仅有 JSON 并不等于服务地图可视化。

    </details>

19. **基于 map 的实验会统计什么？**
    - A) 按唯一可执行文件路径统计所有 execve 尝试，且不会丢失
    - B) 按短 comm 名称统计成功的执行事件，并受容量和测量限制影响
    - C) 仅统计 default 命名空间中的 Pod
    - D) 统计此前每次重启以来的所有进程

    <details>
    <summary>显示答案</summary>

    **答案：B) 按短 comm 名称统计成功的执行事件，并受容量和测量限制影响**

    sched_process_exec 可观察成功的执行状态转换。名称可能冲突；此主机范围示例使用有界内存状态，并选取部分丢失计数器。

    </details>

20. **哪个仅限 Agent 本地使用的命令可以检查 Service 后端 map 条目？**
    - A) cilium-dbg bpf lb list --backends
    - B) cilium debug --all-kernels
    - C) cilium policy trace --enable
    - D) hubble compile bpf

    <details>
    <summary>显示答案</summary>

    **答案：A) cilium-dbg bpf lb list --backends**

    在正确节点的 Agent 中使用 cilium-dbg。cilium-dbg map get 显示用户空间缓存的内容；应使用适当的解码器，而不要修改原始 map。

    </details>

[查看指南](../../../networking/cilium/02-ebpf.md)。
