# Kernel Features Behind Containers

> **Supported Versions**: Linux 6.1 / 6.12 / 6.18 (Amazon Linux 2023), Kubernetes 1.25+ (cgroup v2)
> **Last Updated**: September 13, 2026

## What This Document Covers

- Which kernel features combine to make a container — and the fact that there is no "container" kernel object
- What actually changed operationally in the cgroup v1 → v2 move (especially OOM diagnosis)
- Where netfilter and conntrack sit in Kubernetes networking

## First: There Is No "Container" in the Kernel

This is the starting point for understanding containers. There is no `struct container`, and no single syscall that creates one.

A container is **a convention built by combining several independent kernel features**. When a runtime (containerd, runc) starts a process, it applies these together.

| Purpose | Kernel feature |
|---|---|
| **What can it see** (isolation) | namespaces |
| **How much can it use** (limits) | cgroups |
| **What can it do** (privileges) | capabilities, seccomp, LSM (AppArmor/SELinux) |
| **How is the filesystem composed** | overlayfs (union mount) |
| **How does traffic flow** | veth, bridge/route, netfilter |

Two practical conclusions follow from it being a combination.

**First, isolation is not all-or-nothing.** Some namespaces can be shared while others are isolated. A Kubernetes Pod is exactly that — containers in the same Pod **share** the network and IPC namespaces while mount and PID namespaces are usually **separate**. That is why containers in a Pod can reach each other over `localhost` (shared network) but cannot see each other's filesystems (separate mounts).

**Second, isolation you forget becomes a silent hole.** The kernel does not know "make a container," so if the runtime does not apply a seccomp profile, the workload simply runs without one. This is why container security is a matter of runtime and policy configuration.

## Namespaces — What Can It See

A namespace **separates the "name space" of a kernel resource**, so the same name or number refers to different things in different namespaces.

| Namespace | Isolates | In a Pod |
|---|---|---|
| **mnt** | Mount points | Per container |
| **pid** | Process IDs | Per container (`shareProcessNamespace: true` shares within the Pod) |
| **net** | Interfaces, routing tables, netfilter rules, sockets, ports | **Shared per Pod** |
| **ipc** | System V IPC, POSIX message queues | Shared per Pod |
| **uts** | hostname, domainname | Shared per Pod |
| **user** | UID/GID mapping | Not used by default (see below) |
| **cgroup** | cgroup root path | Per container |
| **time** | Boot time, monotonic clock (5.6+) | Not used |

### Why the net namespace is the Pod boundary

A Pod's identity is decided here. Kubernetes creates one net namespace per Pod (held by the pause container) and puts **all of that Pod's containers into the same net namespace**.

What follows:

- Containers in a Pod share **the same IP and the same port space** → two containers in one Pod cannot both bind 8080
- `localhost` communication works → the foundation of the sidecar pattern
- **netfilter rules are also per net namespace** → this is why a sidecar mesh's init container can install iptables rules inside the Pod's net namespace, and why those rules do not affect the whole node (see [VPC Lattice Kernel Datapath](../service-mesh/vpc-lattice/07-kernel-datapath.md))
- Routing tables are separate too → `ip route` inside a Pod is not the node's

### user namespaces — why they were not the default for so long

A user namespace **maps** root (UID 0) inside the container to an unprivileged UID on the host. Even if a container escapes, it holds only ordinary user privileges on the host — attractive for security.

Yet it was not the default for a long time. The reason is **file ownership.** Files on a volume are recorded with host UIDs; if the container sees a different UID, permissions do not line up. Solving it requires translating UIDs at mount time (idmapped mounts, kernel 5.12+), and storage drivers and CSI must support it too.

### Kubernetes user namespace support status

Per [KEP-127](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/kep.yaml), the maturity stages are:

| Stage | Version |
|---|---|
| alpha | v1.25 |
| beta | v1.35 |
| **stable (GA)** | **v1.36** |

The feature gate is `UserNamespacesSupport`, applying to kubelet and kube-apiserver. **From 1.36 it is GA, so `hostUsers: false` works without enabling a feature gate.**

::: warning Needs verification
Those maturity stages are upstream Kubernetes. **Whether EKS offers that version, and whether your container runtime and CSI drivers support idmapped mounts, are separate questions.** Confirm the EKS supported version and your runtime/storage combination before adopting.
:::

## cgroups — How Much Can It Use

cgroups (control groups) **measure and limit resource use for a group of processes.** This is where Kubernetes `requests`/`limits` ultimately land.

### Structural differences between v1 and v2

| Item | cgroup v1 | cgroup v2 |
|---|---|---|
| **Hierarchy** | A **separate tree per controller** (cpu, memory, blkio…) | **A single unified tree** |
| **Process membership** | Can be in different groups per controller | Belongs to exactly one group |
| **Memory + IO cooperation** | Hard (separate trees cannot coordinate) | Possible (same tree) |
| **Pressure information** | None | **PSI** (`cpu.pressure`, `memory.pressure`, `io.pressure`) |
| **CPU limit representation** | `cpu.cfs_quota_us` / `cpu.cfs_period_us` | `cpu.max` (one file: "quota period") |
| **Memory limit representation** | `memory.limit_in_bytes` | `memory.max`, plus `memory.high` (soft pressure) |
| **AL2023 EKS AMI** | — | **Default** |

Where v1's "separate tree per controller" actually hurt was **coordinating memory reclaim with IO.** When memory runs low and page cache must be dropped, that reclaim itself causes disk IO — and in v1 the two controllers knew nothing about each other. v2's unified tree handles both in the same hierarchy.

### The biggest operational change — OOM diagnosis

Here is the fact you must know about cgroup v2.

> **`memory.current` includes page cache.**

So even when the memory the application actually holds (anon/RSS) is far below the limit, reading many files piles up page cache and pushes `memory.current` to the limit.

There is an important distinction here. **Page cache is reclaimable.** In the normal case the kernel hits the limit, drops page cache to make room, and no OOM occurs. The problem arises **when reclaim cannot keep up with allocation** — that is when the OOM killer acts.

Practical implications:

| Misconception | Reality |
|---|---|
| "`memory.current` near the limit means OOM is imminent" | Most of it is page cache and gets reclaimed. This can be perfectly normal |
| "Just look at RSS" | OOM can happen with low RSS (when reclaim can't keep up) |
| "Raising the limit fixes it" | If the cause is slow reclaim, it will recur |

**Values to look at when diagnosing:**

| File/value | Meaning |
|---|---|
| `memory.current` | Current usage (includes page cache) |
| `memory.stat` → `anon` | Anonymous memory — what the application actually holds |
| `memory.stat` → `file` | Page cache |
| `memory.events` → `oom` / `oom_kill` | OOM occurrences / kills |
| `memory.events` → `high` / `max` | Times the soft/hard limit was hit |
| `memory.pressure` (PSI) | **Fraction of time stalled** by memory pressure |

**PSI is especially useful** because it reports **pressure (how long you waited as a result)** rather than usage (how much you use). A rising `some avg10` in `memory.pressure` means time is being spent on reclaim — something a usage graph alone will not show.

### CPU limits and throttling — why low utilization can still be slow

A CPU limit is a **bandwidth limit.** `cpu.max` of `20000 100000` means "up to 20ms per 100ms period."

Something counterintuitive follows. If the application does its work in a short burst across several threads, it **spends the whole quota early in the period and is forcibly stopped until the period ends.** Average utilization looks like a low 20% while latency spikes.

It is worse with multiple threads. With 4 threads running concurrently, a 20ms quota is consumed in 5ms of wall time. The remaining 95ms is waiting.

**Diagnosis:** `cpu.stat` → `nr_throttled` (periods throttled) and `throttled_usec` (total throttled time). If `nr_throttled` is a meaningful fraction of `nr_periods`, the limit is the cause.

**Directions for response** (see [Resource Optimization](../ops/10-resource-optimization.md) for request/limit design):

- Raise or remove the limit (trading off node stability)
- Align the application's thread count with the limit (JVM `-XX:ActiveProcessorCount`, Go `GOMAXPROCS`, etc.) — **a mismatch between the CPU count the container perceives and its actual quota is often the root cause**
- Check actual stall time with `cpu.pressure` PSI

## Privileges — What Can It Do

Even with isolation (namespaces) and limits (cgroups) in place, reducing the **actions** a process can take is a separate layer.

| Feature | What it does | In Kubernetes |
|---|---|---|
| **capabilities** | Grant/drop root privileges as fine-grained units (`CAP_NET_ADMIN`, `CAP_SYS_ADMIN`, …) | `securityContext.capabilities.add/drop` |
| **seccomp** | Restrict the allowed set of **syscalls** | `securityContext.seccompProfile` (`RuntimeDefault` recommended) |
| **LSM** (AppArmor/SELinux) | Control file and network access by policy | `securityContext.appArmorProfile`, etc. |
| **no_new_privs** | Block privilege escalation via setuid binaries | `allowPrivilegeEscalation: false` |

The three layers answer different questions — capabilities ask "do you hold this privilege," seccomp asks "may you call this syscall," LSM asks "may you touch this object." **One alone is insufficient; layering them is the norm.**

`CAP_NET_ADMIN` deserves a mention. A sidecar mesh's init container needs it to install iptables rules, which is why adopting a mesh raises the security-review question "why does this Pod hold NET_ADMIN?"

## netfilter and conntrack — The Reality of Kubernetes Networking

### netfilter

netfilter is a framework providing **hooks** at defined points in the kernel network stack. `iptables`, `nftables`, and `ipvs` are all userspace tools using those hooks, or implementations on top of them.

Main hook points:

| Hook | When |
|---|---|
| `PREROUTING` | Packet arrives, **before** the routing decision — the DNAT point |
| `INPUT` | Packets bound for local processes |
| `FORWARD` | Packets passing through |
| `OUTPUT` | Packets leaving locally |
| `POSTROUTING` | **After** routing, just before leaving — the SNAT/MASQUERADE point |

Where these hooks are used in Kubernetes:

- **Service ClusterIP → Pod IP translation**: DNAT at `PREROUTING`/`OUTPUT`
- **Source translation for Pod → external traffic**: MASQUERADE at `POSTROUTING`
- **NetworkPolicy**: CNI inserts rules at `FORWARD` and elsewhere (Calico's iptables dataplane)
- **Sidecar mesh traffic interception**: REDIRECT at `OUTPUT`/`PREROUTING` inside the Pod net namespace

### kube-proxy modes — iptables, IPVS, nftables

Service implementation comes in three flavors, and **the landscape shifted in 2025–2026.**

| Mode | Rule evaluation | Status |
|---|---|---|
| **iptables** | **Linear evaluation** of rule chains — rule count grows with Service count and updates approach a full rewrite | Still the **default** (compatibility) |
| **IPVS** | In-kernel L4 load balancer, hash-based O(1) | **Deprecated in Kubernetes 1.35 (December 2025)**, removal targeted for 1.38 |
| **nftables** | O(1) lookup plus **incremental rule updates** | **GA in Kubernetes 1.33** (alpha 1.29 → beta 1.31). Requires **kernel 5.13+** on worker nodes |

How to read this:

- **In large clusters, the iptables-mode bottleneck is rule count and update cost.** The more Services and Endpoints, the longer kube-proxy's sync takes — and during that window the rules are not current.
- **If you run IPVS, you need a migration plan.** Removal is targeted for 1.38 and the recommended replacement is nftables mode.
- AL2023 nodes run kernel 6.x, so they satisfy the nftables mode kernel requirement.
- Even with nftables GA, **the default is still iptables** — you must switch explicitly.

### conntrack — the most frequent source of incidents

For netfilter to do NAT, it must **remember connections.** If you rewrote the address on the way out, you have to undo it on the way back. The kernel table holding that memory is `nf_conntrack`.

Since Kubernetes DNATs every Service, **every Service connection creates a conntrack entry.** That makes the table easy to exhaust.

**What happens on exhaustion is the crux of the problem.** There is no loud error. New connections are **silently dropped**, and the application sees connection timeouts or refusals. From the application side there is no way to know why.

| Observation point | Meaning |
|---|---|
| `/proc/sys/net/netfilter/nf_conntrack_count` | Current entries |
| `/proc/sys/net/netfilter/nf_conntrack_max` | Ceiling |
| `conntrack -S` → `insert_failed` | **Insert failures — direct evidence of exhaustion** |
| `conntrack -S` → `drop` | Dropped packets |
| `dmesg` → `nf_conntrack: table full, dropping packet` | Kernel warning |

**One EKS-specific caution.** kube-proxy also manages conntrack values, and **EKS ships a `kube-proxy-config` ConfigMap by default that takes precedence over command-line arguments.** So you can raise the sysctl on the node and have kube-proxy set it back. The correct path is to adjust `conntrack.maxPerCore`/`conntrack.min` in the ConfigMap and restart the kube-proxy DaemonSet.

Raising `nf_conntrack_max` **increases node memory use.** Each entry costs memory, so you cannot raise it without bound — it must match node size. Concrete settings are in [EKS Node Kernel Tuning](./03-eks-node-tuning.md).

::: warning Needs verification
On Bottlerocket, raising the conntrack ceiling via `settings.kernel.sysctl` does not take effect ([bottlerocket-os/bottlerocket#4221](https://github.com/bottlerocket-os/bottlerocket/issues/4221), filed September 2024). The cause is that **the kube-proxy config file (`/var/lib/kube-proxy-config/config`) takes precedence over command-line arguments**, and the known workaround is passing **`--conntrack-max-per-core=0 --conntrack-min=0`** to kube-proxy (0 meaning "do not change") so kube-proxy leaves it alone and the node's sysctl value survives.

**Whether this was resolved in a specific Bottlerocket release could not be confirmed.** Whichever path you use, verify the actual value on the node after applying. Configuration paths are covered in [EKS Node Kernel Tuning](./03-eks-node-tuning.md).
:::

### Reducing conntrack pressure

There are approaches that reduce the load itself.

- **Bypass Services**: headless Services connecting directly to Pod IPs — no DNAT, so fewer conntrack entries
- **eBPF dataplanes**: Cilium's kube-proxy replacement bypasses the netfilter/conntrack path ([Cilium eBPF](../networking/cilium/02-ebpf.md))
- **Connection reuse**: keepalive reduces connection count, lowering the entry creation rate

## overlayfs — How Image Layers Are Composed

Container images being layered, and those layers appearing as one filesystem, is **union mount** — specifically `overlayfs`.

Three parts:

| Layer | Role |
|---|---|
| **lowerdir** | Read-only — image layers (several can stack) |
| **upperdir** | Writable — the container's changes |
| **merged** | The combined view the container sees |

The operationally important property is **copy-up.** Modifying a file from lowerdir copies **the entire file to upperdir first**, then modifies it. So:

- **Modifying a large file slightly still pays the full copy cost.** Changing one byte of a 1GB file copies 1GB
- Heavy writes inside a container consume node disk (ephemeral storage)
- **Write-heavy paths belong on volumes** — emptyDir, PVC, and so on

## Summary

- There is no "container" in the kernel. It is a **combination** of namespaces (isolation) + cgroups (limits) + capabilities/seccomp/LSM (privileges) + overlayfs (filesystem) + netfilter (network). That is why isolation is selective, and forgotten isolation becomes a silent hole.
- **The net namespace is the Pod boundary.** The shared IP/port space, `localhost` communication, and Pod-scoped netfilter rules all follow from it.
- In cgroup v2, **`memory.current` includes page cache.** OOM diagnosis needs `memory.stat` → `anon`, `memory.events`, and **PSI (`memory.pressure`)** together.
- A CPU limit is a **bandwidth limit**, so throttling spikes latency even at low utilization. `cpu.stat` → `nr_throttled` is the evidence.
- For kube-proxy, **nftables is GA in 1.33 and IPVS is deprecated in 1.35 (removal targeted 1.38)**; the default is still iptables.
- **conntrack exhaustion silently drops connections.** `conntrack -S` → `insert_failed` is the direct evidence, and on EKS you must know the `kube-proxy-config` ConfigMap takes precedence.

Next: [Kernel Networking Stack](./02-network-stack.md) walks the full path a packet travels.

## References

- [Control Group v2 — Linux kernel documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [PSI - Pressure Stall Information](https://docs.kernel.org/accounting/psi.html)
- [namespaces(7) — Linux manual](https://man7.org/linux/man-pages/man7/namespaces.7.html)
- [KEP-127: Support User Namespaces](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/127-user-namespaces/README.md)
- [bottlerocket-os/bottlerocket#4221 — conntrack limit not applied](https://github.com/bottlerocket-os/bottlerocket/issues/4221)
- [NFTables mode for kube-proxy (Kubernetes Blog)](https://kubernetes.io/blog/2025/02/28/nftables-kube-proxy/)
- [KEP-5495: Deprecate IPVS mode in kube-proxy](https://github.com/kubernetes/enhancements/blob/master/keps/sig-network/5495-deprecate-ipvs-mode-in-kube-proxy/README.md)
- [Running kube-proxy in nftables Mode — EKS Best Practices](https://docs.aws.amazon.com/eks/latest/best-practices/nftables.html)
- [Increase nf_conntrack_max limit on EKS nodes](https://repost.aws/knowledge-center/eks-increase-nf-conntrack-max-limit)
- [Amazon EKS-Optimized Amazon Linux 2023 AMIs](https://aws.amazon.com/blogs/containers/amazon-eks-optimized-amazon-linux-2023-amis-now-available/)
