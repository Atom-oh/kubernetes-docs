# AI/ML 最佳实践测验

本测验用于检验你对 Amazon EKS 上 AI/ML 最佳实践的理解，包括基准测试、容器优化、GPU 选择、网络、存储、可观测性和成本优化。

## 测验问题

### 1. 在 LLM 推理基准测试中，TTFT（Time to First Token）衡量什么？

A) 生成一个响应中所有 token 的总时间
B) 从提交请求到生成第一个 token 的时间
C) 连续 token 之间的平均时间
D) 每秒生成的 token 数量

<details>
<summary>显示答案</summary>

**答案：B) 从提交请求到生成第一个 token 的时间**

**解释：**
TTFT（Time to First Token）衡量从请求提交到响应的第一个 token 生成之间的延迟。该指标对用户体验至关重要，因为它决定了用户多快能看到响应的开头。

公式为：`TTFT = t_first_token - t_request`

关于 TTFT 的要点：
- 直接影响应用程序的感知响应速度
- 对于交互式应用程序，应低于 500ms
- 受模型加载、prompt 处理（prefill）和队列深度影响
- 较高的 TTFT 表明 GPU 内存、batch size 或系统负载可能存在问题

其他指标：
- ITL（Inter-Token Latency）：连续 token 之间的时间
- TPS（Tokens Per Second）：生成速度
- E2E Latency：从请求到完整响应的总时间

</details>

### 2. 哪种容器启动优化技术可以最大幅度降低冷启动时间？

A) 仅使用多阶段 Docker 构建
B) 仅进行模型工件解耦
C) 组合方法（解耦 + 多阶段 + 预取 + SOCI）
D) 仅使用更小的基础镜像

<details>
<summary>显示答案</summary>

**答案：C) 组合方法（解耦 + 多阶段 + 预取 + SOCI）**

**解释：**
组合方法可以最大幅度降低冷启动时间，与朴素实现相比可实现 80-95% 的改进。

冷启动优化对比：

| 技术 | 启动时间降低 |
|-----------|-------------------|
| 模型解耦 | 50-70% |
| 多阶段构建 | 30-50% |
| SOCI snapshotter | 60-80% |
| 镜像预取 | 70-90% |
| **组合方法** | **80-95%** |

组合方法的工作方式如下：
1. **模型解耦**：将大型模型权重与容器镜像分离
2. **多阶段构建**：通过排除构建依赖来减小镜像大小
3. **SOCI snapshotter**：启用延迟拉取，使容器可在完整镜像下载完成前启动
4. **镜像预取**：在节点引导期间预先拉取镜像

对于可能达到 10-50GB 的 AI/ML 镜像，此组合可以将启动时间从 5-15 分钟缩短到 1 分钟以内。

</details>

### 3. 哪个 GPU 实例系列最适合需要高带宽节点间通信的大规模分布式训练？

A) G5 (NVIDIA A10G)
B) G6 (NVIDIA L4)
C) P5 (NVIDIA H100)
D) Inf2 (AWS Inferentia2)

<details>
<summary>显示答案</summary>

**答案：C) P5 (NVIDIA H100)**

**解释：**
配备 NVIDIA H100 GPU 的 P5 实例最适合大规模分布式训练，因为它们提供：

- **8x NVIDIA H100 GPUs**，每个具有 80GB HBM3 内存
- **3200 Gbps EFA 网络** - 对分布式训练至关重要
- **NVLink 4.0**，用于节点内高带宽 GPU 到 GPU 通信
- **192 vCPUs 和 2048GB 内存**，用于数据预处理

分布式训练对比：

| 实例 | GPUs | GPU 内存 | 网络 | 训练适用性 |
|----------|------|------------|---------|---------------------|
| G5 | 1-8 A10G | 24GB | 100 Gbps | 小型/中型模型 |
| G6 | 1-8 L4 | 24GB | 100 Gbps | 侧重推理 |
| P4d | 8 A100 | 40-80GB | 400 Gbps EFA | 大规模训练 |
| **P5** | **8 H100** | **80GB** | **3200 Gbps EFA** | **前沿模型** |
| Inf2 | 1-12 Inferentia2 | 32GB | 100 Gbps | 仅推理 |

P5 的 3200 Gbps EFA 带宽是 P4d 的 8 倍，因此非常适合梯度同步跨节点成为瓶颈的训练任务。

</details>

### 4. 在分布式 AI/ML 训练中，EFA（Elastic Fabric Adapter）的主要用途是什么？

A) 增加 GPU 内存容量
B) 提供低延迟、高带宽的节点间通信
C) 启用 GPU 时间共享
D) 加速模型推理

<details>
<summary>显示答案</summary>

**答案：B) 提供低延迟、高带宽的节点间通信**

**解释：**
EFA（Elastic Fabric Adapter）是 Amazon EC2 实例的网络接口，使高性能计算（HPC）和机器学习应用程序能够达到本地 HPC 集群的节点间通信性能。

EFA 对分布式训练的主要优势：
1. **OS-bypass 能力**：允许应用程序直接与网络适配器通信，从而降低延迟
2. **高带宽**：在 P5 实例上最高可达 3200 Gbps
3. **低延迟**：集体操作可实现亚微秒级延迟
4. **NCCL 优化**：与 AWS OFI NCCL plugin 配合使用，以优化 GPU 到 GPU 通信

EFA 配置要求：
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request EFA devices
```

用于 EFA 的 NCCL 环境变量：
```bash
export FI_PROVIDER=efa
export FI_EFA_USE_DEVICE_RDMA=1
export NCCL_ALGO=Ring,Tree
```

EFA 对以下场景至关重要：
- 使用 PyTorch DDP、Horovod 等框架进行多节点分布式训练
- 使用 tensor/pipeline parallelism 进行大模型训练
- 任何梯度同步成为瓶颈的工作负载

</details>

### 5. 对于 AI/ML 工作负载，什么时候应使用 FSx for Lustre 而不是 EFS？

A) 当需要多个 Pod（容器组）共享访问时
B) 当训练数据集超过 10TB 并需要高吞吐量时
C) 临时存储模型检查点时
D) 使用小模型运行推理工作负载时

<details>
<summary>显示答案</summary>

**答案：B) 当训练数据集超过 10TB 并需要高吞吐量时**

**解释：**
FSx for Lustre 是需要高吞吐量的大型训练数据集（>10TB）的最佳选择，而 EFS 更适合较小数据集和共享模型存储。

存储选择指南：

| 使用场景 | 推荐存储 | 原因 |
|----------|---------------------|-----------|
| 训练数据集 <500GB | EBS gp3 | 单节点，成本效益高 |
| 训练数据集 500GB-10TB | EFS | 多节点读取，中等吞吐量 |
| **训练数据集 >10TB** | **FSx Lustre** | **并行文件系统，TB/s 吞吐量** |
| 共享模型权重 | EFS | ReadWriteMany，缓存 |
| 临时检查点 | Instance store | 最低延迟，临时性 |
| 长期模型存储 | S3 | 成本效益高，持久 |

FSx for Lustre 优势：
- 吞吐量最高可达 1+ TB/s（相比 EFS 的约 1-3 GB/s）
- 亚毫秒级延迟
- 通过 `s3ImportPath` 直接集成 S3
- 面向 HPC 工作负载设计的并行文件系统

```yaml
# FSx Lustre for large datasets
storageClassName: fsx-lustre-sc
parameters:
  perUnitStorageThroughput: "250"  # MB/s per TiB
  s3ImportPath: s3://training-data  # Transparent S3 access
```

</details>

### 6. 应监控哪个 DCGM 指标来检测 GPU 热节流？

A) DCGM_FI_DEV_GPU_UTIL
B) DCGM_FI_DEV_FB_USED
C) DCGM_FI_DEV_GPU_TEMP
D) DCGM_FI_DEV_XID_ERRORS

<details>
<summary>显示答案</summary>

**答案：C) DCGM_FI_DEV_GPU_TEMP**

**解释：**
DCGM_FI_DEV_GPU_TEMP 监控 GPU 摄氏温度，这是检测热节流条件的主要指标。

关键 GPU 指标及其用途：

| 指标 | 用途 | 告警阈值 |
|--------|---------|-----------------|
| **DCGM_FI_DEV_GPU_TEMP** | **温度监控** | **>80C 警告，>90C 严重** |
| DCGM_FI_DEV_GPU_UTIL | 计算利用率 | 持续 >95% |
| DCGM_FI_DEV_FB_USED | 内存使用 | 超过总量的 >95% |
| DCGM_FI_DEV_SM_CLOCK | 时钟频率（节流检测） | 低于基线 |
| DCGM_FI_DEV_POWER_USAGE | 功耗 | 接近 TDP 限制 |
| DCGM_FI_DEV_XID_ERRORS | 硬件错误 | 任何增加 |

热节流检测：
```yaml
# Alert rule for thermal issues
- alert: GPUHighTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 80
  for: 5m
  labels:
    severity: warning

- alert: GPUCriticalTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 90
  for: 1m
  labels:
    severity: critical
```

当温度超过阈值时，GPU 会自动降低时钟速度（热节流），从而影响训练和推理性能。

</details>

### 7. 对 GPU 推理工作负载使用 Spot 实例的推荐方法是什么？

A) 永远不要将 Spot 实例用于推理
B) Spot 仅用于训练，On-Demand 用于推理
C) 使用 Spot，并配置优雅终止处理和拓扑分布
D) 使用 Spot，不进行任何特殊配置

<details>
<summary>显示答案</summary>

**答案：C) 使用 Spot，并配置优雅终止处理和拓扑分布**

**解释：**
如果正确配置优雅终止处理和可用性考虑因素，Spot 实例可为无状态推理工作负载节省 60-90% 的成本。

Spot 推理最佳实践：

1. **优雅终止处理**：
```yaml
spec:
  terminationGracePeriodSeconds: 120
  containers:
  - lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "curl -X POST localhost:8000/drain; sleep 30"]
```

2. **用于可用性的拓扑分布**：
```yaml
topologySpreadConstraints:
- maxSkew: 2
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
```

3. **混合容量类型**：
```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
    - weight: 50
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

Spot 适用于推理，因为：
- 推理 Pod 通常是无状态的
- 多个副本提供冗余
- 2 分钟中断警告允许优雅排空

</details>

### 8. 计算 Inter-Token Latency（ITL）的公式是什么？

A) `t_last_token - t_request`
B) `(t_last_token - t_first_token) / (n_tokens - 1)`
C) `n_tokens / total_generation_time`
D) `t_first_token - t_request`

<details>
<summary>显示答案</summary>

**答案：B) `(t_last_token - t_first_token) / (n_tokens - 1)`**

**解释：**
Inter-Token Latency（ITL）衡量生成过程中连续 token 之间的平均时间。公式为：

`ITL = (t_last_token - t_first_token) / (n_tokens - 1)`

其中：
- `t_last_token`：最后一个 token 生成时的时间戳
- `t_first_token`：第一个 token 生成时的时间戳
- `n_tokens`：生成的 token 总数
- 我们除以 `(n_tokens - 1)`，因为衡量的是 token 之间的间隔

ITL 的重要性：
- 决定聊天应用程序的流式输出质量
- 目标：低于 50ms，以获得流畅的用户体验
- 较高的 ITL 表明可能存在 GPU 内存压力或计算瓶颈

其他指标公式：
- **TTFT**：`t_first_token - t_request`（到首个 token 的时间）
- **TPS**：`n_tokens / total_generation_time`（每秒 token 数）
- **E2E Latency**：`t_complete - t_request`（端到端）

示例计算：
- 第一个 token 在 500ms 时生成，最后一个 token 在 2500ms 时生成，共生成 50 个 token
- ITL = (2500 - 500) / (50 - 1) = 2000 / 49 = ~41ms

</details>

### 9. 哪种测试场景最适合用于确定 LLM 推理服务的最大吞吐量？

A) 基线测试
B) 饱和测试
C) 真实数据集测试
D) 长上下文测试

<details>
<summary>显示答案</summary>

**答案：B) 饱和测试**

**解释：**
饱和测试专门用于通过逐步增加并发度直到延迟恶化来确定最大吞吐量，从而揭示系统的容量限制。

测试场景对比：

| 场景 | 目的 | 配置 |
|----------|---------|---------------|
| 基线 | 建立单请求性能 | Concurrency=1, 100 requests |
| **饱和** | **确定吞吐量限制** | **Concurrency=[1,5,10,20,50,100]** |
| 生产 | 验证真实世界性能 | 可变 prompt，真实负载 |
| 真实数据集 | 使用实际数据模式测试 | ShareGPT 或领域数据 |
| 长上下文 | 测试上下文窗口处理 | 4K-128K token prompts |

饱和测试配置：
```yaml
saturation:
  description: "Find maximum throughput"
  concurrency: [1, 5, 10, 20, 50, 100]  # Incrementally increase
  num_requests: 500
  prompt_length: 256
  max_tokens: 512
```

饱和测试揭示的内容：
- 吞吐量与延迟曲线
- 延迟开始恶化的点
- 系统是 GPU 受限、内存受限还是 CPU 受限
- 最佳运行并发级别

目标是找到曲线的“拐点”，即吞吐量趋于平台期而延迟仍保持可接受的地方。

</details>

### 10. SOCI（Seekable OCI）snapshotter 对 AI/ML 容器的用途是什么？

A) 压缩容器镜像
B) 启用延迟拉取，使容器可在完整镜像下载完成前启动
C) 加密容器镜像
D) 在节点之间共享镜像

<details>
<summary>显示答案</summary>

**答案：B) 启用延迟拉取，使容器可在完整镜像下载完成前启动**

**解释：**
SOCI（Seekable OCI）snapshotter 启用容器镜像的延迟加载，允许容器在整个镜像下载完成前启动。这对于大型 AI/ML 镜像（10-50GB）尤其有价值。

SOCI 的工作方式：
1. 为容器镜像层创建索引
2. 最初只下载元数据和必要层
3. 当应用程序访问文件时按需获取剩余层
4. 容器只需下载约 10-20% 的镜像即可启动

对 AI/ML 的好处：
- 容器启动时间减少 60-80%
- 对包含大型且很少访问层的镜像尤其有效
- 当模型权重在容器启动后访问时效果最佳

SOCI 设置：
```bash
# Create SOCI index for an image
soci create \
  --ref public.ecr.aws/myrepo/vllm:latest \
  --platform linux/amd64

# Push the index to registry
soci push \
  --ref public.ecr.aws/myrepo/vllm:latest
```

与其他优化结合：
- 模型解耦（50-70%）
- 多阶段构建（30-50%）
- SOCI snapshotter（60-80%）
- 镜像预取（70-90%）

当容器运行时支持 SOCI（带 SOCI plugin 的 containerd）且镜像存储在兼容的 registry（Amazon ECR）中时，SOCI 最有效。

</details>

### 11. 哪个 Karpenter consolidation policy 设置可以防止在工作时间发生节点中断？

A) consolidationPolicy: WhenEmpty
B) consolidateAfter: 0
C) budgets with schedule and nodes: "0"
D) weight: 0

<details>
<summary>显示答案</summary>

**答案：C) budgets with schedule and nodes: "0"**

**解释：**
Karpenter 带有 schedule 和 `nodes: "0"` 的 disruption budgets 可以在指定时间窗口（通常是工作时间）内阻止任何节点 consolidation。

配置示例：
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m

  budgets:
  # No consolidation during business hours
  - nodes: "0"
    schedule: "0 9-17 * * 1-5"  # 9 AM to 5 PM, Mon-Fri
    duration: 8h

  # Allow 30% consolidation during off-peak
  - nodes: "30%"
```

Budget 参数：
- `nodes`：可以中断的最大节点数量/百分比
- `schedule`：budget 适用时间的 Cron 表达式
- `duration`：schedule 触发后 budget 保持活动的时长

为什么这对 AI/ML 很重要：
- GPU 节点成本高昂，中断会导致冷启动
- 节点替换期间推理延迟会飙升
- 如果 checkpointing 不够频繁，训练任务可能丢失进度
- 工作时间通常流量最高

其他 consolidation 设置：
- `consolidationPolicy: WhenEmpty`：仅 consolidation 完全空闲的节点
- `consolidationPolicy: WhenEmptyOrUnderutilized`：也 consolidation 利用率不足的节点
- `consolidateAfter`：consolidation 前的延迟（例如 5m）

</details>

### 12. 在 Kubernetes 中管理 HuggingFace 和 NGC API keys 的推荐方法是什么？

A) 硬编码在 Dockerfile 中
B) 作为环境变量传入 pod spec
C) 使用 External Secrets Operator 和 AWS Secrets Manager
D) 存储在 ConfigMap 中

<details>
<summary>显示答案</summary>

**答案：C) 使用 External Secrets Operator 和 AWS Secrets Manager**

**解释：**
External Secrets Operator（ESO）与 AWS Secrets Manager 结合，可提供安全、集中式的 secret 管理，并具备自动轮换和审计能力。

推荐 ESO 的原因：
1. **集中式管理**：Secrets 存储在 AWS Secrets Manager 中
2. **自动同步**：ESO 自动更新 Kubernetes Secret
3. **轮换支持**：Secrets 可以在不重新部署 Pod 的情况下轮换
4. **审计跟踪**：AWS CloudTrail 记录所有 secret 访问
5. **IAM 集成**：通过 IRSA 实现细粒度访问控制

配置示例：
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: model-registry-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: model-registry-credentials
  data:
  - secretKey: HUGGING_FACE_HUB_TOKEN
    remoteRef:
      key: ai-ml/huggingface-token
      property: token
  - secretKey: NGC_API_KEY
    remoteRef:
      key: ai-ml/ngc-api-key
      property: key
```

为什么其他选项有问题：
- **硬编码在 Dockerfile 中**：Secrets 会暴露在镜像层中
- **pod spec 中的环境变量**：在 kubectl describe 中可见
- **ConfigMap**：未加密，对任何具有读取权限的人可见

安全最佳实践：
- 使用 IRSA 进行 service account 认证
- 在 Secrets Manager 中启用静态加密
- 实施最小权限访问策略
- 定期轮换 secrets

</details>

### 13. 对于预算中等的 30B 参数模型推理工作负载，哪种 GPU 实例类型最合适？

A) g5.xlarge (1x A10G, 24GB)
B) g5.4xlarge (1x A10G, 24GB)
C) g5.12xlarge (4x A10G, 96GB total)
D) p4d.24xlarge (8x A100, 640GB total)

<details>
<summary>显示答案</summary>

**答案：C) g5.12xlarge (4x A10G, 96GB total)**

**解释：**
30B 参数模型进行 FP16 推理大约需要 60GB GPU 内存（每个参数 2 字节），因此配备 4x A10G GPU（总计 96GB）的 g5.12xlarge 是中等预算下的合适选择。

内存计算：
- 30B 参数 x 2 字节（FP16）= 最少 60GB
- 加上 KV cache 开销：建议约 70-80GB
- g5.12xlarge：4 x 24GB = 96GB（有足够余量）

实例选择指南：

| 模型大小 | 所需内存 | 推荐实例 | 预算 |
|------------|---------------|---------------------|--------|
| <7B | 14GB | g5.xlarge | 低 |
| 7-13B | 26GB | g5.2xlarge | 低-中 |
| 13-30B | 60GB | g5.4xlarge（量化）或 g5.12xlarge | 中 |
| **30B** | **60GB** | **g5.12xlarge (4x A10G)** | **中** |
| 30-70B | 140GB | g5.12xlarge + tensor parallel | 中-高 |
| >70B | 280GB+ | p4d.24xlarge | 高 |

为什么 30B 选择 g5.12xlarge：
- 4 路 tensor parallelism 将模型分布到多个 GPU
- 每个 GPU 保存约 15GB 的模型权重
- 剩余内存可用于 KV cache
- 对推理而言比 P4d 更具成本效益

P4d.24xlarge 也能工作，但对 30B 推理来说过度配置，而且贵得多。

</details>

### 14. 哪个 vLLM 指标表明系统可能因内存压力而开始拒绝请求？

A) vllm:num_requests_running
B) vllm:time_to_first_token_seconds
C) vllm:gpu_cache_usage_perc
D) vllm:request_success_total

<details>
<summary>显示答案</summary>

**答案：C) vllm:gpu_cache_usage_perc**

**解释：**
`vllm:gpu_cache_usage_perc` 衡量 KV（Key-Value）cache 利用率。当该指标接近 100% 时，vLLM 无法接受新请求，因为没有可用内存来存储 attention states。

KV cache 的重要性：
- 存储每个 token 计算出的 attention keys 和 values
- 随着序列长度和 batch size 增长
- 当 cache 满时，vLLM 必须抢占正在运行的请求或拒绝新请求

告警配置：
```yaml
- alert: vLLMKVCacheFull
  expr: vllm:gpu_cache_usage_perc > 0.95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "vLLM KV cache nearly full"
    description: "KV cache usage above 95%, requests may be rejected"
```

当 KV cache 满时该怎么做：
1. 减小 `--max-num-seqs`（并发序列数）
2. 减小 `--max-model-len`（最大序列长度）
3. 启用 chunked prefill
4. 水平扩展（添加更多副本）
5. 使用更大的 GPU 实例

其他 vLLM 指标：
- `vllm:num_requests_running`：当前并发请求数
- `vllm:num_requests_waiting`：队列深度
- `vllm:time_to_first_token_seconds`：TTFT 延迟
- `vllm:gpu_prefix_cache_hit_rate`：缓存效率

</details>

### 15. 在分布式训练中使用 cluster 策略的 placement groups 的主要好处是什么？

A) 降低 EC2 实例成本
B) 自动负载均衡
C) 节点之间最低的网络延迟
D) 增加 GPU 内存

<details>
<summary>显示答案</summary>

**答案：C) 节点之间最低的网络延迟**

**解释：**
Cluster placement groups 会将实例放置在单个 Availability Zone 内物理距离较近的位置，从而最小化网络延迟并最大化节点间通信带宽。

Cluster placement group 的好处：
1. **最低延迟**：实例位于同一网络 spine 上
2. **最大带宽**：可使用完整双分带宽
3. **一致性能**：减少网络抖动
4. **EFA 优化**：最佳 EFA 性能需要 cluster placement

配置：
```bash
# Create cluster placement group
aws ec2 create-placement-group \
  --group-name training-cluster-pg \
  --strategy cluster

# Karpenter configuration
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
spec:
  tags:
    aws:ec2:placement-group: training-cluster-pg
```

Placement group 策略：

| 策略 | 使用场景 | 延迟 | 可用性 |
|----------|----------|---------|--------------|
| **Cluster** | **分布式训练** | **最低** | **单 AZ** |
| Spread | 高可用性 | 更高 | Multi-AZ |
| Partition | 大型部署 | 中等 | Multi-rack |

为什么训练使用 cluster 策略：
- NCCL all-reduce 操作对延迟敏感
- 梯度同步频繁发生（每个 batch）
- 即使很小的延迟增加也会在数千次迭代中累积
- P4d/P5 实例在 cluster placement 中可获得最佳 EFA 性能

权衡：Cluster placement groups 限于单个 AZ，会降低可用性。对于训练来说，这是可以接受的，因为：
- 训练任务可以 checkpoint 并重启
- 更低延迟对训练时间的改善大于冗余带来的帮助

</details>
