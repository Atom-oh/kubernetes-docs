# EBS gp2 与 gp3 实测基准测试

> **记录的测试环境**：Kubernetes 1.36（Amazon EKS）、EBS CSI driver、fio 3.36
> **最后更新**：2026 年 10 月 16 日

AWS 那句“一行操作：将 gp2 迁移到 gp3，节省 20%，性能相同或更好”广为人知，但很难找到图表展示这种差异**何时、以什么形式**出现在 Kubernetes PVC 上。本文将**一个 100 GiB gp2 PVC 和一个 100 GiB gp3 PVC**挂载到同一个 EKS 节点上，用 fio 对两者进行 45 分钟的高强度测试。重点不是“gp2 很慢”，而是：**gp2 有 33 分钟与 gp3 难以区分，之后却在一秒内跌至十分之一**。这些是原始测试运行中报告的结果，并不保证重测能得到相同结果。比较不同运行结果时，请记录初始积分、驱动程序/镜像版本和节点状况。

![架构图：一个 fio Pod 通过 EBS CSI 挂载的块设备发送 4k 随机 I/O 至 gp3（固定 3,000 IOPS）和 gp2（基准 300 IOPS，另有 I/O 积分桶），积分桶余额报告到 CloudWatch BurstBalance。](../.gitbook/assets/en-storage-01-ebs-gp2-gp3-benchmark-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-storage-01-ebs-gp2-gp3-benchmark-0.html)

## TL;DR：测量结果

| 指标（100 GiB，m5.xlarge） | gp3 | gp2 |
|-----------------------------|-----|-----|
| 4k 随机读取 IOPS（qd32） | 平均 **3,001**，600 秒内保持平稳（最低 2,991） | **3,001 → 300**，在 1,999 秒时骤降 |
| 4k 随机读取 p99 延迟（qd32） | 12.9 ms | 109.6 ms（主要受骤降后的时段影响） |
| 4k 随机写入 IOPS（qd32，积分耗尽后） | **3,025** | 601（包含部分重新积累的积分） |
| 4k 随机读取延迟（qd1） | 平均 **0.56 ms** / p99 0.87 ms | 平均 1.65 ms，呈双峰分布：p50 0.60 / p95 3.39 ms |
| 1 MiB 顺序读取 / 写入 | 127 / 126 MiB/s（基准 125 MiB/s） | 130 / 129 MiB/s（≤170 GiB 时上限为 128 MiB/s） |
| 月成本（首尔区域，100 GiB） | **$9.12** | $11.40 |

一句话总结：**容量相同时，gp2 以高出 25% 的价格，卖给你 33 分钟的 3,000 IOPS。**

## 测试环境

| 项目 | 值 |
|------|-------|
| 集群 | Amazon EKS、Kubernetes 1.36、ap-northeast-2 |
| 节点 | **m5.xlarge**（4 vCPU，16 GiB），由 Karpenter 配置；实例 EBS 限额：基准 6,000 IOPS / 1,150 Mbps（143.75 MB/s ≈137 MiB/s），突发 18,750 IOPS / 4,750 Mbps |
| 卷 | 一个 EBS **gp2 100 GiB** 和一个 **gp3 100 GiB**，使用默认设置（`StorageClass` `gp2` / `gp3`、EBS CSI driver） |
| Pod | `alpine:3.20` + `fio 3.36`，`direct=1`（绕过页缓存），`libaio` 引擎，8 GiB 测试文件 |
| 执行方式 | **两个卷从未同时进行测量**；多个卷会共享实例持续/突发 I/O 预算，因此并发测试会引入干扰 |
| 定价 | gp2 $0.114/GB-月，gp3 $0.0912/GB-月 + 额外 IOPS $0.0057/IOPS-月 + 额外吞吐量 $0.0456/MiB/s-月（首尔区域，Pricing API，2026 年 9 月） |

`nodeSelector` 将节点固定为 m5.xlarge，原因只有一个：该实例级 EBS 限额（6,000 IOPS）远高于卷限额（3,000），为观测卷留出余量。还应通过节点总 I/O 和实例/卷超限指标确认瓶颈所在。在较小的实例上（m5.large 的基准为 3,600 IOPS），两个限额会变得难以区分，结果也就不容易解读。

### Deployment 清单

记录的测试运行使用 `alpine:3.20` / fio 3.36。Alpine 3.20 已结束常规支持，因此下面的**重测**示例使用 3.24.2。软件包版本可能变化：请保存打印出的 fio 版本和镜像摘要，并将新结果与历史测量结果分开。这适用于已配置 `ebs.csi.aws.com` 及其 IAM 权限的常规 EC2 节点，不适用于 EKS Auto Mode provisioner。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: bench-storage
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: bench-gp2
provisioner: ebs.csi.aws.com
parameters:
  type: gp2
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: bench-gp3
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
  iops: "3000"
  throughput: "125"
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Delete
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bench-gp2
  namespace: bench-storage
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: bench-gp2
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: bench-gp3
  namespace: bench-storage
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: bench-gp3
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: fio
  namespace: bench-storage
  annotations:
    karpenter.sh/do-not-disrupt: "true"   # keep consolidation from evicting a 45-minute measurement
spec:
  nodeSelector:
    node.kubernetes.io/instance-type: m5.xlarge
  containers:
    - name: fio
      image: alpine:3.24.2
      command: ["sh", "-c", "apk add --no-cache fio && fio --version && sleep infinity"]
      resources:
        requests: { cpu: "1", memory: 1Gi }
        limits: { cpu: "2", memory: 2Gi }
      volumeMounts:
        - { name: gp2, mountPath: /mnt/gp2 }
        - { name: gp3, mountPath: /mnt/gp3 }
  volumes:
    - name: gp2
      persistentVolumeClaim: { claimName: bench-gp2 }
    - name: gp3
      persistentVolumeClaim: { claimName: bench-gp3 }
  restartPolicy: Never
```

> 之所以设置 `karpenter.sh/do-not-disrupt` 注解，是因为本基准测试的第一次尝试确实在没有它的情况下失败了。当节点上的另一个工作负载消失后，Karpenter 判断该节点“利用率不足”，启动整合操作，并在 45 分钟测试运行到一半时驱逐了 fio Pod（退出代码 137）。该注解会阻止某些主动发起的干扰操作。但它无法保证节点故障、Spot 中断、强制终止或 terminationGracePeriod 到期时 Pod 不受影响；PDB 同样无法阻止非自愿故障。请持久化保存结果，并确保测试运行可以重新启动。

### fio 命令

以下各阶段都使用下面的通用选项，并按顺序逐项运行。

```bash
COMMON="--ioengine=libaio --direct=1 --group_reporting --output-format=json"

# 0. lay out the test files (8 GiB, sequential write)
fio --name=layout --filename=/mnt/gp3/testfile --size=8G --rw=write --bs=1M $COMMON
fio --name=layout --filename=/mnt/gp2/testfile --size=8G --rw=write --bs=1M $COMMON

# 1. 4k random read, qd32: gp3 for 600 s, gp2 for 2,700 s (45 minutes, to catch the credit cliff)
fio --name=gp3-randread --filename=/mnt/gp3/testfile --size=8G --rw=randread --bs=4k \
    --iodepth=32 --runtime=600  --time_based --write_iops_log=gp3_rr --log_avg_msec=1000 $COMMON
fio --name=gp2-randread --filename=/mnt/gp2/testfile --size=8G --rw=randread --bs=4k \
    --iodepth=32 --runtime=2700 --time_based --write_iops_log=gp2_rr --log_avg_msec=1000 $COMMON

# 2. 4k random write, qd32, 120 s (gp2 has exhausted its credits by now)
fio --name=gp3-randwrite --filename=/mnt/gp3/testfile --size=8G --rw=randwrite --bs=4k --iodepth=32 --runtime=120 --time_based $COMMON
fio --name=gp2-randwrite --filename=/mnt/gp2/testfile --size=8G --rw=randwrite --bs=4k --iodepth=32 --runtime=120 --time_based $COMMON

# 3. 4k random read, qd1, 60 s: end-to-end completion latency at low concurrency
fio --name=gp3-lat --filename=/mnt/gp3/testfile --size=8G --rw=randread --bs=4k --iodepth=1 --runtime=60 --time_based $COMMON
fio --name=gp2-lat --filename=/mnt/gp2/testfile --size=8G --rw=randread --bs=4k --iodepth=1 --runtime=60 --time_based $COMMON

# 4. 1 MiB sequential read/write, qd8, 60 s: throughput ceiling
fio --name=gp3-seqread  --filename=/mnt/gp3/testfile --size=8G --rw=read  --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
fio --name=gp3-seqwrite --filename=/mnt/gp3/testfile --size=8G --rw=write --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
fio --name=gp2-seqread  --filename=/mnt/gp2/testfile --size=8G --rw=read  --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
fio --name=gp2-seqwrite --filename=/mnt/gp2/testfile --size=8G --rw=write --bs=1M --iodepth=8 --runtime=60 --time_based $COMMON
```

## 测量 1：45 分钟的 4k 随机读取：积分骤降

![IOPS 时间序列：gp3 在 10 分钟内保持平稳的 3,000 IOPS；gp2 保持 3,000 IOPS，之后在 1,999 秒时垂直降至 300 IOPS。](../.gitbook/assets/en-storage-01-ebs-gp2-gp3-iops-timeline.svg)

这是 fio 记录的每秒 IOPS 日志（gp2 有 2,699 个样本，gp3 有 600 个），按原样绘制。下表排除了每份日志的第一个一秒样本（两个卷均为 5,997，这是一个需要单独追踪原因的初始瞬态；纳入该样本可能改变汇总平均值）。

| | gp3（600 秒） | gp2 骤降前（0–1,999 秒） | gp2 骤降后（2,000–2,700 秒） |
|---|---|---|---|
| 平均 IOPS | **3,001** | **3,001** | **300** |
| 最小值 / 最大值 | 2,991 / 3,004 | 2,997 / 3,005 | 297 / 304 |
| 平均延迟（qd32） | 10.4 ms | ≈10.4 ms | ≈106 ms |

如何解读：

- **骤降前，gp2 与 gp3 难以区分**。两者都能提供 3,001 IOPS，p50 都在 10.0–10.2 ms 之间。“gp2 很慢”在这里完全不成立：有积分的 gp2 卷就是一个 3,000 IOPS 的卷。
- **骤降只用了一秒**。1,998 秒时为 3,001 IOPS，1,999 秒时为 2,659，2,000 秒时为 300。它不是逐步退化；90% 的性能仿佛开关一拨就消失了。从应用角度看，这种故障模式就像“数据库查询突然慢了 10 倍，但没人部署过任何东西”。
- **数据与 AWS 文档吻合，误差在一秒以内**。100 GiB gp2 卷的基准为 3 IOPS/GiB × 100 = **300 IOPS**，积分桶容量为 5.4M，突发时长为 `5,400,000 ÷ (3,000 − 300) = 2,000 s`。AWS 表格列出“100 GiB → 2,000 秒”；我们测得 1,999 秒。
- **106 ms 延迟并不代表卷本身很慢**。Little 定律（平均延迟 = 未完成 I/O 数 ÷ 吞吐量）计算得出 32 ÷ 300 = 106.7 ms。我们让 32 个 I/O 同时在途，但每秒只有 300 个完成，因此队列不断增长。3,000 IOPS 时的 10.4 ms 也是同样的计算结果（32 ÷ 3,000 = 10.7 ms）。**当平均在途 I/O 数约为 32 时，这可以近似表示总响应时间，但无法将排队时间与服务时间区分开来**。比较不同运行中的相同 fio `slat`、`clat` 或 `lat` 指标。

> **测试条件披露**：记录的测试运行开始前约 13 分钟，第一次尝试（因 Karpenter 驱逐而提前中止）已让同一个 gp2 卷以 3,000 IOPS 运行了约 8 分钟（UTC 时间 14:55–15:03）。简单的积分模型表明，预先消耗积分应该会让骤降时间早于 2,000 秒；但我们观测到的骤降时间是 2,000 秒。我们无法查明原因（驱逐前实际 I/O 持续时间并不确定）。请将**本次运行报告的骤降形态（一秒内下降 90%）和性能底限**（300 IOPS）视为测试结果，并**使用 AWS 公式（2,000 秒）作为精确持续时间的规划值**。

## 测量 2：积分耗尽后的随机写入：3,025 对 601 IOPS

| 4k 随机写入，qd32，120 秒 | gp3 | gp2（刚耗尽积分后） |
|---|---|---|
| IOPS | **3,025** | **601** |
| 平均延迟 | 10.3 ms | 52.0 ms |
| p50 / p95 / p99 | 10.2 / 11.2 / 12.0 ms | 11.1 / 109.6 / 133.7 ms |

这里真正值得注意的是 gp2 为什么达到 601 IOPS，而不是其 300 IOPS 的基准值。在 gp2 写入测试之前的 120 秒里（gp3 写入测试运行期间），gp2 处于空闲状态，积累了 **300 积分/秒 × 120 秒 = 36,000 积分**。在 120 秒测试期间用掉这 36,000 积分，相当于在 300 IOPS 的基准值上增加 300 IOPS，恰好是**600 IOPS**。实测结果：601。

因此，gp2 积分桶并非“耗尽后就永远为空”，它是**一笔在卷空闲时缓慢回补的银行存款**。这就是为什么间歇性流量下的 gp2 会“时快时慢”，而且这种模式很难调试，因为它很少会按需复现。双峰分布（p50 为 11 ms，p95 为 110 ms）就是其特征：剩余积分的时段速度很快，没有积分的时段则会排队。

## 测量 3：qd1 延迟：低并发下的分布

队列深度为 1 会降低应用产生的并发。内核、虚拟化、EBS 服务和限流延迟仍可能产生影响；这并不是对物理 SSD 本身的测量。

| 4k 随机读取，qd1，60 秒 | gp3 | gp2（受限流） |
|---|---|---|
| 平均延迟 | **0.564 ms** | 1.651 ms |
| p50 | 0.569 ms | **0.602 ms** |
| p95 | 0.627 ms | 3.391 ms |
| p99 | 0.872 ms | 3.555 ms |
| 实际达到的 IOPS | 1,759 | 603 |

- **gp3 的 0.56 ms（p99 为 0.87 ms）是此环境中 EBS 通用型 SSD 的实际往返时间**。在 qd1 下，1,759 IOPS 低于 3,000 的上限，因此没有发生限流，吞吐量完全由延迟决定（1 ÷ 0.564 ms ≈ 1,773）。
- **看 gp2 的 p50：0.602 ms**。它有一半 I/O 的速度与 gp3 完全相同。p50 值相似并不能证明物理设备或服务内部实现相同。另一半 I/O 的延迟为 3.4–3.6 ms，因为超过每秒允许值的 I/O（603 IOPS；与测量 2 的计算方式相同：60 秒空闲期间积累了 18,000 积分，再加上 300 IOPS 的基准值）被滞留在限流队列中。
- 实际结论：**限流体现在分布形态中，而非平均值中**。如果仪表板只显示平均延迟，读数会是 1.6 ms（“稍微慢一点”），但 p95 已经上升了 6 倍。这就是为什么存储仪表板需要在 p95/p99 旁边显示 p50。

## 测量 4：1 MiB 顺序 I/O：两者都达到 125–128 MiB/s 上限

| 1 MiB 顺序 I/O，qd8，60 秒 | gp3 读取 | gp3 写入 | gp2 读取 | gp2 写入 |
|---|---|---|---|---|
| 吞吐量 | 127.3 MiB/s | 126.0 MiB/s | 130.3 MiB/s | 128.9 MiB/s |
| 平均延迟 | 58.0 ms | 58.5 ms | 56.7 ms | 57.3 ms |

在这里，gp2 和 gp3 的表现实际上相同。gp3 在其 125 MiB/s 基准值处达到上限；gp2 则在 128 MiB/s 处达到上限，这是容量不超过 170 GiB 的卷的上限。计算结果还解释了为什么 gp2 的顺序测试没有因积分桶为空而变慢：EBS 会将一个 1 MiB I/O 计为四个 256 KiB 操作，因此 130 MiB/s ≈ 520 IOPS，远低于前面 120 秒空闲期间积累的 36,000 积分。吞吐量上限先于 IOPS 上限触发。

还有一点：此节点（m5.xlarge）的实例级 EBS 带宽基准为 1,150 Mbps ≈ **137 MiB/s**。当实例突发容量可用时，配置为 250 MiB/s 的 gp3 卷可以超过 137 MiB/s。**规划长期持续需求时，应以约 137 MiB/s 的基准值为准**。AWS 规定每 24 小时至少一次可维持最大性能 30 分钟，但这并不代表恰好 30 分钟的固定额度。升级卷之前，请先查看实例规格表中的 EBS 带宽一栏。[ClickHouse 基准测试](../database/01-clickhouse-on-eks.md)中的全表扫描也因同样的原因，恰好停滞在 125–137 MiB/s 区间。

## 成本对比

按首尔区域的价格计算（Pricing API，2026 年 9 月），“如何获得 3,000 IOPS”这个问题没有任何理由让你继续使用 gp2。

| 配置 | 月成本 | 可持续 IOPS | 吞吐量 |
|---------------|--------------|------------------|------------|
| gp2 100 GiB | $11.40 | **300**（最多突发 33 分钟，达到 3,000） | 128 MiB/s |
| gp3 100 GiB（默认） | **$9.12** | **3,000**，无限时 | 125 MiB/s |
| gp3 100 GiB + 6,000 IOPS | $26.22（$9.12 + 3,000 × $0.0057） | 6,000 | 125 MiB/s |
| gp3 100 GiB + 250 MiB/s | $14.82（$9.12 + 125 × $0.0456） | 3,000 | 250 MiB/s |
| gp2 1,000 GiB（为 IOPS 而扩容的卷） | $114.00 | 3,000 | 250 MiB/s |

最后一行是实际中最常见的浪费。在 gp2 时代，为需要 IOPS 的 100 GiB 数据集分配 1,000 GiB 是常见做法。gp3 100 GiB 能以 **$9.12** 的价格提供同样的 3,000 IOPS，便宜 12.5 倍（$114.00 ÷ $9.12）。将 IOPS 与容量解耦正是 gp3 的核心，而这张表正是其结果。

## 在 Kubernetes 上迁移到 gp3

### 新建卷：将 gp3 设为默认 StorageClass

默认 StorageClass 会因集群版本和配置方式而异。请使用 `kubectl get storageclass -o yaml` 检查 provisioner、类型和默认注解。以下是常规 EBS CSI 示例；如有现存默认类，请明确调整。

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: gp3
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

```bash
# Run only if gp2 actually exists and is the default.
kubectl annotate storageclass gp2 storageclass.kubernetes.io/is-default-class="false" --overwrite
kubectl apply -f gp3-storageclass.yaml
```

### 现有 PVC：通过 VolumeAttributesClass 原地更改

`VolumeAttributesClass`（`storage.k8s.io/v1`，自 Kubernetes 1.34 起正式可用）可以更改卷的类型，而无需删除 PVC。EBS CSI driver 支持 `type`、`iops` 和 `throughput` 参数，并在底层调用 EBS Elastic Volumes（`ModifyVolume`），因此 Pod 可以继续运行。

```yaml
apiVersion: storage.k8s.io/v1
kind: VolumeAttributesClass
metadata:
  name: gp3-baseline
driverName: ebs.csi.aws.com
parameters:
  type: gp3
```

将上面的 VAC 保存为 `gp3-baseline-volumeattributesclass.yaml`。使用 `kubectl api-resources --api-group=storage.k8s.io` 检查 API 发现情况，并安装兼容版本的 EBS CSI/external-provisioner/resizer。选择 PVC 所在的 namespace。只指定类型可能会保留 gp2 原有的较高吞吐量，而不是将其降至 gp3 基准值，并因此产生额外费用。

```bash
kubectl apply -f gp3-baseline-volumeattributesclass.yaml
kubectl patch pvc data-postgres-0 --type=merge -p '{"spec":{"volumeAttributesClassName":"gp3-baseline"}}'
kubectl get pvc data-postgres-0 -o jsonpath='{.status.currentVolumeAttributesClassName}'
```

有两点需要注意：EBS 要求同一个卷的每次修改都达到 `completed` 状态后，才能开始下一次修改（1 TiB 的卷通常最多需要六小时，但完成时间尽力而为）；并且**每个卷在滚动的 24 小时内最多允许四次修改**，因此应将类型、IOPS 和吞吐量的修改合并为一次请求。另外，在 Kubernetes 1.31–1.33 上，请确认发行版的 `v1beta1` API 以及控制平面/sidecar 的 feature-gate 配置。直接调用 ModifyVolume 和使用 VAC 都不会自动更改现有的 `storageClassName`。请通过 PVC/VAC 管理目标属性，并检查 PVC 修改状态以及实际 EBS 类型/IOPS/吞吐量。

### 为所有剩余 gp2 设置告警

迁移完成前，请针对 CloudWatch EBS 指标 **`BurstBalance`**（剩余积分百分比）设置告警。对于本文中的 gp2 卷，15% 大约相当于以恒定 3,000 IOPS 运行五分钟；请考虑实际消耗情况、告警评估周期和缺失数据。性能骤降毫无预警，但积分余额会提前示警。

## 如何复现

1. 应用上述清单：`kubectl apply -f bench-storage.yaml`，然后运行 `kubectl wait -n bench-storage pod/fio --for=condition=Ready --timeout=300s`。
2. 将 fio 命令块放入 Pod 内的 shell 脚本中，并使用 `nohup` 运行，结果写入卷（`/mnt/gp3/results`）。不要假设 `kubectl exec` 能持续 45 分钟，而且 Pod 的 `/tmp` 会随 Pod 一起消失。
3. 直接绘制 `--write_iops_log` 的输出（`*_iops.1.log`，格式为 `time_ms, iops, ...`），生成 IOPS 时间序列图。
4. 删除专用的 `bench-storage` namespace 之前，请将原始 JSON、IOPS 日志、CloudWatch 时间序列以及 PVC/EBS 设置导出到集群外部。此示例使用 Delete reclaimPolicy，因此数据也会被删除。请单独删除集群级别的 `bench-gp2`/`bench-gp3` StorageClass。费用取决于实际的节点、卷、EKS 控制平面和网络用量，也包括测试结束后资源继续保留期间产生的费用。

## 注意事项

- **单个卷，单次运行**。AWS 对 gp2 和 gp3 的设计目标都是“99% 的时间内提供预置性能”，因此不同日期的不同卷，其 IOPS 可能会有几个百分点的偏差。本文关注的是**积分模型的形态**，而非绝对数值。
- 有关骤降测量之前 gp2 卷曾经承受的负载，请参阅测量 1 中的条件披露。
- `direct=1` 会绕过页缓存。真实数据库有缓冲池和操作系统缓存，因此可以用少得多的 IOPS 运行；这也正是 gp2 的骤降只“偶尔”出现、且需要很长时间才能诊断的原因。
- 容量大于 100 GiB 的 gp2 卷有更高的基准值（334 GiB → 1,002 IOPS），而容量达到 1,000 GiB 及以上时，基准值至少为 3,000 IOPS，因此不会发生骤降。本文结论适用于**基准 IOPS 低于 3,000 的 gp2 卷**。

## 延伸阅读

- [存储概述](./README.md)：如何选择 EKS 存储，以及本基准测试的适用场景
- [EKS 存储第 1 部分](../eks/04-eks-storage-part1.md)：EBS CSI driver 安装和 StorageClass 基础知识
- [EKS 上的 ClickHouse 实测基准测试](../database/01-clickhouse-on-eks.md)：本文中的 125 MiB/s 吞吐量上限如何体现在真实数据库的全表扫描中

## 参考资料

- [EBS gp2/gp3 性能](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html)
- [EC2 EBS 优化带宽](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html)
- [EBS 修改注意事项](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-modify-volume.html)
- [VolumeAttributesClass](https://kubernetes.io/docs/concepts/storage/volume-attributes-classes/)
- [EBS CSI 卷修改](https://github.com/kubernetes-sigs/aws-ebs-csi-driver/blob/master/docs/modify-volume.md)
- [Karpenter 干扰](https://karpenter.sh/docs/concepts/disruption/)
- [fio 延迟定义](https://github.com/axboe/fio/blob/master/HOWTO.rst)
- [Alpine 发行版支持](https://alpinelinux.org/releases/)
