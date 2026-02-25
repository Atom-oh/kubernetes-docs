# Model Training on EKS Quiz

This quiz tests your understanding of model training on Amazon EKS, including distributed training strategies, Slurm/Slinky integration, GPU and Trainium-based training, storage configuration, and optimization techniques.

## Quiz Questions

### 1. Which distributed training strategy splits a single layer across multiple GPUs?

A) Data Parallelism
B) Tensor Parallelism
C) Pipeline Parallelism
D) Expert Parallelism

<details>
<summary>Show Answer</summary>

**Answer: B) Tensor Parallelism**

**Explanation:**
Tensor Parallelism splits individual layers (such as attention layers or feed-forward networks) across multiple GPUs. Each GPU holds a portion of the layer's weights and computes its part of the operation.

**Comparison of parallelism strategies:**

| Strategy | What is Distributed | Communication Pattern |
|----------|---------------------|----------------------|
| Data Parallelism | Training data batches | Gradient synchronization |
| Tensor Parallelism | Individual layers | Intra-layer communication |
| Pipeline Parallelism | Groups of layers (stages) | Inter-stage activation passing |
| Expert Parallelism | Expert networks in MoE | Token routing |

Tensor Parallelism is particularly useful for very large layers that don't fit in a single GPU's memory, such as the attention layers in large language models.

</details>

### 2. What is the recommended parallelism strategy for training a 200 billion parameter model?

A) Data Parallelism only
B) Tensor Parallelism only
C) Pipeline Parallelism only
D) 3D Parallelism (DP + TP + PP)

<details>
<summary>Show Answer</summary>

**Answer: D) 3D Parallelism (DP + TP + PP)**

**Explanation:**
For models exceeding 100 billion parameters, 3D Parallelism combines all three strategies for maximum efficiency:

- **Data Parallelism (DP)**: Replicates the model across groups of GPUs, each processing different data batches
- **Tensor Parallelism (TP)**: Splits large layers within a node (typically 8 GPUs with NVLink)
- **Pipeline Parallelism (PP)**: Distributes layer groups across nodes to reduce memory per device

Example configuration for a 200B model on 64 A100 GPUs:
```
TP=8  (within each node)
PP=4  (across 4 nodes)
DP=2  (2 data parallel replicas)
Total: 8 × 4 × 2 = 64 GPUs
```

This approach provides:
- Maximum memory efficiency
- Balanced computation and communication
- Ability to train models that exceed single-node memory capacity

</details>

### 3. In Slinky's architecture, which component manages job accounting and cluster state?

A) slurmctld
B) slurmdbd
C) slurmd
D) slurmrestd

<details>
<summary>Show Answer</summary>

**Answer: B) slurmdbd**

**Explanation:**
The Slinky/Slurm components serve different purposes:

| Component | Role | Kubernetes Resource |
|-----------|------|---------------------|
| **slurmctld** | Central controller - manages jobs, partitions, and resource allocation | StatefulSet |
| **slurmdbd** | Database daemon - handles job accounting, usage tracking, and cluster state persistence | StatefulSet with MySQL/MariaDB |
| **slurmd** | Compute daemon - runs on each worker node, executes job steps | DaemonSet |
| **slurmrestd** | REST API - enables programmatic job submission | Deployment |

The slurmdbd daemon is critical for:
- Storing historical job data
- Tracking resource usage for accounting
- Maintaining cluster state for fault recovery
- Supporting fair-share scheduling based on past usage

</details>

### 4. What CRD does Slinky use to define compute node groups (partitions)?

A) SlurmCluster
B) SlurmNodeSet
C) SlurmPartition
D) SlurmWorker

<details>
<summary>Show Answer</summary>

**Answer: B) SlurmNodeSet**

**Explanation:**
Slinky introduces two main Custom Resource Definitions:

1. **SlurmCluster**: Defines the overall cluster configuration including:
   - Controller (slurmctld) settings
   - Database (slurmdbd) configuration
   - REST API settings
   - Shared storage configuration

2. **SlurmNodeSet**: Defines compute node groups (partitions) including:
   - Instance types and GPU configuration
   - Resource allocation (CPUs, memory, GPU memory)
   - Node features for GRES (Generic Resource Scheduling)
   - Autoscaling settings with Karpenter integration
   - Placement group configuration for low-latency networking

Example SlurmNodeSet:
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

### 5. Which environment variable enables EFA (Elastic Fabric Adapter) in NCCL for distributed training?

A) NCCL_EFA_ENABLE=1
B) FI_PROVIDER=efa
C) EFA_ENABLED=true
D) NCCL_NET=efa

<details>
<summary>Show Answer</summary>

**Answer: B) FI_PROVIDER=efa**

**Explanation:**
To enable EFA networking with NCCL for distributed training, you need to set several environment variables:

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

EFA provides up to 400 Gbps networking bandwidth on supported instance types (p4d, p5, trn1) and significantly reduces communication latency for distributed training.

Additionally, pods must request EFA devices:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request 4 EFA devices
```

</details>

### 6. What is the purpose of NVIDIA BioNeMo on EKS?

A) GPU monitoring and metrics collection
B) Drug discovery and molecular modeling
C) Container networking optimization
D) Model quantization and compression

<details>
<summary>Show Answer</summary>

**Answer: B) Drug discovery and molecular modeling**

**Explanation:**
NVIDIA BioNeMo is a specialized framework for AI-driven drug discovery and molecular modeling. It provides:

**Key capabilities:**
- **MegaMolBART**: Molecular generation and optimization
- **ESMFold**: Protein structure prediction
- **DiffDock**: Molecular docking
- **NVIDIA Clara**: Drug discovery pipelines

**Use cases on EKS:**
- Generating novel drug candidates
- Predicting protein-ligand interactions
- Optimizing molecular properties
- High-throughput virtual screening

**Deployment requirements:**
```yaml
resources:
  limits:
    nvidia.com/gpu: 8      # Multiple GPUs for large models
    memory: "500Gi"        # High memory for molecular datasets
```

BioNeMo leverages NVIDIA's GPU acceleration to dramatically speed up computational chemistry workflows compared to CPU-based approaches.

</details>

### 7. Which Neuron SDK package provides high-level training APIs for HuggingFace models on Trainium?

A) torch-neuronx
B) tensorflow-neuronx
C) optimum-neuron
D) transformers-neuronx

<details>
<summary>Show Answer</summary>

**Answer: C) optimum-neuron**

**Explanation:**
The Neuron SDK includes several packages with different purposes:

| Package | Purpose | Level |
|---------|---------|-------|
| **torch-neuronx** | Core PyTorch integration | Low-level |
| **tensorflow-neuronx** | Core TensorFlow integration | Low-level |
| **transformers-neuronx** | Optimized inference for transformers | Mid-level |
| **optimum-neuron** | High-level training/inference APIs | High-level |

**optimum-neuron** is part of HuggingFace's Optimum library and provides:
- `NeuronTrainer`: Drop-in replacement for HuggingFace Trainer
- `NeuronTrainingArguments`: Training configuration with Neuron-specific options
- Automatic tensor parallelism configuration
- Integration with distributed training (ZeRO, pipeline parallelism)
- Checkpoint compatibility with standard HuggingFace models

Example usage:
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

### 8. What is the recommended storage solution for high-throughput distributed training data access on EKS?

A) Amazon EBS gp3
B) Amazon EFS
C) FSx for Lustre
D) Amazon S3 direct access

<details>
<summary>Show Answer</summary>

**Answer: C) FSx for Lustre**

**Explanation:**
FSx for Lustre is the recommended storage for distributed ML training due to:

**Performance characteristics:**
- Up to 1+ TB/s aggregate throughput
- Sub-millisecond latencies
- Parallel file system optimized for HPC/ML workloads

**Key features for ML training:**
- **S3 integration**: Automatic data import/export with S3 data repositories
- **ReadWriteMany**: Multiple pods can access simultaneously
- **High IOPS**: Critical for random access patterns in training
- **Checkpoint support**: Fast checkpoint writes during training

**Comparison:**

| Storage | Throughput | Access Mode | Best For |
|---------|------------|-------------|----------|
| FSx Lustre | Very High | ReadWriteMany | Training data, checkpoints |
| EFS | Medium | ReadWriteMany | Shared configs, models |
| EBS | High | ReadWriteOnce | Single-node workloads |
| S3 | Variable | Object | Cold data, archives |

Configuration example:
```yaml
lustreConfiguration:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: 250  # MB/s per TiB
  dataRepositoryAssociations:
    - fileSystemPath: /data
      dataRepositoryPath: s3://bucket/training-data
```

</details>

### 9. In a Volcano Job with `minAvailable: 4`, what happens if only 3 nodes are available?

A) The job starts with 3 workers
B) The job waits until 4 nodes are available
C) The job fails immediately
D) The job requests additional nodes from Karpenter

<details>
<summary>Show Answer</summary>

**Answer: B) The job waits until 4 nodes are available**

**Explanation:**
The `minAvailable` field in Volcano implements **Gang Scheduling**, which ensures all required pods are scheduled together or none at all.

**Gang Scheduling behavior:**
- If `minAvailable: 4` is set, all 4 pods must be schedulable simultaneously
- The job remains in pending state until resources are available
- Prevents deadlock situations in distributed training
- Ensures consistent training environment

**Why this matters for ML training:**
1. **Distributed training requires all workers**: Training cannot proceed with partial workers
2. **Resource efficiency**: Prevents partial allocation that wastes resources
3. **Deterministic behavior**: Training starts with expected parallelism

Example:
```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
spec:
  minAvailable: 4  # Gang scheduling requirement
  tasks:
    - name: worker
      replicas: 4
```

Without gang scheduling, some workers might start while others are pending, leading to timeouts and failed training jobs.

</details>

### 10. What is the benefit of using BF16 (bfloat16) over FP16 for training?

A) Higher precision
B) No loss scaling required
C) Smaller memory footprint
D) Faster computation

<details>
<summary>Show Answer</summary>

**Answer: B) No loss scaling required**

**Explanation:**
BF16 (Brain Floating Point 16) has the same exponent range as FP32 but with reduced mantissa precision:

| Format | Exponent Bits | Mantissa Bits | Range |
|--------|--------------|---------------|-------|
| FP32 | 8 | 23 | Large |
| FP16 | 5 | 10 | Limited |
| BF16 | 8 | 7 | Large (same as FP32) |

**Why BF16 doesn't need loss scaling:**
- BF16's 8 exponent bits provide the same dynamic range as FP32
- FP16's limited range causes underflow/overflow during training
- Loss scaling artificially increases gradients to prevent underflow in FP16

**BF16 advantages:**
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

BF16 is supported on:
- NVIDIA A100, H100 GPUs (Ampere and later)
- AWS Trainium chips
- Intel Sapphire Rapids CPUs

</details>

### 11. What does gradient checkpointing achieve during training?

A) Faster forward pass
B) Reduced communication overhead
C) Memory savings by recomputing activations
D) Improved model accuracy

<details>
<summary>Show Answer</summary>

**Answer: C) Memory savings by recomputing activations**

**Explanation:**
Gradient checkpointing (also called activation checkpointing) trades compute for memory by selectively storing activations during the forward pass and recomputing them during backpropagation.

**How it works:**
1. **Without checkpointing**: All activations stored in memory
2. **With checkpointing**: Only checkpoint activations stored; intermediate activations recomputed during backward pass

**Memory savings:**
- Reduces activation memory from O(n) to O(sqrt(n)) where n is number of layers
- Enables training 3-4x larger batch sizes
- Critical for training large models on limited GPU memory

**Configuration in PyTorch:**
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

**Trade-offs:**
- ~30% increase in compute time
- 3-4x reduction in activation memory
- Enables training larger models/batches

</details>

### 12. Which DeepSpeed ZeRO stage offloads both optimizer states AND model parameters to CPU memory?

A) ZeRO Stage 1
B) ZeRO Stage 2
C) ZeRO Stage 3
D) ZeRO Stage 0

<details>
<summary>Show Answer</summary>

**Answer: C) ZeRO Stage 3**

**Explanation:**
DeepSpeed ZeRO (Zero Redundancy Optimizer) progressively reduces memory redundancy across stages:

| Stage | Partitions | CPU Offload Available |
|-------|------------|----------------------|
| Stage 0 | None (baseline) | No |
| Stage 1 | Optimizer states | Optimizer states |
| Stage 2 | Optimizer states + Gradients | Optimizer states |
| Stage 3 | Optimizer states + Gradients + Parameters | Both optimizer and parameters |

**ZeRO Stage 3 configuration:**
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

**When to use ZeRO-3:**
- Training models larger than GPU memory
- When you need maximum memory efficiency
- Acceptable to trade some speed for memory

**Memory reduction (approximate):**
- Stage 1: 4x reduction
- Stage 2: 8x reduction
- Stage 3: Linear scaling with number of GPUs (theoretically unlimited)

</details>

### 13. What is the purpose of the `slotsPerWorker` field in an MPIJob specification?

A) Number of CPU cores per worker
B) Number of GPU devices per worker
C) Number of MPI processes per worker
D) Number of network interfaces per worker

<details>
<summary>Show Answer</summary>

**Answer: C) Number of MPI processes per worker**

**Explanation:**
In an MPIJob, `slotsPerWorker` defines how many MPI ranks (processes) each worker pod will run:

```yaml
apiVersion: kubeflow.org/v1
kind: MPIJob
spec:
  slotsPerWorker: 8  # 8 MPI processes per worker
  mpiReplicaSpecs:
    Worker:
      replicas: 4  # 4 worker pods
```

**Total MPI processes = slotsPerWorker × Worker replicas**
In this example: 8 × 4 = 32 MPI processes

**Common configuration:**
- Set `slotsPerWorker` equal to GPUs per node
- Each MPI rank typically handles one GPU
- For 8-GPU nodes: `slotsPerWorker: 8`

**Launcher command example:**
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

This ensures each GPU is assigned to exactly one MPI process, maximizing parallelism while avoiding GPU contention.

</details>

### 14. What is the recommended checkpoint frequency strategy for long-running training jobs?

A) Checkpoint every epoch only
B) Checkpoint every step for maximum safety
C) Checkpoint every N steps, keeping last 3-5 checkpoints
D) No checkpointing to maximize training speed

<details>
<summary>Show Answer</summary>

**Answer: C) Checkpoint every N steps, keeping last 3-5 checkpoints**

**Explanation:**
The optimal checkpoint strategy balances recovery capability with storage costs and training overhead:

**Recommended approach:**
```yaml
checkpoint:
  save_steps: 500           # Save every 500 steps
  save_total_limit: 5       # Keep only last 5 checkpoints
  save_on_each_node: false  # Save from rank 0 only
```

**Why this strategy:**
1. **Recovery granularity**: Limits data loss to ~500 steps maximum
2. **Storage efficiency**: Keeping 3-5 checkpoints prevents storage bloat
3. **Training overhead**: Checkpointing every step is too slow
4. **Epoch-only is risky**: Long epochs mean significant data loss on failure

**Checkpoint size considerations:**
- Large models (70B+): Each checkpoint can be 100-200GB
- 5 checkpoints = 500GB-1TB storage
- Use S3 lifecycle policies for older checkpoints

**Best practices:**
```python
training_args = TrainingArguments(
    save_strategy="steps",
    save_steps=500,
    save_total_limit=5,
    save_safetensors=True,  # Faster, safer format
)
```

For production training, also sync checkpoints to durable storage (S3) with a checkpoint manager sidecar.

</details>

### 15. Which Karpenter configuration ensures GPU training pods are scheduled in a single availability zone for optimal EFA performance?

A) `consolidationPolicy: WhenEmpty`
B) `topology.kubernetes.io/zone` requirement with single value
C) `karpenter.sh/capacity-type: spot`
D) `disruption.budgets.nodes: "0"`

<details>
<summary>Show Answer</summary>

**Answer: B) `topology.kubernetes.io/zone` requirement with single value**

**Explanation:**
EFA (Elastic Fabric Adapter) requires all communicating instances to be in the same Availability Zone. Karpenter's zone requirement ensures this:

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

**Why single AZ matters for EFA:**
- EFA uses AWS's custom network interface for high-bandwidth, low-latency communication
- Cross-AZ communication cannot use EFA's RDMA capabilities
- Network latency increases significantly across AZs

**Other options explained:**
- A) `consolidationPolicy`: Controls node consolidation, not placement
- C) `capacity-type: spot`: Determines pricing model, not zone
- D) `disruption.budgets`: Prevents node disruption, not zone selection

**Complete configuration for GPU training:**
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

## Summary

This quiz covered essential concepts for model training on EKS:

1. **Distributed Training Strategies**: Data, tensor, pipeline, and expert parallelism
2. **Slinky/Slurm Integration**: Components (slurmctld, slurmdbd, slurmd) and CRDs
3. **GPU Training**: NCCL configuration, EFA networking, BioNeMo
4. **Trainium Training**: Neuron SDK packages, optimum-neuron
5. **Storage**: FSx for Lustre for high-throughput training
6. **Scheduling**: Volcano gang scheduling
7. **Optimization**: Mixed precision (BF16), gradient checkpointing, DeepSpeed ZeRO
8. **Infrastructure**: Karpenter NodePools, checkpoint management

For more information, refer to the [Model Training on EKS](../../ai-ml/05-model-training.md) documentation.
