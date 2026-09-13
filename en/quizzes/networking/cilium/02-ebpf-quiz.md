# Cilium eBPF Quiz

> **Review baseline**: Cilium 1.20.1; Linux 5.10+ or documented equivalent backports; limit examples use Linux 6.12.
> **2026-09-12**


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

2. **Where do the Linux eBPF programs in this guide execute when their hooks run?**
   - A) User space only
   - B) In the kernel
   - C) In Hubble Relay
   - D) In the container runtime process

   <details>
   <summary>Show Answer</summary>

   **Answer: B) In the kernel**

   These programs execute in the kernel through its supported interpreter or JIT path. Loaders and observers run in userspace. Kernel execution is not an absolute safety guarantee.

   </details>

3. **What does acceptance by the BPF verifier mean?**
   - A) Kernel crashes are impossible
   - B) The intended application policy has been proven correct
   - C) The program passed checks for its type, memory access and execution constraints
   - D) No further testing is needed

   <details>
   <summary>Show Answer</summary>

   **Answer: C) The program passed checks for its type, memory access and execution constraints**

   The verifier constrains execution; verifier, JIT, helper and kernel bugs or incorrect program logic remain possible.

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

5. **What mechanism shares state or events between BPF programs and userspace?**
   - A) Environment variables
   - B) Only ordinary disk files
   - C) BPF maps
   - D) Kubernetes annotations

   <details>
   <summary>Show Answer</summary>

   **Answer: C) BPF maps**

   Maps include key/value structures, event buffers and reference containers. Pins retain references, not map contents across reboot; reloading does not automatically reuse a map.

   </details>

## eBPF and Cilium

6. **Why can eBPF help implement Cilium's datapath?**
   - A) Programmable kernel hooks and maps avoid a new custom module for every datapath change
   - B) It removes every kernel-module dependency
   - C) It automatically configures any cloud network
   - D) It guarantees lower memory usage

   <details>
   <summary>Show Answer</summary>

   **Answer: A) Programmable kernel hooks and maps avoid a new custom module for every datapath change**

   Cilium uses supported kernel facilities for forwarding, policy and service translation. Required kernel features and workload-specific testing remain necessary.

   </details>

7. **Which statement correctly describes Cilium's WireGuard/IPsec encryption modes?**
   - A) Every cryptographic operation is a BPF instruction
   - B) No configuration or key operation is needed
   - C) Every traffic path is always encrypted
   - D) BPF integrates traffic with kernel WireGuard/IPsec facilities; coverage and key management depend on mode

   <details>
   <summary>Show Answer</summary>

   **Answer: D) BPF integrates traffic with kernel WireGuard/IPsec facilities; coverage and key management depend on mode**

   BPF steering and kernel encryption are different responsibilities. Node encryption does not automatically enable workload mTLS.

   </details>

8. **Which hooks can Cilium use for kube-proxy replacement?**
   - A) Only XDP
   - B) Only TC
   - C) Only tracing probes
   - D) Socket hooks, TC packet paths and optional XDP acceleration

   <details>
   <summary>Show Answer</summary>

   **Answer: D) Socket hooks, TC packet paths and optional XDP acceleration**

   The path depends on traffic and configuration. Service translation can happen before packets exist at socket hooks, in packet paths or through supported XDP acceleration.

   </details>

9. **How should a claim that a Cilium configuration is faster be evaluated?**
   - A) Assume all BPF map lookups have guaranteed latency
   - B) Measure the workload with protocol, routing, policy, encryption and proxy settings recorded
   - C) Treat kernel execution alone as proof
   - D) Compare only product names

   <details>
   <summary>Show Answer</summary>

   **Answer: B) Measure the workload with protocol, routing, policy, encryption and proxy settings recorded**

   Kernel and userspace components have workload-dependent costs. Synthetic results and hook choice do not guarantee application latency.

   </details>

10. **Where can Hubble's HTTP observations come from?**
    - A) Automatically decrypted arbitrary traffic
    - B) Only CPU hardware counters
    - C) A supported L7 proxy path combined with network-flow information
    - D) Every packet regardless of settings

    <details>
    <summary>Show Answer</summary>

    **Answer: C) A supported L7 proxy path combined with network-flow information**

    L7 visibility depends on proxy/policy/visibility settings. Flow records are not automatically application spans or arbitrary business metrics.

    </details>

## eBPF Programming

11. **Which compiler/toolchain statement is correct?**
    - A) Clang directly compiles both C and Rust source
    - B) C commonly uses Clang's BPF backend; Rust uses its own toolchain ecosystem
    - C) A host C syntax check proves kernel verifier acceptance
    - D) BTF supplies missing kernel features

    <details>
    <summary>Show Answer</summary>

    **Answer: B) C commonly uses Clang's BPF backend; Rust uses its own toolchain ecosystem**

    Host syntax, BPF-target compilation, kernel verification and live behavior are separate checks. CO-RE does not create missing helpers or configuration.

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

14. **Which statement matches the Linux 6.12 limits discussed in the guide?**
    - A) All programs have a 4,096-instruction limit
    - B) Every program below one million instructions is accepted
    - C) There are no program or analysis limits
    - D) The BPF-capable load path allows up to one million instructions, the unprivileged path 4,096, and verifier complexity is a separate limit

    <details>
    <summary>Show Answer</summary>

    **Answer: D) The BPF-capable load path allows up to one million instructions, the unprivileged path 4,096, and verifier complexity is a separate limit**

    Program length and verifier exploration are different constraints. Capability/token, program-type and other checks can reject loading; unprivileged BPF is often disabled.

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

16. **What distinguishes native driver XDP from later skb-based processing?**
    - A) It always bypasses every kernel subsystem
    - B) It guarantees a fixed packet rate
    - C) It can process a packet before skb allocation
    - D) It works identically on every NIC and in generic mode

    <details>
    <summary>Show Answer</summary>

    **Answer: C) It can process a packet before skb allocation**

    Native XDP runs early in receive processing. Generic/offloaded modes and driver support differ; actual performance needs measurement.

    </details>

17. **Which bpftool command has the stated meaning?**
    - A) bpftool -p map dump measures lookup latency
    - B) bpftool prog profile id ID duration 10 cycles instructions requests profiling metrics
    - C) bpftool prog load always attaches tracepoints
    - D) bpftool prog show enables missing kernel features

    <details>
    <summary>Show Answer</summary>

    **Answer: B) bpftool prog profile id ID duration 10 cycles instructions requests profiling metrics**

    Profiling requires metric names, permissions and kernel/PMU support. Pretty printing, loading and attachment are different operations.

    </details>

18. **What is Hubble in this context?**
    - A) A kernel compiler
    - B) A replacement for every application tracing SDK
    - C) Cilium network observability using datapath and available proxy events
    - D) An automatic policy synchronizer

    <details>
    <summary>Show Answer</summary>

    **Answer: C) Cilium network observability using datapath and available proxy events**

    Hubble observes flows and supported L7 events. Collection limits and filters affect the result; JSON alone is not a service-map visualization.

    </details>

19. **What does the map-based lab count?**
    - A) All execve attempts by unique executable path, without loss
    - B) Successful execution events by short comm name, subject to capacity and measurement limits
    - C) Only Pods in the default namespace
    - D) All processes across every previous reboot

    <details>
    <summary>Show Answer</summary>

    **Answer: B) Successful execution events by short comm name, subject to capacity and measurement limits**

    sched_process_exec observes successful execution transitions. Names can collide; this host-wide example has bounded in-memory state and selected loss counters.

    </details>

20. **Which agent-local command inspects service backend map entries?**
    - A) cilium-dbg bpf lb list --backends
    - B) cilium debug --all-kernels
    - C) cilium policy trace --enable
    - D) hubble compile bpf

    <details>
    <summary>Show Answer</summary>

    **Answer: A) cilium-dbg bpf lb list --backends**

    Use cilium-dbg in the agent for the correct node. cilium-dbg map get displays userspace-cached content; use the appropriate decoder without modifying raw maps.

    </details>

[Review the guide](../../../networking/cilium/02-ebpf.md).
