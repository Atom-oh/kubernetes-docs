# vLLM デプロイメントクイズ

このクイズでは、Kubernetes で vLLM (Vector Language Model) をデプロイする方法についての理解を確認します。

## クイズの質問

### 1. vLLM (Vector Language Model) の主な目的は何ですか？

A. 画像処理の高速化
B. Large Language Model (LLM) 推論の最適化と高速化
C. Database クエリの最適化
D. Network トラフィック管理

<details>
<summary>回答を表示</summary>

**回答: B. Large Language Model (LLM) 推論の最適化と高速化**

**解説:**
vLLM (Vector Language Model) の主な目的は、Large Language Model (LLM) 推論を最適化し高速化することです。vLLM は PagedAttention と呼ばれる革新的な attention アルゴリズムを使用してメモリ管理を最適化し、高スループットかつ低レイテンシでの LLM 推論を可能にします。

**vLLM の主な機能:**
1. **PagedAttention**: GPU メモリ使用量を最適化する、メモリ効率の高い attention メカニズムです。
2. **Continuous batching**: リクエストを動的にバッチ化してスループットを向上させます。
3. **Distributed inference**: 大規模モデルを複数の GPU と node に分散します。
4. **さまざまなモデルのサポート**: Llama、GPT-NeoX、Falcon、MPT など、さまざまなオープンソース LLM をサポートします。
5. **OpenAI 互換 API**: OpenAI API と互換性のあるインターフェイスを提供します。

**PagedAttention の仕組み:**
PagedAttention は、オペレーティングシステムの仮想メモリ管理から着想を得た手法で、KV (Key-Value) cache を効率的に管理します。従来の手法では各リクエストに固定サイズのメモリブロックを割り当てますが、PagedAttention は必要な分だけメモリを割り当て、それを再利用します。

**vLLM のパフォーマンス上の利点:**
1. **高スループット**: 既存のソリューションと比較して 2〜4 倍高いスループット
2. **メモリ効率**: 最大 8 倍多くの同時リクエストを処理可能
3. **低レイテンシ**: 効率的なメモリ管理により応答時間を短縮
4. **リソース使用率の向上**: GPU リソースをより効率的に利用

**vLLM のユースケース:**
1. **Conversational AI サービス**: Chatbot、仮想アシスタントなど
2. **テキスト生成サービス**: コンテンツ生成、要約、翻訳など
3. **Code 生成と補完**: プログラミング支援ツール
4. **大規模テキスト処理**: ドキュメント分析、情報抽出など

**他の選択肢の問題点:**
- A. 画像処理の高速化: vLLM はテキストベースの言語モデル向けであり、画像処理に特化していません。
- C. Database クエリの最適化: vLLM は Database クエリの最適化とは関係ありません。
- D. Network トラフィック管理: vLLM は Network トラフィック管理とは関係ありません。
</details>

### 2. Kubernetes で vLLM をデプロイする際に最も重要なリソース要件は何ですか？

A. 大量の CPU とメモリ
B. 高性能 GPU と十分な GPU メモリ
C. 高速 Network インターフェイス
D. 大容量の永続 storage

<details>
<summary>回答を表示</summary>

**回答: B. 高性能 GPU と十分な GPU メモリ**

**解説:**
Kubernetes で vLLM をデプロイする際に最も重要なリソース要件は、高性能 GPU と十分な GPU メモリです。Large Language Models (LLMs) は数十億から数千億の parameter を持つため、これらのモデルを効率的に実行するには、強力な GPU コンピューティング能力と、モデル parameter を格納するための十分な GPU メモリが不可欠です。

**GPU 要件:**
1. **GPU type**: NVIDIA A100、H100、V100、RTX A6000 などの高性能 GPU
2. **GPU メモリ**: モデルサイズによって異なりますが、一般的には次のとおりです:
   - 7B parameter モデル: 最低 16GB GPU メモリ
   - 13B parameter モデル: 最低 24GB GPU メモリ
   - 70B parameter モデル: 最低 80GB GPU メモリ、または複数 GPU への分散
3. **GPU の数**: スループット要件とモデルサイズによって異なりますが、大規模モデルは複数の GPU に分散する必要があります。

**vLLM deployment の GPU resource request 例:**
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

**大規模モデル向け distributed deployment の例:**
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
LLM の GPU メモリ要件は、次の要素によって決まります:
1. **Model parameters**: 各 parameter は通常 2 bytes (FP16) または 4 bytes (FP32) を使用します。
2. **KV cache**: 各 token の key-value cache には追加のメモリが必要です。
3. **Batch size**: 同時リクエスト数が増えるほど、メモリ要件も増加します。
4. **Context length**: より長い context length には、より多くの KV cache メモリが必要です。

**概算メモリ要件の式:**
```
Required GPU memory = Model size + (batch size x sequence length x hidden size x layers x 4 bytes)
```

**その他のリソース要件:**
1. **CPU**: 前処理と後処理に十分な CPU core
2. **System memory**: モデルの読み込みと処理に十分な RAM
3. **Storage**: model weight ファイル用の十分な storage
4. **Network**: distributed inference 用の高速 network 接続

**他の選択肢の問題点:**
- A. 大量の CPU とメモリ: CPU は LLM 推論には効率的ではなく、system memory だけでは GPU メモリを代替できません。
- C. 高速 Network インターフェイス: distributed inference では重要ですが、GPU と GPU メモリより優先度は低いです。
- D. 大容量の永続 storage: model weight の storage には必要ですが、推論性能には直接影響しません。
</details>
### 3. Kubernetes の vLLM に最適な storage ソリューションは何ですか？

A. emptyDir volume
B. hostPath volume
C. 高性能 distributed file system (例: FSx for Lustre)
D. 通常の network file system (NFS)

<details>
<summary>回答を表示</summary>

**回答: C. 高性能 distributed file system (例: FSx for Lustre)**

**解説:**
Kubernetes の vLLM に最適な storage ソリューションは、高性能 distributed file system (例: FSx for Lustre) です。vLLM は large language models を処理するために model weight ファイルを迅速に読み込む必要があり、distributed inference 環境では複数の node が同じモデルファイルに同時にアクセスする必要があります。高性能 distributed file system は、高スループット、低レイテンシ、並列アクセス機能を提供することで、これらの要件を満たします。

**高性能 distributed file system の利点:**
1. **高スループット**: 大きなモデルファイルを迅速に読み込めます。
2. **並列アクセス**: 複数の node が同じファイルに同時にアクセスできます。
3. **スケーラビリティ**: 必要に応じて storage 容量と性能を拡張できます。
4. **データ整合性**: 複数の node 間で一貫したデータビューを提供します。
5. **耐久性**: データ複製とバックアップ機能によりデータ損失のリスクを低減します。

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

**他の storage オプションとの比較:**

| Storage Option | Throughput | Latency | Multi-node Access | Scalability | Persistence |
|----------------|------------|---------|-------------------|-------------|-------------|
| emptyDir | High | Very low | Not possible | Limited | Temporary |
| hostPath | High | Very low | Not possible | Limited | Node-dependent |
| NFS | Medium | Medium | Possible | Medium | Persistent |
| FSx for Lustre | Very high | Low | Possible | High | Persistent |
| Google Filestore | High | Low | Possible | High | Persistent |
| Azure NetApp Files | High | Low | Possible | High | Persistent |

**Model loading 性能の最適化戦略:**
1. **Memory mapping**: 大きなモデルファイルをメモリに直接 mapping することで読み込み時間を短縮します
2. **Model sharding**: モデルを複数の shard に分割し、並列に読み込みます
3. **Caching**: よく使われるモデルをメモリに cache し、再読み込みを防ぎます
4. **Pre-loading**: サービス起動時にモデルを事前読み込みし、初回リクエストのレイテンシを短縮します

**他の選択肢の問題点:**
- A. emptyDir volume: Pod が再起動するとデータが失われる一時 storage です。大きなモデルファイルの保存には適していません。
- B. hostPath volume: node local storage に依存するため、multi-node 環境でのデータ共有が困難です。
- D. 通常の network file system (NFS): スループットとレイテンシの面で、高性能 distributed file system より性能が低くなります。
</details>

### 4. vLLM における Tensor Parallelism の主な目的は何ですか？

A. 複数のユーザーリクエストを並列処理する
B. 大規模モデルを複数の GPU に分散してメモリ要件を削減する
C. データ前処理を高速化する
D. Network 通信を最適化する

<details>
<summary>回答を表示</summary>

**回答: B. 大規模モデルを複数の GPU に分散してメモリ要件を削減する**

**解説:**
vLLM における Tensor Parallelism の主な目的は、大規模モデルを複数の GPU に分散してメモリ要件を削減することです。Large Language Models (LLMs) は、単一 GPU のメモリ容量を超える数十億から数千億の parameter を持つことがよくあります。Tensor parallelism は、モデル層を複数の GPU に分割し、各 GPU がモデルの一部だけを格納して処理することで、この問題を解決します。

**Tensor Parallelism の仕組み:**
1. **Model splitting**: モデルの各層 (特に attention と MLP 層) を複数の GPU に分割します。
2. **Parallel computation**: 各 GPU は、割り当てられたモデル部分に対して計算を実行します。
3. **Synchronization**: 必要に応じて GPU 間で中間結果を同期します。
4. **Result aggregation**: 各 GPU からの結果を集約して最終出力を生成します。

**vLLM における tensor parallelism configuration example:**
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

**Tensor parallelism size の選択ガイド:**
1. **Model size**: 必要な tensor parallelism size は、モデル parameter 数によって異なります。
   - 7B parameter モデル: 1〜2 GPU
   - 13B parameter モデル: 2〜4 GPU
   - 70B parameter モデル: 8〜16 GPU
   - 175B parameter モデル: 16+ GPU

2. **GPU メモリ**: Tensor parallelism size は、利用可能な GPU メモリに基づいて調整する必要があります。
   - 24GB GPU: 小規模モデルに適しています
   - 40GB GPU: 中規模モデルに適しています
   - 80GB GPU: 大規模モデルに適しています

3. **パフォーマンス上の考慮事項**: Tensor parallelism は GPU 間通信のオーバーヘッドを発生させます。
   - tensor parallelism size が小さすぎる場合: メモリ不足の問題
   - tensor parallelism size が大きすぎる場合: 通信オーバーヘッドによる性能低下

**Tensor Parallelism と他の並列化手法の比較:**
1. **Data Parallelism**: 同じモデルの複数コピーが異なるデータ batch を処理します。主に training に使用されます。
2. **Pipeline Parallelism**: モデル層を複数の GPU に順番に分散します。
3. **Tensor Parallelism**: 個々の層の計算を複数の GPU に分散します。

**Tensor Parallelism の利点:**
1. **メモリ効率**: 大規模モデルを複数の GPU に分散することでメモリ要件を削減
2. **単一リクエストのレイテンシ削減**: 並列計算により推論速度を改善
3. **リソース使用率の向上**: GPU リソースをより効率的に利用

**Tensor Parallelism の欠点:**
1. **通信オーバーヘッド**: GPU 間のデータ転送によるオーバーヘッド
2. **実装の複雑さ**: 複雑なモデル分割と同期ロジック
3. **ハードウェア要件**: 高速 GPU interconnect (NVLink、NVSwitch など) が必要

**他の選択肢の問題点:**
- A. 複数のユーザーリクエストを並列処理する: これは batch processing または request parallelism の目的です。
- C. データ前処理を高速化する: Tensor parallelism はデータ前処理ではなく、モデル推論に焦点を当てます。
- D. Network 通信を最適化する: Tensor parallelism は network 通信を最適化するものではなく、むしろ追加の通信を発生させます。
</details>
### 5. Kubernetes で vLLM サービスの高可用性を確保する最も効果的な方法は何ですか？

A. 単一の pod に複数の container をデプロイする
B. 複数の replica と適切な resource requests/limits を持つ Deployment を使用する
C. DaemonSet を使用してすべての node にデプロイする
D. CronJob で定期的に再起動する

<details>
<summary>回答を表示</summary>

**回答: B. 複数の replica と適切な resource requests/limits を持つ Deployment を使用する**

**解説:**
Kubernetes で vLLM サービスの高可用性を確保する最も効果的な方法は、複数の replica と適切な resource requests/limits を持つ Deployment を使用することです。このアプローチは、サービス中断なしにトラフィックを処理し、node 障害時に自動復旧を提供し、負荷に基づく scaling を可能にします。

**高可用性 vLLM deployment configuration example:**
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

**高可用性のための追加設定:**

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

**高可用性設定の主な利点:**
1. **Fault tolerance**: node または pod 障害があってもサービス提供を継続
2. **Load balancing**: 複数の instance にトラフィックを分散
3. **Zero downtime updates**: rolling updates による無停止 deployment
4. **Auto-scaling**: 負荷に基づく自動 scaling
5. **Auto-recovery**: 障害が発生した pod の自動再起動

**Load balancing 戦略:**
1. **Internal service load balancing**: Kubernetes Service による基本的な load balancing
2. **External load balancing**: Ingress または cloud load balancer による外部トラフィック分散
3. **Session affinity**: 必要に応じて同じ client リクエストを同じ pod にルーティング

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

**他の選択肢の問題点:**
- A. 単一の pod に複数の container をデプロイする: node 障害時にサービス全体が中断される可能性があり、真の高可用性を提供しません。
- C. DaemonSet を使用してすべての node にデプロイする: すべての node に GPU がある保証はなく、リソースの無駄を招く可能性があります。
- D. CronJob で定期的に再起動する: サービス中断を引き起こし、高可用性ソリューションではありません。
</details>

### 6. vLLM における "Continuous Batching" の主な利点は何ですか？

A. モデル精度の向上
B. スループットの増加と GPU 使用率の向上
C. モデルサイズの削減
D. Network bandwidth の節約

<details>
<summary>回答を表示</summary>

**回答: B. スループットの増加と GPU 使用率の向上**

**解説:**
vLLM における "Continuous Batching" の主な利点は、スループットの増加と GPU 使用率の向上です。Continuous batching は、さまざまな長さと開始時刻を持つリクエストを動的に batch にまとめて処理し、GPU リソースをより効率的に使用して、システム全体のスループットを大幅に向上させます。

**従来の batching と Continuous batching の比較:**
1. **Traditional batching**:
   - 固定サイズの batch を形成するまでリクエストを待機させます
   - すべてのリクエストが同時に開始し、同時に終了します
   - batch 内の最長 sequence に合わせるため padding が必要です
   - 新しいリクエストは現在の batch が完了するまで待つ必要があります

2. **Continuous batching**:
   - リクエストが到着すると動的に処理します
   - 開始時刻と長さが異なるリクエストを同時に処理します
   - 不要な padding なしで効率的にメモリを使用します
   - 完了したリクエストのリソースを新しいリクエストに即座に割り当てます

**Continuous Batching の仕組み:**
1. **Dynamic request scheduling**: リクエストが到着するとすぐに処理を開始します
2. **Token-by-token processing**: 各リクエストを token 単位で処理し、各 step で新しい token を生成します
3. **Resource reallocation**: 完了したリクエストのリソースを新しいリクエストに即座に割り当てます
4. **KV cache management**: PagedAttention による効率的な KV cache 管理

**Continuous Batching の利点:**
1. **高スループット**: GPU リソースをより効率的に利用することで、1 秒あたりに処理できるリクエスト数が増加
2. **低レイテンシ**: リクエストが batch 形成を待つ必要がありません
3. **リソース使用率の向上**: GPU 計算リソースとメモリリソースの idle time を削減
4. **さまざまなリクエスト長への対応**: 異なる長さのリクエストを効率的に処理

**vLLM configuration における continuous batching settings:**
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

**Continuous batching の性能最適化:**
1. **最適な batch size settings**:
   - `max-num-batched-tokens`: 一度に処理できる最大 token 数
   - `max-num-seqs`: 同時に処理できる最大 sequence 数

2. **GPU memory utilization adjustment**:
   - `gpu-memory-utilization`: GPU メモリ使用率 (0.0〜1.0) を設定

3. **KV cache management**:
   - `max-model-len`: 最大 context length を設定
   - `block-size`: PagedAttention block size を設定

**Performance benchmark example:**
| Batching Method | Throughput (req/sec) | Average Latency (ms) | GPU Utilization (%) |
|-----------------|----------------------|----------------------|---------------------|
| Static batching | 10 | 500 | 60% |
| Continuous batching | 25 | 300 | 90% |

**Continuous Batching の制限事項:**
1. **Memory management complexity**: 動的なメモリ割り当てと解放により複雑さが増加
2. **Scheduling overhead**: 動的な request scheduling による追加オーバーヘッド
3. **Optimization difficulty**: さまざまな workload に対して最適な parameter を設定する難しさ

**他の選択肢の問題点:**
- A. モデル精度の向上: Continuous batching はモデル精度に影響しません。
- C. モデルサイズの削減: Continuous batching はモデルサイズを変更しません。
- D. Network bandwidth の節約: Continuous batching は network bandwidth 使用量に直接影響しません。
</details>
### 7. Kubernetes で vLLM サービスを監視する際に最も重要な metric は何ですか？

A. Pod restart count
B. Inference latency、throughput、GPU memory usage
C. Network packet loss rate
D. Disk I/O performance

<details>
<summary>回答を表示</summary>

**回答: B. Inference latency、throughput、GPU memory usage**

**解説:**
Kubernetes で vLLM サービスを監視する際に最も重要な metrics は、inference latency、throughput、GPU memory usage です。これらの metrics は vLLM サービスの性能、効率、リソース使用率を直接反映し、service quality (QoS) とユーザー体験に直接影響します。

**主要な monitoring metrics:**

1. **Inference Latency**:
   - **定義**: リクエストを受信してから応答を返すまでの時間
   - **重要性**: ユーザー体験とサービス応答性に直接影響
   - **測定単位**: ミリ秒 (ms) または秒 (s)
   - **詳細 metrics**:
     - Time to First Token
     - Time per Token
     - Total Generation Time

2. **Throughput**:
   - **定義**: 単位時間あたりに処理できるリクエスト数または token 数
   - **重要性**: system capacity と scalability の評価
   - **測定単位**: Requests per Second (RPS) または Tokens per Second (TPS)
   - **詳細 metrics**:
     - Requests per Second
     - Tokens per Second
     - Batch Size

3. **GPU memory usage**:
   - **定義**: vLLM サービスが使用する GPU メモリ量
   - **重要性**: メモリ不足の防止とリソース最適化
   - **測定単位**: Gigabytes (GB) または Megabytes (MB)
   - **詳細 metrics**:
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

**主な vLLM metrics と PromQL queries:**

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

**追加の monitoring metrics:**
1. **GPU utilization**: GPU compute unit の使用率
2. **CPU usage**: 前処理と後処理に使用される CPU リソース
3. **System memory usage**: Host memory 使用量
4. **Error rate**: 失敗したリクエストの割合
5. **Queue length**: 処理待ちリクエスト数
6. **Batch efficiency**: 平均 batch size と使用率

**Monitoring tool integration:**
1. **Prometheus + Grafana**: metric 収集と可視化
2. **NVIDIA DCGM Exporter**: GPU metric 収集
3. **Jaeger/Zipkin**: Distributed tracing
4. **ELK Stack**: Log 収集と分析

**他の選択肢の問題点:**
- A. Pod restart count: system stability の指標ですが、vLLM サービス性能を直接反映するものではありません。
- C. Network packet loss rate: network 問題の診断には有用ですが、vLLM サービスの中核的な performance metric ではありません。
- D. Disk I/O performance: モデル読み込み時には重要な場合がありますが、稼働中の vLLM サービス性能にはそれほど重要ではありません。
</details>

### 8. Kubernetes の vLLM サービスに最適な network configuration は何ですか？

A. デフォルトの CNI plugin を使用する
B. Tensor parallelism のための高性能 network interface と RDMA support
C. Network policies ですべての traffic を制限する
D. Service mesh を実装する

<details>
<summary>回答を表示</summary>

**回答: B. Tensor parallelism のための高性能 network interface と RDMA support**

**解説:**
Kubernetes の vLLM サービスに最適な network configuration は、tensor parallelism のための高性能 network interface と RDMA (Remote Direct Memory Access) support です。大規模言語モデルを複数 GPU に分散して実行する場合、GPU 間通信の性能はシステム全体の性能に大きく影響します。高性能 network interface と RDMA support は、GPU 間データ転送のレイテンシを最小化し、スループットを最大化して、distributed inference の性能を向上させます。

**高性能 networking の重要性:**
1. **Tensor parallelism**: モデル層を複数 GPU に分散する際、頻繁な GPU 間通信が必要です
2. **Model sharding**: 大規模モデルを複数 node に分散する際、node 間の network performance が重要です
3. **Latency sensitivity**: GPU 間通信レイテンシは全体の inference latency に直接影響します
4. **Bandwidth requirements**: 大きな tensor data transfer には高い bandwidth が必要です

**最適な network configuration の構成要素:**

1. **High-performance network interface**:
   - **NVIDIA ConnectX-6/7**: 最大 200Gbps bandwidth をサポート
   - **InfiniBand**: 超低レイテンシ高帯域 networking
   - **RDMA over Converged Ethernet (RoCE)**: Ethernet network 上の RDMA 機能

2. **RDMA (Remote Direct Memory Access) support**:
   - CPU を介さない GPU メモリ間の直接データ転送
   - レイテンシを最小化しスループットを最大化
   - GPU Direct RDMA: GPU メモリ間の直接データ転送

3. **NVLink/NVSwitch**:
   - 同一 node 内の GPU 間の高速接続
   - 最大 600GB/s bandwidth (NVLink 4.0)
   - multi-GPU system で重要

**Kubernetes における高性能 networking configuration:**

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
NCCL は GPU 間通信を最適化する library で、次の environment variables によって設定できます:

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
vLLM を複数 node に分散する場合、node 間の network performance がさらに重要になります。次の設定が必要です:

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

**他の選択肢の問題点:**
- A. デフォルトの CNI plugin を使用する: デフォルトの CNI plugin は通常、RDMA のような高性能 networking 機能をサポートせず、tensor parallelism に必要な性能を提供しません。
- C. Network policies ですべての traffic を制限する: Security を強化できますが、performance は向上せず、追加のオーバーヘッドを加える可能性があります。
- D. Service mesh を実装する: Service mesh は microservices architecture には有用ですが、vLLM のような high-performance computing workload には不要なオーバーヘッドを追加します。
</details>
### 9. Kubernetes で vLLM サービスの scalability を向上させる最も効果的な方法は何ですか？

A. CPU core を増やす
B. Horizontal scaling (複数 replica) と load balancing、vertical scaling (より大きな GPU) の組み合わせ
C. メモリを増やす
D. より大きな persistent volume を provision する

<details>
<summary>回答を表示</summary>

**回答: B. Horizontal scaling (複数 replica) と load balancing、vertical scaling (より大きな GPU) の組み合わせ**

**解説:**
Kubernetes で vLLM サービスの scalability を向上させる最も効果的な方法は、horizontal scaling (複数 replica) と load balancing、vertical scaling (より大きな GPU) の組み合わせです。このアプローチは、さまざまな workload 要件とリソース制約に柔軟に対応でき、cost efficiency と performance のバランスを取ることができます。

**Horizontal Scaling の利点:**
1. **スループットの増加**: より多くの replica により、より多くの同時リクエストを処理できます
2. **高可用性**: 一部の instance が失敗してもサービスを継続できます
3. **地理的分散**: 複数 region にデプロイしてレイテンシを削減できます
4. **Cost efficiency**: 必要に応じて instance 数を調整できます

**Vertical Scaling の利点:**
1. **より大きなモデルのサポート**: より大きな GPU メモリでより大きなモデルを読み込めます
2. **単一リクエストのレイテンシ削減**: より強力な GPU により推論速度が向上します
3. **より長い context の処理**: より多くのメモリでより長い context を処理できます
4. **通信オーバーヘッドの削減**: 単一 GPU または単一 node 内の複数 GPU を使用する場合、通信オーバーヘッドを削減できます

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
複数の deployment を組み合わせて routing することで、さまざまな model size と type をサポートできます:

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
   - model size と complexity に基づいて適切な instance にリクエストを routing
   - session affinity により KV cache 再利用を最適化

2. **Resource allocation optimization**:
   - workload 特性に適した GPU type を選択
   - 適切な tensor parallelism size を設定

3. **Caching strategy**:
   - よく使われる prompt と response を cache
   - model weight caching

4. **Hybrid cloud scaling**:
   - on-premises と cloud resources を組み合わせる
   - burst traffic に対して cloud scaling を使用

**Scalability testing and benchmarking:**
```bash
# Run load test
kubectl run locust --image=locustio/locust --env="LOCUST_HOST=http://vllm-service" --env="LOCUST_LOCUSTFILE=/mnt/locustfile.py" --volume=locustfile.py:/mnt/locustfile.py
```

**他の選択肢の問題点:**
- A. CPU core を増やす: vLLM は主に GPU-bound であり、CPU core を追加するだけでは性能は大きく改善しません。
- C. メモリを増やす: system memory は重要ですが、GPU メモリが主な制約です。
- D. より大きな persistent volume を provision する: storage 容量はモデル保存には重要ですが、推論性能と scalability には直接影響しません。
</details>

### 10. Kubernetes で vLLM をデプロイする際に最も重要な security consideration は何ですか？

A. Network policy configuration
B. Model weights と API keys の保護、container security hardening
C. Pod security policy configuration
D. Audit logging の有効化

<details>
<summary>回答を表示</summary>

**回答: B. Model weights と API keys の保護、container security hardening**

**解説:**
Kubernetes で vLLM をデプロイする際に最も重要な security consideration は、model weights と API keys の保護、および container security hardening です。vLLM サービスは知的財産である model weights、機密性の高い API keys、ユーザーデータを扱うため、これらの資産を保護し、container 環境の security を強化することが最も重要です。

**主な security considerations:**

1. **Model weight protection**:
   - Model weights は知的財産権を持つ価値ある資産です。
   - 不正アクセス、コピー、漏えいから保護する必要があります。
   - 暗号化 storage と転送中の暗号化が必要です。

2. **API key と認証情報の保護**:
   - API keys、tokens、passwords などの認証情報は安全に管理する必要があります。
   - Kubernetes Secrets または外部 secret management systems を使用するべきです。
   - secrets は environment variables ではなく mounted volumes を通じて提供するべきです。

3. **Container security hardening**:
   - 最小権限の原則を適用
   - container を non-root user として実行
   - read-only file system を使用
   - 不要な capabilities と privileges を削除

4. **Input validation and output filtering**:
   - prompt injection attack を防止
   - 機密情報の漏えいを防止
   - 有害なコンテンツを filter

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

**追加の security best practices:**
1. **Regular security scanning**: container images と dependencies の脆弱性を scan
2. **Principle of least privilege**: 必要最小限の privileges のみを付与
3. **Immutable infrastructure**: 変更が必要な場合は新しい containers をデプロイ
4. **Security monitoring**: 異常な behavior を検出して alert を送信
5. **Emergency response plan**: security incidents に対する対応手順を準備

**他の選択肢の問題点:**
- A. Network policy configuration: 重要ですが、model weights と API keys の保護、および container security hardening より優先度は低いです。
- C. Pod security policy configuration: container security の一部ですが、model weight と API key の保護は含まれません。
- D. Audit logging の有効化: security monitoring には重要ですが、予防的 security measures より優先度は低いです。
</details>
