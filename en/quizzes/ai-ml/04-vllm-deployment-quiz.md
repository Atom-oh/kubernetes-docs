# vLLM Deployment Quiz

Baseline: vLLM 0.29.0. Historical L4 results are distinguished from current validation.

## Quiz Questions

### 1. Which statement correctly describes vLLM?

- A. A model named Vector Language Model
- B. An inference engine for supported generative/multimodal and other model workloads
- C. A database-only optimizer
- D. A training tool that automatically improves every model’s accuracy

<details>
<summary>Show Answer</summary>

**Answer: B. An inference engine for supported generative/multimodal and other model workloads**

vLLM is an engine, not that invented expansion. PagedAttention and batching benefits depend on workloads; no fixed speedup or queue-free execution is guaranteed.
</details>

### 2. How should GPU memory requirements be estimated?

- A. 70B always fits 80GB regardless of precision
- B. Add weights, KV cache, activations/workspaces and communication, accounting for architecture, precision and parallelism
- C. Four CPU cores per GPU guarantee every model runs
- D. More host RAM eliminates GPU requirements

<details>
<summary>Show Answer</summary>

**Answer: B. Add weights, KV cache, activations/workspaces and communication, accounting for architecture, precision and parallelism**

70B FP16/BF16 weights alone are about 140GB. GQA/MQA require KV-head counts, not an MHA hidden-size formula. Check the current NVIDIA capability 7.5 minimum and additional kernel requirements.
</details>

### 3. Which storage statement is correct?

- A. FSx for Lustre is always optimal
- B. snapshot_download downloads from S3
- C. Choose by load time, concurrency, cost and retention; record model revision and integrity
- D. emptyDir is always erased on container restart

<details>
<summary>Show Answer</summary>

**Answer: C. Choose by load time, concurrency, cost and retention; record model revision and integrity**

emptyDir can survive container restart but not Pod recreation. Distinguish FSx static/dynamic provisioning, EBS access modes and identical worker model paths. Hugging Face downloads and S3 transfers are separate.
</details>

### 4. How do TP, PP and independent replicas differ?

- A. Increasing StatefulSet replicas automatically reconfigures TP
- B. TP partitions within layers, PP partitions layer stages, and independent replicas each load the model
- C. TP always lowers single-request latency
- D. Every multi-node deployment uses --rank

<details>
<summary>Show Answer</summary>

**Answer: B. TP partitions within layers, PP partitions layer stages, and independent replicas each load the model**

0.29.0 multiprocessing uses --nnodes/--node-rank and headless workers; Ray needs a real cluster. Match environments, models, network/rendezvous and GPUs. Process topology is not Kubernetes replica count.
</details>

### 5. Which availability statement is correct?

- A. PDB guarantees minimum replicas through every node failure
- B. maxUnavailable0 alone guarantees no downtime
- C. Validate independent replicas, probes, startup, spare capacity, draining and streams together
- D. Spreading one TP group across AZs always improves performance

<details>
<summary>Show Answer</summary>

**Answer: C. Validate independent replicas, probes, startup, spare capacity, draining and streams together**

PDB constrains some voluntary evictions. The example Recreate strategy avoids an extra GPU but causes update downtime. startupProbe gates readiness/liveness during initialization; verify actual loading time.
</details>

### 6. Which batching/cache statement is correct?

- A. Every request executes immediately with no queue
- B. Scheduling occurs step by step and queues can form under token/cache/capacity limits
- C. Prefix caching always reuses entire responses
- D. --swap-space is the 0.29 memory-expansion default

<details>
<summary>Show Answer</summary>

**Answer: B. Scheduling occurs step by step and queues can form under token/cache/capacity limits**

Prefix caching reuses supported prefix KV state. Chunked prefill, max-num-seqs, token budgets and context limits differ. CacheConfig defaults gpu_memory_utilization to 0.92; the example sets 0.80. --swap-space is absent from current CLI.
</details>

### 7. What should current metrics configuration use?

- A. A separate 8001 port and --enable-metrics=true
- B. /metrics on API port 8000 with actual vllm: names, labels and units
- C. KV occupancy as total GPU-memory bytes
- D. Alert on every idle period as low-throughput failure

<details>
<summary>Show Answer</summary>

**Answer: B. /metrics on API port 8000 with actual vllm: names, labels and units**

Examples include vllm:generation_tokens_total and vllm:e2e_request_latency_seconds_bucket. KV occupancy is a ratio where 1 means 100%. Distinguish model aggregation, gateway errors/cancellations, TTFT and end-to-end latency.
</details>

### 8. Which multi-node networking statement is correct?

- A. API keys encrypt every internal transport
- B. Arbitrary copied GID/mlx5 settings configure EFA
- C. Validate supported devices/drivers, OFI NCCL/libfabric and private communication paths
- D. A single-node NCCL test proves multi-node EFA performance

<details>
<summary>Show Answer</summary>

**Answer: C. Validate supported devices/drivers, OFI NCCL/libfabric and private communication paths**

Distributed communication needs a trusted network. API authentication differs from PyTorch/Ray/KV transport security. Generic SR-IOV/InfiniBand templates and invented NCCL variables are not turnkey EKS configuration.
</details>

### 9. Which scaling/routing statement is correct?

- A. An HTTP model header automatically reads the JSON model field
- B. Session affinity automatically shares all KV caches
- C. Select replicas, TP/PP and routing based on measured bottlenecks and model topology
- D. CPU and storage never affect performance when GPUs exist

<details>
<summary>Show Answer</summary>

**Answer: C. Select replicas, TP/PP and routing based on measured bottlenecks and model topology**

Prefix, response and weight caches differ. CPU tokenization, networking or loading can bottleneck. HPA/KEDA and NodePools are separate layers with metric, ownership and capacity requirements.
</details>

### 10. Which API-key/security statement is correct in 0.29.0?

- A. --api-key protects every server endpoint
- B. Other paths and operational capabilities need gateway, permission and network boundaries beyond prefix authentication
- C. CORS replaces authentication
- D. A single regex prevents all prompt injection and PII leakage

<details>
<summary>Show Answer</summary>

**Answer: B. Other paths and operational capabilities need gateway, permission and network boundaries beyond prefix authentication**

The inspected middleware guards /v1,/v2,/inference,/cohere prefixes; other paths and OPTIONS bypass it. Dynamic LoRA needs explicit opt-in and a trusted operator path. Secret RequestResponse auditing and Pod annotations pretending to enable control-plane audit are unsafe/ineffective examples.
</details>

### 11. How should the historical L4 result 5.65s→7.52s be interpreted?

- A. Latency did not increase
- B. p50 increased about 33.1% while aggregate throughput rose in that test range; an old report without raw logs is not current-version proof
- C. A profiler proved the memory bottleneck
- D. Continuous batching skips prefill

<details>
<summary>Show Answer</summary>

**Answer: B. p50 increased about 33.1% while aggregate throughput rose in that test range; an old report without raw logs is not current-version proof**

The reported data is one 0.6.4.post1 run. This audit did not locate raw request/server logs or rerun it. A maximum logged interval average is not instantaneous peak; a roofline calculation is an estimate, not profiler evidence.
</details>

---

[Return to Learning Materials](../../ai-ml/02-vllm-deployment.md)
