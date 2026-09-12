# EKS Node Kernel Tuning Quiz

This quiz tests your understanding of parameter application paths, kernel version transitions, and justified tuning.

## Multiple Choice Questions

1. What are the three problems unfounded kernel tuning creates?
   - A) Security vulnerabilities, license violations, loss of support
   - B) Unreproducible configuration, breakage on kernel upgrade, defeating kernel auto-tuning
   - C) Reduced network bandwidth, increased disk usage, memory leaks
   - D) Pod scheduling failures, image pull failures, authentication failures

<details>

<summary>Show Answer</summary>

**Answer: B) Unreproducible configuration, breakage on kernel upgrade, defeating kernel auto-tuning**

**Explanation:**
Values differing per node make incidents impossible to reproduce. Tunable names and locations move between kernel versions (sysctl → debugfs, and so on), so a setting valid on 6.1 can break on 6.18. And pinning values the kernel auto-tunes under load, like TCP buffers, disables that auto-tuning. So the precondition for tuning is measurement — identify the symptom with drop counters and only touch that point.
</details>

2. What must you know about AL2023's kernel version transition as of 2026?
   - A) AL2023 offers only kernel 6.1
   - B) From August 17, 2026, the default kernel for `al2023-ami-kernel-default` AMIs changed from 6.1 to 6.18, so node replacement alone changes the kernel
   - C) The kernel version is determined automatically by the EKS control plane version
   - D) AL2023 does not support kernel upgrades

<details>

<summary>Show Answer</summary>

**Answer: B) From August 17, 2026, the default kernel for `al2023-ami-kernel-default` AMIs changed from 6.1 to 6.18, so node replacement alone changes the kernel**

**Explanation:**
AL2023 launched in March 2023 with kernel 6.1, added 6.12 support in April 2025, and **its default kernel changed to 6.18 on August 17, 2026.** With `kernel-default` AMIs, node replacement alone — autoscaling, upgrades, spot reclamation — changes the kernel. To pin a kernel you must explicitly use a version-specific AMI such as `al2023-ami-kernel-6.1-*`, and a kernel transition should be treated with the same weight as a Kubernetes version upgrade.
</details>

3. What is the most common root cause of CPU throttling, and the first response?
   - A) Insufficient node CPU — move to a larger instance type
   - B) A mismatch between the CPU count the application perceives and its quota — align `GOMAXPROCS`, `-XX:ActiveProcessorCount`, etc., with the limit
   - C) A kernel scheduler bug — upgrade the kernel
   - D) A cgroup v2 migration problem — revert to v1

<details>

<summary>Show Answer</summary>

**Answer: B) A mismatch between the CPU count the application perceives and its quota — align `GOMAXPROCS`, `-XX:ActiveProcessorCount`, etc., with the limit**

**Explanation:**
If the runtime inside the container sees all node cores and spawns that many threads, it burns the CPU limit's quota instantly. With 4 threads running concurrently, a 20ms quota is consumed in 5ms of wall time and the remaining 95ms is waiting. So the first response is aligning the perceived CPU count with the limit, followed by raising the limit, followed by considering limit removal for extremely sensitive cases.
</details>

4. What is more effective than kernel tuning for node stability, and why?
   - A) Limiting Pod count — lower density avoids problems
   - B) kubelet resource reservations and eviction thresholds — insufficient reservation leads to the kernel or kubelet itself hitting OOM, taking the whole node `NotReady`, and eviction is better than a kernel OOM
   - C) A node restart schedule — periodic restarts to clean up memory
   - D) Smaller images — freeing disk headroom

<details>

<summary>Show Answer</summary>

**Answer: B) kubelet resource reservations and eviction thresholds — insufficient reservation leads to the kernel or kubelet itself hitting OOM, taking the whole node `NotReady`, and eviction is better than a kernel OOM**

**Explanation:**
With insufficient `--system-reserved` and `--kube-reserved`, Pods consume all node memory and the kernel or kubelet hits OOM. The node goes `NotReady` and every Pod on it is affected — far worse than an individual Pod OOM. Eviction is Kubernetes moving a Pod in a controlled way while the OOM killer abruptly kills a process, so the goal is setting `--eviction-hard` so Kubernetes intervenes before a kernel OOM.
</details>

5. Why does PSI (Pressure Stall Information) give a better signal than usage metrics?
   - A) It measures usage more accurately
   - B) It reports the fraction of time stalled on that resource rather than usage, so it reveals time spent on reclaim or contention even when the usage graph looks calm
   - C) It is collected in hardware rather than the kernel
   - D) It retains historical data automatically

<details>

<summary>Show Answer</summary>

**Answer: B) It reports the fraction of time stalled on that resource rather than usage, so it reveals time spent on reclaim or contention even when the usage graph looks calm**

**Explanation:**
`some avg10` in `memory.pressure` is the fraction of the last 10 seconds in which at least one task was stalled on that resource. With memory usage sitting calmly below the limit, a climbing value means time is going into page cache reclaim — something a usage graph alone will not show. It is provided by cgroup v2, node-wide at `/proc/pressure/*` and per cgroup at `<cgroup>/memory.pressure`.
</details>

6. Which of the following is NOT a representative case of "justified tuning"?
   - A) `vm.max_map_count` — OpenSearch-family software fails to start at the default
   - B) `net.core.somaxconn` — evidence available from the accept-queue overflow counter
   - C) `net.ipv4.tcp_rmem` / `tcp_wmem` — pinning the defaults to improve performance
   - D) `net.ipv4.ip_local_port_range` — source port exhaustion shows up directly as connection failures

<details>

<summary>Show Answer</summary>

**Answer: C) `net.ipv4.tcp_rmem` / `tcp_wmem` — pinning the defaults to improve performance**

**Explanation:**
The default for `tcp_rmem`/`tcp_wmem` is **not to touch them.** The kernel is auto-tuning under load, and pinning values disables that. You might consider ceiling adjustments on high-BDP long-distance paths, but it is not a general tuning target. A, B, and D all have clear symptoms and direct evidence counters — startup failure logs, `TcpExtListenOverflows` in `nstat`, and connection failures respectively.
</details>

7. Which value cannot be changed via a Pod's `securityContext.sysctls`?
   - A) Many `net.*` values that are settable per net namespace
   - B) `net.netfilter.nf_conntrack_max` — a node-global value
   - C) TCP-related values belonging to the Pod's net namespace
   - D) All of the above are changeable

<details>

<summary>Show Answer</summary>

**Answer: B) `net.netfilter.nf_conntrack_max` — a node-global value**

**Explanation:**
Many `net.*` values are settable per net namespace and can be changed via Pod `securityContext.sysctls`. By contrast `vm.*`, `fs.*`, and some values like `net.netfilter.nf_conntrack_max` are node-global and require the node bootstrap or Bottlerocket settings path. Also, kubelet rejects "unsafe" sysctls by default, so allowing one requires `--allowed-unsafe-sysctls`, which is itself a node setting.
</details>

8. What matters most long-term in managing kernel parameter changes?
   - A) Always upgrading to the newest kernel
   - B) Managing as code, recording the rationale in comments, and separating node groups by workload character
   - C) Forcing one identical tuning profile on every node
   - D) Applying changes to production immediately

<details>

<summary>Show Answer</summary>

**Answer: B) Managing as code, recording the rationale in comments, and separating node groups by workload character**

**Explanation:**
Codifying with Karpenter `EC2NodeClass`, launch templates, or Bottlerocket settings prevents values differing per node. Without a comment on "why this value," nobody can revert it six months later. Different workload characters need different tuning, so separate node groups rather than forcing one profile. Add to that pinning or planning the kernel transition, verifying actual values after applying (especially conntrack), and measuring before and after under identical conditions.
</details>
