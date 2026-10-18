# Linux 内核概览

> **支持版本**：Linux 6.1 / 6.12 / 6.18（Amazon Linux 2023），Kubernetes 1.33+（Amazon EKS）
> **最后更新**：2026 年 9 月 12 日

## 本节涵盖内容

- 容器和 Kubernetes 实际运行在什么基础之上：为 namespaces、cgroups、netfilter 和 conntrack 提供支持的内核功能
- 数据包在内核中从 Pod 到网卡的传输路径，以及每个阶段可观测和可调优的内容
- 内核参数如何影响 EKS 节点上工作负载的性能与稳定性，以及哪些参数应调整、哪些应保持不变

## 本节的目的

大多数 Kubernetes 文档解释的是**声明式 API 之上的行为**。创建 Pod 后容器会启动；创建 Service 后流量会被分发；设置资源限制后，容器使用量不会超出限制。

但诊断事故时真正需要的知识，往往位于更底层。

| 生产环境中的常见现象 | 内核层面的实际情况 |
|---|---|
| “Pod 被 OOMKilled，但容器内存用量低于限制” | cgroup v2 的 `memory.current` 包括页缓存。只看 RSS 并不足够 |
| “节点上的新连接被静默丢弃” | 除其他数据包丢弃原因外，还要检查 conntrack 数量/上限、插入/丢弃计数器和内核日志 |
| “设置 CPU 限制后，p99 延迟变得不稳定” | CFS/EEVDF 限流。利用率虽低，但任务每个周期都会被强制暂停 |
| “同一节点上 Pod 到 Pod 的速度异常快” | 流量只经过 veth 对，并未经过网卡 |
| “Service 规则有数千条，延迟升高了” | kube-proxy 的 iptables 模式会线性遍历规则 |

**这些现象在 Kubernetes API 层都没有明显的根因。**本节旨在弥合这一认知差距。

## 读者和前置知识

- 具备 EKS/Kubernetes 运维经验、需要直接诊断资源限制和网络故障的基础设施工程师
- 假定你熟悉基本 Linux 命令和进程概念
- 不涵盖阅读内核源码或编写模块；重点是**运维人员可以观测和调优的内容**

## 文档结构

| # | 文档 | 回答的问题 |
|---|----------|---------------------|
| 1 | [容器背后的内核功能](./01-container-primitives.md) | 容器由什么组成？从 cgroup v1 迁移到 v2 在运维上有什么影响？ |
| 2 | [内核网络栈](./02-network-stack.md) | 数据包如何从 socket 到达网卡？可以在哪里挂载 hook？ |
| 3 | [EKS 节点内核调优](./03-eks-node-tuning.md) | 应在何时调整哪些参数？什么情况下应保留默认值？ |

## 如何阅读本节

文档 1 是文档 2 和 3 的前置内容。不理解 cgroup 和 namespace，就难以理解文档 3 中各调优项应放在哪些位置。

如果你是来诊断网络问题的，**阅读文档 2 和文档 3 的网络部分**即可。对于资源问题（OOM、CPU 限流），请按以下路径阅读：**文档 1 的 cgroup 部分 → 文档 3 的内存/CPU 部分**。

## 相关文档

- [Linux 基础](../basics/01-linux-basics.md) / [Linux 运维](../basics/02-linux-advanced.md)：命令和基本操作
- [容器技术](../basics/03-container-technology.md)：容器运行时和镜像层
- [eBPF 基础](../basics/05-ebpf-fundamentals.md)：eBPF 程序类型和用途
- [网络基础第 1 部分](../basics/06-network-fundamentals-part1.md)：从分层模型到云网络
- [Pod 网络基准测试](../networking/06-pod-network-benchmark.md)：与本节理论对应的测量结果
- [资源优化](../ops/10-resource-optimization.md)：request/limit 设计
- [VPC Lattice 内核数据路径](../service-mesh/vpc-lattice/07-kernel-datapath.md)：本地链路拦截中的内核层

## 关于准确性的说明

内核行为会随版本变化，特别是**可调参数会在不同内核版本间迁移位置并更名**（例如从 sysctl 移至 debugfs）。本节针对 AL2023 附带的内核系列（6.1 / 6.12 / 6.18）编写；涉及版本差异的内容会注明对应版本。

未经官方文档确认的内容会以 `Needs verification` 提示块标出，而不会作为事实陈述。**在生产集群应用任何参数前，请直接检查该节点所用内核版本中的实际值。**
