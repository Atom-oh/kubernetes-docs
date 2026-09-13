# EKS Node Kernel Tuning

> **Supported Versions**: Amazon Linux 2023 (kernel 6.1 / 6.12 / 6.18), Kubernetes 1.33+ (Amazon EKS)
> **Last Updated**: September 13, 2026

## What This Document Covers

- What to change and what to leave at defaults on EKS nodes — and how to decide
- The actual paths for applying kernel parameters on EKS, and the pitfall in each
- What the AL2023 kernel transition (6.1 → 6.18) means operationally

## First: Leave Most of It Alone

This is the most important advice in this document.

Kernel defaults are chosen to **behave reasonably across a wide range of workloads**, and many are auto-tuned by the kernel under load (TCP buffer auto-tuning, for example). Unfounded tuning costs you in three ways.

| Problem | Example |
|---|---|
| **Unreproducible configuration** | Values differ per node, so incidents cannot be reproduced |
| **Breakage on kernel upgrade** | A tunable valid on 6.1 is renamed, moved, or gone on 6.18 |
| **Defeating auto-tuning** | Explicit per-socket SO_RCVBUF/SO_SNDBUF disables that socket’s automatic sizing; sysctl bounds are a different control |

**The precondition for tuning is measurement.** Follow this order.

1. Identify the symptom (latency? drops? throughput?)
2. **Look at drop counters first** — `insert_failed` in `conntrack -S`, `dropped` in `tc -s qdisc`, NIC drops in `ethtool -S`
3. Only touch parameters at the point where that counter is rising
4. Measure before and after under identical conditions
5. Record the change and its rationale as code (see application paths below)

For measurement method, see the fixtures in the [Pod Network Benchmark](../networking/06-pod-network-benchmark.md).

## Application Paths — How to Change Kernel Parameters on EKS

There are several ways, and **each has a different scope and pitfall.** Getting this straight matters more in practice.

| Path | Scope | Persistence | Notes |
|---|---|---|---|
| **Node bootstrap** (User Data / `nodeadm`) | Whole node | Reapplied on node replacement | AL2023 uses `nodeadm` config. The most standard |
| **Bottlerocket settings** (`settings.kernel.sysctl`) | Whole node | Managed as node settings | Bottlerocket is immutable, so this is the only path |
| **Pod `securityContext.sysctls`** | **Only the Pod's net namespace** | Pod spec | **Namespaced sysctls only.** Many `net.*` qualify |
| **Privileged init DaemonSet** | Whole node | Reapplied on Pod restart | Commonly used but requires privileged — a security-review item |
| **`kube-proxy-config` ConfigMap** | conntrack-related | Managed by kube-proxy | **On EKS this takes precedence over CLI arguments** |
| **Karpenter `EC2NodeClass`** | Node group | At node provisioning | Manages User Data declaratively |

### Two easily missed points

**First, the distinction between namespaced and non-namespaced sysctls.** Many `net.*` values are settable per net namespace, so Pod `securityContext.sysctls` can change them. By contrast `vm.*`, `fs.*`, and **some values like `net.netfilter.nf_conntrack_max` are node-global** and cannot be changed from a Pod spec.

Also, kubelet rejects "unsafe" sysctls by default. If you need one, allow it explicitly with `--allowed-unsafe-sysctls`, which is a node setting.

**Second, kube-proxy overwrites conntrack.** This was mentioned in [Container Kernel Features](./01-container-primitives.md), but it is the pitfall most frequently hit in practice so it bears repeating — EKS ships a `kube-proxy-config` ConfigMap by default and **it takes precedence over command-line arguments.** Raising the sysctl at bootstrap can be reverted by kube-proxy.

::: warning Needs verification
On Bottlerocket, raising the conntrack ceiling via `settings.kernel.sysctl` does not take effect ([bottlerocket-os/bottlerocket#4221](https://github.com/bottlerocket-os/bottlerocket/issues/4221), filed September 2024). The cause is that **the kube-proxy config file (`/var/lib/kube-proxy-config/config`) takes precedence over command-line arguments.**

When using a kube-proxy configuration file, change its **`conntrack.maxPerCore`/`conntrack.min` fields** if intentionally delegating limit management to node sysctl. Setting both to 0 is not a reason to rely on CLI flags ignored by `--config`. Confirm managed add-on reconciliation and memory headroom before rollout.

**Whether this was resolved in a specific Bottlerocket release could not be confirmed.** Whichever path you use, verify the actual value on the node after applying.

```bash
# Check the actually applied values on the node
cat /proc/sys/net/netfilter/nf_conntrack_max
cat /proc/sys/net/netfilter/nf_conntrack_count
conntrack -S | head
```
:::

## Kernel Version — AL2023's 6.1 → 6.18 Transition

This is the change to know about right now.

| Date | What |
|---|---|
| March 2023 | AL2023 released with kernel **6.1** |
| April 2025 | Kernel **6.12** support added |
| **August 17, 2026** | **The default kernel for `al2023-ami-kernel-default` AMIs changed from 6.1 to 6.18** |

**Two implications follow.**

The default-kernel **AMI family** changed, but replacement uses the AMI selected by your launch template or provisioning policy. A pinned AMI ID does not change its kernel merely because a new node starts. A refreshed latest/default AMI lookup can select a new kernel; EKS-optimized AMIs have their own release selection.

If you must pin a kernel, use **version-specific AMIs** (`al2023-ami-kernel-6.1-*`, etc.) explicitly.

**What to check when the kernel changes:**

| Item | Why |
|---|---|
| Existence and location of tunables | Names change or move from sysctl to debugfs between versions |
| Components depending on kernel modules | eBPF programs, specific CNI features, GPU drivers, custom modules |
| Scheduler behavior | 6.6+ EEVDF (below) — may be noticeable for latency-sensitive workloads |
| Performance regressions | Re-measure benchmarks per kernel version |

**Recommendation**: treat a kernel transition **with the same weight as a Kubernetes version upgrade.** Validate on the same kernel in staging, re-measure your performance baseline, then roll to production.

## CPU — Scheduler and Throttling

### EEVDF — what changed in 6.6

In Linux 6.6, CFS's task-selection logic was replaced by **EEVDF** (Earliest Eligible Virtual Deadline First).

The point worth understanding precisely is **what changed and what did not.**

| Changed | Unchanged |
|---|---|
| **How the next task is picked** (virtual-deadline based) | vruntime machinery, weight calculation |
| Preemption decision for a woken task — **deadline comparison** instead of a heuristic (`sched_wakeup_granularity_ns`) | Group scheduling (cgroup cpu.weight), load balancing |

So it is accurate to see this as **an evolution that replaced the selection logic, not a wholesale replacement of CFS.** The change is within `fair_sched_class`.

Operationally: **wake-up latency characteristics for latency-sensitive workloads may change.** Usually for the better, but if p99 shifts when moving from kernel 6.1 to 6.18, this is one candidate.

### Where the tunables actually live

Confirmed from kernel source (`kernel/sched/debug.c`):

| Item | Status |
|---|---|
| `sched_latency_ns` | **Removed** — no references remain in `kernel/sched/fair.c` |
| `sched_wakeup_granularity_ns` | **Removed** — same |
| **`/sys/kernel/debug/sched/base_slice_ns`** | **The current equivalent.** The internal variable is `sysctl_sched_base_slice`, exposed in debugfs as `base_slice_ns` |

So the CFS-era latency and preemption heuristic tunables are gone, consolidated into **a single base timeslice (`base_slice_ns`)**. Note there is no `sched_` prefix in the name — the path is `/sys/kernel/debug/sched/base_slice_ns`.

Separately, EEVDF lets a task **request its own timeslice** via the `sched_setattr()` syscall. For latency-sensitive applications that path is more appropriate than touching a global tunable.

**Scheduler tunables are still not a recommended tuning target.** debugfs is a kernel debug interface and may not be mounted in production, and in most cases adjusting the application's thread count or cgroup limits is a better answer.

### CPU limits — when throttling is the real problem

As covered in [Container Kernel Features](./01-container-primitives.md), a CPU limit is a bandwidth limit, so it creates latency even at low utilization.

**Diagnosis:**

```bash
# cgroup v2 — from the container's cgroup path
cat cpu.stat
# nr_periods, nr_throttled, throttled_usec
```

If `nr_throttled / nr_periods` is a meaningful fraction, the limit is the cause.

**Priority of responses** (see [Resource Optimization](../ops/10-resource-optimization.md) for design):

1. **Align the CPU count the application perceives with the limit.** This is the most frequently missed root cause — if the runtime inside the container sees all node cores and spawns that many threads, it burns the quota instantly. Set JVM `-XX:ActiveProcessorCount`, Go `GOMAXPROCS`, Node.js `UV_THREADPOOL_SIZE`, etc., to match the limit
2. **Raise the limit** — trading off node stability
3. **For extreme latency sensitivity, consider removing the limit** — but manage noisy-neighbor risk with requests and node separation
4. Check actual stall time with `cpu.pressure` PSI

**CPU Manager's static policy** (dedicated cores) is a separate, valid mechanism for latency-sensitive workloads. It lowers node utilization, so it needs justification.

## Memory — OOM and Pressure

### What to adjust and what to leave

| Parameter | Recommendation |
|---|---|
| `vm.swappiness` | Kubernetes traditionally assumes swap is off. Swap support has matured, but **confirm support status before enabling on EKS** |
| `vm.overcommit_memory` | **Keep the default.** Changing it makes container allocation failure modes hard to predict |
| `vm.min_free_kbytes` | Reclaim headroom. Too low risks OOM on sharp allocations. **Consider only for large-memory nodes with heavy bursts** |
| `vm.max_map_count` | **A genuinely needed adjustment for Elasticsearch/OpenSearch** and similar — the default is low and hits the mmap limit |
| `kernel.pid_max` | When PIDs are exhausted on high-density nodes |

`vm.max_map_count` comes up often as a real case — OpenSearch-family software mmaps many files and fails to start at the default. It is a good example of "justified tuning": a clear symptom, the parameter is the direct cause, and the vendor documents a value.

### kubelet reservations — before kernel parameters

More impactful for node stability than kernel tuning is **kubelet's resource reservation.**

| Setting | Purpose |
|---|---|
| `--system-reserved` | Reserved for the OS and system daemons |
| `--kube-reserved` | Reserved for kubelet and the container runtime |
| `--eviction-hard` | Evict Pods on reaching this threshold |

With insufficient reservation, Pods consume all node memory and **the kernel or kubelet itself hits OOM.** The node goes `NotReady` and every Pod on it is affected — a far worse outcome than an individual Pod OOM.

**Eviction is better than OOM.** Eviction is Kubernetes moving a Pod in a controlled way; the OOM killer is the kernel abruptly killing a process. The goal is to set `--eviction-hard` so Kubernetes intervenes before a kernel OOM.

### Observing pressure with PSI

cgroup v2's PSI gives a better signal than usage.

```bash
# Whole node
cat /proc/pressure/memory
cat /proc/pressure/cpu
cat /proc/pressure/io

# A specific cgroup
: "${KERNEL_CGROUP_PATH:?Set the inspected cgroup directory}"
cat "$KERNEL_CGROUP_PATH/memory.pressure"
```

`some avg10` is the fraction of the last 10 seconds in which **at least one task was stalled on that resource.** A calm usage graph with this value climbing means time is going into reclaim or contention.

## Network — Justified Adjustments

### conntrack

As covered, **the item that most often causes real incidents.**

| Item | Content |
|---|---|
| Symptom | New connections silently dropped. The application only sees timeouts/refusals |
| Direct evidence | Rising **`insert_failed`** in `conntrack -S` |
| Secondary signals | `nf_conntrack: table full` in `dmesg`, `nf_conntrack_count` / `nf_conntrack_max` ratio |
| Adjustment path | **`conntrack.maxPerCore` / `conntrack.min` in the `kube-proxy-config` ConfigMap** (takes precedence on EKS) |
| Cost | Node memory per entry. Cannot be raised without bound |
| Root fix | Reduce connection churn; investigate dataplane/map pressure. Headless DNS alone does not disable tracking |

**Why `maxPerCore` is used** is worth knowing. Being per-core rather than absolute, the same setting scales proportionally across node sizes. Pinning an absolute value (`nf_conntrack_max`) over-provisions small nodes and under-provisions large ones.

Timeouts are also adjustable — reducing `nf_conntrack_tcp_timeout_established` (whose default is very long) reclaims entries sooner. Take care not to break legitimately long-lived connections.

### Socket buffers and queues

| Parameter | When |
|---|---|
| `net.core.somaxconn` | **On accept-queue overflow.** A common adjustment on servers taking connection bursts |
| `net.ipv4.tcp_max_syn_backlog` | On SYN bursts |
| `net.core.netdev_max_backlog` | **When receive softirq cannot keep up** |
| `net.ipv4.tcp_rmem` / `tcp_wmem` | Bounds/defaults for TCP sizing; changing these does not by itself disable autotuning. Adjust only from measured BDP/memory evidence |
| `net.ipv4.ip_local_port_range` | **On source port exhaustion.** Happens in practice on egress-heavy nodes |
| `net.ipv4.tcp_tw_reuse` | On TIME_WAIT accumulation. Apply understanding the behavior |

**`somaxconn` and `ip_local_port_range` are the representative cases of justified adjustment.** The former has an evidence counter (`TcpExtListenOverflows` in `nstat`), and the latter shows up directly as connection failures.

Retain sensible `tcp_rmem`/`tcp_wmem` bounds unless measurements justify changes. Linux documents that explicit **SO_RCVBUF/SO_SNDBUF socket settings** disable the corresponding per-socket autotuning; do not confuse that with setting sysctl min/default/max values.

### qdisc

If in-node drops are confirmed (`dropped` in `tc -s qdisc`), this is the target.

- **`fq_codel`**: bufferbloat mitigation — when latency is the problem
- **`fq`**: pacing — when using bbr
- Increasing queue length (`txqueuelen`) reduces drops but **increases latency.** Decide knowing the trade-off

### Interrupt distribution

If `/proc/interrupts` shows skew to one core and `mpstat -P ALL` shows `%soft` spiking there, look at RSS/RPS/RFS. That said, **current ENA drivers and instance types default to multi-queue with RSS**, so this rarely becomes a problem.

### kube-proxy mode

Not a node kernel parameter, but the biggest influence on dataplane performance.

| Situation | Recommendation |
|---|---|
| Many Services, iptables mode | **Consider nftables mode** — GA in 1.33, O(1) lookup plus incremental updates. Needs kernel 5.13+ (AL2023 satisfies it) |
| **Running IPVS mode** | **Migration plan needed** — deprecated in 1.35, removal targeted 1.38. Recommended replacement is nftables |
| Keeping the default | Even with nftables GA, **the default is still iptables** — switching is an explicit decision |

## Storage

| Parameter | Content |
|---|---|
| **I/O scheduler** | `none` (or `mq-deadline`) is typical for NVMe. Complex schedulers add little on NVMe |
| `vm.dirty_ratio` / `dirty_background_ratio` | Write buffering volume. Affects latency behavior under write bursts |
| **ephemeral storage** | More than kernel parameters, **overlayfs copy-up cost** is the real issue — move write-heavy paths to volumes ([Container Kernel Features](./01-container-primitives.md)) |
| **EBS performance** | Not a kernel matter but volume type, IOPS, and throughput settings ([EBS gp2 vs gp3 Benchmark](../storage/01-ebs-gp2-gp3-benchmark.md)) |

## By Workload

A table that starts from symptoms.

| Workload | Commonly needed adjustments | Evidence counters |
|---|---|---|
| **High-connection gateways/proxies** | conntrack ceiling, `somaxconn`, `ip_local_port_range` | `insert_failed`, `TcpExtListenOverflows`, port exhaustion |
| **Latency-sensitive (trading, real-time)** | Revisit CPU limits, CPU Manager static policy, `fq_codel` | `cpu.stat` throttling, `cpu.pressure` |
| **High-throughput (batch, data)** | Buffer ceilings (long-distance only), `netdev_max_backlog` | qdisc `dropped`, softirq skew |
| **Search/indexing (OpenSearch, etc.)** | **`vm.max_map_count`**, file descriptor limits | Startup failure logs |
| **High-density nodes** | `kernel.pid_max`, kubelet reservations, eviction thresholds | PID exhaustion, node `NotReady` |
| **Blockchain nodes** | File descriptors, disk IOPS, socket buffers | [Blockchain Node Operations](../blockchain/02-nodes-on-eks.md) |

## How to Manage Changes

More important long-term than the tuning itself is **how you manage it.**

| Principle | Why |
|---|---|
| **Manage as code** (Karpenter `EC2NodeClass`, launch templates, Bottlerocket settings) | Prevents values differing per node |
| **Record the rationale in comments** | If nobody knows "why this value" six months later, nobody can revert it |
| **Separate node groups** | Different workload characters need different tuning. Do not force one profile on everything |
| **Pin the kernel or plan the transition** | `kernel-default` AMIs change kernel silently |
| **Verify actual values after applying** | Especially conntrack — another party may overwrite it |
| **Measure before and after under identical conditions** | Tuning without measurement becomes superstition |

## Summary

- **Leave most of it at defaults.** The kernel is auto-tuning under load, and unfounded tuning creates unreproducible configurations and breakage on kernel upgrades.
- The precondition for tuning is measurement. **Start with drop counters** — `insert_failed`, qdisc `dropped`, NIC drops.
- Verify the selected AMI and running kernel. Default AMI families may advance; pinned AMI IDs do not change automatically on replacement.
- The root cause of CPU throttling is usually **a mismatch between the CPU count the application perceives and its quota.** Start with `GOMAXPROCS`/`ActiveProcessorCount`.
- For node stability, **kubelet reservations and eviction thresholds** beat kernel tuning. Eviction is better than a kernel OOM.
- The representative justified adjustments are **conntrack ceiling, `somaxconn`, `ip_local_port_range`, and `vm.max_map_count`** — all have direct evidence counters.
- TCP sysctl bounds and per-socket autotuning overrides are different; tune only with measured evidence.
- **If you run IPVS mode, you need a migration plan** (deprecated in 1.35, removal targeted 1.38).

## References

- [Amazon Linux 2023 — Updating the Linux Kernel](https://docs.aws.amazon.com/linux/al2023/ug/kernel-update.html)
- [Amazon EKS-Optimized Amazon Linux 2023 AMIs](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
- [Increase nf_conntrack_max limit on EKS nodes](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [Running kube-proxy in nftables Mode — EKS Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [KEP-5495: Deprecate IPVS mode in kube-proxy](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [EEVDF Scheduler — Linux kernel documentation](https://docs.kernel.org/scheduler/sched-eevdf.html)
- [kernel/sched/debug.c — debugfs tunable definitions](https://github.com/torvalds/linux/blob/master/kernel/sched/debug.c)
- [bottlerocket-os/bottlerocket#4221 — conntrack limit not applied](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [Reserve Compute Resources for System Daemons (Kubernetes)](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)
- [Using sysctls in a Kubernetes Cluster](https://kubernetes.io/docs/tasks/administer-cluster/sysctl-cluster/)
- [Resource Optimization](../ops/10-resource-optimization.md) / [Pod Network Benchmark](../networking/06-pod-network-benchmark.md)
