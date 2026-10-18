# Amazon EKS の高可用性とレジリエンシーに関するクイズ

> **API の例示基準**: Kubernetes 1.36。公式情報とクイズの前提は[元の章](../../eks/10-eks-resiliency.md)に準拠します。
> **最終更新**: 2026年9月12日

設定や数値の例は説明用です。この監査ではクラウドリソース、カオス実験、ワークロード、ベンチマークを実行していません。所有者が管理するテスト範囲を使い、デプロイ前に仮値を置き換えてください。

このクイズでは、Amazon EKS クラスターの高可用性（HA）、レジリエンシー、Multi-AZ デプロイ、Cell-Based Architecture、Chaos Engineering、PodDisruptionBudget、Topology Spread Constraints の理解を確認します。

## クイズの概要
- Multi-AZ アーキテクチャと設定
- Cell-Based Architecture のパターン
- Chaos Engineering の原則とツール
- PodDisruptionBudget（PDB）の設定
- Topology Spread Constraints
- 災害復旧とフェイルオーバー

## 選択問題

### 1. Multi-AZ EKS ワークロードの主なレジリエンシー上の利点は何ですか？

A. コストが自動的に下がる
B. 容量、データ、ルーティングを準備していれば、1 つの AZ 障害後もサービスを継続できる設計
C. レイテンシーを高くすること
D. 運用の複雑さをなくすこと

<details>
<summary>回答を表示</summary>

**正解: B. 容量、データ、ルーティングを準備していれば、1 つの AZ 障害後もサービスを継続できる設計**

Multi-AZ は障害ドメインの設計を改善しますが、ワークロード/データの自動フェイルオーバーや可用性 99.99% を保証しません。リージョン全体の喪失にも対処しません。3 つの AZ に同容量の node を 6 台ずつ均等配置した例では、1 AZ 喪失後に 4 台が残ります。実際の Pod 配置と容量を調べる必要があります。次はプロビジョニング入力の例で、実行済みコマンドではありません。バージョン 1.36 はこの章の基準です。作成前に、現在のリージョンでの EKS/AMI サポートを確認してください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 2. PodDisruptionBudget が制約するのは何ですか？

A. Pod の CPU 使用量
B. ワークロードの可用性に応じた、サポート対象の voluntary eviction
C. すべての Pod 間通信
D. Pod 終了のすべての原因

<details>
<summary>回答を表示</summary>

**正解: B. ワークロードの可用性に応じた、サポート対象の voluntary eviction**

PDB admission が制約するのは Eviction API です。協調する drain、メンテナンス、自動スケーリング操作で利用されます。Pod の直接削除、Deployment の rolling update/scale-down、非自発的な障害から保護するものではありません。`minAvailable` と `maxUnavailable` のどちらか一方を選び、label が対象の controller 管理下ワークロードと一致することを確認してください。この例は後述する割合指定 PDB の代替であり、両方を重ねて適用するものではありません。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb
  namespace: resilience-demo
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web-app
```

</details>

### 3. `whenUnsatisfiable: DoNotSchedule` は何をしますか？

A. この制約を無視してどこにでもスケジュールする
B. 適格な node が spread 制約を満たさない場合、新しい Pod を未スケジュールのままにする
C. すべてのスケジューリング制約を無視する
D. 分布を均衡させるため既存 Pod を削除する

<details>
<summary>回答を表示</summary>

**正解: B. 適格な node が spread 制約を満たさない場合、新しい Pod を未スケジュールのままにする**

これはスケジューリング時の filter であり、API server が Pod object の作成を拒否するものではありません。`ScheduleAnyway` を指定すると、この spread ルールだけが優先設定になります。resource、affinity、taint、storage の制約は引き続き適用されます。以下の完全な Deployment では image とアプリケーション固有の health path が仮値です。適用前に置き換えてください。`minDomains=2` は、適格な zone が 2 つ残る N-1 計算を可能にしますが、最初から 3 AZ すべてを使うことを強制したり、容量を作ったりするものではありません。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-app
```

</details>

### 4. cell-based architecture の目的ではないものはどれですか？

A. 独立したデプロイ/スケーリング
B. cell 障害をシステム全体へ伝播させること
C. 自己完結した機能単位
D. 他の cell との結合を限定すること

<details>
<summary>回答を表示</summary>

**正解: B. cell 障害をシステム全体へ伝播させること**

隔離は実装とテストが必要な設計特性であり、Namespace label を付けるだけで保証されるものではありません。共有 node、control plane、DNS、router を考慮しながら、別々の routing/admission 上限、容量、データ依存関係を設計してください。以下の 2 つの namespace が示すのはグループ分けだけです。Quota と NetworkPolicy には追加の適用設定が必要であり、物理的な障害ドメインを作るものではありません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-a
  labels:
    cell: a
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cell-b
  labels:
    cell: b
```

</details>

### 5. Chaos Engineering における steady-state hypothesis とは何ですか？

A. サービスを停止状態に保つこと
B. 障害の前・最中・後に許容できる動作を、測定可能な形で示す仮説
C. 実験を停止するコマンドだけ
D. 可能な最大負荷

<details>
<summary>回答を表示</summary>

**正解: B. 障害の前・最中・後に許容できる動作を、測定可能な形で示す仮説**

実験前に、ユーザーに見えるメトリクス、測定期間、データ欠損の扱い、中止しきい値を定義してください。以前の `p99<200ms`、`errors<0.1%`、`throughput>1000req/s`、`Ready Pods>99%` は説明用しきい値であり、観測結果ではありません。Ready Pod の割合は request 可用性を示すものではありません。レビューした operator CRD に `Litmus ChaosExperiment.spec.definition.steadyState` フィールドはありません。以下の JSON は人が確認する計画であり、Kubernetes resource ではありません。

```json
{
  "scenario": "one bounded test fault",
  "hypothesis": {
    "p99_latency_seconds": "<0.2",
    "error_percentage": "<0.1",
    "request_rate_per_second": ">1000",
    "ready_pod_percentage": ">99"
  },
  "required_observations": [
    "baseline",
    "during fault",
    "recovery",
    "missing data"
  ],
  "abort": "Set an independent measured threshold and recovery owner before execution"
}
```

</details>

### 6. Kubernetes 1.36 を前提とする場合、同一 zone を優先する Service field はどれですか？

A. `spec.trafficDistribution: PreferSameZone`
B. `spec.zoneRouting: enabled`
C. `spec.localOnly: true`
D. `spec.crossZone: disabled`

<details>
<summary>回答を表示</summary>

**正解: A. `spec.trafficDistribution: PreferSameZone`**

`PreferSameZone`/`PreferSameNode` は 1.35 で GA になりました。これは優先度を示すもので、厳密な隔離やコスト削減を保証するものではありません。`PreferClose` は以前の別名です。旧 `topology-mode=Auto` annotation は別の hint heuristic を使い、topology-aware-hints は古い案内です。実際に Service を処理する proxy 実装、EndpointSlice、Local traffic policy の優先順位を確認してください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 7. 8 個の replica が正常で、進行中の disruption がなく、`maxUnavailable: 25%` の場合、名目上の eviction 許容量はいくつですか？

A. 1
B. 2
C. 3
D. 4

<details>
<summary>回答を表示</summary>

**正解: B. 2**

`ceil(8×0.25)=2` です。PDB の割合指定はどちらも切り上げます。`maxUnavailable: 25%` の replica 3 個では `ceil(0.75)=1`、`minAvailable: 75%` では正常な Pod が `ceil(2.25)=3` 個必要です。不健全な Pod と進行中の disruption は予算を消費します。あらゆる障害中に常に 6 Pod が実行される保証ではありません。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-app-pdb-percentage
  namespace: resilience-demo
spec:
  selector:
    matchLabels:
      app: web-app
  maxUnavailable: 25%
```

</details>

### 8. レビュー済みの Litmus operator/catalog に関して、誤っている主張はどれですか？

A. `pod-delete` は catalog の fault である
B. `node-drain` は instance termination とは別の fault である
C. `pod-network-loss` は catalog の fault である
D. `cluster-delete` は EKS クラスター全体を削除する標準 fault である

<details>
<summary>回答を表示</summary>

**正解: D. `cluster-delete` は EKS クラスター全体を削除する標準 fault である**

レビュー済み catalog にあるのはこれらの正確な Pod/node fault 名であり、主張にある `cluster-delete` fault ではありません。`network-loss` や `ec2-terminate` のような一般名が有効な ID だと想定しないでください。現在の AWS catalog には `aws-az-chaos`、`ebs-loss-by-id/by-tag`、`ec2-stop-by-id/by-tag` があります。実際の fault 定義、必要な RBAC、runner image を確認してください。operator をインストールしただけで、すべての experiment がインストールされるわけではありません。3.31.0 operator は ChaosHub や ChaosSchedule を定義しません。

</details>

### 9. リージョンの EKS control plane の可用性を管理するのは誰ですか？

A. ユーザーが API server を手動で配置する
B. AWS がリージョン内 3 AZ にわたる control plane を管理する
C. control plane は常に単一 AZ にある
D. マネージド EKS で etcd failover をユーザーが実装する

<details>
<summary>回答を表示</summary>

**正解: B. AWS がリージョン内 3 AZ にわたる control plane を管理する**

リージョナル EKS はマネージド control plane を 3 つの AZ に分散します。customer subnet に最低 2 AZ が必要という要件とは別です。Standard Control Plane の月間 endpoint SLA は 99.95%、Provisioned Control Plane は 99.99% であり、service credit の条件と測定期間も異なります。これはアプリケーションの可用性を保証せず、ユーザー管理のワークロード/PV backup を提供するものでもありません。ワークロード/data plane の配置、データ復旧、SLO 測定は引き続き顧客の責任です。

</details>

### 10. `DoNotSchedule` の場合、Pod 配置時に `maxSkew` が制約するのは何ですか？

A. Pod の総数
B. 配置候補 domain の数と global minimum との差
C. node の最小数
D. node あたりの Pod 上限

<details>
<summary>回答を表示</summary>

**正解: B. 配置候補 domain の数と global minimum との差**

適格な domain と `minDomains` によって global minimum が決まります。適格な domain が `minDomains` 未満の場合、最小値は 0 になります。適格な zone が 2 つ残る場合の 2/2 配置では、`minDomains=3`、`maxSkew=1` により置き換え Pod が block される可能性があります。2/2/2 は健全な配置例の 1 つですが、維持される不変条件ではありません。skew が 2 の例では 3/2/1 が許容され、4/1/1 の偏りに Pod を追加配置すると失敗する場合があります。既存 Pod が自動的に再配置または削除されるわけではありません。

</details>

## 短答問題

### 1. Kubernetes 1.36 の Service で、同一 zone を優先するにはどの field を使いますか？

<details>
<summary>回答を表示</summary>

`spec.trafficDistribution: PreferSameZone` です。これは優先設定です。実際のルーティングとコストを測定してください。従来の topology-aware-hints annotation は、現在の回答ではありません。Local traffic policy と、Service を実際に処理している実装を確認してください。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-app
  namespace: resilience-demo
spec:
  selector:
    app: web-app
  ports:
  - name: http
    port: 80
    targetPort: http
  trafficDistribution: PreferSameZone
```

</details>

### 2. PDB に従った voluntary eviction を利用できる操作を 3 つ挙げ、回避される場合と区別してください。

<details>
<summary>回答を表示</summary>

例として、Eviction を使う `kubectl drain`、Eviction 経由で drain する upgrade workflow、協調動作する node autoscaler の scale-down があります。各実装と force option を確認してください。Deployment/StatefulSet の rollout、`kubectl delete pod` による直接削除、一部のクラウド側 desired capacity 変更は、同じ形で PDB admission を利用しません。cordon は新しいスケジューリングを防ぐだけで、既存 Pod を退避させません。hardware failure、kernel panic、OOM は PDB では防げません。

</details>

### 3. 有用な chaos experiment のための制御を 4 つ説明してください。

<details>
<summary>回答を表示</summary>

測定可能な steady-state hypothesis を定義し、現実的で範囲を限定した fault を選び、代表的な環境を使います。本番環境が必要なら明示的に承認を得てください。独立した観測手段、中止しきい値、復旧担当者を用意して影響範囲を最小限にします。自動化と実験後の分析は再現性を高めますが、本番テストを必須にするものでも、データを自動復元するものでもありません。

</details>

### 4. このワークロード例で 3 AZ を使う理由は何ですか？また、EKS node group の最低要件ですか？

<details>
<summary>回答を表示</summary>

3 つの zone に同等の容量を用意すれば、ワークロードと依存関係も分散されている場合、1 zone 喪失後も既存容量の 3 分の 2 が残ります。これは設計上の選択であり、すべての node group に共通する API の最低要件ではありません。EKS cluster subnet は少なくとも 2 AZ を必要とし、リージョナル管理 control plane は 3 AZ にまたがります。顧客管理の node group の AZ が、EKS 管理 etcd の配置を決めるわけではありません。リージョン、インスタンスタイプ、storage、ワークロード制約に適合する zone を選んでください。

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: owned-ha-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-multi-az
  instanceType: m5.large
  desiredCapacity: 6
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
```

</details>

### 5. routing layer は cell にトラフィックをどのように割り当てるべきですか？

<details>
<summary>回答を表示</summary>

信頼できる tenant identity と安定した hash、明示的な対応表、またはリージョン割り当てを使ってください。router は認可、容量、データ配置を検証する必要があります。任意の client が送る `x-cell-id` を tenant 認可情報として信頼しないでください。mesh の例は、宛先 Service が登録済みで、互換性のあるポリシーがあることを前提とします。未知または信頼されていない cell ID に対して、明示的な拒否/デフォルト動作を定めてください。namespace を 2 つ作るだけ、または routing ConfigMap だけでは、隔離や failover は実装されません。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: cell-routing-example
  namespace: resilience-demo
spec:
  hosts:
  - cell-router.resilience-demo.svc.cluster.local
  http:
  - match:
    - headers:
        x-cell-id:
          exact: cell-a
    route:
    - destination:
        host: app.cell-a.svc.cluster.local
  - match:
    - headers:
        x-cell-id:
          exact: cell-b
    route:
    - destination:
        host: app.cell-b.svc.cluster.local
```

</details>

## ハンズオン演習

### 1. PDB に従った eviction 時に `app=api-server` の正常な replica を 3 つ必要とする `api-server-pdb` を書いてください。

<details>
<summary>回答を表示</summary>

ここでいうのはアプリケーションの label であり、AWS が管理する Kubernetes API server ではありません。namespace と一致する controller 管理下のワークロードが、すでに存在している必要があります。進行中の disruption がなく Ready replica が 5 個なら、eviction の許容量は 2 です。3 replica の場合、正常な Pod を eviction できる許容量はありません。以前のサンプル出力を観測結果とみなさず、実際の status を確認してください。

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-server-pdb
  namespace: resilience-demo
spec:
  minAvailable: 3
  selector:
    matchLabels:
      app: api-server
```
```bash
# Prerequisite: the owned test namespace and matching application already exist.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=api-server
# MUTATION: apply only this reviewed PDB file.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f api-server-pdb.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo describe pdb api-server-pdb
```

</details>

### 2. replica が 6 個の `web-frontend` と zone spread rule を書き、AZ 喪失時のトレードオフを説明してください。

<details>
<summary>回答を表示</summary>

完全な例では、N-1 シナリオ用に `maxSkew=1` と `minDomains=2` を使います。最初に 3 zone へ配置できることと、残った zone の容量は別々に検証する必要があります。自動的に Pod を再配置したり、zone に紐づく PVC を移動したりはしません。アプリケーションの仮 image/health path を置き換えてください。resource は例示です。制御された apply の後、すべての Pod に node name/zone label があると決めつけず、下の Python report を使って確認してください。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-frontend
  namespace: resilience-demo
spec:
  replicas: 6
  selector:
    matchLabels:
      app: web-frontend
  template:
    metadata:
      labels:
        app: web-frontend
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: web-frontend
```
```bash
# MUTATION: replace the image/health contract and review this exact file first.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f web-frontend.yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/web-frontend --timeout=5m
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods -l app=web-frontend -o json > frontend-pods.json
kubectl --context "$KUBE_CONTEXT" get nodes -o json > frontend-nodes.json
```
```python
import collections, json
from pathlib import Path
pods = json.loads(Path("frontend-pods.json").read_text())["items"]
nodes = json.loads(Path("frontend-nodes.json").read_text())["items"]
zones = {n["metadata"]["name"]: n["metadata"].get("labels", {}).get("topology.kubernetes.io/zone", "<unlabeled>") for n in nodes}
counts, ready = collections.Counter(), collections.Counter()
for pod in pods:
    if pod["metadata"].get("deletionTimestamp"):
        continue
    node = pod.get("spec", {}).get("nodeName")
    zone = zones.get(node, "<unknown-node>") if node else "<unscheduled>"
    counts[zone] += 1
    if any(c.get("type") == "Ready" and c.get("status") == "True" for c in pod.get("status", {}).get("conditions", [])):
        ready[zone] += 1
print(json.dumps({"activePodsByZone": dict(counts), "readyPodsByZone": dict(ready)}, indent=2))
```

</details>

### 3. レビュー済みテスト Pod 1 つに対象を限定し、30 秒間停止状態の Litmus Pod-deletion experiment を準備してください。

<details>
<summary>回答を表示</summary>

広範な production selector ではなく、`resilience-demo` namespace 内の、所有者が管理する `payment-service` テストワークロードを使ってください。`TARGET_PODS` は、UID/owner を確認した後に、現在の正確な Pod 名へ置き換えてください。operator、`pod-delete` ChaosExperiment、検証済み runner/helper image、範囲を限定した RBAC が事前にレビュー済みである必要があります。duration/interval の設定によっては削除を繰り返し試みます。30 秒の間に削除がちょうど 1 回起きる証明ではありません。選択した削除操作を 1 回だけ行う要件では、別途 IAM/RBAC 前提条件がある、章内の FIS `COUNT(1)` の例を使ってください。ここでは fault を実行しません。

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: payment-pod-delete-review
  namespace: resilience-demo
spec:
  engineState: stop
  appinfo:
    appns: resilience-demo
    applabel: app=payment-service,experiment-approved=true
    appkind: deployment
  chaosServiceAccount: pod-delete-sa
  experiments:
  - name: pod-delete
    spec:
      components:
        env:
        - name: TOTAL_CHAOS_DURATION
          value: '30'
        - name: CHAOS_INTERVAL
          value: '10'
        - name: FORCE
          value: 'false'
        - name: TARGET_PODS
          value: REPLACE_WITH_ONE_REVIEWED_POD_NAME
        - name: PODS_AFFECTED_PERC
          value: '100'
```
```bash
# Read-only: resolve an exact current Pod name/UID before filling TARGET_PODS.
: "${KUBE_CONTEXT:?Set the owned test context}"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get pods \
  -l 'app=payment-service,experiment-approved=true' -o wide
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosexperiment pod-delete
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get serviceaccount pod-delete-sa
# MUTATION: this reviewed file must still have engineState: stop.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo apply -f payment-pod-delete-review.yaml
```
```bash
# Read-only observation; no experiment is started by these commands.
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosengine payment-pod-delete-review -o yaml
kubectl --context "$KUBE_CONTEXT" -n resilience-demo get chaosresult
```

</details>

## 応用問題

### 1. 可用性 SLO 99.99% の金融サービスワークロードを設計し、証明が必要な項目を挙げてください。

<details>
<summary>回答を表示</summary>

99.99% はワークロードの SLO 目標であり、以下のリソースを用意すれば保証される値ではありません。365 日の時間ベース期間で計算すると、許容停止時間は年間 52.56 分です（以前の「約 52 分」は概算でした）。EKS SLA は別の月次 service-credit 契約です。request 数に基づく可用性では分母も異なります。重要なユーザージャーニー、部分障害、測定期間、RTO/RPO、alerting を定義してください。

primary/secondary region を準備し、data、identity、DNS、routing、observability、capacity を各 region で独立して利用できるようにします。replication lag、write promotion/conflict、復旧責任者をテストしてください。Multi-AZ だけでも Active-Active だけでもデータ損失ゼロは保証されません。以下の元の規模の resource 値は設計の例であり、測定容量でも実行済みデプロイでもありません。

#### Multi-AZ node の入力値と cell resource

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: finance-primary-example
  region: us-west-2
  version: '1.36'
managedNodeGroups:
- name: ng-critical
  instanceType: m5.xlarge
  desiredCapacity: 9
  availabilityZones:
  - us-west-2a
  - us-west-2b
  - us-west-2c
  labels:
    criticality: high
```
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: finance-cell
  labels:
    cell: finance
```
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: cell-quota
  namespace: finance-cell
spec:
  hard:
    requests.cpu: '100'
    requests.memory: 200Gi
    limits.cpu: '200'
    limits.memory: 400Gi
```

quota は node を予約せず、共有依存関係も隔離しません。この章のレビュー済み router/network-policy/data 境界も追加してください。以下の厳密な hostname anti-affinity では、replica が 9 個なら `criticality=high` の適格な node が 9 台必要です。30 replica へスケールするには相応の node 容量が必要です。厳密な配置では、意図的に Pod が Pending のままになる場合があります。仮 image/health contract を置き換え、まず選択したリージョン/バージョン/インスタンスタイプが利用可能か確認してください。

#### 配置と eviction 予算

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-api
  namespace: finance-cell
spec:
  replicas: 9
  selector:
    matchLabels:
      app: payment-api
  template:
    metadata:
      labels:
        app: payment-api
        tier: critical
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: app
        image: registry.example.com/team/web-app:replace-with-reviewed-digest
        ports:
        - name: http
          containerPort: 8080
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            sleep:
              seconds: 5
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
      topologySpreadConstraints:
      - maxSkew: 1
        minDomains: 2
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: payment-api
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: ScheduleAnyway
        labelSelector:
          matchLabels:
            app: payment-api
      nodeSelector:
        criticality: high
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: payment-api
            topologyKey: kubernetes.io/hostname
```
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: critical-service-pdb
  namespace: finance-cell
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: payment-api
```

正常な replica が 9 個の場合、`minAvailable: 80%` は 8 個に切り上がります。他の控除がなければ、正常な Pod を eviction できる名目上の許容量は 1 つです。すべての rollout、クラウド側 scale-down、AZ 障害を制約するものではありません。`minDomains=2` は説明した N-1 配置の計算を支援しますが、自動退避やデータ移行は行いません。

#### 実際の target と metric contract を使う HPA

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: critical-service-hpa
  namespace: finance-cell
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-api
  minReplicas: 9
  maxReplicas: 30
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

CPU resource metric には、関連 container の CPU request と、動作する Metrics Server が必要です。replica 数を増やしても、memory leak、枯渇した database、zone に紐づく volume の制約は解消できません。replica field、GitOps、HPA の管理責任を一致させてください。

定期的な game day では、所有者が管理する scheduler または承認済み workflow を使い、レビュー済みの experiment を個別に起動します。正確な target/ID を記録し、中止条件を監視し、次の fault の前に復元を確認してください。以前の 2024 ChaosSchedule snippet は期限切れであり、Litmus 3.31.0 の CRD でもありません。日付だけ変えても有効にはなりません。99.99% の主張には、週次 schedule ではなく、実際の SLI 証拠と演習が必要です。

</details>

### 2. 事前スケールと範囲を限定した障害復旧を含め、Black Friday の 10 倍トラフィックを計画してください。

<details>
<summary>回答を表示</summary>

10 倍はテスト目標であり、測定結果ではありません。request mix、CPU/メモリ、warm-up、connection、queue、database、外部 service quota をモデル化してください。目標トラフィックを処理しながら 1 AZ を失う場合も予算に含めてください。NodePool limit はプロビジョニングの上限であり、**作成済みまたは予約済みの容量ではありません**。既存の EC2NodeClass、AMI/IAM、subnet/IP、選択したインスタンスタイプが設計要件を満たす必要があります。voluntary disruption budget が 0 でも、interrupt、修復、すべての強制終了を防げるわけではありません。

#### 検証する容量設定

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: blackfriday-example
spec:
  template:
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: reviewed-test-class
      requirements:
      - key: node.kubernetes.io/instance-type
        operator: In
        values:
        - m5.2xlarge
        - m5.4xlarge
        - c5.2xlarge
        - c5.4xlarge
      - key: topology.kubernetes.io/zone
        operator: In
        values:
        - us-west-2a
        - us-west-2b
        - us-west-2c
      - key: karpenter.sh/capacity-type
        operator: In
        values:
        - on-demand
  limits:
    cpu: 2000
    memory: 4000Gi
  disruption:
    consolidationPolicy: WhenEmpty
    consolidateAfter: 30s
    budgets:
    - nodes: '0'
```
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-catalog-hpa
  namespace: resilience-demo
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-catalog
  minReplicas: 50
  maxReplicas: 500
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleDown:
      selectPolicy: Disabled
```

通常時 replica を 10、minimum を 50、maximum を 500 とする元の値は説明用です。replica の下限を 5 倍にしても、スループットが 10 倍になる証明ではありません。この HPA は、CPU request と利用可能な metric がある既存 `product-catalog` Deployment を前提とします。scaleDown を無効にするとスケールアップは許可したまま HPA の縮小を止めます。HPA 全体を停止する設定ではありません。event 前に Ready Pod、正常な endpoint、すでに利用可能な node/余力を確認し、その後レビュー済みの通常 policy に戻してください。

event 前に、代表的なテスト負荷のもとで、この章にある別途レビュー済みの experiment を実行します。範囲を限定した Pod fault、管理された zone shift/network シナリオ、依存関係の latency を個別に検証してください。`node-drain` を AZ 全体の停止とみなしたり、selector を `TARGET_PODS` として渡したり、レビューされていない fault を 1 つの実行中 production engine にまとめたりしないでください。失敗/データ欠損と実際の復旧を含めて結果を記録します。

#### シナリオ別の対応計画

| シナリオ | 証拠 | レビュー済みの対応 |
| --- | --- | --- |
| AZ の機能低下 | Endpoint/customer health、node 状態、data availability | 適格な ARC/手動の切り替えと、実証済みの残存容量。topology spread だけでは Pod は退避されない |
| database latency | query/connection/replication metric | retry/concurrency を制限する。必要であれば任意の read replica へ盲目的に切り替えず、writer promotion/runbook に従う |
| OOM/memory 増加 | limit、working set、restart、アプリケーション証拠 | resource またはアプリケーションの動作を診断/修正する。CPU HPA は OOM を自動修復しない |
| traffic surge | request mix、backlog、saturation、customer error | admission/rate limit と検証済みの scaling を使う。公開範囲/個人化の意味が安全な data だけを cache する |

#### Circuit breaker と metric

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: product-catalog-circuit-breaker
  namespace: resilience-demo
spec:
  host: product-catalog.resilience-demo.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 3s
      http:
        http1MaxPendingRequests: 1000
        http2MaxRequests: 2000
        maxRequestsPerConnection: 10
        maxRetries: 3
    outlierDetection:
      consecutive5xxErrors: 5
      consecutiveGatewayErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
```

proxy pool limit と outlier detection は backend 容量を予約するものではありません。この章の timeout/idempotency のルールに沿って調整してください。以下の query を使用するには、指定名の counter/classic histogram metric、job/namespace/status label を公開する**アプリケーション側の instrumentation**と kube-state-metrics が必要です。関連 status series を初期化し、scrape 対象になっていることを確認してください。これらの metric は EKS が自動提供するものではありません。request の分母が 0、または sample がない状態は、成功率 100% ではなく、証拠が得られない状態です。Pod indicator は Completed/deleting Pod を意図的に除外しており、アプリケーション SLI ではありません。

request rate

```promql
sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
```

5xx の割合

```promql
100 * sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m]))
and on() (sum(rate(http_requests_total{job="product-catalog",namespace="resilience-demo"}[5m])) > 0)
```

classic histogram による p99 秒数

```promql
histogram_quantile(0.99,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="product-catalog",namespace="resilience-demo"}[5m]))
)
```

request availability ではなく、テスト namespace の Ready Pod 割合

```promql
100 *
sum(
  kube_pod_status_ready{namespace="resilience-demo",condition="true"}
  and on (namespace,pod)
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
/
count(
  (kube_pod_status_phase{namespace="resilience-demo",phase=~"Pending|Running|Unknown"} == 1)
  unless on (namespace,pod) kube_pod_deletion_timestamp{namespace="resilience-demo"}
)
```

#### ワークロードの rollback と別途レビューする制御

```bash
# MUTATION: workload revision rollback only, after data/schema and GitOps review.
set -euo pipefail
: "${KUBE_CONTEXT:?Set the verified owned context}"
: "${REVIEWED_REVISION:?Set an inspected compatible Deployment revision}"
[[ "$REVIEWED_REVISION" =~ ^[1-9][0-9]*$ ]]
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout history deployment/product-catalog
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout undo deployment/product-catalog \
  --to-revision="$REVIEWED_REVISION"
kubectl --context "$KUBE_CONTEXT" -n resilience-demo rollout status deployment/product-catalog --timeout=5m
```

rollback 前に GitOps と HPA の管理責任を調整してください。rollout undo は database/PVC の rollback や EKS control plane の downgrade ではありません。`minReplicas` を 100 に上げても HPA は一時停止しません。必要な場合は HPA behavior policy と記録済みの復元計画を使ってください。feature flag の変更には、実際に認証された管理 API/SDK と監査対象の target flag が必要です。認証なしの汎用 disable URL を想定しないでください。

CloudFront の場合、まず既存の完全な設定と ETag を private file に取得してください。

```bash
# Read-only preparation; output can include sensitive origin configuration.
set -euo pipefail
umask 077
: "${CF_DIST_ID:?Set the exact owned CloudFront distribution ID}"
test ! -e cloudfront-current-private.json
aws cloudfront get-distribution-config --id "$CF_DIST_ID" > cloudfront-current-private.json
```

cache policy、cookie、authorization、個人向け content を確認します。変更には完全で有効な DistributionConfig と一致する IfMatch ETag が必要です。`update-distribution` に `--default-cache-behavior` という shortcut はありません。完全な設定を別途準備・レビューし、deployment を待って復元計画を維持してください。transactional/user-specific response に一律 24 時間の TTL を設定しないでください。

元の D-14 基本テスト、D-7 game day、D-3 最終検証/事前スケール、D-Day 監視の予定は計画例として維持しています。この環境で runtime の結果は未検証です。

[CloudFront update API](https://docs.aws.amazon.com/cli/latest/reference/cloudfront/update-distribution.html) · [HPA behavior](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) · [kube-state-metrics Pod metrics](https://github.com/kubernetes/kube-state-metrics/blob/main/docs/metrics/workload/pod-metrics.md)

</details>
