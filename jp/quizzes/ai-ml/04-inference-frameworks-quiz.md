# 推論フレームワーククイズ

このクイズでは、NVIDIA NIM、NVIDIA Dynamo、AIBrix、Ray Serve、AWS Neuron など、Kubernetes デプロイ向けの LLM 推論フレームワークに関する理解を確認します。

## クイズの問題

### 1. LLM デプロイにおける NVIDIA NIM の主な利点は何ですか？

A) オープンソースモデルのみをサポートする
B) 最適化された推論エンジンと OpenAI 互換 API を備えた、本番対応のコンテナ化された LLM デプロイを提供する
C) すべてのモデルを手動でコンパイルする必要がある
D) CPU インスタンスでのみ動作する

<details>
<summary>回答を表示</summary>

**回答: B) 最適化された推論エンジンと OpenAI 互換 API を備えた、本番対応のコンテナ化された LLM デプロイを提供する**

**解説:**
NVIDIA NIM (NVIDIA Inference Microservices) は、いくつかの主要機能を備えた、本番対応のコンテナ化された LLM デプロイを提供します。

1. **最適化された推論エンジン**: 最高のパフォーマンスを実現するために TensorRT-LLM を使用する
2. **OpenAI 互換 API**: OpenAI API 呼び出しのドロップイン置き換え
3. **組み込みモニタリング**: Prometheus メトリクスと Grafana ダッシュボード
4. **NGC Catalog 連携**: 事前最適化済みモデルへ簡単にアクセス
5. **エンタープライズサポート**: NVIDIA による本番環境向け SLA とサポート

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

### 2. NVIDIA Dynamo における「disaggregated serving」とは何ですか？

A) 1つの GPU 上で複数のモデルを実行すること
B) prefill（プロンプト処理）フェーズと decode（トークン生成）フェーズを異なるワーカープールに分離すること
C) 複数のサーバーにログを分散すること
D) GPU なしで推論を実行すること

<details>
<summary>回答を表示</summary>

**回答: B) prefill（プロンプト処理）フェーズと decode（トークン生成）フェーズを異なるワーカープールに分離すること**

**解説:**
Disaggregated serving は、LLM 推論の2つの主要フェーズを分離する NVIDIA Dynamo の重要なアーキテクチャパターンです。

1. **Prefill フェーズ**:
   - 入力プロンプトを処理する
   - 計算集約型（高い FLOPs が必要）
   - A100 のようなハイエンド GPU の恩恵を受ける

2. **Decode フェーズ**:
   - 出力トークンを1つずつ生成する
   - メモリ帯域幅集約型
   - A10G のような、よりコスト効率の高い GPU を使用できる

**分離の利点:**
- リソース使用率の向上
- 異種 GPU 利用によるコスト最適化
- 全体スループットの向上
- prefill と decode のキャパシティを独立してスケーリング可能

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

### 3. AIBrix のどのコンポーネントが動的な LoRA アダプターのロードと管理を処理しますか？

A) Gateway
B) Autoscaler
C) LoRA Manager
D) Model Registry

<details>
<summary>回答を表示</summary>

**回答: C) LoRA Manager**

**解説:**
AIBrix は複数の主要コンポーネントで構成され、それぞれに特定の責任があります。

1. **Gateway**: インテリジェントなリクエストルーティングとロードバランシング
2. **LoRA Manager**: 動的な LoRA アダプターのロードと管理
3. **Autoscaler**: 推論 Pod 向けのワークロード対応 autoscaling
4. **Model Registry**: モデルとアダプターの一元管理

**LoRA Manager** は具体的に次を処理します。
- 再起動なしでの LoRA アダプターの動的ロード
- 異なるアダプター間のホットスワップ
- 複数アダプターのメモリ管理
- アダプターのバージョニングとライフサイクル

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

### 4. 分散推論のために Ray Serve をデプロイする際に使用される Kubernetes operator は何ですか？

A) NVIDIA GPU Operator
B) KubeRay Operator
C) Prometheus Operator
D) Flux Operator

<details>
<summary>回答を表示</summary>

**回答: B) KubeRay Operator**

**解説:**
KubeRay Operator は、分散推論向けの Ray Serve を含む Ray クラスターをデプロイおよび管理するための Kubernetes-native な方法です。

**KubeRay Operator の機能:**
- Ray クラスターのライフサイクルを管理する
- RayCluster、RayJob、RayService CRD をサポートする
- Ray worker の auto-scaling を処理する
- Kubernetes RBAC とネットワーキングに統合する

**インストール:**
```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace
```

**RayService の例:**
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

### 5. LLM 推論に AWS Inferentia2 (inf2) インスタンスを使用する主な利点は何ですか？

A) A100 よりも大きな GPU メモリ
B) GPU インスタンスと比較して最大 70% 低いコスト
C) より高速なモデルコンパイル時間
D) トレーニングワークロードのより優れたサポート

<details>
<summary>回答を表示</summary>

**回答: B) GPU インスタンスと比較して最大 70% 低いコスト**

**解説:**
AWS Inferentia2 は、推論ワークロードに大きなコスト上の利点を提供します。

**コスト上の利点:**
- 同等の GPU インスタンスに対して最大 70% 低いコスト
- ドルあたりの高いスループット
- 推論専用ワークロードに効率的

**サポートされるモデル:**
- Llama 2/3
- Mistral
- Stable Diffusion
- さまざまなエンコーダーモデル

**Instance Types:**
| Instance | Neuron Cores | Memory | Use Case |
|----------|--------------|--------|----------|
| inf2.xlarge | 2 | 32 GB | 7B models |
| inf2.24xlarge | 6 | 96 GB | 13B-70B models |
| inf2.48xlarge | 12 | 192 GB | 70B+ models |

**トレードオフ:**
- Neuron 向けのモデルコンパイルが必要
- GPU と比較してモデルサポートが限定的
- 初期セットアップ時間が長い

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

### 6. LLM 推論で最初のトークンが生成されるまでの時間を測定するメトリクスは何ですか？

A) ITL (Inter-Token Latency)
B) TTFT (Time to First Token)
C) TPS (Tokens Per Second)
D) QPS (Queries Per Second)

<details>
<summary>回答を表示</summary>

**回答: B) TTFT (Time to First Token)**

**解説:**
TTFT (Time to First Token) は、ユーザーが出力を目にするまでにどれだけ待つかを測定する、LLM 推論における重要なレイテンシメトリクスです。

**主要な LLM 推論メトリクス:**

1. **TTFT (Time to First Token)**:
   - リクエスト送信から最初のトークンまでの時間
   - プロンプト処理（prefill）時間を含む
   - 目標: 良好な UX のために < 500ms

2. **ITL (Inter-Token Latency)**:
   - 連続して生成されるトークン間の時間
   - 体感上のストリーミング速度に影響する
   - 目標: < 50ms

3. **スループット**:
   - 1秒あたりに生成されるトークン数
   - システムキャパシティを測定する

4. **E2E レイテンシ**:
   - 完全なレスポンスにかかる総時間
   - TTFT + (ITL * output_tokens)

**モニタリング例:**
```promql
# TTFT P99
histogram_quantile(0.99, sum(rate(nim_time_to_first_token_bucket[5m])) by (le))

# ITL P99
histogram_quantile(0.99, sum(rate(nim_inter_token_latency_bucket[5m])) by (le))

# Throughput
sum(rate(nim_tokens_generated_total[5m]))
```

</details>

### 7. NVIDIA Dynamo における KV-aware routing の目的は何ですか？

A) ユーザーの場所に基づいてリクエストをルーティングすること
B) 最適なパフォーマンスのために KV cache の局所性に基づいてリクエストをルーティングすること
C) 最も安価なインスタンスにリクエストをルーティングすること
D) モデルバージョンに基づいてリクエストをルーティングすること

<details>
<summary>回答を表示</summary>

**回答: B) 最適なパフォーマンスのために KV cache の局所性に基づいてリクエストをルーティングすること**

**解説:**
NVIDIA Dynamo の KV-aware routing は、KV cache データが配置されている場所に基づいてリクエストルーティングを最適化し、データ転送を減らすことでパフォーマンスを向上させます。

**KV-aware Routing の仕組み:**

1. **KV Cache Tracking**: ルーターは、どの decode worker が以前のリクエストの KV データをキャッシュしているかを追跡する
2. **Locality Optimization**: フォローアップリクエスト（マルチターン会話内）を、関連する KV cache をすでに持つ worker にルーティングする
3. **Load Balancing**: 局所性の利点と worker の負荷のバランスを取る

**設定:**
```yaml
router:
  kv_routing:
    enabled: true
    locality_weight: 0.7  # Prefer cache locality
    load_weight: 0.3      # Consider worker load
```

**利点:**
- マルチターン会話での TTFT の短縮
- メモリプレッシャーの低下（重複した KV cache を避ける）
- GPU メモリ使用率の向上
- 有効スループットの向上

**ルーティング判定式:**
```
score = locality_weight * cache_hit_score + load_weight * (1 - worker_load)
```

</details>

### 8. Kubernetes 用 Neuron device plugin をインストールするために使用するコマンドはどれですか？

A) `kubectl apply -f nvidia-device-plugin.yml`
B) `helm install neuron-plugin aws/neuron`
C) `kubectl apply -f k8s-neuron-device-plugin.yml`
D) `eksctl create addon --name neuron-device-plugin`

<details>
<summary>回答を表示</summary>

**回答: C) `kubectl apply -f k8s-neuron-device-plugin.yml`**

**解説:**
Neuron device plugin は、AWS Neuron SDK リポジトリの公式マニフェストを使用して kubectl apply でインストールします。

**インストールコマンド:**
```bash
kubectl apply -f https://raw.githubusercontent.com/aws-neuron/aws-neuron-sdk/master/src/k8/k8s-neuron-device-plugin.yml
```

**検証:**
```bash
# Check DaemonSet
kubectl get ds neuron-device-plugin-daemonset -n kube-system

# Check Neuron devices on nodes
kubectl get nodes -l 'node.kubernetes.io/instance-type in (inf2.xlarge,inf2.8xlarge,inf2.24xlarge,inf2.48xlarge)' \
  -o custom-columns=NAME:.metadata.name,NEURON:.status.allocatable.aws\\.amazon\\.com/neuron
```

**リソースリクエスト形式:**
```yaml
resources:
  limits:
    aws.amazon.com/neuron: 2  # Request 2 Neuron cores
```

NVIDIA device plugin は `nvidia.com/gpu` を使用し、Neuron は `aws.amazon.com/neuron` を使用します。

</details>

### 9. どの推論フレームワークがコア機能として組み込み autoscaling を提供しますか？

A) vLLM standalone
B) NVIDIA NIM
C) AIBrix
D) Triton Inference Server

<details>
<summary>回答を表示</summary>

**回答: C) AIBrix**

**解説:**
AIBrix は、HPA や KEDA のような外部ソリューションを必要とする他のフレームワークとは異なり、コア機能として組み込みのワークロード対応 autoscaling を提供します。

**AIBrix Autoscaler の機能:**
- ワークロード対応スケーリングポリシー
- 複数メトリクスのサポート（RPS、レイテンシ、GPU 使用率、キュー深度）
- 設定可能なスケールアップ/スケールダウン動作
- Deployment ごとのスケーリングポリシー

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

### 10. NVIDIA NIM デプロイにおける NGC Catalog の目的は何ですか？

A) Kubernetes マニフェストを保存すること
B) 事前最適化済みのモデルコンテナと設定を提供すること
C) クラスターネットワーキングを管理すること
D) ユーザー認証を処理すること

<details>
<summary>回答を表示</summary>

**回答: B) 事前最適化済みのモデルコンテナと設定を提供すること**

**解説:**
NGC (NVIDIA GPU Cloud) Catalog は、最適化済みモデルを含む事前構築済み NIM コンテナなど、GPU 向けに最適化されたソフトウェアの NVIDIA のリポジトリです。

**NGC Catalog の機能:**
- 事前最適化済みモデルコンテナ
- 複数のモデルプロファイル（異なるバッチサイズ、精度）
- バージョン管理
- セキュリティスキャン
- エンタープライズサポート

**NGC へのアクセス:**
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

**NGC Images の使用:**
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

**利用可能な NIM プロファイル:**
- `vllm-bf16-tp8`: 8-GPU tensor parallel、BF16 precision
- `vllm-fp8-tp4`: 4-GPU tensor parallel、FP8 precision
- `tensorrt-llm-fp16-tp8`: TensorRT-LLM backend

</details>

### 11. NVIDIA Dynamo は推論向けにどのバックエンドをサポートしていますか？

A) TensorRT-LLM のみ
B) vLLM、SGLang、TensorRT-LLM
C) vLLM のみ
D) PyTorch のみ

<details>
<summary>回答を表示</summary>

**回答: B) vLLM、SGLang、TensorRT-LLM**

**解説:**
NVIDIA Dynamo は backend-agnostic に設計されており、複数の推論エンジンをサポートします。

1. **vLLM**:
   - オープンソース、高パフォーマンス
   - メモリ効率のための PagedAttention
   - 幅広いモデルサポート

2. **SGLang**:
   - 構造化生成向けに最適化
   - 高速な JSON/regex constrained decoding
   - 効率的な prefix caching

3. **TensorRT-LLM**:
   - NVIDIA GPU の最大パフォーマンス
   - 最適化されたカーネル
   - INT8/FP8 quantization

**設定例:**
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

この柔軟性により、次が可能になります。
- 最適なパフォーマンスのためにバックエンドを組み合わせる
- 異なるエンジンをテストする
- 特定のタスクに特化したバックエンドを使用する

</details>

### 12. EKS 上の vLLM デプロイでモデルストレージを扱う推奨方法は何ですか？

A) モデルを ConfigMaps に保存する
B) コンテナ起動時に毎回モデルをダウンロードする
C) 事前ダウンロード済みモデルを含む FSx for Lustre または persistent volumes を使用する
D) モデルをコンテナイメージに埋め込む

<details>
<summary>回答を表示</summary>

**回答: C) 事前ダウンロード済みモデルを含む FSx for Lustre または persistent volumes を使用する**

**解説:**
本番環境の LLM デプロイでは、高パフォーマンスな永続ストレージを使用することが重要です。

**推奨ストレージオプション:**

1. **FSx for Lustre**:
   - 高スループットの並列ファイルシステム
   - 大規模モデルファイルに最適
   - モデル更新のための S3 連携
   - 最大 1000+ MB/s のスループット

2. **EBS gp3 Volumes**:
   - 単一ノードデプロイに適している
   - コスト効率が高い
   - 最大 16,000 IOPS

3. **EFS**:
   - Pod 間での共有アクセス
   - FSx より低いスループット
   - 小さなモデルに適している

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

**他の選択肢が推奨されない理由:**
- **ConfigMaps**: 1MB のサイズ制限があり、大きなファイル向けではない
- **Download at startup**: 起動が遅く、帯域幅コストと信頼性の問題がある
- **Embedded in image**: イメージが巨大になり、pull が遅く、バージョンの柔軟性がない

</details>

### 13. NIM デプロイにおける GenAI-Perf の機能は何ですか？

A) AI 画像を生成すること
B) LLM 推論パフォーマンスをベンチマークしプロファイルすること
C) GPU メモリを管理すること
D) network policies を設定すること

<details>
<summary>回答を表示</summary>

**回答: B) LLM 推論パフォーマンスをベンチマークしプロファイルすること**

**解説:**
GenAI-Perf は、生成 AI 推論パフォーマンスをベンチマークしプロファイルするための NVIDIA のツールです。

**機能:**
- TTFT、ITL、スループットを測定する
- 同時リクエストテストをサポートする
- 複数のエンドポイントタイプ（chat、completion）
- 分析用に結果をエクスポートする

**インストール:**
```bash
pip install genai-perf
```

**使用例:**
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

**報告される主要メトリクス:**
- Time to First Token (P50, P90, P99)
- Inter-Token Latency (P50, P90, P99)
- リクエストスループット
- トークンスループット
- ベンチマーク中の GPU 使用率

</details>

### 14. 複数 Pod にまたがる tensor parallelism を使用した分散 vLLM のデプロイに最も適した Kubernetes リソースタイプはどれですか？

A) Deployment
B) StatefulSet
C) DaemonSet
D) ReplicaSet

<details>
<summary>回答を表示</summary>

**回答: B) StatefulSet**

**解説:**
StatefulSet は、次を必要とする分散 vLLM デプロイに適したリソースです。

1. **安定したネットワーク識別子**: 各 Pod は予測可能な hostname（vllm-0、vllm-1 など）を取得する
2. **順序付きデプロイ**: Pod は順番に作成され、master/worker coordination に重要
3. **安定したストレージ**: 各 Pod が独自の persistent volume を持てる
4. **Headless Service**: NCCL のための直接的な Pod 間通信

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

**Deployment ではなく StatefulSet を使う理由:**
- Deployment は安定した hostname を保証しない
- NCCL には予測可能なアドレス指定が必要
- master election には一貫した Pod identity が必要

</details>

### 15. コンテナから見える Neuron cores の数を制御する環境変数は何ですか？

A) CUDA_VISIBLE_DEVICES
B) NEURON_RT_VISIBLE_CORES
C) AWS_NEURON_CORES
D) NEURON_DEVICE_COUNT

<details>
<summary>回答を表示</summary>

**回答: B) NEURON_RT_VISIBLE_CORES**

**解説:**
`NEURON_RT_VISIBLE_CORES` は、コンテナ内の Neuron runtime から見える Neuron cores を制御します。

**主要な Neuron 環境変数:**

1. **NEURON_RT_VISIBLE_CORES**:
   - 使用する cores を指定する
   - 形式: "0,1" または "0-3"
   ```yaml
   env:
   - name: NEURON_RT_VISIBLE_CORES
     value: "0,1"
   ```

2. **NEURON_RT_NUM_CORES**:
   - 使用する cores の総数
   ```yaml
   env:
   - name: NEURON_RT_NUM_CORES
     value: "2"
   ```

3. **NEURON_CC_FLAGS**:
   - モデルコンパイル用の compiler flags
   ```yaml
   env:
   - name: NEURON_CC_FLAGS
     value: "--model-type transformer"
   ```

**完全な例:**
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

注: `CUDA_VISIBLE_DEVICES` は NVIDIA GPU 用であり、Neuron 用ではありません。

</details>
