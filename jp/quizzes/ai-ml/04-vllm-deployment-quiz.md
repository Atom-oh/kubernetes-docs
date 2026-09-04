# vLLM デプロイメントクイズ

このクイズでは、Kubernetes における vLLM（Vector Language Model）のデプロイに関する理解を確認します。

## クイズ問題

### 1. vLLM（Vector Language Model）の主な目的は何ですか？

A. 画像処理の高速化
B. 大規模言語モデル（LLM）の推論最適化と高速化
C. データベースクエリの最適化
D. ネットワークトラフィックの管理

<details>
<summary>回答を表示</summary>

**回答: B. 大規模言語モデル（LLM）の推論最適化と高速化**

**解説:**
vLLM（Vector Language Model）の主な目的は、大規模言語モデル（LLM）の推論を最適化して高速化することです。vLLM は PagedAttention と呼ばれる革新的な attention アルゴリズムを使用してメモリ管理を最適化し、高スループットかつ低レイテンシでの LLM 推論を可能にします。

**vLLM の主な機能:**
1. **PagedAttention**: GPU メモリ使用量を最適化する、メモリ効率の高い attention メカニズム。
2. **Continuous batching**: リクエストを動的にバッチ化してスループットを向上させます。
3. **分散推論**: 大規模モデルを複数の GPU とノードに分散します。
4. **さまざまなモデルのサポート**: Llama、GPT-NeoX、Falcon、MPT を含む各種オープンソース LLM をサポートします。
5. **OpenAI 互換 API**: OpenAI API と互換性のあるインターフェイスを提供します。

**PagedAttention の仕組み:**
PagedAttention は、オペレーティングシステムの仮想メモリ管理に着想を得て、KV（Key-Value）cache を効率的に管理する手法です。従来の方法では各リクエストに固定サイズのメモリブロックを割り当てますが、PagedAttention は必要な量だけを割り当てて再利用します。

**vLLM のパフォーマンス上の利点:**
1. **高スループット**: 既存のソリューションと比較して 2～4 倍高いスループット
2. **メモリ効率**: 最大 8 倍多い同時リクエストを処理可能
3. **低レイテンシ**: 効率的なメモリ管理による応答時間の短縮
4. **リソース使用率の向上**: GPU リソースをより効率的に利用

**vLLM のユースケース:**
1. **対話型 AI サービス**: チャットボット、仮想アシスタントなど
2. **テキスト生成サービス**: コンテンツ生成、要約、翻訳など
3. **コード生成と補完**: プログラミング支援ツール
4. **大規模テキスト処理**: 文書分析、情報抽出など

**他の選択肢の問題点:**
- A. 画像処理の高速化: vLLM はテキストベースの言語モデル向けであり、画像処理に特化していません。
- C. データベースクエリの最適化: vLLM はデータベースクエリの最適化とは関係ありません。
- D. ネットワークトラフィックの管理: vLLM はネットワークトラフィックの管理とは関係ありません。
</details>

### 2. Kubernetes で vLLM をデプロイする際、最も重要なリソース要件は何ですか？

A. 大容量の CPU とメモリ
B. 高性能 GPU と十分な GPU メモリ
C. 高速ネットワークインターフェイス
D. 大容量の永続ストレージ

<details>
<summary>回答を表示</summary>

**回答: B. 高性能 GPU と十分な GPU メモリ**

**解説:**
Kubernetes で vLLM をデプロイする際に最も重要なリソース要件は、高性能 GPU と十分な GPU メモリです。大規模言語モデル（LLM）には数十億から数千億のパラメータがあり、これらのモデルを効率的に実行するには、強力な GPU の計算能力とモデルパラメータを格納できる十分な GPU メモリが不可欠です。

**GPU 要件:**
1. **GPU タイプ**: NVIDIA A100、H100、V100、RTX A6000 などの高性能 GPU
2. **GPU メモリ**: モデルサイズによって異なりますが、一般に以下のとおりです。
   - 7B パラメータモデル: 最低 16GB の GPU メモリ
   - 13B パラメータモデル: 最低 24GB の GPU メモリ
   - 70B パラメータモデル: 最低 80GB の GPU メモリ、または複数 GPU への分散
3. **GPU 数**: スループット要件とモデルサイズに依存しますが、大規模モデルは複数の GPU に分散する必要があります。

**vLLM デプロイメントの GPU リソースリクエスト例:**
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

**大規模モデルの分散デプロイメント例:**
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

**GPU メモリ要件の計算:**
LLM の GPU メモリ要件は、次の要素によって決まります。
1. **モデルパラメータ**: 各パラメータは通常 2 バイト（FP16）または 4 バイト（FP32）を使用します。
2. **KV cache**: 各トークンの Key-Value cache には追加メモリが必要です。
3. **バッチサイズ**: 同時リクエスト数の増加に伴ってメモリ要件も増加します。
4. **コンテキスト長**: コンテキスト長が長いほど、より多くの KV cache メモリが必要です。

**おおよそのメモリ要件の式:**
```
Required GPU memory = Model size + (batch size x sequence length x hidden size x layers x 4 bytes)
```

**その他のリソース要件:**
1. **CPU**: 前処理と後処理のための十分な CPU コア
2. **システムメモリ**: モデルのロードと処理のための十分な RAM
3. **ストレージ**: モデル重みファイルのための十分なストレージ
4. **ネットワーク**: 分散推論のための高速ネットワーク接続

**他の選択肢の問題点:**
- A. 大容量の CPU とメモリ: CPU は LLM 推論に効率的ではなく、システムメモリだけで GPU メモリを置き換えることはできません。
- C. 高速ネットワークインターフェイス: 分散推論では重要ですが、GPU と GPU メモリより優先度は低くなります。
- D. 大容量の永続ストレージ: モデル重みの保存には必要ですが、推論パフォーマンスに直接影響しません。
</details>

### 3. Kubernetes における vLLM の最適なストレージソリューションは何ですか？

A. emptyDir volume
B. hostPath volume
C. 高性能分散ファイルシステム（例: FSx for Lustre）
D. 通常のネットワークファイルシステム（NFS）

<details>
<summary>回答を表示</summary>

**回答: C. 高性能分散ファイルシステム（例: FSx for Lustre）**

**解説:**
Kubernetes における vLLM の最適なストレージソリューションは、高性能分散ファイルシステム（例: FSx for Lustre）です。vLLM は大規模言語モデルを処理するためにモデル重みファイルを迅速にロードする必要があり、分散推論環境では複数のノードが同じモデルファイルに同時にアクセスする必要があります。高性能分散ファイルシステムは、高スループット、低レイテンシ、並列アクセス機能によってこれらの要件を満たします。

**高性能分散ファイルシステムの利点:**
1. **高スループット**: 大規模なモデルファイルを迅速にロードできます。
2. **並列アクセス**: 複数ノードが同じファイルへ同時にアクセスできます。
3. **スケーラビリティ**: ストレージ容量とパフォーマンスを必要に応じてスケールできます。
4. **データ整合性**: 複数ノードにわたり一貫したデータビューを提供します。
5. **耐久性**: データレプリケーションとバックアップ機能により、データ損失のリスクを低減します。

**AWS FSx for Lustre の設定例:**
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

**Google Cloud Filestore の設定例:**
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

**Azure NetApp Files の設定例:**
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

**他のストレージオプションとの比較:**

| ストレージオプション | スループット | レイテンシ | マルチノードアクセス | スケーラビリティ | 永続性 |
|----------------|------------|---------|-------------------|-------------|-------------|
| emptyDir | 高 | 非常に低い | 不可 | 制限あり | 一時的 |
| hostPath | 高 | 非常に低い | 不可 | 制限あり | ノード依存 |
| NFS | 中 | 中 | 可能 | 中 | 永続的 |
| FSx for Lustre | 非常に高い | 低い | 可能 | 高い | 永続的 |
| Google Filestore | 高い | 低い | 可能 | 高い | 永続的 |
| Azure NetApp Files | 高い | 低い | 可能 | 高い | 永続的 |

**モデルロードのパフォーマンス最適化戦略:**
1. **メモリマッピング**: 大規模モデルファイルをメモリへ直接マッピングしてロード時間を削減
2. **モデルシャーディング**: モデルを複数の shard に分割して並列ロード
3. **キャッシュ**: 頻繁に使用するモデルをメモリにキャッシュして再ロードを防止
4. **事前ロード**: サービス起動時にモデルを事前ロードして、最初のリクエストのレイテンシを削減

**他の選択肢の問題点:**
- A. emptyDir volume: Pod の再起動時にデータが失われる一時ストレージです。大規模モデルファイルの保存には適していません。
- B. hostPath volume: ノードローカルストレージに依存するため、マルチノード環境でのデータ共有が困難です。
- D. 通常のネットワークファイルシステム（NFS）: スループットとレイテンシの面で、高性能分散ファイルシステムよりパフォーマンスが低くなります。
</details>

### 4. vLLM における Tensor Parallelism の主な目的は何ですか？

A. 複数のユーザーリクエストを並列処理する
B. 大規模モデルを複数の GPU に分散してメモリ要件を減らす
C. データ前処理を高速化する
D. ネットワーク通信を最適化する

<details>
<summary>回答を表示</summary>

**回答: B. 大規模モデルを複数の GPU に分散してメモリ要件を減らす**

**解説:**
vLLM における Tensor Parallelism の主な目的は、大規模モデルを複数の GPU に分散してメモリ要件を減らすことです。大規模言語モデル（LLM）は、多くの場合、単一 GPU のメモリ容量を超える数十億または数千億のパラメータを持ちます。Tensor parallelism はモデルレイヤーを複数の GPU に分割し、各 GPU がモデルの一部だけを保存・処理することでこの問題を解決します。

**Tensor Parallelism の仕組み:**
1. **モデル分割**: モデルの各レイヤー（特に attention と MLP レイヤー）を複数 GPU に分割します。
2. **並列計算**: 各 GPU は、割り当てられたモデル部分の計算を実行します。
3. **同期**: 必要に応じて GPU 間で中間結果を同期します。
4. **結果の集約**: 各 GPU の結果を集約して最終出力を生成します。

**vLLM における Tensor parallelism の設定例:**
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

**Tensor parallelism サイズの選択ガイド:**
1. **モデルサイズ**: 必要な Tensor parallelism サイズはモデルパラメータ数に依存します。
   - 7B パラメータモデル: 1～2 GPU
   - 13B パラメータモデル: 2～4 GPU
   - 70B パラメータモデル: 8～16 GPU
   - 175B パラメータモデル: 16 台以上の GPU

2. **GPU メモリ**: 利用可能な GPU メモリに基づいて Tensor parallelism サイズを調整する必要があります。
   - 24GB GPU: 小規模モデルに適する
   - 40GB GPU: 中規模モデルに適する
   - 80GB GPU: 大規模モデルに適する

3. **パフォーマンス上の考慮事項**: Tensor parallelism は GPU 間通信のオーバーヘッドを発生させます。
   - Tensor parallelism サイズが小さすぎる場合: メモリ不足の問題
   - Tensor parallelism サイズが大きすぎる場合: 通信オーバーヘッドによるパフォーマンス低下

**Tensor Parallelism と他の並列化手法の比較:**
1. **Data Parallelism**: 同じモデルの複数コピーが異なるデータバッチを処理します。主にトレーニングで使用されます。
2. **Pipeline Parallelism**: モデルレイヤーを複数 GPU に順番に分散します。
3. **Tensor Parallelism**: 個別レイヤーの計算を複数 GPU に分散します。

**Tensor Parallelism の利点:**
1. **メモリ効率**: 大規模モデルを複数 GPU に分散することでメモリ要件を削減
2. **単一リクエストのレイテンシ短縮**: 並列計算により推論速度を向上
3. **リソース使用率の向上**: GPU リソースをより効率的に利用

**Tensor Parallelism の欠点:**
1. **通信オーバーヘッド**: GPU 間のデータ転送によるオーバーヘッド
2. **実装の複雑性**: 複雑なモデル分割および同期ロジック
3. **ハードウェア要件**: 高速 GPU インターコネクト（NVLink、NVSwitch など）が必要

**他の選択肢の問題点:**
- A. 複数のユーザーリクエストを並列処理する: これはバッチ処理またはリクエスト並列化の目的です。
- C. データ前処理を高速化する: Tensor parallelism はデータ前処理ではなく、モデル推論に重点を置きます。
- D. ネットワーク通信を最適化する: Tensor parallelism はネットワーク通信を最適化するのではなく、むしろ追加の通信を発生させます。
</details>

### 5. Kubernetes で vLLM サービスの高可用性を確保する最も効果的な方法は何ですか？

A. 単一の Pod に複数コンテナをデプロイする
B. 複数 replica と適切なリソース requests/limits を備えた Deployment を使用する
C. DaemonSet で全ノードにデプロイする
D. CronJob で定期的に再起動する

<details>
<summary>回答を表示</summary>

**回答: B. 複数 replica と適切なリソース requests/limits を備えた Deployment を使用する**

**解説:**
Kubernetes で vLLM サービスの高可用性を確保する最も効果的な方法は、複数 replica と適切なリソース requests/limits を備えた Deployment を使用することです。この方法では、サービスを中断せずにトラフィックを処理し、ノード障害時には自動復旧を行い、負荷に応じたスケーリングを実現できます。

**高可用性 vLLM デプロイメント設定例:**
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

**Service 設定例:**
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

**Horizontal Pod Autoscaling 設定例:**
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

**高可用性のための追加設定:**

1. **Pod Disruption Budget（PDB）の設定**:
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

2. **ノード affinity と toleration**:
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

**高可用性設定の主な利点:**
1. **耐障害性**: ノードまたは Pod が障害を起こしてもサービスを継続
2. **ロードバランシング**: 複数インスタンスにトラフィックを分散
3. **ゼロダウンタイム更新**: RollingUpdate による中断なしのデプロイ
4. **自動スケーリング**: 負荷に基づく自動スケーリング
5. **自動復旧**: 障害が発生した Pod を自動再起動

**ロードバランシング戦略:**
1. **内部 Service のロードバランシング**: Kubernetes Service による基本的なロードバランシング
2. **外部ロードバランシング**: Ingress またはクラウドロードバランサーによる外部トラフィックの分散
3. **Session affinity**: 必要に応じて同じクライアントのリクエストを同じ Pod にルーティング

**監視とアラート:**
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

**他の選択肢の問題点:**
- A. 単一の Pod に複数コンテナをデプロイする: ノード障害時にサービス全体が中断する可能性があり、真の高可用性を提供しません。
- C. DaemonSet で全ノードにデプロイする: すべてのノードに GPU がある保証はなく、リソースの浪費につながる可能性があります。
- D. CronJob で定期的に再起動する: サービスの中断を引き起こすため、高可用性のソリューションではありません。
</details>

### 6. vLLM における「Continuous Batching」の主な利点は何ですか？

A. モデル精度の向上
B. スループットの向上と GPU 使用率の改善
C. モデルサイズの削減
D. ネットワーク帯域幅の節約

<details>
<summary>回答を表示</summary>

**回答: B. スループットの向上と GPU 使用率の改善**

**解説:**
vLLM における「Continuous Batching」の主な利点は、スループットの向上と GPU 使用率の改善です。Continuous batching は、さまざまな長さと開始時刻のリクエストを動的にバッチへグループ化して処理します。これにより GPU リソースをより効率的に使用し、システム全体のスループットを大幅に向上させます。

**従来の batching と Continuous batching の比較:**
1. **従来の batching**:
   - 固定サイズのバッチを形成するまでリクエストを待機させる
   - すべてのリクエストが同時に開始・終了する
   - バッチ内で最長のシーケンスに合わせる padding が必要
   - 新規リクエストは現在のバッチが完了するまで待機する必要がある

2. **Continuous batching**:
   - リクエストの到着に合わせて動的に処理する
   - 開始時刻と長さが異なるリクエストを同時に処理する
   - 不要な padding を使わず、メモリを効率的に使用する
   - 完了したリクエストのリソースを直ちに新規リクエストへ割り当てる

**Continuous Batching の仕組み:**
1. **動的リクエストスケジューリング**: リクエスト到着時に直ちに処理を開始
2. **トークン単位の処理**: 各リクエストはトークンごとに処理され、各ステップで新しいトークンを生成
3. **リソースの再割り当て**: 完了したリクエストのリソースを直ちに新規リクエストへ割り当て
4. **KV cache 管理**: PagedAttention による効率的な KV cache 管理

**Continuous Batching の利点:**
1. **高スループット**: GPU リソースのより効率的な利用により、毎秒処理するリクエスト数を増加
2. **低レイテンシ**: リクエストはバッチ形成を待つ必要がない
3. **リソース使用率の向上**: GPU 計算およびメモリリソースのアイドル時間を削減
4. **さまざまなリクエスト長への対応**: 異なる長さのリクエストを効率的に処理

**vLLM 設定での Continuous batching 設定:**
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

**Continuous batching のパフォーマンス最適化:**
1. **最適なバッチサイズの設定**:
   - `max-num-batched-tokens`: 一度に処理できる最大トークン数
   - `max-num-seqs`: 同時に処理できる最大シーケンス数

2. **GPU メモリ使用率の調整**:
   - `gpu-memory-utilization`: GPU メモリ使用率を設定（0.0～1.0）

3. **KV cache 管理**:
   - `max-model-len`: 最大コンテキスト長を設定
   - `block-size`: PagedAttention ブロックサイズを設定

**パフォーマンスベンチマーク例:**
| バッチ処理方式 | スループット（req/sec） | 平均レイテンシ（ms） | GPU 使用率（%） |
|-----------------|----------------------|----------------------|---------------------|
| Static batching | 10 | 500 | 60% |
| Continuous batching | 25 | 300 | 90% |

**Continuous Batching の制限事項:**
1. **メモリ管理の複雑さ**: 動的なメモリ割り当てと解放による複雑さの増加
2. **スケジューリングオーバーヘッド**: 動的リクエストスケジューリングによる追加オーバーヘッド
3. **最適化の難しさ**: 多様なワークロードに対して最適なパラメータを設定する難しさ

**他の選択肢の問題点:**
- A. モデル精度の向上: Continuous batching はモデル精度に影響しません。
- C. モデルサイズの削減: Continuous batching はモデルサイズを変更しません。
- D. ネットワーク帯域幅の節約: Continuous batching はネットワーク帯域幅の使用量に直接影響しません。
</details>

### 7. Kubernetes で vLLM サービスを監視する際に最も重要なメトリクスは何ですか？

A. Pod の再起動回数
B. 推論レイテンシ、スループット、GPU メモリ使用量
C. ネットワークパケット損失率
D. ディスク I/O パフォーマンス

<details>
<summary>回答を表示</summary>

**回答: B. 推論レイテンシ、スループット、GPU メモリ使用量**

**解説:**
Kubernetes で vLLM サービスを監視する際に最も重要なメトリクスは、推論レイテンシ、スループット、および GPU メモリ使用量です。これらのメトリクスは vLLM サービスのパフォーマンス、効率、リソース使用率を直接示し、サービス品質（QoS）とユーザーエクスペリエンスに直接影響します。

**主要な監視メトリクス:**

1. **推論レイテンシ**:
   - **定義**: リクエスト受信からレスポンス返却までの時間
   - **重要性**: ユーザーエクスペリエンスとサービス応答性に直接影響
   - **測定単位**: ミリ秒（ms）または秒（s）
   - **詳細メトリクス**:
     - Time to First Token
     - Time per Token
     - Total Generation Time

2. **スループット**:
   - **定義**: 単位時間あたりに処理できるリクエスト数またはトークン数
   - **重要性**: システム容量とスケーラビリティの評価
   - **測定単位**: Requests per Second（RPS）または Tokens per Second（TPS）
   - **詳細メトリクス**:
     - Requests per Second
     - Tokens per Second
     - Batch Size

3. **GPU メモリ使用量**:
   - **定義**: vLLM サービスが使用する GPU メモリ量
   - **重要性**: メモリ不足の防止とリソース最適化
   - **測定単位**: ギガバイト（GB）またはメガバイト（MB）
   - **詳細メトリクス**:
     - モデル重みのメモリ使用量
     - KV cache のメモリ使用量
     - Activation メモリ使用量
     - GPU メモリ総使用量

**Prometheus メトリクス設定例:**
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

**Prometheus ServiceMonitor の設定:**
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

**主要な vLLM メトリクスと PromQL クエリ:**

1. **推論レイテンシ**:
   ```
   # 95th percentile inference latency
   histogram_quantile(0.95, sum(rate(vllm_request_latency_seconds_bucket[5m])) by (le))

   # Average time per token generation
   avg(rate(vllm_token_generation_time_seconds_sum[5m]) / rate(vllm_token_generation_time_seconds_count[5m]))
   ```

2. **スループット**:
   ```
   # Requests per second
   sum(rate(vllm_requests_total[5m]))

   # Tokens per second
   sum(rate(vllm_generated_tokens_total[5m]))
   ```

3. **GPU メモリ使用量**:
   ```
   # GPU memory usage
   vllm_gpu_memory_used_bytes

   # KV cache memory usage
   vllm_kv_cache_memory_bytes
   ```

**Grafana ダッシュボード設定例:**
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

**アラートルール設定例:**
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

**追加の監視メトリクス:**
1. **GPU 使用率**: GPU 計算ユニットの使用率
2. **CPU 使用量**: 前処理と後処理に使用する CPU リソース
3. **システムメモリ使用量**: ホストメモリ使用量
4. **エラー率**: 失敗したリクエストの割合
5. **キュー長**: 処理待ちリクエスト数
6. **バッチ効率**: 平均バッチサイズと使用率

**監視ツールの統合:**
1. **Prometheus + Grafana**: メトリクスの収集と可視化
2. **NVIDIA DCGM Exporter**: GPU メトリクスの収集
3. **Jaeger/Zipkin**: 分散トレーシング
4. **ELK Stack**: ログの収集と分析

**他の選択肢の問題点:**
- A. Pod の再起動回数: システム安定性の指標ですが、vLLM サービスのパフォーマンスを直接反映しません。
- C. ネットワークパケット損失率: ネットワーク問題の診断には有用ですが、vLLM サービスの中核的なパフォーマンスメトリクスではありません。
- D. ディスク I/O パフォーマンス: モデルロード時には重要となることがありますが、実行中の vLLM サービスパフォーマンスには重要度が低くなります。
</details>

### 8. Kubernetes における vLLM サービスの最適なネットワーク設定は何ですか？

A. デフォルトの CNI plugin を使用する
B. Tensor parallelism 用の高性能ネットワークインターフェイスと RDMA サポート
C. network policy で全トラフィックを制限する
D. service mesh を実装する

<details>
<summary>回答を表示</summary>

**回答: B. Tensor parallelism 用の高性能ネットワークインターフェイスと RDMA サポート**

**解説:**
Kubernetes における vLLM サービスの最適なネットワーク設定は、Tensor parallelism 用の高性能ネットワークインターフェイスと RDMA（Remote Direct Memory Access）サポートです。大規模言語モデルを複数 GPU に分散して実行する場合、GPU 間通信のパフォーマンスはシステム全体のパフォーマンスに大きく影響します。高性能ネットワークインターフェイスと RDMA サポートは、GPU 間データ転送のレイテンシを最小化し、スループットを最大化して分散推論のパフォーマンスを向上させます。

**高性能ネットワーキングの重要性:**
1. **Tensor parallelism**: モデルレイヤーを複数 GPU に分散するときに頻繁な GPU 間通信が必要
2. **モデルシャーディング**: 大規模モデルを複数ノードに分散するときはノード間ネットワーク性能が重要
3. **レイテンシ感度**: GPU 間通信レイテンシは推論全体のレイテンシに直接影響
4. **帯域幅要件**: 大規模 tensor データの転送には高帯域幅が必要

**最適なネットワーク設定の構成要素:**

1. **高性能ネットワークインターフェイス**:
   - **NVIDIA ConnectX-6/7**: 最大 200Gbps の帯域幅をサポート
   - **InfiniBand**: 超低レイテンシ・高帯域幅ネットワーキング
   - **RDMA over Converged Ethernet（RoCE）**: Ethernet ネットワーク上での RDMA 機能

2. **RDMA（Remote Direct Memory Access）サポート**:
   - CPU を介さない GPU メモリ間の直接データ転送
   - レイテンシを最小化しスループットを最大化
   - GPU Direct RDMA: GPU メモリ間の直接データ転送

3. **NVLink/NVSwitch**:
   - 同一ノード内の GPU 間の高速接続
   - 最大 600GB/s の帯域幅（NVLink 4.0）
   - マルチ GPU システムで重要

**Kubernetes での高性能ネットワーキング設定:**

1. **SR-IOV（Single Root I/O Virtualization）Network Device Plugin**:
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

2. **NetworkAttachmentDefinition の設定**:
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

3. **vLLM デプロイメントに高性能ネットワーク設定を適用する**:
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

**NCCL（NVIDIA Collective Communications Library）の設定:**
NCCL は GPU 間通信を最適化するライブラリであり、次の環境変数で設定できます。

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

**マルチノード分散設定:**
vLLM を複数ノードに分散する場合、ノード間のネットワークパフォーマンスはさらに重要になります。以下の設定が必要です。

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

**ネットワークパフォーマンステスト:**
```bash
# Run NCCL test
kubectl run nccl-test --image=nvidia/cuda:11.8.0-devel-ubuntu22.04 --overrides='{"spec": {"containers": [{"name": "nccl-test", "image": "nvidia/cuda:11.8.0-devel-ubuntu22.04", "command": ["/bin/bash", "-c"], "args": ["apt-get update && apt-get install -y git && git clone https://github.com/NVIDIA/nccl-tests.git && cd nccl-tests && make && ./build/all_reduce_perf -b 8 -e 128M -f 2 -g 8"], "resources": {"limits": {"nvidia.com/gpu": 8}}}]}}' --restart=Never

# Network bandwidth test
kubectl run iperf3-server --image=networkstatic/iperf3 --port=5201 -- -s
kubectl expose pod iperf3-server --port=5201 --target-port=5201
kubectl run iperf3-client --image=networkstatic/iperf3 --rm -it -- -c iperf3-server -p 5201 -t 30
```

**他の選択肢の問題点:**
- A. デフォルトの CNI plugin を使用する: デフォルトの CNI plugin は一般に RDMA などの高性能ネットワーキング機能をサポートせず、Tensor parallelism に必要なパフォーマンスを提供しません。
- C. network policy で全トラフィックを制限する: セキュリティは向上しますが、パフォーマンスは改善せず、追加のオーバーヘッドを発生させる可能性があります。
- D. service mesh を実装する: service mesh はマイクロサービスアーキテクチャには有用ですが、vLLM のような高性能コンピューティングワークロードには不要なオーバーヘッドを追加します。
</details>

### 9. Kubernetes における vLLM サービスのスケーラビリティを改善する最も効果的な方法は何ですか？

A. CPU コアを追加で割り当てる
B. Horizontal scaling（複数 replica）とロードバランシング、および Vertical scaling（より大きな GPU）の組み合わせ
C. メモリを追加で割り当てる
D. より大きな PersistentVolume をプロビジョニングする

<details>
<summary>回答を表示</summary>

**回答: B. Horizontal scaling（複数 replica）とロードバランシング、および Vertical scaling（より大きな GPU）の組み合わせ**

**解説:**
Kubernetes における vLLM サービスのスケーラビリティを改善する最も効果的な方法は、Horizontal scaling（複数 replica）とロードバランシング、および Vertical scaling（より大きな GPU）の組み合わせです。このアプローチは、さまざまなワークロード要件とリソース制約に柔軟に対応し、コスト効率とパフォーマンスのバランスを取ることができます。

**Horizontal Scaling の利点:**
1. **スループットの向上**: replica を増やすことで、より多くの同時リクエストを処理可能
2. **高可用性**: 一部のインスタンスが失敗してもサービスを継続
3. **地理的分散**: 複数リージョンにデプロイしてレイテンシを削減
4. **コスト効率**: 必要に応じてインスタンス数を調整可能

**Vertical Scaling の利点:**
1. **より大きなモデルのサポート**: 大きな GPU メモリでより大きなモデルをロード可能
2. **単一リクエストのレイテンシ短縮**: より強力な GPU により推論速度を向上
3. **より長いコンテキストの処理**: より多くのメモリでより長いコンテキストを処理可能
4. **通信オーバーヘッドの削減**: 単一 GPU または単一ノード内の複数 GPU を使用する場合に通信オーバーヘッドを削減

**Horizontal scaling の設定例:**
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

**Horizontal auto-scaling の設定:**
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

**Vertical scaling の設定例:**
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

**ロードバランシング設定:**
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

**モデルシャーディングとルーティング:**
さまざまなモデルサイズとタイプをサポートするため、複数の Deployment を組み合わせてルーティングできます。

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

**API gateway 設定:**
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

**スケーラビリティ最適化戦略:**
1. **リクエストルーティングの最適化**:
   - モデルサイズと複雑さに基づき、適切なインスタンスへリクエストをルーティング
   - Session affinity による KV cache 再利用の最適化

2. **リソース割り当ての最適化**:
   - ワークロードの特性に適した GPU タイプを選択
   - 適切な Tensor parallelism サイズを設定

3. **キャッシュ戦略**:
   - 頻繁に使用する prompt とレスポンスをキャッシュ
   - モデル重みのキャッシュ

4. **Hybrid cloud scaling**:
   - オンプレミスとクラウドのリソースを組み合わせる
   - バーストトラフィックに対するクラウドスケーリング

**スケーラビリティのテストとベンチマーク:**
```bash
# Run load test
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**他の選択肢の問題点:**
- A. CPU コアを追加で割り当てる: vLLM は主に GPU-bound であり、CPU コアを追加するだけではパフォーマンスは大きく向上しません。
- C. メモリを追加で割り当てる: システムメモリは重要ですが、GPU メモリが主な制約です。
- D. より大きな PersistentVolume をプロビジョニングする: ストレージ容量はモデル保存には重要ですが、推論パフォーマンスとスケーラビリティには直接影響しません。
</details>

### 10. Kubernetes で vLLM をデプロイする際に最も重要なセキュリティ上の考慮事項は何ですか？

A. NetworkPolicy の設定
B. モデル重みと API key の保護、コンテナセキュリティの強化
C. Pod security policy の設定
D. audit logging の有効化

<details>
<summary>回答を表示</summary>

**回答: B. モデル重みと API key の保護、コンテナセキュリティの強化**

**解説:**
Kubernetes で vLLM をデプロイする際に最も重要なセキュリティ上の考慮事項は、モデル重みと API key の保護、およびコンテナセキュリティの強化です。vLLM サービスは知的財産であるモデル重み、機密性の高い API key、ユーザーデータを扱うため、これらの資産を保護し、コンテナ環境のセキュリティを強化することが最も重要です。

**主なセキュリティ上の考慮事項:**

1. **モデル重みの保護**:
   - モデル重みは知的財産権を伴う貴重な資産です。
   - 不正アクセス、コピー、漏えいから保護する必要があります。
   - 保存時の暗号化と転送中の暗号化が必要です。

2. **API key と認証情報の保護**:
   - API key、token、password などの認証情報は安全に管理する必要があります。
   - Kubernetes Secrets または外部 secret 管理システムを使用する必要があります。
   - 環境変数ではなく、マウントされた volume を通じて secret を提供する必要があります。

3. **コンテナセキュリティの強化**:
   - 最小権限の原則を適用
   - non-root ユーザーとしてコンテナを実行
   - 読み取り専用ファイルシステムを使用
   - 不要な capability と権限を削除

4. **入力検証と出力フィルタリング**:
   - prompt injection 攻撃を防止
   - 機密情報の漏えいを防止
   - 有害なコンテンツをフィルタリング

**モデル重み保護の設定例:**
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

**API key と認証情報の保護:**
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

**コンテナセキュリティの強化:**
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

**NetworkPolicy:**
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

**入力検証と出力フィルタリング:**
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

**RBAC（Role-Based Access Control）の設定:**
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

**Audit logging の設定:**
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

**追加のセキュリティベストプラクティス:**
1. **定期的なセキュリティスキャン**: コンテナイメージと依存関係の脆弱性をスキャン
2. **最小権限の原則**: 必要最小限の権限のみを付与
3. **Immutable infrastructure**: 変更が必要な場合は新しいコンテナをデプロイ
4. **セキュリティ監視**: 異常な動作を検出してアラートを送信
5. **緊急対応計画**: セキュリティインシデントへの対応手順を準備

**他の選択肢の問題点:**
- A. NetworkPolicy の設定: 重要ですが、モデル重みと API key の保護、およびコンテナセキュリティ強化より優先度は低くなります。
- C. Pod security policy の設定: コンテナセキュリティの一部ですが、モデル重みと API key の保護は含まれません。
- D. audit logging の有効化: セキュリティ監視には重要ですが、予防的なセキュリティ対策より優先度は低くなります。
</details>

### 11. このページの、単一の NVIDIA L4 GPU で測定した Qwen2.5-7B-Instruct ベンチマークでは、同時実行数が 1 から 16 に増加したとき、リクエストごとのレイテンシはどうなりましたか？

A. 増加した負荷に比例して、ほぼ 16 倍に増加した
B. 集計スループットがほぼ線形にスケールする一方で、ほぼ横ばいだった（p50 は 5.65s から 7.52s へ、+33%）
C. リクエストが増えると vLLM が prefill ステージをスキップできるため、低下した
D. 同時実行数 16 に達する前に GPU の KV cache メモリが尽きたため、測定できなかった

<details>
<summary>回答を表示</summary>

**回答: B. 集計スループットがほぼ線形にスケールする一方で、ほぼ横ばいだった（p50 は 5.65s から 7.52s へ、+33%）**

**解説:**
これは Continuous batching の中核となる教訓です。vLLM は、すでに実行中のリクエストの後ろに新しいリクエストをキューイングしません。次の scheduler step で batch に参加させるため、GPU は多くの sequence を直列ではなく並列に処理します。この測定では、約 100～128 token の完全なレスポンスの p50 レイテンシは、同時実行数 1 での 5.65s から同時実行数 16 での 7.52s へと 33% 増えただけであり、集計 completion throughput は約 17 tokens/s から 208 tokens/s（client 測定）へスケールしました。このスケーリングは、帯域幅律速の decode を示す特徴です。同時実行数 1 では、token ごとに約 15.2 GB の bf16 重みを GDDR6 メモリからストリーミングするため、この L4 の約 300 GB/s のメモリ帯域幅では、単一リクエストの decode は測定されたおよそ 17～18 tokens/s に制限されます。一方、最も多忙な測定点でも、計算は GPU の約 121 TFLOPS の bf16 上限の数パーセントにすぎません。Batching により多くのリクエストが同じ重みの読み取りをほぼ無料で共有できるため、レイテンシはほとんど変わらない一方で、スループットはほぼ線形にスケールします。

**他の選択肢が誤っている理由:**
- A. これは Continuous batching ではなく、直列の（非バッチ化）リクエスト処理で発生する動作です。
- C. Continuous batching は prefill をスキップしません。新規リクエストはすべて decode の前に prefill を実行しますが、他のリクエストの decode step と並行して実行されるだけです。
- D. この 24GB L4 では、同時実行数 16 における GPU KV cache 使用量のピークはわずか 2.6% であり、枯渇にはほど遠い状態でした。このベンチマークでは、その上限を探るほど同時実行数を増やしていません。
</details>
