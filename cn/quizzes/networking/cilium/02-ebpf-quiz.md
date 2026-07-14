# Cilium eBPF 测验

> **支持的版本**: Cilium 1.17, Linux Kernel 4.19+
> **最后更新**: February 22, 2026

## eBPF 基本概念

1. **eBPF 代表什么？**
   - A) 扩展 Berkeley 数据包过滤器
   - B) 增强 Berkeley 进程过滤器
   - C) 扩展二进制处理框架
   - D) 增强后端处理函数

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) 扩展 Berkeley 数据包过滤器</p>
   <p><strong>说明</strong>: eBPF 代表 Extended Berkeley Packet Filter，它是原始 BPF 技术的扩展。</p>
   </details>

2. **eBPF 程序在哪里执行？**
   - A) 用户空间
   - B) 内核空间
   - C) Hypervisor
   - D) Container Runtime

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) 内核空间</p>
   <p><strong>说明</strong>: eBPF 程序在 Linux 内核中安全运行。</p>
   </details>

3. **哪种机制可确保 eBPF 程序的安全性？**
   - A) 沙箱
   - B) 虚拟机
   - C) 静态验证器
   - D) 容器化

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) 静态验证器</p>
   <p><strong>说明</strong>: eBPF 验证器会在程序加载前检查其安全性，以防止无限循环或内核崩溃。</p>
   </details>

4. **eBPF 程序可以附加到的内核事件称为什么？**
   - A) 触发器
   - B) 钩子
   - C) 事件监听器
   - D) 回调

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) 钩子</p>
   <p><strong>说明</strong>: eBPF 程序会附加到内核中的各种钩子点，并在事件发生时执行。</p>
   </details>

5. **eBPF 程序与用户空间应用程序之间使用什么来共享数据？**
   - A) 共享内存
   - B) 管道
   - C) BPF Maps
   - D) Sockets

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) BPF Maps</p>
   <p><strong>说明</strong>: BPF Maps 是用于在 eBPF 程序与用户空间应用程序之间共享数据的键值存储。</p>
   </details>

## eBPF 和 Cilium

6. **Cilium 使用 eBPF 的主要原因是什么？**
   - A) 无需内核模块即可实现网络功能
   - B) 提供更好的用户界面
   - C) 使用更少内存
   - D) 更简单的安装过程

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: A) 无需内核模块即可实现网络功能</p>
   <p><strong>说明</strong>: Cilium 使用 eBPF 实现高性能网络、负载均衡、安全策略及其他功能，而无需内核模块。</p>
   </details>

7. **以下哪项不是 Cilium 中使用 eBPF 实现的功能？**
   - A) 网络策略强制执行
   - B) Service 负载均衡
   - C) 网络数据包加密
   - D) 用户身份验证

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: D) 用户身份验证</p>
   <p><strong>说明</strong>: Cilium 使用 eBPF 实现网络策略强制执行、Service 负载均衡和网络数据包处理，但用户身份验证通常由其他系统处理。</p>
   </details>

8. **Cilium 使用哪项 eBPF 功能来替代 kube-proxy？**
   - A) XDP (eXpress Data Path)
   - B) TC (Traffic Control) BPF
   - C) Socket BPF
   - D) Tracing BPF

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: B) TC (Traffic Control) BPF</p>
   <p><strong>说明</strong>: Cilium 主要使用 TC (Traffic Control) BPF 程序来替代 kube-proxy 的 Service 负载均衡功能。</p>
   </details>

9. **为什么 Cilium 基于 eBPF 的负载均衡优于 kube-proxy？**
   - A) 支持更多 Service 类型
   - B) 更好的用户界面
   - C) 更低延迟和更高吞吐量
   - D) 更简单的配置

   <details>
   <summary>显示答案</summary>
   <p><strong>答案</strong>: C) 更低延迟和更高吞吐量</p>
   <p><strong>说明</strong>: Cilium 基于 eBPF 的负载均衡直接在内核空间处理数据包，提供更低的延迟和更高的吞吐量。</p>
   </details>

10. **以下哪项不是 Cilium 中使用 eBPF 收集的指标？**
    - A) 网络连接状态
    - B) 数据包丢弃原因
    - C) Service 响应时间
    - D) 用户登录时间

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) 用户登录时间</p>
    <p><strong>说明</strong>: Cilium 使用 eBPF 收集网络相关指标，例如网络连接状态、数据包丢弃原因和 Service 响应时间，但不会收集用户登录时间等应用程序级别的指标。</p>
    </details>

## eBPF 编程

11. **主要使用哪种语言编写 eBPF 程序？**
    - A) Python
    - B) Go
    - C) C
    - D) Rust

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) C</p>
    <p><strong>说明</strong>: eBPF 程序主要使用 C 编写，并使用 LLVM 编译器编译为 eBPF 字节码。</p>
    </details>

12. **以下哪项不是开发 eBPF 程序的框架？**
    - A) BCC (BPF Compiler Collection)
    - B) libbpf
    - C) bpftrace
    - D) libpcap

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) libpcap</p>
    <p><strong>说明</strong>: libpcap 是一个数据包捕获库，不是 eBPF 程序开发框架。BCC、libbpf 和 bpftrace 都是用于开发 eBPF 程序的框架。</p>
    </details>

13. **以下哪项不是 eBPF map 的类型？**
    - A) Hash Map
    - B) Array Map
    - C) LRU Map
    - D) Graph Map

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: D) Graph Map</p>
    <p><strong>说明</strong>: eBPF 支持多种 map 类型，包括 hash map、array map 和 LRU map，但不支持 graph map。</p>
    </details>

14. **eBPF 程序的最大指令数是多少？**
    - A) 1,000
    - B) 4,096
    - C) 10,000
    - D) 无限制

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) 4,096</p>
    <p><strong>说明</strong>: eBPF 程序最多限制为 4,096 条指令。这一限制用于确保安全性。</p>
    </details>

15. **使用什么系统调用将 eBPF 程序加载到内核中？**
    - A) bpf()
    - B) ebpf()
    - C) sysfs()
    - D) ioctl()

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) bpf()</p>
    <p><strong>说明</strong>: bpf() 系统调用用于将 eBPF 程序加载到内核中，以及创建和访问 eBPF maps。</p>
    </details>

## eBPF 性能和监控

16. **XDP (eXpress Data Path) 提供的主要优势是什么？**
    - A) 更好的安全性
    - B) 更易编程
    - C) 更低延迟
    - D) 更高兼容性

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) 更低延迟</p>
    <p><strong>说明</strong>: XDP 在网络驱动程序级别处理数据包，绕过内核网络堆栈以提供极低延迟。</p>
    </details>

17. **在 Cilium 中使用什么工具监控 eBPF 程序的性能？**
    - A) top
    - B) bpftool
    - C) htop
    - D) iotop

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) bpftool</p>
    <p><strong>说明</strong>: bpftool 是用于检查和管理 eBPF 程序及 maps 的工具，也用于性能监控。</p>
    </details>

18. **Cilium 基于 eBPF 的网络监控工具是什么？**
    - A) Prometheus
    - B) Hubble
    - C) Grafana
    - D) Jaeger

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: B) Hubble</p>
    <p><strong>说明</strong>: Hubble 是 Cilium 基于 eBPF 的网络监控工具，可以实时观察和分析网络流。</p>
    </details>

19. **使用什么工具查找 eBPF 程序中的性能瓶颈？**
    - A) strace
    - B) ltrace
    - C) perf
    - D) gdb

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: C) perf</p>
    <p><strong>说明</strong>: perf 是 Linux 性能分析工具，用于查找 eBPF 程序中的性能瓶颈。</p>
    </details>

20. **在 Cilium 中使用什么命令调试 eBPF 程序？**
    - A) `cilium bpf`
    - B) `cilium debug`
    - C) `cilium monitor`
    - D) `cilium trace`

    <details>
    <summary>显示答案</summary>
    <p><strong>答案</strong>: A) `cilium bpf`</p>
    <p><strong>说明</strong>: `cilium bpf` 命令用于检查和调试 Cilium 的 eBPF 程序及 maps。</p>
    </details>
