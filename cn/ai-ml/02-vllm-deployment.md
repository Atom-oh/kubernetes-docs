# vLLM 部署与优化

> **审查基线**：vLLM 0.29.0，CUDA 12.9 镜像变体；历史 0.6.4.post1 基准测试已分离
> **最后更新**：September 12, 2026

vLLM 是用于生成式模型以及受支持多模态/pooling 工作负载的开源推理引擎。它不应被扩展为“Vector Language Model”。本章审查特定版本及 EKS 运行边界，并不提供通用加速或模型支持保证。

## 实验环境设置

基线为于 2026 年 9 月 9 日发布的 [v0.29.0](https://github.com/vllm-project/vllm/releases/tag/v0.29.0)。其默认 PyPI/Docker 路径使用 CUDA 13.0，并提供独立的 v0.29.0-cu129 镜像。一些带标签的安装文本仍将 CUDA 12.9 称为默认版本；请检查实际镜像变体/digest。

PyPI 要求 Python >=3.10, <3.15，而带标签的 GPU 指南列出 3.10–3.13。这并不保证每个 Python/PyTorch/CUDA 组合都可用。NVIDIA 路径要求计算能力 7.5 或更高，因此不支持 V100 (7.0)。Kernels、dtypes 和量化可能施加额外的设备要求。

请遵循 [AI/ML workloads](01-ai-ml-workloads.md) 中的 AMI/driver/device-plugin 条件。CUDA 镜像不是可直接用于 Trainium/Inferentia 的部署；请单独验证 Neuron 或其他平台插件。请根据模型/cache/concurrency 确定 GPU、RAM 和磁盘规格，而不要将 g5.2xlarge 或 50GB 视为通用最低要求。

## vLLM 简介

vLLM 是一个具有以下特性的 LLM 推理引擎：

![API 请求、scheduler、model loader、engine 和 KV cache 的角色，以及有条件的性能收益。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-0.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-0.html)

### 功能与支持边界

| 功能 | 含义与条件 |
| --- | --- |
| PagedAttention / KV cache | 管理 token 块以减少浪费；kernels/cache 布局取决于模型/backend |
| Continuous batching | Scheduler 在每个步骤调整工作；不保证立即准入、没有排队或固定加速保证 |
| TP / PP / DP / EP | Tensor、pipeline、data 和 expert parallelism 是不同维度，需要模型/backend/network 支持 |
| Precision / quantization | 区分 FP16/BF16 dtypes 与 FP8/INT8/INT4/AWQ 格式，以及权重量化与 KV-cache 量化 |
| Prefix caching / chunked prefill | 检查受支持模型的默认值和覆盖项；不是完整响应缓存，也不会提高准确性 |
| Structured outputs | response_format 或 structured_outputs 限制格式；真实性和业务有效性需要单独检查 |
| Tool calling | 需要 model/chat template/parser 和 client 执行循环；server 不会自动执行 tools |
| LoRA | 需要模型支持和 adapter 注册；仅更改请求 model 不会加载 adapter |

0.29.0 将 Model Runner V2 设为默认 runner。这不是 OpenAI-compatible API 版本，也不是独立的“vLLM Engine V2”。模型系列名称并不保证所有大小、量化或 vision 变体均受支持；请验证 architecture、artifact/tokenizer、chat template 和 kernels。

### 当前 CLI 功能配置

请使用 vllm serve，而不要使用已弃用的 python -m vllm.entrypoints.openai.api_server。当前 CLI 中，原有的 --speculative-model/--num-speculative-tokens 选项已由 --speculative-config 替代。

```bash
# Syntax when compatible target/draft models and sufficient memory are prepared.
vllm serve /models/target \
  --speculative-config '{"model":"/models/draft","method":"draft_model","num_speculative_tokens":5}'
```

这展示的是语法；它不提供这些模型文件，也不保证加速。draft 接受率、额外内存和通信成本可能抵消收益。

使用 --enable-lora --lora-modules adapter=/models/adapter 注册启动 LoRA。运行时加载/卸载需要单独启用 VLLM_ALLOW_RUNTIME_LORA_UPDATING，并且需要受限的 operator 路径。--enable-auto-tool-choice 需要相应的 --tool-call-parser。多模态 URL 还需要 SSRF 控制、允许的域名以及下载/解码限制。

## 系统要求

在 EKS 上部署 vLLM 的系统要求：

![考虑权重和架构的 KV memory、额外开销、设备能力以及明确的 CUDA artifact 要求。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-1.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-1.html)

权重内存估算应从参数数量 × 存储字节数开始。仅 70B 的 FP16/BF16 权重约为 140GB，因此 80GB 并非 70B 的通用要求。还需加入 KV cache、activations、CUDA graphs/workspaces 和通信 buffer，并考虑量化 metadata 和复制的 tensors。

下面是常见的 dense-attention KV 估算。对于 GQA/MQA，请使用 KV-head 数量，而不要套用仅适用于 MHA 的公式中的 hidden size。

```text
KV bytes ≈ 2 × layers × KV_heads × head_dim × cached_tokens × bytes_per_element
```

cached_tokens 汇总了并发请求中保留的 tokens。TP 分片/复制、sliding windows、MLA 和 hybrid architectures 需要单独处理。当前 Qwen2.5-7B 配置有 28 个 layers、4 个 KV heads 和 128 的 head dimension：每个元素为两个字节时，约为 56KiB/token；单个 4096-token 序列约为 224MiB。这是汇总估算，并非按每个 GPU 或总模型内存实测的值。

p4d.24xlarge 使用 40GB A100；应与 80GB A100 p4de 实例区分开来。请根据区域容量、drivers 和工作负载需求比较 p5/g6/g6e 及其他选项。每个 GPU 固定配备四个 CPU cores 或 RAM 为权重两倍之类的规则不能替代测量。

## EKS 基础设施配置

![为工作负载选择的示例性 EKS node、model-storage、image 和 permission 路径。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-2.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-2.html)

## 存储与模型准备

FSx for Lustre 是一种选择，并非强制要求或在所有情况下都是最佳方案。请按加载时间、成本和并发性比较本地 NVMe/EBS、可复用 caches、object storage 和 shared filesystems。emptyDir 可在 container 重启后保留，但无法在 Pod 删除/重建后保留。

请区分 [静态 FSx PV/PVC 和动态配置](01-ai-ml-workloads.md#storage-and-caching)。Hugging Face snapshot_download 从 Hugging Face 下载，而非从 S3 下载。记录 repository revision、完整性、许可证和访问权限。对于 gated models，将 tokens 作为文件挂载，并使用读取该文件的下载阶段。默认不要信任可执行的远程代码。

以下示例使用已验证 revision 的公共 Qwen3-0.6B，且不使用 token。其 emptyDir cache 会在 Pod 重建后再次下载。多节点 workers 需要相同的模型 revision/path。

## vLLM 部署

### Deployment 架构

下图展示了在 EKS 上部署 vLLM 的两种主要架构：

![Single-GPU 服务与分片 multi-node group 的对比，区分 API entry point、workers 和模型路径。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-3.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-3.html)

### Single-GPU 配置示例

这是一个**在 GPU 执行前供审查的模板**。请准备 namespace 和 GPU driver/plugin。digest 标识 v0.29.0-cu129 amd64 artifact；模型 revision 标识已检查的公共 Qwen3-0.6B snapshot。本次审计未执行 image pulling、非 root 执行、kernel 编译和 inference，且这些操作需要环境验证。

Recreate 避免要求额外 GPU replica，但会导致更新停机。startupProbe 为启动预留约 15 分钟；readiness 不是 SLA。Service 为 ClusterIP，不会创建公共 ingress。

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

### Multi-Node 分片与独立 replicas 的对比

对一个模型 replica 进行分片需要 TP/PP 加上 Ray 或 multiprocessing 协调。独立的 API-server replicas 各自加载模型并提供水平扩展；它们是不同的设计。

0.29.0 支持 multiprocessing --nnodes、--node-rank、--master-addr 和 --master-port。旧的 --rank、--tensor-parallel-rank 和 --distributed-init-method 示例不是这些 CLI 选项。当两个已准备节点各提供八个 GPU 时，命令形式如下：

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

这些命令不会创建 nodes、模型文件或连通性。Kubernetes 需要适当的并发 worker 创建、readiness 前 DNS、每个 Pod 的 VLLM_HOST_IP、内部连通性和 shared memory。Ray 要求在使用 --distributed-executor-backend ray 启动一个 API entry point 前，先具备可正常运行的 cluster 和兼容的 Ray dependency；请参见 [Ray](ray/README.md)。保持内部通信 ports 为私有。

## 性能优化

![当前的 memory、offload、scheduler 和通信调优需要工作负载测量。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-4.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-4.html)

### 内存、Scheduler 和通信选项

0.29.0 中的 CacheConfig 默认 gpu_memory_utilization 为 0.92；这并非所有 process VRAM 的硬上限。该示例显式选择 0.80。--kv-cache-memory-bytes 覆盖自动 KV-cache 大小调整，因此请检查选项优先级。

当前 CLI 中没有 --swap-space。权重 CPU offload 和 KV offload 是独立的能力/配置，并不保证 host RAM 能解决 GPU 限制。Prefix caching 可在受支持模型上默认开启；chunked prefill 也取决于模型。队列限制、token budgets、max-num-seqs 和 max-model-len 是不同的控制项。

EFA 需要受支持的 EC2 devices、AMI/plugin/network 以及 AWS OFI NCCL/libfabric。不要将虚构的 NCCL_IB_ENABLE_RDMA flags 或任意的 mlx5/GID 设置复制为通用默认值。检查当前 NVIDIA/PyTorch variables 和实际 backend logs。单节点 NCCL 测试不能证明多节点 EFA 性能。

## 历史测量：单个 L4 GPU 上的 Qwen2.5-7B

这些是 [2026 年 9 月 4 日 repository commit](https://github.com/Atom-oh/kubernetes-docs/commit/8622d388cb684dc4f68083af7be6d91f80b79106) 报告的历史测量结果。本次审计未找到原始请求结果/server logs 或完整 client artifact，也未重新运行该实验。保留报告的数值，但不将其重新标记为当前 0.29.0 性能或独立复现结果。

![历史 L4 benchmark 报告，其中说明了原始 logs 和独立复现的限制。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-6.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-6.html)

### 设置

- **Cluster**：专用 Karpenter NodePool（`bench-gpu`，按需 `g6.2xlarge` — 1x NVIDIA L4、24GB GPU memory、8 vCPU、32 GiB RAM），带有 `nvidia.com/gpu=true:NoSchedule` taint，并带标签以加入现有的 `nvidia-device-plugin` daemonsets；运行后立即删除。
- **Server**：`vllm/vllm-openai:v0.6.4.post1`（发布于 2024-11-15 — 此后 vLLM 项目已发布默认开启 prefix caching 的 V1 engine，因此应将其视为该发布线的快照，而非当前 vLLM），模型为 `Qwen/Qwen2.5-7B-Instruct`，`--dtype bfloat16 --max-model-len 4096 --gpu-memory-utilization 0.90`。一种 precision（bf16，模型的原生 dtype），未使用 quantization、speculative decoding 或 prefix caching——本页其他部分所描述的普通默认值。
- **Client**：在集群**内部**（独立的非 GPU node）以 Job 形式运行的 Python `ThreadPoolExecutor`，通过 `vllm-server` ClusterIP Service 访问 `/v1/chat/completions`。非流式，`temperature=0`、`max_tokens=128`、8 个轮换的简短 prompts（询问 Kubernetes 概念、要求用 1-2 句回答）。实际每个 response 都接近 128-token 上限（所有三个并发 batch 的平均值均约为 102 tokens），而不是在 1-2 句后停止——这有助于在不同并发级别之间进行公平的吞吐量比较，但在将延迟数值理解为“回答简短问题的时间”之前应知晓这一点。
- **Cold start**：从 vLLM engine 的启动 log 到其 `/health` endpoint 返回 `200` 约 4.5 分钟——主要耗时为将约 15 GB 的 Qwen2.5-7B-Instruct weights 从 Hugging Face 下载到 pod 的 ephemeral cache。未包括 image pull 时间；该时间未单独测量。

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

这些 manifests 展示了报告环境的一部分。它们省略了 namespace 创建、现有 EC2NodeClass 和完整 client script，因此不能证明可完整复现。nvidia.com/device-plugin.config:default 是该共享 DaemonSet 配置的条件，并非通用的调度标签要求。所报告的按需声明也需要实际的历史配置。

### 结果

| 并发数 | 请求数 | 总耗时 | Client 延迟 p50 / p90 | Client 汇总吞吐量 | Server 报告的峰值生成吞吐量 | GPU KV cache 使用率 |
|---|---|---|---|---|---|---|
| 1（串行） | 10 | ~53.2 s（请求延迟之和） | 5.65 s / 7.43 s | 每个请求约 17-18 tokens/s | ~17 tokens/s | 0.1-0.2% |
| 4 | 16 | 27.78 s | 6.99 s / 7.88 s | 58.67 tokens/s | 65-66 tokens/s | 0.4-0.7% |
| 8 | 32 | 30.02 s | 7.18 s / 8.15 s | 109.04 tokens/s | 123-129 tokens/s | 0.8-1.4% |
| 16 | 64 | 31.35 s | 7.52 s / 8.74 s | 208.08 tokens/s | 最高 243 tokens/s | 1.5-2.6% |

Client 汇总吞吐量是 completion-token 数量除以测得的总耗时。Server Avg generation throughput 是区间平均值；其记录的最大值并非瞬时“真实峰值”。时间窗口、token 计数和 HTTP 边界不同，因此它们不是可直接互换的指标。

### 解读

报告的 p50 从 5.65s 增加到 7.52s，约增加 33.1%。并发度 4→8→16 时的汇总吞吐量为 58.67→109.04→208.08tokens/s。请将这一 batching 观察与对底层瓶颈的因果证明区分开来。

将约 300GB/s 带宽除以 15.2GB 权重，可得接近 20 tokens/s 的理想化 roofline。本次审计没有直接测量带宽或 FLOP 执行的 profiler 证据，因此不能证明“肯定受内存限制”或“额外请求几乎免费”。KV-cache 占用率和总 VRAM 使用量是不同的量。

### 注意事项

这是在一个模型、一种 precision（bf16）、一种 GPU 类型和一种 context length 上进行的单次运行（n=1）——应将其视为一个经校准的数据点，而不是通用的 vLLM/L4 性能声明。Client 在集群内部（独立的非 GPU node）运行，因此网络延迟反映的是集群内部跳数，而不是外部调用方。此处延迟是完整端到端 HTTP response 时间，而不是首 token 时间（TTFT）——未测试 streaming。Prefix caching、speculative decoding、FP8 和多 GPU tensor parallelism（均在本页前文描述）均未进行测试。完整复现需要缺失的执行 artifacts 和环境细节；不要将这些数值外推到不同的模型大小、GPU 或 prompt 长度。

## 监控与日志

![API port 8000 上的实际 metrics，以及独立的 logging/access 边界。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-5.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-5.html)

### Metrics 和 Logs

默认的 /metrics endpoint 使用 API 的 port 8000。不要虚构独立的 8001 port 或 --enable-metrics=true。请在 ServiceMonitor 中匹配 Service labels、命名 ports 和 namespace 选择。

```promql
# End-to-end p95 by model
histogram_quantile(0.95, sum by (le, model_name) (rate(vllm:e2e_request_latency_seconds_bucket[5m])))
# Generation-token throughput
sum by (model_name) (rate(vllm:generation_tokens_total[5m]))
# Queued requests
sum by (model_name) (vllm:num_requests_waiting)
```

vllm:kv_cache_usage_perc 是一个 ratio，其中 1 表示 100%，而不是总 GPU-memory bytes。除了成功 counters 外，还应观察 gateway errors/cancellations；不要将健康的空闲期称为低吞吐量故障。请验证实际 endpoint names/labels。区分 CRI framing 与 application logs，并避免不加选择地记录 prompt/output/token。

## 自动扩缩容

![已验证的 metrics、一个 Pod scaling owner、独立 replicas 和独立的 node capacity owner。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-10.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-10.html)

### 自动扩缩容与可用性

使用 HPA/KEDA 扩缩独立 replicas 不同于扩缩分片模型的 worker group。增加 StatefulSet replicas 不会自动重新配置 TP/PP。验证 adapter 请求/队列信号，并且没有 CPU requests 时不要使用 CPU-utilization HPA。避免让 Karpenter/Cluster Autoscaler 竞争同一 capacity 的所有权。

PDB 约束部分自愿驱逐，而非所有故障。独立 replicas 可以跨 AZ 部署；将通信密集型 TP/PP group 跨 AZ 放置会带来独立的延迟/成本影响。在宣称更新不会中断前，请验证模型加载、warmup、draining、进行中的 streams 和备用 GPUs。

## 安全配置

--api-key 并不保护每个 endpoint。此版本的 middleware 保护 /v1、/v2、/inference 和 /cohere prefixes；/invocations、/metrics 和一些 operational endpoints 需要额外保护。经身份验证的 gateway 应只允许所需的 paths/methods；将分布式通信限制在受信任网络中。CORS 不是身份验证。

运行时 LoRA、远程模型代码和多模态 URL 分别引入 trust/permission/SSRF 边界。用 regex 阻止“ignore instructions”不能阻止所有 prompt injection，也不能保证移除 PII。无论模型输出如何，都应独立执行 tool/data permissions。

将 secrets 作为文件提供，并正确放置 Pod/container securityContext fields。使 NetworkPolicy selectors、DNS、scrape direction 和内部流量与实际配置匹配。Pod annotations 无法启用 API-server auditing；不要记录 Secret RequestResponse bodies。EKS control-plane audit 和 application access logs 是相互独立的。

## Client 集成

![经身份验证的 gateway allowlists 和独立的 operator access 保护内部 vLLM endpoints。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-7.png)

[🔍 查看交互式图表](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-7.html)

### Client 请求

在部署/readiness 验证后，已授权的开发人员可以使用 kubectl port-forward -n ml-inference service/vllm-demo 8000:8000。请保持其默认 localhost 绑定。此本地示例不能替代生产 gateway 身份验证。

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

请求 model 必须匹配 served-model-name 或 /v1/models。生产 clients 需要基于文件的 gateway credentials，以及 timeout/error/stream 处理。JSON body model field 不是 HTTP model header，因此 header routing 不会自动检查它。

## 验证范围

已检查固定 source 以确认 CLI arguments、metrics、authentication 和 artifact metadata。Kubernetes schemas/local HTTP fixtures 不会验证实际 vLLM parser/kernel/GPU 执行。本次审计未下载模型 weights，也未创建 GPU servers/cloud resources。

## 参考资料

- [vLLM 0.29.0 发布版本](https://github.com/vllm-project/vllm/releases/tag/v0.29.0)
- [并行与扩缩](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/serving/parallelism_scaling.md)
- [安全边界](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/usage/security.md)
- [生产 Metrics](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/usage/metrics.md)
- [Structured outputs](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/features/structured_outputs.md)
- [LoRA adapters](https://github.com/vllm-project/vllm/blob/v0.29.0/docs/features/lora.md)

## 测验

为测试你在本章所学内容，请尝试[主题测验](../quizzes/ai-ml/04-vllm-deployment-quiz.md)。
