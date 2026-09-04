# vLLM Deployment Quiz

This quiz tests your understanding of deploying vLLM (Vector Language Model) in Kubernetes.

## Quiz Questions

### 1. What is the main purpose of vLLM (Vector Language Model)?

A. Image processing acceleration
B. Large Language Model (LLM) inference optimization and acceleration
C. Database query optimization
D. Network traffic management

<details>
<summary>Show Answer</summary>

**Answer: B. Large Language Model (LLM) inference optimization and acceleration**

**Explanation:**
The main purpose of vLLM (Vector Language Model) is to optimize and accelerate Large Language Model (LLM) inference. vLLM uses an innovative attention algorithm called PagedAttention to optimize memory management, enabling LLM inference with high throughput and low latency.

**Key features of vLLM:**
1. **PagedAttention**: Memory-efficient attention mechanism that optimizes GPU memory usage.
2. **Continuous batching**: Dynamically batches requests to improve throughput.
3. **Distributed inference**: Distributes large models across multiple GPUs and nodes.
4. **Various model support**: Supports various open-source LLMs including Llama, GPT-NeoX, Falcon, MPT.
5. **OpenAI-compatible API**: Provides an interface compatible with the OpenAI API.

**How PagedAttention works:**
PagedAttention is a technique inspired by virtual memory management in operating systems, efficiently managing KV (Key-Value) cache. Traditional methods allocate fixed-size memory blocks for each request, but PagedAttention allocates only as much memory as needed and reuses it.

**Performance benefits of vLLM:**
1. **High throughput**: 2-4x higher throughput compared to existing solutions
2. **Memory efficiency**: Can handle up to 8x more concurrent requests
3. **Low latency**: Reduced response time through efficient memory management
4. **Improved resource utilization**: More efficient utilization of GPU resources

**vLLM use cases:**
1. **Conversational AI services**: Chatbots, virtual assistants, etc.
2. **Text generation services**: Content generation, summarization, translation, etc.
3. **Code generation and completion**: Programming support tools
4. **Large-scale text processing**: Document analysis, information extraction, etc.

**Issues with other options:**
- A. Image processing acceleration: vLLM is for text-based language models and is not specialized for image processing.
- C. Database query optimization: vLLM is not related to database query optimization.
- D. Network traffic management: vLLM is not related to network traffic management.
</details>

### 2. What is the most important resource requirement when deploying vLLM in Kubernetes?

A. Large CPU and memory
B. High-performance GPU and sufficient GPU memory
C. High-speed network interface
D. Large persistent storage

<details>
<summary>Show Answer</summary>

**Answer: B. High-performance GPU and sufficient GPU memory**

**Explanation:**
The most important resource requirement when deploying vLLM in Kubernetes is high-performance GPU and sufficient GPU memory. Large Language Models (LLMs) have billions or hundreds of billions of parameters, and powerful GPU computing capability and sufficient GPU memory to store model parameters are essential for running these models efficiently.

**GPU requirements:**
1. **GPU type**: High-performance GPUs like NVIDIA A100, H100, V100, RTX A6000
2. **GPU memory**: Varies by model size, but generally:
   - 7B parameter model: Minimum 16GB GPU memory
   - 13B parameter model: Minimum 24GB GPU memory
   - 70B parameter model: Minimum 80GB GPU memory or distributed across multiple GPUs
3. **Number of GPUs**: Depends on throughput requirements and model size, but large models need to be distributed across multiple GPUs.

**GPU resource request example for vLLM deployment:**
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

**Distributed deployment example for large models:**
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

**GPU memory requirement calculation:**
LLM GPU memory requirements are determined by the following factors:
1. **Model parameters**: Each parameter typically takes 2 bytes (FP16) or 4 bytes (FP32).
2. **KV cache**: Key-value cache for each token requires additional memory.
3. **Batch size**: Memory requirements increase as the number of concurrent requests increases.
4. **Context length**: Longer context lengths require more KV cache memory.

**Approximate memory requirement formula:**
```
Required GPU memory = Model size + (batch size x sequence length x hidden size x layers x 4 bytes)
```

**Other resource requirements:**
1. **CPU**: Sufficient CPU cores for preprocessing and postprocessing
2. **System memory**: Sufficient RAM for model loading and processing
3. **Storage**: Sufficient storage for model weight files
4. **Network**: High-speed network connection for distributed inference

**Issues with other options:**
- A. Large CPU and memory: CPU is not efficient for LLM inference, and system memory alone cannot replace GPU memory.
- C. High-speed network interface: Important for distributed inference but lower priority than GPU and GPU memory.
- D. Large persistent storage: Needed for model weight storage but doesn't directly impact inference performance.
</details>
### 3. What is the optimal storage solution for vLLM in Kubernetes?

A. emptyDir volume
B. hostPath volume
C. High-performance distributed file system (e.g., FSx for Lustre)
D. Regular network file system (NFS)

<details>
<summary>Show Answer</summary>

**Answer: C. High-performance distributed file system (e.g., FSx for Lustre)**

**Explanation:**
The optimal storage solution for vLLM in Kubernetes is a high-performance distributed file system (e.g., FSx for Lustre). vLLM needs to quickly load model weight files to process large language models, and in distributed inference environments, multiple nodes need to simultaneously access the same model files. High-performance distributed file systems meet these requirements by providing high throughput, low latency, and parallel access capabilities.

**Advantages of high-performance distributed file systems:**
1. **High throughput**: Can quickly load large model files.
2. **Parallel access**: Multiple nodes can simultaneously access the same files.
3. **Scalability**: Storage capacity and performance can be scaled as needed.
4. **Data consistency**: Provides consistent data view across multiple nodes.
5. **Durability**: Reduces risk of data loss through data replication and backup features.

**AWS FSx for Lustre configuration example:**
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

**Google Cloud Filestore configuration example:**
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

**Azure NetApp Files configuration example:**
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

**Comparison with other storage options:**

| Storage Option | Throughput | Latency | Multi-node Access | Scalability | Persistence |
|----------------|------------|---------|-------------------|-------------|-------------|
| emptyDir | High | Very low | Not possible | Limited | Temporary |
| hostPath | High | Very low | Not possible | Limited | Node-dependent |
| NFS | Medium | Medium | Possible | Medium | Persistent |
| FSx for Lustre | Very high | Low | Possible | High | Persistent |
| Google Filestore | High | Low | Possible | High | Persistent |
| Azure NetApp Files | High | Low | Possible | High | Persistent |

**Model loading performance optimization strategies:**
1. **Memory mapping**: Reduce loading time by directly mapping large model files to memory
2. **Model sharding**: Split model into multiple shards and load in parallel
3. **Caching**: Cache frequently used models in memory to prevent reloading
4. **Pre-loading**: Pre-load models at service startup to reduce first request latency

**Issues with other options:**
- A. emptyDir volume: Temporary storage where data is lost when pod restarts. Not suitable for storing large model files.
- B. hostPath volume: Relies on node local storage, making data sharing difficult in multi-node environments.
- D. Regular network file system (NFS): Performance is lower than high-performance distributed file systems in terms of throughput and latency.
</details>

### 4. What is the main purpose of Tensor Parallelism in vLLM?

A. Process multiple user requests in parallel
B. Distribute large models across multiple GPUs to reduce memory requirements
C. Accelerate data preprocessing
D. Optimize network communication

<details>
<summary>Show Answer</summary>

**Answer: B. Distribute large models across multiple GPUs to reduce memory requirements**

**Explanation:**
The main purpose of Tensor Parallelism in vLLM is to distribute large models across multiple GPUs to reduce memory requirements. Large Language Models (LLMs) often have billions or hundreds of billions of parameters that exceed the memory capacity of a single GPU. Tensor parallelism solves this problem by splitting model layers across multiple GPUs so each GPU stores and processes only a portion of the model.

**How Tensor Parallelism works:**
1. **Model splitting**: Splits each layer of the model (especially attention and MLP layers) across multiple GPUs.
2. **Parallel computation**: Each GPU performs computations on its assigned portion of the model.
3. **Synchronization**: Synchronizes intermediate results between GPUs when necessary.
4. **Result aggregation**: Aggregates results from each GPU to generate final output.

**Tensor parallelism configuration example in vLLM:**
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

**Tensor parallelism size selection guide:**
1. **Model size**: Required tensor parallelism size depends on the number of model parameters.
   - 7B parameter model: 1-2 GPUs
   - 13B parameter model: 2-4 GPUs
   - 70B parameter model: 8-16 GPUs
   - 175B parameter model: 16+ GPUs

2. **GPU memory**: Tensor parallelism size should be adjusted based on available GPU memory.
   - 24GB GPU: Suitable for small models
   - 40GB GPU: Suitable for medium-sized models
   - 80GB GPU: Suitable for large models

3. **Performance considerations**: Tensor parallelism creates GPU-to-GPU communication overhead.
   - Too small tensor parallelism size: Memory shortage issues
   - Too large tensor parallelism size: Performance degradation due to communication overhead

**Tensor Parallelism vs other parallelization techniques:**
1. **Data Parallelism**: Multiple copies of the same model process different data batches. Primarily used for training.
2. **Pipeline Parallelism**: Distributes model layers sequentially across multiple GPUs.
3. **Tensor Parallelism**: Distributes individual layer computations across multiple GPUs.

**Advantages of Tensor Parallelism:**
1. **Memory efficiency**: Reduces memory requirements by distributing large models across multiple GPUs
2. **Reduced single request latency**: Improves inference speed through parallel computation
3. **Improved resource utilization**: More efficient utilization of GPU resources

**Disadvantages of Tensor Parallelism:**
1. **Communication overhead**: Overhead from data transfer between GPUs
2. **Implementation complexity**: Complex model splitting and synchronization logic
3. **Hardware requirements**: Requires high-speed GPU interconnects (NVLink, NVSwitch, etc.)

**Issues with other options:**
- A. Process multiple user requests in parallel: This is the purpose of batch processing or request parallelism.
- C. Accelerate data preprocessing: Tensor parallelism focuses on model inference, not data preprocessing.
- D. Optimize network communication: Tensor parallelism doesn't optimize network communication; it rather creates additional communication.
</details>
### 5. What is the most effective method to ensure high availability of vLLM services in Kubernetes?

A. Deploy multiple containers in a single pod
B. Use Deployment with multiple replicas and appropriate resource requests/limits
C. Deploy on all nodes with DaemonSet
D. Restart periodically with CronJob

<details>
<summary>Show Answer</summary>

**Answer: B. Use Deployment with multiple replicas and appropriate resource requests/limits**

**Explanation:**
The most effective method to ensure high availability of vLLM services in Kubernetes is to use a Deployment with multiple replicas and appropriate resource requests/limits. This approach handles traffic without service interruption, provides automatic recovery in case of node failures, and enables scaling based on load.

**High availability vLLM deployment configuration example:**
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

**Service configuration example:**
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

**Horizontal Pod Autoscaling configuration example:**
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

**Additional configurations for high availability:**

1. **Pod Disruption Budget (PDB) setting**:
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

2. **Node affinity and tolerations**:
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

3. **Topology spread constraints**:
```yaml
topologySpreadConstraints:
- maxSkew: 1
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
  labelSelector:
    matchLabels:
      app: vllm
```

**Key benefits of high availability configuration:**
1. **Fault tolerance**: Continues providing service even with node or pod failures
2. **Load balancing**: Distributes traffic across multiple instances
3. **Zero downtime updates**: No-interruption deployment through rolling updates
4. **Auto-scaling**: Automatic scaling based on load
5. **Auto-recovery**: Automatic restart of failed pods

**Load balancing strategies:**
1. **Internal service load balancing**: Basic load balancing through Kubernetes Service
2. **External load balancing**: External traffic distribution through Ingress or cloud load balancer
3. **Session affinity**: Route same client requests to same pod when needed

**Monitoring and alerting:**
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

**Issues with other options:**
- A. Deploy multiple containers in a single pod: The entire service can be interrupted in case of node failure, and doesn't provide true high availability.
- C. Deploy on all nodes with DaemonSet: Not all nodes are guaranteed to have GPUs, and can cause resource waste.
- D. Restart periodically with CronJob: This causes service interruption and is not a high availability solution.
</details>

### 6. What is the main benefit of "Continuous Batching" in vLLM?

A. Improved model accuracy
B. Increased throughput and improved GPU utilization
C. Reduced model size
D. Saved network bandwidth

<details>
<summary>Show Answer</summary>

**Answer: B. Increased throughput and improved GPU utilization**

**Explanation:**
The main benefit of "Continuous Batching" in vLLM is increased throughput and improved GPU utilization. Continuous batching dynamically groups requests with various lengths and start times into batches for processing, making more efficient use of GPU resources and significantly improving overall system throughput.

**Traditional batching vs Continuous batching:**
1. **Traditional batching**:
   - Waits for requests to form fixed-size batches
   - All requests start and end simultaneously
   - Requires padding to match longest sequence in batch
   - New requests must wait until current batch completes

2. **Continuous batching**:
   - Processes requests dynamically as they arrive
   - Simultaneously processes requests with different start times and lengths
   - Efficient memory usage without unnecessary padding
   - Resources from completed requests are immediately allocated to new requests

**How Continuous Batching works:**
1. **Dynamic request scheduling**: Starts processing immediately when requests arrive
2. **Token-by-token processing**: Each request is processed token by token, generating new tokens at each step
3. **Resource reallocation**: Resources from completed requests are immediately allocated to new requests
4. **KV cache management**: Efficient KV cache management through PagedAttention

**Benefits of Continuous Batching:**
1. **High throughput**: Increased number of requests processed per second by utilizing GPU resources more efficiently
2. **Low latency**: Requests don't need to wait for batches to form
3. **Improved resource utilization**: Reduced idle time for GPU computation and memory resources
4. **Various request length handling**: Efficiently handles requests of different lengths

**Continuous batching settings in vLLM configuration:**
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

**Continuous batching performance optimization:**
1. **Optimal batch size settings**:
   - `max-num-batched-tokens`: Maximum tokens that can be processed at once
   - `max-num-seqs`: Maximum sequences that can be processed simultaneously

2. **GPU memory utilization adjustment**:
   - `gpu-memory-utilization`: Set GPU memory usage ratio (0.0-1.0)

3. **KV cache management**:
   - `max-model-len`: Set maximum context length
   - `block-size`: Set PagedAttention block size

**Performance benchmark example:**
| Batching Method | Throughput (req/sec) | Average Latency (ms) | GPU Utilization (%) |
|-----------------|----------------------|----------------------|---------------------|
| Static batching | 10 | 500 | 60% |
| Continuous batching | 25 | 300 | 90% |

**Limitations of Continuous Batching:**
1. **Memory management complexity**: Increased complexity due to dynamic memory allocation and deallocation
2. **Scheduling overhead**: Additional overhead from dynamic request scheduling
3. **Optimization difficulty**: Difficulty in setting optimal parameters for various workloads

**Issues with other options:**
- A. Improved model accuracy: Continuous batching doesn't affect model accuracy.
- C. Reduced model size: Continuous batching doesn't change model size.
- D. Saved network bandwidth: Continuous batching doesn't directly affect network bandwidth usage.
</details>
### 7. What is the most important metric for monitoring vLLM services in Kubernetes?

A. Pod restart count
B. Inference latency, throughput, GPU memory usage
C. Network packet loss rate
D. Disk I/O performance

<details>
<summary>Show Answer</summary>

**Answer: B. Inference latency, throughput, GPU memory usage**

**Explanation:**
The most important metrics for monitoring vLLM services in Kubernetes are inference latency, throughput, and GPU memory usage. These metrics directly reflect vLLM service performance, efficiency, and resource utilization, and directly impact service quality (QoS) and user experience.

**Key monitoring metrics:**

1. **Inference Latency**:
   - **Definition**: Time from receiving request to returning response
   - **Importance**: Directly impacts user experience and service responsiveness
   - **Measurement unit**: Milliseconds (ms) or seconds (s)
   - **Detailed metrics**:
     - Time to First Token
     - Time per Token
     - Total Generation Time

2. **Throughput**:
   - **Definition**: Number of requests or tokens that can be processed per unit time
   - **Importance**: System capacity and scalability evaluation
   - **Measurement unit**: Requests per Second (RPS) or Tokens per Second (TPS)
   - **Detailed metrics**:
     - Requests per Second
     - Tokens per Second
     - Batch Size

3. **GPU memory usage**:
   - **Definition**: Amount of GPU memory used by vLLM service
   - **Importance**: Memory shortage prevention and resource optimization
   - **Measurement unit**: Gigabytes (GB) or Megabytes (MB)
   - **Detailed metrics**:
     - Model weight memory usage
     - KV cache memory usage
     - Activation memory usage
     - Total GPU memory usage

**Prometheus metrics configuration example:**
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

**Prometheus ServiceMonitor configuration:**
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

**Key vLLM metrics and PromQL queries:**

1. **Inference latency**:
   ```
   # 95th percentile inference latency
   histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))

   # Average time per token generation
   avg(rate(vllm_token_generation_time_seconds_sum[5m]) / rate(vllm_token_generation_time_seconds_count[5m]))
   ```

2. **Throughput**:
   ```
   # Requests per second
   sum(rate(vllm_requests_total[5m]))

   # Tokens per second
   sum(rate(vllm_generated_tokens_total[5m]))
   ```

3. **GPU memory usage**:
   ```
   # GPU memory usage
   vllm_gpu_memory_used_bytes

   # KV cache memory usage
   vllm_kv_cache_memory_bytes
   ```

**Grafana dashboard configuration example:**
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

**Alert rule configuration example:**
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

**Additional monitoring metrics:**
1. **GPU utilization**: Utilization ratio of GPU compute units
2. **CPU usage**: CPU resources used for preprocessing and postprocessing
3. **System memory usage**: Host memory usage
4. **Error rate**: Ratio of failed requests
5. **Queue length**: Number of requests waiting to be processed
6. **Batch efficiency**: Average batch size and utilization

**Monitoring tool integration:**
1. **Prometheus + Grafana**: Metric collection and visualization
2. **NVIDIA DCGM Exporter**: GPU metric collection
3. **Jaeger/Zipkin**: Distributed tracing
4. **ELK Stack**: Log collection and analysis

**Issues with other options:**
- A. Pod restart count: An indicator of system stability, but doesn't directly reflect vLLM service performance.
- C. Network packet loss rate: Useful for diagnosing network issues, but not a core performance metric for vLLM service.
- D. Disk I/O performance: May be important during model loading, but less important for running vLLM service performance.
</details>

### 8. What is the optimal network configuration for vLLM services in Kubernetes?

A. Use default CNI plugin
B. High-performance network interface and RDMA support for tensor parallelism
C. Restrict all traffic with network policies
D. Implement service mesh

<details>
<summary>Show Answer</summary>

**Answer: B. High-performance network interface and RDMA support for tensor parallelism**

**Explanation:**
The optimal network configuration for vLLM services in Kubernetes is high-performance network interface and RDMA (Remote Direct Memory Access) support for tensor parallelism. When running large language models distributed across multiple GPUs, GPU-to-GPU communication performance significantly impacts overall system performance. High-performance network interfaces and RDMA support minimize GPU-to-GPU data transfer latency and maximize throughput to improve distributed inference performance.

**Importance of high-performance networking:**
1. **Tensor parallelism**: Frequent GPU-to-GPU communication required when distributing model layers across multiple GPUs
2. **Model sharding**: Network performance between nodes important when distributing large models across multiple nodes
3. **Latency sensitivity**: GPU-to-GPU communication latency directly impacts overall inference latency
4. **Bandwidth requirements**: High bandwidth needed for large tensor data transfers

**Optimal network configuration components:**

1. **High-performance network interface**:
   - **NVIDIA ConnectX-6/7**: Supports up to 200Gbps bandwidth
   - **InfiniBand**: Ultra-low latency high-bandwidth networking
   - **RDMA over Converged Ethernet (RoCE)**: RDMA capability on Ethernet networks

2. **RDMA (Remote Direct Memory Access) support**:
   - Direct data transfer between GPU memory without CPU involvement
   - Minimized latency and maximized throughput
   - GPU Direct RDMA: Direct data transfer between GPU memory

3. **NVLink/NVSwitch**:
   - High-speed connection between GPUs within same node
   - Up to 600GB/s bandwidth (NVLink 4.0)
   - Important for multi-GPU systems

**High-performance networking configuration in Kubernetes:**

1. **SR-IOV (Single Root I/O Virtualization) Network Device Plugin**:
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

2. **NetworkAttachmentDefinition configuration**:
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

3. **Apply high-performance network configuration to vLLM deployment**:
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

**NCCL (NVIDIA Collective Communications Library) configuration:**
NCCL is a library that optimizes GPU-to-GPU communication, configurable through the following environment variables:

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

**Multi-node distributed configuration:**
When distributing vLLM across multiple nodes, network performance between nodes becomes even more important. The following configuration is needed:

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

**Network performance testing:**
```bash
# Run NCCL test
kubectl run nccl-test --image=nvidia/cuda:11.8.0-devel-ubuntu22.04 --overrides='{"spec": {"containers": [{"name": "nccl-test", "image": "nvidia/cuda:11.8.0-devel-ubuntu22.04", "command": ["/bin/bash", "-c"], "args": ["apt-get update && apt-get install -y git && git clone https://github.com/NVIDIA/nccl-tests.git && cd nccl-tests && make && ./build/all_reduce_perf -b 8 -e 128M -f 2 -g 8"], "resources": {"limits": {"nvidia.com/gpu": 8}}}]}}' --restart=Never

# Network bandwidth test
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201
kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**Issues with other options:**
- A. Use default CNI plugin: Default CNI plugins typically don't support high-performance networking features like RDMA and don't provide the performance needed for tensor parallelism.
- C. Restrict all traffic with network policies: This can enhance security but doesn't improve performance and may add additional overhead.
- D. Implement service mesh: Service mesh is useful for microservices architecture but adds unnecessary overhead for high-performance computing workloads like vLLM.
</details>
### 9. What is the most effective method to improve scalability of vLLM services in Kubernetes?

A. Allocate more CPU cores
B. Combination of horizontal scaling (multiple replicas) with load balancing and vertical scaling (larger GPUs)
C. Allocate more memory
D. Provision larger persistent volumes

<details>
<summary>Show Answer</summary>

**Answer: B. Combination of horizontal scaling (multiple replicas) with load balancing and vertical scaling (larger GPUs)**

**Explanation:**
The most effective method to improve scalability of vLLM services in Kubernetes is a combination of horizontal scaling (multiple replicas) with load balancing and vertical scaling (larger GPUs). This approach can flexibly respond to various workload requirements and resource constraints, and balance cost efficiency and performance.

**Benefits of Horizontal Scaling:**
1. **Increased throughput**: More concurrent requests can be handled with more replicas
2. **High availability**: Service continues even if some instances fail
3. **Geographic distribution**: Deploy across multiple regions to reduce latency
4. **Cost efficiency**: Can adjust number of instances as needed

**Benefits of Vertical Scaling:**
1. **Larger model support**: Larger GPU memory can load larger models
2. **Reduced single request latency**: Improved inference speed with more powerful GPUs
3. **Longer context handling**: More memory can handle longer contexts
4. **Reduced communication overhead**: Reduced communication overhead when using single GPU or multiple GPUs within single node

**Horizontal scaling configuration example:**
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

**Horizontal auto-scaling configuration:**
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

**Vertical scaling configuration example:**
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

**Load balancing configuration:**
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

**Model sharding and routing:**
Multiple deployments can be combined and routed to support various model sizes and types:

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

**API gateway configuration:**
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

**Scalability optimization strategies:**
1. **Request routing optimization**:
   - Route requests to appropriate instances based on model size and complexity
   - Optimize KV cache reuse through session affinity

2. **Resource allocation optimization**:
   - Select GPU type appropriate for workload characteristics
   - Set appropriate tensor parallelism size

3. **Caching strategy**:
   - Cache frequently used prompts and responses
   - Model weight caching

4. **Hybrid cloud scaling**:
   - Combine on-premises and cloud resources
   - Cloud scaling for burst traffic

**Scalability testing and benchmarking:**
```bash
# Run load test
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**Issues with other options:**
- A. Allocate more CPU cores: vLLM is primarily GPU-bound, and performance doesn't significantly improve by just adding CPU cores.
- C. Allocate more memory: System memory is important, but GPU memory is the main constraint.
- D. Provision larger persistent volumes: Storage capacity is important for model storage but doesn't directly impact inference performance and scalability.
</details>

### 10. What is the most important security consideration when deploying vLLM in Kubernetes?

A. Network policy configuration
B. Protecting model weights and API keys, container security hardening
C. Pod security policy configuration
D. Enabling audit logging

<details>
<summary>Show Answer</summary>

**Answer: B. Protecting model weights and API keys, container security hardening**

**Explanation:**
The most important security consideration when deploying vLLM in Kubernetes is protecting model weights and API keys, and container security hardening. vLLM services handle intellectual property model weights, sensitive API keys, and user data, so protecting these assets and strengthening container environment security is most important.

**Key security considerations:**

1. **Model weight protection**:
   - Model weights are valuable assets with intellectual property rights.
   - Must protect against unauthorized access, copying, and leakage.
   - Encrypted storage and encryption in transit required.

2. **API key and authentication information protection**:
   - Authentication information like API keys, tokens, and passwords must be managed securely.
   - Should use Kubernetes Secrets or external secret management systems.
   - Should provide secrets through mounted volumes instead of environment variables.

3. **Container security hardening**:
   - Apply principle of least privilege
   - Run containers as non-root user
   - Use read-only file system
   - Remove unnecessary capabilities and privileges

4. **Input validation and output filtering**:
   - Prevent prompt injection attacks
   - Prevent sensitive information leakage
   - Filter harmful content

**Model weight protection configuration example:**
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

**API key and authentication information protection:**
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

**Container security hardening:**
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

**Network policy:**
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

**Input validation and output filtering:**
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

**RBAC (Role-Based Access Control) configuration:**
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

**Audit logging configuration:**
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

**Additional security best practices:**
1. **Regular security scanning**: Scan container images and dependencies for vulnerabilities
2. **Principle of least privilege**: Grant only the minimum required privileges
3. **Immutable infrastructure**: Deploy new containers when changes are needed
4. **Security monitoring**: Detect abnormal behavior and send alerts
5. **Emergency response plan**: Prepare response procedures for security incidents

**Issues with other options:**
- A. Network policy configuration: Important, but lower priority than protecting model weights and API keys, and container security hardening.
- C. Pod security policy configuration: Part of container security, but doesn't include model weight and API key protection.
- D. Enabling audit logging: Important for security monitoring, but lower priority than preventive security measures.
</details>

### 11. In the measured Qwen2.5-7B-Instruct benchmark on a single NVIDIA L4 GPU on this page, what happened to per-request latency as concurrency went from 1 to 16?

A. It grew nearly 16x, in proportion to the added load
B. It stayed almost flat (+33%, from p50 5.65s to 7.52s) while aggregate throughput scaled close to linearly
C. It dropped, because more requests let vLLM skip the prefill stage
D. It could not be measured because the GPU ran out of KV cache memory before reaching concurrency 16

<details>
<summary>Show Answer</summary>

**Answer: B. It stayed almost flat (+33%, from p50 5.65s to 7.52s) while aggregate throughput scaled close to linearly**

**Explanation:**
This is the core lesson of continuous batching: vLLM does not queue a new request behind the ones already running. It joins the batch on the next scheduler step, so the GPU processes many sequences in parallel instead of serially. In this measured run, p50 latency for a full ~100-128 token response only grew from 5.65s at concurrency 1 to 7.52s at concurrency 16 (+33%), while aggregate completion throughput scaled from roughly 17 tokens/s to 208 tokens/s (client-measured) — because GPU KV cache usage stayed under 3% the whole time, meaning the GPU was compute-bound, not memory-bound, at these concurrency levels.

**Why the other options are wrong:**
- A. This describes what would happen with serial (non-batched) request handling, not continuous batching.
- C. Continuous batching does not skip prefill; every new request still goes through prefill before decode, it just happens alongside other requests' decode steps.
- D. GPU KV cache usage peaked at only 2.6% at concurrency 16 on this 24 GiB L4 — nowhere near exhausted. The benchmark did not push concurrency high enough to find that limit.
</details>
