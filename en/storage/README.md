# Storage Overview

> **Last Updated**: September 11, 2026

The moment you run stateful workloads on Kubernetes, storage stops being "something you attach" and becomes a domain that dictates performance, cost, and availability. This section covers cloud storage in the order that matters in practice: **how to choose → what it actually measures → how to operate it**.

## What's in this section

| Document | What it covers |
|----------|----------------|
| [EBS gp2 vs gp3 Measured Benchmark](./01-ebs-gp2-gp3-benchmark.md) | Why two identical 100GiB volumes differ by 10x in performance — fio-measured IOPS/latency/throughput and the gp2 burst-credit cliff |

The Kubernetes storage fundamentals and hands-on EKS configuration are covered in depth elsewhere in this book. Read this section together with:

- [Kubernetes Storage](../core/04-storage.md) — PV/PVC, StorageClass, dynamic provisioning, access modes
- [EKS Storage Part 1: EBS, EFS](../eks/04-eks-storage-part1.md) — CSI driver installation and basic usage
- [EKS Storage Part 2: FSx for Lustre, S3, snapshots, performance](../eks/04-eks-storage-part2.md)
- [EKS Storage Part 3: monitoring, troubleshooting, cost](../eks/04-eks-storage-part3.md)

## The storage stack at a glance

Understanding the path from an application write to the physical volume tells you which layer to blame when performance disappoints:

```text
application write()
  → mounted volume filesystem (ext4/xfs)
    → guest kernel and block device
      → EC2 EBS path (IOPS/bandwidth shared by all volumes)
        → EBS service and volume (per-volume IOPS/throughput limits)
```

The volume's own limits and the **instance-level EBS bandwidth/IOPS limits** are separate budgets. An m5.xlarge has a baseline of roughly 6,000 IOPS — driving three gp3 volumes at 3,000 IOPS simultaneously requests 9,000 IOPS, above that sustained baseline. Check instance burst capacity and all other volume traffic as well.

## Choosing AWS storage

| Service | Access mode | Characteristics | Best fit |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO (single node) | Block; latency depends on type/load/queue depth | Databases, single-pod state |
| **EFS** | RWX (multi node) | NFS, ms-level latency, elastic capacity | Shared config/content, shared ML training data |
| **FSx for Lustre** | RWX | Parallel filesystem, high throughput | HPC, large-scale ML training |
| **S3 (Mountpoint CSI)** | RWX (read-heavy) | Object; different operation semantics from POSIX/NFS | Data lakes, models and artifacts |
| **Instance store** | Node-local | NVMe, lowest latency, **ephemeral** | Caches, shuffle data, scratch space |

RWO permits multiple Pods on one node; it is not a single-Pod guarantee. Exceptions such as io2 Multi-Attach require separate support and filesystem/application concurrency design. Mountpoint S3 is not a general POSIX shared filesystem: check modification, rename and locking support for the workload. Instance-store data may survive reboot but can be lost on stop/termination.

## Why measure instead of reading spec sheets

Storage is where the gap between the datasheet and lived experience is widest. The classic traps:

1. **Small gp2 burst credits** — volumes with a baseline below 3,000 IOPS can burst using available credits. Duration depends on initial balance, capacity and load. A full 100 GiB volume at 3,000 IOPS calculates to about 33 minutes; a short test can miss post-depletion performance.
2. **Volume limits vs instance limits** — see the stack diagram above.
3. **Conclusions change with iodepth** — a queue-depth-1 latency test and a queue-depth-32 IOPS test describe entirely different properties of the same volume.

[The EBS gp2 vs gp3 measured benchmark](./01-ebs-gp2-gp3-benchmark.md) demonstrates each of these traps with fio.

## References

- [EBS performance](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EC2 EBS limits](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)
- [Mountpoint S3 semantics](https://github.com/awslabs/mountpoint-s3/blob/main/doc/SEMANTICS.md)
