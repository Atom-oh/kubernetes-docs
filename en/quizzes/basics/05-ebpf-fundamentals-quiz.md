# eBPF Fundamentals Quiz

> **Supported Versions**: Linux Kernel 4.18+, Kubernetes 1.25+
> **Last Updated**: February 2025

This quiz tests your overall understanding of eBPF (extended Berkeley Packet Filter), from basic concepts to its applications in Kubernetes environments.

## Multiple Choice Questions

1. What does the eBPF verifier NOT check?
   - A) No infinite loops
   - B) No out-of-bounds memory access
   - C) Program execution speed
   - D) No use of uninitialized variables

<details>
<summary>View Answer</summary>

**Answer: C) Program execution speed**

**Explanation:**
The eBPF verifier checks for no infinite loops (DAG structure verification), no out-of-bounds memory access, no use of uninitialized variables, correct helper function calls, and guaranteed program termination to ensure program safety. Program execution speed is not a verification item for the verifier.

</details>

2. Which XDP (eXpress Data Path) program return value sends the packet back to the same NIC?
   - A) XDP_DROP
   - B) XDP_PASS
   - C) XDP_TX
   - D) XDP_REDIRECT

<details>
<summary>View Answer</summary>

**Answer: C) XDP_TX**

**Explanation:**
XDP program return values have the following meanings:
- `XDP_DROP`: Drop packet
- `XDP_PASS`: Pass to kernel stack
- `XDP_TX`: Return packet to same NIC
- `XDP_REDIRECT`: Forward to another interface
- `XDP_ABORTED`: Error handling

XDP_TX is used when you want to send the packet back to the network interface that received it.

</details>

3. What is NOT a primary role of eBPF Maps?
   - A) Data sharing between kernel and user space
   - B) State storage
   - C) Compiling eBPF programs
   - D) Event data transmission

<details>
<summary>View Answer</summary>

**Answer: C) Compiling eBPF programs**

**Explanation:**
eBPF maps are data structures used to share data between kernel and user space and to store state. Maps are used for event data transmission (PERF_EVENT_ARRAY, RINGBUF), key-value storage (HASH), statistics collection (PERCPU_ARRAY), and more. Compiling eBPF programs is handled by Clang/LLVM and is not a role of maps.

</details>

4. What is the main advantage that eBPF provides when Cilium replaces kube-proxy?
   - A) O(n) performance proportional to the number of services
   - B) Requires iptables rule evaluation
   - C) O(1) performance through map lookup
   - D) Uses Netfilter

<details>
<summary>View Answer</summary>

**Answer: C) O(1) performance through map lookup**

**Explanation:**
Traditional kube-proxy (iptables mode) has O(n) performance degradation as the number of services increases. Cilium uses eBPF maps to provide constant O(1) lookup performance. This provides significantly improved performance in all aspects including connection establishment time, CPU usage, and connections per second.

</details>

5. What is the primary purpose of bpftrace?
   - A) Compiling eBPF programs to C
   - B) Loading kernel modules
   - C) DTrace-style high-level tracing
   - D) Building container images

<details>
<summary>View Answer</summary>

**Answer: C) DTrace-style high-level tracing**

**Explanation:**
bpftrace is a DTrace-style high-level tracing language that allows you to trace the system with simple one-liner commands. For example, you can easily perform tasks like counting system calls, tracking bytes read per process, tracing file opens, and tracking TCP connections.

</details>

6. In Tetragon's TracingPolicy, what action immediately terminates a process when malicious file access is detected?
   - A) action: Block
   - B) action: Sigkill
   - C) action: Deny
   - D) action: Terminate

<details>
<summary>View Answer</summary>

**Answer: B) action: Sigkill**

**Explanation:**
In Tetragon's TracingPolicy, `action: Sigkill` in `matchActions` immediately terminates the process with a SIGKILL signal when an event matching the policy occurs. This is used to block sensitive file access or malicious network connections in real-time.

</details>

7. What is NOT a main feature of Hubble?
   - A) Network flow observation
   - B) DNS query tracking
   - C) Compiling eBPF programs
   - D) Policy decision monitoring

<details>
<summary>View Answer</summary>

**Answer: C) Compiling eBPF programs**

**Explanation:**
Hubble is a network observability platform built into Cilium that collects and monitors network flows, DNS queries, HTTP requests, policy decisions, and more. Hubble is an observability tool and does not provide eBPF program compilation functionality.

</details>

8. What problem does CO-RE (Compile Once, Run Everywhere) solve?
   - A) Improving eBPF program execution speed
   - B) Portability across different kernel versions
   - C) Reducing memory usage
   - D) Reducing network latency

<details>
<summary>View Answer</summary>

**Answer: B) Portability across different kernel versions**

**Explanation:**
CO-RE uses libbpf and BTF (BPF Type Format) to allow eBPF programs compiled once to run on various kernel versions. This reduces kernel header dependencies and automatically handles struct relocation, eliminating the need for recompilation for each kernel version.

</details>

9. What does Falco detect using eBPF?
   - A) Network bandwidth usage
   - B) Runtime anomalous behavior
   - C) Disk capacity
   - D) CPU temperature

<details>
<summary>View Answer</summary>

**Answer: B) Runtime anomalous behavior**

**Explanation:**
Falco is a CNCF project that uses eBPF to detect runtime anomalous behavior. It detects and alerts on security threats such as reading sensitive files, executing shells in containers, and privilege escalation attempts based on rules.

</details>

10. What is the stack size limit for eBPF programs?
    - A) 128 bytes
    - B) 256 bytes
    - C) 512 bytes
    - D) 1024 bytes

<details>
<summary>View Answer</summary>

**Answer: C) 512 bytes**

**Explanation:**
eBPF programs have a 512 byte stack size limit. To work around this limit, you need to use maps like PERCPU_ARRAY to allocate larger buffers. This limit exists to ensure kernel safety.

</details>

## Short Answer Questions

11. What is the name of the compiler that converts eBPF bytecode to native machine code?

<details>
<summary>View Answer</summary>

**Answer: JIT compiler (Just-In-Time compiler)**

**Explanation:**
The JIT compiler converts eBPF bytecode to native machine code. This provides 4-5x performance improvement compared to the interpreter, and architecture-specific optimizations are applied. It can be enabled by setting `/proc/sys/net/core/bpf_jit_enable` to 1.

</details>

12. What is the name of the eBPF program type that dynamically traces kernel function calls?

<details>
<summary>View Answer</summary>

**Answer: Kprobes (or Kprobe)**

**Explanation:**
Kprobes is an eBPF program type that dynamically traces kernel function calls. Unlike Uprobes which trace user space functions, Kprobes traces functions within the kernel. For example, you can trace the `tcp_connect` function to collect TCP connection information.

</details>

13. What is the name of the network observability platform built into Cilium?

<details>
<summary>View Answer</summary>

**Answer: Hubble**

**Explanation:**
Hubble is a network observability platform built into Cilium that collects data from the eBPF dataplane including network flows, DNS queries, HTTP requests, and policy decisions. You can observe the cluster's network traffic in real-time through Hubble CLI, Hubble UI, and Hubble Relay.

</details>

14. What Linux capability is required to load eBPF programs? (kernel 5.8 and above)

<details>
<summary>View Answer</summary>

**Answer: CAP_BPF**

**Explanation:**
On kernel 5.8 and above, the `CAP_BPF` capability is required to load eBPF programs. In earlier versions, `CAP_SYS_ADMIN` was required. Additionally, `CAP_PERFMON` is needed for attaching to performance monitoring events, and `CAP_NET_ADMIN` is needed for attaching XDP/TC programs.

</details>

15. What is the name of the CNCF project that monitors container energy consumption using eBPF?

<details>
<summary>View Answer</summary>

**Answer: Kepler (Kubernetes-based Efficient Power Level Exporter)**

**Explanation:**
Kepler is a project that uses eBPF to monitor container energy consumption. It provides metrics in Prometheus format such as `kepler_container_joules_total` (energy consumption per container) and `kepler_container_gpu_joules_total` (GPU energy consumption).

</details>

## Hands-on Questions

16. Write the commands to use bpftool to list the eBPF programs currently loaded on the system and query detailed information about a specific program.

<details>
<summary>View Answer</summary>

**Answer:**
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

**Explanation:**
`bpftool prog list` displays a list of all currently loaded eBPF programs. You can check each program's ID, type, name, attachment location, etc. Use `bpftool prog show id <ID>` to query detailed information about a specific program, and `dump xlated` and `dump jited` to view the bytecode and JIT-compiled native code.

</details>

17. Write a bpftrace one-liner command to trace TCP connections occurring from all processes on the system in real-time.

<details>
<summary>View Answer</summary>

**Answer:**
```bash
# TCP connection tracing (Method 1: using kprobe)
sudo bpftrace -e 'kprobe:tcp_connect { printf("%s (PID: %d) connecting...\n", comm, pid); }'

# TCP connection tracing (Method 2: using tracepoint, more detailed info)
sudo bpftrace -e 'tracepoint:tcp:tcp_connect { printf("%s -> %s:%d\n", ntop(args->saddr), ntop(args->daddr), args->dport); }'

# Count TCP connections by process
sudo bpftrace -e 'kprobe:tcp_connect { @[comm] = count(); }'
```

**Explanation:**
bpftrace is a DTrace-style high-level tracing language that allows you to trace the system with simple one-liners. `kprobe:tcp_connect` triggers when the kernel's `tcp_connect` function is called. `comm` represents the process name and `pid` represents the process ID. Using tracepoints allows you to also obtain source/destination IP addresses and port information.

</details>

18. Write the command to use Hubble CLI to observe only dropped packets from a specific namespace.

<details>
<summary>View Answer</summary>

**Answer:**
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

**Explanation:**
Hubble is a network observability tool built into Cilium. The `--namespace` option filters by a specific namespace, and `--verdict DROPPED` filters for only dropped packets. The `-f` option provides real-time streaming, and `-o json` provides JSON format output. Analyzing dropped packets helps diagnose network policy issues or configuration errors.

</details>

## Advanced Questions

19. Explain the three main advantages that eBPF has over kernel modules, and describe specifically what benefits each provides in Kubernetes environments.

<details>
<summary>View Answer</summary>

**Answer:**

Main advantages of eBPF over kernel modules and their benefits in Kubernetes environments:

**1. Safety (Safety guaranteed through verifier)**
- **Advantage**: The eBPF verifier checks for infinite loops, memory access violations, uninitialized variables, etc. before loading the program to prevent kernel crashes.
- **Kubernetes benefit**: CNI plugins (Cilium) and security tools (Tetragon, Falco) can run safely in production clusters. Unlike kernel modules, even if there are bugs, the entire system won't crash, maintaining high availability.

**2. Portability (Kernel version independence through CO-RE)**
- **Advantage**: Using CO-RE (Compile Once, Run Everywhere) and BTF, eBPF programs compiled once can run on various kernel versions. No recompilation is needed for each kernel version.
- **Kubernetes benefit**: The same networking and security solutions can be deployed across heterogeneous node environments (nodes with different kernel versions). Compatibility issues are greatly reduced during cluster upgrades or node additions.

**3. Dynamic loading (Program load/unload without reboot)**
- **Advantage**: eBPF programs can be dynamically loaded and unloaded without system reboot. Functionality can be added or changed at runtime.
- **Kubernetes benefit**: Network policies, security rules, and observability settings can be applied immediately without node restarts. Changes to Cilium NetworkPolicy or Tetragon TracingPolicy are reflected in real-time, enabling security enhancements without operational interruption.

**Additional advantages:**
- **Performance**: JIT compilation provides native code-level performance, enabling O(1) service lookup when replacing kube-proxy.
- **Development difficulty**: Relatively easier than kernel module development, enabling rapid feature development and deployment.

</details>

20. Design an approach to detect and block sensitive file access within containers using an eBPF-based security solution (Tetragon or Falco) in a Kubernetes cluster. Include TracingPolicy or Falco rule examples in your explanation.

<details>
<summary>View Answer</summary>

**Answer:**

**eBPF-based Sensitive File Access Security Design**

**1. Security Requirements Definition**
- Detection targets: `/etc/shadow`, `/etc/passwd`, `/etc/sudoers`, `/var/run/secrets/` (Kubernetes secrets)
- Response approach: Alert on detection, process termination for severe cases

**2. Tetragon TracingPolicy Implementation**

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

**3. Falco Rules Implementation**

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

**4. Deployment and Monitoring**

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

**5. Architecture Explanation**

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

This design leverages eBPF's kernel-level visibility to detect and respond to sensitive file access in real-time without modifying applications.

</details>

---

[Return to Learning Materials](../../basics/05-ebpf-fundamentals.md) | [Next Quiz: Container Technology](./03-container-technology-quiz.md)