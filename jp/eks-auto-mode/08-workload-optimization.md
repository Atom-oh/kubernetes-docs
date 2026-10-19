# ワークロードに応じた最適化

> **サポート対象バージョン**: EKS Auto Mode GA。例は EKS 1.36 を対象にレビュー
> **最終更新日**: 2026年9月12日

ワークロードに合わせて配置と復旧ポリシーを選び、実際の容量、性能、コストを検証してください。Web とバッチの例は範囲を限定したラボ用設定です。GPU の例は**有効化されていない設定テンプレート**であり、検証済みの学習／推論アプリケーションではありません。推論のレプリカ数は 0 で、旧来の学習 Job は suspend 状態です。GPU／モデルの実行、稼働クラスターへのデプロイ、ベンチマークは実施していません。

[運用ガイド](./05-operations.md)のアカウント／コンテキストガードを使用してください。すべての NodePool は動的であり、物理容量を予約しません。必要な例だけを選び、`default`／カスタム NodeClass の認証主体とサブネットアクセスを確認して、継続的に発生するノード／ストレージ料金も考慮してください。taint と selector は配置を制御しますが、テナント間のセキュリティ境界にはなりません。

## Web サービス: 可用性と復旧

オンデマンドは Spot の中断を避けますが、容量や可用性を保証しません。レプリカ、トポロジ、readiness、disruption policy、永続状態、検証済みの障害復旧が引き続き必要です。

この例は 3 レプリカを使用し、3 つすべてが正常なときに PDB が任意の eviction を 1 つ許可します。PDB 値として `N-1` を文字どおり指定する前提ではありません。従来の 10 レプリカ例はサイジングの一例であり、普遍的な要件ではありません。nginx イメージ／digest と non-root 設定は、レビュー済み運用例に合わせています。probe は 8080 番ポートの `/` を確認しますが、任意のアプリケーションイメージが `/health` を実装しているとは限りません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: workload-lab
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/audit-version: v1.36
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: web-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: web-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: web-tier
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 5m
    budgets:
    - nodes: 10%
  limits:
    cpu: '32'
    memory: 128Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      containers:
      - name: web
        image: nginxinc/nginx-unprivileged:1.30.6@sha256:455cebcadcac0b597cdeaab077d93fb8ad59a98f7ed001dcf8f8693154b5d3d3
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        ports:
        - containerPort: 8080
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        readinessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 2
          failureThreshold: 30
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          periodSeconds: 20
          failureThreshold: 3
      terminationGracePeriodSeconds: 60
      automountServiceAccountToken: false
      nodeSelector:
        karpenter.sh/nodepool: web-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: web-tier
        effect: NoSchedule
      securityContext:
        runAsNonRoot: true
        runAsUser: 101
        runAsGroup: 101
        fsGroup: 101
        seccompProfile:
          type: RuntimeDefault
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 128Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        nodeAffinityPolicy: Honor
        nodeTaintsPolicy: Honor
        labelSelector:
          matchLabels:
            app: web-frontend
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web-frontend
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-frontend
  namespace: workload-lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-frontend
```

ゾーンの hard spread には、少なくとも 2 つの配置可能なドメインが必要です。容量が足りない場合、Pod が Pending のままになることがあります。ホスト名の soft spread は優先設定であり、ノードごとに 1 レプリカを置く保証や 3 AZ の保証ではありません。適用されるラベル、サブネット範囲、障害ポリシーを確認してください。

startup probe は初期化に時間がかかるコンテナを、liveness check による早すぎる再起動から保護します。readiness はエンドポイントとしての適格性を制御し、liveness はコンテナを再起動します。アプリケーションに合わせたしきい値を選び、共有依存先が利用できないときに全レプリカを再起動する liveness check は避けてください。ここに示す probe のタイミングは、測定済みの起動 SLA ではありません。

## バッチ: 再試行はチェックポイント復旧ではない

中断、期限超過、Spot 容量の不足を許容できる Job に限り Spot を使用してください。この NodePool にオンデマンドへのフォールバックはありません。`restartPolicy: OnFailure` は、Pod が存続している場合に失敗したコンテナを再起動できますが、ノード終了で失われたプロセスメモリは復旧しません。アプリケーション側で実装しない限り、`SPOT_AWARE=true` は環境変数にすぎません。

次の Indexed Job は、論理 shard 番号を表示する**スモークテスト例**です。旧来の並列度 20／completions 100 のサイジング例ではなく、並列度 2、completions 5、期限、上限付き再試行を設定しています。データ処理の実装ではありません。レビュー済み BusyBox イメージ index は Linux amd64／arm64 を含みますが、この監査ではイメージを実行していません。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: batch-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - c
        - m
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - spot
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
        - arm64
      - key: eks.amazonaws.com/instance-generation
        operator: Gt
        values:
        - '4'
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: default
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: batch-tier
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: batch-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: 10%
  limits:
    cpu: '16'
    memory: 64Gi
---
apiVersion: batch/v1
kind: Job
metadata:
  name: indexed-smoke
  namespace: workload-lab
spec:
  completionMode: Indexed
  parallelism: 2
  completions: 5
  backoffLimit: 2
  activeDeadlineSeconds: 300
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: indexed-smoke
    spec:
      restartPolicy: Never
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: processor
        image: busybox:1.38.0@sha256:fd7dc98638c8e305f4dc34e979f1c0fdfdcaeb0fbf8fcff77ae834b6da3d7e6e
        command:
        - /bin/sh
        - -ec
        args:
        - printf 'logical shard=%s; smoke only\n' "$JOB_COMPLETION_INDEX"
        env:
        - name: JOB_COMPLETION_INDEX
          valueFrom:
            fieldRef:
              fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
        resources:
          requests:
            cpu: 100m
            memory: 32Mi
          limits:
            cpu: 500m
            memory: 64Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: batch-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: batch-tier
        effect: NoSchedule
```

実際の Job には、冪等な出力コミット、永続チェックポイント、再開ロジックが必要です。Indexed Job でも障害状況によって同一 index が複数回実行されるため、副作用が exactly-once になるとは想定しないでください。TTL による削除の前に、必要なログ／成果物をエクスポートしてください。ノードローカルキャッシュや emptyDir は永続チェックポイントではありません。

`WhenEmpty` は、対象となるアプリケーション作業がなくなった後にノードを削除できます。30 秒の `consolidateAfter` は debounce であり、実行中の Job の完了や、30 秒後のノード削除を保証しません。drift、期限切れ、中断は別のライフサイクル経路です。

## GPU 推論: ノード全体の形状を確認する

Auto Mode は NVIDIA ドライバー／デバイス対応と Bottlerocket イメージを管理します。従来の `amiFamily: AL2023` や `blockDeviceMappings` NodeClass フィールドには対応しません。

| インスタンスタイプ | GPU | GPU メモリ | ホスト vCPU／RAM |
|----------|------|------------|-----------------|
| g5.xlarge | 1 A10G | 24 GB | 4／16 GiB |
| g5.2xlarge | 1 A10G | 24 GB | 8／32 GiB |
| g5.4xlarge | 1 A10G | 24 GB | 16／64 GiB |
| g5.12xlarge | 4 A10G | 合計 96 GB、各 24 GB | 48／192 GiB |
| p5.48xlarge | 8 H100 | 合計 640 GB、各 80 GB | 192／2 TiB |

これらは例であり、最新または常に利用可能な GPU インスタンスの一覧ではありません。合算した GPU メモリは、単一デバイスで連続して使えるメモリではありません。特に、旧 Pod の CPU 4／メモリ 16Gi 要求は、ノード／システム予約と DaemonSet のオーバーヘッドを差し引くと g5.xlarge に収まりません。この推論用 NodePool はより大きな G5 サイズを許可し、未レビューの 1 GPU サービスに 8 GPU の学習ノードを選ばない構成です。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: gpu-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: worker-restricted
  advancedNetworking:
    associatePublicIPAddress: false
  ephemeralStorage:
    size: 200Gi
    iops: 6000
    throughput: 250
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: gpu-tier
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - g
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - g5.2xlarge
        - g5.4xlarge
      - key: eks.amazonaws.com/instance-gpu-manufacturer
        operator: In
        values:
        - nvidia
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: gpu-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: gpu-tier
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 10m
    budgets:
    - nodes: 10%
  limits:
    cpu: '64'
    memory: 256Gi
    nvidia.com/gpu: '4'
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-inference
  namespace: workload-lab
spec:
  replicas: 0
  selector:
    matchLabels:
      app: ml-inference
  template:
    metadata:
      labels:
        app: ml-inference
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: inference
        image: registry.example.invalid/reviewed-inference:replace-me
        resources:
          requests:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
          limits:
            cpu: '4'
            memory: 16Gi
            nvidia.com/gpu: 1
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
      nodeSelector:
        karpenter.sh/nodepool: gpu-tier
      tolerations:
      - key: workload-lab
        operator: Equal
        value: gpu-tier
        effect: NoSchedule
      - key: nvidia.com/gpu
        operator: Equal
        value: 'true'
        effect: NoSchedule
```

意図的に `replicas: 0` のままにしてください。無効な placeholder registry／image を、レビュー済みの不変イメージに置き換え、実際の entrypoint、モデル／入力パス、probe、ストレージ、スコープを限定した workload identity を指定してから有効化します。そのイメージでドライバー／CUDA／ライブラリ互換性、non-root UID 1000、セキュリティポリシーを検証してください。この監査では推論ランタイムを検証していません。

`ephemeralStorage` はノードストレージの設定であり、永続モデル／チェックポイントストレージでもスループット保証でもありません。実際に割り当て可能なストレージとバックエンドデバイスを確認してください。ノードの root／data EBS 暗号化によって、任意の PVC が暗号化されるとは限りません。GPU 数の上限は NodePool リソースを制限するもので、総額を制限するものではなく、急速なプロビジョニング中に一時的な超過もあり得ます。旧来の 16／20 GPU の例はサイジング例であり、このラボでは 4 GPU の低い上限を使用します。

10 分の debounce を設定した `WhenEmpty` は、ワークロード終了後の頻繁な入れ替えを減らせます。GPU 初期化完了までスケジューリングを遅らせる機能でも、ノードのウォーム状態を保証する機能でもありません。事前プロビジョニング済みの容量が適する場合は Static NodePool を利用できますが、制限／集約の意味が異なり、継続コストも発生します。

## 分散学習と EFA

Auto Mode の EFA サポートは現行の機能です。**ディスク設定の横にコメントを書いても EFA は有効になりません。** サポート対象の NodeClass フィールドは `advancedNetworking.networkInterfaces` であり、device plugin は `vpc.amazonaws.com/efa` を公開します。

学習ワークロードを有効化する前に、以下をすべて確認してください。

- Auto Mode は現在、EFA DRA 経路をサポートしていません。別のコンピュートモード用 DRANET ResourceClaim の例ではなく、EFA device plugin を使用してください。
- NVIDIA／Neuron ホストドライバーは Auto Mode が管理しますが、EFA ホスト依存関係だけでは、個別の EFA device plugin がインストール済みで Ready であることを証明できません。
- EFA 専用インターフェイスは RDMA を伝送し、Pod IP は伝送しません。プライマリインターフェイスは card 0／device 0 で type は `interface` です。この例は `efa-only` デバイスを 4 つ、Pod IP 用に `/28` prefix を 1 つ追加します。
- 静的インターフェイス設定は IPv4 のみです。起動後に追加の IP／prefix／ENI は追加されません。複数インターフェイス設定と `associatePublicIPAddress` を組み合わせないでください。ワークロードとシステム Pod の IP 容量を計画してください。
- 互換性のある既存 placement group、対応するプライベート AZ／サブネット、必要な相互参照トラフィックを許可するレビュー済み EFA security group を使用してください。例の AZ／グループ名は placeholder であり、その場所に P5 容量がある証拠ではありません。
- EFA／libfabric／NCCL、プロセス起動／rendezvous、GPU／EFA の近接性、必要な hugepage／memory-lock 設定を確認してください。4 デバイスのインターフェイス例は、P5 の最大ネットワーク帯域幅や、Auto Mode の Bottlerocket ホストで GPU／EFA が自動的に整列することを示すものではありません。

次の同一構成 P5 NodePool は、P4d／P5 の混在ワーカーを交換可能とみなすことを避けます。P4d も代替候補ですが、互換性のある NodePool／ランタイムを別途検証してください。以前の 500Gi／16,000 IOPS／スループット 1,000 および追加 2,000Gi data disk の値は例示です。サポート対象 NodeClass は、そのような任意の追加ブロックデバイスを作成しません。

```yaml
apiVersion: eks.amazonaws.com/v1
kind: NodeClass
metadata:
  name: ml-training-nodeclass
spec:
  instanceProfile: eks-node-instance-profile
  subnetSelectorTerms:
  - tags:
      Name: private-subnet
  securityGroupSelectorTerms:
  - tags:
      Name: reviewed-efa-security-group
  advancedNetworking:
    networkInterfaces:
    - networkCardIndex: 0
      deviceIndex: 0
      interfaceType: interface
      secondaryIPv4PrefixCount: 1
    - networkCardIndex: 0
      deviceIndex: 1
      interfaceType: efa-only
    - networkCardIndex: 1
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 2
      deviceIndex: 0
      interfaceType: efa-only
    - networkCardIndex: 3
      deviceIndex: 0
      interfaceType: efa-only
  ephemeralStorage:
    size: 500Gi
    iops: 16000
    throughput: 1000
  placementGroupSelector:
    name: reviewed-ml-training-pg
---
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: ml-training
spec:
  template:
    spec:
      requirements:
      - key: eks.amazonaws.com/instance-category
        operator: In
        values:
        - p
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
      - key: kubernetes.io/arch
        operator: In
        values:
        - amd64
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - p5.48xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - ap-northeast-2a
      nodeClassRef:
        group: eks.amazonaws.com
        kind: NodeClass
        name: ml-training-nodeclass
      expireAfter: 168h
      terminationGracePeriod: 24h
      taints:
      - key: workload-lab
        value: ml-training
        effect: NoSchedule
      - key: nvidia.com/gpu
        value: 'true'
        effect: NoSchedule
    metadata:
      labels:
        workload-lab: ml-training
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30m
    budgets:
    - nodes: 10%
  limits:
    cpu: '960'
    memory: 10Ti
    nvidia.com/gpu: '40'
```

### 旧 PyTorchJob 構成を保持する場合

`kubeflow.org/v1 PyTorchJob` には**Kubeflow Training Operator V1** が必要です。構造検証ではリリース済み v1.9.3 CRD を使用しました。現行 Kubeflow Trainer の TrainJob／Runtime API は異なります。Auto Mode は NodePool を作成しても、いずれの operator もインストールしません。

このテンプレートは suspend 状態で、意図的に無効な placeholder image を使用します。有効化すると、master 1 台と worker 3 台、各ノード 8 個のローカル GPU プロセス、各 Pod 4 つの EFA デバイス、すなわち **8 GPU ノード 4 台で合計 32 GPU**の構成例になります。NodePool の 40 GPU 上限は、交換時の余力を含め、このノード形状を最大 5 台までにする計画上の値です。予約容量でも厳密な課金上限でもありません。

```yaml
apiVersion: kubeflow.org/v1
kind: PyTorchJob
metadata:
  name: distributed-training
  namespace: workload-lab
spec:
  nprocPerNode: '8'
  runPolicy:
    suspend: true
    activeDeadlineSeconds: 3600
    backoffLimit: 1
    cleanPodPolicy: None
  pytorchReplicaSpecs:
    Master:
      replicas: 1
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
    Worker:
      replicas: 3
      restartPolicy: Never
      template:
        metadata:
          labels:
            app: distributed-training
        spec:
          automountServiceAccountToken: false
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            seccompProfile:
              type: RuntimeDefault
          containers:
          - name: pytorch
            image: registry.example.invalid/reviewed-training:replace-me
            resources:
              requests:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
              limits:
                cpu: '32'
                memory: 128Gi
                nvidia.com/gpu: 8
                vpc.amazonaws.com/efa: 4
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop:
                - ALL
          nodeSelector:
            karpenter.sh/nodepool: ml-training
          tolerations:
          - key: workload-lab
            operator: Equal
            value: ml-training
            effect: NoSchedule
          - key: nvidia.com/gpu
            operator: Equal
            value: 'true'
            effect: NoSchedule
```

suspend を解除する前に、operator の分散起動契約に対応する検証済み image／entrypoint、実際のデータセットパス、永続チェックポイント／成果物のエクスポートを用意してください。operator、queue／gang scheduling の動作、4 ノード分の容量、DNS／rendezvous、ネットワークルール、ランタイム権限、期限を検証してください。これは本番向けの完全な学習手順ではありません。検証済み accelerator runtime が必要とする権限を Restricted namespace のテンプレートで満たせない場合は、別途レビュー済みの workload policy が必要になることがあります。クラスター全体の admission security を無効にして解決しないでください。

実行中の旧 PyTorchJob を suspend すると、稼働中の Pod／PodGroup が削除されます。これはチェックポイント操作ではありません。`cleanPodPolicy: None` は完了済み Pod を調査用に保持しますが、成果物はエクスポートしません。永続エクスポート後に、PVC、ノード、別管理の予約容量を含むクリーンアップを確認してください。

### 実デバイス容量を確認する

以下の読み取り専用スナップショットは、実際に割り当て可能な値と Ready 条件を表示します。GPU／EFA の値がない場合や API が失敗した場合、それをデバイス設定の成功と解釈してはいけません。

```bash
kubectl --context "$KUBE_CONTEXT" --request-timeout=15s get nodes \
  -l eks.amazonaws.com/compute-type=auto -o json |
jq '[.items[]|{name:.metadata.name,
  instanceType:.metadata.labels["node.kubernetes.io/instance-type"],
  pool:.metadata.labels["karpenter.sh/nodepool"],
  allocatable:{cpu:.status.allocatable.cpu,memory:.status.allocatable.memory,
    gpu:.status.allocatable["nvidia.com/gpu"],efa:.status.allocatable["vpc.amazonaws.com/efa"]},
  conditions:[.status.conditions[]?|select(.type=="Ready")|{type,status,reason}]}]'
```

## リソースとアーキテクチャの判断

| ワークロード | 候補となるポリシー | 追加で必要な検証 |
|----------|------------------|-------------------------|
| Web／API | オンデマンドまたは慎重に混在させた容量、中程度の集約 | 可用性予算、レプリカ、ランタイムアーキテクチャ、実測レイテンシ |
| Batch／CI | 再起動と期限の要件が許す場合は Spot | 冪等性、永続的な進捗、再試行、容量不足時の動作 |
| Database／streaming | 状態を考慮した配置と disruption policy | quorum、ボリュームトポロジ、復旧、ネットワーク分断時の動作 |
| GPU 推論 | モデルに見合う GPU／CPU／RAM、必要に応じてウォーム容量 | image／ドライバー互換性、probe、cold start、コスト |
| 分散学習 | 構成を揃えた accelerator pool と検証済みのネットワーク／ランタイム | gang 容量、チェックポイント／エクスポート、EFA デバイス、配置 |

従来の 24h／72h／168h／336h の期限と 30s／1m／5m／10m／15m／30m の集約時間は、ポリシー例でありワークロード種別の既定値ではありません。Auto Mode の最大有効期間と別途設定する termination grace は引き続き適用されます。

CPU bound ワークロードにおける従来の CPU 2／メモリ 2Gi request と CPU 4／メモリ 4Gi limit は、burst policy の一例であり、普遍的なサイジングではありません。メモリ bound ワークロードで request／limit をともに 8Gi にしても、CPU request と limit が異なれば Guaranteed QoS にはなりません。Guaranteed QoS には関連するすべてのコンテナ／リソース条件も影響し、メモリ limit によって OOM が発生することもあります。以前の「使用量の 1.2～1.5 倍」「request の 2 倍」という計算式には、一般的な性能根拠が検証されていません。

device-plugin API では GPU は整数の拡張リソースです。limit を指定し、必要に応じて同じ値の request を指定してください。GPU では request だけを指定する方式ではありません。CPU／メモリ request は、必須のシステム処理に必要なノード割り当て可能容量を残す必要があります。limit だけを下げても、通常、request ベースの bin packing は改善しません。

### マルチアーキテクチャの検証

`nginx:latest` を grep するのではなく、固定した image index を確認してください。index に両方のプラットフォームがあることは、パッケージ検査の前提条件ですが、ネイティブ依存関係やアプリケーション動作の証明ではありません。

```bash
: "${IMAGE_REF:?Set a reviewed image reference pinned by digest}"
if ! [[ "$IMAGE_REF" =~ @sha256:[0-9a-f]{64}$ ]]; then
  printf 'Use an immutable sha256 digest reference.\n' >&2
  exit 1
fi
docker buildx imagetools inspect --raw "$IMAGE_REF" > "$WORK_DIR/image-index.json"
jq -e '[.manifests[]?.platform |
         select(.os=="linux" and (.architecture=="amd64" or .architecture=="arm64")) |
         .architecture] | unique | sort == ["amd64","arm64"]' \
  "$WORK_DIR/image-index.json"
```

自分でレビューした Dockerfile に対して、次の操作は特定されていないイメージの公開ではなく、ローカル OCI archive を生成します。

```bash
: "${BUILD_CONTEXT:?Set the reviewed Dockerfile directory}"
test -f "$BUILD_CONTEXT/Dockerfile"
docker buildx build --platform linux/amd64,linux/arm64 \
  --output "type=oci,dest=$WORK_DIR/app-multiarch.tar" "$BUILD_CONTEXT"
```

このビルドには、適切な Buildx builder、native worker、または正しく設定されたエミュレーション／クロスコンパイルが必要です。通常の registry 公開手順の前に、アーキテクチャ別のアプリケーションテストを実行してください。従来の「Spot／Graviton 混在で約 40% 削減」という値は未検証の推定値です。実際に役立つ処理量あたりのコストは[コスト管理ガイド](./06-cost-management.md)を参照してください。

## 参考資料

- [Auto Mode の AI／ML コンピュート](https://docs.aws.amazon.com/eks/latest/userguide/ml-node-pools.html)
- [NodeClass のストレージと静的ネットワークインターフェイス](https://docs.aws.amazon.com/eks/latest/userguide/create-node-class.html)
- [Auto Mode を含む EFA デバイス管理](https://docs.aws.amazon.com/eks/latest/userguide/device-management-efa.html)
- [G5 インスタンス仕様](https://aws.amazon.com/ec2/instance-types/g5/)
- [P5 インスタンス仕様](https://aws.amazon.com/ec2/instance-types/p5/)
- [Kubernetes Job と Indexed Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Kubernetes GPU スケジューリング](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [リソース request、limit、数量](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [トポロジースプレッド制約](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [startup、readiness、liveness probe](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/)
- [Training Operator v1.9.3 PyTorchJob CRD](https://github.com/kubeflow/training-operator/blob/v1.9.3/manifests/base/crds/kubeflow.org_pytorchjobs.yaml)
- [Kubeflow Trainer と旧 v1 からの移行](https://github.com/kubeflow/trainer)
- [Docker マルチプラットフォームビルド](https://docs.docker.com/build/building/multi-platform/)

< [前へ: ノードのライフサイクル](./07-node-lifecycle.md) | [目次](./README.md) | [次へ: 移行ガイド](./09-migration-guide.md) >
