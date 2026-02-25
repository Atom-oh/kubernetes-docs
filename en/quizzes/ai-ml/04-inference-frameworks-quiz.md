# Inference Frameworks Quiz

This quiz tests your understanding of LLM inference frameworks for Kubernetes deployments, including NVIDIA NIM, NVIDIA Dynamo, AIBrix, Ray Serve, and AWS Neuron.

## Quiz Questions

### 1. What is the primary benefit of NVIDIA NIM for LLM deployment?

A) It only supports open-source models
B) It provides production-ready, containerized LLM deployments with optimized inference engines and OpenAI-compatible APIs
C) It requires manual compilation of all models
D) It only works with CPU instances

<details>
<summary>Show Answer</summary>

**Answer: B) It provides production-ready, containerized LLM deployments with optimized inference engines and OpenAI-compatible APIs**

**Explanation:**
NVIDIA NIM (NVIDIA Inference Microservices) provides production-ready, containerized LLM deployments with several key features:

1. **Optimized Inference Engines**: Uses TensorRT-LLM for maximum performance
2. **OpenAI-Compatible APIs**: Drop-in replacement for OpenAI API calls
3. **Built-in Monitoring**: Prometheus metrics and Grafana dashboards
4. **NGC Catalog Integration**: Easy access to pre-optimized models
5. **Enterprise Support**: Production SLAs and support from NVIDIA

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

### 2. What is "disaggregated serving" in NVIDIA Dynamo?

A) Running multiple models on a single GPU
B) Separating prefill (prompt processing) and decode (token generation) phases onto different worker pools
C) Distributing logs across multiple servers
D) Running inference without GPUs

<details>
<summary>Show Answer</summary>

**Answer: B) Separating prefill (prompt processing) and decode (token generation) phases onto different worker pools**

**Explanation:**
Disaggregated serving is a key architectural pattern in NVIDIA Dynamo that separates the two main phases of LLM inference:

1. **Prefill Phase**:
   - Processes the input prompt
   - Compute-intensive (needs high FLOPs)
   - Benefits from high-end GPUs like A100

2. **Decode Phase**:
   - Generates output tokens one at a time
   - Memory-bandwidth intensive
   - Can use more cost-effective GPUs like A10G

**Benefits of Disaggregation:**
- Better resource utilization
- Cost optimization through heterogeneous GPU usage
- Higher overall throughput
- Independent scaling of prefill and decode capacity

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

### 3. Which component of AIBrix handles dynamic LoRA adapter loading and management?

A) Gateway
B) Autoscaler
C) LoRA Manager
D) Model Registry

<details>
<summary>Show Answer</summary>

**Answer: C) LoRA Manager**

**Explanation:**
AIBrix consists of several key components, each with specific responsibilities:

1. **Gateway**: Intelligent request routing and load balancing
2. **LoRA Manager**: Dynamic LoRA adapter loading and management
3. **Autoscaler**: Workload-aware autoscaling for inference pods
4. **Model Registry**: Centralized model and adapter management

The **LoRA Manager** specifically handles:
- Dynamic loading of LoRA adapters without restart
- Hot-swapping between different adapters
- Memory management for multiple adapters
- Adapter versioning and lifecycle

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

### 4. What Kubernetes operator is used to deploy Ray Serve for distributed inference?

A) NVIDIA GPU Operator
B) KubeRay Operator
C) Prometheus Operator
D) Flux Operator

<details>
<summary>Show Answer</summary>

**Answer: B) KubeRay Operator**

**Explanation:**
The KubeRay Operator is the Kubernetes-native way to deploy and manage Ray clusters, including Ray Serve for distributed inference.

**KubeRay Operator Features:**
- Manages Ray cluster lifecycle
- Supports RayCluster, RayJob, and RayService CRDs
- Handles auto-scaling of Ray workers
- Integrates with Kubernetes RBAC and networking

**Installation:**
```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace
```

**RayService Example:**
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

### 5. What is the primary advantage of using AWS Inferentia2 (inf2) instances for LLM inference?

A) Higher GPU memory than A100
B) Up to 70% lower cost compared to GPU instances
C) Faster model compilation times
D) Better support for training workloads

<details>
<summary>Show Answer</summary>

**Answer: B) Up to 70% lower cost compared to GPU instances**

**Explanation:**
AWS Inferentia2 provides significant cost advantages for inference workloads:

**Cost Benefits:**
- Up to 70% lower cost vs comparable GPU instances
- High throughput per dollar
- Efficient for inference-only workloads

**Supported Models:**
- Llama 2/3
- Mistral
- Stable Diffusion
- Various encoder models

**Instance Types:**
| Instance | Neuron Cores | Memory | Use Case |
|----------|--------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | 7B models |
| inf2.24xlarge | 6 | 96 GB | 13B-70B models |
| inf2.48xlarge | 12 | 192 GB | 70B+ models |

**Trade-offs:**
- Requires model compilation for Neuron
- Limited model support compared to GPUs
- Longer initial setup time

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

### 6. What metric measures the time until the first token is generated in LLM inference?

A) ITL (Inter-Token Latency)
B) TTFT (Time to First Token)
C) TPS (Tokens Per Second)
D) QPS (Queries Per Second)

<details>
<summary>Show Answer</summary>

**Answer: B) TTFT (Time to First Token)**

**Explanation:**
TTFT (Time to First Token) is a critical latency metric for LLM inference that measures how long a user waits before seeing any output.

**Key LLM Inference Metrics:**

1. **TTFT (Time to First Token)**:
   - Time from request submission to first token
   - Includes prompt processing (prefill) time
   - Target: < 500ms for good UX

2. **ITL (Inter-Token Latency)**:
   - Time between consecutive generated tokens
   - Affects perceived streaming speed
   - Target: < 50ms

3. **Throughput**:
   - Tokens generated per second
   - Measures system capacity

4. **E2E Latency**:
   - Total time for complete response
   - TTFT + (ITL * output_tokens)

**Monitoring Example:**
```promql
# TTFT P99
histogram_quantile(0.99, sum(rate(nim_time_to_first_token_bucket[5m])) by (le))

# ITL P99
histogram_quantile(0.99, sum(rate(nim_inter_token_latency_bucket[5m])) by (le))

# Throughput
sum(rate(nim_tokens_generated_total[5m]))
```

</details>

### 7. In NVIDIA Dynamo, what is the purpose of KV-aware routing?

A) To route requests based on user location
B) To route requests based on KV cache locality for optimal performance
C) To route requests to the cheapest instance
D) To route requests based on model version

<details>
<summary>Show Answer</summary>

**Answer: B) To route requests based on KV cache locality for optimal performance**

**Explanation:**
KV-aware routing in NVIDIA Dynamo optimizes request routing based on where KV cache data is located, improving performance by reducing data transfer.

**How KV-aware Routing Works:**

1. **KV Cache Tracking**: The router tracks which decode workers have cached KV data for previous requests
2. **Locality Optimization**: Routes follow-up requests (in multi-turn conversations) to workers that already have relevant KV cache
3. **Load Balancing**: Balances locality benefits against worker load

**Configuration:**
```yaml
router:
  kv_routing:
    enabled: true
    locality_weight: 0.7  # Prefer cache locality
    load_weight: 0.3      # Consider worker load
```

**Benefits:**
- Reduced TTFT for multi-turn conversations
- Lower memory pressure (avoid duplicate KV cache)
- Better GPU memory utilization
- Higher effective throughput

**Routing Decision Formula:**
```
score = locality_weight * cache_hit_score + load_weight * (1 - worker_load)
```

</details>

### 8. What command is used to install the Neuron device plugin for Kubernetes?

A) `kubectl apply -f nvidia-device-plugin.yml`
B) `helm install neuron-plugin aws/neuron`
C) `kubectl apply -f k8s-neuron-device-plugin.yml`
D) `eksctl create addon --name neuron-device-plugin`

<details>
<summary>Show Answer</summary>

**Answer: C) `kubectl apply -f k8s-neuron-device-plugin.yml`**

**Explanation:**
The Neuron device plugin is installed using kubectl apply with the official manifest from the AWS Neuron SDK repository.

**Installation Command:**
```bash
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml
```

**Verification:**
```bash
# Check DaemonSet
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# Check Neuron devices on nodes
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

**Resource Request Format:**
```yaml
resources:
  limits:
    aws.amazon.com/neuron: 2  # Request 2 Neuron cores
```

The NVIDIA device plugin uses `nvidia.com/gpu` while Neuron uses `aws.amazon.com/neuron`.

</details>

### 9. Which inference framework provides built-in autoscaling as a core feature?

A) vLLM standalone
B) NVIDIA NIM
C) AIBrix
D) Triton Inference Server

<details>
<summary>Show Answer</summary>

**Answer: C) AIBrix**

**Explanation:**
AIBrix provides built-in, workload-aware autoscaling as a core feature, unlike other frameworks that require external solutions like HPA or KEDA.

**AIBrix Autoscaler Features:**
- Workload-aware scaling policies
- Multiple metric support (RPS, latency, GPU utilization, queue depth)
- Configurable scale-up/scale-down behavior
- Per-deployment scaling policies

**AIBrix Autoscaler Configuration:**
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

**Comparison:**
| Framework | Auto-scaling |
|-----------|--------------|
| NIM | Manual (external HPA/KEDA) |
| Dynamo | Manual (external) |
| AIBrix | Built-in |
| vLLM | Manual (external) |
| Ray Serve | Built-in |
| Triton | Manual (external) |

</details>

### 10. What is the purpose of the NGC Catalog in NVIDIA NIM deployments?

A) To store Kubernetes manifests
B) To provide pre-optimized model containers and configurations
C) To manage cluster networking
D) To handle user authentication

<details>
<summary>Show Answer</summary>

**Answer: B) To provide pre-optimized model containers and configurations**

**Explanation:**
The NGC (NVIDIA GPU Cloud) Catalog is NVIDIA's repository for GPU-optimized software, including pre-built NIM containers with optimized models.

**NGC Catalog Features:**
- Pre-optimized model containers
- Multiple model profiles (different batch sizes, precisions)
- Version management
- Security scanning
- Enterprise support

**Accessing NGC:**
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

**Using NGC Images:**
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

**Available NIM Profiles:**
- `vllm-bf16-tp8`: 8-GPU tensor parallel, BF16 precision
- `vllm-fp8-tp4`: 4-GPU tensor parallel, FP8 precision
- `tensorrt-llm-fp16-tp8`: TensorRT-LLM backend

</details>

### 11. Which backends does NVIDIA Dynamo support for inference?

A) Only TensorRT-LLM
B) vLLM, SGLang, and TensorRT-LLM
C) Only vLLM
D) PyTorch only

<details>
<summary>Show Answer</summary>

**Answer: B) vLLM, SGLang, and TensorRT-LLM**

**Explanation:**
NVIDIA Dynamo is designed to be backend-agnostic and supports multiple inference engines:

1. **vLLM**:
   - Open-source, high-performance
   - PagedAttention for memory efficiency
   - Wide model support

2. **SGLang**:
   - Optimized for structured generation
   - Fast JSON/regex constrained decoding
   - Efficient prefix caching

3. **TensorRT-LLM**:
   - Maximum NVIDIA GPU performance
   - Optimized kernels
   - INT8/FP8 quantization

**Configuration Example:**
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

This flexibility allows:
- Mixing backends for optimal performance
- Testing different engines
- Using specialized backends for specific tasks

</details>

### 12. What is the recommended way to handle model storage for vLLM deployments on EKS?

A) Store models in ConfigMaps
B) Download models at container startup every time
C) Use FSx for Lustre or persistent volumes with pre-downloaded models
D) Embed models in the container image

<details>
<summary>Show Answer</summary>

**Answer: C) Use FSx for Lustre or persistent volumes with pre-downloaded models**

**Explanation:**
For production LLM deployments, using high-performance persistent storage is critical:

**Recommended Storage Options:**

1. **FSx for Lustre**:
   - High-throughput parallel file system
   - Ideal for large model files
   - S3 integration for model updates
   - Up to 1000+ MB/s throughput

2. **EBS gp3 Volumes**:
   - Good for single-node deployments
   - Cost-effective
   - Up to 16,000 IOPS

3. **EFS**:
   - Shared access across pods
   - Lower throughput than FSx
   - Good for smaller models

**FSx for Lustre Setup:**
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

**Why NOT other options:**
- **ConfigMaps**: 1MB size limit, not for large files
- **Download at startup**: Slow startup, bandwidth costs, reliability issues
- **Embedded in image**: Huge images, slow pulls, version inflexibility

</details>

### 13. What is the function of GenAI-Perf in NIM deployments?

A) To generate AI images
B) To benchmark and profile LLM inference performance
C) To manage GPU memory
D) To configure network policies

<details>
<summary>Show Answer</summary>

**Answer: B) To benchmark and profile LLM inference performance**

**Explanation:**
GenAI-Perf is NVIDIA's tool for benchmarking and profiling generative AI inference performance.

**Features:**
- Measures TTFT, ITL, throughput
- Supports concurrent request testing
- Multiple endpoint types (chat, completion)
- Export results for analysis

**Installation:**
```bash
pip install genai-perf
```

**Usage Example:**
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

**Key Metrics Reported:**
- Time to First Token (P50, P90, P99)
- Inter-Token Latency (P50, P90, P99)
- Request throughput
- Token throughput
- GPU utilization during benchmark

</details>

### 14. Which Kubernetes resource type is most appropriate for deploying distributed vLLM with tensor parallelism across multiple pods?

A) Deployment
B) StatefulSet
C) DaemonSet
D) ReplicaSet

<details>
<summary>Show Answer</summary>

**Answer: B) StatefulSet**

**Explanation:**
StatefulSet is the appropriate resource for distributed vLLM deployments that require:

1. **Stable Network Identity**: Each pod gets a predictable hostname (vllm-0, vllm-1, etc.)
2. **Ordered Deployment**: Pods are created in sequence, important for master/worker coordination
3. **Stable Storage**: Each pod can have its own persistent volume
4. **Headless Service**: Direct pod-to-pod communication for NCCL

**StatefulSet Configuration:**
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

**Why StatefulSet over Deployment:**
- Deployments don't guarantee stable hostnames
- NCCL requires predictable addressing
- Master election needs consistent pod identity

</details>

### 15. What environment variable controls the number of Neuron cores visible to a container?

A) CUDA_VISIBLE_DEVICES
B) NEURON_RT_VISIBLE_CORES
C) AWS_NEURON_CORES
D) NEURON_DEVICE_COUNT

<details>
<summary>Show Answer</summary>

**Answer: B) NEURON_RT_VISIBLE_CORES**

**Explanation:**
`NEURON_RT_VISIBLE_CORES` controls which Neuron cores are visible to the Neuron runtime within a container.

**Key Neuron Environment Variables:**

1. **NEURON_RT_VISIBLE_CORES**:
   - Specifies which cores to use
   - Format: "0,1" or "0-3"
   ```yaml
   env:
   - name: NEURON_RT_VISIBLE_CORES
     value: "0,1"
   ```

2. **NEURON_RT_NUM_CORES**:
   - Total number of cores to use
   ```yaml
   env:
   - name: NEURON_RT_NUM_CORES
     value: "2"
   ```

3. **NEURON_CC_FLAGS**:
   - Compiler flags for model compilation
   ```yaml
   env:
   - name: NEURON_CC_FLAGS
     value: "--model-type transformer"
   ```

**Complete Example:**
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

Note: `CUDA_VISIBLE_DEVICES` is for NVIDIA GPUs, not Neuron.

</details>
