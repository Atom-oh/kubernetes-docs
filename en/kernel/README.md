# Linux Kernel Overview

> **Supported Versions**: Linux 6.1 / 6.12 / 6.18 (Amazon Linux 2023), Kubernetes 1.33+ (Amazon EKS)
> **Last Updated**: September 12, 2026

## What This Section Covers

- What containers and Kubernetes actually run on top of — the kernel features behind namespaces, cgroups, netfilter, and conntrack
- The path a packet travels inside the kernel from a Pod to the NIC, and what you can observe and tune at each point
- How kernel parameters affect workload performance and stability on EKS nodes, and what to change versus what to leave alone

## Why This Section Exists

Most Kubernetes documentation explains things **on top of a declarative API**. Create a Pod and containers start; create a Service and traffic is distributed; set a resource limit and the container uses no more than that.

But the knowledge you need when diagnosing an incident lives one layer below.

| Symptom you meet in production | The reality at the kernel layer |
|---|---|
| "The Pod was OOMKilled but container memory was under the limit" | cgroup v2's `memory.current` includes page cache. Looking at RSS alone is not enough |
| "New connections on the node are silently dropped" | `nf_conntrack` table exhaustion. It only shows in the `nf_conntrack_insert_failed` counter |
| "I set a CPU limit and p99 got spiky" | CFS/EEVDF throttling. Utilization is low but the task is forcibly stopped every period |
| "Pod-to-Pod on the same node is unusually fast" | It only traverses the veth pair and never touches the NIC |
| "We have thousands of Service rules and latency went up" | Linear rule evaluation in iptables-mode kube-proxy |

**None of these have a visible cause at the Kubernetes API layer.** Closing that gap is the purpose of this section.

## Audience and Assumptions

- Infrastructure engineers with EKS/Kubernetes operations experience who must diagnose resource constraints and network failures directly
- We assume you know basic Linux commands and process concepts
- Reading kernel source or writing modules is out of scope. We focus on **what an operator can observe and tune**

## Document Structure

| # | Document | Question it answers |
|---|----------|---------------------|
| 1 | [Kernel Features Behind Containers](./01-container-primitives.md) | What is a container made of? Why does the cgroup v1 → v2 change matter operationally? |
| 2 | [Kernel Networking Stack](./02-network-stack.md) | What path does a packet travel from socket to NIC? Where can you attach hooks? |
| 3 | [EKS Node Kernel Tuning](./03-eks-node-tuning.md) | Which parameters should you change and when? When is leaving the default the right answer? |

## How to Read This Section

Document 1 is prerequisite for 2 and 3. Without cgroups and namespaces, the tuning items in 3 will not make sense in their given places.

If you came here to diagnose a network problem, **document 2 plus the network section of document 3** is enough. For resource problems (OOM, CPU throttling), the path is **the cgroup section of document 1 → the memory/CPU sections of document 3**.

## Related Documents

- [Linux Basics](../basics/01-linux-basics.md) / [Linux Operations](../basics/02-linux-advanced.md) — commands and basic operations
- [Container Technology](../basics/03-container-technology.md) — container runtimes and image layers
- [eBPF Fundamentals](../basics/05-ebpf-fundamentals.md) — eBPF program types and uses
- [Network Fundamentals, Part 1](../basics/06-network-fundamentals-part1.md) — from layer models to the cloud
- [Pod Network Benchmark](../networking/06-pod-network-benchmark.md) — measurements corresponding to this section's theory
- [Resource Optimization](../ops/10-resource-optimization.md) — request/limit design
- [VPC Lattice Kernel Datapath](../service-mesh/vpc-lattice/07-kernel-datapath.md) — the kernel layer of link-local interception

## A Note on Accuracy

Kernel behavior changes between versions, and in particular **tunables move location and change names across kernel versions** (sysctl → debugfs, and so on). This section is written against the kernel series AL2023 ships (6.1 / 6.12 / 6.18), and version-dependent items state which version they refer to.

Anything not confirmed against official documentation is marked with a `Needs verification` block rather than stated as fact. **Before applying any parameter to a production cluster, check the actual value on that node's kernel version directly.**
