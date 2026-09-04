# vLLM のデプロイと最適化

> **対応バージョン**: Kubernetes 1.31, 1.32, 1.33  
> **最終更新**: September 4, 2026

vLLM は、大規模言語モデル（LLM）向けに最も広く採用されている、オープンソースの高性能推論エンジンです。本章では、vLLM の最新機能とアーキテクチャを確認し、EKS 上で本番規模にデプロイして最適化する方法を学びます。

## ラボ環境のセットアップ

このドキュメントの例を実行するには、以下のツールと環境が必要です。

### 必要なツールとリソース
- kubectl v1.31 以降
- Helm v3.10 以降
- NVIDIA GPU を搭載した EKS クラスター（最小推奨: g5.2xlarge インスタンス）
- NVIDIA ドライバーおよび NVIDIA Device Plugin がインストール済み
- 少なくとも 50GB のディスク容量

### GPU ノードのセットアップ

```bash
# Install NVIDIA Device Plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU nodes
kubectl get nodes "-o=custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu"
```

## vLLM の紹介

vLLM は、以下の特性を備えた LLM 推論エンジンです。

![vLLM の主要機能、その内部コンポーネントのパイプライン、メモリ効率や高スループットなどの利点をまとめた図。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-0.svg)

### vLLM の主要機能

1. **PagedAttention**:
   - KV cache を効率的に管理するメモリ管理技術
   - オペレーティングシステムの仮想メモリ管理から着想
   - 同時リクエスト処理を最大 10 倍に増加

2. **Continuous Batching**:
   - GPU 使用率を最大化するためにリクエストを動的にバッチ処理
   - 新規リクエストを到着後すぐに処理開始
   - スループットを最大 2 倍改善

3. **Distributed Inference**:
   - tensor parallelization によって大規模モデルをサポート
   - 複数 GPU 間でのモデルシャーディング
   - 175B+ パラメータモデルをサポート

4. **Quantization**:
   - INT8、FP16 を含むさまざまな精度をサポート
   - メモリ使用量を削減し、推論速度を向上
   - 精度低下を最小限に抑えつつ、メモリ効率を最大 2 倍改善

## 対応モデル

vLLM は以下のモデルをサポートしています。

| モデルファミリー | 対応モデル | Quantization オプション |
|-------------|-----------------|---------------------|
| **LLaMA 3 / 3.1 / 3.2 / 3.3** | 1B, 3B, 8B, 70B, 405B | FP16, BF16, FP8, INT8, INT4, AWQ, GPTQ |
| **DeepSeek V3 / R1** | 7B, 67B, 671B (MoE) | FP16, BF16, FP8, AWQ, GPTQ |
| **Qwen 2 / 2.5 / QwQ** | 0.5B ~ 72B | FP16, BF16, FP8, INT8, AWQ, GPTQ |
| **Mistral / Mixtral** | 7B, 8x7B, 8x22B, Large 2 | FP16, BF16, FP8, AWQ, GPTQ |
| **Gemma 2 / 3** | 2B, 9B, 27B | FP16, BF16, INT8 |
| **Phi-3 / Phi-4** | 3.8B, 7B, 14B | FP16, BF16, INT8, AWQ |
| **Command R / R+** | 35B, 104B | FP16, BF16 |
| **DBRX** | 132B (MoE) | FP16, BF16 |
| **StarCoder 2** | 3B, 7B, 15B | FP16, BF16 |
| **Vision Models (VLM)** | LLaVA, Pixtral, Qwen2-VL, InternVL | FP16, BF16 |

1. **PagedAttention**: 長いシーケンスの処理時にメモリ使用量を最適化する、メモリ効率の高い attention メカニズム。
2. **Continuous Batching**: スループットを向上させるためにリクエストを動的にバッチ処理します。
3. **Distributed Inference**: 大規模モデルを処理するために、複数の GPU とノードにモデルを分散します。
4. **Quantization**: メモリ使用量を削減し、スループットを向上させる INT8/INT4 quantization をサポートします。
5. **OpenAI Compatible API**: OpenAI API と互換性のあるインターフェースを提供します。

### v0.6 系で追加された vLLM の機能

vLLM は急速に進化しており、最近のリリースでは重要な新機能が追加されています。

#### Speculative Decoding

小さなドラフトモデルを使用して複数の候補トークンを生成し、大きなモデルがそれらを 1 回のパスで検証することで、推論速度を 2～3 倍向上させます。

```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-70B-Instruct \
  --speculative-model meta-llama/Llama-3.1-8B-Instruct \
  --num-speculative-tokens 5
```

#### Prefix Caching

同じ system prompt またはコンテキストを共有するリクエスト間で KV cache を自動的に再利用し、TTFT（Time to First Token）を大幅に削減します。

```bash
--enable-prefix-caching
```

#### Chunked Prefill

長い prompt の prefill を decode ステップと交互に実行する小さなチャンクに分割し、長いコンテキストを持つリクエストが他のリクエストのレイテンシに与える影響を軽減します。

```bash
--enable-chunked-prefill --max-num-batched-tokens 2048
```

#### 動的 LoRA Adapter ロード

複数の LoRA adapter をランタイムで動的にロード/アンロードし、単一のベースモデルから多くのカスタマイズ済みモデルを提供します。

```bash
--enable-lora --max-loras 4 --max-lora-rank 64
```

```python
# Specify LoRA model in API request
response = client.chat.completions.create(
    model="my-custom-lora-adapter",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

#### Structured Output

JSON Schema、regex パターン、CFG（Context-Free Grammar）を介した制約付き出力生成をサポートし、信頼性の高い構造化データ生成を実現します。

```python
from openai import OpenAI
client = OpenAI(base_url="http://vllm-service:8000/v1")

response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "Return user information as JSON"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "user_info",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "email": {"type": "string"}
                },
                "required": ["name", "age", "email"]
            }
        }
    }
)
```

#### Tool Calling

agent ワークフローとの統合に向けて、OpenAI 互換の Tool/Function Calling をサポートします。

```python
response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "What's the weather in Seoul?"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a specified location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"]
            }
        }
    }]
)
```

#### FP8 Quantization

Hopper（H100）および Ada Lovelace（L4、L40S）GPU で FP8 quantization をサポートし、ほぼ同一の精度を維持しながらメモリ使用量を半減します。

```bash
--quantization fp8 --kv-cache-dtype fp8
```

#### Vision-Language Model（VLM）Serving

画像とテキストを同時に処理するマルチモーダルモデルをサポートします。

```python
response = client.chat.completions.create(
    model="llava-hf/llava-v1.6-mistral-7b-hf",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
    }]
)
```

## システム要件

EKS 上に vLLM をデプロイするためのシステム要件は以下のとおりです。

![vLLM のハードウェアおよびソフトウェアの前提条件と、GPU メモリによってサポートされるモデルサイズの層を示した図。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-1.svg)

1. **ハードウェア**:
   - NVIDIA GPU（Volta、Turing、Ampere、Hopper アーキテクチャ）
   - 最小 GPU メモリ: モデルサイズによって異なる
     - 7B モデル: 最低 16GB の GPU メモリ
     - 13B モデル: 最低 24GB の GPU メモリ
     - 70B モデル: 最低 80GB の GPU メモリ（または複数 GPU に分散）

2. **ソフトウェア**:
   - CUDA 12.1 以降（FP8 には CUDA 12.4 を推奨）
   - Python 3.9 以降
   - PyTorch 2.4.0 以降

3. **EKS ノードタイプ**:
   - p5.48xlarge: NVIDIA H100 GPU 8 基、各 80GB（最高性能）
   - p4d.24xlarge: NVIDIA A100 GPU 8 基、各 40GB または 80GB
   - g6.12xlarge: NVIDIA L4 GPU 4 基、各 24GB（コスト効率が高い）
   - g5.12xlarge: NVIDIA A10G GPU 4 基、各 24GB
   - g6e.12xlarge: NVIDIA L40S GPU 4 基、各 48GB
   - trn1.32xlarge: AWS Trainium 16 基、各 32GB（AWS シリコン）

## EKS インフラストラクチャ設定

![vLLM を実行する Amazon EKS クラスターのアーキテクチャ図。control plane、GPU および CPU node group、ストレージとネットワーキングのリソース、補助的な AWS サービスを含みます。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-2.svg)

## ストレージ設定

vLLM は大規模なモデル weights をロードする必要があるため、高性能なストレージを必要とします。

### FSx for Lustre のセットアップ

FSx for Lustre は、大規模なモデル weights を迅速にロードするのに適した高性能並列ファイルシステムです。

```yaml
apiVersion: fsx.aws.k8s.io/v1beta1
kind: Lustre
metadata:
  name: vllm-models
spec:
  deploymentType: SCRATCH_2
  storageCapacity: 1200
  subnetIds:
    - subnet-0123456789abcdef0
  securityGroupIds:
    - sg-0123456789abcdef0
  perUnitStorageThroughput: 200
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fsx-lustre-sc
provisioner: fsx.csi.aws.com
parameters:
  fileSystemId: fs-0123456789abcdef0
  mountName: vllm-models
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-models-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: fsx-lustre-sc
  resources:
    requests:
      storage: 1200Gi
```

### S3 からのモデルのダウンロード

Hugging Face モデルを S3 に保存し、FSx for Lustre にダウンロードする Job:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: model-download
spec:
  template:
    spec:
      containers:
      - name: model-download
        image: huggingface/transformers:latest
        command:
        - python
        - -c
        - |
          from huggingface_hub import snapshot_download
          import os

          model_id = "meta-llama/Llama-3.1-70B-Instruct"
          dest_dir = "/models/llama-3.1-70b"

          os.makedirs(dest_dir, exist_ok=True)
          snapshot_download(repo_id=model_id, local_dir=dest_dir, token=os.environ["HF_TOKEN"])
        env:
        - name: HF_TOKEN
          valueFrom:
            secretKeyRef:
              name: huggingface-token
              key: token
        volumeMounts:
        - name: models-volume
          mountPath: /models
      restartPolicy: Never
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
```

## vLLM のデプロイ

### デプロイアーキテクチャ

次の図は、EKS 上で vLLM をデプロイするための 2 つの主要アーキテクチャを示しています。

![load balancer から入力を受け、FSx/S3 をバックエンドにしたストレージを共有する、単一ノードの vLLM Pod デプロイとマルチノードの NCCL 同期デプロイを比較した図。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-3.svg)

### 単一ノードデプロイ

単一 GPU、または単一ノード上の複数 GPU で vLLM を実行する Deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-inference
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      containers:
      - name: vllm-server
        image: vllm/vllm-openai:latest
        command:
        - python
        - -m
        - vllm.entrypoints.openai.api_server
        - --model=/models/llama-3.1-70b
        - --tensor-parallel-size=8
        - --gpu-memory-utilization=0.95
        - --max-num-batched-tokens=16384
        - --enable-prefix-caching
        - --enable-chunked-prefill
        - --port=8000
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 8
        volumeMounts:
        - name: models-volume
          mountPath: /models
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4,5,6,7"
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

### マルチノード分散デプロイ

大規模モデルを複数ノードに分散する方法:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-config
data:
  hostfile: |
    vllm-inference-0 slots=8
    vllm-inference-1 slots=8
  run_server.sh: |
    #!/bin/bash

    RANK=$HOSTNAME
    if [[ $HOSTNAME == "vllm-inference-0" ]]; then
      RANK=0
    elif [[ $HOSTNAME == "vllm-inference-1" ]]; then
      RANK=1
    fi

    python -m vllm.entrypoints.openai.api_server \
      --model=/models/llama-3.1-70b \
      --tensor-parallel-size=16 \
      --pipeline-parallel-size=1 \
      --max-num-batched-tokens=8192 \
      --port=8000 \
      --host=0.0.0.0 \
      --master-addr=vllm-inference-0 \
      --master-port=29500 \
      --rank=$RANK
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: vllm-inference
spec:
  serviceName: "vllm-inference"
  replicas: 2
  selector:
    matchLabels:
      app: vllm-inference
  template:
    metadata:
      labels:
        app: vllm-inference
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - vllm-inference
            topologyKey: kubernetes.io/hostname
      containers:
      - name: vllm-server
        image: vllm/vllm-openai:latest
        command:
        - bash
        - /config/run_server.sh
        ports:
        - containerPort: 8000
        - containerPort: 29500
        resources:
          limits:
            nvidia.com/gpu: 8
        volumeMounts:
        - name: models-volume
          mountPath: /models
        - name: config-volume
          mountPath: /config
        env:
        - name: CUDA_VISIBLE_DEVICES
          value: "0,1,2,3,4,5,6,7"
        - name: NCCL_DEBUG
          value: "INFO"
        - name: NCCL_IB_DISABLE
          value: "0"
        - name: NCCL_IB_GID_INDEX
          value: "3"
        - name: NCCL_NET_GDR_LEVEL
          value: "5"
      volumes:
      - name: models-volume
        persistentVolumeClaim:
          claimName: vllm-models-pvc
      - name: config-volume
        configMap:
          name: vllm-config
          defaultMode: 0755
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8000
    targetPort: 8000
    name: api
  - port: 29500
    targetPort: 29500
    name: nccl
  clusterIP: None
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-inference-lb
spec:
  selector:
    app: vllm-inference
    statefulset.kubernetes.io/pod-name: vllm-inference-0
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

## パフォーマンス最適化

![GPU メモリ、スループット、ネットワークの最適化手法と各設定フラグが、全体的なパフォーマンス向上に集約されることを示した図。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-4.svg)

### GPU メモリの最適化

vLLM の GPU メモリ使用量を最適化する方法:

1. **GPU メモリ使用率の調整**:

```bash
--gpu-memory-utilization=0.9
```

2. **Quantization の適用**:

```bash
--quantization awq
```

3. **Swap Space の活用**:

```bash
--swap-space=16
```

### スループットの最適化

vLLM のスループットを最適化する方法:

1. **バッチサイズの調整**:

```bash
--max-num-batched-tokens=8192
```

2. **KV Cache の最適化**:

```bash
--block-size=16
```

3. **Tensor Parallel 処理の調整**:

```bash
--tensor-parallel-size=8
```

### ネットワークの最適化

分散デプロイにおけるネットワークパフォーマンスを最適化する方法:

1. **EFA（Elastic Fabric Adapter）の活用**:

```yaml
resources:
  limits:
    nvidia.com/gpu: 8
    vpc.amazonaws.com/efa: 1
```

2. **NCCL 設定の最適化**:

```yaml
env:
- name: NCCL_DEBUG
  value: "INFO"
- name: NCCL_MIN_NCHANNELS
  value: "4"
- name: NCCL_SOCKET_IFNAME
  value: "^lo,docker"
- name: NCCL_ASYNC_ERROR_HANDLING
  value: "1"
```

3. **ノード配置の最適化**:

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-west-2a
```

## 測定ベンチマーク: 単一 L4 GPU 上の Qwen2.5-7B

ここまでのこのページ上の数値はすべて、一般的な vLLM プロジェクトの主張または設定フラグの説明です。このセクションは異なります。実際の vLLM server に対する 1 回の測定であり、「continuous batching がスループットを向上させる」とは具体的にどのようなものかを、1 つのモデルと GPU で確認できます。

![client Job が ClusterIP Service 経由で vLLM server に到達し、単一の NVIDIA L4 GPU 上でリクエストをバッチ処理する様子と、測定されたスループット、レイテンシ、compute ではなくメモリ帯域幅が制約となった理由を示した図。](../.gitbook/assets/en-ai-ml-02-vllm-deployment-6.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-ai-ml-02-vllm-deployment-6.html)

### セットアップ

- **クラスター**: 専用 Karpenter NodePool（`bench-gpu`、オンデマンド `g6.2xlarge` — NVIDIA L4 1 基、GPU メモリ 24GB、8 vCPU、RAM 32 GiB）。`nvidia.com/gpu=true:NoSchedule` で taint され、既存の `nvidia-device-plugin` daemonset に参加するようラベル付けされ、実行直後に削除されました。
- **Server**: `vllm/vllm-openai:v0.6.4.post1`（2024-11-15 リリース — vLLM プロジェクトはその後、prefix caching がデフォルトで有効な V1 engine をリリースしているため、これは現行の vLLM ではなく、そのリリース系列のスナップショットとして扱ってください）、モデル `Qwen/Qwen2.5-7B-Instruct`、`--dtype bfloat16 --max-model-len 4096 --gpu-memory-utilization 0.90`。quantization、speculative decoding、prefix caching を使用しない 1 つの精度（bf16、モデルのネイティブ dtype）であり、このページの他の箇所で説明している通常のデフォルトです。
- **Client**: クラスター**内**（別の非 GPU ノード）で Job として実行される Python `ThreadPoolExecutor`。`vllm-server` ClusterIP Service 経由で `/v1/chat/completions` にアクセスします。non-streaming、`temperature=0`、`max_tokens=128`、短い prompt を 8 個ローテーション（Kubernetes の概念について 1～2 文の回答を求める質問）。実際には、すべての応答が 1～2 文で停止するのではなく、128 トークン上限に近い値で実行されました（3 つすべての同時実行バッチで一貫して平均約 102 トークン）。これは同時実行レベル間でスループットを公平に比較するのに有用ですが、レイテンシの数値を「短い質問に答えるまでの時間」として読む前に知っておくべき点です。
- **コールドスタート**: vLLM engine の起動ログから `/health` endpoint が `200` を返すまで約 4.5 分。Hugging Face から Qwen2.5-7B-Instruct の約 15 GB の weights を Pod の ephemeral cache にダウンロードする時間が大部分を占めます。image pull 時間は含まれず、個別には測定していません。

### 再現方法

```yaml
# NodePool (Karpenter) - dedicated, deleted after the run — nodeClassRef points at the cluster's existing GPU EC2NodeClass (AMI/subnets/SG), not shown here
apiVersion: karpenter.sh/v1
kind: NodePool
metadata: { name: bench-gpu }
spec:
  limits: { cpu: "16", memory: 128Gi, nvidia.com/gpu: "1" }
  template:
    metadata:
      labels: { node-type: bench-gpu, nvidia.com/device-plugin.config: default }
    spec:
      expireAfter: 6h
      nodeClassRef: { group: karpenter.k8s.aws, kind: EC2NodeClass, name: gpu }
      requirements:
        - { key: node.kubernetes.io/instance-type, operator: In, values: [g6.2xlarge] }
      taints: [{ key: nvidia.com/gpu, value: "true", effect: NoSchedule }]
---
# vLLM server (namespace bench-gpu) + the ClusterIP Service the client calls
apiVersion: apps/v1
kind: Deployment
metadata: { name: vllm-server, namespace: bench-gpu }
spec:
  replicas: 1
  selector: { matchLabels: { app: vllm-server } }
  template:
    metadata: { labels: { app: vllm-server } }
    spec:
      nodeSelector: { node-type: bench-gpu }
      tolerations: [{ key: nvidia.com/gpu, value: "true", effect: NoSchedule }]
      containers:
        - name: vllm
          image: vllm/vllm-openai:v0.6.4.post1
          args: ["--model", "Qwen/Qwen2.5-7B-Instruct", "--max-model-len", "4096",
                 "--gpu-memory-utilization", "0.90", "--dtype", "bfloat16"]
          ports: [{ containerPort: 8000 }]
          resources:
            limits: { nvidia.com/gpu: "1" }
            requests: { nvidia.com/gpu: "1", cpu: "3", memory: 20Gi }
          readinessProbe: { httpGet: { path: /health, port: 8000 }, initialDelaySeconds: 30, periodSeconds: 10, failureThreshold: 60 }
---
apiVersion: v1
kind: Service
metadata: { name: vllm-server, namespace: bench-gpu }
spec:
  selector: { app: vllm-server }
  ports: [{ port: 8000, targetPort: 8000 }]
```

client は、`urllib` + `concurrent.futures.ThreadPoolExecutor` を使って `http://vllm-server:8000/v1/chat/completions` に N 個のリクエストを送信し、それぞれの所要時間を測定するシンプルな Python script です。同じ namespace 内で `batch/v1` Job として実行してください。重要な注意点として、上記の `nvidia.com/device-plugin.config: default` ノードラベルは必須です。これがないと、共有の `nvidia-device-plugin` DaemonSet は新しいノードにスケジュールされず、taint と toleration が正しく一致していても `nvidia.com/gpu` は割り当て可能リソースとして登録されません。

### 結果

| 同時実行数 | リクエスト数 | 経過時間 | Client レイテンシ p50 / p90 | Client 合計スループット | Server 報告のピーク生成スループット | GPU KV cache 使用率 |
|---|---|---|---|---|---|---|
| 1（直列） | 10 | ~53.2 s（リクエストレイテンシの合計） | 5.65 s / 7.43 s | リクエストあたり ~17-18 tokens/s | ~17 tokens/s | 0.1-0.2% |
| 4 | 16 | 27.78 s | 6.99 s / 7.88 s | 58.67 tokens/s | 65-66 tokens/s | 0.4-0.7% |
| 8 | 32 | 30.02 s | 7.18 s / 8.15 s | 109.04 tokens/s | 123-129 tokens/s | 0.8-1.4% |
| 16 | 64 | 31.35 s | 7.52 s / 8.74 s | 208.08 tokens/s | 最大 243 tokens/s | 1.5-2.6% |

「Client 合計スループット」は、Pod 外部から測定した、そのバッチ内のすべてのリクエストの completion tokens 合計を経過時間で割った値です。「Server 報告」は、`Running: <concurrency>` 時の vLLM 自身の定期的な `Avg generation throughput` ログ行です。HTTP/JSON のオーバーヘッドを除外し、測定間隔中の平均だけでなく真のピークを捉えるため、Client の数値よりやや高くなります。GPU メモリ使用量（実行後に `nvidia-smi` で測定）は、このインスタンスでドライバーが合計として報告する 23.0 GiB のうち 19.2 GiB でした。`gpu-memory-utilization=0.90` は、weights と KV cache blocks のためにその大部分を事前割り当てするよう vLLM に指示します。そのため、以下の KV cache の割合は、実際の空き VRAM ではなく、確保済みプールの使用率を表します。

### 分析

- **リクエストあたりのレイテンシはほとんど変化しません。** 同じ約 100～128 トークンの応答について、同時リクエスト数を 1 から 16 に増やしても、p50 レイテンシは 5.65 s から 7.52 s（+33%）にしか上がりません。これは continuous batching が意図どおりに機能していることを示しています。新しいリクエストは、その後ろでキューイングされるのではなく、実行中のバッチに参加します。
- **合計スループットはほぼ線形にスケールします。** 同時リクエスト数を 4 → 8 → 16 と増やすと、合計スループットは毎回ほぼ 2 倍になります（58.67 → 109.04 → 208.08 tokens/s）。
- **これは compute-bound ではなく bandwidth-bound の decode であり、まさにそのためバッチ処理が有効です。** バッチ 1 では、トークンごとに約 15.2 GB の bf16 weights を GDDR6 メモリからストリーミングする必要があります。この L4 の約 300 GB/s のメモリ帯域幅では、単一リクエストの decode はおよそ 20 tokens/s に制限され、測定された約 17～18 と一致します。compute はまったく異なる状況を示します。最も多忙だった測定点（合計 208 tokens/s）でも、GPU の処理量は約 3 TFLOP/s で、L4 の dense bf16 compute 約 121 TFLOPS に対して数パーセントにすぎません。KV cache 容量も制約にはなりませんでした（実行全体を通して 3% 未満）。continuous batching は、まさにこの種の bandwidth-bound decode に対する解決策です。あるリクエストのために weights がすでにメモリから読み込まれていれば、同じ weight read で 16 リクエストに応答するコストはほぼゼロです。これが、レイテンシがほとんど増えない一方でスループットがほぼ線形にスケールする理由です。

### 注意事項

これは、1 つのモデル、1 つの精度（bf16）、1 種類の GPU、1 つのコンテキスト長における単一実行（n=1）です。一般的な vLLM/L4 のパフォーマンス主張ではなく、校正された 1 つのデータポイントとして扱ってください。client はクラスター内（別の非 GPU ノード）で実行されたため、ネットワークレイテンシは外部 caller ではなくクラスター内の hop を反映しています。ここでのレイテンシは、time-to-first-token（TTFT）ではなく、完全な end-to-end HTTP 応答時間です。streaming はテストしていません。prefix caching、speculative decoding、FP8、およびマルチ GPU tensor parallelism（すべてこのページの前半で説明）は実施していません。上記の manifest を使用して再現してください。これらの数値を異なるモデルサイズ、GPU、または prompt 長に外挿しないでください。

## モニタリングとログ記録

![vLLM、GPU、Kubernetes のメトリクスが Prometheus/Grafana のモニタリングスタックに流れ、ダッシュボードとアラートを生成する様子と、独立した logging stack を示した図。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-5.svg)

### Prometheus メトリクス

vLLM server から Prometheus メトリクスを収集する方法:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-metrics
  labels:
    app: vllm-inference
spec:
  selector:
    app: vllm-inference
  ports:
  - port: 8001
    targetPort: 8001
    name: metrics
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-metrics
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: vllm-inference
  endpoints:
  - port: metrics
    interval: 15s
```

### ログ収集

vLLM server のログを CloudWatch に収集する方法:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
  namespace: logging
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/containers/vllm-*.log
      pos_file /var/log/fluentd-vllm.log.pos
      tag kubernetes.vllm.*
      read_from_head true
      <parse>
        @type json
        time_format %Y-%m-%dT%H:%M:%S.%NZ
      </parse>
    </source>

    <filter kubernetes.vllm.**>
      @type kubernetes_metadata
      @id filter_kube_metadata
    </filter>

    <match kubernetes.vllm.**>
      @type cloudwatch_logs
      log_group_name /eks/vllm/logs
      log_stream_name_key $.kubernetes.pod_name
      remove_log_stream_name_key true
      auto_create_stream true
      region us-west-2
    </match>
```

## オートスケーリング

![CPU、GPU、リクエストレート、キュー長のシグナルが Pod レベルのオートスケーリングを駆動し、それが GPU ノードのオートスケーリングと Spot capacity を駆動する様子を示した図。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-6.svg)

### HPA（Horizontal Pod Autoscaler）

リクエスト量に基づいて vLLM server を自動的にスケールする方法:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-inference
  minReplicas: 1
  maxReplicas: 5
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
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: 100
```

### Karpenter を使用したノードのオートスケーリング

GPU ノードを自動的にプロビジョニングする方法:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: vllm-gpu
spec:
  template:
    spec:
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p3.16xlarge
        - g5.12xlarge
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: vpc.amazonaws.com/efa
        operator: In
        values:
        - "true"
      nodeClassRef:
        name: vllm-gpu-class
  limits:
    nvidia.com/gpu: 32
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: vllm-gpu-class
spec:
  subnetSelector:
    karpenter.sh/discovery: vllm-cluster
  securityGroupSelector:
    karpenter.sh/discovery: vllm-cluster
  ttlSecondsAfterEmpty: 30
```

## セキュリティ設定

### Network Policy

vLLM server へのネットワークアクセスを制限する方法:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: vllm-network-policy
spec:
  podSelector:
    matchLabels:
      app: vllm-inference
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api-gateway
    ports:
    - protocol: TCP
      port: 8000
  - from:
    - podSelector:
        matchLabels:
          app: vllm-inference
    ports:
    - protocol: TCP
      port: 29500
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: vllm-inference
    ports:
    - protocol: TCP
      port: 29500
  - to:
    ports:
    - protocol: TCP
      port: 443
```

### Security Context

コンテナの security context を設定する方法:

```yaml
securityContext:
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
```

## Client 統合

![client SDK が API gateway を経由し、認証と rate limiting のためのセキュリティ層を通って、load-balanced なバックエンド Service に到達する様子を示した図。](../../assets/diagrams/rendered/en-ai-ml-02-vllm-deployment-7.svg)

### API Gateway

vLLM server の前段に API gateway をデプロイする方法:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
      - name: api-gateway
        image: nginx:latest
        ports:
        - containerPort: 80
        volumeMounts:
        - name: nginx-config
          mountPath: /etc/nginx/conf.d
      volumes:
      - name: nginx-config
        configMap:
          name: nginx-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
data:
  default.conf: |
    server {
      listen 80;

      location /v1/ {
        proxy_pass http://vllm-inference:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
      }
    }
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
spec:
  selector:
    app: api-gateway
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
```

### Client の例

Python client を使用して vLLM server にリクエストを送信する方法:

```python
import requests
import json

url = "http://api-gateway/v1/completions"

payload = {
    "model": "llama-3.1-70b",
    "prompt": "Once upon a time",
    "max_tokens": 100,
    "temperature": 0.7
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))

print(response.json())
```

## ベストプラクティス

### リソース管理

1. **メモリオーバーヘッドを考慮する**:
   - GPU メモリに加えて、十分な CPU メモリを割り当てます。
   - CPU メモリはモデルサイズのおよそ 2 倍を割り当てることを推奨します。

2. **CPU コアの割り当て**:
   - GPU ごとに少なくとも 4 CPU コアを割り当てます。
   - tensor parallelization を使用する場合は、より多くの CPU コアが必要になることがあります。

3. **ノードの選択**:
   - モデルサイズに基づいて適切なノードタイプを選択します。
   - メモリ帯域幅の高いノードを選択します。

### 高可用性

1. **複数 Availability Zone へのデプロイ**:
   - 複数の Availability Zone に vLLM server をデプロイします。
   - 各 Availability Zone に十分な capacity を確保します。

2. **負荷分散**:
   - 複数の vLLM server インスタンスにリクエストを分散します。
   - 同じユーザーからのリクエストが同じ server にルーティングされるよう、session affinity を設定します。

3. **障害復旧**:
   - 失敗した server を検出する health check を設定します。
   - 自動復旧メカニズムを実装します。

### コスト最適化

1. **Spot インスタンスを活用する**:
   - コスト削減のために Spot インスタンスを使用します。
   - 中断耐性のあるワークロードに適しています。

2. **モデルの Quantization**:
   - メモリ使用量を削減するために INT8 または INT4 quantization を適用します。
   - 精度とパフォーマンスのバランスを検討します。

3. **オートスケーリング**:
   - リクエスト量に基づいて server を自動的にスケールします。
   - アイドル時に server をスケールダウンしてコストを削減します。

## まとめ

vLLM は最も活発に開発されているオープンソース LLM 推論エンジンであり、Speculative Decoding、Prefix Caching、動的 LoRA ロード、Structured Output、Tool Calling など、本番環境で不可欠な機能を包括的にサポートしています。適切な GPU インスタンスの選定、高性能ストレージ、ネットワーク最適化、EKS 上でのオートスケーリングを組み合わせることで、コスト効率が高くスケーラブルな LLM serving プラットフォームを構築できます。SGLang や TGI などの他フレームワークとの比較については、[推論フレームワーク](./04-inference-frameworks.md)の章を参照してください。

## 参考資料

- [vLLM 公式ドキュメント](https://docs.vllm.ai/) - vLLM の公式ドキュメントおよび最新機能ガイド
- [AI on EKS](https://awslabs.github.io/ai-on-eks/) - EKS 上に AI/ML ワークロードをデプロイするための AWS ガイドと例

## クイズ

この章で学んだ内容を確認するには、[トピッククイズ](../quizzes/ai-ml/04-vllm-deployment-quiz.md)に挑戦してください。
