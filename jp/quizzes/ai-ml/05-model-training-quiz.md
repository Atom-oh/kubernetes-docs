# EKS での Model Training クイズ

このクイズでは、Distributed Training 戦略、Slurm/Slinky 統合、GPU および Trainium ベースのトレーニング、ストレージ設定、最適化手法など、Amazon EKS 上での Model Training に関する理解を確認します。

## クイズ問題

### 1. 1 つのレイヤーを複数の GPU に分割する Distributed Training 戦略はどれですか？

A) Data Parallelism
B) Tensor Parallelism
C) Pipeline Parallelism
D) Expert Parallelism

<details>
<summary>答えを表示</summary>

**解答: B) Tensor Parallelism**

**解説:**
Tensor Parallelism は、個々のレイヤー（attention layer や feed-forward network など）を複数の GPU に分割します。各 GPU はレイヤーの重みの一部を保持し、処理の該当部分を計算します。

**並列化戦略の比較:**

| 戦略 | 分散されるもの | 通信パターン |
|----------|---------------------|----------------------|
| Data Parallelism | トレーニングデータのバッチ | Gradient synchronization |
| Tensor Parallelism | 個々のレイヤー | レイヤー内通信 |
| Pipeline Parallelism | レイヤーのグループ（stage） | stage 間の activation 受け渡し |
| Expert Parallelism | MoE の expert network | token routing |

Tensor Parallelism は、大規模言語モデルの attention layer など、単一 GPU のメモリに収まらない非常に大きなレイヤーに特に有用です。

</details>

### 2. 2,000 億パラメータのモデルをトレーニングするために推奨される並列化戦略はどれですか？

A) Data Parallelism のみ
B) Tensor Parallelism のみ
C) Pipeline Parallelism のみ
D) 3D Parallelism (DP + TP + PP)

<details>
<summary>答えを表示</summary>

**解答: D) 3D Parallelism (DP + TP + PP)**

**解説:**
1,000 億パラメータを超えるモデルでは、最大効率を得るために 3D Parallelism が 3 つすべての戦略を組み合わせます。

- **Data Parallelism (DP)**: GPU のグループ全体にモデルを複製し、それぞれが異なるデータバッチを処理します
- **Tensor Parallelism (TP)**: ノード内で大きなレイヤーを分割します（通常は NVLink を備えた 8 GPU）
- **Pipeline Parallelism (PP)**: デバイスあたりのメモリを削減するため、レイヤーグループをノード間に分散します

64 個の A100 GPU 上で 200B モデルを実行する場合の設定例:
```
TP=8  (within each node)
PP=4  (across 4 nodes)
DP=2  (2 data parallel replicas)
Total: 8 × 4 × 2 = 64 GPUs
```

このアプローチには次の利点があります。
- 最大限のメモリ効率
- 計算と通信のバランス
- 単一ノードのメモリ容量を超えるモデルをトレーニングできる能力

</details>

### 3. Slinky のアーキテクチャで、ジョブのアカウンティングとクラスター状態を管理するコンポーネントはどれですか？

A) slurmctld
B) slurmdbd
C) slurmd
D) slurmrestd

<details>
<summary>答えを表示</summary>

**解答: B) slurmdbd**

**解説:**
Slinky/Slurm の各コンポーネントは、それぞれ異なる目的を持ちます。

| コンポーネント | 役割 | Kubernetes Resource |
|-----------|------|---------------------|
| **slurmctld** | 中央コントローラー - ジョブ、partition、リソース割り当てを管理します | StatefulSet |
| **slurmdbd** | データベース daemon - ジョブアカウンティング、使用量追跡、クラスター状態の永続化を処理します | MySQL/MariaDB を含む StatefulSet |
| **slurmd** | compute daemon - 各 worker node 上で実行され、ジョブステップを実行します | DaemonSet |
| **slurmrestd** | REST API - プログラムによるジョブ送信を可能にします | Deployment |

slurmdbd daemon は次の点で重要です。
- 過去のジョブデータを保存する
- アカウンティングのためにリソース使用量を追跡する
- 障害復旧のためにクラスター状態を維持する
- 過去の使用量に基づく fair-share scheduling をサポートする

</details>

### 4. Slinky が compute node group（partition）を定義するために使用する CRD はどれですか？

A) SlurmCluster
B) SlurmNodeSet
C) SlurmPartition
D) SlurmWorker

<details>
<summary>答えを表示</summary>

**解答: B) SlurmNodeSet**

**解説:**
Slinky は 2 つの主要な Custom Resource Definition を導入します。

1. **SlurmCluster**: 次を含むクラスター全体の設定を定義します。
   - Controller (slurmctld) 設定
   - Database (slurmdbd) 設定
   - REST API 設定
   - 共有ストレージ設定

2. **SlurmNodeSet**: 次を含む compute node group（partition）を定義します。
   - Instance type と GPU 設定
   - リソース割り当て（CPU、メモリ、GPU メモリ）
   - GRES (Generic Resource Scheduling) のためのノード機能
   - Karpenter 統合による autoscaling 設定
   - 低レイテンシーネットワークのための placement group 設定

SlurmNodeSet の例:
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

### 5. Distributed Training のために NCCL で EFA (Elastic Fabric Adapter) を有効化する環境変数はどれですか？

A) NCCL_EFA_ENABLE=1
B) FI_PROVIDER=efa
C) EFA_ENABLED=true
D) NCCL_NET=efa

<details>
<summary>答えを表示</summary>

**解答: B) FI_PROVIDER=efa**

**解説:**
Distributed Training のために NCCL で EFA ネットワークを有効化するには、いくつかの環境変数を設定する必要があります。

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

EFA は、対応する instance type（p4d、p5、trn1）で最大 400 Gbps のネットワーク帯域幅を提供し、Distributed Training における通信レイテンシーを大幅に削減します。

さらに、Pod は EFA デバイスをリクエストする必要があります。
```yaml
resources:
  limits:
    vpc.amazonaws.com/efa: 4  # Request 4 EFA devices
```

</details>

### 6. EKS 上で NVIDIA BioNeMo を使用する目的は何ですか？

A) GPU のモニタリングとメトリクス収集
B) 創薬と分子モデリング
C) コンテナネットワークの最適化
D) モデルの量子化と圧縮

<details>
<summary>答えを表示</summary>

**解答: B) 創薬と分子モデリング**

**解説:**
NVIDIA BioNeMo は、AI 駆動の創薬と分子モデリングのための専用フレームワークです。次を提供します。

**主な機能:**
- **MegaMolBART**: 分子生成と最適化
- **ESMFold**: タンパク質構造予測
- **DiffDock**: 分子ドッキング
- **NVIDIA Clara**: 創薬パイプライン

**EKS 上でのユースケース:**
- 新規医薬品候補の生成
- タンパク質-リガンド相互作用の予測
- 分子特性の最適化
- High-throughput virtual screening

**Deployment 要件:**
```yaml
resources:
  limits:
    nvidia.com/gpu: 8      # Multiple GPUs for large models
    memory: "500Gi"        # High memory for molecular datasets
```

BioNeMo は NVIDIA の GPU アクセラレーションを活用し、CPU ベースのアプローチと比較して computational chemistry ワークフローを劇的に高速化します。

</details>

### 7. Trainium 上の HuggingFace モデル向けに高レベルのトレーニング API を提供する Neuron SDK パッケージはどれですか？

A) torch-neuronx
B) tensorflow-neuronx
C) optimum-neuron
D) transformers-neuronx

<details>
<summary>答えを表示</summary>

**解答: C) optimum-neuron**

**解説:**
Neuron SDK には、目的の異なる複数のパッケージが含まれています。

| パッケージ | 目的 | レベル |
|---------|---------|-------|
| **torch-neuronx** | Core PyTorch integration | 低レベル |
| **tensorflow-neuronx** | Core TensorFlow integration | 低レベル |
| **transformers-neuronx** | transformers 向けに最適化された inference | 中レベル |
| **optimum-neuron** | 高レベルの training/inference API | 高レベル |

**optimum-neuron** は HuggingFace の Optimum ライブラリの一部で、次を提供します。
- `NeuronTrainer`: HuggingFace Trainer のドロップイン置き換え
- `NeuronTrainingArguments`: Neuron 固有のオプションを含むトレーニング設定
- 自動 tensor parallelism 設定
- Distributed Training との統合（ZeRO、pipeline parallelism）
- 標準 HuggingFace モデルとの checkpoint 互換性

使用例:
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

### 8. EKS 上で high-throughput な Distributed Training データアクセスに推奨されるストレージソリューションはどれですか？

A) Amazon EBS gp3
B) Amazon EFS
C) FSx for Lustre
D) Amazon S3 への直接アクセス

<details>
<summary>答えを表示</summary>

**解答: C) FSx for Lustre**

**解説:**
FSx for Lustre は、次の理由により Distributed ML Training に推奨されるストレージです。

**パフォーマンス特性:**
- 最大 1+ TB/s の aggregate throughput
- サブミリ秒レイテンシー
- HPC/ML workload 向けに最適化された並列ファイルシステム

**ML Training 向けの主な機能:**
- **S3 integration**: S3 data repository との自動データインポート/エクスポート
- **ReadWriteMany**: 複数の Pod が同時にアクセス可能
- **High IOPS**: トレーニングにおけるランダムアクセスパターンに重要
- **Checkpoint support**: トレーニング中の高速 checkpoint 書き込み

**比較:**

| ストレージ | スループット | アクセスモード | 最適な用途 |
|---------|------------|-------------|----------|
| FSx Lustre | 非常に高い | ReadWriteMany | トレーニングデータ、checkpoint |
| EFS | 中程度 | ReadWriteMany | 共有設定、モデル |
| EBS | 高い | ReadWriteOnce | 単一ノード workload |
| S3 | 可変 | Object | コールドデータ、アーカイブ |

設定例:
```yaml
lustreConfiguration:
  deploymentType: PERSISTENT_2
  perUnitStorageThroughput: 250  # MB/s per TiB
  dataRepositoryAssociations:
    - fileSystemPath: /data
      dataRepositoryPath: s3://bucket/training-data
```

</details>

### 9. `minAvailable: 4` の Volcano Job で、利用可能なノードが 3 つしかない場合はどうなりますか？

A) ジョブは 3 つの worker で開始します
B) ジョブは 4 つのノードが利用可能になるまで待機します
C) ジョブは即座に失敗します
D) ジョブは Karpenter に追加ノードをリクエストします

<details>
<summary>答えを表示</summary>

**解答: B) ジョブは 4 つのノードが利用可能になるまで待機します**

**解説:**
Volcano の `minAvailable` フィールドは **Gang Scheduling** を実装し、必要なすべての Pod がまとめてスケジュールされるか、まったくスケジュールされないことを保証します。

**Gang Scheduling の動作:**
- `minAvailable: 4` が設定されている場合、4 つすべての Pod が同時にスケジュール可能である必要があります
- リソースが利用可能になるまで、ジョブは pending 状態のままです
- Distributed Training における deadlock 状況を防ぎます
- 一貫したトレーニング環境を保証します

**これが ML Training で重要な理由:**
1. **Distributed Training にはすべての worker が必要**: 一部の worker だけではトレーニングを進められません
2. **Resource efficiency**: リソースを浪費する部分的な割り当てを防ぎます
3. **Deterministic behavior**: 期待される並列度でトレーニングを開始します

例:
```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
spec:
  minAvailable: 4  # Gang scheduling requirement
  tasks:
    - name: worker
      replicas: 4
```

Gang Scheduling がない場合、一部の worker が開始される一方で他が pending のままとなり、timeout やトレーニングジョブの失敗につながる可能性があります。

</details>

### 10. トレーニングで FP16 より BF16 (bfloat16) を使用する利点は何ですか？

A) より高い精度
B) loss scaling が不要
C) より小さいメモリフットプリント
D) より高速な計算

<details>
<summary>答えを表示</summary>

**解答: B) loss scaling が不要**

**解説:**
BF16 (Brain Floating Point 16) は FP32 と同じ指数範囲を持ちますが、仮数部の精度は低くなっています。

| フォーマット | 指数部ビット | 仮数部ビット | 範囲 |
|--------|--------------|---------------|-------|
| FP32 | 8 | 23 | 広い |
| FP16 | 5 | 10 | 限定的 |
| BF16 | 8 | 7 | 広い（FP32 と同じ） |

**BF16 が loss scaling を必要としない理由:**
- BF16 の 8 つの exponent bit は FP32 と同じ dynamic range を提供します
- FP16 の限られた範囲は、トレーニング中に underflow/overflow を引き起こします
- Loss scaling は FP16 での underflow を防ぐため、勾配を人工的に大きくします

**BF16 の利点:**
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

BF16 は次でサポートされています。
- NVIDIA A100、H100 GPU（Ampere 以降）
- AWS Trainium チップ
- Intel Sapphire Rapids CPU

</details>

### 11. トレーニング中に gradient checkpointing は何を実現しますか？

A) より高速な forward pass
B) 通信 overhead の削減
C) activation の再計算によるメモリ節約
D) モデル精度の向上

<details>
<summary>答えを表示</summary>

**解答: C) activation の再計算によるメモリ節約**

**解説:**
Gradient checkpointing（activation checkpointing とも呼ばれます）は、forward pass 中に activation を選択的に保存し、backpropagation 中にそれらを再計算することで、計算量と引き換えにメモリを節約します。

**仕組み:**
1. **checkpointing なし**: すべての activation がメモリに保存されます
2. **checkpointing あり**: checkpoint activation のみが保存され、中間 activation は backward pass 中に再計算されます

**メモリ節約:**
- activation メモリを O(n) から O(sqrt(n)) に削減します。ここで n はレイヤー数です
- 3〜4 倍大きい batch size でのトレーニングを可能にします
- 限られた GPU メモリで大規模モデルをトレーニングするために重要です

**PyTorch での設定:**
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

**トレードオフ:**
- 計算時間が約 30% 増加
- activation メモリが 3〜4 倍削減
- より大きなモデル/バッチのトレーニングが可能

</details>

### 12. optimizer state と model parameter の両方を CPU メモリに offload する DeepSpeed ZeRO stage はどれですか？

A) ZeRO Stage 1
B) ZeRO Stage 2
C) ZeRO Stage 3
D) ZeRO Stage 0

<details>
<summary>答えを表示</summary>

**解答: C) ZeRO Stage 3**

**解説:**
DeepSpeed ZeRO (Zero Redundancy Optimizer) は、stage が進むにつれてメモリの冗長性を段階的に削減します。

| Stage | 分割対象 | CPU Offload の可否 |
|-------|------------|----------------------|
| Stage 0 | なし（baseline） | なし |
| Stage 1 | Optimizer states | Optimizer states |
| Stage 2 | Optimizer states + Gradients | Optimizer states |
| Stage 3 | Optimizer states + Gradients + Parameters | optimizer と parameter の両方 |

**ZeRO Stage 3 設定:**
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

**ZeRO-3 を使用する場合:**
- GPU メモリより大きなモデルをトレーニングする場合
- 最大限のメモリ効率が必要な場合
- メモリのためにある程度の速度低下を受け入れられる場合

**メモリ削減（概算）:**
- Stage 1: 4 倍削減
- Stage 2: 8 倍削減
- Stage 3: GPU 数に応じた線形スケーリング（理論上は無制限）

</details>

### 13. MPIJob specification における `slotsPerWorker` フィールドの目的は何ですか？

A) worker あたりの CPU core 数
B) worker あたりの GPU device 数
C) worker あたりの MPI process 数
D) worker あたりの network interface 数

<details>
<summary>答えを表示</summary>

**解答: C) worker あたりの MPI process 数**

**解説:**
MPIJob では、`slotsPerWorker` は各 worker pod が実行する MPI rank（process）の数を定義します。

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
この例では、8 × 4 = 32 MPI process です。

**一般的な設定:**
- `slotsPerWorker` をノードあたりの GPU 数と同じに設定します
- 各 MPI rank は通常 1 つの GPU を担当します
- 8-GPU ノードの場合: `slotsPerWorker: 8`

**Launcher command の例:**
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

これにより、各 GPU がちょうど 1 つの MPI process に割り当てられ、GPU の競合を避けながら並列度を最大化できます。

</details>

### 14. 長時間実行されるトレーニングジョブに推奨される checkpoint 頻度戦略はどれですか？

A) epoch ごとにのみ checkpoint を取得する
B) 最大限の安全性のために step ごとに checkpoint を取得する
C) N step ごとに checkpoint を取得し、直近 3〜5 個の checkpoint を保持する
D) トレーニング速度を最大化するために checkpoint を取得しない

<details>
<summary>答えを表示</summary>

**解答: C) N step ごとに checkpoint を取得し、直近 3〜5 個の checkpoint を保持する**

**解説:**
最適な checkpoint 戦略は、復旧能力とストレージコスト、トレーニングの overhead のバランスを取ります。

**推奨アプローチ:**
```yaml
checkpoint:
  save_steps: 500           # Save every 500 steps
  save_total_limit: 5       # Keep only last 5 checkpoints
  save_on_each_node: false  # Save from rank 0 only
```

**この戦略の理由:**
1. **Recovery granularity**: データ損失を最大で約 500 step に制限します
2. **Storage efficiency**: 3〜5 個の checkpoint を保持することで storage bloat を防ぎます
3. **Training overhead**: 毎 step の checkpoint は遅すぎます
4. **Epoch-only is risky**: 長い epoch は障害時に大きなデータ損失を意味します

**Checkpoint size considerations:**
- 大規模モデル（70B+）: 各 checkpoint は 100〜200GB になる場合があります
- 5 checkpoint = 500GB〜1TB のストレージ
- 古い checkpoint には S3 lifecycle policy を使用します

**Best practices:**
```python
training_args = TrainingArguments(
    save_strategy="steps",
    save_steps=500,
    save_total_limit=5,
    save_safetensors=True,  # Faster, safer format
)
```

本番トレーニングでは、checkpoint manager sidecar を使って checkpoint を耐久性のあるストレージ（S3）にも同期します。

</details>

### 15. GPU training Pod が最適な EFA パフォーマンスのために単一の Availability Zone にスケジュールされることを保証する Karpenter 設定はどれですか？

A) `consolidationPolicy: WhenEmpty`
B) 単一の値を持つ `topology.kubernetes.io/zone` requirement
C) `karpenter.sh/capacity-type: spot`
D) `disruption.budgets.nodes: "0"`

<details>
<summary>答えを表示</summary>

**解答: B) 単一の値を持つ `topology.kubernetes.io/zone` requirement**

**解説:**
EFA (Elastic Fabric Adapter) では、通信するすべてのインスタンスが同じ Availability Zone にある必要があります。Karpenter の zone requirement はこれを保証します。

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

**EFA で単一 AZ が重要な理由:**
- EFA は高帯域幅・低レイテンシー通信のために AWS のカスタム network interface を使用します
- Cross-AZ communication では EFA の RDMA 機能を使用できません
- AZ 間ではネットワークレイテンシーが大幅に増加します

**他の選択肢の説明:**
- A) `consolidationPolicy`: ノード統合を制御するもので、配置ではありません
- C) `capacity-type: spot`: 価格モデルを決定するもので、zone ではありません
- D) `disruption.budgets`: ノードの中断を防ぐもので、zone 選択ではありません

**GPU training の完全な設定:**
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

## まとめ

このクイズでは、EKS 上での Model Training に関する重要な概念を扱いました。

1. **Distributed Training Strategies**: data、tensor、pipeline、expert parallelism
2. **Slinky/Slurm Integration**: コンポーネント（slurmctld、slurmdbd、slurmd）と CRD
3. **GPU Training**: NCCL 設定、EFA ネットワーク、BioNeMo
4. **Trainium Training**: Neuron SDK パッケージ、optimum-neuron
5. **Storage**: high-throughput training のための FSx for Lustre
6. **Scheduling**: Volcano gang scheduling
7. **Optimization**: mixed precision（BF16）、gradient checkpointing、DeepSpeed ZeRO
8. **Infrastructure**: Karpenter NodePool、checkpoint 管理

詳細については、[EKS での Model Training](../../ai-ml/05-model-training.md) ドキュメントを参照してください。
