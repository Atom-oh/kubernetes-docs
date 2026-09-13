# vLLM 部署与优化

> **支持的版本**: Kubernetes 1.31, 1.32, 1.33  
> **最后更新**: September 4, 2026

vLLM 是应用最广泛的开源高性能 Large Language Models（LLMs）推理引擎。在本章中，我们将探讨 vLLM 的最新功能和架构，并学习如何在 EKS 上以生产规模部署和优化它。

## 实验环境设置

要跟随本文档中的示例操作，您需要以下工具和环境：

### 所需工具和资源
- kubectl v1.31 或更高版本
- Helm v3.10 或更高版本
- 配备 NVIDIA GPUs 的 EKS 集群（最低推荐：g5.2xlarge 实例）
- 已安装 NVIDIA 驱动程序和 NVIDIA Device Plugin
- 至少 50GB 磁盘空间

### GPU 节点设置

```bash
# Install NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU nodes
kubectl get nodes "-o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu"
```

## vLLM 简介

vLLM 是具有以下特性的 LLM 推理引擎：

![展示 vLLM 核心功能、其内部组件流水线，以及内存效率和高吞吐量等最终优势的图表。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-0.svg)

### vLLM 的关键功能

1. **PagedAttention**:
   - 高效管理 KV cache 的内存管理技术
   - 受操作系统虚拟内存管理启发
   - 可实现最多 10 倍的并发请求处理能力

2. **Continuous Batching**:
   - 动态批处理请求以最大化 GPU 利用率
   - 新请求到达后立即开始处理
   - 吞吐量最高提升 2 倍

3. **Distributed Inference**:
   - 通过 tensor parallelization 支持大规模模型
   - 跨多个 GPU 进行模型分片
   - 支持 175B+ 参数模型

4. **Quantization**:
   - 支持包括 INT8、FP16 在内的多种精度
   - 降低内存使用并提升推理速度
   - 在精度损失极小的情况下，内存效率最高提升 2 倍

## 支持的模型

vLLM 支持以下模型：

| 模型系列 | 支持的模型 | 量化选项 |
|-------------|-----------------|---------------------|
| **LLaMA 3 / 3.1 / 3.2 / 3.3** | 1B, 3B, 8B, 70B, 405B | FP16, BF16, FP8, INT8, INT4, AWQ, GPTQ |
| **DeepSeek V3 / R1** | 7B, 67B, 671B (MoE) | FP16, BF16, FP8, AWQ, GPTQ |
| **Qwen 2 / 2.5 / QwQ** | 0.5B ~ 72B | FP16, BF16, FP8, INT8, AWQ, GPTQ |
| **Mistral / Mixtral** | 7B, 8x7B, 8x22B, Large 2 | FP16, BF16, FP8, AWQ, GPTQ |
| **Gemma 2 / 3** | 2B, 9B, 27B | FP16, BF16, INT8 |
| **Phi-3 / Phi-4** | 3.8B, 7B, 14B | FP16, BF16, INT8, AWQ |
| **Command R / R+** | 35B, 104B | FP16, BF16 |
| **DBRX** | 132B (MoE) | FP16, BF16 |
| **StarCoder 2** | 3B, 7B, 15B | FP16, BF16 |
| **Vision Models (VLM)** | LLaVA, Pixtral, Qwen2-VL, InternVL | FP16, BF16 |

1. **PagedAttention**: 在处理长序列时优化内存使用的内存高效注意力机制。
2. **Continuous Batching**: 动态批处理请求以提高吞吐量。
3. **Distributed Inference**: 将模型分布到多个 GPU 和节点上，以处理大规模模型。
4. **Quantization**: 支持 INT8/INT4 量化，以降低内存使用并提高吞吐量。
5. **OpenAI Compatible API**: 提供与 OpenAI API 兼容的接口。

### v0.6 系列中新增的 vLLM 功能

vLLM 正在快速发展，最近的版本带来了重要的新功能：

#### Speculative Decoding

使用较小的草稿模型生成多个候选 token，再由较大的模型在一次传递中验证，从而将推理速度提升 2-3 倍：

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --speculative-model meta-llama/Llama-3.1-8B-Instruct \
  --num-speculative-tokens 5
```

#### Prefix Caching

自动在共享相同 system prompt 或上下文的请求间复用 KV cache，显著缩短 TTFT（Time to First Token）：

```bash
--enable-prefix-caching
```

#### Chunked Prefill

将长 prompt prefill 拆分成与 decode 步骤交错执行的较小块，降低长上下文请求对其他请求延迟的影响：

```bash
--enable-chunked-prefill --max-num-batched-tokens 2048
```

#### Dynamic LoRA Adapter Loading

在运行时动态加载/卸载多个 LoRA adapter，从单个基础模型提供许多定制模型：

```bash
--enable-lora --max-loras 4 --max-lora-rank 64
```

```python
# Specify LoRA model in API request
response = client.chat.completions.create(
    model="my-custom-lora-adapter",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

#### Structured Output

通过 JSON Schema、regex patterns 和 CFG（Context-Free Grammar）支持受约束的输出生成，以实现可靠的结构化数据生成：

```python
from openai import OpenAI
client = OpenAI(base_url="http://vllm-service:8000/v1")

response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "Return user information as JSON"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "user_info",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "email": {"type": "string"}
                },
                "required": ["name", "age", "email"]
            }
        }
    }
)
```

#### Tool Calling

支持与 OpenAI 兼容的 Tool/Function Calling，以集成 agent 工作流：

```python
response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "What's the weather in Seoul?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a specified location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"]
            }
        }
    }]
)
```

#### FP8 Quantization

在 Hopper (H100) 和 Ada Lovelace (L4, L40S) GPUs 上支持 FP8 quantization，在保持近乎相同精度的同时将内存使用减半：

```bash
--quantization fp8 --kv-cache-dtype fp8
```

#### Vision-Language Model (VLM) Serving

支持同时处理图像和文本的多模态模型：

```python
response = client.chat.completions.create(
    model="llava-hf/llava-v1.6-mistral-7b-hf",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
    }]
)
```

## 系统要求

在 EKS 上部署 vLLM 的系统要求：

![展示 vLLM 的硬件和软件前提条件，以及 GPU 内存如何决定支持的模型规模层级的图表。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-1.svg)

1. **硬件**:
   - NVIDIA GPU（Volta、Turing、Ampere、Hopper 架构）
   - 最低 GPU 内存：因模型大小而异
     - 7B 模型：最低 16GB GPU 内存
     - 13B 模型：最低 24GB GPU 内存
     - 70B 模型：最低 80GB GPU 内存（或分布到多个 GPU）

2. **软件**:
   - CUDA 12.1 或更高版本（FP8 推荐 CUDA 12.4）
   - Python 3.9 或更高版本
   - PyTorch 2.4.0 或更高版本

3. **EKS 节点类型**:
   - p5.48xlarge: 8x NVIDIA H100 GPU，每个 80GB（最高性能）
   - p4d.24xlarge: 8x NVIDIA A100 GPU，每个 40GB 或 80GB
   - g6.12xlarge: 4x NVIDIA L4 GPU，每个 24GB（经济高效）
   - g5.12xlarge: 4x NVIDIA A10G GPU，每个 24GB
   - g6e.12xlarge: 4x NVIDIA L40S GPU，每个 48GB
   - trn1.32xlarge: 16x AWS Trainium，每个 32GB（AWS 芯片）

## EKS 基础设施配置

![在 Amazon EKS 集群中运行 vLLM 的架构图：包含 control plane、GPU 和 CPU node groups、存储与网络资源，以及支持性的 AWS 服务。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-2.svg)

## 存储配置

vLLM 需要高性能存储，因为它需要加载大型模型权重：

### FSx for Lustre 设置

FSx for Lustre 是适合快速加载大型模型权重的高性能并行文件系统：

```yaml
apiVersion: fsx.aws.k8s.io/v1beta1
kind: Lustre
metadata:
  name: vllm-models
spec:
  deploymentType: SCRATCH_2
  storageCapacity: 1200
  subnetIds:
    - subnet-0123456789abcdef0
  securityGroupIds:
    - sg-0123456789abcdef0
  perUnitStorageThroughput: 200
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
parameters:
  fileSystemId: fs-0123456789abcdef0
  mountName: vllm-models
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

### 从 S3 下载模型

将 Hugging Face 模型存储到 S3 并下载到 FSx for Lustre 的 Job：

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: model-download
spec:
  template:
    spec:
      containers:
      - name: model-download
        image: huggingface/transformers:latest
        command:
        - python
        - -c
        - |
          from huggingface_hub import snapshot_download
          import os

          model_id = "meta-llama/Llama-3.1-70B-Instruct"
          dest_dir = "/models/llama-3.1-70b"

          os.makedirs(dest_dir, exist_ok=True)
          snapshot_download(repo_id=model_id, local_dir=dest_dir, token=os.environ["HF_TOKEN"])
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: huggingface-token
              key: token
        volumeMounts:
        - name: models-volume
          mountPath: /models
      restartPolicy: Never
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
```

## vLLM 部署

### 部署架构

下图展示了在 EKS 上部署 vLLM 的两种主要架构：

![比较单节点 vLLM Pod 部署和多节点 NCCL 同步部署的图表，两者均由 load balancer 提供流量并共享由 FSx/S3 支持的存储。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-3.svg)

### 单节点部署

在单个 GPU 或单节点上的多个 GPU 上运行 vLLM 的 Deployment：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      containers:
      - name: vllm-server
        image: vllm/vllm-openai:latest
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        - --model=/models/llama-3.1-70b
        - --tensor-parallel-size=8
        - --gpu-memory-utilization=0.95
        - --max-num-batched-tokens=16384
        - --enable-prefix-caching
        - --enable-chunked-prefill
        - --port=8000
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 8
        volumeMounts:
        - name: models-volume
          mountPath: /models
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4,5,6,7"
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### 多节点分布式部署

跨多个节点分配大型模型的方法：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-config
data:
  hostfile: |
    vllm-inference-0 slots=8
    vllm-inference-1 slots=8
  run_server.sh: |
    #!/bin/bash

    RANK=$HOSTNAME
    if [[ $HOSTNAME == "vllm-inference-0" ]]; then
      RANK=0
    elif [[ $HOSTNAME == "vllm-inference-1" ]]; then
      RANK=1
    fi

    python -m vllm.entrypoints.openai.api_server \
      --model=/models/llama-3.1-70b \
      --tensor-parallel-size=16 \
      --pipeline-parallel-size=1 \
      --max-num-batched-tokens=8192 \
      --port=8000 \
      --host=0.0.0.0 \
      --master-addr=vllm-inference-0 \
      --master-port=29500 \
      --rank=$RANK
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vllm-inference
spec:
  serviceName: "vllm-inference"
  replicas: 2
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - vllm-inference
            topologyKey: kubernetes.io/hostname
      containers:
      - name: vllm-server
        image: vllm/vllm-openai:latest
        command:
        - bash
        - /config/run_server.sh
        ports:
        - containerPort: 8000
        - containerPort: 29500
        resources:
          limits:
            nvidia.com/gpu: 8
        volumeMounts:
        - name: models-volume
          mountPath: /models
        - name: config-volume
          mountPath: /config
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4,5,6,7"
        - name: NCCL_DEBUG
          value: "INFO"
        - name: NCCL_IB_DISABLE
          value: "0"
        - name: NCCL_IB_GID_INDEX
          value: "3"
        - name: NCCL_NET_GDR_LEVEL
          value: "5"
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
      - name: config-volume
        configMap:
          name: vllm-config
          defaultMode: 0755
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8000
    targetPort: 8000
    name: api
  - port: 29500
    targetPort: 29500
    name: nccl
  clusterIP: None
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference-lb
spec:
  selector:
    app: vllm-inference
    statefulset.kubernetes.io/pod-name: vllm-inference-0
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

## 性能优化

![展示 GPU 内存、吞吐量和网络优化技术及其各自配置 flag 的图表，它们共同带来整体性能提升。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-4.svg)

### GPU 内存优化

优化 vLLM GPU 内存使用的方法：

1. **GPU 内存利用率调整**:

```bash
--gpu-memory-utilization=0.9
```

2. **应用量化**:

```bash
--quantization awq
```

3. **使用 Swap Space**:

```bash
--swap-space=16
```

### 吞吐量优化

优化 vLLM 吞吐量的方法：

1. **批处理大小调整**:

```bash
--max-num-batched-tokens=8192
```

2. **KV Cache 优化**:

```bash
--block-size=16
```

3. **Tensor Parallel Processing 调整**:

```bash
--tensor-parallel-size=8
```

### 网络优化

在分布式部署中优化网络性能的方法：

1. **使用 EFA (Elastic Fabric Adapter)**:

```yaml
resources:
  limits:
    nvidia.com/gpu: 8
    vpc.amazonaws.com/efa: 1
```

2. **NCCL 设置优化**:

```yaml
env:
- name: NCCL_DEBUG
  value: "INFO"
- name: NCCL_MIN_NCHANNELS
  value: "4"
- name: NCCL_SOCKET_IFNAME
  value: "^lo,docker"
- name: NCCL_ASYNC_ERROR_HANDLING
  value: "1"
```

3. **节点放置优化**:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-west-2a
```

## 实测基准：单个 L4 GPU 上的 Qwen2.5-7B

到目前为止，本页中的其他数字都是通用的 vLLM 项目声明或配置 flag 描述。本节有所不同：它针对真实的 vLLM server 进行了一次测量运行，因此您可以了解在一个具体的模型和 GPU 上，“continuous batching 改善吞吐量”实际是什么样子。

![客户端 Job 通过 ClusterIP Service 访问 vLLM server，后者将请求批处理到单个 NVIDIA L4 GPU 上；图中同时展示测得的吞吐量、延迟，以及限制因素是内存带宽而非计算能力的原因。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-6.html)

### 设置

- **集群**: 专用 Karpenter NodePool（`bench-gpu`，按需 `g6.2xlarge` — 1x NVIDIA L4、24GB GPU 内存、8 vCPU、32 GiB RAM），带有污点 `nvidia.com/gpu=true:NoSchedule`，并带有标签以加入现有的 `nvidia-device-plugin` daemonsets，运行后立即删除。
- **Server**: `vllm/vllm-openai:v0.6.4.post1`（于 2024-11-15 发布 — vLLM 项目此后已推出默认启用 prefix caching 的 V1 engine，因此应将此视为该发布系列的快照，而不是当前的 vLLM），模型 `Qwen/Qwen2.5-7B-Instruct`，`--dtype bfloat16 --max-model-len 4096 --gpu-memory-utilization 0.90`。使用一种精度（bf16，即模型的原生 dtype），不使用 quantization、speculative decoding 或 prefix caching — 即本页其他部分所述的普通默认设置。
- **Client**: 一个作为 Job 在**集群内部**（单独的非 GPU 节点）运行的 Python `ThreadPoolExecutor`，通过 `vllm-server` ClusterIP Service 访问 `/v1/chat/completions`。非流式，`temperature=0`、`max_tokens=128`，8 个轮换的短 prompt（询问 Kubernetes 概念的问题，要求回答 1-2 句话）。实际上，每个响应都接近 128-token 上限（全部三个并发批次的平均值约为 102 tokens），而不是在 1-2 句话后停止 — 这有助于在不同并发级别之间进行可比的吞吐量比较，但在将延迟数字理解为“回答简短问题的时间”之前值得注意。
- **冷启动**: 从 vLLM engine 的启动日志到其 `/health` endpoint 返回 `200`，约 4.5 分钟 — 主要耗时是将约 15 GB 的 Qwen2.5-7B-Instruct 权重从 Hugging Face 下载到 Pod 的 ephemeral cache。未包含 image pull 时间；未单独测量。

### 复现

```yaml
# NodePool (Karpenter) - dedicated, deleted after the run — nodeClassRef points at the cluster's existing GPU EC2NodeClass (AMI/subnets/SG), not shown here
apiVersion: karpenter.sh/v1
kind: NodePool
metadata: { name: bench-gpu }
spec:
  limits: { cpu: "16", memory: 128Gi, nvidia.com/gpu: "1" }
  template:
    metadata:
      labels: { node-type: bench-gpu, nvidia.com/device-plugin.config: default }
    spec:
      expireAfter: 6h
      nodeClassRef: { group: karpenter.k8s.aws, kind: EC2NodeClass, name: gpu }
      requirements:
        - { key: node.kubernetes.io/instance-type, operator: In, values: [g6.2xlarge] }
      taints: [{ key: nvidia.com/gpu, value: "true", effect: NoSchedule }]
---
# vLLM server (namespace bench-gpu) + the ClusterIP Service the client calls
apiVersion: apps/v1
kind: Deployment
metadata: { name: vllm-server, namespace: bench-gpu }
spec:
  replicas: 1
  selector: { matchLabels: { app: vllm-server } }
  template:
    metadata: { labels: { app: vllm-server } }
    spec:
      nodeSelector: { node-type: bench-gpu }
      tolerations: [{ key: nvidia.com/gpu, value: "true", effect: NoSchedule }]
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.6.4.post1
          args: ["--model", "Qwen/Qwen2.5-7B-Instruct", "--max-model-len", "4096",
                 "--gpu-memory-utilization", "0.90", "--dtype", "bfloat16"]
          ports: [{ containerPort: 8000 }]
          resources:
            limits: { nvidia.com/gpu: "1" }
            requests: { nvidia.com/gpu: "1", cpu: "3", memory: 20Gi }
          readinessProbe: { httpGet: { path: /health, port: 8000 }, initialDelaySeconds: 30, periodSeconds: 10, failureThreshold: 60 }
---
apiVersion: v1
kind: Service
metadata: { name: vllm-server, namespace: bench-gpu }
spec:
  selector: { app: vllm-server }
  ports: [{ port: 8000, targetPort: 8000 }]
```

客户端是一个普通的 Python 脚本，使用 `urllib` + `concurrent.futures.ThreadPoolExecutor` 向 `http://vllm-server:8000/v1/chat/completions` 发送 N 个请求并计时；请将其作为同一 namespace 中的 `batch/v1` Job 运行。有一个值得强调的注意事项：需要上面的 `nvidia.com/device-plugin.config: default` 节点标签 — 没有它，共享的 `nvidia-device-plugin` DaemonSet 永远不会调度到新节点上，即使污点和 toleration 正确匹配，`nvidia.com/gpu` 也不会注册为可分配资源。

### 结果

| 并发数 | 请求数 | 总耗时 | Client 延迟 p50 / p90 | Client 聚合吞吐量 | Server 报告的生成吞吐量峰值 | GPU KV cache 使用率 |
|---|---|---|---|---|---|---|
| 1（串行） | 10 | ~53.2 s（请求延迟之和） | 5.65 s / 7.43 s | 每个请求约 17-18 tokens/s | ~17 tokens/s | 0.1-0.2% |
| 4 | 16 | 27.78 s | 6.99 s / 7.88 s | 58.67 tokens/s | 65-66 tokens/s | 0.4-0.7% |
| 8 | 32 | 30.02 s | 7.18 s / 8.15 s | 109.04 tokens/s | 123-129 tokens/s | 0.8-1.4% |
| 16 | 64 | 31.35 s | 7.52 s / 8.74 s | 208.08 tokens/s | 最高 243 tokens/s | 1.5-2.6% |

“Client 聚合吞吐量”是该批次中所有请求的 completion tokens 总数除以 wall-clock time，从 Pod 外部测得。“Server 报告的”是 vLLM 自己在 `Running: <concurrency>` 时定期记录的 `Avg generation throughput` 日志行 — 它略高于 Client 数字，因为它排除了 HTTP/JSON 开销，并捕获了测量间隔之间的真实峰值，而不只是平均值。GPU 使用的内存（在运行后使用 `nvidia-smi` 测量）：该实例中 driver 报告总量 23.0 GiB 中的 19.2 GiB — `gpu-memory-utilization=0.90` 指示 vLLM 预先分配其中大部分用于权重加 KV cache blocks，因此下方 KV cache 百分比描述的是该预留池的使用率，而非实际空闲 VRAM。

### 分析

- **单请求延迟几乎不变。** 对相同的约 100-128 token 响应，并发请求从 1 增加到 16 时，p50 延迟仅从 5.65 s 增至 7.52 s（+33%）— 这正是 continuous batching 按预期工作的结果：新请求加入正在运行的 batch，而不是在它后面排队。
- **聚合吞吐量接近线性扩展。** 4 → 8 → 16 个并发请求每次都大致使聚合吞吐量翻倍（58.67 → 109.04 → 208.08 tokens/s）。
- **这是受带宽限制的 decode，而非受计算限制 — 这正是 batching 有帮助的原因。** 在 batch 1 时，每生成一个 token 都必须从 GDDR6 内存流式读取约 15.2 GB 的 bf16 权重；在该 L4 约 300 GB/s 的内存带宽下，这将单请求 decode 限制在约 20 tokens/s，与测得的约 17-18 相符。计算能力则呈现完全不同的情况：即使在最繁忙的测量点（208 tokens/s 聚合）下，GPU 的工作量约为 3 TFLOP/s，而 L4 的密集 bf16 计算能力约为 121 TFLOPS — 只达到其上限的百分之几。KV cache 容量也从未成为限制（整个运行过程保持在 3% 以下）。Continuous batching 正是解决这类受带宽限制 decode 的方法：当权重已为一个请求从内存读取后，使用同一份权重读取为 16 个请求提供服务几乎没有额外成本，因此吞吐量接近线性扩展，而延迟几乎不会增长。

### 注意事项

这是在一个模型、一种精度（bf16）、一种 GPU 类型和一种上下文长度上的单次运行（n=1）— 应将其视为一个经过校准的数据点，而不是通用的 vLLM/L4 性能声明。Client 在集群内部（单独的非 GPU 节点）运行，因此网络延迟反映的是集群内跳数，而非外部调用方。此处的延迟是完整的端到端 HTTP 响应时间，而不是 time-to-first-token (TTFT) — 未测试流式传输。未测试 prefix caching、speculative decoding、FP8 和多 GPU tensor parallelism（均在本页前文中描述）。请使用上面的 manifests 复现；不要将这些数字外推到不同的模型大小、GPU 或 prompt 长度。

## 监控和日志记录

![展示 vLLM、GPU 和 Kubernetes 指标流入 Prometheus/Grafana 监控栈以生成仪表板和告警，同时还有独立日志栈的图表。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-5.svg)

### Prometheus 指标

从 vLLM server 收集 Prometheus 指标的方法：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-metrics
  labels:
    app: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8001
    targetPort: 8001
    name: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: vllm-inference
  endpoints:
  - port: metrics
    interval: 15s
```

### 日志收集

将 vLLM server 日志收集到 CloudWatch 的方法：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: logging
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/vllm-*.log
      pos_file /var/log/fluentd-vllm.log.pos
      tag kubernetes.vllm.*
      read_from_head true
      <parse>
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.vllm.**>
      @type kubernetes_metadata
      @id filter_kube_metadata
    </filter>

    <match kubernetes.vllm.**>
      @type cloudwatch_logs
      log_group_name /eks/vllm/logs
      log_stream_name_key $.kubernetes.pod_name
      remove_log_stream_name_key true
      auto_create_stream true
      region us-west-2
    </match>
```

## 自动扩缩容

![展示 CPU、GPU、请求速率和队列长度信号如何驱动 Pod 级自动扩缩容，进而驱动 GPU 节点自动扩缩容和 Spot 容量的图表。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-6.svg)

### HPA (Horizontal Pod Autoscaler)

基于请求量自动扩缩容 vLLM servers 的方法：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-inference
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

### 使用 Karpenter 进行节点自动扩缩容

自动预置 GPU 节点的方法：

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: vllm-gpu
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.16xlarge
        - g5.12xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: vpc.amazonaws.com/efa
        operator: In
        values:
        - "true"
      nodeClassRef:
        name: vllm-gpu-class
  limits:
    nvidia.com/gpu: 32
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: vllm-gpu-class
spec:
  subnetSelector:
    karpenter.sh/discovery: vllm-cluster
  securityGroupSelector:
    karpenter.sh/discovery: vllm-cluster
  ttlSecondsAfterEmpty: 30
```

## 安全配置

### Network Policy

限制对 vLLM servers 的网络访问的方法：

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
spec:
  podSelector:
    matchLabels:
      app: vllm-inference
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  - from:
    - podSelector:
        matchLabels:
          app: vllm-inference
    ports:
    - protocol: TCP
      port: 29500
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: vllm-inference
    ports:
    - protocol: TCP
      port: 29500
  - to:
    ports:
    - protocol: TCP
      port: 443
```

### Security Context

配置容器 Security Context 的方法：

```yaml
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

## Client 集成

![展示 Client SDKs 通过 API gateway 到达 vLLM 的图表，途经用于身份验证和速率限制的 security layer，最后到达负载均衡的 backend service。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-7.svg)

### API Gateway

在 vLLM servers 前部署 API gateway 的方法：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: nginx:latest
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-config
          mountPath: /etc/nginx/conf.d
      volumes:
      - name: nginx-config
        configMap:
          name: nginx-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
data:
  default.conf: |
    server {
      listen 80;

      location /v1/ {
        proxy_pass http://vllm-inference:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
      }
    }
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Client 示例

使用 Python client 向 vLLM server 发送请求的方法：

```python
import requests
import json

url = "http://api-gateway/v1/completions"

payload = {
    "model": "llama-3.1-70b",
    "prompt": "Once upon a time",
    "max_tokens": 100,
    "temperature": 0.7
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))

print(response.json())
```

## 最佳实践

### 资源管理

1. **考虑内存开销**:
   - 除 GPU 内存外，还应分配充足的 CPU 内存。
   - 建议分配约为模型大小两倍的 CPU 内存。

2. **CPU 核心分配**:
   - 每个 GPU 至少分配 4 个 CPU 核心。
   - 使用 tensor parallelization 时可能需要更多 CPU 核心。

3. **节点选择**:
   - 根据模型大小选择合适的节点类型。
   - 选择内存带宽高的节点。

### 高可用性

1. **多 Availability Zone 部署**:
   - 跨多个 availability zones 部署 vLLM servers。
   - 确保每个 availability zone 中都有充足容量。

2. **负载均衡**:
   - 将请求分发到多个 vLLM server 实例。
   - 配置 session affinity，使同一用户的请求路由到同一 server。

3. **故障恢复**:
   - 配置 health checks 以检测失败的 servers。
   - 实现自动恢复机制。

### 成本优化

1. **使用 Spot Instances**:
   - 使用 Spot instances 降低成本。
   - 适用于可容忍中断的工作负载。

2. **模型量化**:
   - 应用 INT8 或 INT4 quantization 以降低内存使用。
   - 考虑精度与性能之间的平衡。

3. **自动扩缩容**:
   - 基于请求量自动扩缩容 servers。
   - 在空闲时缩减 servers 以降低成本。

## 结论

vLLM 是最活跃开发的开源 LLM 推理引擎，全面支持生产环境必需的功能，包括 Speculative Decoding、Prefix Caching、动态 LoRA 加载、Structured Output 和 Tool Calling。结合在 EKS 上适当的 GPU 实例选择、高性能存储、网络优化和自动扩缩容，您可以构建一个经济高效且可扩展的 LLM serving platform。有关与 SGLang 和 TGI 等其他框架的比较，请参阅 [Inference Frameworks](./04-inference-frameworks.md) 章节。

## 参考资料

- [vLLM 官方文档](https://docs.vllm.ai/) - vLLM 官方文档和最新功能指南
- [AI on EKS](https://awslabs.github.io/ai-on-eks/) - 在 EKS 上部署 AI/ML workloads 的 AWS 指南和示例

## 测验

要测试您在本章中学到的知识，请尝试 [主题测验](../quizzes/ai-ml/04-vllm-deployment-quiz.md)。
