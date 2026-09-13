# 存储概览

> **最后更新**: September 2, 2026

一旦你开始在 Kubernetes 上运行有状态工作负载，存储就不再只是“附加的东西”，而成为决定性能、成本和可用性的领域。本节按实践中重要的顺序介绍云存储：**如何选择 → 实际衡量什么 → 如何运维**。

## 本节内容

| 文档 | 涵盖内容 |
|----------|----------------|
| [EBS gp2 vs gp3 实测基准测试](./01-ebs-gp2-gp3-benchmark.md) | 为什么两个相同的 100GiB volume 在性能上相差 10 倍 — 通过 fio 测量的 IOPS/延迟/吞吐量，以及 gp2 burst credit 临界点 |

本书的其他部分深入讲解 Kubernetes 存储基础知识和 EKS 实操配置。请将本节与以下内容一同阅读：

- [Kubernetes 存储](../core/04-storage.md) — PV/PVC、StorageClass、动态配置、访问模式
- [EKS 存储第 1 部分：EBS、EFS](../eks/04-eks-storage-part1.md) — CSI driver 安装和基本用法
- [EKS 存储第 2 部分：FSx for Lustre、S3、snapshots、性能](../eks/04-eks-storage-part2.md)
- [EKS 存储第 3 部分：监控、故障排除、成本](../eks/04-eks-storage-part3.md)

## 存储栈概览

了解从应用程序写入到物理 volume 的路径，有助于你在性能不佳时确定应该归咎于哪一层：

```text
application write()
  → container filesystem (ext4/xfs)
    → kernel block layer (io scheduler, page cache or O_DIRECT)
      → EBS volume (per-volume-type IOPS/throughput limits)
        → EC2 instance EBS bandwidth limit  ← the one everyone forgets
```

volume 自身的限制和 **instance-level EBS bandwidth/IOPS limits** 是彼此独立的预算。m5.xlarge 的基准约为 6,000 IOPS——附加三个各为 3,000 IOPS 的 gp3 volume 后，无论这些 volume 的额定性能如何，instance 都会成为瓶颈。

## 选择 AWS 存储

| 服务 | 访问模式 | 特性 | 最适合 |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO（单节点） | Block，亚毫秒级延迟 | 数据库、单 Pod 状态 |
| **EFS** | RWX（多节点） | NFS，毫秒级延迟，弹性容量 | 共享配置/内容、共享 ML 训练数据 |
| **FSx for Lustre** | RWX | 并行文件系统，高吞吐量 | HPC、大规模 ML 训练 |
| **S3 (Mountpoint CSI)** | RWX（读密集型） | Object，高吞吐量 / 高延迟 | 数据湖、模型和 artifacts |
| **Instance store** | Node-local | NVMe，最低延迟，**ephemeral** | 缓存、shuffle 数据、临时空间 |

## 为什么要测量而不是阅读规格表

存储是数据表与实际体验差距最大的领域。典型陷阱包括：

1. **gp2 burst credits** — 新 volume 会以 3,000 IOPS 运行，直到 credit bucket 耗尽，之后降至其基准值（3 IOPS/GiB）。如果你的负载测试在 30 分钟内完成，你就会在未察觉的情况下越过这个临界点。
2. **Volume 限制与 instance 限制** — 请参阅上方的存储栈图。
3. **结论会随 iodepth 改变** — queue-depth-1 延迟测试和 queue-depth-32 IOPS 测试描述的是同一 volume 截然不同的属性。

[EBS gp2 vs gp3 实测基准测试](./01-ebs-gp2-gp3-benchmark.md) 使用 fio 展示了上述每个陷阱。
