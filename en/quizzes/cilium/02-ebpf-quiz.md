# Cilium eBPF Quiz

> **Supported Version**: Cilium 1.17, Linux Kernel 4.19+
> **Last Updated**: July 21, 2025

## eBPF Basic Concepts

1. **What does eBPF stand for?**
   - A) Extended Berkeley Packet Filter
   - B) Enhanced Berkeley Process Filter
   - C) Extended Binary Processing Framework
   - D) Enhanced Backend Processing Function

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) Extended Berkeley Packet Filter</p>
   <p><strong>Explanation</strong>: eBPF stands for Extended Berkeley Packet Filter, which is an extension of the original BPF technology.</p>
   </details>

2. **Where do eBPF programs execute?**
   - A) User Space
   - B) Kernel Space
   - C) Hypervisor
   - D) Container Runtime

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Kernel Space</p>
   <p><strong>Explanation</strong>: eBPF programs run safely inside the Linux kernel.</p>
   </details>

3. **What mechanism ensures the safety of eBPF programs?**
   - A) Sandbox
   - B) Virtual Machine
   - C) Static Verifier
   - D) Containerization

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) Static Verifier</p>
   <p><strong>Explanation</strong>: The eBPF verifier checks program safety before it is loaded to prevent infinite loops or kernel crashes.</p>
   </details>

4. **What are the kernel events that eBPF programs can attach to called?**
   - A) Triggers
   - B) Hooks
   - C) Event Listeners
   - D) Callbacks

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) Hooks</p>
   <p><strong>Explanation</strong>: eBPF programs are attached to various hook points in the kernel and execute when events occur.</p>
   </details>

5. **What is used for data sharing between eBPF programs and user space applications?**
   - A) Shared Memory
   - B) Pipes
   - C) BPF Maps
   - D) Sockets

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) BPF Maps</p>
   <p><strong>Explanation</strong>: BPF Maps are key-value stores used to share data between eBPF programs and user space applications.</p>
   </details>

## eBPF and Cilium

6. **What is the main reason Cilium uses eBPF?**
   - A) Implementing networking features without kernel modules
   - B) Providing a better user interface
   - C) Using less memory
   - D) Easier installation process

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: A) Implementing networking features without kernel modules</p>
   <p><strong>Explanation</strong>: Cilium uses eBPF to implement high-performance networking, load balancing, security policies, and other features without kernel modules.</p>
   </details>

7. **Which is NOT a feature implemented using eBPF in Cilium?**
   - A) Network policy enforcement
   - B) Service load balancing
   - C) Network packet encryption
   - D) User authentication

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: D) User authentication</p>
   <p><strong>Explanation</strong>: Cilium uses eBPF to implement network policy enforcement, service load balancing, and network packet processing, but user authentication is typically handled by other systems.</p>
   </details>

8. **Which eBPF feature does Cilium use to replace kube-proxy?**
   - A) XDP (eXpress Data Path)
   - B) TC (Traffic Control) BPF
   - C) Socket BPF
   - D) Tracing BPF

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: B) TC (Traffic Control) BPF</p>
   <p><strong>Explanation</strong>: Cilium primarily uses TC (Traffic Control) BPF programs to replace kube-proxy's service load balancing functionality.</p>
   </details>

9. **Why is Cilium's eBPF-based load balancing superior to kube-proxy?**
   - A) Supports more service types
   - B) Better user interface
   - C) Lower latency and higher throughput
   - D) Easier configuration

   <details>
   <summary>Show Answer</summary>
   <p><strong>Answer</strong>: C) Lower latency and higher throughput</p>
   <p><strong>Explanation</strong>: Cilium's eBPF-based load balancing processes packets directly in kernel space, providing lower latency and higher throughput.</p>
   </details>

10. **Which is NOT a metric collected using eBPF in Cilium?**
    - A) Network connection status
    - B) Packet drop reasons
    - C) Service response time
    - D) User login time

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) User login time</p>
    <p><strong>Explanation</strong>: Cilium uses eBPF to collect network-related metrics such as network connection status, packet drop reasons, and service response time, but does not collect application-level metrics like user login time.</p>
    </details>

## eBPF Programming

11. **What language is primarily used to write eBPF programs?**
    - A) Python
    - B) Go
    - C) C
    - D) Rust

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) C</p>
    <p><strong>Explanation</strong>: eBPF programs are primarily written in C and compiled to eBPF bytecode using the LLVM compiler.</p>
    </details>

12. **Which is NOT a framework for developing eBPF programs?**
    - A) BCC (BPF Compiler Collection)
    - B) libbpf
    - C) bpftrace
    - D) libpcap

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) libpcap</p>
    <p><strong>Explanation</strong>: libpcap is a packet capture library and is not a framework for eBPF program development. BCC, libbpf, and bpftrace are all frameworks for developing eBPF programs.</p>
    </details>

13. **Which is NOT a type of eBPF map?**
    - A) Hash Map
    - B) Array Map
    - C) LRU Map
    - D) Graph Map

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: D) Graph Map</p>
    <p><strong>Explanation</strong>: eBPF supports various types of maps including hash maps, array maps, and LRU maps, but does not support graph maps.</p>
    </details>

14. **What is the maximum number of instructions in an eBPF program?**
    - A) 1,000
    - B) 4,096
    - C) 10,000
    - D) Unlimited

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) 4,096</p>
    <p><strong>Explanation</strong>: eBPF programs are limited to a maximum of 4,096 instructions. This is a limit to ensure safety.</p>
    </details>

15. **What system call is used to load eBPF programs into the kernel?**
    - A) bpf()
    - B) ebpf()
    - C) sysfs()
    - D) ioctl()

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) bpf()</p>
    <p><strong>Explanation</strong>: The bpf() system call is used to load eBPF programs into the kernel and to create and access eBPF maps.</p>
    </details>

## eBPF Performance and Monitoring

16. **What is the main benefit provided by XDP (eXpress Data Path)?**
    - A) Better security
    - B) Easier programming
    - C) Lower latency
    - D) Higher compatibility

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) Lower latency</p>
    <p><strong>Explanation</strong>: XDP processes packets at the network driver level, bypassing the kernel networking stack to provide very low latency.</p>
    </details>

17. **What tool is used to monitor the performance of eBPF programs in Cilium?**
    - A) top
    - B) bpftool
    - C) htop
    - D) iotop

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) bpftool</p>
    <p><strong>Explanation</strong>: bpftool is a tool used to inspect and manage eBPF programs and maps, and is also used for performance monitoring.</p>
    </details>

18. **What is Cilium's eBPF-based network monitoring tool?**
    - A) Prometheus
    - B) Hubble
    - C) Grafana
    - D) Jaeger

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: B) Hubble</p>
    <p><strong>Explanation</strong>: Hubble is Cilium's eBPF-based network monitoring tool that can observe and analyze network flows in real-time.</p>
    </details>

19. **What tool is used to find performance bottlenecks in eBPF programs?**
    - A) strace
    - B) ltrace
    - C) perf
    - D) gdb

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: C) perf</p>
    <p><strong>Explanation</strong>: perf is a Linux performance analysis tool used to find performance bottlenecks in eBPF programs.</p>
    </details>

20. **What command is used for debugging eBPF programs in Cilium?**
    - A) `cilium bpf`
    - B) `cilium debug`
    - C) `cilium monitor`
    - D) `cilium trace`

    <details>
    <summary>Show Answer</summary>
    <p><strong>Answer</strong>: A) `cilium bpf`</p>
    <p><strong>Explanation</strong>: The `cilium bpf` command is used to inspect and debug Cilium's eBPF programs and maps.</p>
    </details>
