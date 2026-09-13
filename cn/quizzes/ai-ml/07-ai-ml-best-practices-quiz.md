# AI/ML 最佳实践测验

关于度量、恢复和当前 API 的 15 道问题。

## 1. TTFT 度量的是什么，它在什么情况下无法获得？

<details>
<summary>答案与说明</summary>

从请求发出到首个非空输出的时间。首个 HTTP 帧与首个 token 可能并不一致；非流式响应无法度量真实的 TTFT/ITL。需要明确 tokenizer、失败情况和预热边界。
</details>

## 2. 组合使用启动优化是否总能带来 80–95% 的提升？

<details>
<summary>答案与说明</summary>

不是。应分别度量镜像拉取/解包、模型下载/加载、readiness 以及节点准备。评估 prefetch/lazy-loading 的开销、缓存和全量权重读取，而不是套用固定的节省比例。
</details>

## 3. 如何为大规模分布式训练选择 GPU？

<details>
<summary>答案与说明</summary>

需要确认具体实例规格的设备数/显存、CPU/RAM/网络、模型状态/激活值、通信、价格和配额。实例族名称并不能确定 GPU 数量，也不能证明某个选择在所有场景下最优。
</details>

## 4. EFA 和放置组（placement group）是否总是必需的？

<details>
<summary>答案与说明</summary>

EFA 是面向合适工作负载的高性能通道，并非每个 DDP 的前提条件。EFA 通信要求处于同一可用区（AZ）；为获得性能，建议使用 cluster placement group。需要验证驱动/插件/安全组/网络接口。
</details>

## 5. 超过 10TB 的数据集是否一定需要 FSx？

<details>
<summary>答案与说明</summary>

不存在依靠单一容量阈值即可决定的做法。应比较 I/O、并发、元数据、延迟、持久性、挂载语义和成本。需要区分 EFS/FSx/S3/instance store 以及当前 gp3 的限制。
</details>

## 6. 仅凭温度能否判定发生了降频（throttling）或硬件故障？

<details>
<summary>答案与说明</summary>

不能。应检查具体设备的限制、时钟频率、功耗、降频原因和工作负载。DCGM FB_USED 的单位是 MiB，XID_ERRORS 反映的是最后一个错误码；并非每个 XID 都意味着硬件故障。
</details>

## 7. 对于 Spot 推理，120 秒宽限期加上一次 drain 调用是否足够？

<details>
<summary>答案与说明</summary>

EC2 并不总能保证 120 秒，也不能假定存在任意的 vLLM/drain API。需要测试网关的 readiness、SIGTERM、流式响应、重试、重复请求和缓存重新加载。
</details>

## 8. 平均 ITL 如何计算？

<details>
<summary>答案与说明</summary>

需要真实的 token 时间戳且至少有两个 token：(last-first)/(tokens-1)。要考虑一次返回多个 token 的分块以及空输出/单 token 输出；同时区分特定工具对 TPOT 的定义。
</details>

## 9. 饱和测试能够说明什么？

<details>
<summary>答案与说明</summary>

说明吞吐、延迟、错误和 goodput 随负载的变化。它本身并不能证明存在 CPU/GPU/内存瓶颈。需要区分到达率与并发度，并检查客户端、profiling 和队列。
</details>

## 10. SOCI 0.15 standalone 模式使用什么作为输入？

<details>
<summary>答案与说明</summary>

本地 OCI image-layout 目录/归档文件，而不是通用的 docker-save tar 包。convert --standalone 不需要 containerd；实际的 lazy-start 收益需要通过运行时/镜像仓库/工作负载来验证。
</details>

## 11. 如何配置 UTC 09–17 的工作时段预算？

<details>
<summary>答案与说明</summary>

使用 0 9 * * 1-5 并设置 8h 时长。0 9-17 * * 1-5 会每小时启动一次，并会延续到次日 01:00。预算限制的是自愿性中断，而不是 Spot 回收、故障或强制过期。
</details>

## 12. ESO 的刷新是否会自动签发凭证、重新加载应用并审计每一次读取？

<details>
<summary>答案与说明</summary>

不会。需要区分 provider 轮换、Secret 同步和应用重新读取。subPath/env 形式的值不会自动刷新；CloudTrail 不会记录每一次本地读取。ESO 2.10 提供的是 v1，而不是 v1beta1。
</details>

## 13. 如何估算 30B FP16 模型所需的 GPU 显存？

<details>
<summary>答案与说明</summary>

仅权重约为 60GB；还需加上 KV、激活值、workspace 和通信开销。四块 24GB GPU 合计 96GB，但仍需检查分片方式/峰值显存/吞吐。13B FP16 会超过 24GB；70B FP16 会超过 96GB。
</details>

## 14. 当前 vLLM 的 KV cache 占用率高是否总会导致请求被拒绝？

<details>
<summary>答案与说明</summary>

应使用 vllm:kv_cache_usage_perc。要结合队列、抢占（preemption）和内存状态来解读占用率；并不保证会立即拒绝请求。避免使用已废弃的 gpu_cache_usage_perc 和未经确认的命中率指标名称。
</details>

## 15. Karpenter 的放置组是否通过 tag 来配置？

<details>
<summary>答案与说明</summary>

1.14.1 版本使用 EC2NodeClass.spec.placementGroupSelector 的 name/id。aws:ec2:placement-group tag 并不是放置 API。需要验证 AZ、容量和网络，并评估单可用区带来的恢复风险。
</details>

[返回指南](../../ai-ml/07-ai-ml-best-practices.md)
