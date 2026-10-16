# Kubernetes スケジューリング、プリエンプション、Eviction

> **サポート対象バージョン**: Kubernetes 1.34 - 1.36 (Descheduler v0.36 の例)
> **最終更新**: September 17, 2026

Kubernetes において、スケジューリングは Pod を適切な Node に配置するプロセスです。プリエンプションは高優先度の Pod のための空きを確保するために低優先度の Pod を削除するプロセスであり、Eviction は Pod を終了します。ワークロードコントローラーは置き換え用の Pod を作成する場合があり、その Pod はスケジューラーによって別途配置されます。この章では、Kubernetes のスケジューリングメカニズム、Node 選択、プリエンプション、Eviction、および Amazon EKS におけるスケジューリング最適化手法について学びます。

## ラボ環境のセットアップ

このドキュメントの例に従うには、以下のツールと環境が必要です。

### 必要なツール
- API サーバーと 1 マイナーバージョン以内の kubectl
- 動作する Kubernetes クラスター（EKS、minikube、kind など）
- 複数の Node を持つクラスター（スケジューリングテスト用）

### スケジューリング例のセットアップ

```bash
# Create namespace
kubectl create namespace scheduling-demo

# Add labels to nodes (if you have multiple nodes)
kubectl label nodes <node-name> disktype=ssd
kubectl label nodes <node-name> gpu=true

# Create a pod using node affinity
kubectl -n scheduling-demo apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: nginx-ssd
  labels:
    app: nginx
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: disktype
            operator: In
            values:
            - ssd
  containers:
  - name: nginx
    image: nginx
EOF

# Create priority class
kubectl apply -f - <<EOF
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical service pods only."
EOF

# Create Pod Disruption Budget (PDB)
kubectl -n scheduling-demo apply -f - <<EOF
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: nginx
EOF
```

## Kubernetes スケジューリングアーキテクチャ

![Kubernetes スケジューリングアーキテクチャ: kube-scheduler は、配置ポリシーによる制約の下で、キューイング、フィルタリング、スコアリング、バインディングを通じて Pod を処理します。優先度ベースのプリエンプションと Eviction はパイプラインにフィードバックされます。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-0.html)

## スケジューリング概念の比較

| 概念 | 目的 | ユースケース | Kubernetes バージョン |
|---------|---------|-----------|-------------------|
| **Node Selector** | 特定のラベルを持つ Node に Pod を配置 | 単純な Node 選択 | すべてのバージョン |
| **Node Affinity** | 複雑な Node 選択ルールを定義 | 高度な Node 選択 | 1.6+ |
| **Pod Affinity** | 他の Pod の近くに Pod を配置 | 関連 Service の同一配置 | 1.6+ |
| **Pod Anti-Affinity** | 他の Pod から離して Pod を配置 | 高可用性の確保 | 1.6+ |
| **Taints and Tolerations** | 特定の Pod のみを Node 上で許可 | 専用 Node、Node 分離 | 1.6+ |
| **Topology Spread Constraints** | トポロジードメイン全体に Pod を分散 | アベイラビリティーゾーン間の分散 | 1.16+ (1.19 で GA) |
| **Priority and Preemption** | 重要なワークロードを優先 | クリティカルな Service の保証 | 1.8+ (1.11 で GA) |
| **Pod Disruption Budget** | 同時に中断される Pod を制限 | 高可用性の確保 | 1.4+ (1.21 で GA) |

## 基本的なスケジューリングの概念

> **重要な概念**: Kubernetes スケジューラーは、Pod を実行する最適な Node を選択するコントロールプレーンコンポーネントです。フィルタリングとスコアリングの 2 フェーズで動作します。

### スケジューリングプロセス

1. **フィルタリングフェーズ（Predicates）**
   - Pod を実行できる適切な Node のセットを特定します
   - リソース要件、Node Selector、Affinity ルール、Taint/Toleration などを考慮します
   - いずれかの条件を満たさない Node を除外します

2. **スコアリングフェーズ（Priorities）**
   - フィルタリングを通過した Node にスコアを付与します
   - リソース使用率、Pod 分散、Affinity 設定などを考慮します
   - 最も高いスコアの Node を選択します

3. **バインディングフェーズ**
   - 選択した Node に Pod を割り当てます
   - API サーバーのバインディング情報を更新します

## 目次
1. [スケジューリングの概要](#scheduling-overview)
2. [スケジューラーの仕組み](#how-the-scheduler-works)
3. [Node 選択](#node-selection)
4. [Pod Affinity と Anti-Affinity](#pod-affinity-and-anti-affinity)
5. [Taints and Tolerations](#taints-and-tolerations)
6. [Node Affinity](#node-affinity)
7. [Pod Priority と Preemption](#pod-priority-and-preemption)
8. [Pod Eviction](#pod-eviction)
9. [Pod Disruption Budget (PDB)](#pod-disruption-budget-pdb)
10. [Node Pressure Eviction](#node-pressure-eviction)
11. [TopologySpreadConstraints](#topologyspreadconstraints)
12. [Pod Deletion Cost](#pod-deletion-cost)
13. [Descheduler](#descheduler)
14. [Amazon EKS におけるスケジューリング最適化](#scheduling-optimization-in-amazon-eks)
15. [スケジューリングのベストプラクティス](#scheduling-best-practices)
16. [まとめ](#conclusion)

## スケジューリングの概要

Kubernetes スケジューラーは、Pod を適切な Node に配置するコントロールプレーンコンポーネントです。スケジューラーは Pod を配置する最適な Node を決定するために、さまざまな要素を考慮します。

1. **リソース要件**: Pod が要求する CPU、メモリ、その他のリソース
2. **ハードウェア/ソフトウェア/ポリシー制約**: Node Selector、Node Affinity、Taint など
3. **Affinity/Anti-Affinity の仕様**: 他の Pod との配置関係
4. **データローカリティ**: データに近い場所への Pod 配置
5. **ワークロード間の干渉**: 異なるワークロード間の干渉を最小化
6. **カスタム目標**: デッドライン認識またはワークロード干渉認識のスケジューリングには適切なカスタムロジックが必要であり、デフォルトスケジューラーはアプリケーションのデッドラインを推論しません

### スケジューリングプロセス

スケジューリングプロセスは大きく 2 フェーズに分けられます。

1. **フィルタリング**: Pod を実行できる Node のセットを特定します
   - リソース要件が満たされているかを確認
   - Node Selector、Affinity、Taint などの制約を確認

2. **スコアリング**: フィルタリングされた Node をスコアリングして最適な Node を選択します
   - リソース使用率のバランス
   - Pod 間 Affinity/Anti-Affinity
   - データローカリティ
   - Taint/Toleration

## スケジューラーの仕組み

Kubernetes スケジューラーは次のプロセスで動作します。

![Pod 作成イベントがスケジューリングキュー、kube-scheduler、Filter プラグイン、Score プラグイン、最適 Node の選択、API サーバーへのバインディングリクエストを経由して、Pod が Node に配置されるまでを示すパイプライン図。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-1.html)

1. **Pod キューの監視**: スケジューラーは、未スケジュールの Pod を API サーバーで監視します。
2. **Node のフィルタリング**: Pod を実行できる Node のセットを特定します。
3. **Node のスコアリング**: フィルタリングされた Node をスコアリングします。
4. **Node の選択**: 最も高いスコアの Node を選択します。
5. **バインディング**: 選択した Node に Pod をバインドします。

### スケジューリングプラグイン

Kubernetes スケジューラーはプラグインアーキテクチャを使用して拡張できるよう設計されています。さまざまなプラグインがスケジューリングプロセスの異なる段階で動作します。

1. **Filter プラグイン**: Pod を実行できない Node をフィルタリングします
   - NodeResourcesFit: Node のリソース容量を確認
   - NodeName: Pod の nodeName フィールドを確認
   - NodeUnschedulable: Node のスケジュール可否を確認
   - TaintToleration: Taint と Toleration を確認

2. **Score プラグイン**: Node にスコアを付与します
   - NodeResourcesBalancedAllocation: リソース使用量のバランスを考慮
   - ImageLocality: イメージローカリティを考慮
   - InterPodAffinity: Pod 間 Affinity を考慮
   - NodeAffinity: Node Affinity を考慮

### NodeResourcesFit スコアリング戦略: LeastAllocated と MostAllocated

`NodeResourcesFit` は Filter プラグイン（Node に Pod のための十分な割り当て可能 CPU/メモリがあるか）と Score プラグインの両方です。Score プラグインの挙動は、`KubeSchedulerConfiguration` で設定する `scoringStrategy.type` により制御されます。

- **`LeastAllocated`**（デフォルト）: すでに割り当てられているリソースが*少ない* Node ほど高いスコアを付けます。新しい Pod は最も空いている Node に引き寄せられ、負荷を均等に分散します。
- **`MostAllocated`**: すでに割り当てられているリソースが*多い* Node ほど高いスコアを付けます（Pod が収まる限り）。新しい Pod は最も使用率の高い Node に先に詰め込まれ、他の Node は未使用または空のままになります。
- **`RequestedToCapacityRatio`**: 両者の間を設定可能な曲線で表す戦略です。純粋な最小/最大ではなくカスタム形状が必要な GPU などの拡張リソースに有用です。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: most-allocated-scheduler
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: MostAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
```

Amazon EKS のコントロールプレーンはフルマネージドであるため、デフォルト kube-scheduler の `KubeSchedulerConfiguration` を直接編集することはできません。`MostAllocated` を使用するには、*2 番目の*スケジューラー（この設定で `kube-scheduler` バイナリを実行し、専用の `ServiceAccount` を介して `system:kube-scheduler`/`system:volume-scheduler` にバインドする `Deployment`）を実行し、以下の [複数スケジューラー](#multiple-schedulers) で示すように特定の Pod を `spec.schedulerName` で指定します。これは [カスタムスケジューラーの構築](../scheduling/01-custom-scheduler-part1.md) と同じパターンです。

**検証済みテスト — 分散とビンパッキングの動作。** 実際の違いを確認するため、不均一なベースライン負荷を `nodeName` に固定したフィラー Pod で設定した使い捨ての 3 worker `kind` クラスター（`kubectl version` v1.37.0、隔離済み、テスト後に削除済み — 共有インフラストラクチャには一切影響していません）を使用しました（Node あたり CPU 割り当て可能量は 16）。`worker`=12 Pod（75%）、`worker2`=6 Pod（37%）、`worker3`=0 Pod（0%）です。その後、同一の 1-CPU Pod 6 個を、同じ初期状態に対してデフォルトスケジューラー（`LeastAllocated`）と `MostAllocated` を設定した 2 番目のスケジューラーで、それぞれスケジュールしました。

| スケジューラー / 戦略 | 新しい 6 Pod の配置先 | 最終 CPU 使用率（worker / worker2 / worker3） |
|---|---|---|
| デフォルト（`LeastAllocated`） | すべて `worker3`（最も空いている Node） | 75% / 37% / 37% — 3 Node すべてが使用中 |
| `MostAllocated` | `worker` に 3 個、`worker2` に 3 個（最も使用率の高い 2 Node） | 93% / 56% / 0% — `worker3` は完全にアイドル状態のまま |

`LeastAllocated` は `worker3` を `worker2` と同じ状態になるまで使用率を上げるため、すべての Node が部分的に使用され、どの Node も安全にスケールダウンできなくなります。`MostAllocated` はすでに使用率の高い Node に負荷を集中させ続け、`worker3` を未使用のままにしました。これはまさに、クラスターオートスケーラーまたは Karpenter の統合処理によって終了される Node です。

このため、Karpenter または Cluster Autoscaler と並行して実行する **バッチ/短命な Job ワークロード**では、`MostAllocated` が一般的に推奨されます。Job を少数の Node にビンパッキングすると、完全にアイドル状態となり統合の対象になる Node 数が最大化され、コンピューティングコストを直接削減できます。`LeastAllocated` は、トラフィックの急増や単一のパックされた Node にカスケードする圧力を発生させずに `kubectl drain` を吸収する余裕をすべての Node に残すため、長時間実行されるレイテンシーに敏感な Service には引き続き優れたデフォルトです。

この比較を完全に再現する手順については、[Scheduler Scoring Strategy Lab](../labs/core/08-scheduling-preemption-eviction-lab.md) を参照してください。

### 複数スケジューラー

Kubernetes は複数のスケジューラーを同時に実行できます。これにより、特定のワークロード向けにカスタムスケジューリングロジックを実装できます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
spec:
  schedulerName: my-custom-scheduler
  containers:
  - name: container
    image: nginx
```

上記の例では、`schedulerName` フィールドが Pod をスケジュールするスケジューラーを指定します。

## Node 選択

Kubernetes には Pod を特定の Node に配置する複数のメカニズムがあります。

![3 つの Node 配置メカニズムを比較する図: Node ラベルに一致する nodeSelector、特定の Node に固定する nodeName、候補 Zone に対して式を評価する nodeAffinity。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-2.html)

### Node Selector

Node Selector は、特定のラベルを持つ Node にのみ Pod を配置するよう制限する最も簡単な方法です。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-pod
spec:
  nodeSelector:
    gpu: "true"
  containers:
  - name: gpu-container
    image: busybox:1.36
    command: ["sh", "-c", "sleep 3600"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

上記の例では、Pod は `gpu=true` ラベルを持つ Node にのみ配置されます。

GPU の例はスケジューリングのみをテストします。Node には実際に GPU があり、`nvidia.com/gpu` をアドバタイズする動作中のデバイスプラグインが必要です。`gpu=true` ラベルだけでは GPU リソースは割り当てられません。

### nodeName

`nodeName` フィールドを使用して、Pod を特定の Node に直接配置できます。この方法はスケジューラーをバイパスするため、通常は推奨されません。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: specific-node-pod
spec:
  nodeName: worker-node-1
  containers:
  - name: container
    image: nginx
```

上記の例では、Pod は `worker-node-1` という名前の Node に直接配置されます。

## Pod Affinity と Anti-Affinity

Pod Affinity と Anti-Affinity は、Pod 間の関係に基づいて Pod を配置する方法を提供します。

![同じ Node に web Pod と cache Pod を同一配置する Pod Affinity と、異なる Node に 2 つの web Pod レプリカを分離する Pod Anti-Affinity を対比する図。いずれもハードまたはソフト要件として設定できます。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-3.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-3.html)

### Pod Affinity

Pod Affinity は、特定のラベルを持つ Pod と同じ Node またはトポロジードメインに Pod を配置します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
spec:
  affinity:
    podAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname
  containers:
  - name: frontend
    image: nginx
```

上記の例では、`frontend` Pod は `app=cache` ラベルを持つ Pod と同じホストに配置されます。

### Pod Anti-Affinity

Pod Anti-Affinity は、特定のラベルを持つ Pod とは異なる Node またはトポロジードメインに Pod を配置します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  labels:
    app: frontend
spec:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - frontend
        topologyKey: kubernetes.io/hostname
  containers:
  - name: frontend
    image: nginx
```

上記の例では、`frontend` Pod は `app=frontend` ラベルを持つ他の Pod とは異なるホストに配置されます。これは、同じアプリケーションのインスタンスを複数の Node に分散して高可用性を実現する場合に便利です。

### Affinity の種類

Pod Affinity と Anti-Affinity には 2 種類あります。

1. **requiredDuringSchedulingIgnoredDuringExecution**: スケジューリング時に満たす必要があるハード要件
2. **preferredDuringSchedulingIgnoredDuringExecution**: 優先されますが必須ではないソフト要件

```yaml
# preferredDuringSchedulingIgnoredDuringExecution example
affinity:
  podAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - cache
        topologyKey: kubernetes.io/hostname
```

上記の例では、`weight` フィールドはこの設定の重みを示します。複数の設定がある場合、重みが大きい設定ほど重要と見なされます。

## Taints and Tolerations

Taint と Toleration は、Node が特定の Pod を拒否できるようにするメカニズムです。

![一致する Toleration を持たない限り Pod を拒否する Node Taint、3 つの Taint effect である NoSchedule、PreferNoSchedule、NoExecute、および key=gpu:NoSchedule で Taint された GPU Node が通常の Pod を拒否し、一致する Toleration を持つ GPU Pod を受け入れる例を示す図。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-4.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-4.html)

### Taint

Taint は、Pod が Node にスケジュールされるのを制限するために Node に適用されます。

```bash
# Add taint to node
kubectl taint nodes node1 key=value:NoSchedule
```

Taint effect には 3 種類あります。

1. **NoSchedule**: Toleration のない Pod は Node にスケジュールされません
2. **PreferNoSchedule**: Toleration のない Pod を Node にスケジュールしないことを優先します
3. **NoExecute**: Toleration のない Pod は Node から Eviction されます

### Toleration

Toleration は、Pod が Taint のある Node にスケジュールされることを許可するために Pod に適用されます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  tolerations:
  - key: "key"
    operator: "Equal"
    value: "value"
    effect: "NoSchedule"
  containers:
  - name: nginx
    image: nginx
```

上記の例では、Pod は `key=value:NoSchedule` Taint のある Node にスケジュールできます。

### ユースケース

Taint と Toleration の一般的なユースケースは以下のとおりです。

1. **専用 Node**: 特定のワークロードのみを実行する Node を指定
2. **特殊なハードウェア**: GPU などの特殊なハードウェアを持つ Node を管理
3. **Node メンテナンス**: メンテナンス中の Node への新しい Pod のスケジューリングを防止
4. **Node の問題**: 問題のある Node から Pod を Eviction

### デフォルト Taint

Kubernetes は一部の Node にデフォルト Taint を適用します。

- **node.kubernetes.io/not-ready**: Node の準備ができていません
- **node.kubernetes.io/unreachable**: Node に到達できません
- **node.kubernetes.io/memory-pressure**: Node にメモリプレッシャーがあります
- **node.kubernetes.io/disk-pressure**: Node にディスクプレッシャーがあります
- **node.kubernetes.io/pid-pressure**: Node に PID プレッシャーがあります
- **node.kubernetes.io/network-unavailable**: Node ネットワークを利用できません
- **node.kubernetes.io/unschedulable**: Node はスケジュール不可です

## Node Affinity

Node Affinity は、Pod を特定の Node セットに配置する、より表現力の高い方法を提供します。Node Selector よりも複雑な条件を指定できます。

### Node Affinity の種類

Node Affinity には 2 種類あります。

1. **requiredDuringSchedulingIgnoredDuringExecution**: スケジューリング時に満たす必要があるハード要件
2. **preferredDuringSchedulingIgnoredDuringExecution**: 優先されますが必須ではないソフト要件

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: with-node-affinity
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
        - matchExpressions:
          - key: topology.kubernetes.io/zone
            operator: In
            values:
            - us-west-2a
            - us-west-2b
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: In
            values:
            - another-node-label-value
  containers:
  - name: with-node-affinity
    image: nginx
```

上記の例では、Pod は `topology.kubernetes.io/zone` ラベルが `us-west-2a` または `us-west-2b` である Node にのみ配置されます。さらに、`another-node-label-key=another-node-label-value` ラベルを持つ Node に優先的に配置されます。

### 演算子

Node Affinity はさまざまな演算子をサポートします。

- **In**: ラベル値が指定した値のいずれかに一致
- **NotIn**: ラベル値が指定した値のいずれにも一致しない
- **Exists**: 指定したキーを持つラベルが存在
- **DoesNotExist**: 指定したキーを持つラベルが存在しない
- **Gt**: ラベル値が指定値より大きい
- **Lt**: ラベル値が指定値より小さい

## Pod Priority と Preemption

Kubernetes は、重要なワークロードがクラスターリソースを確保できるよう、Pod Priority と Preemption の機能を提供します。

![PriorityClass が Pod に優先度を割り当て、リソースが不足したときに低優先度 Pod の Preemption をトリガーする様子、高優先度 Pod のスケジューリング失敗からスケジュールまでの 4 ステップの Preemption プロセス、および組み込み PriorityClass の例を示す図。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-5.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-5.html)

### PriorityClass

PriorityClass は Pod の相対的な重要度を定義します。優先度の値が高いほど、Pod は重要です。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "This priority class should be used for critical workloads."
```

上記の例では、`value` フィールドは優先度の値を示します。値が高いほど、優先度も高くなります。`globalDefault` フィールドを `true` に設定すると、この PriorityClass は PriorityClass を指定していない Pod に適用されます。

### Pod への PriorityClass の適用

Pod に PriorityClass を適用するには、`priorityClassName` フィールドを使用します。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority
  containers:
  - name: container
    image: nginx
```

### Preemption

Preemption は、高優先度の Pod をスケジュールするために低優先度の Pod を削除するプロセスです。スケジューラーが高優先度 Pod をスケジュールする Node を見つけられない場合、リソースを確保するために低優先度 Pod を Preemption します。

Preemption プロセス:
1. スケジューラーが高優先度 Pod をスケジュールする Node を見つけられない
2. スケジューラーが Preemption により低優先度 Pod を削除する Node を選択
3. API を介して選択した低優先度 Pod の削除をリクエストし、kubelet/runtime が終了を実行
4. Pod が正常に終了すると、その Node に高優先度 Pod をスケジュール

### Preemption に関する考慮事項

Preemption を使用する際の考慮事項は以下のとおりです。

1. **正常終了期間**: Preemption された Pod は、`terminationGracePeriodSeconds` で指定した時間だけ正常終了プロセスを実行します
2. **PodDisruptionBudget**: スケジューラーは違反の回避を試みますが、PDB を回避できる適切な犠牲 Pod がない場合、Preemption が PDB に違反することがあります
3. **システム PriorityClass**: Kubernetes はシステムコンポーネント用の PriorityClass を提供します
   - `system-cluster-critical`: クラスター運用に不可欠な Pod
   - `system-node-critical`: Node 運用に不可欠な Pod

## Pod Eviction

Pod Eviction は Pod を終了します。ワークロードコントローラーは置き換え用の Pod を作成する場合があり、その Pod はスケジューラーによって別途配置されます。Eviction はさまざまな理由で発生します。

![Pod Eviction の 3 つの発生元をまとめた図。NotReady または Unreachable Node から Pod を Eviction する controller manager、メモリ、nodefs、imagefs、pid の Eviction シグナルを監視しながらリソース不足またはハードウェア問題で Pod を Eviction する kubelet、およびメンテナンスのために Node を drain するユーザー。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-6.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-6.html)

### Eviction の種類

1. **kube-controller-manager による Eviction**:
   - taint-eviction-controller が NoExecute Taint を処理します。Pod には通常、300 秒の not-ready/unreachable Toleration が付与され、Eviction はその Toleration 設定に従います
   - Node が Unreachable 状態の場合

2. **kubelet による Eviction**:
   - Node のリソース不足（メモリ、ディスクなど）
   - ハードウェア障害は Node を利用不能にする可能性がありますが、汎用の kubelet プレッシャー Eviction シグナルではありません

3. **ユーザーによる Eviction**:
   - `kubectl drain` コマンドの実行
   - Node メンテナンスタスク

### kubelet Eviction シグナル

kubelet は次の Eviction シグナルを監視します。

1. **memory.available**: 利用可能なメモリ
2. **nodefs.available**: Node ファイルシステムの利用可能な領域
3. **nodefs.inodesFree**: Node ファイルシステムの利用可能な inode
4. **imagefs.available**: イメージファイルシステムの利用可能な領域
5. **imagefs.inodesFree**: イメージファイルシステムの利用可能な inode
6. **pid.available**: 利用可能なプロセス ID

各シグナルにソフトおよびハードしきい値を設定できます。

- **ソフトしきい値**: しきい値超過後、`grace-period` の経過時に Pod を Eviction
- **ハードしきい値**: しきい値超過時に Pod を即座に Eviction

```yaml
# kubelet configuration example
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
  imagefs.available: "15%"
  imagefs.inodesFree: "5%"
evictionSoft:
  memory.available: "200Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: "1m"
  nodefs.available: "2m"
evictionMaxPodGracePeriod: 30
evictionPressureTransitionPeriod: "30s"
```

### Eviction の優先順位

kubelet は、使用量がリクエストを超過しているか、次に Pod Priority、さらにリクエストに対する使用量の順で候補を順位付けします。BestEffort、Burstable、Guaranteed Pod の順にすべてを単純に Eviction するわけではありません。ディスク/PID プレッシャーには異なるアカウンティング上の制約があり、QoS は普遍的な Eviction 順序ではありません。

## Pod Disruption Budget (PDB)

Pod Disruption Budget (PDB) は、自発的な中断の間にアプリケーションの可用性を維持する方法です。PDB は同時に中断できる Pod の数を制限します。

![PodDisruptionBudget の minAvailable、maxUnavailable、selector 設定が Node drain などの自発的な中断を制御し、Eviction を許可または拒否する様子と、等価な minAvailable と maxUnavailable の設定が同じ効果を生む Deployment の例を示す図。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-7.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-7.html)

### PDB の定義

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: frontend
```

または

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: frontend-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: frontend
```

上記の例では:
- `minAvailable`: 常に利用可能でなければならない最小 Pod 数
- `maxUnavailable`: 同時に利用不能になり得る最大 Pod 数
- `selector`: PDB が適用される Pod を選択するラベルセレクター

### PDB の動作

1. Node drain などの自発的な中断が発生すると、Kubernetes は PDB を確認します
2. PDB 条件を満たす場合、Pod Eviction を続行します
3. PDB 条件を満たさない場合、Pod Eviction を拒否します

PDB は通常の drain/descheduler 操作などの Eviction API リクエストを制御します。直接的な Pod 削除、コントローラーのロールアウト、Node プレッシャー Eviction はこの制御をバイパスします。`minAvailable: 2` と `maxUnavailable: 1` が等価なのは、必要なレプリカ数が 3 のワークロードに限られ、どちらも置き換え用の容量を作成しません。

### PDB のベストプラクティス

1. **すべてのクリティカルなワークロードに PDB を設定**: 高可用性を必要とするすべてのワークロードに PDB を設定します
2. **適切な値を選択**: ワークロードの特性に適した `minAvailable` または `maxUnavailable` の値を選択します
3. **レプリカ数を考慮**: `minAvailable` をレプリカ数と同じにすると自発的 Eviction をブロックできますが、メンテナンスが停止する可能性があるため、意図的な中断許容量を設定します
4. **定期テスト**: Node drain などのタスクを通じて PDB の動作をテストします

## Node Pressure Eviction

Node Pressure Eviction は、Node のリソース不足によって Pod が Eviction されるメカニズムです。

### Node Condition の状態

kubelet は次の Node Condition 状態をレポートします。

1. **MemoryPressure**: Node のメモリが不足
2. **DiskPressure**: Node のディスク領域が不足
3. **PIDPressure**: Node のプロセス ID が不足

これらの状態が発生すると、kubelet はリソースを確保するために Pod を Eviction します。

### Eviction ポリシーの設定

Eviction ポリシーは kubelet 設定で設定できます。

```yaml
# kubelet configuration example
evictionHard:
  memory.available: "100Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
  imagefs.available: "15%"
  imagefs.inodesFree: "5%"
evictionSoft:
  memory.available: "200Mi"
  nodefs.available: "15%"
evictionSoftGracePeriod:
  memory.available: "1m"
  nodefs.available: "2m"
evictionMinimumReclaim:
  memory.available: "50Mi"
  nodefs.available: "5%"
evictionMaxPodGracePeriod: 30
evictionPressureTransitionPeriod: "30s"
```

上記の例では:
- `evictionMinimumReclaim`: Eviction 後に再確保する必要がある最小リソース
- `evictionPressureTransitionPeriod`: プレッシャー状態の遷移間の待機時間

## TopologySpreadConstraints

TopologySpreadConstraints は、アベイラビリティーゾーン、Node、リージョンなどのトポロジードメイン全体に Pod をどのように分散するかをきめ細かく制御します。この機能は、高可用性と効率的なリソース使用率を達成する際に Pod Anti-Affinity より柔軟性を提供します。

![TopologySpreadConstraints が maxSkew、topologyKey、whenUnsatisfiable、通常の labelSelector を通じてアベイラビリティーゾーン間の Pod 分散を制御する様子、whenUnsatisfiable の DoNotSchedule と ScheduleAnyway オプション、maxSkew=1 の新しい Pod が最も少ない Pod を持つ Zone である ap-northeast-2b に配置される EKS の例を示す図。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-8.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-8.html)

### 主要フィールド

| フィールド | 説明 | 必須 |
|-------|-------------|----------|
| **maxSkew** | DoNotSchedule の場合は対象ドメインとグローバル最小値の許容差。ScheduleAnyway は skew を設定として使用 | はい |
| **topologyKey** | トポロジードメインを定義する Node ラベルキー | はい |
| **whenUnsatisfiable** | 制約を満たせない場合のアクション: `DoNotSchedule` または `ScheduleAnyway` | はい |
| **labelSelector** | カウントする Pod を選択。通常はこれと一致する Pod ラベルを指定 | いいえ（null は Pod に一致しない） |
| **minDomains** | skew 計算の対象となる最小の適格ドメイン数（v1.30 以降 stable） | いいえ |
| **matchLabelKeys** | 分散計算のために一致させる Pod ラベルキー（1.27+） | いいえ |

### whenUnsatisfiable オプション

- **DoNotSchedule**: 制約を満たせない場合、スケジューラーは Pod をスケジュールしません（ハード制約）
- **ScheduleAnyway**: スケジューラーは Pod をスケジュールしますが、skew を最小化する Node をより高く優先します（ソフト制約）

### EKS アベイラビリティーゾーン分散の例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: web
      containers:
      - name: web
        image: nginx:1.30.4
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
```

この設定は以下を保証します。
1. Pod はアベイラビリティーゾーン全体に均等に分散されます（ハード制約）
2. Pod は各 Zone 内の Node 全体に優先的に分散されます（ソフト制約）

### minDomains と matchLabelKeys

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-min-domains
spec:
  replicas: 4
  selector:
    matchLabels:
      app: distributed-app
  template:
    metadata:
      labels:
        app: distributed-app
        version: v1
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: distributed-app
        minDomains: 3
        matchLabelKeys:
        - version
      containers:
      - name: app
        image: myapp:v1
```

- **minDomains**: 適格なドメインが 3 未満の場合、グローバル最小値はゼロになります。maxSkew 1 では、適格なドメインごとに一致する Pod を 1 つずつスケジュールできますが、追加の Pod は Pending のままになることがあります。すべての Pod を直ちにブロックするわけではありません。
- **matchLabelKeys**: Pod の `version` ラベル値をセレクターで自動的に使用し、セレクターを変更せずにリビジョンごとの分散を可能にします。

### Pod Anti-Affinity に対する利点

| 項目 | TopologySpreadConstraints | Pod Anti-Affinity |
|--------|---------------------------|-------------------|
| **柔軟性** | 制御された skew を許可（maxSkew > 1） | 二値: 同一または異なるドメイン |
| **ソフト制約** | ベストエフォートのための `ScheduleAnyway` | `preferredDuringScheduling` ですが制御は少ない |
| **マルチレベル** | 異なる topologyKey による複数の制約 | 複雑なネストルールが必要 |
| **パフォーマンス** | 大規模でより良いスケジューラーパフォーマンス | 多数の Pod があるとスケジューリングが遅くなる場合がある |
| **ユースケース** | 許容範囲を持つ均等な分散 | 厳格な分離 |

## Pod Deletion Cost

Pod Deletion Cost は、スケールダウン時に ReplicaSet コントローラーが使用するベストエフォートの設定です。HPA は必要なレプリカ数を変更しますが、個々の犠牲 Pod を選択しません。この annotation は Job/StatefulSet を保護せず、Eviction を防止せず、削除順序も保証しません。

### 仕組み

コントローラー（HPA または手動スケールダウンなど）がレプリカを減らす必要がある場合、以下を考慮します。
1. 削除コストが低い Pod が先に削除される
2. デフォルトの削除コストは 0
3. 有効範囲: -2147483648 ～ 2147483647

### 基本例

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: worker-pod
  annotations:
    controller.kubernetes.io/pod-deletion-cost: "100"
spec:
  containers:
  - name: worker
    image: worker:latest
```

### HPA スケールダウン優先度の制御

HPA スケールダウン中に重要な Pod を保護するには、削除コストを使用します。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-service
spec:
  replicas: 5
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
      # Lower cost pods are deleted first during scale-down
      annotations:
        controller.kubernetes.io/pod-deletion-cost: "0"
    spec:
      containers:
      - name: web
        image: nginx:1.30.4
```

### キャッシュ保護パターン

CPU 使用率 HPA でスケーリングする場合、キャッシュには明示的な CPU リクエストを設定します。以下はスケジューリング例であり、完全な Redis 本番設定ではありません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cache-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cache
  template:
    metadata:
      labels:
        app: cache
    spec:
      automountServiceAccountToken: false
      containers:
      - name: cache
        image: redis:7
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
```

実際のキャッシュの温まり具合を測定した後、認可されたオペレーター/コントローラーは、スケールダウン前に選択した ReplicaSet 所有 Pod に一度 annotation を付与できます。

```bash
kubectl -n default annotate pod "$CACHE_POD" \
  controller.kubernetes.io/pod-deletion-cost="1000" --overwrite
```

`CACHE_POD` を実際のキャッシュ Pod に設定します。頻繁な annotation 書き込みは API 負荷を発生させます。カスタムアップデーターには Redis と Kubernetes の両方のクライアントツールに加え、狭くスコープされた Pod patch 権限が必要です。経過時間だけではキャッシュが温まっている証拠にはなりません。この例ではアップデーターをインストールしません。

### 実用的なユースケース

1. **ReplicaSet で管理されるステートフルキャッシュ**: 温まったレプリカの維持を優先
2. **リーダー選出**: リーダー Pod の稼働時間を延長
3. **接続ドレイン**: 長時間接続を処理する時間を確保
4. **キャッシュウォームアップ**: 温まったキャッシュを持つ Pod を保持
5. **制限事項**: Job および StatefulSet コントローラーはこの設定を使用しません

## Descheduler

Descheduler は、Pod を Node から Eviction して、スケジューラーがより適切な Node に再スケジュールできるようにする Kubernetes コンポーネントです。新しい Pod だけを配置するスケジューラーとは異なり、Descheduler は時間の経過とともに最適な Pod 配置を維持するのに役立ちます。

![Node の追加、削除、または Pod の変更によって均等に分散されたクラスターのバランスが崩れたとき、Descheduler が実行中の Pod を Eviction してスケジューラーに再配置させることでバランスを復元する仕組みと、RemoveDuplicates、LowNodeUtilization、PodLifeTime など 6 つの代表的な Descheduler 戦略を示す図。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-9.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-9.html)

### 再スケジューリングが必要な理由

1. **クラスターの変更**: 新しい Node の追加、Node ラベルの変更
2. **Pod のドリフト**: 初期配置が時間の経過とともに最適でなくなる
3. **Affinity 違反**: クラスター変更後にルールが違反される
4. **リソースの不均衡**: 一部の Node は過剰使用、他は過少使用
5. **失敗した Pod**: 再起動ループで停止した Pod

### 主な戦略

| 戦略 | 説明 | ユースケース |
|----------|-------------|----------|
| **RemoveDuplicates** | 同一 Node から重複 Pod を削除 | Node 障害後の HA を確保 |
| **LowNodeUtilization** | 過剰使用 Node から過少使用 Node に Pod を移動 | クラスターリソースのバランス調整 |
| **RemovePodsHavingTooManyRestarts** | 過剰に再起動した Pod を Eviction | 問題のある Pod をクリーンアップ |
| **PodLifeTime** | 指定した経過時間より古い Pod を Eviction | 新しいスケジューリングを強制 |
| **RemovePodsViolatingInterPodAntiAffinity** | Anti-Affinity ルールに違反する Pod を Eviction | Affinity 準拠を復元 |
| **RemovePodsViolatingNodeAffinity** | Node Affinity に違反する Pod を Eviction | Affinity 準拠を復元 |
| **RemovePodsViolatingTopologySpreadConstraint** | 分散制約に違反する Pod を Eviction | 均等な分散を復元 |

### Helm インストール

Descheduler v0.36.0 は検証済みの例のリリースであり、テスト対象には Kubernetes v1.36 と、その前の 2 マイナーバージョンが含まれます。別のリリースに適用する前に、互換性マトリックスを確認してください。`schedule` と `deschedulerPolicy.profiles`（以下に示すポリシープロファイル）を含むレビュー済みの Helm values を `descheduler-values.yaml` に保存します。古い `strategies.*.enabled` の値ではこの API を設定できません。

```bash
helm repo add descheduler https://kubernetes-sigs.github.io/descheduler/
helm upgrade --install descheduler descheduler/descheduler \
  --version 0.36.0 --namespace kube-system \
  --values descheduler-values.yaml
```

### DeschedulerPolicy の設定

```yaml
apiVersion: descheduler/v1alpha2
kind: DeschedulerPolicy
profiles:
- name: default
  pluginConfig:
  - name: DefaultEvictor
    args:
      nodeFit: true
  - name: RemoveDuplicates
    args:
      excludeOwnerKinds: [StatefulSet]
  - name: LowNodeUtilization
    args:
      thresholds:
        cpu: 20
        memory: 20
        pods: 20
      targetThresholds:
        cpu: 50
        memory: 50
        pods: 50
  - name: RemovePodsHavingTooManyRestarts
    args:
      podRestartThreshold: 100
      includingInitContainers: true
  - name: PodLifeTime
    args:
      maxPodLifeTimeSeconds: 86400
      labelSelector:
        matchLabels:
          app.kubernetes.io/lifecycle: ephemeral
  - name: RemovePodsViolatingNodeAffinity
    args:
      nodeAffinityType: [requiredDuringSchedulingIgnoredDuringExecution]
  - name: RemovePodsViolatingTopologySpreadConstraint
    args:
      constraints: [DoNotSchedule]
  plugins:
    balance:
      enabled:
      - RemoveDuplicates
      - LowNodeUtilization
      - RemovePodsViolatingTopologySpreadConstraint
    deschedule:
      enabled:
      - RemovePodsHavingTooManyRestarts
      - PodLifeTime
      - RemovePodsViolatingNodeAffinity
```

### PDB の遵守

Descheduler は Pod Disruption Budget (PDB) を遵守します。Pod を Eviction すると PDB に違反する場合、Descheduler はその Pod を Eviction しません。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
```

この PDB がある場合、Descheduler は再スケジューリング操作中に `app: web` ラベルを持つ Pod が少なくとも 2 個利用可能なままであることを保証します。

上記のポリシーは Descheduler 設定ファイルであり、kubectl apply 用の API オブジェクトではありません。グループの再分散には Balance プラグインを、Pod 単位の判断には Deschedule プラグインを使用します。LowNodeUtilization は通常、実際の CPU 使用量ではなくリソースリクエストを評価し、Eviction しても置き換え用 Pod が別の場所に配置されるとは限りません。定期的な Eviction を有効にする前に、保護措置を確認し、dry-run でテストしてください。

### Descheduler CronJob の例

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: descheduler
  namespace: kube-system
spec:
  schedule: "*/30 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: descheduler
          containers:
          - name: descheduler
            image: registry.k8s.io/descheduler/descheduler:v0.36.0
            args:
            - --policy-config-file=/policy/policy.yaml
            - --v=3
            volumeMounts:
            - name: policy
              mountPath: /policy
          volumes:
          - name: policy
            configMap:
              name: descheduler-policy
          restartPolicy: OnFailure
```

スタンドアロンの CronJob は Helm の代替であり、追加のインストールではありません。`descheduler` ServiceAccount/RBAC と、キー `policy.yaml` を持つ `descheduler-policy` ConfigMap が必要です。これらの前提条件を提供するには公式 chart/manifests を使用してください。

> **詳細**: カスタムスケジューラーの詳細については、以下を参照してください。
> - [Custom Scheduler Part 1: 基本概念](../scheduling/01-custom-scheduler-part1.md)
> - [Custom Scheduler Part 2: 実装](../scheduling/02-custom-scheduler-part2.md)
> - [Custom Scheduler Part 3: 高度な機能](../scheduling/03-custom-scheduler-part3.md)

## Amazon EKS におけるスケジューリング最適化

Amazon EKS では、Kubernetes のスケジューリング機能を使用してワークロードを最適化できます。

![4 つの EKS スケジューリング最適化手段を示す図。Node group とインスタンスタイプの選択、アベイラビリティーゾーン分散、Karpenter 自動スケーリング、リソースリクエストと制限のチューニングが、それぞれ実装するメカニズムまたは自動化ツールである Cluster Autoscaler、マルチ AZ 配置、Karpenter NodePool、Vertical Pod Autoscaler に接続されています。](../.gitbook/assets/en-core-08-scheduling-preemption-eviction-11.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-core-08-scheduling-preemption-eviction-11.html)

### Node Group とインスタンスタイプ

EKS では、さまざまな Node group とインスタンスタイプを活用して、ワークロードに適したリソースを提供できます。

1. **さまざまなインスタンスタイプ**: コンピューティング最適化、メモリ最適化、ストレージ最適化など
2. **Spot Instance**: コスト効率の高いワークロード向けの Spot Instance
3. **GPU Instance**: AI/ML ワークロード向けの GPU Instance

Node ラベルと Taint を使用して、特定のワークロードを特定の Node group に配置できます。

既存のクラスターに対して、Region が一致し、サポート対象の GPU インスタンス/AMI と必要な IAM 権限を備えたレビュー済みの eksctl 設定を使用してください。

```yaml
# gpu-nodegroup.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: my-cluster
  region: us-west-2
managedNodeGroups:
- name: gpu-nodes
  instanceType: p3.2xlarge
  desiredCapacity: 1
  privateNetworking: true
  labels:
    workload-type: gpu
  taints:
  - key: gpu
    value: "true"
    effect: NoSchedule
```

```bash
eksctl create nodegroup --config-file=gpu-nodegroup.yaml
```

### アベイラビリティーゾーン分散

EKS では、Pod Anti-Affinity と Topology Spread Constraints を使用して、複数のアベイラビリティーゾーンにワークロードを分散できます。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web
      containers:
      - name: web
        image: nginx
```

上記の例では、`topologySpreadConstraints` が複数のアベイラビリティーゾーン全体に Pod を均等に分散します。

### Karpenter による Auto Scaling

Amazon EKS では、Karpenter を使用してワークロードに適した Node を自動プロビジョニングできます。

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default-class
  limits:
    cpu: 1000
    memory: 1000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default-class
spec:
  role: KarpenterNodeRole-my-cluster
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: my-cluster
```

Karpenter は Pod のリソース要件に最適なインスタンスタイプを選択してコストを最適化します。

### リソースリクエストと制限の最適化

EKS において、ワークロードのリソースリクエストと制限を最適化することは重要です。

1. **Vertical Pod Autoscaler (VPA)**: 実際のワークロードリソース使用量に基づいてリソースリクエストを最適化
2. **Goldilocks**: VPA 推奨値を可視化してリソースリクエストの最適化を支援
3. **Resource Quotas**: Namespace ごとのリソース使用量を制限

```yaml
# VPA example
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: frontend-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  updatePolicy:
    updateMode: "Recreate"
```

## スケジューリングのベストプラクティス

Kubernetes と EKS におけるスケジューリング最適化のベストプラクティスは以下のとおりです。

1. **適切なリソースリクエストと制限を設定**:
   - 実際のワークロードリソース使用量に基づいてリソースリクエストを設定
   - 重要なワークロードに適切なリソース制限を設定
   - VPA を使用してリソースリクエストを自動最適化

2. **ワークロード分散**:
   - Pod Anti-Affinity を使用して重要なワークロードを複数の Node に分散
   - Topology Spread Constraints を使用してワークロードを複数のアベイラビリティーゾーンに分散
   - Node Affinity を使用して特定のワークロードを特定の Node に配置

3. **Node リソースの最適化**:
   - さまざまなインスタンスタイプを使用してワークロードに適したリソースを提供
   - コスト最適化のために Spot Instance を使用
   - Karpenter を使用してワークロードに適した Node を自動プロビジョニング

4. **PDB 設定**:
   - 重要なワークロードに PDB を設定
   - ワークロードの特性に適した `minAvailable` または `maxUnavailable` の値を選択
   - PDB の動作を定期的にテスト

5. **Priority と Preemption の設定**:
   - 重要なワークロードに高い PriorityClass を設定
   - システムコンポーネントには `system-cluster-critical` または `system-node-critical` PriorityClass を使用
   - Preemption の影響を理解し、テスト

6. **Node Taint と Toleration**:
   - 特殊なワークロード向けに専用 Node を設定
   - メンテナンス中の Node に Taint を適用
   - 適切な Toleration を設定

## まとめ

Kubernetes のスケジューリング、Preemption、Eviction のメカニズムは、クラスターリソースを効率的に管理し、ワークロードの可用性を維持するうえで重要な役割を果たします。これらの機能を理解して活用することで、Amazon EKS クラスターのワークロードを最適化し、信頼性高く運用できます。

スケジューリング最適化は継続的なプロセスであり、ワークロードの特性とクラスターの状態に従って調整を続ける必要があります。監視ツールを使用してクラスターのリソース使用量を追跡し、必要に応じてスケジューリングポリシーを調整することが重要です。

## クイズ

この章で学んだ内容をテストするには、[スケジューリング、Preemption、Eviction クイズ](../quizzes/core/08-scheduling-preemption-eviction-quiz.md) に挑戦してください。
