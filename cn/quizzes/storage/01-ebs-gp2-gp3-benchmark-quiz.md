# EBS gp2 与 gp3 实测基准测验

1. 在持续 4k 随机读取（qd32）下，100 GiB gp2 卷的实测 IOPS 表现如何？
   - A) 从一开始就平稳地维持在约 300 IOPS
   - B) 它在约 33 分钟（1,999 s）内以 3,001 IOPS 与 gp3 持平，随后在一秒内降至 300 IOPS
   - C) 它从 3,000 IOPS 开始，并在 45 分钟内逐渐降至 300 IOPS
   - D) 它在完整的 45 分钟内保持 3,000 IOPS
<details>
<summary>显示答案</summary>

**答案：B) 它在约 33 分钟（1,999 s）内以 3,001 IOPS 与 gp3 持平，随后在一秒内降至 300 IOPS**

**说明：**
fio 的每秒 IOPS 日志记录显示：在 1,998 s 时为 3,001，在 1,999 s 时为 2,659，在 2,000 s 时为 300。只要积分仍然存在，gp2 与 gp3 就没有区别；积分耗尽的瞬间，90% 的容量仿佛开关被切断一样消失。准确的说法不是“gp2 很慢”，而是“gp2 会突然变慢”。

</details>

2. 为什么 100 GiB gp2 卷的突发持续时间计算为约 2,000 秒？
   - A) 5,400,000 积分 ÷ (3,000 − 300) IOPS = 2,000 s
   - B) 100 GiB × 20 s/GiB = 2,000 s
   - C) 3,000 IOPS ÷ 1.5 = 2,000 s
   - D) 无论卷大小如何，AWS 都将其固定为 2,000 s
<details>
<summary>显示答案</summary>

**答案：A) 5,400,000 积分 ÷ (3,000 − 300) IOPS = 2,000 s**

**说明：**
gp2 的基线为 3 IOPS/GiB（100 GiB → 300 IOPS），并具有一个 540 万积分的积分池。在 3,000 IOPS 下突发时，扣除基线补充的 300 后，每秒消耗 2,700 积分，因此 5,400,000 ÷ 2,700 = 2,000 s。更大的卷具有更高的基线且耗尽得更慢；在 1 TiB 及以上时，基线已达到 3,000，因此不会出现断崖式下降。

</details>

3. 积分耗尽后，gp2 的 qd32 平均延迟实测约为 106 ms。哪种解释正确？
   - A) EBS 设备的响应时间变得比 100 ms 更慢
   - B) 根据 Little 定律，32 个未完成的 I/O ÷ 300 IOPS ≈ 106.7 ms——这是在队列中等待的时间
   - C) 网络延迟激增
   - D) 这是 fio 测量错误
<details>
<summary>显示答案</summary>

**答案：B) 根据 Little 定律，32 个未完成的 I/O ÷ 300 IOPS ≈ 106.7 ms——这是在队列中等待的时间**

**说明：**
平均延迟 = 未完成的 I/O ÷ 吞吐量。在仅每秒完成 300 个 I/O 的同时保持 32 个 I/O 在途，意味着每个 I/O 平均等待 106.7 ms。在 3,000 IOPS 下的 10.4 ms 也是同样的计算（32 ÷ 3,000 = 10.7 ms）。qd32 基准中的延迟是排队时间；设备延迟则是 qd1 测量显示的结果（gp3：0.56 ms）。

</details>

4. 为什么 gp2 在积分耗尽后立即运行的 120 秒随机写入测试，测得的是 601 IOPS 而非 300？
   - A) 写入不会消耗积分
   - B) 在此前 120 s 的静置期间，gp2 累积了 300 积分/s × 120 s = 36,000 积分，这在 120 秒测试中额外增加了 300 IOPS
   - C) fio 将写入 IOPS 计算了两次
   - D) gp2 的写入基线是其读取基线的两倍
<details>
<summary>显示答案</summary>

**答案：B) 在此前 120 s 的静置期间，gp2 累积了 300 积分/s × 120 s = 36,000 积分，这在 120 秒测试中额外增加了 300 IOPS**

**说明：**
gp2 的积分池耗尽后不会永远为空；它像一个银行账户，只要卷处于静置状态，就会以 3 积分/GiB/s（100 GiB → 300/s）的速率补充。在 120 s 内消耗 36,000 积分，会在 300 的基线上恰好增加 300 IOPS，达到 600（实测：601）。qd1 测试中的 603 IOPS 也遵循相同的计算方式，即在 60 秒静置期间累积了 18,000 积分。这就是为什么 gp2 在间歇性流量下会“有时很快，有时很慢”。

</details>

5. 在 qd1 4k 随机读取测试中，受限的 gp2 显示 p50 为 0.602 ms、p95 为 3.391 ms。这个分布说明了什么？
   - A) gp2 设备从根本上比 gp3 更慢
   - B) 设备与 gp3 相同（p50 几乎等于 gp3 的 0.569 ms），但超出每秒限额的 I/O 在限流队列中等待，产生了双峰分布
   - C) 测试期间另一个 Pod 共享了该卷
   - D) 随机读取始终会呈现双峰分布
<details>
<summary>显示答案</summary>

**答案：B) 设备与 gp3 相同（p50 几乎等于 gp3 的 0.569 ms），但超出每秒限额的 I/O 在限流队列中等待，产生了双峰分布**

**说明：**
gp2 中一半的 I/O 在 0.6 ms 内完成，与 gp3 完全相同。另一半则为 3.4–3.6 ms，因为超出每秒限额（约 603 IOPS）的 I/O 被保留在限流队列中。仅看平均值会显示 1.65 ms——“稍微慢一点”——而 p95 却增长了 6 倍。这就是为什么存储仪表板需要同时展示 p50 和 p95/p99。

</details>

6. 为什么 gp2 和 gp3 在 1 MiB 顺序读取/写入测试中都停在 125–130 MiB/s？
   - A) gp3 达到了其 125 MiB/s 基线，而 gp2（≤170 GiB）达到了其 128 MiB/s 上限；两个值恰好接近
   - B) m5.xlarge 实例的网络带宽限制
   - C) fio 的 iodepth=8 是瓶颈
   - D) gp2 的积分耗尽，并使两个卷都变慢
<details>
<summary>显示答案</summary>

**答案：A) gp3 达到了其 125 MiB/s 基线，而 gp2（≤170 GiB）达到了其 128 MiB/s 上限；两个值恰好接近**

**说明：**
gp3 的默认吞吐量为 125 MiB/s；对于 170 GiB 或更小的卷，gp2 的上限为 128 MiB/s。gp2 的空积分池没有降低顺序测试速度，因为 EBS 将一个 1 MiB I/O 计作四个 256 KiB 操作，因此 130 MiB/s 仅约为 520 IOPS——完全处于此前静置期间累积的 36,000 积分范围内。吞吐量上限先于 IOPS 上限生效。请注意，m5.xlarge 实例的 EBS 带宽（≈137 MiB/s）略高，因此不是此处的瓶颈；但即使将 gp3 提高到 250 MiB/s，在该实例上仍会停在接近 137 MiB/s 的水平。

</details>

7. 对于需要持续 3,000 IOPS 的 100 GiB 数据集，哪种成本比较（首尔区域）是正确的？
   - A) gp2 100 GiB（$11.40）已足够
   - B) gp3 100 GiB（$9.12）可无限制提供 3,000 IOPS，而在 gp2 上获得相同基线需要 1 TiB（$114.00）——大约相差 12 倍
   - C) gp3 需要额外付费的 IOPS，因此成本高于 gp2
   - D) 两种卷每月的成本相同
<details>
<summary>显示答案</summary>

**答案：B) gp3 100 GiB（$9.12）可无限制提供 3,000 IOPS，而在 gp2 上获得相同基线需要 1 TiB（$114.00）——大约相差 12 倍**

**说明：**
$11.40 的 gp2 100 GiB 仅保证持续 300 IOPS（3,000 IOPS 的突发最多持续 33 分钟）。在 gp2 时代，标准做法是为了 IOPS 将卷扩容至 1 TiB，成本为 $114.00。gp3 将 IOPS 与容量解耦，并以 $9.12 为 100 GiB 提供相同的 3,000 IOPS。如有需要，还可单独购买 6,000 IOPS（+$17.10）或 250 MiB/s（+$5.70）。

</details>

8. 在不重启 Pod 的情况下，将具有数据的现有 gp2 PVC 转换为 gp3 的 Kubernetes 原生方式是什么？
   - A) 将 StorageClass 的 `type` 参数编辑为 gp3，现有 PV 将自动更改
   - B) 创建一个 `VolumeAttributesClass`（storage.k8s.io/v1，在 Kubernetes 1.34 中 GA），并设置 PVC 的 `volumeAttributesClassName`；EBS CSI driver 调用 ModifyVolume
   - C) 删除 PVC，然后使用 gp3 StorageClass 重新创建它
   - D) 在节点上运行 `aws ec2 modify-volume` 是唯一选项
<details>
<summary>显示答案</summary>

**答案：B) 创建一个 `VolumeAttributesClass`（storage.k8s.io/v1，在 Kubernetes 1.34 中 GA），并设置 PVC 的 `volumeAttributesClassName`；EBS CSI driver 调用 ModifyVolume**

**说明：**
StorageClass 参数仅在创建新卷时应用；现有 PV 不受影响。VolumeAttributesClass 让你可以在 Pod 运行时更改 `type`、`iops` 和 `throughput`，底层使用 EBS Elastic Volumes。注意事项：同一个卷的下一次修改之前，每次修改都必须达到 `completed` 状态（1 TiB 卷最长可达六小时），并且 EBS 在滚动的 24 小时内每个卷最多允许四次修改，因此应将类型、IOPS 和吞吐量更改批量合并到一个请求中；Kubernetes 1.31–1.33 则需要 v1beta1 API 和一个 feature gate。直接运行 `aws ec2 modify-volume` 也可以，但 PV 对象会保留 `gp2` 作为其 StorageClass 名称，这会在之后造成困惑。

</details>
