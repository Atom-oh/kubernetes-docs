# 资源优化测验

> **相关文档**: [资源优化](../../ops/10-resource-optimization.md)

## 单项选择题

### 1. Kubernetes 中 resource requests 和 limits 有什么区别？

- A) Requests 仅用于 CPU，limits 仅用于 memory
- B) Requests 是用于调度的保证资源；limits 是允许的最大值
- C) Requests 和 limits 是同一回事
- D) Limits 是保证资源，requests 是可选的

<details>
<summary>显示答案</summary>

**答案: B) Requests 是用于调度的保证资源；limits 是允许的最大值**

**解释:**
Requests 是 Kubernetes 保证给 container 并用于调度决策的资源。Limits 是 container 可使用的最大资源。超过 CPU limits 会导致 throttling；超过 memory limits 可能导致 OOM kills。

</details>

### 2. 在 node 资源压力下，哪个 QoS class 的优先级最高？

- A) BestEffort
- B) Burstable
- C) Guaranteed
- D) 所有 class 的优先级相同

<details>
<summary>显示答案</summary>

**答案: C) Guaranteed**

**解释:**
Guaranteed pods（CPU 和 memory 的 requests=limits）拥有最高优先级，在资源压力下最后被驱逐。BestEffort pods（无 requests/limits）最先被驱逐，其次是 Burstable pods。

</details>

### 3. Kubernetes containers 中 CPU throttling 的原因是什么？

- A) memory 不足
- B) Container 在 CFS 周期内超过其 CPU limit
- C) 网络拥塞
- D) 磁盘 I/O 瓶颈

<details>
<summary>显示答案</summary>

**答案: B) Container 在 CFS 周期内超过其 CPU limit**

**解释:**
Linux CFS (Completely Fair Scheduler) 会在 100ms 周期内强制执行 CPU limits。如果 container 在周期早期就用完配额，它会被 throttled（暂停），直到下一个周期开始。这会记录在 `cpu.cfs_throttled_us` 中。

</details>

### 4. 对于 containers，推荐的 JVM MaxRAMPercentage 设置是多少？

- A) 100%
- B) 90%
- C) 75%
- D) 50%

<details>
<summary>显示答案</summary>

**答案: C) 75%**

**解释:**
将 MaxRAMPercentage 设置为 75%，会为非堆使用保留 25% 的 container memory：metaspace、thread stacks、native memory 和 OS overhead。使用更高的值会在非堆 memory 意外增长时增加 OOM kills 的风险。

</details>

### 5. 在 VPA 中，“Initial” update mode 做什么？

- A) 持续更新 pods
- B) 仅在 pods 首次创建时设置资源
- C) 删除所有现有 pods
- D) 完全禁用 VPA

<details>
<summary>显示答案</summary>

**答案: B) 仅在 pods 首次创建时设置资源**

**解释:**
“Initial” mode 仅在 pod 创建时应用 VPA 建议，而不会应用到正在运行的 pods。这与 HPA 搭配使用很有用，因为它避免了冲突 - VPA 设置初始大小，HPA 处理扩缩容，现有 pods 不会被中断。

</details>

### 6. 应根据 container CPU limits 配置哪个 Go runtime 设置？

- A) GOGC
- B) GOMAXPROCS
- C) GOPATH
- D) GOROOT

<details>
<summary>显示答案</summary>

**答案: B) GOMAXPROCS**

**解释:**
GOMAXPROCS 控制执行 Go code 的 OS threads 数量。默认情况下，Go 使用所有 host CPUs，而不是 container limits。将 GOMAXPROCS 设置为匹配 container CPU limits（使用 automaxprocs library）可防止过多的 context switching。

</details>

### 7. GOMEMLIMIT 在 Go applications 中用于什么？

- A) 设置最小 memory allocation
- B) 向垃圾回收器提供软 memory limit 提示
- C) 限制 goroutines 数量
- D) 配置 swap memory

<details>
<summary>显示答案</summary>

**答案: B) 向垃圾回收器提供软 memory limit 提示**

**解释:**
GOMEMLIMIT 告诉 Go garbage collector 目标 memory ceiling。当 memory 接近此 limit 时，GC 会更早触发，从而降低 OOM kills 的风险，同时仍能高效利用可用 memory。

</details>

### 8. 对于 containers 中的 Python Gunicorn workers，推荐的 worker count 公式是什么？

- A) 2 * CPU_CORES + 1
- B) 基于 container CPU limit，而不是 host cores
- C) 始终使用 1 个 worker
- D) 使用 100 个 workers 以获得最大吞吐量

<details>
<summary>显示答案</summary>

**答案: B) 基于 container CPU limit，而不是 host cores**

**解释:**
经典公式 (2*cores+1) 使用 host CPU count，这在 containers 中会导致 oversubscription。Worker count 应基于 container CPU limits（例如，每个 CPU limit 配置 2-4 个 workers），以避免资源争用和 OOM 问题。

</details>

### 9. 超过 memory limit 的 container 会发生什么？

- A) 它会被 CPU throttled
- B) 它会被 kernel OOM killed
- C) 它会自动水平扩缩容
- D) memory 会从其他 containers 借用

<details>
<summary>显示答案</summary>

**答案: B) 它会被 kernel OOM killed**

**解释:**
与 CPU（会被 throttled）不同，memory limits 是硬性强制执行的。当 container 超过其 memory limit 时，Linux OOM killer 会终止 container 中的进程。Kubernetes 随后会根据其 restart policy 重启 container。

</details>

### 10. VPA Recommender 组件的目的是什么？

- A) 使用新资源重启 pods
- B) 分析资源使用情况并生成资源建议
- C) 管理 node scaling
- D) 验证资源配置

<details>
<summary>显示答案</summary>

**答案: B) 分析资源使用情况并生成资源建议**

**解释:**
VPA Recommender 会随时间观察 containers 的实际资源使用情况，并为 requests 和 limits 生成建议。它会考虑 CPU 和 memory 使用模式、峰值和变化情况，以建议合适的值。

</details>
