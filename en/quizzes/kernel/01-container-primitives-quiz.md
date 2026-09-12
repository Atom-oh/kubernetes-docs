# Kernel Features Behind Containers Quiz

This quiz tests your understanding of namespaces, cgroup v2, netfilter, and conntrack.

## Multiple Choice Questions

1. What does "there is no container in the kernel" mean, and what practical conclusion follows?
   - A) Containers are a kind of virtual machine and unrelated to the kernel
   - B) A container is a convention combining namespaces, cgroups, capabilities, and more — so isolation is selective, and isolation a runtime omits becomes a silent hole
   - C) Containers are implemented purely in userspace libraries
   - D) Kernel 6.x added a `struct container`

<details>

<summary>Show Answer</summary>

**Answer: B) A container is a convention combining namespaces, cgroups, capabilities, and more — so isolation is selective, and isolation a runtime omits becomes a silent hole**

**Explanation:**
There is no `struct container` and no single syscall that creates one. A runtime starts a process while applying namespaces (isolation), cgroups (limits), capabilities/seccomp/LSM (privileges), overlayfs (filesystem), and netfilter (network) together. Two conclusions follow from it being a combination — isolation is not all-or-nothing but selective (a Pod sharing the network namespace while separating mounts is the example), and since the kernel does not know "make a container," a runtime that does not apply a seccomp profile simply runs without one.
</details>

2. Why can two containers in a Pod reach each other over `localhost` while being unable to bind the same port?
   - A) Kubernetes automatically creates an inter-container proxy
   - B) They share a net namespace per Pod, so they use the same IP and port space
   - C) The CNI links a per-container loopback
   - D) kube-proxy routes intra-Pod traffic

<details>

<summary>Show Answer</summary>

**Answer: B) They share a net namespace per Pod, so they use the same IP and port space**

**Explanation:**
Kubernetes creates one net namespace per Pod (held by the pause container) and puts all that Pod's containers into it. So they share the same IP and port space, `localhost` works, and two containers cannot both bind 8080. This is the foundation of the sidecar pattern. Also, netfilter rules are per net namespace, so a sidecar mesh's init container can install iptables rules inside the Pod without affecting the whole node.
</details>

3. Why can `memory.current` sit near the limit in cgroup v2 and still be perfectly normal?
   - A) `memory.current` is an estimate and therefore inaccurate
   - B) `memory.current` includes page cache, and page cache is reclaimable — the kernel drops it on hitting the limit to make room
   - C) cgroup v2 does not enforce limits
   - D) `memory.current` shows whole-node memory

<details>

<summary>Show Answer</summary>

**Answer: B) `memory.current` includes page cache, and page cache is reclaimable — the kernel drops it on hitting the limit to make room**

**Explanation:**
Even with the memory the application actually holds (anon/RSS) far below the limit, reading many files piles up page cache and pushes `memory.current` to the limit. But page cache is reclaimable, so normally the kernel drops it to make room and no OOM occurs. The problem is **when reclaim cannot keep up with allocation** — that is when the OOM killer acts. So diagnosis needs `memory.stat` → `anon`, `memory.events` → `oom`, and PSI (`memory.pressure`) together.
</details>

4. With CPU utilization at a low 20% but p99 latency spiking, how do you confirm the CPU limit is the cause?
   - A) Re-check utilization with `top`
   - B) Check the ratio of `nr_throttled` to `nr_periods` in `cpu.stat`
   - C) Check `memory.pressure`
   - D) Check the node's `/proc/loadavg`

<details>

<summary>Show Answer</summary>

**Answer: B) Check the ratio of `nr_throttled` to `nr_periods` in `cpu.stat`**

**Explanation:**
A CPU limit is a bandwidth limit. `cpu.max` of `20000 100000` means "up to 20ms per 100ms period," so an application doing short bursts across threads spends the quota early and is forcibly stopped until the period ends. Average utilization looks like 20% while latency spikes. A meaningful `nr_throttled / nr_periods` ratio means the limit is the cause. The root cause is usually a mismatch between the CPU count the application perceives and its quota, so align `GOMAXPROCS` or `-XX:ActiveProcessorCount` first.
</details>

5. Which statement about kube-proxy modes is correct as of 2026?
   - A) nftables is the default and iptables has been removed
   - B) nftables is GA in 1.33, IPVS is deprecated in 1.35 (removal targeted 1.38), and the default is still iptables
   - C) IPVS is the default and nftables is alpha
   - D) All three modes have identical performance characteristics

<details>

<summary>Show Answer</summary>

**Answer: B) nftables is GA in 1.33, IPVS is deprecated in 1.35 (removal targeted 1.38), and the default is still iptables**

**Explanation:**
nftables mode matured alpha 1.29 → beta 1.31 → **GA 1.33**, offering O(1) lookup and incremental rule updates (requires kernel 5.13+ on workers; AL2023 satisfies it). IPVS mode was **deprecated in 1.35 (December 2025)** with removal targeted for 1.38, and the recommended replacement is nftables. For compatibility **the default is still iptables**, so switching to nftables is an explicit decision. If you run IPVS, you need a migration plan.
</details>

6. What are the symptom and the direct evidence of conntrack table exhaustion?
   - A) A clear kernel panic — immediately visible in `dmesg`
   - B) New connections are silently dropped and the application only sees timeouts. The direct evidence is `insert_failed` in `conntrack -S`
   - C) All existing connections drop immediately
   - D) CPU utilization rises to 100%

<details>

<summary>Show Answer</summary>

**Answer: B) New connections are silently dropped and the application only sees timeouts. The direct evidence is `insert_failed` in `conntrack -S`**

**Explanation:**
Since Kubernetes DNATs every Service, all Service traffic creates conntrack entries and the table is easy to exhaust. On exhaustion there is no loud error — new connections are silently dropped and the application sees only timeouts or refusals, with no way to know why from its side. `insert_failed` in `conntrack -S` is the direct evidence of insert failures, and the `nf_conntrack: table full` warning in `dmesg` is a secondary signal.
</details>

7. What must you watch out for when adjusting conntrack values on EKS?
   - A) A sysctl setting in the node bootstrap is sufficient
   - B) The `kube-proxy-config` ConfigMap that EKS ships by default takes precedence over command-line arguments, so raising the sysctl alone can be reverted by kube-proxy
   - C) conntrack is a fixed value that cannot be adjusted
   - D) A Pod's `securityContext.sysctls` can change node-global values

<details>

<summary>Show Answer</summary>

**Answer: B) The `kube-proxy-config` ConfigMap that EKS ships by default takes precedence over command-line arguments, so raising the sysctl alone can be reverted by kube-proxy**

**Explanation:**
kube-proxy also manages conntrack values, and EKS ships a `kube-proxy-config` ConfigMap by default that takes precedence over CLI arguments. The correct path is adjusting `conntrack.maxPerCore`/`conntrack.min` in the ConfigMap and restarting the kube-proxy DaemonSet. `maxPerCore` is used because being per-core rather than absolute, it scales proportionally across node sizes. D is wrong — `nf_conntrack_max` is node-global and cannot be changed from a Pod spec.
</details>

8. What operational problem does overlayfs copy-up create?
   - A) Image layers are stored redundantly, increasing registry size
   - B) Modifying a file from lowerdir copies the entire file to upperdir, so even a small change to a large file pays the full copy cost
   - C) Container startup time grows with layer count
   - D) Read performance degrades in proportion to layer count

<details>

<summary>Show Answer</summary>

**Answer: B) Modifying a file from lowerdir copies the entire file to upperdir, so even a small change to a large file pays the full copy cost**

**Explanation:**
overlayfs merges a read-only lowerdir (image layers) with a writable upperdir (changes). Modifying a lowerdir file requires copying it to upperdir first, and that is a **full file copy** — changing one byte of a 1GB file copies 1GB. So heavy writes inside a container consume node ephemeral storage, and **write-heavy paths belong on volumes** like emptyDir or a PVC.
</details>
