# vLLM 部署与优化

> **审查基线**：vLLM 0.29.0、CUDA 12.9 镜像变体；历史 0.6.4.post1 基准测试单独列出
> **已检查的最新版本**：vLLM 0.31.0（2026 年 10 月 5 日），检查日期为 2026 年 10 月 12 日
> **最后更新**：October 12, 2026

vLLM 是用于生成式模型以及受支持的多模态/池化工作负载的开源推理引擎。不应将其展开为“Vector Language Model”。本章审查特定版本及 EKS 运行边界，不提供通用加速或模型支持保证。

## 实验环境设置

本章的清单和本地检查使用于 2026 年 9 月 9 日发布的 [v0.29.0](https://github.com/vllm-project/vllm/releases/tag/v0.29.0)。后续版本包括 v0.30.0（2026 年 9 月 22 日）和 [v0.31.0](https://github.com/vllm-project/vllm/releases/tag/v0.31.0)（2026 年 10 月 5 日）。

在 v0.31.0 中：

- 默认拒绝每请求的 `mm_processor_kwargs` 和 `media_io_kwargs`。仅使用显式的 `--trust-request-mm-kwargs` 选项允许它们。
- `tokenizer_mode="slow"` 已被移除。

本章的 0.29.0 示例尚未在 v0.30.0 或 v0.31.0 上重新运行。升级前请审查[版本变更](https://github.com/vllm-project/vllm/releases/tag/v0.31.0)和兼容性。

0.29.0 的默认 PyPI/Docker 路径使用 CUDA 13.0，并提供单独的 v0.29.0-cu129 镜像。一些带标签的安装文本仍将 CUDA 12.9 称为默认版本；请检查实际镜像变体/digest。

PyPI 要求 Python >=3.10, <3.15，而带标签的 GPU 指南列出 3.10–3.13。这并不保证每种 Python/PyTorch/CUDA 组合都可用。NVIDIA 路径要求计算能力 7.5 或更高，因此不支持 V100（7.0）。内核、数据类型和量化可能施加额外的设备要求。

请遵循[AI/ML 工作负载](01-ai-ml-workloads.md)中的 AMI/驱动程序/device plugin 条件。CUDA 镜像不能直接用于 Trainium/Inferentia 部署；请分别验证 Neuron 或其他平台插件。应根据模型/缓存/并发量调整 GPU、RAM 和磁盘大小，而不是将 g5.2xlarge 或 50GB 视为通用最低配置。

## vLLM 简介

vLLM 是具有以下特性的 LLM 推理引擎：

![具有条件性性能收益的 API 请求、调度器、模型加载器、引擎和 KV 缓存职责。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-0.html)

### 功能与支持边界

| 功能 | 含义和条件 |
| --- | --- |
| PagedAttention / KV cache | 管理 token 块以减少浪费；内核/缓存布局取决于模型/backend |
| Continuous batching | 调度器在每一步调整工作；不保证立即接纳、排队或固定加速效果 |
| TP / PP / DP / EP | Tensor、pipeline、data 和 expert parallelism 是不同的维度，需要模型/backend/network 支持 |
| Precision / quantization | 区分 FP16/BF16 数据类型与 FP8/INT8/INT4/AWQ 格式，以及权重量化与 KV-cache 量化 |
| Prefix caching / chunked prefill | 检查受支持模型的默认值和覆盖项；并非完整响应缓存或准确性改进 |
| Structured outputs | response_format 或 structured_outputs 约束格式；真实性和业务有效性需要单独检查 |
| Tool calling | 需要模型/chat template/parser 和客户端执行循环；服务器不会自动执行工具 |
| LoRA | 需要模型支持和 adapter 注册；仅更改请求模型不会加载 adapter |

0.29.0 将 Model Runner V2 设为默认 runner。这不是 OpenAI-compatible API 版本，也不是独立的“vLLM Engine V2”。模型系列名称并不保证所有尺寸、量化或视觉变体均受支持；请验证架构、artifact/tokenizer、chat template 和内核。

### 当前 CLI 功能配置

使用 vllm serve 代替已弃用的 python -m vllm.entrypoints.openai.api_server。当前 CLI 中，先前的 --speculative-model/--num-speculative-tokens 选项由 --speculative-config 替代。

```bash
# Syntax when compatible target/draft models and sufficient memory are prepared.
vllm serve /models/target \
  --speculative-config '{"model":"/models/draft","method":"draft_model","num_speculative_tokens":5}'
```

这展示了语法；它不提供这些模型文件，也不保证加速效果。草稿接受率、额外内存和通信成本可能抵消收益。

使用 --enable-lora --lora-modules adapter=/models/adapter 注册启动时 LoRA。运行时加载/卸载需要单独启用 VLLM_ALLOW_RUNTIME_LORA_UPDATING，并使用受限的 operator 路径。--enable-auto-tool-choice 需要适当的 --tool-call-parser。多模态 URL 还需要 SSRF 控制、允许的域名以及下载/解码限制。

## 系统要求

在 EKS 上部署 vLLM 的系统要求：

![考虑权重和架构的 KV 内存、额外开销、设备能力和明确的 CUDA artifact 要求。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-1.html)

从参数数量 × 存储字节数开始估算权重内存。仅 70B 的 FP16/BF16 权重大约为 140GB，因此 80GB 不是通用的 70B 要求。还应加入 KV cache、激活值、CUDA graphs/workspaces 和通信缓冲区，并考虑量化元数据和复制的张量。

以下是常见的 dense-attention KV 估算。对于 GQA/MQA，应使用 KV-head 数量，而不是套用仅适用于 MHA 的公式中的 hidden size。

```text
KV bytes ≈ 2 × layers × KV_heads × head_dim × cached_tokens × bytes_per_element
```

cached_tokens 是并发请求中保留 token 的总和。TP 分片/复制、sliding windows、MLA 和混合架构需要分别处理。当前 Qwen2.5-7B 配置有 28 层、4 个 KV heads 和 128 的 head dimension：每个元素为两个字节时约为 56KiB/token，或单个 4096-token 序列为 224MiB。这是汇总估算，并非测量得到的每 GPU 或模型总内存。

p4d.24xlarge 使用 40GB A100；请与 80GB A100 p4de 实例区分。请根据区域容量、驱动程序和工作负载需求比较 p5/g6/g6e 及其他选项。每 GPU 固定四个 CPU 核心或 RAM 为权重两倍等规则不能替代测量。

## EKS 基础设施配置

![为工作负载选择的示例性 EKS 节点、模型存储、镜像和权限路径。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-2.html)

## 存储和模型准备

FSx for Lustre 是一种选项，并非必需或始终最优。应根据加载时间、成本和并发量比较本地 NVMe/EBS、可复用缓存、对象存储和共享文件系统。emptyDir 可在容器重启后继续存在，但在 Pod 删除/重新创建后不会保留。

请区分[静态 FSx PV/PVC 和动态置备](01-ai-ml-workloads.md#storage-and-caching)。Hugging Face snapshot_download 从 Hugging Face 下载，而不是从 S3 下载。记录仓库 revision、完整性、许可证和访问权限。对于受限模型，将 token 作为文件挂载，并使用读取该文件的下载阶段。默认不要信任可执行的远程代码。

以下示例使用无需 token 的公开 Qwen3-0.6B 的已验证 revision。其 emptyDir 缓存在 Pod 重新创建后会再次下载。多节点 worker 需要相同的模型 revision/path。

## vLLM 部署

### Deployment 架构

下图展示了在 EKS 上部署 vLLM 的两种主要架构：

![单 GPU 服务与分片的多节点组，区分 API 入口点、worker 和模型路径。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-3.html)

### 单 GPU 配置示例

这是一个**在 GPU 执行前供审查的模板**。准备 namespace 和 GPU driver/plugin。digest 标识 v0.29.0-cu129 amd64 artifact；模型 revision 标识经过检查的公开 Qwen3-0.6B snapshot。本次审计未执行镜像拉取、非 root 执行、内核编译和推理，需进行环境验证。

Recreate 无需额外 GPU replica，但会在更新时导致停机。startupProbe 为启动提供约 15 分钟；readiness 不是 SLA。该 Service 为 ClusterIP，不会创建公共 ingress。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-demo
  namespace: ml-inference
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: vllm-demo
  template:
    metadata:
      labels:
        app: vllm-demo
    spec:
      automountServiceAccountToken: false
      nodeSelector:
        kubernetes.io/arch: amd64
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: vllm
          image: vllm/vllm-openai@sha256:3e10e8189823e0f7ae4620c271bcdaaf64127ec7d0edc351591a508498b7684a
          command: ["vllm", "serve"]
          args:
            - Qwen/Qwen3-0.6B
            - --revision=c1899de289a04d12100db370d81485cdf75e47ca
            - --served-model-name=qwen3-demo
            - --dtype=float16
            - --max-model-len=2048
            - --max-num-seqs=8
            - --gpu-memory-utilization=0.80
            - --host=0.0.0.0
            - --port=8000
          env:
            - name: HF_HOME
              value: /cache/huggingface
            - name: XDG_CACHE_HOME
              value: /cache
            - name: XDG_CONFIG_HOME
              value: /cache/config
            - name: VLLM_NO_USAGE_STATS
              value: "1"
            - name: VLLM_CACHE_ROOT
              value: /cache/vllm
            - name: TORCHINDUCTOR_CACHE_DIR
              value: /cache/torchinductor
            - name: TRITON_CACHE_DIR
              value: /cache/triton
          ports:
            - name: http
              containerPort: 8000
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
              ephemeral-storage: 4Gi
            limits:
              cpu: "4"
              memory: 12Gi
              ephemeral-storage: 12Gi
              nvidia.com/gpu: 1
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: [ALL]
          startupProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 10
            failureThreshold: 90
          readinessProbe:
            httpGet:
              path: /health
              port: http
            periodSeconds: 10
          volumeMounts:
            - name: cache
              mountPath: /cache
            - name: tmp
              mountPath: /tmp
            - name: shm
              mountPath: /dev/shm
      volumes:
        - name: cache
          emptyDir:
            sizeLimit: 8Gi
        - name: tmp
          emptyDir:
            sizeLimit: 1Gi
        - name: shm
          emptyDir:
            medium: Memory
            sizeLimit: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-demo
  namespace: ml-inference
  labels:
    app: vllm-demo
spec:
  type: ClusterIP
  selector:
    app: vllm-demo
  ports:
    - name: http
      port: 8000
      targetPort: http
```

### 多节点分片与独立副本

对一个模型 replica 进行分片需要 TP/PP 以及 Ray 或 multiprocessing 协调。独立 API-server replicas 各自加载模型并提供横向扩展；它们是不同的设计。

0.29.0 支持 multiprocessing 的 --nnodes、--node-rank、--master-addr 和 --master-port。旧的 --rank、--tensor-parallel-rank 和 --distributed-init-method 示例并非这些 CLI 选项。当两个已准备节点各提供八个 GPU 时，命令形式如下：

```bash
# node0: substitute an actual trusted head IP and identical prepared model path.
vllm serve /models/model --distributed-executor-backend mp \
  --tensor-parallel-size 8 --pipeline-parallel-size 2 \
  --nnodes 2 --node-rank 0 --master-addr 10.0.0.10 --master-port 29500
# node1: the worker does not start a duplicate API server.
vllm serve /models/model --distributed-executor-backend mp \
  --tensor-parallel-size 8 --pipeline-parallel-size 2 \
  --nnodes 2 --node-rank 1 --master-addr 10.0.0.10 --master-port 29500 --headless
```

这些命令不会创建节点、模型文件或连接。Kubernetes 需要适当的并发 worker 创建、readiness 前 DNS、每个 Pod 的 VLLM_HOST_IP、内部连接和共享内存。Ray 在使用 --distributed-executor-backend ray 启动一个 API 入口点之前，需要一个正常运行的 cluster 和兼容的 Ray dependency；请参阅 [Ray](ray/README.md)。保持内部通信端口私有。

## 性能优化

![当前的内存、offload、调度器和通信调优需要工作负载测量。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-4.html)

### 内存、调度器和通信选项

0.29.0 中的 CacheConfig 默认将 gpu_memory_utilization 设为 0.92；这不是所有进程 VRAM 的硬上限。示例明确选择 0.80。--kv-cache-memory-bytes 会覆盖自动 KV-cache 大小调整，因此请检查选项优先级。

当前 CLI 中不存在 --swap-space。权重 CPU offload 和 KV offload 是独立的能力/配置，不能保证主机 RAM 能解决 GPU 限制。对于受支持的模型，prefix caching 可能默认开启；chunked prefill 也取决于模型。队列限制、token 预算、max-num-seqs 和 max-model-len 是不同的控制项。

EFA 需要受支持的 EC2 设备、AMI/plugin/network 以及 AWS OFI NCCL/libfabric。不要将虚构的 NCCL_IB_ENABLE_RDMA 标志或任意 mlx5/GID 设置作为通用默认值复制。检查当前 NVIDIA/PyTorch 变量和实际 backend 日志。单节点 NCCL 测试不能证明多节点 EFA 性能。

## 历史测量：单张 L4 GPU 上的 Qwen2.5-7B

这些是 [2026 年 9 月 4 日仓库提交](https://github.com/Atom-oh/kubernetes-docs/commit/8622d388cb684dc4f68083af7be6d91f80b79106)中报告的历史测量。本次审计未找到原始请求结果/服务器日志或完整客户端 artifact，也没有重新运行该实验。保留所报告的数值，不将其重新标记为当前 0.29.0 性能或独立复现的结果。

![带有原始日志和独立复现限制的历史 L4 基准测试报告。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-6.html)

### 设置

- **Cluster**：专用 Karpenter NodePool（`bench-gpu`，按需 `g6.2xlarge` — 1x NVIDIA L4、24GB GPU 内存、8 vCPU、32 GiB RAM），带有 `nvidia.com/gpu=true:NoSchedule` 污点，并带有标签以加入现有的 `nvidia-device-plugin` daemonsets，在运行后立即删除。
- **Server**：`vllm/vllm-openai:v0.6.4.post1`（发布于 2024-11-15 — vLLM 项目此后推出了其 V1 engine，默认启用 prefix caching，因此应将其视为该发布线的快照，而非当前 vLLM），模型 `Qwen/Qwen2.5-7B-Instruct`，`--dtype bfloat16 --max-model-len 4096 --gpu-memory-utilization 0.90`。一种 precision（bf16，模型的原生 dtype），没有 quantization、speculative decoding 或 prefix caching — 即本页面其他部分所述的朴素默认值。
- **Client**：作为 **集群内部** Job（独立的非 GPU 节点）运行的 Python `ThreadPoolExecutor`，通过 `vllm-server` ClusterIP Service 访问 `/v1/chat/completions`。非流式、`temperature=0`、`max_tokens=128`、8 个轮换的简短 prompts（询问 Kubernetes 概念问题，要求给出 1-2 句答案）。实际上，每个响应都接近 128-token 上限（所有三个并发批次的平均值一致约为 102 token），而非在 1-2 句后停止 — 这有助于在不同并发级别之间公平比较吞吐量，但在将延迟数值理解为“回答一个简短问题所需时间”前应知悉这一点。
- **Cold start**：从 vLLM engine 的启动日志到其 `/health` endpoint 返回 `200` 约为 4.5 分钟 — 主要由将约 15 GB 的 Qwen2.5-7B-Instruct 权重从 Hugging Face 下载到 Pod 的 ephemeral cache 所致。未包含镜像拉取时间；未单独测量。

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

这些清单展示了所报告环境的一部分。它们省略了 namespace 创建、现有 EC2NodeClass 和完整的客户端脚本，因此不能构成完整复现。nvidia.com/device-plugin.config:default 是该共享 DaemonSet 配置的条件，而非通用调度标签要求。所报告的按需声明也需要实际的历史配置。

### 结果

| 并发量 | 请求数 | 总耗时 | 客户端延迟 p50 / p90 | 客户端聚合吞吐量 | 服务器报告的峰值生成吞吐量 | GPU KV 缓存使用率 |
|---|---|---|---|---|---|---|
| 1（串行） | 10 | ~53.2 s（请求延迟之和） | 5.65 s / 7.43 s | 每请求约 ~17-18 tokens/s | ~17 tokens/s | 0.1-0.2% |
| 4 | 16 | 27.78 s | 6.99 s / 7.88 s | 58.67 tokens/s | 65-66 tokens/s | 0.4-0.7% |
| 8 | 32 | 30.02 s | 7.18 s / 8.15 s | 109.04 tokens/s | 123-129 tokens/s | 0.8-1.4% |
| 16 | 64 | 31.35 s | 7.52 s / 8.74 s | 208.08 tokens/s | 最高 243 tokens/s | 1.5-2.6% |

客户端聚合吞吐量是 completion-token 数量除以测得的总耗时。服务器 Avg generation throughput 是区间平均值；其最大的日志值并非瞬时“真实峰值”。时间窗口、token 计数和 HTTP 边界不同，因此它们不是可直接互换的指标。

### 解读

报告的 p50 从 5.65s 增加到 7.52s，约增加 33.1%。并发量为 4→8→16 时的聚合吞吐量为 58.67→109.04→208.08tokens/s。应将这一 batching 观察与底层瓶颈的因果证明区分开来。

用约 300GB/s 的带宽除以 15.2GB 权重，可得到接近 20 tokens/s 的理想化 roofline。本次审计没有 profiler 证据直接测量带宽或 FLOP 执行，因此不能证明“确定受内存限制”或“额外请求几乎免费”。KV-cache 占用率和总 VRAM 使用量是不同的量。

### 注意事项

这是在一个模型、一种 precision（bf16）、一种 GPU 类型和一种上下文长度上的单次运行（n=1）— 应将其视为一个经过校准的数据点，而非通用的 vLLM/L4 性能声明。客户端在集群内部（独立的非 GPU 节点）运行，因此网络延迟反映集群内部跳数，而非外部调用方。这里的延迟是完整端到端 HTTP 响应时间，而非首 token 时间（TTFT）— 未测试流式响应。未测试 prefix caching、speculative decoding、FP8 和多 GPU tensor parallelism（均在本页前文描述）。完整复现需要缺失的执行 artifact 和环境细节；请不要将这些数值外推到不同的模型大小、GPU 或 prompt 长度。

## 监控和日志记录

![API 端口 8000 上的实际指标以及独立的日志记录/访问边界。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-5.html)

### 指标和日志

默认的 /metrics endpoint 使用 API 的端口 8000。不要虚构单独的 8001 端口或 --enable-metrics=true。应在 ServiceMonitor 中匹配 Service 标签、命名端口和 namespace 选择。

```promql
# End-to-end p95 by model
histogram_quantile(0.95, sum by (le, model_name) (rate(vllm:e2e_request_latency_seconds_bucket[5m])))
# Generation-token throughput
sum by (model_name) (rate(vllm:generation_tokens_total[5m]))
# Queued requests
sum by (model_name) (vllm:num_requests_waiting)
```

vllm:kv_cache_usage_perc 是一个比例，其中 1 表示 100%，而不是 GPU 总内存字节数。应与成功计数器一起观察 gateway 错误/取消，并且不要将健康的空闲时段称为低吞吐量故障。验证实际 endpoint 名称/标签。区分 CRI framing 与应用日志，避免无差别记录 prompt/output/token。

## 自动扩缩容

![已验证的指标、一个 Pod 扩缩容所有者、独立副本和单独的节点容量所有者。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-10.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-10.html)

### 自动扩缩容和可用性

使用 HPA/KEDA 扩缩独立副本不同于扩缩分片模型的 worker 组。增加 StatefulSet replicas 不会自动重新配置 TP/PP。验证 adapter 请求/队列信号，且不要在没有 CPU requests 的情况下使用 CPU-utilization HPA。避免让 Karpenter/Cluster Autoscaler 竞争同一容量的所有权。

PDB 约束某些自愿驱逐，而非所有故障。独立副本可以跨 AZ 分布；将通信密集的 TP/PP 组置于跨 AZ 环境时，会有单独的延迟/成本影响。在声称无中断更新前，请验证模型加载、warmup、draining、进行中的 streams 和备用 GPU。

## 安全配置

--api-key 并不保护每个 endpoint。此版本的 middleware 保护 /v1、/v2、/inference 和 /cohere 前缀；/invocations、/metrics 和某些运维 endpoint 需要额外保护。经过认证的 gateway 应仅允许所需路径/methods；将分布式通信限制在受信任网络中。CORS 不是认证。

运行时 LoRA、远程模型代码和多模态 URL 分别引入信任/权限/SSRF 边界。用正则表达式阻止“ignore instructions”无法防止所有 prompt injection，也不能保证删除 PII。独立于模型输出执行 tool/data 权限控制。

将 secrets 作为文件提供，并正确放置 Pod/container securityContext 字段。将 NetworkPolicy selectors、DNS、抓取方向和内部流量与实际配置匹配。Pod annotations 无法启用 API-server auditing；不要记录 Secret RequestResponse 正文。EKS control-plane audit 和应用访问日志相互独立。

## 客户端集成

![经过认证的 gateway allowlists 和独立的 operator access 可保护内部 vLLM endpoints。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-7.html)

### 客户端请求

在验证 Deployment/readiness 后，已获授权的开发者可以使用 kubectl port-forward -n ml-inference service/vllm-demo 8000:8000。保留其默认 localhost 绑定。此本地示例不能替代生产 gateway 认证。

```python
import json
import urllib.request

payload = {
    "model": "qwen3-demo",
    "messages": [{"role": "user", "content": "Explain a Kubernetes Pod briefly."}],
    "max_tokens": 64,
    "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": False},
}
request = urllib.request.Request(
    "http://127.0.0.1:8000/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=60) as response:
    result = json.load(response)
print(result["choices"][0]["message"]["content"])
```

请求模型必须与 served-model-name 或 /v1/models 匹配。生产客户端需要基于文件的 gateway 凭证以及 timeout/error/stream 处理。JSON 正文的 model 字段不是 HTTP model header，因此 header routing 不会自动检查它。

## 验证范围

已检查固定版本的源代码中的 CLI arguments、metrics、authentication 和 artifact metadata。Kubernetes schemas/local HTTP fixtures 无法验证实际的 vLLM parser/kernel/GPU 执行。本次审计未下载模型权重，也未创建 GPU servers/cloud resources。

## 参考资料

- [vLLM 0.29.0 发布版（审查基线）](https://github.com/vllm-project/vllm/releases/tag/v0.29.0)
- [vLLM 0.31.0 发布版（已检查的最新版本）](https://github.com/vllm-project/vllm/releases/tag/v0.31.0)
- [并行化和扩缩容](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/serving/parallelism_scaling.md)
- [安全边界](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/usage/security.md)
- [生产指标](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/usage/metrics.md)
- [结构化输出](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/features/structured_outputs.md)
- [LoRA adapters](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/features/lora.md)

## 测验

要测试你在本章中学到的内容，请尝试[主题测验](../quizzes/ai-ml/04-vllm-deployment-quiz.md)。
