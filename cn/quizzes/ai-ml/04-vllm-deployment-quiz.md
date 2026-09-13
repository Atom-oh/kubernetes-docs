# vLLM 部署测验

基线版本：vLLM 0.29.0。历史 L4 测试结果与当前验证结果需加以区分。

## 测验题目

### 1. 哪项陈述正确描述了 vLLM？

- A. 一个名为 Vector Language Model 的模型
- B. 面向受支持的生成式/多模态及其他模型工作负载的推理引擎
- C. 仅用于数据库的优化器
- D. 一个能自动提升所有模型准确率的训练工具

<details>
<summary>显示答案</summary>

**答案：B. 面向受支持的生成式/多模态及其他模型工作负载的推理引擎**

vLLM 是一个引擎，而非上述臆造的英文缩写全称。PagedAttention 和批处理带来的收益取决于具体工作负载；并不保证固定的加速比，也不保证执行过程中完全没有排队。
</details>

### 2. 应如何估算 GPU 内存需求？

- A. 70B 模型无论精度如何都能装入 80GB
- B. 将权重、KV cache、激活值/工作区以及通信开销相加，并考虑架构、精度和并行策略
- C. 每个 GPU 配四个 CPU 核心即可保证所有模型都能运行
- D. 主机内存越大就不再需要 GPU

<details>
<summary>显示答案</summary>

**答案：B. 将权重、KV cache、激活值/工作区以及通信开销相加，并考虑架构、精度和并行策略**

仅 70B 模型的 FP16/BF16 权重就约为 140GB。GQA/MQA 需要按 KV 头数量计算，而不能套用 MHA 的隐藏层维度公式。请确认当前 NVIDIA 计算能力 7.5 的最低要求以及额外的 kernel 需求。
</details>

### 3. 哪项存储相关陈述是正确的？

- A. FSx for Lustre 始终是最优选择
- B. snapshot_download 从 S3 下载
- C. 依据加载时间、并发度、成本和保留期进行选择，并记录模型 revision 与完整性
- D. emptyDir 在容器重启时总会被清空

<details>
<summary>显示答案</summary>

**答案：C. 依据加载时间、并发度、成本和保留期进行选择，并记录模型 revision 与完整性**

emptyDir 可以在容器重启后保留，但无法在 Pod 重建后保留。需要区分 FSx 的静态/动态制备（provisioning）、EBS 访问模式以及各 worker 上相同的模型路径。Hugging Face 下载与 S3 传输是两件不同的事情。
</details>

### 4. TP、PP 与独立副本有何区别？

- A. 增加 StatefulSet 的副本数会自动重新配置 TP
- B. TP 在层内切分，PP 按层的阶段切分，而独立副本各自加载完整模型
- C. TP 总能降低单请求延迟
- D. 所有多节点部署都使用 --rank

<details>
<summary>显示答案</summary>

**答案：B. TP 在层内切分，PP 按层的阶段切分，而独立副本各自加载完整模型**

0.29.0 的 multiprocessing 方式使用 --nnodes/--node-rank 以及 headless worker；Ray 则需要一个真实的集群。需要保证环境、模型、网络/rendezvous 和 GPU 相互匹配。进程拓扑并不等于 Kubernetes 的副本数量。
</details>

### 5. 哪项可用性相关陈述是正确的？

- A. PDB 能在任何节点故障情况下保证最小副本数
- B. 仅设置 maxUnavailable0 就能保证零停机
- C. 需要同时验证独立副本、探针（probe）、启动过程、备用容量、节点排空（draining）以及流式响应
- D. 将单个 TP 组跨可用区（AZ）分布总能提升性能

<details>
<summary>显示答案</summary>

**答案：C. 需要同时验证独立副本、探针（probe）、启动过程、备用容量、节点排空（draining）以及流式响应**

PDB 只能约束部分自愿驱逐。示例中的 Recreate 策略可以省下一块额外的 GPU，但会在更新期间造成停机。startupProbe 在初始化阶段控制 readiness/liveness 的生效时机；请验证实际的加载时间。
</details>

### 6. 哪项批处理/缓存相关陈述是正确的？

- A. 每个请求都会立即执行，不存在排队
- B. 调度是按 step 逐步进行的，在 token/缓存/容量受限时会形成队列
- C. 前缀缓存（prefix caching）总是复用完整的响应内容
- D. --swap-space 是 0.29 中扩展内存的默认方式

<details>
<summary>显示答案</summary>

**答案：B. 调度是按 step 逐步进行的，在 token/缓存/容量受限时会形成队列**

前缀缓存复用的是受支持的前缀 KV 状态。Chunked prefill、max-num-seqs、token 预算和上下文限制各不相同。CacheConfig 中 gpu_memory_utilization 默认为 0.92，而示例设置为 0.80。--swap-space 在当前 CLI 中已不存在。
</details>

### 7. 当前的指标（metrics）配置应采用什么方式？

- A. 单独的 8001 端口以及 --enable-metrics=true
- B. 在 API 端口 8000 上暴露 /metrics，并使用实际的 vllm: 指标名称、标签和单位
- C. 将 KV 占用率表示为 GPU 内存的总字节数
- D. 对每个空闲时段都按低吞吐故障告警

<details>
<summary>显示答案</summary>

**答案：B. 在 API 端口 8000 上暴露 /metrics，并使用实际的 vllm: 指标名称、标签和单位**

示例包括 vllm:generation_tokens_total 和 vllm:e2e_request_latency_seconds_bucket。KV 占用率是一个比率，1 表示 100%。需要区分模型维度的聚合、网关错误/取消、TTFT 与端到端延迟。
</details>

### 8. 哪项多节点网络相关陈述是正确的？

- A. API key 会加密所有内部传输
- B. 随意复制来的 GID/mlx5 设置即可配置好 EFA
- C. 需要验证受支持的设备/驱动、OFI NCCL/libfabric 以及私有通信路径
- D. 单节点 NCCL 测试即可证明多节点 EFA 的性能

<details>
<summary>显示答案</summary>

**答案：C. 需要验证受支持的设备/驱动、OFI NCCL/libfabric 以及私有通信路径**

分布式通信需要可信网络。API 认证与 PyTorch/Ray/KV 传输层的安全性是不同的事情。通用的 SR-IOV/InfiniBand 模板以及臆造的 NCCL 环境变量并不是可直接使用的 EKS 配置。
</details>

### 9. 哪项扩缩容/路由相关陈述是正确的？

- A. HTTP 的 model 请求头会自动读取 JSON 中的 model 字段
- B. 会话亲和性（session affinity）会自动共享所有 KV cache
- C. 依据实测瓶颈和模型拓扑来选择副本数、TP/PP 以及路由方式
- D. 只要有 GPU，CPU 和存储就完全不影响性能

<details>
<summary>显示答案</summary>

**答案：C. 依据实测瓶颈和模型拓扑来选择副本数、TP/PP 以及路由方式**

前缀缓存、响应缓存和权重缓存各不相同。CPU 分词、网络或模型加载都可能成为瓶颈。HPA/KEDA 与 NodePool 属于不同层，各自有指标、归属和容量方面的要求。
</details>

### 10. 在 0.29.0 中，哪项 API key／安全相关陈述是正确的？

- A. --api-key 会保护服务器的所有端点
- B. 除前缀认证之外，其他路径和运维能力还需要网关、权限和网络边界来保护
- C. CORS 可以替代认证
- D. 单个正则表达式就能阻止所有提示注入（prompt injection）和 PII 泄露

<details>
<summary>显示答案</summary>

**答案：B. 除前缀认证之外，其他路径和运维能力还需要网关、权限和网络边界来保护**

经查阅的中间件只保护 /v1,/v2,/inference,/cohere 这些前缀；其他路径以及 OPTIONS 请求会绕过它。动态 LoRA 需要显式启用，并依赖可信的运维路径。对 Secret 做 RequestResponse 级别审计，以及用 Pod 注解假装开启控制平面审计，都属于不安全／无效的示例。
</details>

### 11. 应如何解读历史 L4 结果中的 5.65s→7.52s？

- A. 延迟没有增加
- B. 在该测试范围内 p50 上升约 33.1%，而总吞吐量有所提高；缺少原始日志的旧报告不能作为当前版本的证据
- C. profiler 已证明存在内存瓶颈
- D. 连续批处理会跳过 prefill

<details>
<summary>显示答案</summary>

**答案：B. 在该测试范围内 p50 上升约 33.1%，而总吞吐量有所提高；缺少原始日志的旧报告不能作为当前版本的证据**

所报告的数据来自一次 0.6.4.post1 的运行。本次审查未能找到原始的请求/服务器日志，也未重新运行该测试。日志记录区间内的最大平均值并不等于瞬时峰值；roofline 计算只是一种估算，而非 profiler 提供的证据。
</details>

---

[返回学习材料](../../ai-ml/02-vllm-deployment.md)
