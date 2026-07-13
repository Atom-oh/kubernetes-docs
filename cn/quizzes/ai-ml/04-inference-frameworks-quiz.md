# 推理框架测验

本测验测试你对面向 Kubernetes 部署的 LLM 推理框架的理解，包括 NVIDIA NIM、NVIDIA Dynamo、AIBrix、Ray Serve 和 AWS Neuron。

## 测验题目

### 1. NVIDIA NIM 用于 LLM 部署的主要优势是什么？

A) 它只支持开源模型
B) 它通过优化的推理引擎和 OpenAI-compatible APIs 提供生产就绪、容器化的 LLM 部署
C) 它要求手动编译所有模型
D) 它只适用于 CPU 实例

<details>
<summary>显示答案</summary>

**答案：B) 它通过优化的推理引擎和 OpenAI-compatible APIs 提供生产就绪、容器化的 LLM 部署**

**解释：**
NVIDIA NIM (NVIDIA Inference Microservices) 提供生产就绪、容器化的 LLM 部署，并具备多项关键特性：

1. **优化的推理引擎**：使用 TensorRT-LLM 以获得最高性能
2. **OpenAI-Compatible APIs**：可直接替代 OpenAI API 调用
3. **内置监控**：Prometheus 指标和 Grafana 仪表板
4. **NGC Catalog 集成**：轻松访问预优化模型
5. **企业支持**：来自 NVIDIA 的生产 SLA 和支持

```yaml
# NIM deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nim-llama-70b
spec:
  template:
    spec:
      containers:
      - name: nim
        image: nvcr.io/nim/meta/llama-3.1-70b-instruct:1.2.0
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 8
```

</details>

### 2. NVIDIA Dynamo 中的“分离式服务”是什么？

A) 在单个 GPU 上运行多个模型
B) 将 prefill（提示处理）和 decode（Token 生成）阶段分离到不同的工作池中
C) 将日志分发到多个服务器
D) 在没有 GPU 的情况下运行推理

<details>
<summary>显示答案</summary>

**答案：B) 将 prefill（提示处理）和 decode（Token 生成）阶段分离到不同的工作池中**

**解释：**
分离式服务是 NVIDIA Dynamo 中的一种关键架构模式，它将 LLM 推理的两个主要阶段分开：

1. **Prefill 阶段**：
   - 处理输入提示
   - 计算密集型（需要高 FLOPs）
   - 受益于 A100 等高端 GPU

2. **Decode 阶段**：
   - 一次生成一个输出 Token
   - 内存带宽密集型
   - 可以使用 A10G 等更具成本效益的 GPU

**分离的优势：**
- 更好的资源利用率
- 通过异构 GPU 使用实现成本优化
- 更高的总体吞吐量
- 独立扩展 prefill 和 decode 容量

```yaml
# Dynamo configuration example
prefill:
  replicas: 2
  backend: vllm
  tensor_parallel_size: 8
  # Uses p4d.24xlarge with A100 GPUs

decode:
  replicas: 4
  backend: vllm
  tensor_parallel_size: 4
  # Uses g5.12xlarge with A10G GPUs
```

</details>

### 3. AIBrix 的哪个组件负责动态加载和管理 LoRA adapter？

A) Gateway
B) Autoscaler
C) LoRA Manager
D) Model Registry

<details>
<summary>显示答案</summary>

**答案：C) LoRA Manager**

**解释：**
AIBrix 由多个关键组件组成，每个组件都有特定职责：

1. **Gateway**：智能请求路由和负载均衡
2. **LoRA Manager**：动态加载和管理 LoRA adapter
3. **Autoscaler**：面向 inference Pod（容器组）的工作负载感知自动扩缩容
4. **Model Registry**：集中式模型和 adapter 管理

**LoRA Manager** 专门处理：
- 无需重启即可动态加载 LoRA adapter
- 在不同 adapter 之间热切换
- 多个 adapter 的内存管理
- Adapter 版本控制和生命周期

```bash
# Register a LoRA adapter
curl -X POST http://aibrix-registry:8081/v1/lora/register \
  -d '{
    "name": "customer-support",
    "base_model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_path": "s3://aibrix-models/lora/customer-support",
    "rank": 16,
    "alpha": 32
  }'

# Use LoRA in inference request
curl -X POST http://aibrix-gateway:8080/v1/chat/completions \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "lora_adapter": "customer-support",
    "messages": [{"role": "user", "content": "Help me"}]
  }'
```

</details>

### 4. 使用哪个 Kubernetes operator 来部署 Ray Serve 以进行分布式推理？

A) NVIDIA GPU Operator
B) KubeRay Operator
C) Prometheus Operator
D) Flux Operator

<details>
<summary>显示答案</summary>

**答案：B) KubeRay Operator**

**解释：**
KubeRay Operator 是用于部署和管理 Ray 集群的 Kubernetes 原生方式，包括用于分布式推理的 Ray Serve。

**KubeRay Operator 特性：**
- 管理 Ray 集群生命周期
- 支持 RayCluster、RayJob 和 RayService CRD
- 处理 Ray worker 的自动扩缩容
- 与 Kubernetes RBAC 和网络集成

**安装：**
```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace
```

**RayService 示例：**
```yaml
apiVersion: ray.io/v1
kind: RayService
metadata:
  name: vllm-serve
spec:
  serveConfigV2: |
    applications:
    - name: vllm-app
      import_path: serve_vllm:deployment
      deployments:
      - name: VLLMDeployment
        num_replicas: 2
        ray_actor_options:
          num_gpus: 1
  rayClusterConfig:
    workerGroupSpecs:
    - groupName: gpu-workers
      replicas: 2
      maxReplicas: 8
```

</details>

### 5. 使用 AWS Inferentia2 (inf2) 实例进行 LLM 推理的主要优势是什么？

A) 比 A100 拥有更高的 GPU 内存
B) 与 GPU 实例相比，成本最多降低 70%
C) 模型编译时间更快
D) 更好地支持训练工作负载

<details>
<summary>显示答案</summary>

**答案：B) 与 GPU 实例相比，成本最多降低 70%**

**解释：**
AWS Inferentia2 为推理工作负载提供显著的成本优势：

**成本优势：**
- 与同类 GPU 实例相比，成本最多降低 70%
- 每美元高吞吐量
- 适合仅推理工作负载

**支持的模型：**
- Llama 2/3
- Mistral
- Stable Diffusion
- 各种 encoder 模型

**实例类型：**
| 实例 | Neuron Cores | 内存 | 用例 |
|----------|--------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | 7B 模型 |
| inf2.24xlarge | 6 | 96 GB | 13B-70B 模型 |
| inf2.48xlarge | 12 | 192 GB | 70B+ 模型 |

**权衡：**
- 需要为 Neuron 编译模型
- 与 GPU 相比，模型支持有限
- 初始设置时间更长

```yaml
# Neuron resource request
resources:
  limits:
    aws.amazon.com/neuron: 2
    memory: 32Gi
  requests:
    aws.amazon.com/neuron: 2
```

</details>

### 6. 哪个指标衡量 LLM 推理中生成第一个 Token 之前的时间？

A) ITL (Inter-Token Latency)
B) TTFT (Time to First Token)
C) TPS (Tokens Per Second)
D) QPS (Queries Per Second)

<details>
<summary>显示答案</summary>

**答案：B) TTFT (Time to First Token)**

**解释：**
TTFT (Time to First Token) 是 LLM 推理中的关键延迟指标，用于衡量用户在看到任何输出之前等待的时间。

**关键 LLM 推理指标：**

1. **TTFT (Time to First Token)**：
   - 从提交请求到第一个 Token 的时间
   - 包括提示处理（prefill）时间
   - 目标：良好 UX 低于 500ms

2. **ITL (Inter-Token Latency)**：
   - 连续生成 Token 之间的时间
   - 影响感知到的流式输出速度
   - 目标：低于 50ms

3. **吞吐量**：
   - 每秒生成的 Token 数
   - 衡量系统容量

4. **E2E 延迟**：
   - 完整响应的总时间
   - TTFT + (ITL * output_tokens)

**监控示例：**
```promql
# TTFT P99
histogram_quantile(0.99, sum(rate(nim_time_to_first_token_bucket[5m])) by (le))

# ITL P99
histogram_quantile(0.99, sum(rate(nim_inter_token_latency_bucket[5m])) by (le))

# Throughput
sum(rate(nim_tokens_generated_total[5m]))
```

</details>

### 7. 在 NVIDIA Dynamo 中，KV-aware routing 的目的是什么？

A) 根据用户位置路由请求
B) 根据 KV cache 局部性路由请求，以获得最佳性能
C) 将请求路由到最便宜的实例
D) 根据模型版本路由请求

<details>
<summary>显示答案</summary>

**答案：B) 根据 KV cache 局部性路由请求，以获得最佳性能**

**解释：**
NVIDIA Dynamo 中的 KV-aware routing 会根据 KV cache 数据的位置优化请求路由，通过减少数据传输来提升性能。

**KV-aware Routing 的工作方式：**

1. **KV Cache 跟踪**：router 跟踪哪些 decode worker 已缓存先前请求的 KV 数据
2. **局部性优化**：将后续请求（在多轮对话中）路由到已经具有相关 KV cache 的 worker
3. **负载均衡**：在局部性收益和 worker 负载之间取得平衡

**配置：**
```yaml
router:
  kv_routing:
    enabled: true
    locality_weight: 0.7  # Prefer cache locality
    load_weight: 0.3      # Consider worker load
```

**优势：**
- 降低多轮对话的 TTFT
- 降低内存压力（避免重复 KV cache）
- 更好的 GPU 内存利用率
- 更高的有效吞吐量

**路由决策公式：**
```
score = locality_weight * cache_hit_score + load_weight * (1 - worker_load)
```

</details>

### 8. 使用哪个命令安装 Kubernetes 的 Neuron device plugin？

A) `kubectl apply -f nvidia-device-plugin.yml`
B) `helm install neuron-plugin aws/neuron`
C) `kubectl apply -f k8s-neuron-device-plugin.yml`
D) `eksctl create addon --name neuron-device-plugin`

<details>
<summary>显示答案</summary>

**答案：C) `kubectl apply -f k8s-neuron-device-plugin.yml`**

**解释：**
Neuron device plugin 使用 kubectl apply，并通过 AWS Neuron SDK repository 的官方 manifest 进行安装。

**安装命令：**
```bash
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml
```

**验证：**
```bash
# Check DaemonSet
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# Check Neuron devices on nodes
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

**资源请求格式：**
```yaml
resources:
  limits:
    aws.amazon.com/neuron: 2  # Request 2 Neuron cores
```

NVIDIA device plugin 使用 `nvidia.com/gpu`，而 Neuron 使用 `aws.amazon.com/neuron`。

</details>

### 9. 哪个推理框架将内置自动扩缩容作为核心特性提供？

A) vLLM standalone
B) NVIDIA NIM
C) AIBrix
D) Triton Inference Server

<details>
<summary>显示答案</summary>

**答案：C) AIBrix**

**解释：**
AIBrix 将内置的、工作负载感知的自动扩缩容作为核心特性提供，而其他框架需要 HPA 或 KEDA 等外部解决方案。

**AIBrix Autoscaler 特性：**
- 工作负载感知的扩缩容策略
- 支持多个指标（RPS、延迟、GPU 利用率、队列深度）
- 可配置的扩容/缩容行为
- 按部署设置扩缩容策略

**AIBrix Autoscaler 配置：**
```yaml
autoscaler:
  enabled: true
  poll_interval: 30s
  scaling_policies:
    - name: default
      min_replicas: 2
      max_replicas: 10
      target_metrics:
        - name: requests_per_second
          target: 50
        - name: gpu_utilization
          target: 80
        - name: queue_depth
          target: 20
      scale_up:
        stabilization_window: 60s
        step_size: 2
      scale_down:
        stabilization_window: 300s
        step_size: 1
```

**比较：**
| 框架 | 自动扩缩容 |
|-----------|--------------|
| NIM | 手动（外部 HPA/KEDA） |
| Dynamo | 手动（外部） |
| AIBrix | 内置 |
| vLLM | 手动（外部） |
| Ray Serve | 内置 |
| Triton | 手动（外部） |

</details>

### 10. NGC Catalog 在 NVIDIA NIM 部署中的用途是什么？

A) 存储 Kubernetes manifests
B) 提供预优化的模型容器和配置
C) 管理集群网络
D) 处理用户身份验证

<details>
<summary>显示答案</summary>

**答案：B) 提供预优化的模型容器和配置**

**解释：**
NGC (NVIDIA GPU Cloud) Catalog 是 NVIDIA 面向 GPU 优化软件的仓库，其中包括带有优化模型的预构建 NIM 容器。

**NGC Catalog 特性：**
- 预优化的模型容器
- 多种模型 profile（不同的 batch size、precision）
- 版本管理
- 安全扫描
- 企业支持

**访问 NGC：**
```bash
# Create NGC API key secret
kubectl create secret generic ngc-api-key \
  --from-literal=NGC_API_KEY='your-ngc-api-key'

# Create docker config secret for image pull
kubectl create secret docker-registry ngc-credentials \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password='your-ngc-api-key'
```

**使用 NGC Images：**
```yaml
spec:
  imagePullSecrets:
  - name: ngc-credentials
  containers:
  - name: nim
    image: nvcr.io/nim/meta/llama-3.1-70b-instruct:1.2.0
    env:
    - name: NGC_API_KEY
      valueFrom:
        secretKeyRef:
          name: ngc-api-key
          key: NGC_API_KEY
```

**可用的 NIM Profiles：**
- `vllm-bf16-tp8`: 8-GPU tensor parallel, BF16 precision
- `vllm-fp8-tp4`: 4-GPU tensor parallel, FP8 precision
- `tensorrt-llm-fp16-tp8`: TensorRT-LLM backend

</details>

### 11. NVIDIA Dynamo 支持哪些推理 backend？

A) 仅 TensorRT-LLM
B) vLLM、SGLang 和 TensorRT-LLM
C) 仅 vLLM
D) 仅 PyTorch

<details>
<summary>显示答案</summary>

**答案：B) vLLM、SGLang 和 TensorRT-LLM**

**解释：**
NVIDIA Dynamo 旨在与 backend 无关，并支持多个推理引擎：

1. **vLLM**：
   - 开源、高性能
   - 使用 PagedAttention 提升内存效率
   - 广泛的模型支持

2. **SGLang**：
   - 针对结构化生成进行了优化
   - 快速 JSON/regex 约束解码
   - 高效的前缀缓存

3. **TensorRT-LLM**：
   - 最高的 NVIDIA GPU 性能
   - 优化 kernel
   - INT8/FP8 量化

**配置示例：**
```yaml
# Using vLLM backend for prefill
prefill:
  backend: vllm
  model: meta-llama/Llama-3.1-70B-Instruct
  tensor_parallel_size: 8

# Using SGLang backend for decode
decode:
  backend: sglang
  model: meta-llama/Llama-3.1-70B-Instruct
  tensor_parallel_size: 4

# Or using TensorRT-LLM
prefill:
  backend: tensorrt-llm
  engine_path: /models/llama-70b-trt
```

这种灵活性允许：
- 混合 backend 以获得最佳性能
- 测试不同引擎
- 为特定任务使用专用 backend

</details>

### 12. 在 EKS 上处理 vLLM 部署的模型存储，推荐方式是什么？

A) 将模型存储在 ConfigMaps 中
B) 每次容器启动时下载模型
C) 使用 FSx for Lustre 或带有预下载模型的 persistent volumes
D) 将模型嵌入容器镜像中

<details>
<summary>显示答案</summary>

**答案：C) 使用 FSx for Lustre 或带有预下载模型的 persistent volumes**

**解释：**
对于生产级 LLM 部署，使用高性能持久化存储至关重要：

**推荐的存储选项：**

1. **FSx for Lustre**：
   - 高吞吐量并行文件系统
   - 非常适合大型模型文件
   - 用于模型更新的 S3 集成
   - 吞吐量最高可达 1000+ MB/s

2. **EBS gp3 Volumes**：
   - 适合单节点部署
   - 成本效益高
   - 最高可达 16,000 IOPS

3. **EFS**：
   - 跨 Pod 共享访问
   - 吞吐量低于 FSx
   - 适合较小模型

**FSx for Lustre 设置：**
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache
spec:
  accessModes:
  - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

**为什么不选择其他选项：**
- **ConfigMaps**：1MB 大小限制，不适合大型文件
- **启动时下载**：启动慢、带宽成本高、存在可靠性问题
- **嵌入镜像**：镜像巨大、拉取慢、版本不灵活

</details>

### 13. GenAI-Perf 在 NIM 部署中的作用是什么？

A) 生成 AI 图像
B) 对 LLM 推理性能进行基准测试和分析
C) 管理 GPU 内存
D) 配置 network policies

<details>
<summary>显示答案</summary>

**答案：B) 对 LLM 推理性能进行基准测试和分析**

**解释：**
GenAI-Perf 是 NVIDIA 用于对生成式 AI 推理性能进行基准测试和分析的工具。

**特性：**
- 衡量 TTFT、ITL、吞吐量
- 支持并发请求测试
- 多种 endpoint 类型（chat、completion）
- 导出结果用于分析

**安装：**
```bash
pip install genai-perf
```

**使用示例：**
```bash
genai-perf \
  --endpoint-type chat \
  --service-kind openai \
  --url http://nim-inference:8000/v1 \
  --model meta/llama-3.1-70b-instruct \
  --concurrency 16 \
  --input-sequence-length 512 \
  --output-sequence-length 256 \
  --num-prompts 100 \
  --profile-export-file nim-benchmark.json

# Analyze results
genai-perf analyze nim-benchmark.json
```

**报告的关键指标：**
- Time to First Token (P50, P90, P99)
- Inter-Token Latency (P50, P90, P99)
- 请求吞吐量
- Token 吞吐量
- 基准测试期间的 GPU 利用率

</details>

### 14. 哪种 Kubernetes 资源类型最适合部署跨多个 Pod 的、使用 tensor parallelism 的分布式 vLLM？

A) Deployment
B) StatefulSet
C) DaemonSet
D) ReplicaSet

<details>
<summary>显示答案</summary>

**答案：B) StatefulSet**

**解释：**
StatefulSet 适合需要以下能力的分布式 vLLM 部署：

1. **稳定的网络身份**：每个 Pod 都获得可预测的 hostname（vllm-0、vllm-1 等）
2. **有序部署**：Pod 按顺序创建，这对 master/worker 协调很重要
3. **稳定存储**：每个 Pod 可以拥有自己的 persistent volume
4. **Headless Service**：用于 NCCL 的直接 Pod 到 Pod 通信

**StatefulSet 配置：**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vllm-distributed
spec:
  serviceName: "vllm-distributed"
  replicas: 2
  selector:
    matchLabels:
      app: vllm-distributed
  template:
    metadata:
      labels:
        app: vllm-distributed
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        env:
        - name: MASTER_ADDR
          value: "vllm-distributed-0.vllm-distributed"
        - name: MASTER_PORT
          value: "29500"
        ports:
        - containerPort: 8000
        - containerPort: 29500  # NCCL communication
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-distributed
spec:
  clusterIP: None  # Headless service
  selector:
    app: vllm-distributed
```

**为什么选择 StatefulSet 而不是 Deployment：**
- Deployment 不保证稳定的 hostname
- NCCL 需要可预测的寻址
- Master election 需要一致的 Pod 身份

</details>

### 15. 哪个环境变量控制容器可见的 Neuron cores 数量？

A) CUDA_VISIBLE_DEVICES
B) NEURON_RT_VISIBLE_CORES
C) AWS_NEURON_CORES
D) NEURON_DEVICE_COUNT

<details>
<summary>显示答案</summary>

**答案：B) NEURON_RT_VISIBLE_CORES**

**解释：**
`NEURON_RT_VISIBLE_CORES` 控制容器内 Neuron runtime 可见的 Neuron cores。

**关键 Neuron 环境变量：**

1. **NEURON_RT_VISIBLE_CORES**：
   - 指定要使用哪些 cores
   - 格式："0,1" 或 "0-3"
   ```yaml
   env:
   - name: NEURON_RT_VISIBLE_CORES
     value: "0,1"
   ```

2. **NEURON_RT_NUM_CORES**：
   - 要使用的 cores 总数
   ```yaml
   env:
   - name: NEURON_RT_NUM_CORES
     value: "2"
   ```

3. **NEURON_CC_FLAGS**：
   - 模型编译的 compiler flags
   ```yaml
   env:
   - name: NEURON_CC_FLAGS
     value: "--model-type transformer"
   ```

**完整示例：**
```yaml
containers:
- name: vllm-neuron
  image: public.ecr.aws/neuron/pytorch-inference-neuronx:latest
  env:
  - name: NEURON_RT_NUM_CORES
    value: "2"
  - name: NEURON_RT_VISIBLE_CORES
    value: "0,1"
  - name: NEURON_CC_FLAGS
    value: "--model-type transformer"
  resources:
    limits:
      aws.amazon.com/neuron: 2
```

注意：`CUDA_VISIBLE_DEVICES` 用于 NVIDIA GPU，而不是 Neuron。

</details>
