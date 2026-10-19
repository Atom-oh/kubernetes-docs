# カスタムスケジューラークイズ（パート1）

> **例で使用する基準**: Kubernetes 1.35.8、Go 1.27.2
> **最終更新日**: 2026年10月16日

このクイズでは、Kubernetes におけるカスタムスケジューラーの実装と使用方法について理解を確認します。

## クイズ

### 1. Kubernetes におけるスケジューラーの主な役割は何ですか？

A. Pod の作成と削除
B. Pod を適切な Node に割り当てる
C. Node リソースの監視
D. コンテナイメージのダウンロード

<details>
<summary>解答を表示</summary>

**回答: B. Pod を適切な Node に割り当てる**

**解説:**
Kubernetes におけるスケジューラーの主な役割は、Pod を適切な Node に割り当てることです。スケジューラーは新しく作成された Pod を監視し、まだ Node に割り当てられていない Pod の実行先として最適な Node を探します。

**スケジューラーの主な機能:**
1. **Pod と Node の割り当て**: Pod の要件と Node で利用できるリソースを考慮し、最適な Node を選びます。
2. **フィルタリング**: リソース不足や taint などの理由で Pod を実行できない Node を候補から除外します。
3. **スコアリング**: 条件に合う Node にスコアを付け、最適な Node を選びます。
4. **バインド**: 選択した Node に Pod をバインドして、スケジューリングの決定を確定します。

**スケジューリングの流れ（Kubernetes 1.35.8）:**
1. **Filter**: `NodeResourcesFit` は Pod の実効リソース要求と、残りの割り当て可能リソースを照合します。`NodePorts` は要求されたホストポートを確認し、`NodeAffinity` は Node セレクターとアフィニティを処理し、`TaintToleration` は taint を確認します。`VolumeBinding`、`VolumeZone`、`NodeVolumeLimits` などのボリュームプラグインはストレージ制約を適用します。Node の圧迫状態は Node condition や taint に反映されます。`CheckNodeDiskPressure` などの名前は過去の predicate であり、現在設定可能なプラグイン名ではありません。
2. **Score**: `NodeResourcesFit`（既定値は `LeastAllocated`）、`NodeResourcesBalancedAllocation`、`NodeAffinity`、`InterPodAffinity`、`PodTopologySpread`、`TaintToleration`、`ImageLocality` が配置先の選好に寄与します。これらすべてが実リソース使用率を測定するわけではありません。
3. **Bind**: 残りの framework フェーズが成功すると、スケジューラーは Node の割り当てを記録します。その後、kubelet とコンテナランタイムが実行を管理します。スコアが高くても、起動、レイテンシー、可用性が保証されるわけではありません。

**セカンダリースケジューラーの設定例:**
この設定は既定のフィルターを残したまま、スコアリングの重みを変更します。このクイズに登場する設定は `--config` で読み込むファイルであり、`kubectl` で適用する Kubernetes API リソースではありません。
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

**ほかの選択肢が誤りである理由:**
- A. Pod の作成と削除: 主に controller manager と API server の役割です。
- C. Node リソースの監視: 主に kubelet と metrics server の役割です。
- D. コンテナイメージのダウンロード: kubelet とコンテナランタイムの役割です。
</details>

### 2. 次のうち、カスタムスケジューラーを実装する方法ではないものはどれですか？

A. 既存の kube-scheduler を拡張する
B. 独自のスケジューラーを一から実装する
C. scheduling framework のプラグインを開発する
D. kubelet を変更する

<details>
<summary>解答を表示</summary>

**回答: D. kubelet を変更する**

**解説:**
kubelet の変更は、カスタムスケジューラーの実装方法ではありません。kubelet は各 Node 上で動作し、Pod の実行を管理するエージェントですが、スケジューリングの決定は行いません。スケジューリングは kube-scheduler またはカスタムスケジューラーが担当します。

**カスタムスケジューラーを実装する方法:**

1. **kube-scheduler を基にセカンダリースケジューラーを設定する**: 既定のプラグインを維持し、必要な動作だけを調整します。Part 1 には、コマンド、RBAC、ConfigMap、Deployment を含む一式があります。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

2. **独立したスケジューラーを実装する**: 正しいキャッシュ、キュー、list/watch の復旧、リソース計算、ボリューム調整、再試行、leader election、バインドを実装する必要があります。watch だけを使うループでは既存 Pod や接続断を見落とします。本番用コードでは informer と workqueue を使い、tombstone、キャンセル、古いオブジェクトを処理してください。Ready な Node を選んだだけでは、Pod の要件を満たすことを確認したことにはなりません。そのため Part 1 の例では、これらの処理を upstream の kube-scheduler に委ねています。

3. **framework プラグインを開発する**: プラグインをスケジューラーのバイナリに組み込み、`app.WithPlugin` で登録します。Q4 では Filter プラグイン、Q6 では Score プラグイン、Q7 では登録用コマンドを示します。各インターフェイスは `k8s.io/kube-scheduler/framework` v0.35.8 に固定されています。シグネチャは Kubernetes のマイナーバージョンによって異なります。

**kubelet の役割:**
kubelet は各 Node 上で動作するエージェントで、次の処理を担当します。
- Pod spec に従ってコンテナを実行、管理する
- Node の状態を監視して報告する
- コンテナのヘルスチェックを行う
- ボリュームのマウントを管理する

kubelet は、どの Pod をどの Node で実行するかというスケジューラーの決定を実行します。kubelet 自身はスケジューリングを決定しません。

**ほかの選択肢の解説:**
- A. 既存の kube-scheduler を拡張する: カスタムスケジューラーを実装する有効な方法です。
- B. 独自のスケジューラーを一から実装する: カスタムスケジューラーを実装する有効な方法です。
- C. scheduling framework のプラグインを開発する: カスタムスケジューラーを実装する有効な方法です。
</details>

### 3. Pod で特定のスケジューラーを指定するフィールドはどれですか？

A. spec.scheduler
B. spec.schedulerName
C. metadata.scheduler
D. spec.nodeName

<details>
<summary>解答を表示</summary>

**回答: B. spec.schedulerName**

**解説:**
Pod で特定のスケジューラーを指定するフィールドは `spec.schedulerName` です。このフィールドを設定すると、指定した名前のスケジューラーだけがその Pod をスケジュールします。既定値は `default-scheduler` です。

**Pod spec の例:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: custom-scheduled-pod
  labels:
    app: my-app
spec:
  schedulerName: custom-scheduler  # Specify custom scheduler
  containers:
  - name: main-container
    image: nginx:1.30.6
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
```

この Pod は `custom-scheduler` という名前のスケジューラーだけがスケジュールします。クラスタ内にその名前のスケジューラーがなければ、Pod は `Pending` 状態のままになります。

**スケジューラー名の設定:**
Part 1 の Deployment 一式を使い、この設定を `/etc/scheduler/config.yaml` としてマウントし、`--config=/etc/scheduler/config.yaml` を指定します。現在の設定方法は `--scheduler-name` ではありません。ServiceAccount と Lease の権限も事前に必要です。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
```

**スケジューラーを選ぶ際の考慮事項:**
1. **可用性**: 指定したスケジューラーが稼働していなければ、Pod はスケジュールされません。
2. **機能**: スケジューラーごとにアルゴリズムやポリシーを変えられます。
3. **ポリシーによる振り分け**: `schedulerName` が選ぶのはスケジューラープロファイルです。この設定だけでセキュリティやリソースが分離されるわけではありません。
4. **特殊なハードウェア**: GPU や FPGA などを対象に専用スケジューラーを使えます。

**スケジューラーの状態確認:**
```bash
# Check pod status
kubectl get pod custom-scheduled-pod

# Check scheduling events
kubectl describe pod custom-scheduled-pod | grep -A 5 Events

# Check scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100
```

**ほかの選択肢が誤りである理由:**
- A. spec.scheduler: Kubernetes API に存在しないフィールドです。
- C. metadata.scheduler: Kubernetes API に存在しないフィールドです。
- D. spec.nodeName: このフィールドはスケジューラーを介さず、Pod を特定の Node に直接割り当てるためのものです。スケジューラーを指定するフィールドではありません。
</details>

### 4. Kubernetes のスケジューリング framework における「Filter」拡張ポイントの役割は何ですか？

A. Node にスコアを付ける
B. Pod を Node にバインドする
C. Pod を実行できない Node を除外する
D. scheduling queue 内の Pod を並べ替える

<details>
<summary>解答を表示</summary>

**回答: C. Pod を実行できない Node を除外する**

**解説:**
Kubernetes のスケジューリング framework における「Filter」拡張ポイント（旧称「Predicate」）は、Pod を実行できない Node を除外します。Filter プラグインは各 Node が Pod の要件を満たすか確認し、満たさない Node を候補から除きます。

**Scheduling Framework の拡張ポイント:**
* **PreEnqueue / QueueSort**: キューへの追加を制御し、キュー内の Pod を並べ替えます。
* **PreFilter / Filter**: 共有状態を準備し、実行可能でない Node を除外します。
* **PostFilter**: 実行可能な Node がない場合に、preemption などによる回復を試みます。
* **PreScore / Score / optional NormalizeScore**: 実行可能な Node を評価して順位付けします。正規化後のプラグインスコアは 0～100 でなければなりません。
* **Reserve / Unreserve**: 仮定した状態を記録し、スケジューリングに失敗した場合は取り消します。物理的な CPU やデバイスを割り当てる処理ではありません。
* **Permit**: 次の処理への続行を許可、拒否、または待機させます。
* **PreBind / Bind / PostBind**: 依存関係を準備し、バインドを確定して、その後の処理を実行します。`PostBind` から確定済みのバインドを取り消すことはできません。インターフェイスにバージョン固有のメソッドが加わることがあるため、対象リリースに合わせてコンパイルしてください。

**既定の Filter プラグイン:**
`NodeResourcesFit`、`NodeName`、`NodeUnschedulable`、`NodePorts`、`TaintToleration`、`NodeAffinity`、`InterPodAffinity`、`PodTopologySpread`、`VolumeRestrictions`、`NodeVolumeLimits`、`VolumeBinding`、`VolumeZone` は、それぞれ異なる制約を扱います。古い predicate 名や、プロバイダー固有の `EBSLimits` は現在のプラグイン名ではありません。

**カスタム Filter の例（`plugins/filter.go`）:**
この単純なラベル規則は、通常なら必須の Node affinity で表現できます。ここでは framework のインターフェイスを示しています。ラベルがない場合、ほかの Pod を preempt しても解決しませんが、後から Node ラベルが変われば再試行時に Pod が適格になることがあります。

```go
package plugins

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyFilterPlugin struct{}

var _ fwk.FilterPlugin = &MyFilterPlugin{}

func (*MyFilterPlugin) Name() string { return "MyFilterPlugin" }

func (*MyFilterPlugin) Filter(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	if info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "missing node")
	}
	if info.Node().Labels["custom-label"] != "required-value" {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "node lacks required label")
	}
	return nil
}

func NewFilter(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyFilterPlugin{}, nil
}
```

**既定のプラグインを維持してカスタム Filter を有効にする:**
このプラグインは Q7 で登録します。ラベルチェックを追加するために `NodeResourcesFit` を無効にしてはいけません。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
  plugins:
    filter:
      enabled:
      - name: MyFilterPlugin
```

**ほかの選択肢が誤りである理由:**
- A. Node にスコアを付ける: 「Score」拡張ポイントの役割です。
- B. Pod を Node にバインドする: 「Bind」拡張ポイントの役割です。
- D. scheduling queue 内の Pod を並べ替える: 「Queue Sort」拡張ポイントの役割です。
</details>

### 5. スケジューラーではなく kubelet とコンテナランタイムが行う処理はどれですか？

A. Node のリソース要求と割り当て可能リソースを評価する
B. Pod の priority と preemption を考慮する
C. イメージレイヤーをダウンロードしてコンテナを作成する
D. Node affinity と Pod 間 affinity を評価する

<details>
<summary>解答を表示</summary>

**回答: C. イメージレイヤーをダウンロードしてコンテナを作成する**

**解説:**
スケジューラーは配置先の Node を選び、kubelet はランタイムにイメージの取得とコンテナの作成を依頼します。ただし、**イメージのローカルキャッシュはスケジューリングに影響することがあります**。既定の `ImageLocality` Score プラグインは、Node から報告されたキャッシュ済みイメージとイメージサイズを使います。キャッシュ情報が古い場合もあり、キャッシュがあれば取得を避けられるとは限りません。

**実装時の考慮事項:**
1. **リソース**: `NodeResourcesFit` を維持してください。このプラグインは実効リソース要求と、スケジューラーのキャッシュにある割り当て済み・仮定済みの使用量を使います。CPU やメモリの実測値は別の入力です。CPU とメモリの limit は過剰割り当てが可能であり、既定の適合判定ではありません。
2. **Priority**: PriorityClass と `preemptionPolicy` を意図して使ってください。affinity、ボリューム、その他の制約を preemption で解決できなければ、高 priority の Pod でも `Pending` のままになる場合があります。
3. **配置**: 必須の Node affinity は配置可能な Node を制限し、優先 affinity はスコアに影響します。以下の例の AZ は、実際に適格な容量があるゾーンに置き換えてください。通常の GPU 要件や topology 要件には、カスタムスケジューラーが不要なこともよくあります。

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
            values: [us-east-1a, us-east-1b]
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

4. **その他の制約**: taint/toleration、topology spread、ストレージの topology とアタッチ上限、ハードウェアリソースのチェックを維持してください。ネットワーク上の近さをモデル化する場合は、信頼できる topology データを使います。ラベルだけではレイテンシーを証明できません。
5. **イメージの扱い**: `ImageLocality` は選好であり、容量や起動の保証ではありません。Node 上ではイメージのガベージコレクション、レジストリ認証、取得失敗も発生します。

**ほかの選択肢について:**
A、B、D はいずれもスケジューリング時に考慮する内容です。ここでの違いは、配置の判断とランタイムの処理の区別であり、スケジューリングとイメージ情報の区別ではありません。
</details>

### 6. Kubernetes のスケジューリング framework における「Score」拡張ポイントの役割は何ですか？

A. Pod を実行できない Node を除外する
B. フィルタリングを通過した Node にスコアを付ける
C. Pod を Node にバインドする
D. scheduling queue 内の Pod を並べ替える

<details>
<summary>解答を表示</summary>

**回答: B. フィルタリングを通過した Node にスコアを付ける**

**解説:**
Kubernetes のスケジューリング framework における「Score」拡張ポイント（旧称「Priority」）は、フィルタリングを通過した Node にスコアを割り当てます。スコアリングプラグインが各 Node を評価し、そのスコアに基づいて配置先が選ばれます。

**スコアリングの流れ:**
1. 各スコアリングプラグインがスコアを計算します。必要に応じて正規化した後の範囲は 0～100 です。
2. 設定された重みに従って、プラグインごとのスコアを重み付けします。
3. すべてのプラグインの重み付きスコアを合計します。
4. 合計スコアが最も高い Node を Pod の配置先に選びます。

**既定のスコアリングプラグイン:**
Kubernetes には次の既定プラグインがあります。

1. **NodeResourcesBalancedAllocation**: 実測使用率ではなく、要求済み CPU とメモリの割合が均衡した Node を優先します。
2. **NodeResourcesFit**: 要求量と割り当て可能量に対して、設定済みの LeastAllocated、MostAllocated、RequestedToCapacityRatio 戦略を使います。
3. **NodeAffinity**: Node affinity ルールに基づいてスコアを付けます。
4. **InterPodAffinity**: Pod 間の affinity/anti-affinity ルールに基づいてスコアを付けます。
5. **PodTopologySpread**: topology domain 全体に Pod を均等に分散できる Node を高く評価します。
6. **TaintToleration**: toleration されない PreferNoSchedule taint にペナルティを与えます。強制的な taint はフィルタリング時に処理します。
7. **ImageLocality**: 必要なコンテナイメージをすでに持つ Node を高く評価します。

**カスタムスコアリングプラグイン（`plugins/score.go`）:**
この例では、Node ラベルは管理者が制御するポリシー入力です。無効な値は暗黙に選好を作り出すのではなく、スコアリングサイクルを失敗させます。有効なスコア 0 はフィルターではありません。

```go
package plugins

import (
	"context"
	"strconv"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type MyScorePlugin struct{}

var _ fwk.ScorePlugin = &MyScorePlugin{}

func (*MyScorePlugin) Name() string { return "MyScorePlugin" }

func (*MyScorePlugin) Score(_ context.Context, _ fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) (int64, *fwk.Status) {
	if info == nil || info.Node() == nil {
		return 0, fwk.NewStatus(fwk.Error, "missing node")
	}
	value := info.Node().Labels["custom-score-label"]
	if value == "" {
		return 0, nil
	}
	score, err := strconv.ParseInt(value, 10, 64)
	if err != nil || score < fwk.MinNodeScore || score > fwk.MaxNodeScore {
		return 0, fwk.NewStatus(fwk.Error, "custom-score-label must be an integer from 0 to 100")
	}
	return score, nil
}

// Scores are already absolute 0-100 values; no relative rescaling is needed.
func (*MyScorePlugin) ScoreExtensions() fwk.ScoreExtensions { return nil }

func NewScore(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &MyScorePlugin{}, nil
}
```

**2つのプラグインを使う計算例の重み:**
次の例では Score プラグインのセットだけを意図的に置き換えます。既定の Filter プラグインは有効なままです。実際のポリシーでは、必要なほかのスコアリング選好も残してください。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      disabled:
      - name: "*"
      enabled:
      - name: MyScorePlugin
        weight: 5
      - name: NodeResourcesBalancedAllocation
        weight: 2
```

**スコア計算の例:**
これは測定結果ではなく、計算例です。A、B、C がフィルタリングを通過し、有効な2つのプラグインが次の最終スコア（0～100）を返したとします。

1. MyScorePlugin（重み: 5）
   - Node A: 80 点
   - Node B: 60 点
   - Node C: 90 点

2. NodeResourcesBalancedAllocation（重み: 2）
   - Node A: 70 点
   - Node B: 90 点
   - Node C: 50 点

重み付き合計スコア:
- Node A: (80 x 5) + (70 x 2) = 400 + 140 = 540 点
- Node B: (60 x 5) + (90 x 2) = 300 + 180 = 480 点
- Node C: (90 x 5) + (50 x 2) = 450 + 100 = 550 点

この例では Node C が最も高いスコアになったため、Pod は Node C にスケジュールされます。

**ほかの選択肢が誤りである理由:**
- A. Pod を実行できない Node を除外する: 「Filter」拡張ポイントの役割です。
- C. Pod を Node にバインドする: 「Bind」拡張ポイントの役割です。
- D. scheduling queue 内の Pod を並べ替える: 「Queue Sort」拡張ポイントの役割です。
</details>

### 7. Kubernetes でスケジューラーを拡張する方法ではないものはどれですか？

A. Scheduling framework プラグイン
B. Scheduler extender
C. 複数のスケジューラーをデプロイする
D. Node controller を変更する

<details>
<summary>解答を表示</summary>

**回答: D. Node controller を変更する**

**解説:**
Node controller の変更は、Kubernetes でスケジューラーを拡張する方法ではありません。Node controller は Node の状態を監視、管理する control plane コンポーネントであり、スケジューリングの判断には直接関与しません。

**スケジューラーを拡張する方法:**

1. **Framework プラグイン**はスケジューラー内で動作します。Q4 と Q6 の Filter/Score の例を Part 1 モジュール内の `plugins/` に保存し、このコマンドを `cmd/with-plugins/main.go` として保存します。`CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/with-plugins` でビルドします。プラグインを登録しただけでは有効になりません。設定でそのプラグインを参照する必要があります。

```go
package main

import (
	"os"

	"example.com/custom-scheduler/plugins"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin("MyFilterPlugin", plugins.NewFilter),
		app.WithPlugin("MyScorePlugin", plugins.NewScore),
	)
	os.Exit(cli.Run(command))
}
```

このバージョンでは factory が `(context.Context, runtime.Object, framework.Handle)` を受け取ります。これらの例には独自引数がありません。設定を追加する場合は、バージョン管理された framework runtime decoder で `runtime.Unknown` の payload をデコード、検証してください。未登録の独自型に対する型アサーションは避けます。

2. **HTTP extender** は外部のフィルタリング、優先順位付け、必要に応じたバインドを追加します。`extenders` は profile の下ではなく、最上位に置きます。この設定例を使うには、extender service の実装、指定パスにマウントした対応する TLS 証明書、ネットワーク接続性、上限付きのエラー処理が必要です。単体で動くサーバーや EKS マネージドスケジューラーの設定例ではありません。`bindVerb` を省略すると既定の binder が使われます。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
extenders:
- urlPrefix: https://extender.scheduler-lab.svc:8443
  filterVerb: filter
  prioritizeVerb: prioritize
  weight: 5
  enableHTTPS: true
  tlsConfig:
    caFile: /etc/extender-tls/ca.crt
    certFile: /etc/extender-tls/tls.crt
    keyFile: /etc/extender-tls/tls.key
  httpTimeout: 2s
  nodeCacheCapable: false
  ignorable: false
```

`ignorable: false` の場合、extender の Filter が失敗すると、そのスケジューリング試行はブロックされます。`true` にすると、必須の独自制約を迂回するおそれがあります。Prioritization のエラー処理は異なります。Kubernetes 1.35.8 は失敗を記録して extender のスコアを除外するため、スコアを必須ルールの強制に使ってはいけません。可能な場合は framework プラグインを優先し、タイムアウト、再試行、障害時の挙動をテストしてください。

3. **複数のスケジューラー**では、異なる `profiles[].schedulerName` と独立した leader-election group を使います。既定スケジューラーと同じ identity や Lease で2つ目のプロセスを起動せず、Part 1 の Deployment/RBAC 一式を使ってください。

**Node controller の役割:**
kubelet は通常 Node を登録し、ヘルス状態を報告します。Node lifecycle controller は heartbeat を監視し、condition や taint を更新して、Node が不健全な場合の対応を調整します。これらの情報はスケジューリングに影響しますが、Node controller の変更はスケジューラーの拡張 API ではありません。

**方法を選ぶ際の考慮事項:**
実装の複雑さ、Node ごとの HTTP オーバーヘッド、キャッシュの整合性、障害時の動作、アップグレードとの互換性を評価してください。EKS ではセカンダリースケジューラーをデプロイします。マネージド既定スケジューラーのフラグや registry を置き換えることはできません。

**ほかの選択肢の解説:**
- A. Scheduling framework プラグイン: 有効なスケジューラー拡張方法です。
- B. Scheduler extender: 有効なスケジューラー拡張方法です。
- C. 複数のスケジューラーをデプロイする: 有効なスケジューラー拡張方法です。
</details>

### 8. Kubernetes スケジューラーの `--leader-elect` フラグは何のために使いますか？

A. スケジューラーにリーダーシップ権限を与える
B. 複数のスケジューラーインスタンスのうち1つだけを稼働させる
C. クラスタのリーダー Node 上だけでスケジューラーを実行する
D. スケジューラーにほかのコンポーネントより高い優先度を与える

<details>
<summary>解答を表示</summary>

**回答: B. 複数のスケジューラーインスタンスのうち1つだけを稼働させる**

**解説:**
Kubernetes スケジューラーの `--leader-elect` フラグは、高可用性（HA）構成で1つのスケジューラーインスタンスだけが有効になり、処理を行うようにします。同じ Lease group 内のレプリカを調整する機能です。あらゆる障害を防ぐ fencing ではなく、競合に安全な API 操作の代わりにもなりません。

**Leader election の仕組み:**
1. 複数のスケジューラーインスタンスをデプロイすると、leader election のアルゴリズムで1つがリーダーに選出されます。
2. 選出されたインスタンスだけが実際のスケジューリング処理を行います。
3. ほかのインスタンスは standby となり、現在のリーダーが失敗すると新しいリーダーが選出されます。
4. この仕組みでは Kubernetes の resource lock を使用します。

**Leader election の設定:**
Lease の identity とタイミングには、バージョン管理された設定ファイルを使用します。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
```

**HA デプロイ:**
Part 1 の Deployment 一式では、同じ設定と ServiceAccount を使う2つのレプリカをすでに実行します。独立したラボでは3レプリカに増やせます。これだけで本番環境の HA が実証されるわけではありません。障害ドメインの分離、API への接続性、起動時の容量、フェイルオーバー動作を確認してください。

```bash
kubectl -n scheduler-lab scale deployment/custom-scheduler --replicas=3
kubectl -n scheduler-lab get lease custom-scheduler -o yaml
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
```

**独自実装の場合:**
kube-scheduler コマンドには client-go の leader election がすでに組み込まれています。独自実装では、プロセスごとに一意な identity、スケジューラー group 内で共有する Lease、更新権限、リーダーシップを失った際にスケジューリング処理を停止する仕組みが必要です。client-go の仕組みでも、同時に動作するすべてのプロセスを fencing できるわけではありません。バインドや外部副作用は、競合に安全な設計にする必要があります。`ReleaseOnCancel` を使う場合は、Lease を解放する前に保護対象の処理を停止してください。

**Election を無効にしてよい場合:**
隔離された実験、またはロールアウトや障害時も含めて別の仕組みが常に単一プロセスの稼働を保証する場合に限り、無効化してください。`replicas: 1` でもローリングアップデート中にプロセスが重複することがあります。スケジューラー名が異なる場合は election group も分ける必要があります。名前が異なるだけでは election を安全に無効化できません。

**ほかの選択肢が誤りである理由:**
- A. スケジューラーにリーダーシップ権限を与える: leader election の具体的な目的を説明していない曖昧な表現です。
- C. クラスタのリーダー Node 上だけでスケジューラーを実行する: リーダーシップはプロセスに属し、クラスタ全体で共通する「リーダー Node」はありません。セカンダリースケジューラーを worker Node 上の Pod として実行することもできます。
- D. スケジューラーにほかのコンポーネントより高い優先度を与える: leader election は優先度ではなく、複数のスケジューラーインスタンス間の調整に使います。
</details>

### 9. Kubernetes で Pod のスケジューリング優先度を設定するリソースはどれですか？

A. PodSchedulingPolicy
B. PriorityClass
C. SchedulingPriority
D. PodPriority

<details>
<summary>解答を表示</summary>

**回答: B. PriorityClass**

**解説:**
Kubernetes で Pod のスケジューリング優先度を設定するリソースは `PriorityClass` です。PriorityClass は Pod の相対的な重要度を定義し、スケジューラーが配置先や preemption を判断する際に優先度を考慮できるようにします。

**PriorityClass リソース:**
```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000  # Priority value (higher value means higher priority)
globalDefault: false  # Whether to use this class as the default
description: "High priority pods"  # Description
preemptionPolicy: PreemptLowerPriority  # Preemption policy (default: PreemptLowerPriority)
```

**主なフィールド:**
1. **value**: 優先度の値です。値が大きいほど優先度が高くなります。ユーザー定義の値は最大 `1000000000` です。組み込みの critical class には、これより大きい予約済み範囲が使われます。
2. **globalDefault**: `true` にすると、PriorityClass を指定せず新規に admission された Pod にクラスタ全体の既定値として適用されます。既存 Pod は遡って変更されません。以下のラボ用 class はすべて `false` です。
3. **description**: PriorityClass の説明です。
4. **preemptionPolicy**: preemption のポリシーです。`PreemptLowerPriority`（既定値）または `Never` を指定できます。

**Pod への PriorityClass の適用:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: high-priority-pod
spec:
  priorityClassName: high-priority  # Reference PriorityClass name
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**優先度と preemption の動作:**
1. **スケジューリング優先度**: 優先度の高い Pod が scheduling queue で先に処理されます。
2. **Preemption**: 優先度の高い Pod を配置できる Node がない場合、スケジューラーは優先度の低い Pod を削除（preempt）して空きを作ることがあります。
3. **Preemption policy**: `preemptionPolicy: Never` を使う Pod はほかの Pod を preempt しませんが、自身が preempt される可能性はあります。優先度の高い Pod を配置できず queue backoff になる間に、優先度の低い Pod が先に進むこともあります。

**システム PriorityClass:**
Kubernetes には次のシステム PriorityClass があります。
- **system-cluster-critical**: クラスタ運用に不可欠な Pod 用（値: 2000000000）
- **system-node-critical**: Node 運用に不可欠な Pod 用（値: 2000001000）

```bash
# Check system PriorityClasses
kubectl get priorityclasses | grep system
```

**PriorityClass の使用例:**
```yaml
# Define multiple priority classes
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
globalDefault: false
description: "High priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: medium-priority
value: 100000
globalDefault: false
description: "Medium priority pods"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: low-priority
value: 10000
globalDefault: false
description: "Low priority pods"
preemptionPolicy: Never  # Do not preempt
```

**優先度と preemption 関連メトリクスの監視:**
```bash
# Check preemption events
kubectl get events | grep -i preempt

# Check pod priorities
kubectl get pods -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority
```

**カスタムスケジューラーで優先度を扱う:**
カスタムスケジューラーを実装する場合は、スケジューリングを判断する際に Pod の優先度を考慮してください。

```go
package priorityexample

import (
    "sort"
    v1 "k8s.io/api/core/v1"
)

func podPriority(pod *v1.Pod) int32 {
    if pod == nil || pod.Spec.Priority == nil {
        return 0
    }
    return *pod.Spec.Priority
}

// Demonstrates only priority comparison, not queue backoff or requeue handling.
func sortPodsByPriority(pods []*v1.Pod) {
    sort.SliceStable(pods, func(i, j int) bool {
        return podPriority(pods[i]) > podPriority(pods[j])
    })
}
```

**ほかの選択肢が誤りである理由:**
- A. PodSchedulingPolicy: Kubernetes API に存在しないリソースです。
- C. SchedulingPriority: Kubernetes API に存在しないリソースです。
- D. PodPriority: リソース型ではなく、Pod spec のフィールド（`spec.priority`）です。このフィールドは PriorityClass によって自動的に設定されます。
</details>

### 10. Kubernetes スケジューラーの `NodeResourcesFit` プラグインの役割は何ですか？

A. Node の物理的な場所に応じて Pod を配置する
B. 残りの割り当て可能リソースと Pod の実効要求を比較する
C. Node の OS と Pod の互換性を確認する
D. Node のネットワーク帯域幅を測定する

<details>
<summary>解答を表示</summary>

**回答: B. 残りの割り当て可能リソースと Pod の実効要求を比較する**

**解説:**
`NodeResourcesFit` は、Pod の実効要求を、すでに割り当て済みまたは仮定済みの要求を差し引いた Node の **allocatable resources** と比較します。Pod 数の上限と、関連する extended resource も確認します。新しい Pod と `Capacity` 全体を単純に比較するわけではありません。また、CPU やメモリの limit の合計が容量を超えた場合に、通常それを拒否するものでもありません。

**リソースの計算:**
* 通常のコンテナ、順番に実行される init container、再起動可能な sidecar、Pod overhead、サポート対象の Pod-level resource 設定を考慮します。API の defaulting により limit から request が導出される場合もあります。
* scheduler snapshot を使用してください。そこには仮定済みバインドも含まれます。API から Running Pod だけを列挙して合計すると、予約済みの需要を見落とします。
* 対象バージョンの feature gate と DRA の動作を維持してください。CPU とメモリの計算だけでは、リソース適合を完全には実装できません。

**設定:**
`NodeResourcesFit` は既定で有効です。この例では Filter 段階を維持したまま、スコアリング戦略を変更します。

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
profiles:
- schedulerName: custom-scheduler
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

**スコアリング戦略:**
NodeResourcesFit プラグインは次のスコアリング戦略をサポートします。

1. **LeastAllocated**: 要求済みリソースの割合が低い Node に高いスコアを与えます。リソース使用を分散するのに役立ちます。
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **MostAllocated**: 要求済みリソースの割合が高い Node に高いスコアを与えます。Node 数を抑えるため、リソース使用を集約するのに役立ちます。
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **RequestedToCapacityRatio**: 設定した区分線形の形状を使い、要求リソースと容量の比率に基づいてスコアを付けます。上記の単一リソースの簡略式では、整数の丸め、ゼロまたは容量超過時の扱い、リソースの重みを省略しています。実使用率に基づく式ではありません。

**リソースの種類:**
NodeResourcesFit プラグインは次のリソースを扱います。

1. **CPU**: コアまたはミリコアで測定します。
2. **メモリ**: バイト単位で測定します。
3. **Ephemeral storage**: Node のローカル一時ストレージです。
4. **Extended resources**: GPU、FPGA などのカスタムリソースです。

**Node リソースの確認:**
```bash
# Check node's allocatable resources
kubectl describe node <node-name> | grep Allocatable -A 5

# Check node's resource usage
kubectl top node <node-name>
```

**Pod のリソース要求の確認:**
```bash
# Check pod's resource requests
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].resources.requests}'
```

**安全な適合判定の実装:**
scheduler framework では upstream のプラグインを維持してください。新しい Pod の CPU/メモリだけを合計し、既存の需要を無視して `true` を返す自作関数は、正しい置き換えになりません。付属の監査では、2コアの Node に既存の 1500m 要求があるケースについて、固定された upstream の適合判定をローカルで確認します。追加の 1コア要求は拒否され、CPU limit がより大きくても 250m の要求は適合します。これはローカルの計算確認であり、クラスタのスケジューリング性能試験ではありません。

Metrics Server が利用できる場合、`kubectl top` は現在のメトリクスを表示します。これらは既定の適合判定やスコアリングに使う要求量の合計ではありません。差異を調べる際は init container と overhead を含む Pod spec 全体を確認してください。

**ほかの選択肢が誤りである理由:**
- A. Node の物理的な場所に応じて Pod を配置する: NodeAffinity や PodTopologySpread など、topology 関連プラグインの役割です。
- C. Node の OS と Pod の互換性を確認する: 必要に応じて OS label と配置制約を使います。それだけでイメージやランタイムの互換性が証明されるわけではありません。`NodeResourcesFit` の役割でもありません。
- D. Node のネットワーク帯域幅を測定する: Kubernetes スケジューラーは既定ではネットワーク帯域幅を考慮しません。カスタムメトリクスとプラグインが必要です。
</details>

## 参考資料

この例は [Part 1 モジュールと Deployment](../../scheduling/01-custom-scheduler-part1.md) を使用します。ローカルのコンパイル、設定、計算の確認は本番運用への適合性を証明するものではありません。クラスタや AWS へのデプロイは行っていません。

* [Scheduler configuration and default plugins](https://kubernetes.io/docs/reference/scheduling/config/)
* [Framework extension points](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [Resource scoring](https://kubernetes.io/docs/concepts/scheduling-eviction/resource-bin-packing/)
* [Priority and preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [Pinned Go interfaces](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
