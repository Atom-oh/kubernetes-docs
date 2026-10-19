# カスタムスケジューラークイズ（パート2）

> **例の基準**: Kubernetes 1.35.8、Go 1.27.2
> **最終更新**: 2026年10月16日

このクイズでは、Kubernetes のカスタムスケジューラーの実装と利用に関する応用知識を確認します。

## クイズ問題

### 1. Kubernetes scheduling framework の「Bind」拡張ポイントの役割は何ですか？

A. スケジューリングの決定を確定するため、Pod を Node に割り当てる
B. Pod と Node 間のネットワーク接続を設定する
C. Pod と Service 間の関連付けを作成する
D. Pod とボリューム間の関連付けを設定する

<details>
<summary>回答を表示</summary>

**回答: A. スケジューリングの決定を確定するため、Pod を Node に割り当てる**

**解説:**
Bind 拡張ポイントは、選択した Node への Pod の割り当てを記録し、スケジューリングの決定を確定します。Bind 段階では binding cycle 中に割り当てがコミットされます。その後に PostBind が実行されますが、kubelet でイメージ、ストレージ、ランタイムの障害が発生する可能性は残ります。

**Bind の処理:**
1. スケジューラーはフィルタリングとスコアリングで最適な Node を選びます。
2. 選んだ Node 上に Pod を予約します（reserve）。
3. Bind 段階で Pod の `spec.nodeName` を選択した Node 名に更新します。
4. 更新した Pod 情報を API server に保存します。
5. kubelet が Pod 情報を検知し、その Node 上で Pod を実行します。

**Bind リクエストの例:**
Bind は Node 選択、仮割り当て/予約、Permit、PreBind の後、binding cycle 内で行われます。記録するのは割り当てであり、コンテナの起動成功ではありません。対象バージョンの API キャッシュ経路とバインドエラーも処理する upstream の `DefaultBinder` を維持します。次の完全なヘルパーは、リクエストの識別情報を送信せずに示します。

```go
package bindingexample

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// This only constructs a request; it neither selects a node nor calls the API.
// Use DefaultBinder within the complete scheduler pipeline for actual binding.
func BindingFor(pod *v1.Pod, nodeName string) (*v1.Binding, error) {
	if pod == nil || pod.Name == "" || pod.Namespace == "" || pod.UID == "" || nodeName == "" {
		return nil, fmt.Errorf("admitted Pod name, namespace, UID and selected node are required")
	}
	return &v1.Binding{
		ObjectMeta: metav1.ObjectMeta{Name: pod.Name, Namespace: pod.Namespace, UID: pod.UID},
		Target:     v1.ObjectReference{Kind: "Node", Name: nodeName},
	}, nil
}
```

Pod UID によって、削除済み Pod と同じ名前で作成された新しい Pod を取り違えずに済みます。Bind リクエスト自体はリソース、アフィニティ、taint を検査しません。これらはスケジューラーパイプラインの前段で確認します。

**Default Binder の設定:**
次の設定は `DefaultBinder` を含むすべての既定値を維持し、未登録のカスタム binder を有効にするものではありません。

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

**Bind 関連イベントの確認:**
```bash
# Check pod scheduling events
kubectl get events | grep -i "Successfully assigned"
```

**Bind 失敗のトラブルシューティング:**
Bind 段階でよくある失敗原因:
1. API server への接続障害
2. 権限不足
3. Node 名の誤り
4. 競合状態（別のスケジューラーが同じ Pod を同時に Bind しようとする）

**他の選択肢について:**
- B. Pod と Node 間のネットワーク接続を設定する: ネットワーク設定は CNI プラグインの役割であり、スケジューラーの Bind 段階とは関係ありません。
- C. Pod と Service 間の関連付けを作成する: Service と Pod はラベルセレクターで結び付けられ、スケジューラーの Bind 段階とは関係ありません。
- D. Pod とボリューム間の関連付けを設定する: PV/PVC のバインドや CSI のプロビジョニングはストレージコントローラーとスケジューラーの VolumeBinding プラグインが担当し、遅延バインドも扱います。Pod と Node の Bind とは別の操作です。
</details>

### 2. Kubernetes の Node Affinity に関係する演算子ではないものはどれですか？

A. In
B. NotIn
C. Exists
D. Contains

<details>
<summary>回答を表示</summary>

**回答: D. Contains**

**解説:**
Kubernetes の Node Affinity に `Contains` 演算子はありません。Kubernetes は `Contains` 演算子を提供していません。

**Node Affinity でサポートされる演算子:**
1. **In**: ラベル値が指定値のいずれかと一致する必要があります。
2. **NotIn**: ラベル値が指定値と一致してはいけません。
3. **Exists**: 指定したラベルキーが存在する必要があります。
4. **DoesNotExist**: 指定したラベルキーが存在してはいけません。
5. **Gt**: ラベル値が指定値より大きい必要があります（Greater than）。
6. **Lt**: ラベル値が指定値より小さい必要があります（Less than）。

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
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 1
        preference:
          matchExpressions:
          - key: another-node-label-key
            operator: Exists
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**Node Affinity の種類:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: Pod を Node にスケジュールするために必ず満たすハード要件です。
2. **preferredDuringSchedulingIgnoredDuringExecution**: 満たすことが望ましいものの、必須ではないソフト要件です。

**演算子の使用例:**
1. **In 演算子:**
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: In
     values:
     - us-east-1a
     - us-east-1b
   ```
   Node の `topology.kubernetes.io/zone` ラベル値は `us-east-1a` または `us-east-1b` である必要があります。

2. **NotIn 演算子:**
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: NotIn
     values:
     - us-east-1c
   ```
   Node の `topology.kubernetes.io/zone` ラベル値は `us-east-1c` であってはいけません。

3. **Exists 演算子:**
   ```yaml
   - key: topology.kubernetes.io/zone
     operator: Exists
   ```
   Node に `topology.kubernetes.io/zone` ラベルが存在する必要があります。

4. **DoesNotExist 演算子:**
   ```yaml
   - key: emptyLabel
     operator: DoesNotExist
   ```
   Node に `emptyLabel` ラベルが存在してはいけません。

5. **Gt/Lt 演算子:**
   ```yaml
   - key: node-size
     operator: Gt
     values:
     - "10"
   ```
   Node の `node-size` ラベル値は 10 より大きい必要があります。

**必須の Node Affinity の確認:**
既定の `NodeAffinity` プラグインを維持します。読み取り専用ヘルパーには、常に true を返す `matchNodeSelectorTerm` のスタブではなく、バージョンに対応したコンポーネントヘルパーを使います。

```go
package affinityexample

import (
	"fmt"

	v1 "k8s.io/api/core/v1"
	nodeaffinity "k8s.io/component-helpers/scheduling/corev1/nodeaffinity"
)

// A read-only check of Pod nodeSelector and required node affinity.
// The scheduler's NodeAffinity plugin also handles profile-level addedAffinity.
func MatchesRequired(pod *v1.Pod, node *v1.Node) (bool, error) {
	if pod == nil || node == nil {
		return false, fmt.Errorf("pod and node are required")
	}
	return nodeaffinity.GetRequiredNodeAffinity(pod).Match(node)
}
```

`nodeSelector` と必須 Node Affinity の両方が一致する必要があります。セレクターの各 term は OR、1つの term 内の各 expression は AND です。空の term はどの Node にも一致しません。キーが存在しない場合も `NotIn` は一致するため、キーの存在が必要なら `Exists` を追加します。`Gt`/`Lt` は比較値を整数1つだけ受け取り、Node ラベル値も整数である必要があります。`IgnoredDuringExecution` では、後からラベルが変わっても、それだけを理由に割り当て済み Pod は退避されません。プロファイルレベルの `addedAffinity` は引き続きスケジューラープラグインが処理します。

**他の選択肢について:**
- A. In: Node Affinity で有効な演算子です。
- B. NotIn: Node Affinity で有効な演算子です。
- C. Exists: Node Affinity で有効な演算子です。
</details>

### 3. Kubernetes の Pod Topology Spread Constraints の主な目的は何ですか？

A. Pod を複数の Node に均等に分散する
B. Pod を特定の Node だけに配置する
C. Pod を特定の zone だけに配置する
D. Pod を特定のラベルを持つ Node だけに配置する

<details>
<summary>回答を表示</summary>

**回答: A. Pod を複数の Node に均等に分散する**

**解説:**
Topology spread は、新たに配置する各 Pod を対象ドメイン間に分散します。耐障害性の向上に役立ちますが、既存 Pod を再配置したり、レイテンシー、容量、可用性を保証したりはしません。

**主なフィールド:**
1. **maxSkew**: `DoNotSchedule` では、配置候補ドメインの Pod 数が、対象ドメインのグローバル最小値からどれだけ離れてよいかを制限します。
2. **topologyKey**: Node ラベルでドメインを定義します。
3. **whenUnsatisfiable**: `DoNotSchedule` はハード制約です。`ScheduleAnyway` はスコアリング上の優先事項であり、他のハードフィルターを無効にしません。
4. **labelSelector**: 新しい Pod と同じ namespace 内で、集計対象の Pod を選択します。新しい Pod 自身も意図したセレクターに一致することを確認します。
5. **minDomains / nodeAffinityPolicy / nodeTaintsPolicy**: 対象ドメインの集計方法に影響します。不足している Node や AZ 容量を作り出すものではありません。

**Pod Topology Spread Constraints の例:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
  labels:
    app: web
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web
  - maxSkew: 2
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: web
  containers:
  - name: nginx
    image: nginx:1.30.6
```

この例では、候補配置が2つの制約を両方満たす必要があります。`DoNotSchedule` の場合は次のように計算します。
1. 空のドメインを含め、対象となるすべてのドメインで一致する Pod 数を数えます。
2. 対象ドメインのグローバル最小値を求めます。`minDomains` よりドメイン数が少ない場合、値は0です。
3. 新しい Pod がセレクターに一致するなら、配置候補ドメインの数に加えて、その候補の数と最小値を比較します。

Pod 数が **2,2,1** で `maxSkew: 1` の場合、3番目のドメインには新しい一致 Pod を配置できます（2−1=1）が、最初の2つには配置できません（3−1=2）。これは候補配置を判定する仕組みであり、既存の全ドメインの組み合わせが常に均等であると約束するものではありません。

**一般的な topology key:**
1. **kubernetes.io/hostname**: Node 単位の分散
2. **topology.kubernetes.io/zone**: zone 単位の分散
3. **topology.kubernetes.io/region**: region 単位の分散
4. **node.kubernetes.io/instance-type**: インスタンスタイプ単位の分散

**ユースケース:**
1. **高可用性**: 複数の Node、zone、region に Pod を分散し、障害耐性を高めます。
2. **リソースの均衡**: クラスター全体にワークロードを分散します。
3. **コスト最適化**: 特定のタイプの Node にワークロードを配置します。
4. **Topology ポリシー**: 障害耐性と、ドメイン間通信や実測レイテンシーとのバランスを取ります。

**カスタムスケジューラーでの処理:**
`PodTopologySpread` とその PreFilter/Filter/Score 段階を維持します。正しく扱うには、スケジューラーのスナップショット、namespace/セレクターの一致、対象および空のドメイン、新しい Pod、`minDomains`、Node Affinity/taint ポリシー、再キューイベントを考慮する必要があります。skew の計算を省き、Running Pod を走査するだけの実装では不十分です。

この EKS ラボでは、1つの AWS Region にある EC2 Node を使います。`topology.kubernetes.io/region` ラベルを設定しても、マルチリージョンクラスターにはなりません。AZ 間に Pod を分散すると AZ 間通信量が増える場合があり、ネットワークレイテンシーが自動的に最小になるわけではありません。

**他の選択肢について:**
- B. Pod を特定の Node だけに配置する: nodeSelector または Node Affinity の役割です。
- C. Pod を特定の zone だけに配置する: Node Affinity で zone を指定します。Topology spread の主な目的は均等な分散です。
- D. Pod を特定のラベルを持つ Node だけに配置する: nodeSelector または Node Affinity の役割です。
</details>

### 4. Kubernetes の Taints and Tolerations の主な役割は何ですか？

A. 特定の Pod を特定の Node のみにスケジュールする
B. 特定の Pod が特定の Node にスケジュールされないようにする
C. Node が一部の Pod を拒否し、Pod はそれを許容できるようにする
D. Pod 間の通信を制限する

<details>
<summary>回答を表示</summary>

**回答: C. Node が一部の Pod を拒否し、Pod はそれを許容できるようにする**

**解説:**
Taint は Pod を遠ざけ、toleration は一致する taint を無視できるようにします。Toleration を設定しても、その Node への配置が強制されたり、リソースやアフィニティのフィルターが迂回されたりはしません。

**Effect の種類:**
1. **NoSchedule**: 対応する toleration がない Pod の新規スケジューリングを防ぎますが、すでに動作中の Pod は退避しません。
2. **PreferNoSchedule**: ソフトな優先設定です。他のスコアが上回れば、他に容量がある場合でも、その Node に配置される可能性があります。
3. **NoExecute**: 対応する toleration がない新規 Pod のスケジューリングを防ぎます。既存 Pod は toleration がない場合、または設定した toleration 時間が過ぎた場合に退避処理の対象になります。API 上の削除だけでは、到達不能な Node 上のプロセスが停止した証拠にはなりません。

**Taint の設定例:**
```bash
# Apply taint to node
kubectl taint nodes node1 key=value:NoSchedule

# Remove taint from node
kubectl taint nodes node1 key=value:NoSchedule-
```

**Taint と Toleration の例:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pod-with-toleration
spec:
  tolerations:
  - key: key
    operator: Equal
    value: value
    effect: NoSchedule
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**Toleration のフィールド:**
- `Equal`（既定の演算子）はキーと値を比較します。`Exists` では値を省略します。
- effect を指定した場合は一致する必要があります。空の effect はそのキーの全 effect に一致します。空のキーは `Exists` が必要で全キーに一致するため、意図して使います。
- `tolerationSeconds` は `NoExecute` にのみ適用されます。省略すると一致する taint を無期限に許容し、指定すると許容時間を制限します。
- この例では既定の `Equal`/`Exists` の動作を使います。Kubernetes 1.35 で任意の比較演算子を使う機能は alpha で、ここでは無効です。

```yaml
tolerations:
- key: "node.kubernetes.io/not-ready"
  operator: "Exists"
  effect: "NoExecute"
  tolerationSeconds: 300
```

**一般的なユースケース:**
1. **専用 Node**: taint、制御された toleration、必須アフィニティを組み合わせます。taint だけでは対象ワークロードが専用 Node に配置されるとは限りません。
2. **専用ハードウェア**: GPU などの特別なハードウェアを持つ Node に特定の Pod を配置します。
3. **Node メンテナンス**: メンテナンス中の新規 Pod 配置を防ぎます。
4. **Control plane の保護**: 一般ワークロードが control plane Node に配置されないようにします。

**システム taint:**
Kubernetes は次のシステム taint を自動的に設定します。
1. **node.kubernetes.io/not-ready**: Node が Ready ではない
2. **node.kubernetes.io/unreachable**: Node に到達できない
3. **node.kubernetes.io/memory-pressure**: Node がメモリー不足
4. **node.kubernetes.io/disk-pressure**: Node がディスク不足
5. **node.kubernetes.io/pid-pressure**: Node が PID 不足
6. **node.kubernetes.io/network-unavailable**: Node のネットワークが利用できない
7. **node.kubernetes.io/unschedulable**: Node がスケジュール不可に設定されている

**ハード taint の確認:**
次の完全なヘルパーは、effect とワイルドカードを含む、基準バージョンの一致規則を使います。`PreferNoSchedule` はハードチェックから除外し、`NoExecute` は含めます。これはスケジューラーの他のフィルターや taint eviction controller の代わりにはなりません。

```go
package taintexample

import (
    v1 "k8s.io/api/core/v1"
    corehelpers "k8s.io/component-helpers/scheduling/corev1"
    "k8s.io/klog/v2"
)

// Checks hard scheduling taints only; it does not implement eviction timers.
func ToleratesHardTaints(pod *v1.Pod, node *v1.Node) bool {
	if pod == nil || node == nil {
		return false
	}
	_, untolerated := corehelpers.FindMatchingUntoleratedTaint(
		klog.Background(), node.Spec.Taints, pod.Spec.Tolerations,
		func(taint *v1.Taint) bool {
			return taint.Effect == v1.TaintEffectNoSchedule || taint.Effect == v1.TaintEffectNoExecute
		}, false, // Equal/Exists behavior; comparison-operator feature is not enabled here.
	)
	return !untolerated
}
```

**他の選択肢について:**
- A. 特定の Pod を特定の Node のみにスケジュールする: nodeSelector または Node Affinity の役割です。
- B. 特定の Pod が特定の Node にスケジュールされないようにする: これは taint と toleration のうち、Pod を遠ざける側だけを説明しています。podAntiAffinity は他の Pod との位置関係を扱います。
- D. Pod 間の通信を制限する: NetworkPolicy の役割です。
</details>

### 5. Kubernetes の Scheduler Extender の主な特徴ではないものはどれですか？

A. HTTP webhook を通じてスケジューラーと通信する
B. フィルタリングと優先順位付けを提供する
C. スケジューラーのコードベースに直接統合される
D. 外部プロセスとして実行される

<details>
<summary>回答を表示</summary>

**回答: C. スケジューラーのコードベースに直接統合される**

**解説:**
Scheduler Extender はスケジューラーのコードベースに直接統合されません。HTTP webhook を通じて通信する外部プロセスです。これが Scheduling Framework プラグインとの主な違いです。

**Scheduler Extender の主な特徴:**
1. **HTTP webhook**: スケジューラーは HTTP リクエストで extender と通信します。
2. **外部プロセス**: extender はスケジューラーとは別のプロセスとして実行されます。
3. **フィルタリングと優先順位付け**: Node のフィルタリングや優先順位付けを提供できます。
4. **Bind**: オプションで Pod を Node にバインドできます。

**Extender の設定:**
Part2 の TLS サービスと証明書の前提条件を、セカンダリスケジューラーとともに使います。`extenders` はトップレベルの設定です。必須フィルターでは `ignorable: false` を維持します。可用性を強制したいリソースに対して、障害を許容する extender と `ignoredByScheduler: true` を組み合わせないでください。この例では GPU の計上を組み込みのリソースフィルターに任せています。

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

**Wire Protocol (Kubernetes 1.35.8):**
Go の型は大文字始まりのフィールド名でシリアライズされます。`nodeCacheCapable: false` の場合は `Pod` と完全な `Nodes` を送り、`NodeNames` は null です。true にするには、別途管理する Node キャッシュと `NodeNames` の契約が必要です。以下は有効な JSON 例であり、山括弧で囲んだプレースホルダーではありません。

1. **Filter / Prioritize リクエスト:**
```json
{
  "Pod": {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
      "name": "gpu-pod",
      "namespace": "default",
      "uid": "00000000-0000-0000-0000-000000000001",
      "annotations": {
        "training.example.com/min-gpu-memory-mib": "16384"
      }
    },
    "spec": {
      "schedulerName": "custom-scheduler",
      "containers": [
        {
          "name": "worker",
          "image": "busybox:1.38.0",
          "resources": {
            "requests": {
              "nvidia.com/gpu": "1"
            },
            "limits": {
              "nvidia.com/gpu": "1"
            }
          }
        }
      ]
    }
  },
  "Nodes": {
    "items": [
      {
        "metadata": {
          "name": "gpu-node",
          "labels": {
            "training.example.com/gpu-memory-mib": "16384"
          }
        },
        "status": {
          "allocatable": {
            "nvidia.com/gpu": "1"
          }
        }
      }
    ]
  },
  "NodeNames": null
}
```

2. **Filter レスポンス:** 提示された候補 Node のみを返せます。`FailedAndUnresolvableNodes` は preemption で解決できない失敗を示します。

```json
{
  "Nodes": {
    "items": [
      {
        "metadata": {
          "name": "gpu-node",
          "labels": {
            "training.example.com/gpu-memory-mib": "16384"
          }
        },
        "status": {
          "allocatable": {
            "nvidia.com/gpu": "1"
          }
        }
      }
    ]
  },
  "NodeNames": null,
  "FailedNodes": {},
  "FailedAndUnresolvableNodes": {},
  "Error": ""
}
```

3. **Prioritize レスポンス:** `Host`/`Score` の配列だけを返し、スコア範囲は **0～10** です。Framework のスコアは 0～100 です。優先順位付けでエラーが起きると、この extender のスコアは省略されるため、必須ルールは Filter に置きます。

```json
[
  {
    "Host": "gpu-node",
    "Score": 2
  }
]
```

4. **任意の Bind リクエストとレスポンス:** リクエストは Pod の名前、namespace、UID、および選択した Node を識別します。Part2 はこの callback を実装せず、`bindVerb` も設定しません。

```json
{
  "PodName": "gpu-pod",
  "PodNamespace": "default",
  "PodUID": "00000000-0000-0000-0000-000000000001",
  "Node": "gpu-node"
}
```

```json
{
  "Error": ""
}
```

5. **任意の preemption callback:** `preemptVerb` は `ExtenderPreemptionArgs`/`ExtenderPreemptionResult` を使って Pod と候補 victim を交換します。PreFilter や PreScore の callback ではありません。

**実装:**
完全な入力サイズ制限付き handler と TLS コマンドは[Part2](../../scheduling/02-custom-scheduler-part2.md)を参照してください。Pod/Node の欠落、不正なメモリー要件、過大な入力、不正なキャッシュ契約を拒否します。実行可能なコードとして、未実装の `customFilter` や `customScore` 関数を扱わないでください。

**Scheduler Extender と Scheduling Framework Plugin の比較:**

| 特徴 | Scheduler Extender | Scheduling Framework Plugin |
|---------|-------------------|---------------------------|
| 統合方法 | HTTP webhook | コードベースへ直接統合 |
| 実行方式 | 外部プロセス | スケジューラー内 |
| 性能 | HTTP のオーバーヘッドにより比較的低速 | 直接統合のため高速 |
| 開発言語 | 制限なし | Go |
| デプロイ | 独立したサービス | スケジューラーとともにデプロイ |
| 保守 | スケジューラーから独立 | スケジューラーのバージョンと連動 |

**Scheduler Extender の長所と短所:**
長所:
- スケジューラーのコードベースから独立して開発できる
- さまざまなプログラミング言語で実装できる
- スケジューラーのアップグレードの影響を受けにくい

短所:
- HTTP 通信のオーバーヘッドによる性能低下
- スケジューリングサイクルの一部の段階しか拡張できない
- スケジューラーと extender の間で通信障害が発生する可能性がある

**他の選択肢について:**
- A. HTTP webhook を通じてスケジューラーと通信する: Scheduler Extender の特徴です。
- B. フィルタリングと優先順位付けを提供する: Scheduler Extender の特徴です。
- D. 外部プロセスとして実行される: Scheduler Extender の特徴です。
</details>

### 6. Kubernetes の Pod Affinity と Anti-Affinity の主な目的は何ですか？

A. Pod と Node の関係を定義する
B. Pod とボリュームの関係を定義する
C. Pod 間の関係を定義する
D. Pod と Service の関係を定義する

<details>
<summary>回答を表示</summary>

**回答: C. Pod 間の関係を定義する**

**解説:**
Pod Affinity と Anti-Affinity は、Pod 同士の配置関係を定義します。Affinity は特定の Pod と同じ topology domain（Node、zone、region など）に配置し、Anti-Affinity は同じ domain を避けるために使います。

**主な要素:**
1. **topologyKey**: Pod 間の関係を定める topology domain を指定する Node ラベルキーです。
2. **labelSelector**: 関係の対象となる Pod を選ぶラベルセレクターです。
3. **namespaces**: ラベルセレクターを適用する namespace の一覧です。

**Pod Affinity の種類:**
1. **requiredDuringSchedulingIgnoredDuringExecution**: スケジューリング時に満たさなければならないハード要件です。
2. **preferredDuringSchedulingIgnoredDuringExecution**: 満たすことが望ましいソフト要件です。

**Pod Affinity の例:**
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

この例では:
1. **Pod Affinity**: web server Pod は `app=cache` ラベルを持つ Pod と同じ Node（`kubernetes.io/hostname`）に配置される必要があります。
2. **Pod Anti-Affinity**: web server Pod は、できれば `app=web` ラベルを持つ他の Pod と異なる Node に配置します。

**一般的な topology key:**
1. **kubernetes.io/hostname**: Node 単位の関係
2. **topology.kubernetes.io/zone**: zone 単位の関係
3. **topology.kubernetes.io/region**: region 単位の関係

**ユースケース:**
1. **高可用性**: 同じアプリケーションのインスタンスを異なる Node、zone、region に分散します。
2. **近接配置の優先**: 同じ場所への配置で一部のネットワーク費用が下がる場合があります。依存する前に競合とレイテンシーを測定します。
3. **リソース分離**: リソースを大量に使う Pod を異なる Node に分散します。
4. **ライセンス制約**: ライセンス制限のあるアプリケーションを特定 Node に集中させます。

**Pod Affinity と Node Affinity の違い:**
- **Node Affinity**: Pod と Node の関係を定義します。
- **Pod Affinity**: Pod 同士の関係を定義します。

**性能への影響:**
Pod Affinity と Anti-Affinity はすべての Node と Pod を考慮するため、計算コストが高くなる場合があります。大規模クラスターではスケジューリング性能に影響し得るため、慎重に使います。

**カスタムスケジューラーでの処理:**
`InterPodAffinity` と、その前処理およびスコアリングを維持します。正しい処理には、新しい Pod の必須 term、既存 Pod の必須 Anti-Affinity、namespace の選択、topology label、自己アフィニティの初期化動作を考慮する必要があります。常に true を返すスタブでは不正な配置を許したり、Anti-Affinity 用に反転してすべての Node を拒否したりする可能性があります。

`namespaces` と `namespaceSelector` の両方を指定した場合、対象 namespace は和集合になります。どちらも省略した場合は、新しい Pod の namespace が使われます。`namespaceSelector: {}` は全 namespace を選択します。この例では、必須の `app=cache` Pod が選択した namespace 内の適格な Node にすでに存在する必要があります。優先 Anti-Affinity は分離を保証しません。`IgnoredDuringExecution` では、ラベルや peer が変化しても Pod を継続的に移動しません。

**他の選択肢について:**
- A. Pod と Node の関係を定義する: Node Affinity の役割です。
- B. Pod とボリュームの関係を定義する: Volume Binding と PersistentVolumeClaim の役割です。
- D. Pod と Service の関係を定義する: Service のラベルセレクターで処理します。
</details>

### 7. Kubernetes scheduler の「QueueSort」拡張ポイントの役割は何ですか？

A. Node をスコアリングする
B. Pod を実行できない Node を除外する
C. スケジューリングキュー内の Pod を並べ替える
D. Pod を Node にバインドする

<details>
<summary>回答を表示</summary>

**回答: C. スケジューリングキュー内の Pod を並べ替える**

**解説:**
QueueSort 拡張ポイントは、スケジューリングキュー内の Pod の順序を決めます。この順序によって、どの Pod を先に処理するかが決まります。

**スケジューリングキューと QueueSort:**
スケジューラーはキュー内の Pod を1つずつ処理します。QueueSort プラグインがその順序を決めます。既定では `PrioritySort` が Pod の優先度で並べ替えます。

**バージョン付きインターフェイス:**
Kubernetes 1.35.8 で QueueSort は `Less(fwk.QueuedPodInfo, fwk.QueuedPodInfo) bool` を実装します。これらのインターフェイスには getter 経由でアクセスします。既定の `PrioritySort` は、許可された priority、次にキュー時刻を比較します。

**完全なカスタム例（`quizplugins/queue.go`）:**
この実装はラボ独自の優先順位を適用する前に、許可済み priority を維持します。namespace や label に基づく優先設定は、同じ優先度の Pod 間で不公平を生む可能性があります。信頼できない label を、Admission 制御された PriorityClass の代わりに使わないでください。

```go
package quizplugins

import (
	"context"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	corehelpers "k8s.io/component-helpers/scheduling/corev1"
	fwk "k8s.io/kube-scheduler/framework"
)

type CustomQueueSort struct{}

var _ fwk.QueueSortPlugin = &CustomQueueSort{}

func (*CustomQueueSort) Name() string { return "CustomQueueSort" }

func (*CustomQueueSort) Less(a, b fwk.QueuedPodInfo) bool {
	pa, pb := a.GetPodInfo().GetPod(), b.GetPodInfo().GetPod()
	ap, bp := corehelpers.PodPriority(pa), corehelpers.PodPriority(pb)
	if ap != bp {
		return ap > bp
	}
	// Lab tie-breakers only; do not override the admitted Pod priority.
	aPreferred := pa.Namespace == "high-priority-namespace"
	bPreferred := pb.Namespace == "high-priority-namespace"
	if aPreferred != bPreferred {
		return aPreferred
	}
	if critical(pa) != critical(pb) {
		return critical(pa)
	}
	return a.GetTimestamp().Before(b.GetTimestamp())
}

func critical(pod *v1.Pod) bool { return pod.Labels["training.example.com/critical"] == "true" }

func NewQueue(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &CustomQueueSort{}, nil
}
```

後述の PoolConstraint 例とともに `cmd/quiz-scheduler/main.go` に登録します。

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
		app.WithPlugin("CustomQueueSort", quizplugins.NewQueue),
		app.WithPlugin("PoolConstraint", quizplugins.NewPool),
	)
	os.Exit(cli.Run(command))
}
```

Part1 の module から `CGO_ENABLED=0 go build -buildvcs=false -o custom-scheduler ./cmd/quiz-scheduler` でビルドします。選んだ構成で必要なプラグインだけを有効にします。

**Scheduler 設定での QueueSort プラグインの有効化:**
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
    queueSort:
      enabled:
      - name: CustomQueueSort
      disabled:
      - name: PrioritySort  # Disable default plugin
```

**QueueSort プラグインの特徴:**
1. **有効化は1つだけ**: 一度に有効にできる QueueSort プラグインは1つです。
2. **キューの共有**: 1つの scheduler process 内のすべての profile で QueueSort プラグインと設定を共有する必要があります。別の scheduler process は別のキューを持ちます。
3. **性能上の重要性**: 効率的なソートアルゴリズムが重要です。複雑なロジックはスケジューリング性能に影響します。

**QueueSort プラグインのユースケース:**
1. **業務上の優先度**: 業務上の重要性に応じて Pod を並べ替えます。
2. **リソース効率**: 空きリソースを使うため、リソース request が小さい Pod を先に処理します。
3. **Service Level Agreement (SLA)**: SLA 要件に従って Pod を並べ替えます。
4. **バッチ処理**: バッチジョブと対話型ジョブの優先度を調整します。

**スケジューリングキューの監視:**
```bash
# Check queue information in scheduler logs
kubectl logs -n scheduler-lab -l app=custom-scheduler --prefix --tail=100

# Check pods pending scheduling
kubectl get pods -A --field-selector=spec.schedulerName=custom-scheduler,spec.nodeName= -o wide
```

**他の選択肢について:**
- A. Node をスコアリングする: 「Score」拡張ポイントの役割です。
- B. Pod を実行できない Node を除外する: 「Filter」拡張ポイントの役割です。
- D. Pod を Node にバインドする: 「Bind」拡張ポイントの役割です。
</details>

### 8. Kubernetes の Pod Priority Preemption の主な目的は何ですか？

A. 優先度の低い Pod を削除して、優先度の高い Pod をスケジュールできるようにする
B. 優先度の高い Pod により多くのリソースを割り当てる
C. 優先度の高い Pod をより速く実行する
D. 優先度の高い Pod を特定の Node だけに配置する

<details>
<summary>回答を表示</summary>

**回答: A. 優先度の低い Pod を削除して、優先度の高い Pod をスケジュールできるようにする**

**解説:**
優先度の高い Pod を配置できず、その Pod のポリシーと残る制約が許せば、スケジューラーは優先度の低い Pod を preempt することがあります。

**Pod Priority と Preemption の仕組み:**
1. **PriorityClass の定義**: Pod の優先度を定義するクラスター全体のリソースです。
2. **Pod への優先度の指定**: Pod は `spec.priorityClassName` で PriorityClass を参照します。
3. **処理順序**: 優先度の高い Pod がスケジューリングキューで先に処理されます。
4. **Preemption の処理**: 高優先度 Pod のポリシーが許し、他の制約も満たせる場合、スケジューラーは低優先度 Pod を退避することがあります。

**PriorityClass の例:**
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

**Pod への優先度の適用:**
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

**Preemption ポリシー:**
PriorityClass の `preemptionPolicy` フィールドは次の値を取ります。
1. **PreemptLowerPriority（既定）**: 優先度の低い Pod を preempt できます。
2. **Never**: 優先度の低い Pod を preempt しません。

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority-no-preemption
value: 1000000
globalDefault: false
description: "High priority pods that do not preempt other pods"
preemptionPolicy: Never  # Do not preempt
```

**Preemption の流れ:**
1. スケジューラーが高優先度 Pod の配置を試みます。
2. 適切な Node がなければ、各 Node 上で preemption 候補 Pod を特定します。
3. 候補 victim は低優先度 Pod から選びます。
4. スケジューラーはポリシーに従って候補または victim の集合を選びます。全体で victim 数が最小になる保証はありません。
5. 選択された Pod を猶予期間付きで終了します。
6. victim の終了後に再度スケジューリングを試みます。nominated になっても Bind が保証されるわけではありません。

**Preemption に関する考慮点:**
1. **猶予付き終了期間**: preempt された Pod には `terminationGracePeriodSeconds`（既定値: 30秒）の猶予があります。
2. **Pod Disruption Budget (PDB)**: PDB 違反を避けようとしますが、準拠はベストエフォートであり保証されません。
3. **Nomination**: `status.nominatedNodeName` は候補 Node を記録します。Preemption は Node taint の追加で予約する仕組みではありません。
4. **System Pod**: Critical PriorityClass には高い予約済み優先度がありますが、さらに高優先度の Pod や別の退避機構から常に保護されるわけではありません。

**Preemption イベントの確認:**
```bash
# Check preemption events
kubectl get events | grep -i preempt
```

**Preemption 関連メトリクスの監視:**
設定済みの監視システムから、カスタムスケジューラーの認証済み HTTPS メトリクス endpoint 上の `scheduler_preemption_attempts_total` を読み取ります。`kubectl get --raw /metrics` が読むのは API server のメトリクスであり、この endpoint のものではありません。

```bash
kubectl get pods -A -o custom-columns=NAME:.metadata.name,PRIORITY:.spec.priority,NOMINATED:.status.nominatedNodeName
```

**安全な Preemption 処理:**
PostFilter で `DefaultPreemption` を維持します。これは低優先度 Pod の削除をシミュレーションして、関連する制約を再実行します。最初に見つけた Node 上の低優先度 Pod をすべて削除するのは安全ではありません。候補の選択では PDB 違反と victim の優先度を考慮しますが、全体で victim 数を最小化する保証はありません。

Preemption では、存在しない label、互換性のない volume topology、不足しているハードウェアは解決できません。Nomination 後も Pod が Pending のままの場合があり、別の高優先度 Pod によって結果が変わる場合があります。置換、終了、API 更新は非同期です。この監査では eviction loop を実行していません。

**Preemption の長所と短所:**
長所:
- 制約が許す場合に、高優先度ワークロード用の領域を確保できます。
- クラスターリソースを効率的に使えます。
- Service Level Agreement (SLA) への準拠を支援します。

短所:
- Preempt された Pod が中断されます。
- 再スケジュールに伴うオーバーヘッドがあります。
- Preemption の判断ロジックが複雑です。

**他の選択肢について:**
- B. 優先度の高い Pod により多くのリソースを割り当てる: Pod の優先度はリソース割り当てに直接影響しません。リソース request と limit は Pod spec で別々に定義します。
- C. 優先度の高い Pod をより速く実行する: 優先度はスケジューリング順に影響しますが、Pod 自体の実行速度は変えません。
- D. 優先度の高い Pod を特定の Node だけに配置する: nodeSelector または Node Affinity の役割であり、優先度とは直接関係ありません。
</details>

### 9. Kubernetes scheduler の「PreFilter」拡張ポイントの役割は何ですか？

A. フィルタリング前に Pod とクラスターの状態を前処理する
B. フィルタリング後に Node をスコアリングする
C. Pod を Node に Bind する前に検証する
D. スケジューリングキュー内の Pod を並べ替える

<details>
<summary>回答を表示</summary>

**回答: A. フィルタリング前に Pod とクラスターの状態を前処理する**

**解説:**
PreFilter 拡張ポイントは、フィルタリング段階で使うデータを準備し、Pod をスケジュールできるか事前確認する場合があります。

**PreFilter 拡張ポイントの主な機能:**
1. **データの準備**: フィルタリング段階で使うデータ構造を初期化して準備します。
2. **事前チェック**: Pod をスケジュールできるか先に確認します。
3. **状態の保存**: スケジューリングサイクル内で使う状態情報を保存します。
4. **最適化**: 不要なフィルタリングを避け、性能を高めます。

**バージョン付きインターフェイス:**
Kubernetes 1.35.8 では `PreFilter(ctx, state, pod, nodes) (*fwk.PreFilterResult, *fwk.Status)` を使います。`state` は `fwk.CycleState`、`nodes` は `[]fwk.NodeInfo` です。任意の AddPod/RemovePod 拡張には、スケジュール中の Pod、シミュレーション上追加/削除した PodInfo、NodeInfo が渡されます。これらは preemption シミュレーションを支援し、複製された state 上で実行されることもあります。通常の informer callback ではありません。

**既定の PreFilter プラグイン:**
Kubernetes には次の既定 PreFilter プラグインがあります。
1. **InterPodAffinity**: Pod 間の affinity と anti-affinity の要件を処理します。
2. **NodeAffinity**: Node Affinity の要件を処理します。
3. **NodePorts**: Pod が要求する host port を処理します。
4. **NodeResourcesFit**: Node のリソース要件を処理します。
5. **PodTopologySpread**: Pod Topology Spread Constraints を処理します。
6. **VolumeBinding**: ボリュームのバインド要件を処理します。

**完全な PreFilter + Filter の例（`quizplugins/prefilter.go`）:**
一般的な pool label なら必須 Node Affinity のほうが単純です。この例は、検証済みのサイクル単位の state と `Clone()` を示します。他の Pod には依存しないため、AddPod/RemovePod 拡張は不要です。PreFilter state がない場合はエラーにし、スケジュール許可として扱いません。

```go
package quizplugins

import (
	"context"
	"strings"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	validation "k8s.io/apimachinery/pkg/util/validation"
	fwk "k8s.io/kube-scheduler/framework"
)

const poolStateKey fwk.StateKey = "training.example.com/pool-constraint"

type poolState struct{ Pool string }

func (s *poolState) Clone() fwk.StateData { return &poolState{Pool: s.Pool} }

type PoolConstraint struct{}

var _ fwk.PreFilterPlugin = &PoolConstraint{}
var _ fwk.FilterPlugin = &PoolConstraint{}

func (*PoolConstraint) Name() string { return "PoolConstraint" }

func (*PoolConstraint) PreFilter(_ context.Context, state fwk.CycleState, pod *v1.Pod, _ []fwk.NodeInfo) (*fwk.PreFilterResult, *fwk.Status) {
	pool := pod.Annotations["training.example.com/required-pool"]
	if problems := validation.IsValidLabelValue(pool); len(problems) != 0 {
		return nil, fwk.NewStatus(fwk.UnschedulableAndUnresolvable, strings.Join(problems, "; "))
	}
	state.Write(poolStateKey, &poolState{Pool: pool})
	return nil, nil
}

func (*PoolConstraint) PreFilterExtensions() fwk.PreFilterExtensions { return nil }

func (*PoolConstraint) Filter(_ context.Context, state fwk.CycleState, _ *v1.Pod, info fwk.NodeInfo) *fwk.Status {
	data, err := state.Read(poolStateKey)
	if err != nil {
		return fwk.AsStatus(err)
	}
	prepared, ok := data.(*poolState)
	if !ok || info == nil || info.Node() == nil {
		return fwk.NewStatus(fwk.Error, "invalid prepared state or node")
	}
	if prepared.Pool != "" && info.Node().Labels["training.example.com/pool"] != prepared.Pool {
		return fwk.NewStatus(fwk.UnschedulableAndUnresolvable, "required pool label does not match")
	}
	return nil
}

func NewPool(_ context.Context, _ runtime.Object, _ fwk.Handle) (fwk.Plugin, error) {
	return &PoolConstraint{}, nil
}
```

**実装した両段階を有効にし、既定のリソースチェックを維持する:**
問7の登録コマンドにこのプラグインも含まれます。

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
    preFilter:
      enabled:
      - name: PoolConstraint
    filter:
      enabled:
      - name: PoolConstraint
```

**PreFilter と Filter の関係:**
1. **PreFilter**: 全 Node のフィルタリングを始める前に1回実行します。
2. **Filter**: 各 Node に対して個別に実行します。

PreFilter は Filter 段階で使うデータを準備します。また、どの Node にも配置できない Pod を事前に特定し、不要なフィルタリングを防ぎます。

**PreFilter のユースケース:**
1. **複雑な制約の処理**: Pod 間 affinity や topology spread などを効率的に処理します。
2. **事前検証**: Pod を配置できるか確認し、不要な処理を避けます。
3. **データのキャッシュ**: フィルタリング段階で繰り返し使うデータを事前計算し、性能を高めます。
4. **状態の共有**: 複数のプラグイン間で共有する状態情報を管理します。

**他の選択肢について:**
- B. フィルタリング後に Node をスコアリングする: 「Score」拡張ポイントの役割です。
- C. Pod を Node に Bind する前に検証する: 「PreBind」拡張ポイントの役割です。
- D. スケジューリングキュー内の Pod を並べ替える: 「QueueSort」拡張ポイントの役割です。
</details>

### 10. Kubernetes の Node taint `node.kubernetes.io/unreachable:NoExecute` は何を意味しますか？

A. Node に到達できず、toleration がない Pod は退避される
B. Node はスケジュール不可だが、既存の Pod は実行を続ける
C. Node はメンテナンス中で、新しい Pod は配置されない
D. Node のリソースが不足しており、新しい Pod はなるべく配置されない

<details>
<summary>回答を表示</summary>

**回答: A. Node に到達できず、toleration がない Pod は退避される**

**解説:**
`node.kubernetes.io/unreachable:NoExecute` taint は、Node に到達できず、この taint に一致する toleration を持たない Pod が Node から退避されることを示します。node controller は Node の status が `Ready` から `Unknown` に変わると、この taint を自動で追加します。

**Node が到達不能になる状態:**
一般的な原因:
1. ネットワーク接続の障害
2. kubelet process の crash
3. Node system の障害
4. Node の電源障害

**Taint の構成要素:**
1. **Key**: `node.kubernetes.io/unreachable`
2. **Value**: 通常は空文字列ですが、値を持つ場合もあります。
3. **Effect**: `NoExecute`。toleration がない Pod は Node から退避されます。

**NoExecute effect:**
`NoExecute` effect では次の動作になります。
1. 一致する toleration がない新しい Pod は、taint のある Node に配置されません。
2. すでに Node 上で動作している Pod のうち、この taint に一致する toleration がないものは退避されます。

**システム taint:**
Kubernetes は Node の status に応じて次のシステム taint を自動で追加します。
1. **node.kubernetes.io/not-ready:NoExecute**: Node が Ready ではない
2. **node.kubernetes.io/unreachable:NoExecute**: Node に到達できない
3. **node.kubernetes.io/memory-pressure:NoSchedule**: Node がメモリー不足
4. **node.kubernetes.io/disk-pressure:NoSchedule**: Node がディスク不足
5. **node.kubernetes.io/pid-pressure:NoSchedule**: Node が PID 不足
6. **node.kubernetes.io/network-unavailable:NoSchedule**: Node のネットワークが使用できない
7. **node.kubernetes.io/unschedulable:NoSchedule**: Node がスケジュール不可に設定されている

**既定の toleration:**
既定の Admission 動作では、同等の toleration が明示的に指定されていない場合に限って、Kubernetes は次の toleration を追加します。DaemonSet Pod には、not-ready/unreachable に対する期限なしの NoExecute toleration が代わりに付与されます。

```yaml
tolerations:
- key: node.kubernetes.io/not-ready
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
- key: node.kubernetes.io/unreachable
  operator: Exists
  effect: NoExecute
  tolerationSeconds: 300
```

これらの既定値は、taint 処理が始まってから300秒の間その taint を許容します。障害検知から置換までの時間が正確に5分という意味ではありません。検知、taint 公開、controller の処理制限、削除によって遅延します。切断されたプロセスが動き続けている場合もあります。

**カスタム toleration:**
toleration を長くすると Pod の置換が遅れ、障害が長引く場合があります。長いほうが安全と決めつけず、アプリケーションの復旧要件に基づいて選びます。

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  tolerations:
  - key: node.kubernetes.io/unreachable
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 600  # Tolerate for 10 minutes
  containers:
  - name: nginx
    image: nginx:1.30.6
```

**Node controller と退避のタイミング:**
基準とする upstream 1.35.8 では、`--node-monitor-period` の既定値は5秒、`--node-monitor-grace-period` は**50秒**であり、40秒ではありません。古い `--pod-eviction-timeout` flag は、taint に基づく退避の現行機構ではありません。一致する Pod toleration と taint-eviction controller が退避を制御します。検知、taint の公開、controller の rate limit、削除処理により、さらに時間がかかる場合があります。

Kubernetes 1.29 以降、taint に基づく退避は独立した `taint-eviction-controller` で実行されます。既定で有効ですが、自主管理 control plane では個別に設定できます。これらの値は EKS の設定手順でも failover 時間の保証でもありません。到達不能な Node 上の stateful Pod を強制削除する前に、古い writer が停止または fence されていることを確認し、同時書き込みを防いでください。

**Node の状態と taint の確認:**
```bash
# Check node status
kubectl get nodes

# Check node details
kubectl describe node <node-name>

# Check node taints
kubectl get node <node-name> -o jsonpath='{.spec.taints}'
```

**Pod toleration の確認:**
```bash
# Check pod tolerations
kubectl get pod <pod-name> -o jsonpath='{.spec.tolerations}'
```

**カスタムスケジューラーでの taint 処理:**
カスタムスケジューラーを実装するときは、Node taint と Pod toleration を考慮します。

```go
package diagnostic

import v1 "k8s.io/api/core/v1"

// This observes a taint; it is not a network probe or proof a process stopped.
func HasUnreachableTaint(node *v1.Node) bool {
    if node == nil {
        return false
    }
    for _, taint := range node.Spec.Taints {
        if taint.Key == "node.kubernetes.io/unreachable" && taint.Effect == v1.TaintEffectNoExecute {
            return true
        }
    }
    return false
}
```

**他の選択肢について:**
- B. Node はスケジュール不可だが、既存の Pod は実行を続ける: これは `NoSchedule` effect の動作です。`NoExecute` effect では toleration がない既存 Pod も退避します。
- C. Node はメンテナンス中で、新しい Pod は配置されない: 通常は `node.kubernetes.io/unschedulable:NoSchedule` taint の動作です。
- D. PreferNoSchedule はソフトな優先設定です。一般にメモリー不足とディスク不足には NoSchedule taint が使われ、どちらも unreachable:NoExecute を表すものではありません。
</details>

## 参考資料

[Part1 module](../../scheduling/01-custom-scheduler-part1.md) と [Part2 の実装](../../scheduling/02-custom-scheduler-part2.md) を使用してください。コードと設定はローカルで確認し、クラウドへのデプロイや eviction は実行していません。

* [v1.35.8 の Framework interface](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/framework/interface.go)
* [Extender の wire type](https://github.com/kubernetes/kubernetes/blob/v1.35.8/staging/src/k8s.io/kube-scheduler/extender/v1/types.go)
* [Node と Pod の affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
* [Topology spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
* [Taints と toleration](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
* [Priority と preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
* [Node lifecycle の既定値](https://github.com/kubernetes/kubernetes/blob/v1.35.8/pkg/controller/nodelifecycle/config/v1alpha1/defaults.go)
