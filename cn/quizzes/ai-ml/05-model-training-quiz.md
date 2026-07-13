# EKS 上的模型训练测验

本测验用于检验你对 Amazon EKS 上模型训练的理解，包括分布式训练策略、Slurm/Slinky 集成、基于 GPU 和 Trainium 的训练、存储配置以及优化技术。

## 测验题目

### 1. 哪种分布式训练策略会将单个层拆分到多个 GPU 上？

A) 数据并行
B) 张量并行
C) 流水线并行
D) 专家并行

<details>
<summary>显示答案</summary>

**答案：B) 张量并行**

**解析：**
张量并行会将单个层（例如 attention 层或前馈网络）拆分到多个 GPU 上。每个 GPU 保存该层权重的一部分，并计算该操作中属于自己的部分。

**并行策略对比：**

| 策略 | 分布的内容 | 通信模式 |
|----------|---------------------|----------------------|
| 数据并行 | 训练数据批次 | 梯度同步 |
| 张量并行 | 单个层 | 层内通信 |
| 流水线并行 | 层组（阶段） | 阶段间激活传递 |
| 专家并行 | MoE 中的专家网络 | Token 路由 |

张量并行尤其适用于大到无法放入单个 GPU 内存的层，例如大型语言模型中的 attention 层。

</details>

### 2. 训练一个 2000 亿参数模型时，推荐使用哪种并行策略？

A) 仅数据并行
B) 仅张量并行
C) 仅流水线并行
D) 3D 并行（DP + TP + PP）

<details>
<summary>显示答案</summary>

**答案：D) 3D 并行（DP + TP + PP）**

**解析：**
对于超过 1000 亿参数的模型，3D 并行会结合三种策略以获得最高效率：

- **数据并行 (DP)**：在多组 GPU 之间复制模型，每组处理不同的数据批次
- **张量并行 (TP)**：在一个节点内拆分大型层（通常是带 NVLink 的 8 个 GPU）
- **流水线并行 (PP)**：将层组分布到多个节点，以降低每个设备所需的内存

在 64 个 A100 GPU 上训练 200B 模型的示例配置：
```
TP=8  (within each node)
PP=4  (across 4 nodes)
DP=2  (2 data parallel replicas)
Total: 8 × 4 × 2 = 64 GPUs
```

这种方法提供：
- 最大化的内存效率
- 计算与通信的平衡
- 训练超出单节点内存容量的模型的能力

</details>

### 3. 在 Slinky 的架构中，哪个组件管理作业计费和集群状态？

A) slurmctld
B) slurmdbd
C) slurmd
D) slurmrestd

<details>
<summary>显示答案</summary>

**答案：B) slurmdbd**

**解析：**
Slinky/Slurm 组件承担不同用途：

| 组件 | 角色 | Kubernetes 资源 |
|-----------|------|---------------------|
| **slurmctld** | 中央控制器 - 管理作业、分区和资源分配 | StatefulSet |
| **slurmdbd** | 数据库守护进程 - 处理作业计费、使用情况跟踪和集群状态持久化 | 带 MySQL/MariaDB 的 StatefulSet |
| **slurmd** | 计算守护进程 - 在每个 worker 节点上运行，执行作业步骤 | DaemonSet |
| **slurmrestd** | REST API - 支持以编程方式提交作业 | Deployment |

slurmdbd 守护进程对于以下方面至关重要：
- 存储历史作业数据
- 跟踪用于计费的资源使用情况
- 维护用于故障恢复的集群状态
- 支持基于过去使用情况的 fair-share 调度

</details>

### 4. Slinky 使用哪个 CRD 来定义计算节点组（分区）？

A) SlurmCluster
B) SlurmNodeSet
C) SlurmPartition
D) SlurmWorker

<details>
<summary>显示答案</summary>

**答案：B) SlurmNodeSet**

**解析：**
Slinky 引入了两个主要的 Custom Resource Definitions：

1. **SlurmCluster**：定义整体集群配置，包括：
   - Controller (slurmctld) 设置
   - Database (slurmdbd) 配置
   - REST API 设置
   - 共享存储配置

2. **SlurmNodeSet**：定义计算节点组（分区），包括：
   - 实例类型和 GPU 配置
   - 资源分配（CPU、内存、GPU 内存）
   - 用于 GRES（Generic Resource Scheduling）的节点特性
   - 与 Karpenter 集成的自动扩缩设置
   - 用于低延迟网络的 placement group 配置

SlurmNodeSet 示例：
```yaml
apiVersion: slinky.slurm.net/v1alpha1
kind: SlurmNodeSet
metadata:
  name: gpu-a100-nodes
spec:
  partition: gpu-a100
  nodeCount: 4
  nodeTemplate:
    instanceType: p4d.24xlarge
    gpus:
      type: nvidia-a100
      count: 8
```

</details>

### 5. 哪个环境变量会在 NCCL 中启用 EFA (Elastic Fabric Adapter)，用于分布式训练？

A) NCCL_EFA_ENABLE=1
B) FI_PROVIDER=efa
C) EFA_ENABLED=true
D) NCCL_NET=efa

<details>
<summary>显示答案</summary>

**答案：B) FI_PROVIDER=efa**

**解析：**
要为分布式训练启用 NCCL 的 EFA 网络，需要设置多个环境变量：

```bash
# Primary EFA configuration
export FI_PROVIDER=efa              # Use EFA as the libfabric provider
export FI_EFA_USE_DEVICE_RDMA=1     # Enable device-level RDMA
export RDMAV_FORK_SAFE=1            # Safe forking with RDMA

# NCCL configuration for EFA
export NCCL_DEBUG=INFO              # Enable debugging output
export NCCL_ALGO=Ring               # Use Ring algorithm (works well with EFA)
export NCCL_PROTO=Simple            # Simple protocol for EFA
```

EFA 在受支持的实例类型（p4d、p5、trn1）上提供高达 400 Gbps 的网络带宽，并显著降低分布式训练的通信延迟。

此外，Pod 必须请求 EFA 设备：
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request 4 EFA devices
```

</details>

### 6. NVIDIA BioNeMo 在 EKS 上的用途是什么？

A) GPU 监控和指标收集
B) 药物发现和分子建模
C) 容器网络优化
D) 模型量化和压缩

<details>
<summary>显示答案</summary>

**答案：B) 药物发现和分子建模**

**解析：**
NVIDIA BioNeMo 是一个面向 AI 驱动的药物发现和分子建模的专用框架。它提供：

**关键能力：**
- **MegaMolBART**：分子生成和优化
- **ESMFold**：蛋白质结构预测
- **DiffDock**：分子对接
- **NVIDIA Clara**：药物发现流水线

**EKS 上的用例：**
- 生成新的候选药物
- 预测蛋白质-配体相互作用
- 优化分子性质
- 高通量虚拟筛选

**部署要求：**
```yaml
resources:
  limits:
    nvidia.com/gpu: 8      # Multiple GPUs for large models
    memory: "500Gi"        # High memory for molecular datasets
```

与基于 CPU 的方法相比，BioNeMo 利用 NVIDIA 的 GPU 加速显著提升计算化学工作流的速度。

</details>

### 7. 哪个 Neuron SDK 包为 Trainium 上的 HuggingFace 模型提供高级训练 API？

A) torch-neuronx
B) tensorflow-neuronx
C) optimum-neuron
D) transformers-neuronx

<details>
<summary>显示答案</summary>

**答案：C) optimum-neuron**

**解析：**
Neuron SDK 包含多个用途不同的包：

| 包 | 用途 | 级别 |
|---------|---------|-------|
| **torch-neuronx** | 核心 PyTorch 集成 | 低级 |
| **tensorflow-neuronx** | 核心 TensorFlow 集成 | 低级 |
| **transformers-neuronx** | 面向 transformers 的优化推理 | 中级 |
| **optimum-neuron** | 高级训练/推理 API | 高级 |

**optimum-neuron** 是 HuggingFace Optimum 库的一部分，并提供：
- `NeuronTrainer`：HuggingFace Trainer 的即插即用替代品
- `NeuronTrainingArguments`：带有 Neuron 特定选项的训练配置
- 自动张量并行配置
- 与分布式训练集成（ZeRO、流水线并行）
- 与标准 HuggingFace 模型的 checkpoint 兼容性

使用示例：
```python
from optimum.neuron import NeuronTrainer, NeuronTrainingArguments

training_args = NeuronTrainingArguments(
    tensor_parallel_size=8,
    bf16=True,
)
trainer = NeuronTrainer(model=model, args=training_args)
trainer.train()
```

</details>

### 8. 在 EKS 上进行高吞吐分布式训练数据访问时，推荐的存储方案是什么？

A) Amazon EBS gp3
B) Amazon EFS
C) FSx for Lustre
D) Amazon S3 直接访问

<details>
<summary>显示答案</summary>

**答案：C) FSx for Lustre**

**解析：**
由于以下原因，FSx for Lustre 是分布式 ML 训练的推荐存储：

**性能特征：**
- 高达 1+ TB/s 的聚合吞吐量
- 亚毫秒级延迟
- 针对 HPC/ML 工作负载优化的并行文件系统

**面向 ML 训练的关键特性：**
- **S3 集成**：与 S3 数据存储库自动导入/导出数据
- **ReadWriteMany**：多个 Pod 可以同时访问
- **高 IOPS**：对训练中的随机访问模式至关重要
- **Checkpoint 支持**：训练期间快速写入 checkpoint

**对比：**

| 存储 | 吞吐量 | 访问模式 | 最适合 |
|---------|------------|-------------|----------|
| FSx Lustre | 非常高 | ReadWriteMany | 训练数据、checkpoint |
| EFS | 中等 | ReadWriteMany | 共享配置、模型 |
| EBS | 高 | ReadWriteOnce | 单节点工作负载 |
| S3 | 可变 | 对象 | 冷数据、归档 |

配置示例：
```yaml
lustreConfiguration:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: 250  # MB/s per TiB
  dataRepositoryAssociations:
    - fileSystemPath: /data
      dataRepositoryPath: s3://bucket/training-data
```

</details>

### 9. 在设置了 `minAvailable: 4` 的 Volcano Job 中，如果只有 3 个节点可用，会发生什么？

A) 作业会以 3 个 worker 启动
B) 作业会等待直到 4 个节点可用
C) 作业会立即失败
D) 作业会向 Karpenter 请求额外节点

<details>
<summary>显示答案</summary>

**答案：B) 作业会等待直到 4 个节点可用**

**解析：**
Volcano 中的 `minAvailable` 字段实现了 **Gang Scheduling**，它确保所有必需的 Pod 要么一起被调度，要么全部不调度。

**Gang Scheduling 行为：**
- 如果设置了 `minAvailable: 4`，则所有 4 个 Pod 必须能够同时被调度
- 作业会保持 pending 状态，直到资源可用
- 防止分布式训练中的死锁情况
- 确保一致的训练环境

**为什么这对 ML 训练很重要：**
1. **分布式训练需要所有 worker**：训练无法在只有部分 worker 的情况下继续
2. **资源效率**：防止浪费资源的部分分配
3. **确定性行为**：训练以预期的并行度启动

示例：
```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
spec:
  minAvailable: 4  # Gang scheduling requirement
  tasks:
    - name: worker
      replicas: 4
```

如果没有 gang scheduling，一些 worker 可能会启动，而另一些仍处于 pending 状态，从而导致超时和训练作业失败。

</details>

### 10. 训练时使用 BF16 (bfloat16) 相比 FP16 的好处是什么？

A) 更高精度
B) 不需要 loss scaling
C) 更小的内存占用
D) 更快的计算

<details>
<summary>显示答案</summary>

**答案：B) 不需要 loss scaling**

**解析：**
BF16 (Brain Floating Point 16) 与 FP32 具有相同的指数范围，但尾数精度更低：

| 格式 | 指数位 | 尾数位 | 范围 |
|--------|--------------|---------------|-------|
| FP32 | 8 | 23 | 大 |
| FP16 | 5 | 10 | 有限 |
| BF16 | 8 | 7 | 大（与 FP32 相同） |

**为什么 BF16 不需要 loss scaling：**
- BF16 的 8 个指数位提供与 FP32 相同的动态范围
- FP16 的有限范围会在训练期间导致下溢/上溢
- Loss scaling 会人为放大梯度，以防止 FP16 中的下溢

**BF16 优势：**
```python
# FP16 requires loss scaling
scaler = GradScaler()
with autocast(dtype=torch.float16):
    loss = model(inputs)
scaler.scale(loss).backward()
scaler.step(optimizer)

# BF16 is simpler - no scaling needed
with autocast(dtype=torch.bfloat16):
    loss = model(inputs)
loss.backward()
optimizer.step()
```

BF16 支持于：
- NVIDIA A100、H100 GPU（Ampere 及更新架构）
- AWS Trainium 芯片
- Intel Sapphire Rapids CPU

</details>

### 11. 梯度 checkpointing 在训练过程中实现了什么？

A) 更快的 forward pass
B) 降低通信开销
C) 通过重新计算 activations 节省内存
D) 提升模型准确率

<details>
<summary>显示答案</summary>

**答案：C) 通过重新计算 activations 节省内存**

**解析：**
梯度 checkpointing（也称为 activation checkpointing）通过在 forward pass 期间选择性存储 activations，并在 backpropagation 期间重新计算它们，用计算换取内存。

**工作方式：**
1. **不使用 checkpointing**：所有 activations 都存储在内存中
2. **使用 checkpointing**：只存储 checkpoint activations；中间 activations 在 backward pass 期间重新计算

**内存节省：**
- 将 activation 内存从 O(n) 降低到 O(sqrt(n))，其中 n 是层数
- 支持训练大 3-4 倍的 batch size
- 对于在有限 GPU 内存上训练大型模型至关重要

**PyTorch 中的配置：**
```python
from torch.utils.checkpoint import checkpoint

class Model(nn.Module):
    def forward(self, x):
        # Checkpoint specific layers
        x = checkpoint(self.layer1, x)
        x = checkpoint(self.layer2, x)
        return x

# Or enable for entire model
model.gradient_checkpointing_enable()
```

**权衡：**
- 计算时间增加约 30%
- activation 内存减少 3-4 倍
- 支持训练更大的模型/batch

</details>

### 12. DeepSpeed ZeRO 的哪个阶段会将优化器状态和模型参数都 offload 到 CPU 内存？

A) ZeRO Stage 1
B) ZeRO Stage 2
C) ZeRO Stage 3
D) ZeRO Stage 0

<details>
<summary>显示答案</summary>

**答案：C) ZeRO Stage 3**

**解析：**
DeepSpeed ZeRO (Zero Redundancy Optimizer) 会随着阶段逐步降低内存冗余：

| 阶段 | 分区内容 | 可用的 CPU Offload |
|-------|------------|----------------------|
| Stage 0 | 无（基线） | 否 |
| Stage 1 | 优化器状态 | 优化器状态 |
| Stage 2 | 优化器状态 + 梯度 | 优化器状态 |
| Stage 3 | 优化器状态 + 梯度 + 参数 | 优化器和参数两者 |

**ZeRO Stage 3 配置：**
```json
{
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {
      "device": "cpu",
      "pin_memory": true
    },
    "offload_param": {
      "device": "cpu",
      "pin_memory": true
    }
  }
}
```

**何时使用 ZeRO-3：**
- 训练大于 GPU 内存的模型
- 当你需要最高内存效率时
- 可以接受用一定速度换取内存时

**内存减少（近似）：**
- Stage 1：减少 4 倍
- Stage 2：减少 8 倍
- Stage 3：随 GPU 数量线性扩展（理论上无限）

</details>

### 13. MPIJob 规范中的 `slotsPerWorker` 字段用途是什么？

A) 每个 worker 的 CPU 核心数
B) 每个 worker 的 GPU 设备数
C) 每个 worker 的 MPI 进程数
D) 每个 worker 的网络接口数

<details>
<summary>显示答案</summary>

**答案：C) 每个 worker 的 MPI 进程数**

**解析：**
在 MPIJob 中，`slotsPerWorker` 定义每个 worker Pod 将运行多少个 MPI rank（进程）：

```yaml
apiVersion: kubeflow.org/v1
kind: MPIJob
spec:
  slotsPerWorker: 8  # 8 MPI processes per worker
  mpiReplicaSpecs:
    Worker:
      replicas: 4  # 4 worker pods
```

**总 MPI 进程数 = slotsPerWorker × Worker replicas**
在此示例中：8 × 4 = 32 个 MPI 进程

**常见配置：**
- 将 `slotsPerWorker` 设置为等于每个节点的 GPU 数
- 每个 MPI rank 通常处理一个 GPU
- 对于 8-GPU 节点：`slotsPerWorker: 8`

**Launcher 命令示例：**
```yaml
command:
  - mpirun
  - -np
  - "32"  # Total processes (must match slots × workers)
  - -bind-to
  - none
  - -map-by
  - slot
```

这确保每个 GPU 恰好分配给一个 MPI 进程，从而在避免 GPU 争用的同时最大化并行度。

</details>

### 14. 对于长时间运行的训练作业，推荐的 checkpoint 频率策略是什么？

A) 仅在每个 epoch checkpoint
B) 每一步都 checkpoint，以获得最高安全性
C) 每 N 步 checkpoint，并保留最近 3-5 个 checkpoint
D) 不进行 checkpoint，以最大化训练速度

<details>
<summary>显示答案</summary>

**答案：C) 每 N 步 checkpoint，并保留最近 3-5 个 checkpoint**

**解析：**
最佳 checkpoint 策略需要在恢复能力、存储成本和训练开销之间取得平衡：

**推荐方法：**
```yaml
checkpoint:
  save_steps: 500           # Save every 500 steps
  save_total_limit: 5       # Keep only last 5 checkpoints
  save_on_each_node: false  # Save from rank 0 only
```

**为什么使用这种策略：**
1. **恢复粒度**：将数据丢失限制在最多约 500 步
2. **存储效率**：保留 3-5 个 checkpoint 可防止存储膨胀
3. **训练开销**：每一步 checkpoint 过慢
4. **仅按 epoch 存在风险**：长 epoch 意味着失败时会出现显著的数据丢失

**Checkpoint 大小注意事项：**
- 大型模型（70B+）：每个 checkpoint 可能为 100-200GB
- 5 个 checkpoint = 500GB-1TB 存储
- 对较旧的 checkpoint 使用 S3 lifecycle policies

**最佳实践：**
```python
training_args = TrainingArguments(
    save_strategy="steps",
    save_steps=500,
    save_total_limit=5,
    save_safetensors=True,  # Faster, safer format
)
```

对于生产训练，还应使用 checkpoint manager sidecar 将 checkpoint 同步到持久存储（S3）。

</details>

### 15. 哪个 Karpenter 配置可确保 GPU 训练 Pod 被调度到单个可用区，以获得最佳 EFA 性能？

A) `consolidationPolicy: WhenEmpty`
B) 带单个值的 `topology.kubernetes.io/zone` requirement
C) `karpenter.sh/capacity-type: spot`
D) `disruption.budgets.nodes: "0"`

<details>
<summary>显示答案</summary>

**答案：B) 带单个值的 `topology.kubernetes.io/zone` requirement**

**解析：**
EFA (Elastic Fabric Adapter) 要求所有通信实例位于同一个 Availability Zone。Karpenter 的 zone requirement 可确保这一点：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
spec:
  template:
    spec:
      requirements:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
            - us-west-2a  # Single AZ for EFA
```

**为什么单个 AZ 对 EFA 很重要：**
- EFA 使用 AWS 的自定义网络接口进行高带宽、低延迟通信
- 跨 AZ 通信无法使用 EFA 的 RDMA 能力
- 跨 AZ 时网络延迟会显著增加

**其他选项说明：**
- A) `consolidationPolicy`：控制节点合并，而不是放置位置
- C) `capacity-type: spot`：决定定价模型，而不是 zone
- D) `disruption.budgets`：防止节点中断，而不是 zone 选择

**GPU 训练的完整配置：**
```yaml
requirements:
  - key: node.kubernetes.io/instance-type
    operator: In
    values: [p4d.24xlarge]
  - key: topology.kubernetes.io/zone
    operator: In
    values: [us-west-2a]  # Single zone
  - key: karpenter.sh/capacity-type
    operator: In
    values: [on-demand]   # Stability for training
```

</details>

## 总结

本测验涵盖了 EKS 上模型训练的核心概念：

1. **分布式训练策略**：数据、张量、流水线和专家并行
2. **Slinky/Slurm 集成**：组件（slurmctld、slurmdbd、slurmd）和 CRD
3. **GPU 训练**：NCCL 配置、EFA 网络、BioNeMo
4. **Trainium 训练**：Neuron SDK 包、optimum-neuron
5. **存储**：用于高吞吐训练的 FSx for Lustre
6. **调度**：Volcano gang scheduling
7. **优化**：混合精度（BF16）、梯度 checkpointing、DeepSpeed ZeRO
8. **基础设施**：Karpenter NodePool、checkpoint 管理

更多信息请参阅 [EKS 上的模型训练](../../ai-ml/05-model-training.md) 文档。
