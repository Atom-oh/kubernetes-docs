# 存储概览

> **最后更新**：September 11, 2026

在 Kubernetes 上运行有状态工作负载后，存储就不再只是“附加上去的东西”，而成为决定性能、成本和可用性的一个领域。本节按照实践中最重要的顺序介绍云存储：**如何选择 → 实际衡量什么 → 如何运维**。

## 本节内容

| 文档 | 内容简介 |
|----------|----------------|
| [EBS gp2 与 gp3 实测基准测试](./01-ebs-gp2-gp3-benchmark.md) | 为什么两个相同的 100GiB 卷性能相差 10 倍：fio 测得的 IOPS/延迟/吞吐量，以及 gp2 突发积分骤降 |

本书其他部分详细介绍了 Kubernetes 存储基础知识和 EKS 实操配置。请结合以下内容阅读本节：

- [Kubernetes 存储](../core/04-storage.md)：PV/PVC、StorageClass、动态配置、访问模式
- [EKS 存储第 1 部分：EBS、EFS](../eks/04-eks-storage-part1.md)：CSI 驱动安装和基本用法
- [EKS 存储第 2 部分：FSx for Lustre、S3、快照、性能](../eks/04-eks-storage-part2.md)
- [EKS 存储第 3 部分：监控、故障排查、成本](../eks/04-eks-storage-part3.md)

## 存储栈一览

了解从应用写入到物理卷的路径，就能判断性能不佳时应该归咎于哪一层：

```text
application write()
  → mounted volume filesystem (ext4/xfs)
    → guest kernel and block device
      → EC2 EBS path (IOPS/bandwidth shared by all volumes)
        → EBS service and volume (per-volume IOPS/throughput limits)
```

卷自身的限制与**实例级 EBS 带宽/IOPS 限制**是相互独立的预算。m5.xlarge 的基准性能约为 6,000 IOPS，因此同时以 3,000 IOPS 驱动三个 gp3 卷，相当于请求 9,000 IOPS，超过了该实例的持续基准性能。还要检查实例突发容量以及其他所有卷的流量。

## 选择 AWS 存储

| 服务 | 访问模式 | 特性 | 最适合的用途 |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO（单节点） | 块存储；延迟取决于类型/负载/队列深度 | 数据库、单 Pod 状态数据 |
| **EFS** | RWX（多节点） | NFS，毫秒级延迟，容量弹性扩展 | 共享配置/内容、共享 ML 训练数据 |
| **FSx for Lustre** | RWX | 并行文件系统，高吞吐量 | HPC、大规模 ML 训练 |
| **S3 (Mountpoint CSI)** | RWX（以读取为主） | 对象存储；操作语义不同于 POSIX/NFS | 数据湖、模型和制品 |
| **实例存储** | 节点本地 | NVMe，延迟最低，**临时性** | 缓存、shuffle 数据、临时空间 |

RWO 允许同一节点上的多个 Pod 使用卷；它并不保证只能由单个 Pod 使用。io2 Multi-Attach 等例外情况需要单独提供支持，并设计文件系统/应用程序的并发访问机制。Mountpoint S3 并非通用的 POSIX 共享文件系统：请确认它对工作负载所需的修改、重命名和锁定操作的支持情况。实例存储中的数据可能在重启后保留，但在停止/终止实例时可能丢失。

## 为什么要实测，而不是只看规格表

存储领域的规格表与实际体验之间的差距最大。常见陷阱包括：

1. **gp2 突发积分不足**：基准 IOPS 低于 3,000 的卷可以利用可用积分进行突发。突发持续时间取决于初始积分余额、容量和负载。一个满载的 100 GiB 卷以 3,000 IOPS 运行，计算出的突发时间约为 33 分钟；短时间测试可能无法反映积分耗尽后的性能。
2. **卷限制与实例限制**：请参阅上方的存储栈示意图。
3. **结论会随 iodepth 改变**：队列深度为 1 的延迟测试与队列深度为 32 的 IOPS 测试，描述的是同一卷完全不同的属性。

[EBS gp2 与 gp3 实测基准测试](./01-ebs-gp2-gp3-benchmark.md)使用 fio 展示了上述每一种陷阱。

## 参考资料

- [EBS 性能](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EC2 EBS 限制](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)
- [Mountpoint S3 语义](https://github.com/awslabs/mountpoint-s3/blob/main/doc/SEMANTICS.md)
