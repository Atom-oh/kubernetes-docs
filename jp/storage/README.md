# Storage 概要

> **最終更新**: September 2, 2026

Kubernetes で stateful workload を実行した瞬間、storage は単なる「後付けするもの」ではなくなり、performance、cost、availability を左右する領域になります。このセクションでは、実務で重要となる順序で cloud storage を扱います: **選び方 → 実際に測定されるもの → 運用方法**。

## このセクションの内容

| ドキュメント | 内容 |
|----------|----------------|
| [EBS gp2 vs gp3 実測ベンチマーク](./01-ebs-gp2-gp3-benchmark.md) | 同一の 100GiB volume でも performance が 10 倍異なる理由 — fio で測定した IOPS/latency/throughput と gp2 burst-credit cliff |

Kubernetes storage の基礎と実践的な EKS 設定については、本書の別の箇所で詳しく扱っています。このセクションは以下と併せてお読みください:

- [Kubernetes Storage](../core/04-storage.md) — PV/PVC、StorageClass、dynamic provisioning、access modes
- [EKS Storage Part 1: EBS, EFS](../eks/04-eks-storage-part1.md) — CSI driver のインストールと基本的な使用方法
- [EKS Storage Part 2: FSx for Lustre, S3, snapshots, performance](../eks/04-eks-storage-part2.md)
- [EKS Storage Part 3: monitoring, troubleshooting, cost](../eks/04-eks-storage-part3.md)

## Storage stack の概要

application write から physical volume に至る経路を理解すると、performance が期待に届かないときに、どの layer を疑うべきかが分かります:

```text
application write()
  → container filesystem (ext4/xfs)
    → kernel block layer (io scheduler, page cache or O_DIRECT)
      → EBS volume (per-volume-type IOPS/throughput limits)
        → EC2 instance EBS bandwidth limit  ← the one everyone forgets
```

volume 自体の limits と **instance-level EBS bandwidth/IOPS limits** は別々の予算です。m5.xlarge の baseline はおよそ 6,000 IOPS です。3,000 IOPS の gp3 volume を 3 つアタッチすると、volume の定格にかかわらず instance が bottleneck になります。

## AWS storage の選択

| Service | Access mode | 特性 | 最適な用途 |
|---------|-------------|-----------------|----------|
| **EBS (gp3/io2)** | RWO (single node) | Block、sub-ms latency | Databases、single-pod state |
| **EFS** | RWX (multi node) | NFS、ms-level latency、elastic capacity | Shared config/content、共有 ML training data |
| **FSx for Lustre** | RWX | Parallel filesystem、high throughput | HPC、大規模 ML training |
| **S3 (Mountpoint CSI)** | RWX (read-heavy) | Object、high throughput / high latency | Data lakes、models と artifacts |
| **Instance store** | Node-local | NVMe、最も低い latency、**ephemeral** | Caches、shuffle data、scratch space |

## Spec sheet を読むのではなく測定する理由

Storage は、datasheet と実際の使用感の差が最も大きい領域です。代表的な落とし穴は次のとおりです:

1. **gp2 burst credits** — 新しい volume は credit bucket が枯渇するまで 3,000 IOPS で動作し、その後 baseline（3 IOPS/GiB）まで低下します。load test が 30 分以内に終わった場合、この cliff を見ないまま通り過ぎてしまいます。
2. **Volume limits と instance limits** — 上の stack diagram を参照してください。
3. **結論は iodepth によって変わる** — queue-depth-1 の latency test と queue-depth-32 の IOPS test は、同じ volume のまったく異なる特性を表します。

[実測した EBS gp2 vs gp3 ベンチマーク](./01-ebs-gp2-gp3-benchmark.md)では、fio を使ってこれらの各落とし穴を実証します。
