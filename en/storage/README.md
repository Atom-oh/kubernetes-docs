# Storage Overview

> **Last Updated**: September 1, 2026

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
  → container filesystem (ext4/xfs)
    → kernel block layer (io scheduler, page cache or O_DIRECT)
      → EBS volume (per-volume-type IOPS/throughput limits)
        → EC2 instance EBS bandwidth limit  ← the one everyone forgets
```

The volume's own limits and the **instance-level EBS bandwidth/IOPS limits** are separate budgets. An m5.xlarge has a baseline of roughly 6,000 IOPS — attach three gp3 volumes at 3,000 IOPS each and the instance becomes the bottleneck regardless of what the volumes are rated for.

## Choosing AWS storage

| Service | Access mode | Characteristics | Best fit |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO (single node) | Block, sub-ms latency | Databases, single-pod state |
| **EFS** | RWX (multi node) | NFS, ms-level latency, elastic capacity | Shared config/content, shared ML training data |
| **FSx for Lustre** | RWX | Parallel filesystem, high throughput | HPC, large-scale ML training |
| **S3 (Mountpoint CSI)** | RWX (read-heavy) | Object, high throughput / high latency | Data lakes, models and artifacts |
| **Instance store** | Node-local | NVMe, lowest latency, **ephemeral** | Caches, shuffle data, scratch space |

## Why measure instead of reading spec sheets

Storage is where the gap between the datasheet and lived experience is widest. The classic traps:

1. **gp2 burst credits** — a fresh volume runs at 3,000 IOPS until the credit bucket drains, then drops to its baseline (3 IOPS/GiB). If your load test finished within 30 minutes, you sailed past the cliff without seeing it.
2. **Volume limits vs instance limits** — see the stack diagram above.
3. **Conclusions change with iodepth** — a queue-depth-1 latency test and a queue-depth-32 IOPS test describe entirely different properties of the same volume.

[The EBS gp2 vs gp3 measured benchmark](./01-ebs-gp2-gp3-benchmark.md) demonstrates each of these traps with fio.
