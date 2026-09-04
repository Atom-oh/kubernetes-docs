# vLLM 部署测验

本测验用于检验你对在 Kubernetes 中部署 vLLM（Vector Language Model）的理解。

## 测验问题

### 1. vLLM（Vector Language Model）的主要用途是什么？

A. 图像处理加速
B. Large Language Model（LLM）推理优化和加速
C. 数据库查询优化
D. 网络流量管理

<details>
<summary>显示答案</summary>

**答案：B. Large Language Model（LLM）推理优化和加速**

**说明：**
vLLM（Vector Language Model）的主要用途是优化和加速 Large Language Model（LLM）推理。vLLM 使用名为 PagedAttention 的创新注意力算法来优化内存管理，从而实现高吞吐量、低延迟的 LLM 推理。

**vLLM 的主要特性：**
1. **PagedAttention**：可优化 GPU 内存使用的高内存效率注意力机制。
2. **Continuous batching**：动态地将请求批处理，以提高吞吐量。
3. **Distributed inference**：在多个 GPU 和节点之间分配大型模型。
4. **Various model support**：支持 Llama、GPT-NeoX、Falcon、MPT 等多种开源 LLM。
5. **OpenAI-compatible API**：提供与 OpenAI API 兼容的接口。

**PagedAttention 的工作原理：**
PagedAttention 是一种受操作系统虚拟内存管理启发的技术，可高效管理 KV（Key-Value）缓存。传统方法会为每个请求分配固定大小的内存块，而 PagedAttention 仅分配所需的内存并重复使用它。

**vLLM 的性能优势：**
1. **高吞吐量**：与现有解决方案相比，吞吐量高出 2-4 倍
2. **内存效率**：最多可处理 8 倍以上的并发请求
3. **低延迟**：通过高效的内存管理缩短响应时间
4. **提高资源利用率**：更高效地利用 GPU 资源

**vLLM 使用场景：**
1. **Conversational AI 服务**：Chatbot、虚拟助手等
2. **文本生成服务**：内容生成、摘要、翻译等
3. **代码生成和补全**：编程辅助工具
4. **大规模文本处理**：文档分析、信息提取等

**其他选项的问题：**
- A. 图像处理加速：vLLM 面向基于文本的语言模型，并不专用于图像处理。
- C. 数据库查询优化：vLLM 与数据库查询优化无关。
- D. 网络流量管理：vLLM 与网络流量管理无关。
</details>

### 2. 在 Kubernetes 中部署 vLLM 时，最重要的资源要求是什么？

A. 大量 CPU 和内存
B. 高性能 GPU 和充足的 GPU 内存
C. 高速网络接口
D. 大型持久存储

<details>
<summary>显示答案</summary>

**答案：B. 高性能 GPU 和充足的 GPU 内存**

**说明：**
在 Kubernetes 中部署 vLLM 时，最重要的资源要求是高性能 GPU 和充足的 GPU 内存。Large Language Model（LLM）拥有数十亿甚至数千亿个参数，要高效运行这些模型，强大的 GPU 计算能力以及用于存储模型参数的充足 GPU 内存至关重要。

**GPU 要求：**
1. **GPU 类型**：如 NVIDIA A100、H100、V100、RTX A6000 等高性能 GPU
2. **GPU 内存**：因模型大小而异，但通常为：
   - 70 亿参数模型：至少 16GB GPU 内存
   - 130 亿参数模型：至少 24GB GPU 内存
   - 700 亿参数模型：至少 80GB GPU 内存，或分布到多个 GPU 上
3. **GPU 数量**：取决于吞吐量要求和模型大小，但大型模型需要分布到多个 GPU 上。

**vLLM 部署的 GPU 资源请求示例：**
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

**大型模型的分布式部署示例：**
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

**GPU 内存要求计算：**
LLM GPU 内存要求由以下因素决定：
1. **模型参数**：每个参数通常占用 2 字节（FP16）或 4 字节（FP32）。
2. **KV 缓存**：每个 token 的 Key-Value 缓存需要额外内存。
3. **Batch size**：并发请求数量增加时，内存要求也会增加。
4. **上下文长度**：更长的上下文长度需要更多 KV 缓存内存。

**近似内存要求公式：**
```
Required GPU memory = Model size + (batch size x sequence length x hidden size x layers x 4 bytes)
```

**其他资源要求：**
1. **CPU**：用于预处理和后处理的充足 CPU 核心
2. **系统内存**：用于模型加载和处理的充足 RAM
3. **存储**：用于模型权重文件的充足存储空间
4. **网络**：用于分布式推理的高速网络连接

**其他选项的问题：**
- A. 大量 CPU 和内存：CPU 不适合 LLM 推理，且仅靠系统内存无法替代 GPU 内存。
- C. 高速网络接口：对分布式推理很重要，但优先级低于 GPU 和 GPU 内存。
- D. 大型持久存储：模型权重存储需要它，但它不会直接影响推理性能。
</details>
### 3. Kubernetes 中 vLLM 的最佳存储解决方案是什么？

A. emptyDir 卷
B. hostPath 卷
C. 高性能分布式文件系统（例如 FSx for Lustre）
D. 普通网络文件系统（NFS）

<details>
<summary>显示答案</summary>

**答案：C. 高性能分布式文件系统（例如 FSx for Lustre）**

**说明：**
Kubernetes 中 vLLM 的最佳存储解决方案是高性能分布式文件系统（例如 FSx for Lustre）。vLLM 需要快速加载模型权重文件以处理 Large Language Model，并且在分布式推理环境中，多个节点需要同时访问相同的模型文件。高性能分布式文件系统通过提供高吞吐量、低延迟和并行访问能力来满足这些要求。

**高性能分布式文件系统的优势：**
1. **高吞吐量**：可快速加载大型模型文件。
2. **并行访问**：多个节点可同时访问相同文件。
3. **可扩展性**：可按需扩展存储容量和性能。
4. **数据一致性**：在多个节点之间提供一致的数据视图。
5. **持久性**：通过数据复制和备份功能降低数据丢失风险。

**AWS FSx for Lustre 配置示例：**
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

**Google Cloud Filestore 配置示例：**
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

**Azure NetApp Files 配置示例：**
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

**与其他存储选项的比较：**

| 存储选项 | 吞吐量 | 延迟 | 多节点访问 | 可扩展性 | 持久性 |
|----------------|------------|---------|-------------------|-------------|-------------|
| emptyDir | 高 | 非常低 | 不可用 | 有限 | 临时 |
| hostPath | 高 | 非常低 | 不可用 | 有限 | 依赖节点 |
| NFS | 中等 | 中等 | 可用 | 中等 | 持久 |
| FSx for Lustre | 非常高 | 低 | 可用 | 高 | 持久 |
| Google Filestore | 高 | 低 | 可用 | 高 | 持久 |
| Azure NetApp Files | 高 | 低 | 可用 | 高 | 持久 |

**模型加载性能优化策略：**
1. **内存映射**：通过将大型模型文件直接映射到内存来减少加载时间
2. **模型分片**：将模型拆分为多个分片并行加载
3. **缓存**：将常用模型缓存在内存中以避免重新加载
4. **预加载**：在服务启动时预加载模型以缩短首次请求延迟

**其他选项的问题：**
- A. emptyDir 卷：Pod 重启时数据会丢失的临时存储。不适合存储大型模型文件。
- B. hostPath 卷：依赖节点本地存储，使得多节点环境中的数据共享变得困难。
- D. 普通网络文件系统（NFS）：在吞吐量和延迟方面，其性能低于高性能分布式文件系统。
</details>

### 4. vLLM 中 Tensor Parallelism 的主要用途是什么？

A. 并行处理多个用户请求
B. 将大型模型分布到多个 GPU 以降低内存要求
C. 加速数据预处理
D. 优化网络通信

<details>
<summary>显示答案</summary>

**答案：B. 将大型模型分布到多个 GPU 以降低内存要求**

**说明：**
vLLM 中 Tensor Parallelism 的主要用途是将大型模型分布到多个 GPU 以降低内存要求。Large Language Model（LLM）通常拥有数十亿甚至数千亿个参数，超出单个 GPU 的内存容量。Tensor parallelism 通过在多个 GPU 之间拆分模型层来解决这个问题，使每个 GPU 仅存储和处理模型的一部分。

**Tensor Parallelism 的工作原理：**
1. **模型拆分**：将模型的每一层（尤其是注意力层和 MLP 层）拆分到多个 GPU 上。
2. **并行计算**：每个 GPU 对其分配的模型部分执行计算。
3. **同步**：必要时在 GPU 之间同步中间结果。
4. **结果聚合**：聚合每个 GPU 的结果以生成最终输出。

**vLLM 中的 Tensor parallelism 配置示例：**
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

**Tensor parallelism 大小选择指南：**
1. **模型大小**：所需的 Tensor parallelism 大小取决于模型参数数量。
   - 70 亿参数模型：1-2 个 GPU
   - 130 亿参数模型：2-4 个 GPU
   - 700 亿参数模型：8-16 个 GPU
   - 1750 亿参数模型：16+ 个 GPU

2. **GPU 内存**：应根据可用 GPU 内存调整 Tensor parallelism 大小。
   - 24GB GPU：适合小型模型
   - 40GB GPU：适合中型模型
   - 80GB GPU：适合大型模型

3. **性能注意事项**：Tensor parallelism 会产生 GPU 到 GPU 的通信开销。
   - Tensor parallelism 大小过小：内存不足问题
   - Tensor parallelism 大小过大：因通信开销导致性能下降

**Tensor Parallelism 与其他并行技术的对比：**
1. **Data Parallelism**：同一模型的多个副本处理不同的数据批次。主要用于训练。
2. **Pipeline Parallelism**：将模型层按顺序分布到多个 GPU 上。
3. **Tensor Parallelism**：将单个层的计算分布到多个 GPU 上。

**Tensor Parallelism 的优势：**
1. **内存效率**：通过在多个 GPU 之间分布大型模型来降低内存要求
2. **降低单个请求延迟**：通过并行计算提高推理速度
3. **提高资源利用率**：更高效地利用 GPU 资源

**Tensor Parallelism 的缺点：**
1. **通信开销**：GPU 之间数据传输产生的开销
2. **实现复杂度**：复杂的模型拆分和同步逻辑
3. **硬件要求**：需要高速 GPU 互连（NVLink、NVSwitch 等）

**其他选项的问题：**
- A. 并行处理多个用户请求：这是 batch processing 或请求并行的用途。
- C. 加速数据预处理：Tensor parallelism 专注于模型推理，而不是数据预处理。
- D. 优化网络通信：Tensor parallelism 不会优化网络通信；相反，它会产生额外通信。
</details>
### 5. 在 Kubernetes 中确保 vLLM 服务高可用性的最有效方法是什么？

A. 在单个 Pod 中部署多个容器
B. 使用具有多个副本以及适当资源请求/限制的 Deployment
C. 使用 DaemonSet 在所有节点上部署
D. 使用 CronJob 定期重启

<details>
<summary>显示答案</summary>

**答案：B. 使用具有多个副本以及适当资源请求/限制的 Deployment**

**说明：**
在 Kubernetes 中确保 vLLM 服务高可用性的最有效方法是使用具有多个副本和适当资源请求/限制的 Deployment。此方法可在不中断服务的情况下处理流量，在节点故障时提供自动恢复，并可根据负载进行扩缩容。

**高可用 vLLM 部署配置示例：**
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

**Service 配置示例：**
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

**Horizontal Pod Autoscaling 配置示例：**
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

**高可用性的其他配置：**

1. **Pod Disruption Budget（PDB）设置：**
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

2. **节点亲和性和容忍度：**
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

3. **拓扑分布约束：**
```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector:
    matchLabels:
      app: vllm
```

**高可用性配置的主要优势：**
1. **容错能力**：即使节点或 Pod 故障也可继续提供服务
2. **负载均衡**：在多个实例之间分配流量
3. **零停机更新**：通过滚动更新实现不中断部署
4. **自动扩缩容**：根据负载自动扩缩容
5. **自动恢复**：自动重启失败的 Pod

**负载均衡策略：**
1. **内部服务负载均衡**：通过 Kubernetes Service 进行基本负载均衡
2. **外部负载均衡**：通过 Ingress 或云负载均衡器分配外部流量
3. **会话亲和性**：在需要时将同一客户端请求路由到同一 Pod

**监控和告警：**
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
- A. 在单个 Pod 中部署多个容器：节点故障时整个服务可能中断，且不能提供真正的高可用性。
- C. 使用 DaemonSet 在所有节点上部署：并非所有节点都保证拥有 GPU，且可能导致资源浪费。
- D. 使用 CronJob 定期重启：这会导致服务中断，并非高可用性解决方案。
</details>

### 6. vLLM 中“Continuous Batching”的主要优势是什么？

A. 提高模型准确率
B. 提高吞吐量和 GPU 利用率
C. 减小模型大小
D. 节省网络带宽

<details>
<summary>显示答案</summary>

**答案：B. 提高吞吐量和 GPU 利用率**

**说明：**
vLLM 中“Continuous Batching”的主要优势是提高吞吐量和 GPU 利用率。Continuous batching 将具有不同长度和开始时间的请求动态分组为批次进行处理，从而更高效地使用 GPU 资源，并显著提高整体系统吞吐量。

**Traditional batching 与 Continuous batching：**
1. **Traditional batching**：
   - 等待请求组成固定大小的批次
   - 所有请求同时开始和结束
   - 需要填充以匹配批次中最长的序列
   - 新请求必须等待当前批次完成

2. **Continuous batching**：
   - 请求到达时动态处理
   - 同时处理具有不同开始时间和长度的请求
   - 无需不必要的填充即可高效使用内存
   - 已完成请求的资源会立即分配给新请求

**Continuous Batching 的工作原理：**
1. **动态请求调度**：请求到达时立即开始处理
2. **逐 token 处理**：每个请求逐 token 处理，并在每一步生成新 token
3. **资源重新分配**：已完成请求的资源会立即分配给新请求
4. **KV 缓存管理**：通过 PagedAttention 高效管理 KV 缓存

**Continuous Batching 的优势：**
1. **高吞吐量**：通过更高效地利用 GPU 资源，提高每秒处理的请求数量
2. **低延迟**：请求无需等待批次形成
3. **提高资源利用率**：减少 GPU 计算和内存资源的空闲时间
4. **处理不同请求长度**：高效处理不同长度的请求

**vLLM 配置中的 Continuous batching 设置：**
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
   - `max-num-batched-tokens`：可一次处理的最大 token 数
   - `max-num-seqs`：可同时处理的最大序列数

2. **GPU 内存利用率调整**：
   - `gpu-memory-utilization`：设置 GPU 内存使用比例（0.0-1.0）

3. **KV 缓存管理**：
   - `max-model-len`：设置最大上下文长度
   - `block-size`：设置 PagedAttention 块大小

**性能基准示例：**
| 批处理方法 | 吞吐量（req/sec） | 平均延迟（ms） | GPU 利用率（%） |
|-----------------|----------------------|----------------------|---------------------|
| Static batching | 10 | 500 | 60% |
| Continuous batching | 25 | 300 | 90% |

**Continuous Batching 的局限性：**
1. **内存管理复杂度**：动态内存分配和释放会增加复杂度
2. **调度开销**：动态请求调度会产生额外开销
3. **优化难度**：难以为各种工作负载设置最佳参数

**其他选项的问题：**
- A. 提高模型准确率：Continuous batching 不影响模型准确率。
- C. 减小模型大小：Continuous batching 不会改变模型大小。
- D. 节省网络带宽：Continuous batching 不会直接影响网络带宽使用。
</details>
### 7. 在 Kubernetes 中监控 vLLM 服务时最重要的指标是什么？

A. Pod 重启次数
B. 推理延迟、吞吐量、GPU 内存使用量
C. 网络丢包率
D. 磁盘 I/O 性能

<details>
<summary>显示答案</summary>

**答案：B. 推理延迟、吞吐量、GPU 内存使用量**

**说明：**
在 Kubernetes 中监控 vLLM 服务时，最重要的指标是推理延迟、吞吐量和 GPU 内存使用量。这些指标直接反映 vLLM 服务性能、效率和资源利用率，并直接影响服务质量（QoS）和用户体验。

**主要监控指标：**

1. **推理延迟**：
   - **定义**：从接收请求到返回响应的时间
   - **重要性**：直接影响用户体验和服务响应能力
   - **测量单位**：毫秒（ms）或秒（s）
   - **详细指标**：
     - 首个 Token 时间
     - 每个 Token 时间
     - 总生成时间

2. **吞吐量**：
   - **定义**：单位时间内可处理的请求或 token 数量
   - **重要性**：系统容量和可扩展性评估
   - **测量单位**：每秒请求数（RPS）或每秒 Token 数（TPS）
   - **详细指标**：
     - 每秒请求数
     - 每秒 Token 数
     - Batch Size

3. **GPU 内存使用量**：
   - **定义**：vLLM 服务使用的 GPU 内存量
   - **重要性**：防止内存不足并优化资源
   - **测量单位**：千兆字节（GB）或兆字节（MB）
   - **详细指标**：
     - 模型权重内存使用量
     - KV 缓存内存使用量
     - 激活内存使用量
     - GPU 总内存使用量

**Prometheus 指标配置示例：**
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

**Prometheus ServiceMonitor 配置：**
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

**主要 vLLM 指标和 PromQL 查询：**

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

3. **GPU 内存使用量**：
   ```
   # GPU memory usage
   vllm_gpu_memory_used_bytes

   # KV cache memory usage
   vllm_kv_cache_memory_bytes
   ```

**Grafana dashboard 配置示例：**
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

**告警规则配置示例：**
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

**其他监控指标：**
1. **GPU 利用率**：GPU 计算单元的利用率
2. **CPU 使用量**：预处理和后处理使用的 CPU 资源
3. **系统内存使用量**：主机内存使用量
4. **错误率**：失败请求的比例
5. **队列长度**：等待处理的请求数量
6. **批处理效率**：平均 batch size 和利用率

**监控工具集成：**
1. **Prometheus + Grafana**：指标收集和可视化
2. **NVIDIA DCGM Exporter**：GPU 指标收集
3. **Jaeger/Zipkin**：分布式追踪
4. **ELK Stack**：日志收集和分析

**其他选项的问题：**
- A. Pod 重启次数：这是系统稳定性指标，但无法直接反映 vLLM 服务性能。
- C. 网络丢包率：对诊断网络问题有用，但不是 vLLM 服务的核心性能指标。
- D. 磁盘 I/O 性能：模型加载期间可能很重要，但对运行中的 vLLM 服务性能不那么重要。
</details>

### 8. Kubernetes 中 vLLM 服务的最佳网络配置是什么？

A. 使用默认 CNI plugin
B. 用于 Tensor parallelism 的高性能网络接口和 RDMA 支持
C. 使用 network policies 限制所有流量
D. 实现 service mesh

<details>
<summary>显示答案</summary>

**答案：B. 用于 Tensor parallelism 的高性能网络接口和 RDMA 支持**

**说明：**
Kubernetes 中 vLLM 服务的最佳网络配置是用于 Tensor parallelism 的高性能网络接口和 RDMA（Remote Direct Memory Access）支持。当在多个 GPU 之间分布式运行 Large Language Model 时，GPU 到 GPU 的通信性能会显著影响整体系统性能。高性能网络接口和 RDMA 支持可最大限度地减少 GPU 到 GPU 数据传输延迟并最大化吞吐量，从而提高分布式推理性能。

**高性能网络的重要性：**
1. **Tensor parallelism**：在多个 GPU 之间分配模型层时，需要频繁的 GPU 到 GPU 通信
2. **模型分片**：在多个节点之间分配大型模型时，节点之间的网络性能很重要
3. **延迟敏感性**：GPU 到 GPU 的通信延迟直接影响整体推理延迟
4. **带宽要求**：大型 tensor 数据传输需要高带宽

**最佳网络配置组件：**

1. **高性能网络接口**：
   - **NVIDIA ConnectX-6/7**：支持高达 200Gbps 带宽
   - **InfiniBand**：超低延迟、高带宽网络
   - **RDMA over Converged Ethernet（RoCE）**：以太网网络上的 RDMA 能力

2. **RDMA（Remote Direct Memory Access）支持**：
   - 在无需 CPU 参与的情况下，直接在 GPU 内存之间传输数据
   - 最大限度降低延迟并最大化吞吐量
   - GPU Direct RDMA：GPU 内存之间的直接数据传输

3. **NVLink/NVSwitch**：
   - 同一节点内 GPU 之间的高速连接
   - 高达 600GB/s 带宽（NVLink 4.0）
   - 对多 GPU 系统很重要

**Kubernetes 中的高性能网络配置：**

1. **SR-IOV（Single Root I/O Virtualization）Network Device Plugin：**
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

2. **NetworkAttachmentDefinition 配置：**
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

3. **将高性能网络配置应用于 vLLM 部署：**
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

**NCCL（NVIDIA Collective Communications Library）配置：**
NCCL 是一个优化 GPU 到 GPU 通信的库，可通过以下环境变量配置：

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

**多节点分布式配置：**
当在多个节点之间分配 vLLM 时，节点之间的网络性能变得更加重要。需要以下配置：

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
- A. 使用默认 CNI plugin：默认 CNI plugin 通常不支持 RDMA 等高性能网络功能，也无法提供 Tensor parallelism 所需的性能。
- C. 使用 network policies 限制所有流量：这可以增强安全性，但不会提高性能，且可能增加额外开销。
- D. 实现 service mesh：service mesh 对微服务架构很有用，但会为 vLLM 等高性能计算工作负载增加不必要的开销。
</details>
### 9. 在 Kubernetes 中提高 vLLM 服务可扩展性的最有效方法是什么？

A. 分配更多 CPU 核心
B. 将水平扩展（多个副本）与负载均衡以及垂直扩展（更大的 GPU）相结合
C. 分配更多内存
D. 配置更大的持久卷

<details>
<summary>显示答案</summary>

**答案：B. 将水平扩展（多个副本）与负载均衡以及垂直扩展（更大的 GPU）相结合**

**说明：**
在 Kubernetes 中提高 vLLM 服务可扩展性的最有效方法，是将水平扩展（多个副本）与负载均衡以及垂直扩展（更大的 GPU）相结合。此方法可灵活响应各种工作负载要求和资源限制，并平衡成本效益与性能。

**水平扩展的优势：**
1. **提高吞吐量**：更多副本可处理更多并发请求
2. **高可用性**：即使部分实例失败，服务仍会继续运行
3. **地理分布**：跨多个区域部署以降低延迟
4. **成本效益**：可按需调整实例数量

**垂直扩展的优势：**
1. **支持更大模型**：更大的 GPU 内存可以加载更大的模型
2. **降低单个请求延迟**：使用更强大的 GPU 提高推理速度
3. **处理更长上下文**：更多内存可处理更长的上下文
4. **降低通信开销**：使用单个 GPU 或单个节点内的多个 GPU 时降低通信开销

**水平扩展配置示例：**
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

**水平自动扩缩容配置：**
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

**垂直扩展配置示例：**
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

**负载均衡配置：**
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

**模型分片和路由：**
可组合多个 Deployment 并路由请求，以支持不同模型大小和类型：

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

**API gateway 配置：**
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
   - 根据模型大小和复杂度将请求路由到适当实例
   - 通过会话亲和性优化 KV 缓存复用

2. **资源分配优化**：
   - 选择适合工作负载特征的 GPU 类型
   - 设置适当的 Tensor parallelism 大小

3. **缓存策略**：
   - 缓存常用 prompt 和响应
   - 模型权重缓存

4. **混合云扩展**：
   - 结合本地部署和云资源
   - 使用云扩展来应对突发流量

**可扩展性测试和基准测试：**
```bash
# Run load test
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**其他选项的问题：**
- A. 分配更多 CPU 核心：vLLM 主要受 GPU 限制，仅增加 CPU 核心无法显著提高性能。
- C. 分配更多内存：系统内存很重要，但 GPU 内存才是主要限制。
- D. 配置更大的持久卷：存储容量对模型存储很重要，但不会直接影响推理性能和可扩展性。
</details>

### 10. 在 Kubernetes 中部署 vLLM 时最重要的安全注意事项是什么？

A. Network policy 配置
B. 保护模型权重和 API key，并强化容器安全
C. Pod security policy 配置
D. 启用审计日志

<details>
<summary>显示答案</summary>

**答案：B. 保护模型权重和 API key，并强化容器安全**

**说明：**
在 Kubernetes 中部署 vLLM 时最重要的安全注意事项是保护模型权重和 API key，并强化容器安全。vLLM 服务会处理具有知识产权的模型权重、敏感 API key 和用户数据，因此保护这些资产并加强容器环境安全最为重要。

**主要安全注意事项：**

1. **模型权重保护**：
   - 模型权重是具有知识产权的宝贵资产。
   - 必须防范未经授权的访问、复制和泄露。
   - 需要静态加密和传输加密。

2. **API key 和认证信息保护**：
   - API key、token 和密码等认证信息必须得到安全管理。
   - 应使用 Kubernetes Secrets 或外部 secret 管理系统。
   - 应通过挂载卷而非环境变量提供 secret。

3. **容器安全强化**：
   - 应用最小权限原则
   - 以非 root 用户运行容器
   - 使用只读文件系统
   - 移除不必要的 capabilities 和权限

4. **输入验证和输出过滤**：
   - 防止 prompt injection 攻击
   - 防止敏感信息泄露
   - 过滤有害内容

**模型权重保护配置示例：**
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

**容器安全强化：**
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

**RBAC（Role-Based Access Control）配置：**
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

**审计日志配置：**
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
1. **定期安全扫描**：扫描容器镜像和依赖项中的漏洞
2. **最小权限原则**：仅授予最低限度的所需权限
3. **不可变基础设施**：需要变更时部署新容器
4. **安全监控**：检测异常行为并发送告警
5. **应急响应计划**：为安全事件准备响应流程

**其他选项的问题：**
- A. Network policy 配置：很重要，但优先级低于保护模型权重和 API key 以及强化容器安全。
- C. Pod security policy 配置：是容器安全的一部分，但不包括模型权重和 API key 保护。
- D. 启用审计日志：对安全监控很重要，但优先级低于预防性安全措施。
</details>

### 11. 在本页面基于单个 NVIDIA L4 GPU 测得的 Qwen2.5-7B-Instruct 基准测试中，并发度从 1 增加到 16 时，单个请求延迟发生了什么变化？

A. 它几乎增长了 16 倍，与增加的负载成正比
B. 它几乎保持不变（p50 从 5.65s 增至 7.52s，+33%），而总吞吐量接近线性扩展
C. 它下降了，因为更多请求使 vLLM 可以跳过 prefill 阶段
D. 无法测量，因为并发度达到 16 前 GPU 已耗尽 KV 缓存内存

<details>
<summary>显示答案</summary>

**答案：B. 它几乎保持不变（p50 从 5.65s 增至 7.52s，+33%），而总吞吐量接近线性扩展**

**说明：**
这正是 Continuous batching 的核心经验：vLLM 不会将新请求排在已经运行的请求之后。它会在下一个 scheduler 步骤加入 batch，因此 GPU 会并行处理许多序列而非串行处理。在此次测量运行中，一个完整约 100-128 token 响应的 p50 延迟，仅从并发度 1 时的 5.65s 增至并发度 16 时的 7.52s（+33%）；与此同时，总完成吞吐量从约 17 tokens/s 扩展至 208 tokens/s（客户端测量）。这种扩展是受带宽限制的 decode 的标志：在并发度为 1 时，对每个 token 从 GDDR6 内存流式读取约 15.2 GB 的 bf16 权重，会将单请求 decode 限制在这块 L4 约 300 GB/s 内存带宽下测得的约 17-18 tokens/s；而即使在测得的最繁忙点，计算量也只占 GPU 约 121 TFLOPS bf16 上限的百分之几。Batching 让许多请求几乎可以免费共享同一次权重读取，这正是吞吐量接近线性扩展而延迟几乎不变的原因。

**其他选项错误的原因：**
- A. 这描述的是串行（非批处理）请求处理时会发生的情况，而不是 Continuous batching。
- C. Continuous batching 不会跳过 prefill；每个新请求在 decode 前仍会经过 prefill，只是它会与其他请求的 decode 步骤同时发生。
- D. 并发度为 16 时，GPU KV 缓存使用量峰值仅为这块 24GB L4 的 2.6%——远未耗尽。该基准测试并未将并发度提高到足以找到该限制的程度。
</details>
