# AI/ML ベストプラクティス クイズ

このクイズでは、benchmarking、container optimization、GPU selection、networking、storage、observability、cost optimization など、Amazon EKS 上での AI/ML ベストプラクティスに関する理解を確認します。

## クイズ問題

### 1. LLM inference benchmarking において、TTFT (Time to First Token) は何を測定しますか？

A) 応答内のすべてのトークンを生成する合計時間
B) リクエスト送信から最初のトークンが生成されるまでの時間
C) 連続するトークン間の平均時間
D) 1 秒あたりに生成されるトークン数

<details>
<summary>答えを表示</summary>

**答え: B) リクエスト送信から最初のトークンが生成されるまでの時間**

**解説:**
TTFT (Time to First Token) は、リクエストが送信されてから応答の最初のトークンが生成されるまでの latency を測定します。この metric は、ユーザーが応答の開始をどれだけ早く確認できるかを決定するため、user experience にとって重要です。

式は次のとおりです: `TTFT = t_first_token - t_request`

TTFT の重要なポイント:
- アプリケーションの体感的な応答性に直接影響します
- interactive applications では < 500ms を目標にする必要があります
- model loading、prompt processing (prefill)、queue depth の影響を受けます
- TTFT が高い場合、GPU memory、batch size、または system load に潜在的な問題があることを示します

その他の metrics:
- ITL (Inter-Token Latency): 連続するトークン間の時間
- TPS (Tokens Per Second): 生成速度
- E2E Latency: リクエストから完全な応答までの合計時間

</details>

### 2. container startup optimization technique のうち、cold start time を最も大きく削減できるのはどれですか？

A) Multi-stage Docker builds のみ
B) Model artifact decoupling のみ
C) Combined approach (decoupling + multi-stage + prefetching + SOCI)
D) 小さい base images だけを使用する

<details>
<summary>答えを表示</summary>

**答え: C) Combined approach (decoupling + multi-stage + prefetching + SOCI)**

**解説:**
combined approach は cold start time を最も大きく削減し、naive な実装と比較して 80-95% の改善を実現します。

Cold start optimization の比較:

| Technique | Startup Reduction |
|-----------|-------------------|
| Model decoupling | 50-70% |
| Multi-stage builds | 30-50% |
| SOCI snapshotter | 60-80% |
| Image prefetching | 70-90% |
| **Combined approach** | **80-95%** |

combined approach は次のように機能します:
1. **Model decoupling**: 大きな model weights を container images から分離します
2. **Multi-stage builds**: build dependencies を除外して image size を削減します
3. **SOCI snapshotter**: lazy pulling を有効にし、完全な image download の前に containers を起動できるようにします
4. **Image prefetching**: node bootstrap 中に images を事前に pull します

10-50GB になり得る AI/ML images では、この組み合わせにより startup を 5-15 分から 1 分未満に短縮できます。

</details>

### 3. high-bandwidth の inter-node communication を必要とする large-scale distributed training に最も適した GPU instance family はどれですか？

A) G5 (NVIDIA A10G)
B) G6 (NVIDIA L4)
C) P5 (NVIDIA H100)
D) Inf2 (AWS Inferentia2)

<details>
<summary>答えを表示</summary>

**答え: C) P5 (NVIDIA H100)**

**解説:**
NVIDIA H100 GPUs を搭載した P5 instances は、次を提供するため large-scale distributed training に最適です:

- 各 80GB HBM3 memory を備えた **8x NVIDIA H100 GPUs**
- distributed training に不可欠な **3200 Gbps EFA networking**
- node 内での high-bandwidth GPU-to-GPU communication のための **NVLink 4.0**
- data preprocessing のための **192 vCPUs と 2048GB memory**

distributed training の比較:

| Instance | GPUs | GPU Memory | Network | Training Suitability |
|----------|------|------------|---------|---------------------|
| G5 | 1-8 A10G | 24GB | 100 Gbps | 小規模/中規模 models |
| G6 | 1-8 L4 | 24GB | 100 Gbps | Inference focus |
| P4d | 8 A100 | 40-80GB | 400 Gbps EFA | Large-scale training |
| **P5** | **8 H100** | **80GB** | **3200 Gbps EFA** | **Frontier models** |
| Inf2 | 1-12 Inferentia2 | 32GB | 100 Gbps | Inference only |

P5 の 3200 Gbps EFA bandwidth は P4d の 8 倍であり、nodes 間の gradient synchronization が bottleneck になる training jobs に理想的です。

</details>

### 4. distributed AI/ML training における EFA (Elastic Fabric Adapter) の主な目的は何ですか？

A) GPU memory capacity を増やす
B) low-latency、high-bandwidth の inter-node communication を提供する
C) GPU time-sharing を有効にする
D) model inference を高速化する

<details>
<summary>答えを表示</summary>

**答え: B) low-latency、high-bandwidth の inter-node communication を提供する**

**解説:**
EFA (Elastic Fabric Adapter) は Amazon EC2 instances 用の network interface で、high-performance computing (HPC) と machine learning applications が on-premises HPC clusters の inter-node communication performance を実現できるようにします。

distributed training における EFA の主な利点:
1. **OS-bypass capability**: applications が network adapter と直接通信できるようにし、latency を削減します
2. **High bandwidth**: P5 instances で最大 3200 Gbps
3. **Low latency**: collective operations で sub-microsecond latencies
4. **NCCL optimization**: optimized GPU-to-GPU communication のために AWS OFI NCCL plugin と連携します

EFA configuration requirements:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request EFA devices
```

EFA 用 NCCL environment variables:
```bash
export FI_PROVIDER=efa
export FI_EFA_USE_DEVICE_RDMA=1
export NCCL_ALGO=Ring,Tree
```

EFA は次に不可欠です:
- PyTorch DDP、Horovod などの frameworks を使用した multi-node distributed training
- tensor/pipeline parallelism を使用した large model training
- gradient synchronization が bottleneck になる任意の workload

</details>

### 5. AI/ML workloads で EFS の代わりに FSx for Lustre を使用すべきなのはいつですか？

A) 複数の pods から shared access が必要な場合
B) training datasets が 10TB を超え、high throughput が必要な場合
C) model checkpoints を一時的に保存する場合
D) 小さな models で inference workloads を実行する場合

<details>
<summary>答えを表示</summary>

**答え: B) training datasets が 10TB を超え、high throughput が必要な場合**

**解説:**
FSx for Lustre は high throughput を必要とする大規模 training datasets (>10TB) に最適な選択肢であり、EFS はより小さな datasets と shared model storage に適しています。

Storage selection guide:

| Use Case | Recommended Storage | Reasoning |
|----------|---------------------|-----------|
| Training datasets <500GB | EBS gp3 | Single node, cost-effective |
| Training datasets 500GB-10TB | EFS | Multi-node read, moderate throughput |
| **Training datasets >10TB** | **FSx Lustre** | **Parallel filesystem, TB/s throughput** |
| Shared model weights | EFS | ReadWriteMany, caching |
| Temporary checkpoints | Instance store | Lowest latency, ephemeral |
| Long-term model storage | S3 | Cost-effective, durable |

FSx for Lustre の利点:
- 最大 1+ TB/s の throughput (EFS の ~1-3 GB/s と比較)
- sub-millisecond latencies
- `s3ImportPath` による直接 S3 integration
- HPC workloads 向けに設計された parallel filesystem

```yaml
# FSx Lustre for large datasets
storageClassName: fsx-lustre-sc
parameters:
  perUnitStorageThroughput: "250"  # MB/s per TiB
  s3ImportPath: s3://training-data  # Transparent S3 access
```

</details>

### 6. GPU thermal throttling を検出するために monitor すべき DCGM metric はどれですか？

A) DCGM_FI_DEV_GPU_UTIL
B) DCGM_FI_DEV_FB_USED
C) DCGM_FI_DEV_GPU_TEMP
D) DCGM_FI_DEV_XID_ERRORS

<details>
<summary>答えを表示</summary>

**答え: C) DCGM_FI_DEV_GPU_TEMP**

**解説:**
DCGM_FI_DEV_GPU_TEMP は GPU temperature を Celsius で monitor し、thermal throttling conditions を検出するための主要な指標です。

主な GPU metrics とその目的:

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| **DCGM_FI_DEV_GPU_TEMP** | **Thermal monitoring** | **>80C warning, >90C critical** |
| DCGM_FI_DEV_GPU_UTIL | Compute utilization | >95% sustained |
| DCGM_FI_DEV_FB_USED | Memory usage | >95% of total |
| DCGM_FI_DEV_SM_CLOCK | Clock frequency (throttling detection) | Below baseline |
| DCGM_FI_DEV_POWER_USAGE | Power consumption | Near TDP limit |
| DCGM_FI_DEV_XID_ERRORS | Hardware errors | Any increase |

Thermal throttling detection:
```yaml
# Alert rule for thermal issues
- alert: GPUHighTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 80
  for: 5m
  labels:
    severity: warning

- alert: GPUCriticalTemperature
  expr: DCGM_FI_DEV_GPU_TEMP > 90
  for: 1m
  labels:
    severity: critical
```

temperature が threshold を超えると、GPUs は自動的に clock speeds を下げ (thermal throttling)、training と inference performance に影響します。

</details>

### 7. GPU inference workloads で Spot instances を使用する場合の推奨 approach は何ですか？

A) inference では Spot instances を決して使用しない
B) Spot は training のみに使用し、inference には On-Demand を使用する
C) graceful termination handling と topology spread とともに Spot を使用する
D) 特別な configuration なしで Spot を使用する

<details>
<summary>答えを表示</summary>

**答え: C) graceful termination handling と topology spread とともに Spot を使用する**

**解説:**
Spot instances は、graceful termination handling と availability considerations を適切に構成すれば、stateless inference workloads に対して 60-90% の cost savings を提供できます。

Spot inference のベストプラクティス:

1. **Graceful termination handling**:
```yaml
spec:
  terminationGracePeriodSeconds: 120
  containers:
  - lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "curl -X POST localhost:8000/drain; sleep 30"]
```

2. **Topology spread for availability**:
```yaml
topologySpreadConstraints:
- maxSkew: 2
  topologyKey: topology.kubernetes.io/zone
  whenUnsatisfiable: ScheduleAnyway
```

3. **Mixed capacity types**:
```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot"]
    - weight: 50
      preference:
        matchExpressions:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
```

Spot が inference に適している理由:
- Inference pods は通常 stateless です
- 複数の replicas が redundancy を提供します
- 2 分間の interruption warning により graceful drainage が可能です

</details>

### 8. Inter-Token Latency (ITL) を計算する式はどれですか？

A) `t_last_token - t_request`
B) `(t_last_token - t_first_token) / (n_tokens - 1)`
C) `n_tokens / total_generation_time`
D) `t_first_token - t_request`

<details>
<summary>答えを表示</summary>

**答え: B) `(t_last_token - t_first_token) / (n_tokens - 1)`**

**解説:**
Inter-Token Latency (ITL) は、生成中の連続するトークン間の平均時間を測定します。式は次のとおりです:

`ITL = (t_last_token - t_first_token) / (n_tokens - 1)`

各項目:
- `t_last_token`: 最後のトークンが生成された timestamp
- `t_first_token`: 最初のトークンが生成された timestamp
- `n_tokens`: 生成されたトークンの合計数
- トークン間の intervals を測定しているため、`(n_tokens - 1)` で割ります

ITL の重要性:
- chat applications の streaming quality を決定します
- 目標: smooth な user experience のために < 50ms
- ITL が高い場合、GPU memory pressure または compute bottlenecks を示します

その他の metric formulas:
- **TTFT**: `t_first_token - t_request` (time to first token)
- **TPS**: `n_tokens / total_generation_time` (tokens per second)
- **E2E Latency**: `t_complete - t_request` (end-to-end)

計算例:
- 最初のトークンが 500ms、最後のトークンが 2500ms、50 トークンが生成された場合
- ITL = (2500 - 500) / (50 - 1) = 2000 / 49 = ~41ms

</details>

### 9. LLM inference service の maximum throughput を見つけるために最も適切な test scenario はどれですか？

A) Baseline test
B) Saturation test
C) Real dataset test
D) Long context test

<details>
<summary>答えを表示</summary>

**答え: B) Saturation test**

**解説:**
saturation test は、latency が悪化するまで concurrency を段階的に増やすことで maximum throughput を見つけるために特別に設計されており、system の capacity limits を明らかにします。

Test scenario comparison:

| Scenario | Purpose | Configuration |
|----------|---------|---------------|
| Baseline | Establish single-request performance | Concurrency=1, 100 requests |
| **Saturation** | **Find throughput limits** | **Concurrency=[1,5,10,20,50,100]** |
| Production | Validate real-world performance | Variable prompts, realistic load |
| Real dataset | Test with actual data patterns | ShareGPT or domain data |
| Long context | Test context window handling | 4K-128K token prompts |

Saturation test configuration:
```yaml
saturation:
  description: "Find maximum throughput"
  concurrency: [1, 5, 10, 20, 50, 100]  # Incrementally increase
  num_requests: 500
  prompt_length: 256
  max_tokens: 512
```

saturation test で分かること:
- throughput と latency の curve
- latency が悪化し始める point
- system が GPU-bound、memory-bound、または CPU-bound のいずれであるか
- optimal operating concurrency level

目標は、throughput が plateau に達し、latency が許容範囲に留まる curve の「knee」を見つけることです。

</details>

### 10. AI/ML containers に対する SOCI (Seekable OCI) snapshotter の目的は何ですか？

A) container images を圧縮する
B) lazy pulling を有効にし、完全な image download の前に containers を起動できるようにする
C) container images を暗号化する
D) nodes 間で images を共有する

<details>
<summary>答えを表示</summary>

**答え: B) lazy pulling を有効にし、完全な image download の前に containers を起動できるようにする**

**解説:**
SOCI (Seekable OCI) snapshotter は container images の lazy loading を有効にし、image 全体が download される前に containers を起動できるようにします。これは大きな AI/ML images (10-50GB) に特に有効です。

SOCI の仕組み:
1. container image layers の index を作成します
2. 最初は metadata と essential layers のみを download します
3. application が files にアクセスすると、残りの layers を on-demand で取得します
4. image の約 10-20% のみが download された状態で container を起動できます

AI/ML における利点:
- container startup time を 60-80% 削減
- 大きく、ほとんどアクセスされない layers を持つ images に特に効果的
- model weights が container startup 後にアクセスされる場合に最も効果的

SOCI setup:
```bash
# Create SOCI index for an image
soci create \
  --ref public.ecr.aws/myrepo/vllm:latest \
  --platform linux/amd64

# Push the index to registry
soci push \
  --ref public.ecr.aws/myrepo/vllm:latest
```

他の optimizations との組み合わせ:
- Model decoupling (50-70%)
- Multi-stage builds (30-50%)
- SOCI snapshotter (60-80%)
- Image prefetching (70-90%)

SOCI は、container runtime が対応している場合 (SOCI plugin を備えた containerd) かつ images が compatible registries (Amazon ECR) に保存されている場合に最も効果的です。

</details>

### 11. business hours 中の node disruption を防ぐ Karpenter consolidation policy setting はどれですか？

A) consolidationPolicy: WhenEmpty
B) consolidateAfter: 0
C) budgets with schedule and nodes: "0"
D) weight: 0

<details>
<summary>答えを表示</summary>

**答え: C) budgets with schedule and nodes: "0"**

**解説:**
Karpenter の disruption budgets で schedule と `nodes: "0"` を指定すると、指定した time windows (通常は business hours) 中の node consolidation を完全に防止できます。

Configuration example:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m

  budgets:
  # No consolidation during business hours
  - nodes: "0"
    schedule: "0 9-17 * * 1-5"  # 9 AM to 5 PM, Mon-Fri
    duration: 8h

  # Allow 30% consolidation during off-peak
  - nodes: "30%"
```

Budget parameters:
- `nodes`: disrupt 可能な nodes の最大数/割合
- `schedule`: budget が適用されるタイミングの Cron expression
- `duration`: schedule が trigger された後に budget が active である期間

AI/ML でこれが重要な理由:
- GPU nodes は高価であり、disruption は cold starts を引き起こします
- node replacement 中に inference latency が急増します
- checkpointing が頻繁でない場合、training jobs は進捗を失う可能性があります
- business hours は通常 traffic が最も多い時間帯です

その他の consolidation settings:
- `consolidationPolicy: WhenEmpty`: 完全に empty な nodes のみを consolidate します
- `consolidationPolicy: WhenEmptyOrUnderutilized`: underutilized な nodes も consolidate します
- `consolidateAfter`: consolidation 前の delay (例: 5m)

</details>

### 12. Kubernetes で HuggingFace と NGC API keys を管理する推奨方法は何ですか？

A) Dockerfile に hardcode する
B) pod spec の environment variables として渡す
C) AWS Secrets Manager と External Secrets Operator を使用する
D) ConfigMap に保存する

<details>
<summary>答えを表示</summary>

**答え: C) AWS Secrets Manager と External Secrets Operator を使用する**

**解説:**
AWS Secrets Manager と External Secrets Operator (ESO) を使用すると、automatic rotation と auditing capabilities を備えた secure で centralized な secret management を提供できます。

ESO が推奨される理由:
1. **Centralized management**: Secrets を AWS Secrets Manager に保存します
2. **Automatic sync**: ESO が Kubernetes secrets を自動的に更新します
3. **Rotation support**: pods を redeploy せずに Secrets を rotate できます
4. **Audit trail**: AWS CloudTrail がすべての secret access を記録します
5. **IAM integration**: IRSA による fine-grained access control

Configuration example:
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: model-registry-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secretsmanager
    kind: ClusterSecretStore
  target:
    name: model-registry-credentials
  data:
  - secretKey: HUGGING_FACE_HUB_TOKEN
    remoteRef:
      key: ai-ml/huggingface-token
      property: token
  - secretKey: NGC_API_KEY
    remoteRef:
      key: ai-ml/ngc-api-key
      property: key
```

その他の選択肢に問題がある理由:
- **Hardcoded in Dockerfile**: Secrets が image layers に露出します
- **Environment variables in pod spec**: kubectl describe で表示されます
- **ConfigMap**: 暗号化されず、read access を持つ誰にでも表示されます

Security best practices:
- service account authentication に IRSA を使用します
- Secrets Manager で encryption at rest を有効にします
- least-privilege access policies を実装します
- secrets を定期的に rotate します

</details>

### 13. medium budget の 30B parameter model inference workload では、どの GPU instance type が最も適切ですか？

A) g5.xlarge (1x A10G, 24GB)
B) g5.4xlarge (1x A10G, 24GB)
C) g5.12xlarge (4x A10G, 96GB total)
D) p4d.24xlarge (8x A100, 640GB total)

<details>
<summary>答えを表示</summary>

**答え: C) g5.12xlarge (4x A10G, 96GB total)**

**解説:**
30B parameter model は FP16 inference で約 60GB の GPU memory (parameter あたり 2 bytes) を必要とするため、4x A10G GPUs (合計 96GB) を備えた g5.12xlarge が medium budget に適した選択肢です。

Memory calculation:
- 30B parameters x 2 bytes (FP16) = 最低 60GB
- KV cache overhead を含めると: ~70-80GB 推奨
- g5.12xlarge: 4 x 24GB = 96GB (余裕を持って十分)

Instance selection guide:

| Model Size | Memory Needed | Recommended Instance | Budget |
|------------|---------------|---------------------|--------|
| <7B | 14GB | g5.xlarge | Low |
| 7-13B | 26GB | g5.2xlarge | Low-Medium |
| 13-30B | 60GB | g5.4xlarge (quantized) or g5.12xlarge | Medium |
| **30B** | **60GB** | **g5.12xlarge (4x A10G)** | **Medium** |
| 30-70B | 140GB | g5.12xlarge + tensor parallel | Medium-High |
| >70B | 280GB+ | p4d.24xlarge | High |

30B に g5.12xlarge が適している理由:
- 4-way tensor parallelism により model を GPUs 全体に分散します
- 各 GPU は model weights の約 15GB を保持します
- 残りの memory を KV cache に利用できます
- inference では P4d より cost-effective です

P4d.24xlarge でも動作しますが、30B inference には過剰であり、かなり高価です。

</details>

### 14. memory pressure により system が requests を reject し始める可能性を示す vLLM metric はどれですか？

A) vllm:num_requests_running
B) vllm:time_to_first_token_seconds
C) vllm:gpu_cache_usage_perc
D) vllm:request_success_total

<details>
<summary>答えを表示</summary>

**答え: C) vllm:gpu_cache_usage_perc**

**解説:**
`vllm:gpu_cache_usage_perc` は KV (Key-Value) cache utilization を測定します。この metric が 100% に近づくと、attention states を保存するための memory がないため、vLLM は新しい requests を受け付けられません。

KV cache の重要性:
- 各 token の計算済み attention keys と values を保存します
- sequence length と batch size に応じて増加します
- full になると、vLLM は running requests を preempt するか、新しい requests を reject する必要があります

Alert configuration:
```yaml
- alert: vLLMKVCacheFull
  expr: vllm:gpu_cache_usage_perc > 0.95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "vLLM KV cache nearly full"
    description: "KV cache usage above 95%, requests may be rejected"
```

KV cache が full になった場合の対応:
1. `--max-num-seqs` (concurrent sequences) を減らす
2. `--max-model-len` (maximum sequence length) を減らす
3. chunked prefill を有効にする
4. horizontal scale (replicas を追加) する
5. より大きな GPU instances を使用する

その他の vLLM metrics:
- `vllm:num_requests_running`: 現在の concurrent requests
- `vllm:num_requests_waiting`: Queue depth
- `vllm:time_to_first_token_seconds`: TTFT latency
- `vllm:gpu_prefix_cache_hit_rate`: Caching efficiency

</details>

### 15. distributed training で cluster strategy の placement groups を使用する主な利点は何ですか？

A) EC2 instance costs の削減
B) Automatic load balancing
C) nodes 間の最低 network latency
D) GPU memory の増加

<details>
<summary>答えを表示</summary>

**答え: C) nodes 間の最低 network latency**

**解説:**
Cluster placement groups は、single Availability Zone 内で instances を物理的に近接配置し、inter-node communication の network latency を最小化し bandwidth を最大化します。

Cluster placement group の利点:
1. **Lowest latency**: 同じ network spine 上の instances
2. **Maximum bandwidth**: full bisection bandwidth を利用可能
3. **Consistent performance**: network jitter を削減
4. **EFA optimization**: 最高の EFA performance には cluster placement が必要です

Configuration:
```bash
# Create cluster placement group
aws ec2 create-placement-group \
  --group-name training-cluster-pg \
  --strategy cluster

# Karpenter configuration
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
spec:
  tags:
    aws:ec2:placement-group: training-cluster-pg
```

Placement group strategies:

| Strategy | Use Case | Latency | Availability |
|----------|----------|---------|--------------|
| **Cluster** | **Distributed training** | **Lowest** | **Single AZ** |
| Spread | High availability | Higher | Multi-AZ |
| Partition | Large deployments | Medium | Multi-rack |

training に cluster strategy を使用する理由:
- NCCL all-reduce operations は latency-sensitive です
- Gradient synchronization は頻繁に発生します (every batch)
- 小さな latency increase でも、数千の iterations にわたって影響が蓄積します
- P4d/P5 instances は cluster placement で最高の EFA performance を達成します

Trade-off: Cluster placement groups は single AZ に制限されるため、availability が低下します。training では次の理由から許容されます:
- Training jobs は checkpoint と restart が可能です
- Lower latency による training time の改善は redundancy のメリットを上回ります

</details>
