# EKS 上の AI Infrastructure クイズ

このクイズでは、JARK Stack、Dynamic Resource Allocation、AI workloads 向けの本番プラットフォームなど、Amazon EKS 上の AI/ML infrastructure patterns に関する理解を確認します。

## クイズ問題

### 1. EKS 上の AI/ML infrastructure の文脈で、JARK Stack は何を表しますか？

A) Java, Ansible, Redis, Kafka
B) JupyterHub, Argo Workflows, Ray, Karpenter
C) Jenkins, Airflow, RabbitMQ, Kubernetes
D) JupyterLab, Apache Spark, Ray, Kubeflow

<details>
<summary>答えを表示</summary>

**解答: B) JupyterHub, Argo Workflows, Ray, Karpenter**

**解説:**
JARK Stack は、EKS 上の完全な AI/ML development environment であり、次で構成されます。

- **JupyterHub**: GPU 対応 notebook profile を備えた multi-user interactive development environment
- **Argo Workflows**: DAG ベースの workflow による ML pipeline orchestration
- **Ray (KubeRay)**: training、tuning、serving のための統合 distributed computing
- **Karpenter**: GPU と Neuron support を備えた高速で費用対効果の高い node provisioning

この stack は、data scientist と ML engineer が Kubernetes 上で ML model を開発、トレーニング、デプロイするために必要なものをすべて提供します。

</details>

### 2. Enterprise environment で EKS 上の JupyterHub とともに一般的に使用される authentication method はどれですか？

A) ConfigMaps に保存された基本的な username/password
B) SSH key ベースの authentication
C) OAuth を使用した Amazon Cognito
D) Kubernetes ServiceAccount tokens

<details>
<summary>答えを表示</summary>

**解答: C) OAuth を使用した Amazon Cognito**

**解説:**
OAuth を使用した Amazon Cognito は、enterprise environment の EKS 上の JupyterHub に推奨される authentication method です。理由は次のとおりです。

1. **Single Sign-On (SSO)**: corporate identity provider (SAML, OIDC) と統合します
2. **Multi-factor Authentication**: security を強化するための MFA をサポートします
3. **User Management**: user management と access control を一元化します
4. **Scalability**: user base に合わせて scale する managed service です
5. **Compliance**: security compliance 要件を満たすのに役立ちます

設定例:
```python
c.JupyterHub.authenticator_class = 'oauthenticator.generic.GenericOAuthenticator'
c.GenericOAuthenticator.oauth_callback_url = 'https://jupyter.example.com/hub/oauth_callback'
c.GenericOAuthenticator.authorize_url = 'https://your-domain.auth.us-west-2.amazoncognito.com/oauth2/authorize'
```

</details>

### 3. Kubernetes 上の Ray において、Ray Head node の目的は何ですか？

A) すべての training data と model weights を保存すること
B) cluster を調整し、dashboard を実行し、worker scheduling を管理すること
C) すべての GPU computations を排他的に実行すること
D) external API requests のみを処理すること

<details>
<summary>答えを表示</summary>

**解答: B) cluster を調整し、dashboard を実行し、worker scheduling を管理すること**

**解説:**
Ray Head node は、Ray cluster の中央 coordinator として機能します。

1. **Global Control Store (GCS)**: cluster metadata と state を管理します
2. **Dashboard**: monitoring と debugging のために Ray dashboard を実行します (port 8265)
3. **Client Connections**: Ray clients からの接続を受け付けます (port 10001)
4. **Scheduling**: worker 全体で task と actor の scheduling を調整します
5. **Autoscaling**: KubeRay autoscaler と連携して worker group を scale します

Head node は通常、compute-intensive workloads 自体を実行しません。これらは resource requirements (CPU, GPU, memory) に基づいて worker nodes に分散されます。

```yaml
headGroupSpec:
  rayStartParams:
    dashboard-host: '0.0.0.0'
    block: 'true'
```

</details>

### 4. GPU scheduling において、従来の Kubernetes device plugins に対する Dynamic Resource Allocation (DRA) の主な利点は何ですか？

A) DRA は GPU hardware の検出がより高速である
B) DRA は細粒度の GPU sharing (MIG, MPS, time-slicing) と topology-aware scheduling を可能にする
C) DRA は memory overhead が少ない
D) DRA は NVIDIA GPUs でのみ動作する

<details>
<summary>答えを表示</summary>

**解答: B) DRA は細粒度の GPU sharing (MIG, MPS, time-slicing) と topology-aware scheduling を可能にする**

**解説:**
Dynamic Resource Allocation (DRA) は、従来の device plugins では提供できない capabilities を提供します。

| Feature | Traditional Device Plugin | DRA |
|---------|--------------------------|-----|
| GPU Allocation | GPU 全体のみ | Fractional (MIG, MPS, time-slice) |
| Topology Awareness | 限定的 | NVLink/IMEX aware |
| Sharing Modes | 基本的な time-slicing | MIG, MPS, time-slicing, exclusive |
| Resource Claims | Static | constraints 付きの Dynamic |
| Multi-GPU Scheduling | Independent | Topology-constrained |

DRA は ResourceClaims と ResourceSlices を使用して次を提供します。
- 細粒度の GPU memory partitioning (3g.20gb などの MIG profiles)
- MPS による CUDA context sharing
- development workloads 向けの time-slicing
- NVLink 接続された GPUs 向けの topology-aware scheduling

これは、72 個の相互接続された GPUs を持つ P6e-GB200 UltraServers に不可欠です。

</details>

### 5. Workload 間で最も強い isolation を提供する GPU sharing strategy はどれですか？

A) Time-Slicing
B) MPS (Multi-Process Service)
C) MIG (Multi-Instance GPU)
D) Exclusive mode

<details>
<summary>答えを表示</summary>

**解答: C) MIG (Multi-Instance GPU)**

**解説:**
GPU sharing strategies の中で、MIG は sharing を許可しながら最も強い isolation を提供します。

| Strategy | Isolation Level | How It Works |
|----------|----------------|--------------|
| **Exclusive** | Full (sharing なし) | GPU あたり 1 workload |
| **MIG** | Strong (hardware) | hardware-partitioned GPU instances |
| **MPS** | Medium | thread limits 付きの shared CUDA context |
| **Time-Slicing** | Weak | workloads 間の context switching |

MIG (A100/H100 GPUs で利用可能) は次を提供します。
- **Hardware Isolation**: 各 MIG instance は専用の SM units、memory、cache を持ちます
- **Fault Isolation**: 1 つの instance の error は他に影響しません
- **QoS Guarantees**: instance ごとに予測可能な performance
- **Memory Protection**: 分離された memory spaces により data leakage を防止します

A100 80GB の MIG profiles 例:
- `7g.80gb` - Full GPU
- `3g.40gb` - Half GPU (2 instances)
- `1g.10gb` - 1/7 GPU (7 instances)

</details>

### 6. 完全な DRA support に必要な NVIDIA GPU Operator の最小 version はどれですか？

A) v22.9.0
B) v23.6.0
C) v24.3.0
D) v25.3.0

<details>
<summary>答えを表示</summary>

**解答: D) v25.3.0**

**解説:**
完全な Dynamic Resource Allocation (DRA) support には、NVIDIA GPU Operator v25.3.0 以降が必要です。この version には次が含まれます。

1. **DRA Driver**: GPU resource management のための native DRA driver
2. **ResourceSlice Support**: GPU topology information を公開します
3. **Sharing Configuration**: DRA 経由の MIG、MPS、time-slicing
4. **CEL Expressions**: Common Expression Language を使用した device selection

DRA を有効にした設定:
```yaml
draDriver:
  enabled: true
  version: "v0.1.0"
  config:
    sharing:
      mps:
        enabled: true
      timeSlicing:
        enabled: true
      mig:
        enabled: true
        strategy: mixed
```

以前の versions は、DRA が提供する細粒度の control なしで、従来の device plugin mode のみをサポートします。

</details>

### 7. Agents on EKS platform において、Langfuse の目的は何ですか？

A) embeddings を保存するための vector database
B) Source control と CI/CD pipelines
C) LLM observability、tracing、monitoring
D) Tool discovery と registration

<details>
<summary>答えを表示</summary>

**解答: C) LLM observability、tracing、monitoring**

**解説:**
Langfuse は、次を提供する open-source LLM observability platform です。

1. **Tracing**: LLM interactions の end-to-end traces
2. **Prompt Management**: prompt の version 管理と管理
3. **Evaluation**: LLM outputs の scoring と evaluation
4. **Analytics**: usage metrics、latency、cost tracking
5. **Debugging**: LLM chains と agents の問題を特定します

Agents on EKS platform architecture では次のようになります。
- **GitLab**: Source control と CI/CD
- **Langfuse**: LLM observability と tracing
- **Milvus**: RAG のための vector database
- **MCP Gateway**: Tool discovery と registration

統合例:
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-xxx",
    secret_key="sk-xxx",
    host="https://langfuse.agents.example.com"
)

# Trace LLM calls
trace = langfuse.trace(name="customer-support-agent")
```

</details>

### 8. EKS 上の high-throughput distributed training workloads に推奨される storage solution はどれですか？

A) Amazon EBS gp3 volumes
B) standard performance mode の Amazon EFS
C) Amazon FSx for Lustre
D) Mountpoint を使用した Amazon S3

<details>
<summary>答えを表示</summary>

**解答: C) Amazon FSx for Lustre**

**解説:**
Amazon FSx for Lustre は、high-throughput distributed training に推奨される storage solution です。理由は次のとおりです。

1. **High Throughput**: storage 1 TiB あたり最大 1000+ MB/s
2. **Low Latency**: metadata operations 向けの sub-millisecond latencies
3. **S3 Integration**: S3 との native data repository integration
4. **Parallel Access**: parallel file system workloads 向けに最適化されています
5. **POSIX Compliance**: ML frameworks 向けの完全な POSIX support

AI/ML 向け storage 比較:

| Storage | Throughput | Use Case |
|---------|------------|----------|
| EFS | 最大 10 GB/s | shared notebooks、model storage |
| FSx Lustre | 最大 1+ TB/s | Distributed training、HPC |
| S3 + Mountpoint | Variable | cold data、checkpoints |
| EBS gp3 | 最大 1 GB/s | Single-node workloads |

FSx for Lustre の設定:
```yaml
parameters:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: "500"  # MB/s per TiB
  dataCompressionType: LZ4
  s3ImportPath: s3://ml-datasets
```

</details>

### 9. AI/ML workloads において EFA (Elastic Fabric Adapter) は何に使用されますか？

A) GPU nodes 上の保存データを暗号化すること
B) multi-node distributed training のための high-bandwidth、low-latency networking
C) GPU memory allocation を管理すること
D) workloads を external services に認証すること

<details>
<summary>答えを表示</summary>

**解答: B) multi-node distributed training のための high-bandwidth、low-latency networking**

**解説:**
Elastic Fabric Adapter (EFA) は、HPC と ML workloads 向けの AWS の high-performance network interface です。

1. **High Bandwidth**: 最大 3200 Gbps (16x EFA を備えた trn1n.32xlarge)
2. **Low Latency**: collective operations 向けの一貫した low-latency
3. **OS Bypass**: kernel を bypass する direct hardware access
4. **NCCL Integration**: NVIDIA Collective Communications Library 向けに最適化されています

AI/ML 向け EFA-supported instances:
- `p4d.24xlarge`: 4x 400 Gbps EFA
- `p5.48xlarge`: 32x 400 Gbps EFA
- `trn1.32xlarge`: 8x 800 Gbps EFA
- `trn1n.32xlarge`: 16x 1600 Gbps EFA

NCCL と EFA を使用するための environment variables:
```yaml
env:
- name: FI_PROVIDER
  value: "efa"
- name: FI_EFA_USE_DEVICE_RDMA
  value: "1"
- name: NCCL_ALGO
  value: "Ring,Tree"
```

Resource request:
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4
```

</details>

### 10. 即時対応が必要な GPU memory exhaustion を示す Prometheus metric はどれですか？

A) DCGM_FI_DEV_GPU_UTIL > 80
B) DCGM_FI_DEV_GPU_TEMP > 70
C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95
D) DCGM_FI_DEV_SM_CLOCK < 1000

<details>
<summary>答えを表示</summary>

**解答: C) DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) > 0.95**

**解説:**
この metric は GPU frame buffer (memory) utilization percentage を計算します。95% を超えると、GPU はほぼ memory を使い切っています。

GPU monitoring の主要な DCGM metrics:

| Metric | Description | Critical Threshold |
|--------|-------------|-------------------|
| `DCGM_FI_DEV_FB_USED` | 使用済み frame buffer memory | - |
| `DCGM_FI_DEV_FB_FREE` | 空き frame buffer memory | - |
| `DCGM_FI_DEV_GPU_UTIL` | GPU compute utilization | <20% (underutilized) |
| `DCGM_FI_DEV_GPU_TEMP` | GPU temperature | >85C (overheating) |
| `DCGM_FI_DEV_XID_ERRORS` | hardware error count | >0 (hardware issue) |

memory exhaustion の alert rule:
```yaml
- alert: GPUMemoryExhausted
  expr: (DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100 > 95
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "GPU memory nearly exhausted"
```

memory exhaustion の原因:
- OOM (Out of Memory) errors
- Training job failures
- Inference request rejections

</details>

### 11. GPU workloads に対する Karpenter の consolidation feature の目的は何ですか？

A) 複数の GPUs を単一の virtual GPU に merge すること
B) training checkpoints を単一の file に combine すること
C) workloads を bin-pack し、cost savings のために underutilized nodes を削除すること
D) 複数の GPU pods から logs を consolidate すること

<details>
<summary>答えを表示</summary>

**解答: C) workloads を bin-pack し、cost savings のために underutilized nodes を削除すること**

**解説:**
Karpenter の consolidation feature は、次により cluster costs を最適化します。

1. **Bin-Packing**: workloads をより少ない、より利用率の高い nodes に移動します
2. **Node Removal**: 空または underutilized nodes を終了します
3. **Right-Sizing**: nodes をより適切な instance types に置き換えます
4. **Cost Reduction**: idle GPU resources を最小化します

Consolidation policies:
```yaml
disruption:
  consolidationPolicy: WhenEmptyOrUnderutilized
  consolidateAfter: 5m
```

- **WhenEmpty**: 完全に空の nodes のみを consolidate します
- **WhenEmptyOrUnderutilized**: 空または underused nodes を consolidate します

GPU workloads では、consolidation は重要です。理由は次のとおりです。
- GPU instances は高価です ($3-30+/hour)
- Underutilized GPUs は大きな cost の無駄になります
- Training jobs は完了することが多く、idle nodes が残ります

Best practices:
- development では短めの `consolidateAfter` を使用します (5m)
- production training では長めの期間を使用します (30m)
- runaway scaling を防ぐために適切な `limits` を設定します

</details>

### 12. DRA において ResourceSlice は何に使用されますか？

A) containers 間で CPU resources を分割すること
B) node 上で利用可能な GPU resources とその topology を表すこと
C) 異なる workloads のために network bandwidth を slice すること
D) storage volumes を partition すること

<details>
<summary>答えを表示</summary>

**解答: B) node 上で利用可能な GPU resources とその topology を表すこと**

**解説:**
ResourceSlice は、利用可能な devices とその topology を表す DRA resource です。

```yaml
apiVersion: resource.k8s.io/v1alpha3
kind: ResourceSlice
metadata:
  name: gb200-nvl72-node-1
spec:
  nodeName: p6e-gb200-node-1
  pool:
    name: gb200-pool
    generation: 1
    resourceSliceCount: 1
  driver: gpu.nvidia.com
  devices:
  - name: gpu-0
    basic:
      attributes:
        gpu.nvidia.com/product: "NVIDIA-GB200"
        gpu.nvidia.com/memory: "192Gi"
        gpu.nvidia.com/nvlink.version: "5.0"
        gpu.nvidia.com/nvswitch.connected: "true"
```

ResourceSlice は次を提供します。
1. **Device Inventory**: node 上の利用可能な devices をすべて一覧表示します
2. **Attributes**: GPU model、memory、capabilities
3. **Topology Information**: NVLink connections、NUMA node、NVSwitch
4. **Capacity**: scheduling に利用可能な resources

scheduler は ResourceSlices を使用して次を行います。
- 必要な GPU types を持つ nodes を見つける
- topology-aware multi-GPU workloads を schedule する
- NVLink 接続された GPUs が一緒に割り当てられることを保証する

</details>

### 13. Agents on EKS platform のどの component が RAG (Retrieval-Augmented Generation) 向けの vector storage を提供しますか？

A) GitLab
B) Langfuse
C) Milvus
D) MCP Gateway

<details>
<summary>答えを表示</summary>

**解答: C) Milvus**

**解説:**
Milvus は、AI applications 向けに最適化された open-source vector database です。

1. **Vector Storage**: high-dimensional embedding vectors を保存します
2. **Similarity Search**: 高速な approximate nearest neighbor (ANN) search
3. **GPU Acceleration**: query nodes と index nodes は GPUs を使用できます
4. **Scalability**: large-scale deployments 向けの distributed architecture

Milvus を使用した RAG architecture:
```
User Query → Embedding Model → Milvus (vector search) → Retrieved Context → LLM → Response
```

EKS 上の Milvus 設定:
```yaml
queryNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU-accelerated search

indexNode:
  replicas: 2
  resources:
    requests:
      nvidia.com/gpu: "1"  # GPU-accelerated indexing
```

Agent integration:
```python
from pymilvus import connections, Collection

connections.connect(host="milvus.milvus.svc.cluster.local", port="19530")
collection = Collection("knowledge_base")

# Search for similar documents
results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param={"metric_type": "IP", "params": {"nprobe": 10}},
    limit=5
)
```

</details>

### 14. Distributed training 中の GPU node failures を処理するための推奨アプローチは何ですか？

A) training を最初から手動で restart する
B) Ray Train のような fault-tolerant training frameworks と checkpointing を使用する
C) failures を防ぐために GPU replicas の数を増やす
D) interruptions を避けるために on-demand instances のみを使用する

<details>
<summary>答えを表示</summary>

**解答: B) Ray Train のような fault-tolerant training frameworks と checkpointing を使用する**

**解説:**
fault-tolerant frameworks と checkpointing が推奨されるアプローチである理由は次のとおりです。

1. **Automatic Recovery**: training は最後の checkpoint から再開します
2. **Cost Efficiency**: より安価な Spot instances の使用を可能にします
3. **Scalability**: 動的な cluster size changes に対応します
4. **Progress Preservation**: lost compute time を最小化します

checkpointing を使用した Ray Train:
```python
from ray.train.torch import TorchTrainer
from ray.train import Checkpoint, ScalingConfig

def train_loop_per_worker():
    # Load from checkpoint if available
    checkpoint = ray.train.get_checkpoint()
    if checkpoint:
        with checkpoint.as_directory() as checkpoint_dir:
            model.load_state_dict(torch.load(f"{checkpoint_dir}/model.pt"))

    for epoch in range(epochs):
        # Training logic
        train_epoch()

        # Save checkpoint
        with tempfile.TemporaryDirectory() as temp_dir:
            torch.save(model.state_dict(), f"{temp_dir}/model.pt")
            ray.train.report(
                {"loss": loss},
                checkpoint=Checkpoint.from_directory(temp_dir)
            )

trainer = TorchTrainer(
    train_loop_per_worker,
    scaling_config=ScalingConfig(
        num_workers=4,
        use_gpu=True,
    ),
    run_config=ray.train.RunConfig(
        checkpoint_config=ray.train.CheckpointConfig(
            num_to_keep=3,
            checkpoint_frequency=10,
        )
    )
)
```

</details>

### 15. Agents on EKS platform における MCP Gateway の目的は何ですか？

A) microservices 間の traffic を route すること
B) container image registries を管理すること
C) AI agents のための tool discovery と registration を提供すること
D) pods 間の communication を暗号化すること

<details>
<summary>答えを表示</summary>

**解答: C) AI agents のための tool discovery と registration を提供すること**

**解説:**
MCP (Model Context Protocol) Gateway は、AI agents のための tool discovery と management を提供します。

1. **Tool Registry**: 利用可能な tools/functions の central registry
2. **Discovery**: Kubernetes 内の tools の automatic discovery
3. **Routing**: tool calls を適切な backends に route します
4. **Authentication**: OIDC ベースの access control
5. **Rate Limiting**: tool abuse を防止します

MCP Gateway configuration:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-gateway-config
data:
  config.yaml: |
    registry:
      type: kubernetes
      kubernetes:
        namespace: mcp-tools
        label_selector: "mcp.anthropic.com/tool=true"

    discovery:
      enabled: true
      interval: 30s
      endpoints:
      - name: kubernetes
        type: kubernetes
        config:
          namespaces: ["mcp-tools", "ai-agents"]
```

Agent integration:
```python
# Agent discovers and uses tools via MCP Gateway
env:
- name: MCP_GATEWAY_URL
  value: "http://mcp-gateway.mcp-gateway.svc.cluster.local:8080"
```

MCP により、agents は次を行えます。
- 利用可能な tools を動的に discover する
- external APIs と services を call する
- databases と file systems に access する
- code と commands を execute する

</details>

---

## まとめ

このクイズでは、EKS 上の AI infrastructure における主要な concepts を取り上げました。

- **JARK Stack**: 完全な ML environments のための JupyterHub + Argo Workflows + Ray + Karpenter
- **Dynamic Resource Allocation**: MIG、MPS、time-slicing による細粒度の GPU scheduling
- **Agents Platform**: AI agent development のための GitLab + Langfuse + Milvus + MCP Gateway
- **Storage**: sharing には EFS、high-throughput training には FSx Lustre
- **Networking**: multi-node distributed training のための EFA
- **Monitoring**: GPU observability のための DCGM metrics と Prometheus alerts

詳細については、[AI Infrastructure on EKS](../../ai-ml/06-ai-infrastructure.md) documentation を参照してください。
