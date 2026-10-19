# カスタムスケジューラークイズ（パート3）

> **例のベースライン**: Kubernetes 1.35.8、Go 1.27.2。ネイティブ1.37の機能は別途記載
> **最終更新日**: 2026年10月16日

このクイズでは、Kubernetesにおけるカスタムスケジューラーの実装と利用に関する高度な理解を確認します。

## クイズ問題

### 1. 複数のスケジューラーに関する主張のうち、誤っているものはどれですか？

A. スケジューラーを追加すると、APIの監視やキャッシュに必要な処理が増える
B. 独立して仮定された配置は、リソースを奪い合う可能性がある
C. スケジューラーを追加すると、ノード容量が自動的に増える
D. 関係のないスケジューラーグループは、異なるリーダー選出Leaseを使う必要がある

<details>
<summary>答えを表示</summary>

**答え: C. スケジューラーを追加すると、ノード容量が自動的に増える**

**解説:**
スケジューラーはPodを割り当てますが、ノード容量を作り出すものではありません。スケジューラーの追加により、APIやネットワークの負荷が増えることがあります。各スケジューラーは確定済みのPod状態を監視しますが、それぞれのメモリ上の配置仮定は、他のスケジューラーと共有される予約トランザクションではありません。リソースフィルターを維持し、共有プールでの同時スケジューリングをテストしてください。

`schedulerName`を省略すると`default-scheduler`が選ばれます。準拠するすべてのスケジューラーがそのPodをbindするわけではありません。同一スケジューラーのレプリカは高可用性のため意図的に同じLeaseを共有します。無関係なグループが同じLeaseを共有すると互いにブロックする可能性があり、リーダーシップを協調せずに同一プロファイルを使うプロセスは競合する可能性があります。

**Podの振り分け例:**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: default-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: custom-pod
spec:
  schedulerName: custom-scheduler
  tolerations:
  - key: dedicated
    operator: Equal
    value: custom-scheduler
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: 100m
        memory: 64Mi
```

**スケジューラーの識別情報とノードプールポリシーの分離:**
パート1のDeploymentとRBACを一式で使用してください。名前とLeaseの識別情報は`KubeSchedulerConfiguration`で設定し、廃止された`--scheduler-name`フラグは使いません。組み込みの`NodeAffinity`プラグインはプロファイル単位の`addedAffinity`をサポートします。デフォルトの`NodeSelector`プラグインはありません。

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
  - name: NodeAffinity
    args:
      addedAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
          - matchExpressions:
            - key: training.example.com/scheduler-pool
              operator: In
              values:
              - custom
```

```bash
# Only label/taint a node selected for this isolated lab.
: "${CUSTOM_NODE:?Select the lab node}"
kubectl label node "$CUSTOM_NODE" training.example.com/scheduler-pool=custom --overwrite
kubectl taint node "$CUSTOM_NODE" dedicated=custom-scheduler:NoSchedule --overwrite
```

上のカスタムPodは例のtaintをtolerateします。Tolerationは配置を強制するものではなく、スケジューラー名、ノードラベル、クォータはいずれもセキュリティ境界ではありません。次のnamespaceクォータは、受け入れられるリクエストを制限しますが、ノードプールを予約するものではありません。対象ワークロードにリクエストを指定し、先にnamespaceを作成してください。
**namespaceクォータの例:**
   ```yaml
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: default-scheduler-quota
     namespace: default-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi

   ---
   apiVersion: v1
   kind: ResourceQuota
   metadata:
     name: custom-scheduler-quota
     namespace: custom-workloads
   spec:
     hard:
       pods: "10"
       requests.cpu: "20"
       requests.memory: 40Gi
   ```

**セカンダリースケジューラーの読み取り専用監視:**
実際のnamespaceとラベルを使用してください。EKSのマネージドコントロールプレーンコンポーネントは、ここに示すセカンダリーDeploymentではありません。

```bash
kubectl -n scheduler-lab get pods -l app=custom-scheduler
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100
kubectl -n scheduler-lab get lease custom-scheduler
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**その他の選択肢:** A、B、Dはいずれも実際に考慮すべきワークロードまたは調整上の事項です。
</details>

### 2. Kubernetesスケジューラーにおける「Permit」拡張ポイントの役割は何ですか？

A. Podをノードにbindする
B. Podのスケジューリングを許可、拒否、または遅延する
C. Podを実行できないノードを除外する
D. ノードにスコアを割り当てる

<details>
<summary>答えを表示</summary>

**答え: B. Podのスケジューリングを許可、拒否、または遅延する**

**解説:**
スケジューリングフレームワークの`Permit`プラグインは、ノードの選択後、bind処理の前に実行されます。これによりPodの処理を続行させたり、拒否したり、待機させたりできます。

**Permitのバージョン付き契約:**
`Permit(ctx, fwk.CycleState, pod, nodeName)`はステータスと待機時間を返します。`Success`は処理を続行し、`Wait`はフレームワークにPodを保留させます。`Unschedulable`などの失敗ステータスは試行を拒否します。`framework.Deny`というenumはありません。拒否されても直ちに別ノードへbindされるわけではなく、再試行・バックオフと予約の後始末が続きます。

`TaintToleration`と`PodTopologySpread`はデフォルトのPermitプラグインではありません。ベースラインでは、実際のFilter/Scoreステージに残します。

**Permitインターフェイスの完全な例（`quizplugins/permit.go`）:**
注釈の値はテスト用の指示であり、信頼できる認可情報ではありません。外部の承認サービスは用意されていません。フレームワークに登録された後で統合テストドライバーが解放しない限り、`wait` Podはタイムアウトします。消費されない非公開チャネルからフレームワークの待機中Podを解放することはできません。

```go
package quizplugins

import (
	"context"
	"time"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	fwk "k8s.io/kube-scheduler/framework"
)

type CustomPermit struct{ handle fwk.Handle }

var _ fwk.PermitPlugin = &CustomPermit{}

func (*CustomPermit) Name() string { return "CustomPermit" }

func (*CustomPermit) Permit(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) (*fwk.Status, time.Duration) {
	// These are test directives, not an authorization or approval mechanism.
	switch pod.Annotations["training.example.com/permit"] {
	case "", "allow":
		return nil, 0
	case "wait":
		return fwk.NewStatus(fwk.Wait, "waiting for the test driver"), 30 * time.Second
	case "deny":
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "test driver denied"), 0
	default:
		return fwk.NewStatus(fwk.Error, "unknown test permit directive"), 0
	}
}

// Call only after the framework has registered the waiting Pod. The caller
// must handle false (not registered yet, already released, deleted or timed out).
func (p *CustomPermit) Allow(uid types.UID) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Allow(p.Name())
	return true
}

func (p *CustomPermit) Reject(uid types.UID, reason string) bool {
	waiting := p.handle.GetWaitingPod(uid)
	if waiting == nil {
		return false
	}
	waiting.Reject(p.Name(), reason)
	return true
}

func NewPermit(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &CustomPermit{handle: handle}, nil
}
```

これと後述のPreBind例を`cmd/quiz-scheduler/main.go`に登録します。ビルド前に両方のソースファイルを保存してください。

```go
package main

import (
	"os"

	"example.com/custom-scheduler/quizplugins"
	"k8s.io/component-base/cli"
	"k8s.io/kubernetes/cmd/kube-scheduler/app"
)

func main() {
	command := app.NewSchedulerCommand(
		app.WithPlugin("CustomPermit", quizplugins.NewPermit),
		app.WithPlugin("IdentityPreBind", quizplugins.NewPreBind),
	)
	os.Exit(cli.Run(command))
}
```

パート1のモジュールを使い、`CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler`でビルドします。該当する拡張ポイントだけを有効にし、デフォルト設定は維持してください。

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
    permit:
      enabled:
      - name: CustomPermit
```

**Permitのユースケース:**
1. **Gang scheduling**: 関連するPodグループの全Podをスケジュールできる状態になるまで、処理を待たせる。
2. **リソース予約**: Podのスケジュール前に外部リソースを予約する。
3. **ポリシー検証**: Podのスケジューリングが組織のポリシーに準拠することを確認する。
4. **承認ワークフロー**: Podのスケジューリングに外部承認を求める。

**Permitバリアだけでは完全なGang schedulerにならない理由:**
実用的な実装には、namespaceとUIDによるグループ識別、一意なメンバー数の集計、再試行・削除・タイムアウトへの対応、失敗時の予約解放、bind失敗への対処が必要です。非公開の`WaitingPod`を自作したり、同じ再試行を重複して数えたり、Permitの戻り値より前に現在のPodが登録済みだとみなしたりしてはいけません。バリアはコンテナの同時起動やstarvationが起きないことを保証しません。保守されている実装については、設問3を参照してください。

**その他の選択肢の問題点:**
- A. Podをノードにbindする: これは`Bind`拡張ポイントの役割です。
- C. Podを実行できないノードを除外する: これは`Filter`拡張ポイントの役割です。
- D. ノードにスコアを割り当てる: これは`Score`拡張ポイントの役割です。
</details>
### 3. KubernetesにおけるGang Schedulingの主な目的は何ですか？

A. Podを特定のノードだけに配置する
B. 必要なPodグループの配置を調整する
C. Podを複数のノードに均等に分散する
D. 優先度に基づいてPodをスケジュールする

<details>
<summary>答えを表示</summary>

**答え: B. 必要なPodグループの配置を調整する**

**解説:**
Gang Schedulingの目的は、必要なグループの配置を調整してから処理を進めることです。分散学習ジョブや分散データ処理など、すべての構成要素が同時に動作しなければならないワークロードで重要です。

**Gang schedulingが必要な理由:**
1. **全か無かの要件**: すべての構成要素を同時に動かす必要があるワークロードでは、一部だけが動いてもジョブは進みません。
2. **リソース浪費の防止**: 一部のPodだけがスケジュールされ、残りが待機すると、先に配置されたPodが使うリソースが無駄になることがあります。
3. **デッドロックの防止**: 相互依存するPodを別々のタイミングで配置すると、デッドロックが発生することがあります。

**実装方法とバージョン:**
Kubernetes 1.35では`GenericWorkload`/`GangScheduling`がオプトインのalpha機能として導入されました。上流Kubernetes 1.37のPodGroupスケジューリング機能はbetaですが、デフォルトでは無効です。`GenericWorkload`と`scheduling.k8s.io/v1beta1` APIが必要です。これはEKSでの機能提供を示す証拠でも、マネージドコントロールプレーンのフラグを変更してよいという許可でもありません。

Volcanoは別途インストールするスケジューラーです。Kube-batchはVolcanoの旧称にあたる前身であり、現在の別製品として推奨するものではありません。対応するコントローラー、CRD、Gang Schedulingの有効化、Openキューが前提条件です。

**Volcano Jobの例（1.15.2のschemaで確認済み）:**
コントローラーがPodGroupを作成します。`minMember: 4`に対してPodが1つだけの定義ではなく、4つすべてのメンバーを定義しています。このCPUのみを使う`sleep`ワークロードはマニフェスト上の関係を示す例であり、分散学習やベンチマークではありません。実環境にはデプロイしていません。

```yaml
apiVersion: batch.volcano.sh/v1alpha1
kind: Job
metadata:
  name: gang-demo
  namespace: default
spec:
  minAvailable: 4
  schedulerName: volcano
  queue: default
  maxRetry: 1
  tasks:
  - name: workers
    replicas: 4
    template:
      spec:
        restartPolicy: Never
        containers:
        - name: worker
          image: busybox:1.38.0
          command:
          - sh
          - -c
          - sleep 60
          resources:
            requests:
              cpu: 250m
              memory: 128Mi
            limits:
              memory: 256Mi
```

スケジューリング判断は最低限必要なグループを調整しますが、プロセスが同時刻に起動することまでは保証しません。アプリケーション側のバリア、タイムアウト方針、公平性、復旧は別途必要です。ネイティブPodGroup配置には、異種PodやPod間依存関係に関する既知の制限もあります。配置順序のアルゴリズムで実行可能な配置が必ず見つかるとは限りません。

**Gang schedulingの長所と短所:**
長所:
- 設定された最低限のグループを調整できる
- リソースの浪費を防げる
- 部分割り当てによるデッドロックを減らせる。ただし公平性とタイムアウトへの配慮は必要

短所:
- 実装が複雑になる
- スケジューリングが遅れる可能性がある
- クラスターのリソース利用率が下がる可能性がある

**Gang schedulingが必要なワークロード:**
1. **分散学習ジョブ**: TensorFlowやPyTorchなどの分散学習フレームワーク
2. **分散データ処理**: SparkやFlinkなどのフレームワーク
3. **MPIジョブ**: 高性能計算（HPC）ワークロード
4. **密結合並列ジョブ**: 宣言された最低数のワーカーを必要とするワークロード

**その他の選択肢の問題点:**
- A. Podを特定のノードだけに配置する: これはnode selectorまたはnode affinityの役割です。
- C. Podを複数のノードに均等に分散する: これはPod topology spread constraintの役割です。
- D. 優先度に基づいてPodをスケジュールする: これはPod priorityとpreemptionの役割です。
</details>

### 4. kube-schedulerのextender callback契約に含まれない関数はどれですか？

A. 候補ノードのフィルタリング
B. 候補ノードの優先順位付け
C. Podとノードの任意のbind
D. `ValidatingWebhookConfiguration`によるAdmission検証

<details>
<summary>答えを表示</summary>

**答え: D. `ValidatingWebhookConfiguration`によるAdmission検証**

Extenderは設定に応じてfilter、prioritize、preempt、bind callbackを実装できます。決まったURLパスはありません。たとえば`filterVerb`に`validate`というパス名を指定することもできますが、payloadと意味がfilteringであることに変わりはありません。Admission webhookは別のAPI契約です。

**設定:**
パート2のTLSサービスと証明書の前提条件を再利用してください。`extenders`はトップレベルです。必須のフィルタリングはfail-closedにし、スケジューラー自身のリソース計算も維持してください。

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
- urlPrefix: https://scheduler-extender.scheduler-lab.svc:8443
  filterVerb: filter
  prioritizeVerb: prioritize
  weight: 1
  enableHTTPS: true
  tlsConfig:
    caFile: /etc/extender-client/ca.crt
    certFile: /etc/extender-client/tls.crt
    keyFile: /etc/extender-client/tls.key
  httpTimeout: 2s
  nodeCacheCapable: false
  ignorable: false
```

**wire contract:**
* Filter/prioritizeは`ExtenderArgs`で`Pod`と、`nodeCacheCapable`に応じて完全な`Nodes`または`NodeNames`を受け取ります。
* Filterは`Nodes`/`NodeNames`、失敗理由のmap、`Error`を返します。
* Prioritizeは`[{"Host":"node-a","Score":7}]`のような配列をそのまま返します。scoreは0～10で、100ではありません。優先順位付けでエラーが発生するとそのextenderのscoreは除外されるため、必須制約の適用には使えません。
* Bindは`PodName`、`PodNamespace`、`PodUID`、`Node`を使います。実際のbindに成功した後でのみ成功を返してください。`customBind`がnilを返すだけのstubはbind実装ではありません。
* Preemptは候補victimのmapを含む`ExtenderPreemptionArgs`を使い、`ExtenderPreemptionResult.NodeNameToMetaVictims`を返します。架空の`podsToPreempt` envelopeは返しません。

[パート2](../../scheduling/02-custom-scheduler-part2.md)にある、上限を設けたhandlerを一式で使用してください。`bindVerb`は未設定のままにして、`DefaultBinder`を維持します。ここでは追加のHTTP serverも、常に成功を返す偽のbind endpointも用意していません。
</details>
### 5. Kubernetesスケジューラーフレームワークにおける「PostFilter」拡張ポイントの役割は何ですか？

A. filtering後にノードへスコアを付ける
B. filtering後にPodをノードへbindする
C. filteringで実行可能なノードがない場合にpreemptionを実行する
D. filtering後にPodの状態を更新する

<details>
<summary>答えを表示</summary>

**答え: C. filteringで実行可能なノードがない場合にpreemptionを実行する**

**解説:**
PostFilterは、filteringの結果、実行可能なノードが1つもない場合に復旧を試みます。デフォルトのpreemptionはその実装の1つです。全ノードが除外されPodを配置できないとき、PostFilterプラグインは、その後の試行を可能にするための適切な処理を試せます。

**バージョン付きインターフェイスと安全な拡張:**
固定されたAPIは`fwk.CycleState`と`fwk.NodeToStatusReader`を使い、`PostFilterResult`は`NominatingInfo`を埋め込みます。nominated nodeは次の配置候補であり、bindが確定したことを意味しません。

完全に実装・テストされた代替策がない限り、デフォルトの`DefaultPreemption`を維持してください。これは残りの制約を考慮して優先度の低いvictimを評価し、PDB違反をベストエフォートで考慮します。victim選択を省いたループからPodを直接削除するのは安全ではありません。復旧プラグインは他の適切な処理も行えるため、PostFilterが定義上preemptionだけに限られるわけではありません。

以下の設定は、デフォルト実装を無効化せずに調整するものです。candidateの上限は探索範囲を制限しますが、全体最適や最終的なスケジューリングを保証しません。

**Preemption関連の設定:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: DefaultPreemption
    args:
      minCandidateNodesPercentage: 10
      minCandidateNodesAbsolute: 100
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Preemptionの流れ:**
1. Podがすべてのノードでfilteringに失敗すると、PostFilter phaseが呼び出されます。
2. PostFilterプラグインがpreemption候補のノードを特定します。
3. 各ノードでpreemptするPodを決定します。
4. preemption後にPodを配置できることを検証します。
5. preemption方針を選択します。
6. 選択したノードをPodの`nominatedNodeName`に設定します。
7. preemptされたPodは猶予期間を設けて終了します。
8. victimの終了後にスケジューリングを再試行します。nominated nodeはbindを保証しません。

**Preemption関連メトリクスの監視:**
```bash
# Inspect nominations; scheduler metrics require its authenticated HTTPS endpoint.
kubectl get pods -A -o custom-columns=NAME:.metadata.name,NOMINATED:.status.nominatedNodeName
```

**Preemptionイベントの確認:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**その他の選択肢の問題点:**
- A. filtering後にノードへスコアを付ける: これは`Score`拡張ポイントの役割です。
- B. filtering後にPodをノードへbindする: これは`Bind`拡張ポイントの役割です。
- D. filtering後にPodの状態を更新する: これはスケジューラーフレームワークの拡張ポイントではありません。
</details>

### 6. Kubernetesスケジューラーの`NodeResourcesBalancedAllocation`プラグインの主な目的は何ですか？

A. 要求CPUとメモリの割合が均衡しているノードに高いスコアを付ける
B. リソース使用率が低いノードに高いスコアを付ける
C. リソース使用率が高いノードに高いスコアを付ける
D. ノードのリソース上限を設定する

<details>
<summary>答えを表示</summary>

**答え: A. 要求CPUとメモリの割合が均衡しているノードに高いスコアを付ける**

**解説:**
`NodeResourcesBalancedAllocation`は、実測CPU/メモリ使用率ではなく、**実効的な要求量とallocatable量の比率**を均衡させます。固定された実装で対象となるリソースが2つの場合は、次のようになります。

```
cpuFraction = min(requestedCPU / allocatableCPU, 1)
memoryFraction = min(requestedMemory / allocatableMemory, 1)
std = abs(cpuFraction - memoryFraction) / 2
score = int((1 - std) * 100)
```

要求量の合計には、配置対象のPodとスケジューラーが計上済みの要求量が含まれます。このプラグインは、バージョン固有のリソースオプションも扱います。対象リソースが2つを超える場合は母標準偏差を使います。

以下は実測値ではなく、計算方法を示す例です。割合が80%/80%なら100、90%/50%なら80、30%/90%なら70になります。他のプラグインとそのweightもノード選択に影響します。

**scheduler configurationで`NodeResourcesBalancedAllocation`を有効にする:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    score:
      enabled:
      - name: NodeResourcesBalancedAllocation
        weight: 2
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**プラグイン設定:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  pluginConfig:
  - name: NodeResourcesBalancedAllocation
    args:
      resources:
      - name: cpu
        weight: 1
      - name: memory
        weight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**`NodeResourcesBalancedAllocation`と他のscoreプラグインの比較:**
1. **`NodeResourcesBalancedAllocation`**: 要求量とallocatable量の比率が均衡したノードを優先します。
2. **`NodeResourcesFit`**: 設定された`LeastAllocated`、`MostAllocated`、または`RequestedToCapacityRatio`のscore方式を使います。
3. **`NodeResourcesFit`の`LeastAllocated`方式**: 要求割合の低いノードを優先します。
4. **`NodeResourcesFit`の`MostAllocated`方式**: 要求割合の高いノードを優先します。

**ユースケース:**
1. **リソースバランス**: クラスター全体でCPUとメモリの要求量の偏りを減らします。
2. **ボトルネック予防**: 要求リソースの不均衡を減らせますが、実行時のボトルネックは防ぎません。
3. **スケーラビリティ向上**: リソース要求が均衡したクラスターは、より効率よくスケールできます。

**算術ヘルパー（`scoring/formulas.go`）:**
これは数式と、元の章で説明する任意の70:30 GPU weight付けを確認するものです。完全なスケジューラープラグインではありません。CPUのmillicore、init/sidecar container、overhead、機能固有の処理を含む、組み込みのリソース計算を維持してください。

```go
package scoring

import (
	"fmt"
	"math"
)

// Two-resource form of the pinned BalancedAllocation formula.
// Inputs are effective requested/allocatable fractions, not live utilization.
func BalancedScore(cpuFraction, memoryFraction float64) (int64, error) {
	for _, value := range []float64{cpuFraction, memoryFraction} {
		if math.IsNaN(value) || math.IsInf(value, 0) || value < 0 {
			return 0, fmt.Errorf("fractions must be finite and non-negative")
		}
	}
	cpuFraction = math.Min(cpuFraction, 1)
	memoryFraction = math.Min(memoryFraction, 1)
	std := math.Abs(cpuFraction-memoryFraction) / 2
	return int64((1 - std) * 100), nil
}

// Optional policy arithmetic only; no GPU telemetry collector is implemented here.
// The caller must establish freshness and workload/device relevance first.
func WeightedGPUScore(packing int64, utilization float64) (int64, error) {
	if packing < 0 || packing > 100 || math.IsNaN(utilization) || math.IsInf(utilization, 0) || utilization < 0 || utilization > 1 {
		return 0, fmt.Errorf("packing must be 0..100 and utilization finite in 0..1")
	}
	utilizationScore := int64((1 - utilization) * 100)
	return (packing*7 + utilizationScore*3) / 10, nil
}
```

**その他の選択肢の問題点:**
- B. リソース使用率が低いノードに高いスコアを付ける: これは`NodeResourcesFit`の`LeastAllocated`方式です。
- C. リソース使用率が高いノードに高いスコアを付ける: これは`NodeResourcesFit`の`MostAllocated`方式です。
- D. ノードのリソース上限を設定する: これはスケジューラープラグインの役割ではありません。ノードのリソース上限はノード自体のプロパティです。
</details>
### 7. Kubernetesスケジューラーにおける「PreBind」拡張ポイントの役割は何ですか？

A. Podをノードにbindする
B. bind前に必要な処理を行う
C. bind後にクリーンアップする
D. bind失敗後に復旧処理を行う

<details>
<summary>答えを表示</summary>

**答え: B. bind前に必要な処理を行う**

**解説:**
PreBindは、Podのbind確定前に必要な準備を調整します。`VolumeBinding`は、ストレージコントローラーとの連携による、スケジューリングに関連したvolumeのbindやprovisioningを扱います。`DefaultPreBind`というデフォルトプラグインはありません。

1.35.8のインターフェイスには`fwk.CycleState`を使う`PreBindPreFlight`と`PreBind`の**両方**があります。Preflightは、不要な処理を避けるためにPodについてSkipを返せます。

**読み取り専用の完全な例（`quizplugins/prebind.go`）:**
このオプトインのidentity checkは、volumeのprovisioning、CNIの設定、service endpointの作成、GPUの割り当てを行いません。それらには実際のコントローラーやデバイス機構が必要です。`DefaultBinder`はすでにUIDを持つため、この追加のround tripはインターフェイスの例にすぎません。

```go
package quizplugins

import (
	"context"
	"fmt"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	fwk "k8s.io/kube-scheduler/framework"
)

type IdentityPreBind struct{ handle fwk.Handle }

var _ fwk.PreBindPlugin = &IdentityPreBind{}

func (*IdentityPreBind) Name() string { return "IdentityPreBind" }

func (*IdentityPreBind) PreBindPreFlight(_ context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	if pod.Annotations["training.example.com/check-identity"] != "true" {
		return fwk.NewStatus(fwk.Skip)
	}
	return nil
}

// Read-only interface demonstration. DefaultBinder already carries the Pod UID;
// this extra API round trip is not required for ordinary scheduling.
func (p *IdentityPreBind) PreBind(parent context.Context, _ fwk.CycleState, pod *v1.Pod, _ string) *fwk.Status {
	ctx, cancel := context.WithTimeout(parent, 3*time.Second)
	defer cancel()
	current, err := p.handle.ClientSet().CoreV1().Pods(pod.Namespace).Get(ctx, pod.Name, metav1.GetOptions{})
	if err != nil {
		return fwk.AsStatus(err)
	}
	if current.UID != pod.UID || current.DeletionTimestamp != nil || current.Spec.NodeName != "" {
		return fwk.AsStatus(fmt.Errorf("Pod identity/state changed before binding"))
	}
	return nil
}

func NewPreBind(_ context.Context, _ runtime.Object, handle fwk.Handle) (fwk.Plugin, error) {
	return &IdentityPreBind{handle: handle}, nil
}
```

設問2のコマンドにこのプラグインを登録します。`VolumeBinding`は有効なままにしてください。

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
    preBind:
      enabled:
      - name: IdentityPreBind
```

**責務の境界:**
ストレージprovisioningは該当するprovisioner/controllerが行い、スケジューラーは配置とbindを調整します。CNIネットワークやSecret/volumeのmountは割り当て後にruntime/kubeletの仕組みで行われます。Service、EndpointSlice、load balancerの各controllerは、それぞれが管理するリソースを調整します。カスタムプラグインが外部予約を調整するなら、上限のある冪等な操作と独自のUnreserveによる後始末を実装する必要があります。フレームワークは任意の外部副作用を自動で取り消せません。

**PreBind失敗時の処理:**
PreBindプラグインが失敗を返すと:
1. スケジューリングcycleが中止されます。
2. Podはスケジューリングqueueに戻ります。
3. Unreserve hookがプラグイン所有の仮定を取り消します。外部リソースの後始末は実際に実装する必要があります。
4. 失敗イベントが記録されます。

**PreBindのログとイベントの監視:**
```bash
# Check PreBind-related messages in scheduler logs
kubectl -n scheduler-lab logs -l app=custom-scheduler --prefix --tail=100

# Check pod events
kubectl describe pod <pod-name>
```

**その他の選択肢の問題点:**
- A. Podをノードにbindする: これは`Bind`拡張ポイントの役割です。
- C. bind後にクリーンアップする: これは`PostBind`拡張ポイントの役割です。
- D. 失敗後の復旧には、プラグイン所有の予約に対するUnreserveと、フレームワークの再試行処理が含まれます。
</details>

### 8. Kubernetesスケジューラーの`NodeResourcesFit`プラグインの主な目的は何ですか？

A. ノードのリソース使用量を監視する
B. ノードのリソース上限を設定する
C. 残りのallocatable量とPodの実効要求量を比較する
D. ノード間のリソース使用量の均衡を保つ

<details>
<summary>答えを表示</summary>

**答え: C. 残りのallocatable量とPodの実効要求量を比較する**

**解説:**
`NodeResourcesFit`は、Podの実効要求量を、割り当て済み/仮定済みの要求量を差し引いたallocatable量と比較します。該当するPod数と拡張リソースの制約も対象です。通常、CPUやメモリのlimit合計を容量と比較するものではありません。Admission/defaultingで導出される要求量、init container、再起動可能なsidecar、overhead、有効なリソース機能を考慮する必要があります。

デフォルトのFilter stageを維持してください。以下の設定はscoreの動作を変えますが、リソース適合性の判定処理は置き換えません。

**`NodeResourcesFit`プラグインの設定:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    filter:
      enabled:
      - name: NodeResourcesFit
    score:
      enabled:
      - name: NodeResourcesFit
        weight: 1
  pluginConfig:
  - name: NodeResourcesFit
    args:
      scoringStrategy:
        type: LeastAllocated
        resources:
        - name: cpu
          weight: 1
        - name: memory
          weight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**Score方式:**
`NodeResourcesFit`プラグインは次のscore方式をサポートします。

1. **`LeastAllocated`**: 要求割合の低いノードに高いscoreを付けます。
   ```
   score ≈ 100 × (allocatable - requested) / allocatable
   ```

2. **`MostAllocated`**: 要求割合の高いノードに高いscoreを付けます。
   ```
   score ≈ 100 × requested / allocatable
   ```

3. **`RequestedToCapacityRatio`**: 要求量とallocatable量の比率に対して、設定した区分線形の形状を適用します。上の数式は単一リソースを使った簡略例です。

**独自実装に関する注意:**
上流の`NodeResourcesFit`を維持してください。score weight mapに載ったリソースだけを見ると、必須リソースを見落とす場合があります。また、CPUの`Quantity.Value()`はmillicore精度を失います。通常のcontainerの要求量だけを合計しても、init/sidecar/overheadの動作を取りこぼします。比率を整数化してからscaleする自作scoreでは、すべて0になることもあります。

パート1のローカルチェックは、固定バージョンの実際のfit関数をテストします。2 coreのノードで要求済み量が1500mの場合、さらに1 coreを要求すると収まりませんが、CPU limitがより大きくても250mなら収まります。これは合成データによる計算テストであり、クラスターのベンチマークではありません。

**リソース要求量とlimitの例:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: resource-demo
spec:
  containers:
  - name: nginx
    image: nginx:1.30.6
    resources:
      requests:
        cpu: "500m"
        memory: "256Mi"
      limits:
        cpu: "1"
        memory: "512Mi"
```

**その他の選択肢の問題点:**
- A. ノードのリソース使用量を監視する: これはmetrics serverや監視システムの役割です。
- B. ノードのリソース上限を設定する: これはノード設定またはkubeletの役割です。
- D. ノード間のリソース使用量の均衡を保つ: これは`NodeResourcesBalancedAllocation`プラグインの役割です。
</details>
### 9. Kubernetesスケジューラーの`InterPodAffinity`プラグインの主な目的は何ですか？

A. Podとノード間のaffinityを処理する
B. Pod間のaffinityとanti-affinityを処理する
C. Podとvolume間のaffinityを処理する
D. Podとservice間のaffinityを処理する

<details>
<summary>答えを表示</summary>

**答え: B. Pod間のaffinityとanti-affinityを処理する**

**解説:**
`InterPodAffinity`プラグインは、Pod間のaffinityとanti-affinityを処理します。Podを他のPodと同じtopology domain（node、zone、regionなど）に配置するか（affinity）、異なるdomainに配置するか（anti-affinity）を制御します。

**`InterPodAffinity`プラグインの主な機能:**
1. **Pod affinity ruleの処理**: 特定のlabelを持つ他のPodと同じtopology domainに配置します。
2. **Pod anti-affinity ruleの処理**: 特定のlabelを持つ他のPodとは異なるtopology domainに配置します。
3. **Topology domainの考慮**: node、zone、regionなど、複数階層のtopology domainを考慮します。

**Pod affinityとanti-affinityの種類:**
1. **`requiredDuringSchedulingIgnoredDuringExecution`**: Podをスケジュールするために満たさなければならない規則（hard requirement）。
2. **`preferredDuringSchedulingIgnoredDuringExecution`**: 必須ではないものの、優先される規則（soft requirement）。

**Pod affinityとanti-affinityの例:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web
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
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app
              operator: In
              values:
              - web
          topologyKey: kubernetes.io/hostname
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**`InterPodAffinity`プラグインの設定:**
```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
- schedulerName: custom-scheduler
  plugins:
    preFilter:
      enabled:
      - name: InterPodAffinity
    filter:
      enabled:
      - name: InterPodAffinity
    score:
      enabled:
      - name: InterPodAffinity
        weight: 2
  pluginConfig:
  - name: InterPodAffinity
    args:
      hardPodAffinityWeight: 1
leaderElection:
  leaderElect: true
  resourceLock: leases
  resourceName: custom-scheduler
  resourceNamespace: scheduler-lab
  leaseDuration: 15s
  renewDeadline: 10s
  retryPeriod: 2s
```

**組み込み実装を一式で使用する:**
`InterPodAffinity`とその前処理を維持してください。namespace selector、入力Podのrequired term、既存Podのrequired anti-affinity、topology、self-affinityのbootstrap動作を考慮します。単なる`*v1.Affinity`は`Clone`を備えたフレームワークのStateDataではありません。また、stateがない場合に必須のチェックを黙って回避してはいけません。

この例では、選択したnamespaceに適合する`app=cache` Podが存在する必要があります。preferred anti-affinityは分散を保証しません。`hardPodAffinityWeight`はscoreに影響しますが、必須制約を緩和しません。実際のワークロードで規模と配置のトレードオフをテストしてください。同じ場所への配置によって、最低latencyが実証されるわけではありません。

**Pod affinityとanti-affinityのユースケース:**
1. **高可用性**: 同じアプリケーションのinstanceを別のnode、zone、regionに分散する
2. **性能の最適化**: 測定結果から競合とlatencyのトレードオフが妥当と確認できる場合に、通信するPodを近くに配置する
3. **リソース分離**: リソース負荷の高いPodを別々のnodeに分散する
4. **ライセンス制限**: ライセンス制約のあるアプリケーションを特定のnodeに集約する

**Pod affinityとanti-affinityによる性能への影響:**
Pod affinityとanti-affinityはすべてのnodeとPodを考慮するため、計算コストが高くなる場合があります。大規模クラスターではスケジューリング性能に影響することがあるため、慎重に使用してください。

**その他の選択肢の問題点:**
- A. Podとノード間のaffinityを処理する: これは`NodeAffinity`プラグインの役割です。
- C. Podとvolume間のaffinityを処理する: これは`VolumeBinding`プラグインの役割です。
- D. Podとservice間のaffinityを処理する: これはKubernetesのスケジューラープラグインではありません。
</details>

### 10. Kubernetesスケジューラーの`NodeName`プラグインの主な目的は何ですか？

A. Podの`spec.nodeName`フィールドがノード名と一致することを確認する
B. ノードに名前を割り当てる
C. Podにノード名を割り当てる
D. ノード名の形式を検証する

<details>
<summary>答えを表示</summary>

**答え: A. Podの`spec.nodeName`フィールドがノード名と一致することを確認する**

**解説:**
`NodeName`プラグインに空でない`nodeName`が渡されると、その述語は一致する名前だけを受け入れます。通常の動作では、あらかじめノードを割り当てたPodは未スケジュールqueueから除外済みです。プラグイン自体がスケジューラーを迂回させるわけではありません。

**`NodeName`プラグインの主な機能:**
1. **ノード名の照合**: Podの`spec.nodeName`が設定されている場合、一致する名前のノードだけを受け入れます。
2. **フィールドの意味**: `spec.nodeName`はノードを直接指定する値であり、スケジューラーによる選択フィールドではありません。
3. **スケジューラーの迂回**: `spec.nodeName`を設定したPodは通常のスケジューリング処理を迂回して指定ノードに割り当てられる。

**名前照合に相当する述語:**
このhelperは組み込みチェックの例です。`NodeName`という名前の置き換えプラグインを登録しないでください。

```go
package quizplugins

import v1 "k8s.io/api/core/v1"

// Equivalent name predicate for explanation; not a replacement scheduler.
func NodeNameMatches(pod *v1.Pod, node *v1.Node) bool {
	if pod == nil || node == nil {
		return false
	}
	return pod.Spec.NodeName == "" || pod.Spec.NodeName == node.Name
}
```

**`nodeName`を指定したPodの例:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  nodeName: worker-node-1  # Direct assignment to specific node
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**`nodeName`を使う際の注意事項:**
1. **スケジューラーの迂回**: `nodeName`を使うと、スケジューラーのfiltering、scoringなどの処理を迂回します。
2. **ノードの存在**: 間違ったノード名や存在しない名前を指定しても、別ノードは選択されません。
3. **Admissionは引き続き適用**: スケジューラーの適合性チェックは迂回しますが、リソース不足でkubeletのAdmissionに拒否されることがあります。
4. **残る制約**: NoSchedule taintやaffinityによるスケジューリングチェックは迂回しますが、NoExecuteとノード側のAdmissionは引き続き適用されます。スケジューラーのvolume調整を迂回すると、WaitForFirstConsumerのPVCがPendingのままになることがあります。

`kubernetes.io/hostname`ラベルとNode objectの名前が同じとは限りません。以下のラベル例を使う前に、実際の値を確認してください。

**`nodeName`、`nodeSelector`、`nodeAffinity`の比較:**
1. **`nodeName`**: 特定ノードへ直接割り当てます。最も制約が強く、柔軟性は最も低くなります。
2. **`nodeSelector`**: labelでノードを選びます。単純ですが、表現力は限られます。
3. **`nodeAffinity`**: 複雑なノード選択規則をサポートします。最も柔軟で表現力があります。

**`nodeName`のユースケース:**
1. **デバッグ**: 問題を調査するため、特定ノードでPodを動かす。
2. **テスト**: 特定ノードでテストを実行する。
3. **専用ハードウェア**: 特定のハードウェアを持つノードにPodを割り当てる。
4. **Static Podとの違い**: APIで作成した`nodeName`付きPodはStatic Podではありません。Static Podはkubeletローカルの設定から作成されます。

**`nodeName`を使う際の注意点:**
1. **置き換え時の動作**: Podは移動しません。controllerが置き換えPodを作成することはありますが、同じ失敗ノード名に固定したtemplateは、置き換え後も制約になります。
2. **スケーラビリティの制限**: ノード名を固定するとスケーラビリティが制限されます。
3. **メンテナンスの難しさ**: ノード名が変わるとPod定義の更新が必要です。
4. **負荷分散なし**: スケジューラーの負荷分散機能を利用できません。

**代替手段と推奨事項:**
1. **`nodeSelector`を使う:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: nginx
   spec:
     nodeSelector:
       kubernetes.io/hostname: worker-node-1
     containers:
     - name: nginx
       image: nginx:1.30.6
   ```

2. **`nodeAffinity`を使う:**
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: nginx
   spec:
     affinity:
       nodeAffinity:
         requiredDuringSchedulingIgnoredDuringExecution:
           nodeSelectorTerms:
           - matchExpressions:
             - key: kubernetes.io/hostname
               operator: In
               values:
               - worker-node-1
     containers:
     - name: nginx
       image: nginx:1.30.6
   ```

**その他の選択肢の問題点:**
- B. ノードに名前を割り当てる: ノード名はノード作成時に決まり、スケジューラープラグインの役割ではありません。
- C. Podにノード名を割り当てる: これは`NodeName`プラグインではなく、スケジューラーのbind stageで行います。
- D. ノード名の形式を検証する: これはスケジューラープラグインではなく、API serverの検証処理で行います。
</details>

### 11. scale-down時の優先設定としてPod Deletion Costを使うcontrollerはどれですか？

A. StatefulSetによるordinal順の削除
B. Deploymentが所有するものを含むReplicaSet
C. 単独Podの削除全般
D. Deploymentをまたいで全Podを順位付けするグローバルスケジューラー

<details>
<summary>答えを表示</summary>

**答え: B. Deploymentが所有するものを含むReplicaSet**

注釈の値は1つのReplicaSet内で比較され、ベストエフォートです。未設定の場合は0で、負数を含む符号付きint32値を指定できます。割り当て状態、phase、readinessが優先される場合があるため、costの高い未ready Podが、costの低いready Podより先に削除されることもあります。この機能は1.21でalpha、1.22からbetaかつデフォルト有効です。
</details>

### 12. 削除コストを更新する方法として、元の章の内容に合うものはどれですか？

A. 高いcostとPDBによって、通常のscale-down時にreplicaの生存を保証する
B. リクエストを受けるたびにPod全体を置き換える
C. 大まかな状態遷移時だけcostをpatchし、Pod UIDを確認して古いメトリクスを拒否する
D. メトリクスを取得できない場合は活動量を0として、直ちにcostを下げる

<details>
<summary>答えを表示</summary>

**答え: C. 大まかな状態遷移時だけcostをpatchし、Pod UIDを確認して古いメトリクスを拒否する**

書き込み担当を1つに限定し、リクエスト数に上限を設け、注釈だけを最小限patchします。UIDを確認すれば、同じ名前の新しいPodに誤ってpatchすることを防げます。scaleのserver dry-runでは、どのPodが削除されるか予測できません。通常のReplicaSet scale-downはPodを直接削除し、PDBによって阻止されません。アプリケーションのdrain、readiness、復旧にも引き続き対処が必要です。
</details>

## 参考資料

コードは[パート1のmodule](../../scheduling/01-custom-scheduler-part1.md)を使います。ローカルでのコード/設定テストは、承認システム、Gang workload、GPU実行、または本番運用可能性を実証するものではありません。

* [スケジューリングフレームワーク](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)
* [固定バージョンのframework interface](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [スケジューラー設定](https://kubernetes.io/docs/reference/scheduling/config/)
* [ネイティブPodGroup scheduling](https://kubernetes.io/docs/concepts/scheduling-eviction/podgroup-scheduling/)
* [PodGroup policy](https://kubernetes.io/docs/concepts/workloads/workload-api/policies/)
* [Volcano Job](https://volcano.sh/en/docs/vcjob/)
* [Volcano 1.15.2 Job CRD](https://github.com/volcano-sh/volcano/blob/v1.15.2/config/crd/volcano/bases/batch.volcano.sh_jobs.yaml)
* [BalancedAllocation scorer](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/scheduler/framework/plugins/noderesources/balanced_allocation.go)
* [ノードへの割り当て](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [ReplicaSetのPod削除コスト](https://kubernetes.io/docs/concepts/workloads/controllers/replicaset/#pod-deletion-cost)
