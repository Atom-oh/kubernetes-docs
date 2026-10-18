# 资源优化测验

> **相关文档**：[资源优化](../../ops/10-resource-optimization.md)

## 1. 哪项陈述正确描述了内存压力下的驱逐？

- A) 仅 QoS 类别决定驱逐顺序
- B) 超出 requests 的用量、Pod Priority 和相对用量都会产生影响
- C) Guaranteed Pod 永远不会被驱逐
- D) PDB 会阻止所有节点压力驱逐

<details>
<summary>显示答案</summary>

**答案：B**

QoS 很有用，但它并非绝对的驱逐顺序。要区分容器限制导致的 OOM、内存压力驱逐和 DiskPressure。

</details>

## 2. CPU throttled-period ratio 衡量的是什么？

- A) CPU 时间损失的精确比例
- B) 出现 throttling 的配额周期所占比例
- C) CPU request 利用率
- D) 平均内存利用率

<details>
<summary>显示答案</summary>

**答案：B**

线程共享配额。仅凭周期比例无法确定损失的时间，也不能证明提高限制就是正确的修复方法。

</details>

## 3. 关于 JVM 堆和容器内存，哪项陈述正确？

- A) 75% 始终是最佳值
- B) 选择比例时要测量非堆内存和 RSS
- C) MaxRAMPercentage 始终会立即响应 Pod 限制的变更
- D) 内核 SIGKILL 始终会生成堆转储

<details>
<summary>显示答案</summary>

**答案：B**

Metaspace、栈、直接缓冲区和 JNI 都需要内存。要区分 JVM ergonomics 与 cgroup 限制，以及 Java OOME 与 SIGKILL。

</details>

## 4. 为什么设置 JAVA_OPTS 可能不会应用 JVM 选项？

- A) 这是 JVM 必须拒绝的安全选项
- B) 除非 entrypoint 将其传递给 JVM，否则 JVM 不会自动读取它
- C) Kubernetes 不支持环境变量
- D) Java 21 无法在容器中运行

<details>
<summary>显示答案</summary>

**答案：B**

使用 JAVA_TOOL_OPTIONS 或显式的 java 参数，并检查实际的 VM.flags 输出。

</details>

## 5. 关于 VPA upperBound，哪项陈述正确？

- A) 始终将其复制到容器内存限制
- B) 它属于 request 建议范围，而不是容器限制
- C) 它是 HPA 的最大副本数
- D) 它是确保不会发生 OOM 的内存量

<details>
<summary>显示答案</summary>

**答案：B**

要区分 target、lowerBound、upperBound 和 uncappedTarget。Initial 模式仍可能通过新的 requests 影响 HPA 的分母。

</details>

## 6. 关于 Go 1.25+ 的默认 GOMAXPROCS，哪项陈述正确？

- A) 它始终使用主机 CPU 数量，并且需要外部库
- B) 在语言版本/兼容性默认设置的约束下，它会考虑配额和 CPU 亲和性；显式设置会停用自动更新
- C) 它只使用 CPU requests
- D) 在所有环境中，500m 始终会产生 1

<details>
<summary>显示答案</summary>

**答案：B**

此示例使用 Go 1.27.2 和 go.mod 1.25+ 进行了测试。配额取整和最小值条件都很重要。

</details>

## 7. GOMEMLIMIT 和 Node 的 old-space 限制有什么共同的局限？

- A) 它们无法完全限制进程 RSS
- B) 它们会强制释放所有原生内存
- C) 它们能保证避免容器 OOM
- D) 它们会自动更改 Pod requests

<details>
<summary>显示答案</summary>

**答案：A**

Go 的值是由运行时管理的软限制；Node 的选项控制 V8 old space。要单独考虑原生内存分配和多个 worker。

</details>

## 8. 应如何选择 Gunicorn/Tokio worker 数量？

- A) 固定使用主机 CPU 数量的某个倍数就足够了
- B) 验证实际设置，并测试配额、内存和工作负载行为
- C) Rust 不需要并发限制，因为它没有 GC
- D) 线程/进程数量不会影响内存

<details>
<summary>显示答案</summary>

**答案：B**

配置必须实际读取 WEB_CONCURRENCY。显式设置的 Tokio worker_threads 会覆盖环境变量；blocking pool 是独立的。

</details>

## 9. 应如何解读 OOM reason 和 Pending phase 指标？

- A) 对 reason gauge 应用 increase，以获得精确的 OOM 计数
- B) 统计所有 Pending 序列，以得出当前 Pending 数量
- C) 评估 0/1 值，并保留 reason gauge 只能反映最后状态这一限制
- D) Pending 始终意味着 CPU 不足

<details>
<summary>显示答案</summary>

**答案：C**

Pending 序列也可能取值为零。结合近期重启情况和最后一次 OOM reason，无法还原该时间段内的每次 OOM。

</details>

## 10. 关于 Auto Mode 装箱和占位 Pod，哪项陈述正确？

- A) 4-vCPU 实例始终能容纳 4 CPU 的应用 requests
- B) 占位 Pod 是 EC2 Capacity Reservation
- C) 要考虑 allocatable、开销和调度约束；占位 Pod 不能保证容量
- D) preemptionPolicy Never 会阻止该 Pod 被抢占

<details>
<summary>显示答案</summary>

**答案：C**

Never 会阻止此 Pod 抢占其他 Pod。NodePool 使用 karpenter.sh/v1；Auto Mode NodeClass 的组是 eks.amazonaws.com。

</details>
