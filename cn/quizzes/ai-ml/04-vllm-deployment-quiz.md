# vLLM 部署测验

本测验用于测试你对在 Kubernetes 中部署 vLLM (Vector Language Model) 的理解。

## 测验问题

### 1. vLLM (Vector Language Model) 的主要用途是什么？

A. 图像处理加速
B. Large Language Model (LLM) 推理优化和加速
C. Database 查询优化
D. 网络流量管理

<details>
<summary>显示答案</summary>

**答案：B. Large Language Model (LLM) 推理优化和加速**

**解释：**
 vLLM (Vector Language Model) 的主要用途是优化和加速 Large Language Model (LLM) 推理。vLLM 使用一种名为 PagedAttention 的创新 attention 算法来优化内存管理，从而实现高吞吐量和低延迟的 LLM 推理。

**vLLM 的关键特性：**
1. **PagedAttention**：内存高效的 attention 机制，可优化 GPU memory 使用。
2. **Continuous batching**：动态批处理请求以提高吞吐量。
3. **Distributed inference**：将大型模型分布到多个 GPU 和节点上。
4. **Various model support**：支持包括 Llama、GPT-NeoX、Falcon、MPT 在内的各种开源 LLM。
5. **OpenAI-compatible API**：提供与 OpenAI API 兼容的接口。

**PagedAttention 的工作方式：**
PagedAttention 是一种受 operating system 中虚拟内存管理启发的技术，可高效管理 KV (Key-Value) cache。传统方法会为每个请求分配固定大小的内存块，而 PagedAttention 只分配所需的内存量并进行复用。

**vLLM 的性能优势：**
1. **高吞吐量**：与现有解决方案相比，吞吐量提高 2-4 倍
2. **内存效率**：可处理最多 8 倍的并发请求
3. **低延迟**：通过高效的内存管理减少响应时间
4. **资源利用率提升**：更高效地利用 GPU 资源

**vLLM 使用场景：**
1. **Conversational AI 服务**：Chatbot、虚拟助手等。
2. **文本生成服务**：内容生成、摘要、翻译等。
3. **代码生成和补全**：编程辅助工具
4. **大规模文本处理**：文档分析、信息抽取等。

**其他选项的问题：**
- A. 图像处理加速：vLLM 用于基于文本的语言模型，并不专门用于图像处理。
- C. Database 查询优化：vLLM 与 Database 查询优化无关。
- D. 网络流量管理：vLLM 与网络流量管理无关。
</details>

### 2. 在 Kubernetes 中部署 vLLM 时，最重要的资源需求是什么？

A. 大量 CPU 和 memory
B. 高性能 GPU 和充足的 GPU memory
C. 高速网络接口
D. 大容量 persistent storage

<details>
<summary>显示答案</summary>

**答案：B. 高性能 GPU 和充足的 GPU memory**

**解释：**
在 Kubernetes 中部署 vLLM 时，最重要的资源需求是高性能 GPU 和充足的 GPU memory。Large Language Model (LLM) 拥有数十亿或数千亿个参数，要高效运行这些模型，强大的 GPU 计算能力和用于存储模型参数的充足 GPU memory 必不可少。

**GPU 要求：**
1. **GPU 类型**：NVIDIA A100、H100、V100、RTX A6000 等高性能 GPU
2. **GPU memory**：随模型大小而异，但通常为：
   - 7B 参数模型：最低 16GB GPU memory
   - 13B 参数模型：最低 24GB GPU memory
   - 70B 参数模型：最低 80GB GPU memory，或分布到多个 GPU
3. **GPU 数量**：取决于吞吐量需求和模型大小，但大型模型需要分布到多个 GPU 上。

**vLLM deployment 的 GPU resource request 示例：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            nvidia.com/gpu: 1
            cpu: 4
            memory: 16Gi
```

**大型模型的 distributed deployment 示例：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-large
  template:
    metadata:
      labels:
        app: vllm-large
    spec:
      nodeSelector:
        gpu-type: a100-80gb
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
        - --max-model-len=4096
        resources:
          limits:
            nvidia.com/gpu: 8
          requests:
            nvidia.com/gpu: 8
            cpu: 32
            memory: 128Gi
```

**GPU memory 需求计算：**
LLM 的 GPU memory 需求由以下因素决定：
1. **模型参数**：每个参数通常占用 2 字节 (FP16) 或 4 字节 (FP32)。
2. **KV cache**：每个 token 的 key-value cache 需要额外内存。
3. **Batch size**：随着并发请求数量增加，内存需求也会增加。
4. **Context length**：更长的 context length 需要更多 KV cache memory。

**近似内存需求公式：**
```
Required GPU memory = Model size + (batch size x sequence length x hidden size x layers x 4 bytes)
```

**其他资源需求：**
1. **CPU**：用于预处理和后处理的充足 CPU cores
2. **System memory**：用于模型加载和处理的充足 RAM
3. **Storage**：用于模型权重文件的充足 storage
4. **Network**：用于 distributed inference 的高速网络连接

**其他选项的问题：**
- A. 大量 CPU 和 memory：CPU 对 LLM 推理效率不高，且仅靠 system memory 无法替代 GPU memory。
- C. 高速网络接口：对 distributed inference 很重要，但优先级低于 GPU 和 GPU memory。
- D. 大容量 persistent storage：模型权重存储需要它，但不会直接影响推理性能。
</details>
### 3. Kubernetes 中 vLLM 的最佳 storage 解决方案是什么？

A. emptyDir volume
B. hostPath volume
C. 高性能 distributed file system（例如 FSx for Lustre）
D. 常规 network file system (NFS)

<details>
<summary>显示答案</summary>

**答案：C. 高性能 distributed file system（例如 FSx for Lustre）**

**解释：**
Kubernetes 中 vLLM 的最佳 storage 解决方案是高性能 distributed file system（例如 FSx for Lustre）。vLLM 需要快速加载模型权重文件来处理大型语言模型，并且在 distributed inference 环境中，多个节点需要同时访问相同的模型文件。高性能 distributed file system 通过提供高吞吐量、低延迟和并行访问能力来满足这些需求。

**高性能 distributed file system 的优势：**
1. **高吞吐量**：可以快速加载大型模型文件。
2. **并行访问**：多个节点可以同时访问相同文件。
3. **可扩展性**：可以按需扩展 storage 容量和性能。
4. **数据一致性**：在多个节点之间提供一致的数据视图。
5. **持久性**：通过数据复制和备份功能降低数据丢失风险。

**AWS FSx for Lustre configuration 示例：**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre
provisioner: fsx.csi.aws.com
parameters:
  subnetId: subnet-0eabfaa81fb22bcaf
  securityGroupIds: sg-068000ccf82dfba88
  deploymentType: SCRATCH_2
  automaticBackupRetentionDays: "0"
  dailyAutomaticBackupStartTime: "00:00"
  perUnitStorageThroughput: "200"
  dataCompressionType: "NONE"
mountOptions:
  - flock

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre
  resources:
    requests:
      storage: 1200Gi

---
# Use in vLLM deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=/models/llama-2-70b
        - --tensor-parallel-size=8
        volumeMounts:
        - name: model-storage
          mountPath: /models
        resources:
          limits:
            nvidia.com/gpu: 8
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: vllm-models
```

**Google Cloud Filestore configuration 示例：**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: filestore-hpc
provisioner: filestore.csi.storage.gke.io
parameters:
  tier: ENTERPRISE
  network: default
  location: us-central1-a

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: filestore-hpc
  resources:
    requests:
      storage: 1200Gi
```

**Azure NetApp Files configuration 示例：**
```yaml
# StorageClass definition
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: netapp-files-premium
provisioner: netapp.io/trident
parameters:
  backendType: "azure-netapp-files"
  serviceLevel: "Premium"

---
# PersistentVolumeClaim definition
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: netapp-files-premium
  resources:
    requests:
      storage: 1200Gi
```

**与其他 storage 选项的比较：**

| Storage Option | Throughput | Latency | Multi-node Access | Scalability | Persistence |
|----------------|------------|---------|-------------------|-------------|-------------|
| emptyDir | High | Very low | Not possible | Limited | Temporary |
| hostPath | High | Very low | Not possible | Limited | Node-dependent |
| NFS | Medium | Medium | Possible | Medium | Persistent |
| FSx for Lustre | Very high | Low | Possible | High | Persistent |
| Google Filestore | High | Low | Possible | High | Persistent |
| Azure NetApp Files | High | Low | Possible | High | Persistent |

**模型加载性能优化策略：**
1. **Memory mapping**：通过将大型模型文件直接映射到内存来减少加载时间
2. **Model sharding**：将模型拆分为多个 shard 并并行加载
3. **Caching**：将常用模型缓存在内存中，避免重新加载
4. **Pre-loading**：在服务启动时预加载模型，以降低首次请求延迟

**其他选项的问题：**
- A. emptyDir volume：临时 storage，pod 重启时数据会丢失。不适合存储大型模型文件。
- B. hostPath volume：依赖节点本地 storage，在多节点环境中难以共享数据。
- D. 常规 network file system (NFS)：在吞吐量和延迟方面，性能低于高性能 distributed file system。
</details>

### 4. vLLM 中 Tensor Parallelism 的主要用途是什么？

A. 并行处理多个用户请求
B. 将大型模型分布到多个 GPU 上以降低内存需求
C. 加速数据预处理
D. 优化网络通信

<details>
<summary>显示答案</summary>

**答案：B. 将大型模型分布到多个 GPU 上以降低内存需求**

**解释：**
vLLM 中 Tensor Parallelism 的主要用途是将大型模型分布到多个 GPU 上以降低内存需求。Large Language Model (LLM) 通常拥有数十亿或数千亿个参数，超过单个 GPU 的内存容量。Tensor parallelism 通过将模型层拆分到多个 GPU 上来解决这个问题，使每个 GPU 只存储和处理模型的一部分。

**Tensor Parallelism 的工作方式：**
1. **Model splitting**：将模型的每一层（尤其是 attention 和 MLP 层）拆分到多个 GPU 上。
2. **Parallel computation**：每个 GPU 对分配给自己的模型部分执行计算。
3. **Synchronization**：必要时在 GPU 之间同步中间结果。
4. **Result aggregation**：聚合每个 GPU 的结果以生成最终输出。

**vLLM 中 Tensor parallelism configuration 示例：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-tensor-parallel
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      nodeSelector:
        nvidia.com/gpu.product: A100-SXM4-80GB
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8  # Distribute model across 8 GPUs
        - --max-model-len=4096
        - --gpu-memory-utilization=0.9
        resources:
          limits:
            nvidia.com/gpu: 8  # Request 8 GPUs
```

**Tensor parallelism size 选择指南：**
1. **模型大小**：所需的 tensor parallelism size 取决于模型参数数量。
   - 7B 参数模型：1-2 个 GPU
   - 13B 参数模型：2-4 个 GPU
   - 70B 参数模型：8-16 个 GPU
   - 175B 参数模型：16+ 个 GPU

2. **GPU memory**：应根据可用 GPU memory 调整 tensor parallelism size。
   - 24GB GPU：适合小型模型
   - 40GB GPU：适合中型模型
   - 80GB GPU：适合大型模型

3. **性能考虑**：Tensor parallelism 会产生 GPU-to-GPU 通信开销。
   - Tensor parallelism size 过小：会出现内存不足问题
   - Tensor parallelism size 过大：因通信开销导致性能下降

**Tensor Parallelism 与其他并行化技术：**
1. **Data Parallelism**：同一模型的多个副本处理不同的数据 batch。主要用于训练。
2. **Pipeline Parallelism**：将模型层按顺序分布到多个 GPU 上。
3. **Tensor Parallelism**：将单个层的计算分布到多个 GPU 上。

**Tensor Parallelism 的优势：**
1. **内存效率**：通过将大型模型分布到多个 GPU 上来降低内存需求
2. **降低单个请求延迟**：通过并行计算提高推理速度
3. **资源利用率提升**：更高效地利用 GPU 资源

**Tensor Parallelism 的劣势：**
1. **通信开销**：GPU 之间数据传输产生开销
2. **实现复杂度**：模型拆分和同步逻辑复杂
3. **硬件要求**：需要高速 GPU interconnect（NVLink、NVSwitch 等）

**其他选项的问题：**
- A. 并行处理多个用户请求：这是 batch processing 或 request parallelism 的用途。
- C. 加速数据预处理：Tensor parallelism 关注模型推理，而不是数据预处理。
- D. 优化网络通信：Tensor parallelism 不会优化网络通信；相反，它会产生额外通信。
</details>
### 5. 在 Kubernetes 中确保 vLLM 服务高可用的最有效方法是什么？

A. 在单个 pod 中部署多个 containers
B. 使用包含多个 replicas 且具有适当 resource requests/limits 的 Deployment
C. 使用 DaemonSet 部署到所有 nodes
D. 使用 CronJob 定期重启

<details>
<summary>显示答案</summary>

**答案：B. 使用包含多个 replicas 且具有适当 resource requests/limits 的 Deployment**

**解释：**
在 Kubernetes 中确保 vLLM 服务高可用的最有效方法是使用包含多个 replicas 且具有适当 resource requests/limits 的 Deployment。这种方法可以在不中断服务的情况下处理流量，在节点故障时提供自动恢复，并支持根据负载进行扩展。

**高可用 vLLM deployment configuration 示例：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
  labels:
    app: vllm
spec:
  replicas: 3  # Run multiple replicas
  selector:
    matchLabels:
      app: vllm
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero downtime updates
  template:
    metadata:
      labels:
        app: vllm
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - vllm
              topologyKey: "kubernetes.io/hostname"  # Distribute pods across different nodes
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        resources:
          requests:
            nvidia.com/gpu: 1
            cpu: 4
            memory: 16Gi
          limits:
            nvidia.com/gpu: 1
            cpu: 8
            memory: 32Gi
        readinessProbe:  # Readiness check
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
        livenessProbe:  # Liveness check
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 30
        ports:
        - containerPort: 8000
          name: http
```

**Service configuration 示例：**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  type: ClusterIP
```

**Horizontal Pod Autoscaling configuration 示例：**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-service
  minReplicas: 2
  maxReplicas: 10
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
        name: inference_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

**高可用的附加配置：**

1. **Pod Disruption Budget (PDB) 设置**：
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: vllm-pdb
spec:
  minAvailable: 2  # At least 2 pods must always be running
  selector:
    matchLabels:
      app: vllm
```

2. **Node affinity 和 tolerations**：
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: nvidia.com/gpu.product
          operator: In
          values:
          - A100-SXM4-40GB
          - A100-SXM4-80GB
tolerations:
- key: nvidia.com/gpu
  operator: Exists
  effect: NoSchedule
```

3. **Topology spread constraints**：
```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector:
    matchLabels:
      app: vllm
```

**高可用配置的关键收益：**
1. **容错能力**：即使 node 或 pod 故障，也能继续提供服务
2. **Load balancing**：将流量分布到多个实例
3. **零停机更新**：通过 rolling updates 实现不中断部署
4. **Auto-scaling**：基于负载自动扩缩容
5. **Auto-recovery**：自动重启失败的 pods

**Load balancing 策略：**
1. **内部 service load balancing**：通过 Kubernetes Service 实现基础 load balancing
2. **外部 load balancing**：通过 Ingress 或云 load balancer 分发外部流量
3. **Session affinity**：需要时将同一客户端请求路由到同一 pod

**Monitoring 和 alerting：**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-monitor
spec:
  selector:
    matchLabels:
      app: vllm
  endpoints:
  - port: http
    interval: 15s
    path: /metrics
```

**其他选项的问题：**
- A. 在单个 pod 中部署多个 containers：发生节点故障时整个服务可能中断，无法提供真正的高可用。
- C. 使用 DaemonSet 部署到所有 nodes：并非所有 nodes 都保证有 GPU，可能造成资源浪费。
- D. 使用 CronJob 定期重启：这会造成服务中断，不是高可用解决方案。
</details>

### 6. vLLM 中 “Continuous Batching” 的主要收益是什么？

A. 提高模型准确性
B. 提高吞吐量并改善 GPU 利用率
C. 减小模型大小
D. 节省网络带宽

<details>
<summary>显示答案</summary>

**答案：B. 提高吞吐量并改善 GPU 利用率**

**解释：**
vLLM 中 “Continuous Batching” 的主要收益是提高吞吐量并改善 GPU 利用率。Continuous batching 会将不同长度和不同开始时间的请求动态分组为 batch 进行处理，从而更高效地使用 GPU 资源，并显著提高整体系统吞吐量。

**传统 batching 与 Continuous batching：**
1. **传统 batching**：
   - 等待请求形成固定大小的 batch
   - 所有请求同时开始并同时结束
   - 需要 padding 以匹配 batch 中最长的 sequence
   - 新请求必须等到当前 batch 完成

2. **Continuous batching**：
   - 请求到达时动态处理
   - 同时处理不同开始时间和不同长度的请求
   - 无需不必要的 padding，内存使用更高效
   - 已完成请求释放的资源会立即分配给新请求

**Continuous Batching 的工作方式：**
1. **动态请求调度**：请求到达时立即开始处理
2. **逐 token 处理**：每个请求按 token 逐步处理，每一步生成新 token
3. **资源重新分配**：已完成请求释放的资源立即分配给新请求
4. **KV cache 管理**：通过 PagedAttention 高效管理 KV cache

**Continuous Batching 的收益：**
1. **高吞吐量**：通过更高效地利用 GPU 资源，提高每秒处理的请求数量
2. **低延迟**：请求不需要等待 batch 形成
3. **资源利用率提升**：减少 GPU 计算和内存资源的空闲时间
4. **处理多样化请求长度**：高效处理不同长度的请求

**vLLM configuration 中的 Continuous batching 设置：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        - --max-num-batched-tokens=8192  # Maximum tokens per batch
        - --max-num-seqs=256  # Maximum sequences to process simultaneously
        - --max-model-len=4096  # Maximum context length
        resources:
          limits:
            nvidia.com/gpu: 1
```

**Continuous batching 性能优化：**
1. **最佳 batch size 设置**：
   - `max-num-batched-tokens`：一次可处理的最大 tokens 数
   - `max-num-seqs`：可同时处理的最大 sequences 数

2. **GPU memory utilization 调整**：
   - `gpu-memory-utilization`：设置 GPU memory 使用比例 (0.0-1.0)

3. **KV cache 管理**：
   - `max-model-len`：设置最大 context length
   - `block-size`：设置 PagedAttention block size

**性能 benchmark 示例：**
| Batching Method | Throughput (req/sec) | Average Latency (ms) | GPU Utilization (%) |
|-----------------|----------------------|----------------------|---------------------|
| Static batching | 10 | 500 | 60% |
| Continuous batching | 25 | 300 | 90% |

**Continuous Batching 的限制：**
1. **内存管理复杂度**：由于动态内存分配和释放，复杂度增加
2. **调度开销**：动态请求调度带来额外开销
3. **优化难度**：难以针对各种 workload 设置最佳参数

**其他选项的问题：**
- A. 提高模型准确性：Continuous batching 不影响模型准确性。
- C. 减小模型大小：Continuous batching 不会改变模型大小。
- D. 节省网络带宽：Continuous batching 不会直接影响网络带宽使用。
</details>
### 7. 在 Kubernetes 中监控 vLLM 服务时最重要的指标是什么？

A. Pod restart count
B. 推理延迟、吞吐量、GPU memory 使用率
C. 网络 packet loss rate
D. Disk I/O performance

<details>
<summary>显示答案</summary>

**答案：B. 推理延迟、吞吐量、GPU memory 使用率**

**解释：**
在 Kubernetes 中监控 vLLM 服务时，最重要的指标是推理延迟、吞吐量和 GPU memory 使用率。这些指标直接反映 vLLM 服务的性能、效率和资源利用率，并直接影响服务质量 (QoS) 和用户体验。

**关键监控指标：**

1. **推理延迟**：
   - **定义**：从接收请求到返回响应的时间
   - **重要性**：直接影响用户体验和服务响应能力
   - **计量单位**：毫秒 (ms) 或秒 (s)
   - **详细指标**：
     - Time to First Token
     - Time per Token
     - Total Generation Time

2. **吞吐量**：
   - **定义**：单位时间内可处理的请求数或 tokens 数
   - **重要性**：系统容量和可扩展性评估
   - **计量单位**：Requests per Second (RPS) 或 Tokens per Second (TPS)
   - **详细指标**：
     - Requests per Second
     - Tokens per Second
     - Batch Size

3. **GPU memory 使用率**：
   - **定义**：vLLM 服务使用的 GPU memory 量
   - **重要性**：防止内存不足并优化资源
   - **计量单位**：Gigabytes (GB) 或 Megabytes (MB)
   - **详细指标**：
     - Model weight memory usage
     - KV cache memory usage
     - Activation memory usage
     - Total GPU memory usage

**Prometheus metrics configuration 示例：**
```yaml
# Expose metrics from vLLM service
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        - --tensor-parallel-size=1
        - --enable-metrics=true  # Enable metrics
```

**Prometheus ServiceMonitor configuration：**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: vllm
  endpoints:
  - port: http
    interval: 15s
    path: /metrics
```

**关键 vLLM metrics 和 PromQL queries：**

1. **推理延迟**：
   ```
   # 95th percentile inference latency
   histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))

   # Average time per token generation
   avg(rate(vllm_token_generation_time_seconds_sum[5m]) / rate(vllm_token_generation_time_seconds_count[5m]))
   ```

2. **吞吐量**：
   ```
   # Requests per second
   sum(rate(vllm_requests_total[5m]))

   # Tokens per second
   sum(rate(vllm_generated_tokens_total[5m]))
   ```

3. **GPU memory 使用率**：
   ```
   # GPU memory usage
   vllm_gpu_memory_used_bytes

   # KV cache memory usage
   vllm_kv_cache_memory_bytes
   ```

**Grafana dashboard configuration 示例：**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  vllm-dashboard.json: |
    {
      "title": "vLLM Performance Dashboard",
      "panels": [
        {
          "title": "Inference Latency",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))",
              "legendFormat": "p95 Latency"
            },
            {
              "expr": "histogram_quantile(0.50, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))",
              "legendFormat": "p50 Latency"
            }
          ]
        },
        {
          "title": "Throughput",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "sum(rate(vllm_requests_total[5m]))",
              "legendFormat": "Requests/sec"
            },
            {
              "expr": "sum(rate(vllm_generated_tokens_total[5m]))",
              "legendFormat": "Tokens/sec"
            }
          ]
        },
        {
          "title": "GPU Memory Usage",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "vllm_gpu_memory_used_bytes / 1024 / 1024 / 1024",
              "legendFormat": "GPU Memory (GB)"
            },
            {
              "expr": "vllm_kv_cache_memory_bytes / 1024 / 1024 / 1024",
              "legendFormat": "KV Cache (GB)"
            }
          ]
        },
        {
          "title": "GPU Utilization",
          "type": "graph",
          "datasource": "Prometheus",
          "targets": [
            {
              "expr": "DCGM_FI_DEV_GPU_UTIL",
              "legendFormat": "GPU {{gpu}}"
            }
          ]
        }
      ]
    }
```

**Alert rule configuration 示例：**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vllm-alerts
  namespace: monitoring
spec:
  groups:
  - name: vllm.rules
    rules:
    - alert: HighInferenceLatency
      expr: histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le)) > 2
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High inference latency"
        description: "95th percentile latency is above 2 seconds"

    - alert: LowThroughput
      expr: sum(rate(vllm_requests_total[5m])) < 10
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Low request throughput"
        description: "Request throughput is below 10 RPS"

    - alert: HighGPUMemoryUsage
      expr: vllm_gpu_memory_used_bytes / vllm_gpu_memory_total_bytes > 0.95
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High GPU memory usage"
        description: "GPU memory usage is above 95%"
```

**附加监控指标：**
1. **GPU utilization**：GPU compute units 的利用率
2. **CPU usage**：用于预处理和后处理的 CPU 资源
3. **System memory usage**：Host memory 使用率
4. **Error rate**：失败请求比例
5. **Queue length**：等待处理的请求数
6. **Batch efficiency**：平均 batch size 和利用率

**Monitoring tool integration：**
1. **Prometheus + Grafana**：Metric collection 和 visualization
2. **NVIDIA DCGM Exporter**：GPU metric collection
3. **Jaeger/Zipkin**：Distributed tracing
4. **ELK Stack**：Log collection 和 analysis

**其他选项的问题：**
- A. Pod restart count：这是系统稳定性的指标，但不直接反映 vLLM 服务性能。
- C. 网络 packet loss rate：有助于诊断网络问题，但不是 vLLM 服务的核心性能指标。
- D. Disk I/O performance：在模型加载期间可能重要，但对运行中的 vLLM 服务性能不那么重要。
</details>

### 8. Kubernetes 中 vLLM 服务的最佳网络配置是什么？

A. 使用默认 CNI plugin
B. 支持 tensor parallelism 的高性能网络接口和 RDMA
C. 使用 network policies 限制所有流量
D. 实现 service mesh

<details>
<summary>显示答案</summary>

**答案：B. 支持 tensor parallelism 的高性能网络接口和 RDMA**

**解释：**
Kubernetes 中 vLLM 服务的最佳网络配置是支持 tensor parallelism 的高性能网络接口和 RDMA (Remote Direct Memory Access)。当运行分布到多个 GPU 的大型语言模型时，GPU-to-GPU 通信性能会显著影响整体系统性能。高性能网络接口和 RDMA 支持可最大限度降低 GPU-to-GPU 数据传输延迟，并最大化吞吐量，从而提高 distributed inference 性能。

**高性能网络的重要性：**
1. **Tensor parallelism**：将模型层分布到多个 GPU 时需要频繁的 GPU-to-GPU 通信
2. **Model sharding**：将大型模型分布到多个节点时，节点间网络性能很重要
3. **延迟敏感性**：GPU-to-GPU 通信延迟直接影响整体推理延迟
4. **带宽需求**：大型 tensor 数据传输需要高带宽

**最佳网络配置组件：**

1. **高性能网络接口**：
   - **NVIDIA ConnectX-6/7**：支持最高 200Gbps 带宽
   - **InfiniBand**：超低延迟高带宽网络
   - **RDMA over Converged Ethernet (RoCE)**：Ethernet 网络上的 RDMA 能力

2. **RDMA (Remote Direct Memory Access) 支持**：
   - 无需 CPU 参与即可在 GPU memory 之间直接传输数据
   - 最小化延迟并最大化吞吐量
   - GPU Direct RDMA：GPU memory 之间的直接数据传输

3. **NVLink/NVSwitch**：
   - 同一节点内 GPU 之间的高速连接
   - 最高 600GB/s 带宽 (NVLink 4.0)
   - 对多 GPU 系统很重要

**Kubernetes 中的高性能网络配置：**

1. **SR-IOV (Single Root I/O Virtualization) Network Device Plugin**：
```yaml
# SR-IOV network device plugin configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: sriovdp-config
  namespace: kube-system
data:
  config.json: |
    {
      "resourceList": [
        {
          "resourceName": "nvidia_sriov_netdevice",
          "rootDevices": ["0000:03:00.0"],
          "sriovMode": true,
          "deviceType": "netdevice"
        },
        {
          "resourceName": "nvidia_sriov_rdma",
          "rootDevices": ["0000:03:00.0"],
          "sriovMode": true,
          "deviceType": "rdma"
        }
      ]
    }
```

2. **NetworkAttachmentDefinition configuration**：
```yaml
apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-rdma-network
spec:
  config: '{
    "cniVersion": "0.3.1",
    "name": "sriov-rdma-network",
    "type": "sriov",
    "ipam": {
      "type": "host-local",
      "subnet": "192.168.1.0/24",
      "rangeStart": "192.168.1.10",
      "rangeEnd": "192.168.1.200"
    },
    "capabilities": { "ips": true }
  }'
```

3. **将高性能网络配置应用到 vLLM deployment**：
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-distributed
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
      annotations:
        k8s.v1.cni.cncf.io/networks: sriov-rdma-network
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
        - --max-model-len=4096
        resources:
          limits:
            nvidia.com/gpu: 8
            nvidia.com/sriov_rdma: 8
        env:
        - name: NCCL_DEBUG
          value: "INFO"
        - name: NCCL_IB_DISABLE
          value: "0"
        - name: NCCL_IB_GID_INDEX
          value: "3"
        - name: NCCL_IB_HCA
          value: "mlx5_0:1,mlx5_1:1,mlx5_2:1,mlx5_3:1"
        - name: NCCL_SOCKET_IFNAME
          value: "eth0,ens"
```

**NCCL (NVIDIA Collective Communications Library) configuration：**
NCCL 是一个优化 GPU-to-GPU 通信的库，可通过以下环境变量进行配置：

```
# Enable NCCL debug information
NCCL_DEBUG=INFO

# Enable InfiniBand usage
NCCL_IB_DISABLE=0

# Set InfiniBand GID index
NCCL_IB_GID_INDEX=3

# Specify HCA (Host Channel Adapter) to use
NCCL_IB_HCA=mlx5_0:1,mlx5_1:1

# Specify network interface
NCCL_SOCKET_IFNAME=eth0,ens

# Enable RDMA transport
NCCL_IB_ENABLE_RDMA=1

# Enable GPU Direct RDMA
NCCL_IB_GDR_LEVEL=4
```

**多节点 distributed configuration：**
当将 vLLM 分布到多个节点时，节点间网络性能会变得更加重要。需要以下配置：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vllm-distributed-node1
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-rdma-network
spec:
  nodeSelector:
    kubernetes.io/hostname: node1
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model=meta-llama/Llama-2-70b-chat-hf
    - --tensor-parallel-size=16
    - --tensor-parallel-rank=0-7
    - --distributed-init-method=tcp://vllm-init:7777
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_IB_DISABLE
      value: "0"
    resources:
      limits:
        nvidia.com/gpu: 8
        nvidia.com/sriov_rdma: 8

---
apiVersion: v1
kind: Pod
metadata:
  name: vllm-distributed-node2
  annotations:
    k8s.v1.cni.cncf.io/networks: sriov-rdma-network
spec:
  nodeSelector:
    kubernetes.io/hostname: node2
  containers:
  - name: vllm
    image: vllm/vllm-openai:latest
    args:
    - --model=meta-llama/Llama-2-70b-chat-hf
    - --tensor-parallel-size=16
    - --tensor-parallel-rank=8-15
    - --distributed-init-method=tcp://vllm-init:7777
    env:
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_IB_DISABLE
      value: "0"
    resources:
      limits:
        nvidia.com/gpu: 8
        nvidia.com/sriov_rdma: 8
```

**网络性能测试：**
```bash
# Run NCCL test
kubectl run nccl-test --image=nvidia/cuda:11.8.0-devel-ubuntu22.04 --overrides='{"spec": {"containers": [{"name": "nccl-test", "image": "nvidia/cuda:11.8.0-devel-ubuntu22.04", "command": ["/bin/bash", "-c"], "args": ["apt-get update && apt-get install -y git && git clone https://github.com/NVIDIA/nccl-tests.git && cd nccl-tests && make && ./build/all_reduce_perf -b 8 -e 128M -f 2 -g 8"], "resources": {"limits": {"nvidia.com/gpu": 8}}}]}}' --restart=Never

# Network bandwidth test
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201
kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**其他选项的问题：**
- A. 使用默认 CNI plugin：默认 CNI plugins 通常不支持 RDMA 等高性能网络功能，也无法提供 tensor parallelism 所需的性能。
- C. 使用 network policies 限制所有流量：这可以增强安全性，但不会提高性能，并且可能增加额外开销。
- D. 实现 service mesh：Service mesh 对 microservices 架构有用，但会为 vLLM 这类高性能计算 workload 增加不必要的开销。
</details>
### 9. 提高 Kubernetes 中 vLLM 服务可扩展性的最有效方法是什么？

A. 分配更多 CPU cores
B. 将 horizontal scaling（多个 replicas）与 load balancing 和 vertical scaling（更大的 GPU）相结合
C. 分配更多 memory
D. 配置更大的 persistent volumes

<details>
<summary>显示答案</summary>

**答案：B. 将 horizontal scaling（多个 replicas）与 load balancing 和 vertical scaling（更大的 GPU）相结合**

**解释：**
提高 Kubernetes 中 vLLM 服务可扩展性的最有效方法，是将 horizontal scaling（多个 replicas）与 load balancing 和 vertical scaling（更大的 GPU）相结合。这种方法可以灵活应对各种 workload 需求和资源约束，并平衡成本效率与性能。

**Horizontal Scaling 的收益：**
1. **吞吐量提升**：使用更多 replicas 可以处理更多并发请求
2. **高可用**：即使部分实例失败，服务也会继续运行
3. **地理分布**：跨多个 region 部署以降低延迟
4. **成本效率**：可按需调整实例数量

**Vertical Scaling 的收益：**
1. **支持更大模型**：更大的 GPU memory 可以加载更大模型
2. **降低单个请求延迟**：更强大的 GPU 可提高推理速度
3. **处理更长 context**：更多 memory 可处理更长 context
4. **降低通信开销**：使用单个 GPU 或单节点内多个 GPU 时可降低通信开销

**Horizontal scaling configuration 示例：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  replicas: 5  # Run multiple replicas
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
        resources:
          limits:
            nvidia.com/gpu: 1
```

**Horizontal auto-scaling configuration：**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-service
  minReplicas: 2
  maxReplicas: 10
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
        name: inference_requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

**Vertical scaling configuration 示例：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large-model
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-large
  template:
    metadata:
      labels:
        app: vllm-large
    spec:
      nodeSelector:
        gpu-type: a100-80gb  # Select larger GPU
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8  # Distribute model across multiple GPUs
        resources:
          limits:
            nvidia.com/gpu: 8  # Allocate more GPUs
```

**Load balancing configuration：**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vllm-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/affinity: "cookie"
    nginx.ingress.kubernetes.io/session-cookie-name: "route"
    nginx.ingress.kubernetes.io/session-cookie-expires: "172800"
    nginx.ingress.kubernetes.io/session-cookie-max-age: "172800"
spec:
  rules:
  - host: vllm.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: vllm-service
            port:
              number: 80
```

**Model sharding 和 routing：**
可以组合多个 deployments 并进行路由，以支持各种模型大小和类型：

```yaml
# Small model deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-small
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-7b-chat-hf
---
# Medium model deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-medium
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-13b-chat-hf
---
# Large model deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-large
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: vllm
        args:
        - --model=meta-llama/Llama-2-70b-chat-hf
        - --tensor-parallel-size=8
```

**API gateway configuration：**
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: vllm-routing
spec:
  hosts:
  - "api.example.com"
  gateways:
  - api-gateway
  http:
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-7b"
    route:
    - destination:
        host: vllm-small
        port:
          number: 8000
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-13b"
    route:
    - destination:
        host: vllm-medium
        port:
          number: 8000
  - match:
    - uri:
        prefix: "/v1/completions"
      headers:
        model:
          exact: "llama-2-70b"
    route:
    - destination:
        host: vllm-large
        port:
          number: 8000
```

**可扩展性优化策略：**
1. **请求路由优化**：
   - 根据模型大小和复杂度将请求路由到合适实例
   - 通过 session affinity 优化 KV cache 复用

2. **资源分配优化**：
   - 选择适合 workload 特征的 GPU 类型
   - 设置适当的 tensor parallelism size

3. **Caching 策略**：
   - 缓存常用 prompts 和 responses
   - 模型权重缓存

4. **Hybrid cloud scaling**：
   - 结合本地和云资源
   - 使用云扩展应对突发流量

**可扩展性测试和 benchmarking：**
```bash
# Run load test
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**其他选项的问题：**
- A. 分配更多 CPU cores：vLLM 主要受 GPU 限制，仅增加 CPU cores 不会显著提升性能。
- C. 分配更多 memory：System memory 很重要，但 GPU memory 是主要约束。
- D. 配置更大的 persistent volumes：Storage 容量对模型存储很重要，但不会直接影响推理性能和可扩展性。
</details>

### 10. 在 Kubernetes 中部署 vLLM 时，最重要的安全考虑是什么？

A. Network policy configuration
B. 保护模型权重和 API keys，进行 container security hardening
C. Pod security policy configuration
D. 启用 audit logging

<details>
<summary>显示答案</summary>

**答案：B. 保护模型权重和 API keys，进行 container security hardening**

**解释：**
在 Kubernetes 中部署 vLLM 时，最重要的安全考虑是保护模型权重和 API keys，并进行 container security hardening。vLLM 服务会处理具有知识产权价值的模型权重、敏感 API keys 和用户数据，因此保护这些资产并加强 container 环境安全最为重要。

**关键安全考虑：**

1. **模型权重保护**：
   - 模型权重是具有知识产权的宝贵资产。
   - 必须防止未经授权的访问、复制和泄露。
   - 需要加密 storage 和传输中加密。

2. **API key 和认证信息保护**：
   - API keys、tokens 和 passwords 等认证信息必须安全管理。
   - 应使用 Kubernetes Secrets 或外部 secret management systems。
   - 应通过 mounted volumes 提供 secrets，而不是通过环境变量。

3. **Container security hardening**：
   - 应用最小权限原则
   - 以非 root 用户运行 containers
   - 使用只读 file system
   - 移除不必要的 capabilities 和 privileges

4. **输入验证和输出过滤**：
   - 防止 prompt injection 攻击
   - 防止敏感信息泄露
   - 过滤有害内容

**模型权重保护 configuration 示例：**
```yaml
# Encrypted persistent volume claim
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: encrypted-storage
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3
  encrypted: "true"
  kmsKeyId: arn:aws:kms:us-west-2:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-storage
spec:
  accessModes:
    - ReadOnlyMany
  storageClassName: encrypted-storage
  resources:
    requests:
      storage: 100Gi

---
# Restrict access to model weights
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      securityContext:
        fsGroup: 1000
        runAsUser: 1000
        runAsGroup: 1000
      containers:
      - name: vllm
        volumeMounts:
        - name: model-volume
          mountPath: /models
          readOnly: true
      volumes:
      - name: model-volume
        persistentVolumeClaim:
          claimName: model-storage
```

**API key 和认证信息保护：**
```yaml
# Use Kubernetes Secrets
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
type: Opaque
data:
  openai-api-key: base64EncodedApiKey
  huggingface-token: base64EncodedToken

---
# External secret management system integration (HashiCorp Vault)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vllm-service
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/agent-inject-secret-api-keys: "secret/data/api-keys"
    vault.hashicorp.com/role: "vllm-role"

---
# Mount secrets as volume
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      containers:
      - name: vllm
        volumeMounts:
        - name: api-keys
          mountPath: /app/secrets
          readOnly: true
      volumes:
      - name: api-keys
        secret:
          secretName: api-keys
```

**Container security hardening：**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    spec:
      # Pod level security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        # Container level security context
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
          seccompProfile:
            type: RuntimeDefault
```

**Network policy：**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
spec:
  podSelector:
    matchLabels:
      app: vllm
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
    ports:
    - protocol: TCP
      port: 9090
  - to:
    - namespaceSelector:
        matchLabels:
          name: huggingface
    ports:
    - protocol: TCP
      port: 443
```

**输入验证和输出过滤：**
```python
# Prompt validation and filtering example
def validate_prompt(prompt):
    # Check prompt injection patterns
    if re.search(r"(ignore|forget|disregard).*instructions", prompt, re.IGNORECASE):
        return False, "Potential prompt injection detected"

    # Check sensitive commands
    if re.search(r"(system|sudo|exec|eval)", prompt, re.IGNORECASE):
        return False, "Potentially harmful commands detected"

    return True, prompt

# Output filtering example
def filter_output(response):
    # PII filtering
    response = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED SSN]", response)
    response = re.sub(r"\b\d{16}\b", "[REDACTED CREDIT CARD]", response)

    # Harmful content filtering
    for harmful_pattern in HARMFUL_PATTERNS:
        if re.search(harmful_pattern, response, re.IGNORECASE):
            response = "[Content removed due to policy violation]"
            break

    return response
```

**RBAC (Role-Based Access Control) configuration：**
```yaml
# Create service account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vllm-service
  namespace: ml-services

---
# Role definition
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: vllm-role
  namespace: ml-services
rules:
- apiGroups: [""]
  resources: ["secrets"]
  verbs: ["get"]
  resourceNames: ["model-access-keys"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get"]
  resourceNames: ["vllm-config"]

---
# Role binding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: vllm-role-binding
  namespace: ml-services
subjects:
- kind: ServiceAccount
  name: vllm-service
  namespace: ml-services
roleRef:
  kind: Role
  name: vllm-role
  apiGroup: rbac.authorization.k8s.io
```

**Audit logging configuration：**
```yaml
# ConfigMap for audit logging
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-audit-config
data:
  audit.yaml: |
    apiVersion: audit.k8s.io/v1
    kind: Policy
    rules:
    - level: RequestResponse
      resources:
      - group: ""
        resources: ["secrets"]
    - level: Metadata
      resources:
      - group: ""
        resources: ["pods"]

# Enable audit logging
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-service
spec:
  template:
    metadata:
      annotations:
        audit-log-path: "/var/log/vllm/audit.log"
        audit-log-maxage: "30"
        audit-log-maxbackup: "10"
        audit-log-maxsize: "100"
    spec:
      containers:
      - name: vllm
        volumeMounts:
        - name: audit-logs
          mountPath: /var/log/vllm
      volumes:
      - name: audit-logs
        emptyDir: {}
```

**其他安全最佳实践：**
1. **定期安全扫描**：扫描 container images 和 dependencies 中的漏洞
2. **最小权限原则**：仅授予所需的最小权限
3. **Immutable infrastructure**：需要变更时部署新的 containers
4. **安全监控**：检测异常行为并发送 alerts
5. **应急响应计划**：为安全事件准备响应流程

**其他选项的问题：**
- A. Network policy configuration：很重要，但优先级低于保护模型权重和 API keys 以及 container security hardening。
- C. Pod security policy configuration：是 container security 的一部分，但不包括模型权重和 API key 保护。
- D. 启用 audit logging：对安全监控很重要，但优先级低于预防性安全措施。
</details>
