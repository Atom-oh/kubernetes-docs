# パート 9: Calico 運用ガイド

> **確認済みベースライン**: Calico 3.32.2 / Operator 1.42.6 / Calico がテストした Kubernetes 1.34～1.36。
> **最終更新日**: 2026年9月12日

## 概要

この章では、Calico デプロイのインストール、監視、トラブルシューティング、アップグレード、本番環境のベストプラクティスを含む包括的な運用方法を説明します。

運用はフィードバックループとして行います。インストールを検証し、動作を観察し、変化を診断し、アップグレード前に復旧可能な設定と状態を保持します。設定のエクスポートと、テスト済みのデータストア復旧は目的が異なります。

## インストールガイド

プラットフォームに合ったプロファイルを選び、インストール管理者を一つに決めます。次の例は、**Calico CNI を全面的に使う新規のセルフマネージド Linux クラスター**で、iptables と VXLAN を使う構成です。重複しない Pod CIDR、互換性のあるノード OS とカーネル、Kubernetes API への接続、対象ノード間のアンダーレイ UDP 4789 通信を準備します。これは VPC CNI のポリシー専用構成ではありません。EKS には[パート 8](08-eks-integration.md)を使ってください。別のオーバーレイ/BGP 構成を選ぶ前に[ネットワークモード](03-networking-modes.md)を確認します。

### Tigera Operator のマニフェスト

Calico 3.32 では Operator マニフェストに加えて、独立した Calico CRD も必要です。

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/v1_crd_projectcalico_org.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/tigera-operator.yaml
kubectl wait --for=condition=Available deployment/tigera-operator \
  -n tigera-operator --timeout=300s
```

次を `installation.yaml` として保存し、例示された Pod CIDR を準備済みクラスターに合わせて置き換えます。MTU は省略すると Operator が検出します。実際の経路を測定せず、推測した MTU を設定しないでください。

```yaml
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
---
apiVersion: operator.tigera.io/v1
kind: APIServer
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Goldmane
metadata:
  name: default
spec: {}
---
apiVersion: operator.tigera.io/v1
kind: Whisker
metadata:
  name: default
spec: {}
```

```bash
kubectl apply -f installation.yaml
```

この VXLAN 例では BGP を無効にしています。BGP 診断が必要なのは、選択したプロファイルで BGP を有効にした場合だけです。Calico API server と Goldmane/Whisker は OSS コンポーネントです。現行の OSS フローログガイドでは、可観測性機能をテクニカルプレビューとしています。運用上依存する前に、その状態を確認してください。

コンポーネントのリソースサイズと Typha のスケーリングは、測定結果がサポート対象の上書きを正当化するまでは Operator に任せてください。根拠のない固定メモリ上限、サポートされない `typhaDeployment.spec.replicas` / `minReadySeconds` の上書き、または旧 `componentResources` リストへの `KubeControllers` 追加は、本番構成ではありません。バージョンに対応した Installation API を使い、[アーキテクチャ](02-architecture.md)と[スケーリング](07-advanced-topics.md)を参照してください。

### Helm を使う場合

Helm chart は同じ Operator をインストールします。次を `calico-values.yaml` として保存してください。マニフェストで二つ目の Operator をインストールせず、この方法を使います。

```yaml
installation:
  enabled: true
  variant: Calico
  cni:
    type: Calico
  calicoNetwork:
    bgp: Disabled
    linuxDataplane: Iptables
    ipPools:
    - cidr: 10.244.0.0/16
      blockSize: 26
      encapsulation: VXLAN
      natOutgoing: Enabled
      nodeSelector: all()
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
  nodeUpdateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
apiServer:
  enabled: true
goldmane:
  enabled: true
whisker:
  enabled: true
manageCRDs: true
```

```bash
helm repo add projectcalico https://docs.tigera.io/calico/charts
helm repo update projectcalico
helm template calico projectcalico/tigera-operator \
  --namespace tigera-operator --version v3.32.2 \
  -f calico-values.yaml > calico-rendered.yaml

# Apply only after reviewing the prepared cluster and rendered resources.
helm install calico projectcalico/tigera-operator \
  --namespace tigera-operator --create-namespace --version v3.32.2 \
  -f calico-values.yaml
```

最上位の `podAnnotations` は Operator Pod に適用されます。Felix メトリクスを有効にしたり、すべてのコンポーネントの Prometheus スクレイピングを設定したりはしません。メトリクスは後述の監視セクションで明示的に設定してください。`manageCRDs: true` にすると起動後に Operator が CRD を管理します。新しいフィールドを使う際のアップグレード順序は後で説明します。

### 直接マニフェストを使う場合

すでに直接マニフェストで管理しているインストールでは、対応するリリースとプロファイルを使い、既存のカスタマイズを維持します。適用前にダウンロードしたファイルを確認してください。

```bash
curl -fL https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/manifests/calico.yaml \
  -o calico.yaml
```

Pod CIDR や有効にするネットワークモードなど、関連する設定を編集します。全体に対する `sed` 置換では、例やコメント内の値だけが変わり、実際の IP pool が設定されないことがあります。`kube-system` 内の直接マニフェストのリソースと、`calico-system` 内の Operator インストールを混在させないでください。

### インストールを検証する

```bash
kubectl get tigerastatus
kubectl get installation default -o yaml
kubectl rollout status daemonset/calico-node -n calico-system --timeout=300s
kubectl get pods -n calico-system -o wide
kubectl get nodes -o wide
```

直接マニフェストの場合は、実際の名前空間とリソース名を確認します。コンポーネントが Ready でも、ポリシー適用やアプリケーションへの到達性は証明できません。管理対象のワークロードを使い、必要な Service/DNS 経路と、許可される接続および拒否される接続をテストしてください。API アクセスを確認する際は、実際の API server HTTPS エンドポイントと適切な認証を使います。`kubernetes.default` への HTTP リクエストは、認証済み API のヘルスチェックではありません。

## calicoctl コマンドリファレンス

公式リリースから対応する **3.32.2** バイナリをインストールし、[インストールの章](01-introduction.md)の説明に従ってチェックサムを検証します。リリースアセットには Linux AMD64/ARM64、macOS AMD64/ARM64、Windows AMD64 があります。実際のホストアーキテクチャを選んでください。Bash 内で PowerShell のダウンロードコマンドを実行しないでください。また、アップグレード後に古いクライアントを使う場合は、互換性警告を調査せずに無視しないでください。

Kubernetes データストアにアクセスする場合、一般的な Unix シェル設定は次のとおりです。

```bash
export DATASTORE_TYPE=kubernetes
export KUBECONFIG="$HOME/.kube/config"
calicoctl version
calicoctl get nodes -o wide
calicoctl get networkpolicy -A
calicoctl get globalnetworkpolicy
calicoctl get tier
calicoctl get networkset -A
calicoctl get globalnetworkset
calicoctl get workloadendpoint -A
calicoctl get hostendpoint
calicoctl get ippool -o yaml
calicoctl get bgpconfiguration default -o yaml
calicoctl get bgppeer -o wide
calicoctl get felixconfiguration default -o yaml
```

kubeconfig では対象クラスターを選択し、適切な RBAC を付与してください。`--config` を明示して Calico API 設定ファイルを指定できます。`~/.config` 配下の任意のパスが自動検出されるとは限りません。etcdv3 データストアへ直接アクセスする場合は、サポートされた設定と証明書検証を使います。これは別のデプロイプロファイルであり、EKS 管理下の etcd にアクセスする権限を意味しません。

### ローカルノードの診断

`calicoctl node status` が報告するのは**ローカルノードの BGP 状態**です。kubeconfig を設定しただけで、リモートからクラスター全体の Ready 状態を確認できるわけではありません。対象ノード上で、文書化されたアクセス方法を使って実行するか、下記のようにそのノードの BIRD ソケットを調べます。

`calicoctl node diags` は選択したノード上に診断アーカイブを収集します。サポートされる `--log-dir` は**入力ログディレクトリ**を指定します。3.32.2 に `--output-dir` フラグはありません。実装には root 権限が必要で、特権診断コンテナの起動や Felix への状態ダンプシグナル送信を行うことがあります。受動的なヘルスチェックではなく、意図して証拠を収集する操作として扱ってください。作成されたアーカイブを保護し、コマンドが表示する出力先を使います。

### Calico IPAM

アドレスを**Calico IPAM**が割り当てる場合に限って、次のコマンドを使います。VPC CNI、host-local、その他の IPAM では、実際に割り当てを行うコンポーネントを調査してください。

```bash
calicoctl ipam show
calicoctl ipam show --show-blocks
calicoctl ipam show --show-borrowed
calicoctl ipam show --show-configuration
calicoctl ipam show --ip=10.244.0.15
calicoctl ipam check --show-problem-ips -o ipam-report.json
```

`--show-blocks` はブロックの使用状況を報告します。ブロックとノードの対応には BlockAffinity レコードを使います。これは Kubernetes Node の PodCIDR とは異なります。`--ip` は読み取り専用の割り当て検索です。レポートから調査候補は特定できますが、Pod が存在しないだけでは、その割り当てを安全に解放できる証拠になりません。

確認済み CLI に `ipam release --block` または `--handle` フラグはありません。レポートに基づく解放にも割り当てシーケンスの検査があり、[高度な IPAM](07-advanced-topics.md)のクリーンアップ手順が必要です。`ipam split NUMBER --cidr=...` は実在するコマンドですが、割り当てブロックではなく**IP pool**を分割します。データストアのロックが必要で、分割数は2のべき乗でなければなりません。これは計画的な移行操作であり、Pod が停止したときに通常実施する修復ではありません。

### リソースの変更とエクスポート

`get`、`create`、`apply`、`replace`、`patch`、`delete` はサポート対象のリソース型を操作します。型と名前空間を明示し、ポリシー一式を確認して、patch 時は無関係なフィールドを保持してください。たとえばログ設定の変更は既存の FelixConfiguration またはその GitOps 管理元に加えます。新しいフィールドだけを持つ置き換えオブジェクトを作らないでください。

`calicoctl get all` は全リソースのバックアップではありません。必要なリソース型を列挙し、Kubernetes ポリシーと Operator リソースも個別に含めてください。`calicoctl get ... --export` は存在しますが、確認済み CLI はリソース名を指定しないとこのフラグを無視します。リストのエクスポートが、完全で移植可能な災害復旧バックアップに変わるわけではありません。後述のバックアップセクションを参照してください。

## Prometheus メトリクス

**インストール済みバージョンの `/metrics` 出力**で名前、型、ラベルを確認してください。データプレーン固有の系列がすべてのプロファイルに存在するとは限りません。系列がないことは値がゼロという意味ではありません。下記の名前は Calico 3.32.2 のソースと公式メトリクスリファレンスで確認しています。

### コンポーネントのメトリクスを有効にする

Felix メトリクスはデフォルトで無効で、既定のポートは **9091** です。Typha メトリクスも既定では無効です。Typha バイナリの既定ポートは **9091** ですが、この Operator 例では明示的に **9093** を選びます。kube-controllers メトリクスは既定で有効になっており、ポートは **9094** です。

既存の Operator インストールでは、設定の管理元を通じて次の設定をマージしてください。

```bash
kubectl patch felixconfiguration default --type=merge \
  -p '{"spec":{"prometheusMetricsEnabled":true,"prometheusMetricsPort":9091}}'
kubectl patch installation default --type=merge \
  -p '{"spec":{"typhaMetricsPort":9093}}'
kubectl get service calico-typha-metrics -n calico-system
kubectl get service calico-kube-controllers-metrics -n calico-system
```

`typhaMetricsPort` を設定すると、Operator は Typha メトリクス用 Service を作成します。競合する Service に置き換えないでください。直接マニフェストによるインストールでは、Typha の環境設定と Service を別途用意する必要があります。メトリクスへのアクセスを適切に制限してください。host-network のエンドポイントでは、ワークロード NetworkPolicy 以外のホスト/ネットワークセキュリティ制御が必要な場合があります。

### メトリクス名と意味

| メトリクス | 型 / 意味 |
| --- | --- |
| `felix_active_local_endpoints` | Gauge。ローカルのワークロード**およびホスト**の Endpoint 数。0 が正当な値の場合もあり、Ready 判定には使えない |
| `felix_active_local_policies` | Gauge。このノードで有効なポリシー数。合計するとローカルのポリシーインスタンス数となり、クラスター内の一意なポリシー数にはならない |
| `felix_cluster_num_hosts`、`felix_cluster_num_policies` | 各 Felix が観測するクラスター全体の Gauge。同じ値をノード間で重複して合計しない |
| `felix_int_dataplane_failures` | Counter。再試行されるデータプレーン更新の失敗数。確認済みメトリクス名に `_total` 接尾辞はない |
| `felix_int_dataplane_apply_time_seconds` | 増分データプレーン更新時間の **Summary**。quantile、`_sum`、`_count` を出力し、ヒストグラムバケットは出力しない |
| `felix_iptables_restore_calls`、`felix_iptables_restore_errors` | iptables データプレーンにおける iptables-restore の呼び出し数とエラー数を表す Counter |
| `felix_log_errors`、`felix_logs_dropped` | プロセスログの書き込みエラー / 出力のブロックによるログ破棄数。ERROR レベルのログ件数や拒否パケット数ではない |
| `typha_connections_active` | Gauge。ハンドシェイク中を含むオープン接続数 |
| `typha_connections_streaming{syncer="..."}` | Gauge。ハンドシェイクを完了してストリーミング中のクライアント数 |
| `typha_connections_accepted` | Counter。受け入れた接続数 |
| `typha_connections_dropped` | Counter。**リバランスによって**切断された接続数であり、一般的なネットワーク障害数ではない |
| `typha_cache_size{syncer="..."}` | Gauge。キャッシュ内のキー/値エントリ数 |
| `typha_updates_total{syncer="..."}` | Counter。データストアの syncer **から受信した**更新数 |
| `ipam_allocations_in_use{ippool="...",node="..."}` | kube-controllers の Gauge。ワークロード/インターフェイスに割り当て済みの Calico IPAM アドレス数 |
| `ipam_ippool_size{ippool="..."}` | kube-controllers の Gauge。pool CIDR 内の総アドレス数 |
| `ipam_allocations_gc_candidates` | 調査対象となるリーク候補。アドレスを解放する許可ではない |

BIRD の制御ソケットは Prometheus exporter ではありません。`bird_protocol_up` や `calico_bgp_peer_status` などの名前は、検証済みラベルと意味を持つ exporter/collector を別途選んだ場合に限って使えます。このインストールではその系列を生成しません。以下の BGP 診断または[CalicoNodeStatus の方法](04-bgp-deep-dive.md)を使い、exporter のアラートは実際の出力を確認してから追加してください。

### ServiceMonitor の接続

この例は Prometheus Operator の CRD と `monitoring` 名前空間がすでにあることを前提とします。ServiceMonitor のラベルを Prometheus リソースの `serviceMonitorSelector` に合わせ、`serviceMonitorNamespaceSelector` にこの名前空間が含まれることを確認してください。PrometheusRule のラベルも同様に `ruleSelector` に合わせます。選択されないカスタムリソースは有効でもスクレイピングやルール評価を行いません。

次の**個別の Service**は Operator 管理下の Service を変更せず、3つすべてに `http-metrics` という名前付きポートを用意します。すでにこれらのエンドポイントをスクレイピングしている場合は、重複を追加せず既存の設定を再利用してください。ServiceMonitor の `jobLabel` が、以下で使う `calico-felix`、`calico-typha`、`calico-kube-controllers` の job 名を作ります。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-felix-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-felix
spec:
  clusterIP: None
  selector:
    k8s-app: calico-node
  ports:
  - name: http-metrics
    port: 9091
    targetPort: 9091
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-typha-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-typha
spec:
  clusterIP: None
  selector:
    k8s-app: calico-typha
  ports:
  - name: http-metrics
    port: 9093
    targetPort: 9093
    protocol: TCP
---
apiVersion: v1
kind: Service
metadata:
  name: calico-audit-kube-controllers-metrics
  namespace: calico-system
  labels:
    audit.calico/component: calico-kube-controllers
spec:
  clusterIP: None
  selector:
    k8s-app: calico-kube-controllers
  ports:
  - name: http-metrics
    port: 9094
    targetPort: 9094
    protocol: TCP
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: calico-components
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  jobLabel: audit.calico/component
  selector:
    matchExpressions:
    - key: audit.calico/component
      operator: Exists
  namespaceSelector:
    matchNames:
    - calico-system
  endpoints:
  - port: http-metrics
    interval: 30s
    scrapeTimeout: 10s
    path: /metrics
```

エンドポイントの検出/RBAC、ネットワークアクセス、Prometheus の Targets ページを確認します。ServiceMonitor の `endpoints.port` が選ぶのは**Service のポート名**であり、コンテナポート番号ではありません。ロードバランスされた Service アドレスをスクレイピングして全ノードが含まれていると思い込まず、検出された各 target を確認してください。

## Grafana ダッシュボード

設定済みの Prometheus datasource と、時系列/統計パネルを使います。以下はパネル用クエリであり、そのままインポートできる完全なダッシュボードではありません。単一クラスターのメトリクスを選びます。中央集約型のマルチクラスター datasource では、selector と集約処理で cluster ラベルを保持してください。

| パネル | PromQL |
| --- | --- |
| ノードごとの Endpoint 数 | `felix_active_local_endpoints{job="calico-felix"}` |
| ノードごとの有効ポリシー数 | `felix_active_local_policies{job="calico-felix"}` |
| 観測されたクラスターのポリシー数 | `max(felix_cluster_num_policies{job="calico-felix"})` |
| 1秒あたりのデータプレーン再試行 | `rate(felix_int_dataplane_failures{job="calico-felix"}[5m])` |
| Typha のストリーミング接続 | `typha_connections_streaming{job="calico-typha"}` |
| ローカル Summary の p99 | `felix_int_dataplane_apply_time_seconds{job="calico-felix",quantile="0.99"}` |

プロセス単位の Summary quantile はクラスター全体の p99 ではなく、`histogram_quantile` で合算できません。更新中の平均増分適用時間を求めるには、次を使います。

```promql
rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
/ rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])
```

観測がない場合、平均は未定義（`0/0`）であり、レイテンシがゼロという証拠ではありません。この Summary に `_bucket` 系列を捏造したり、未検証の `felix_iptables_restore_time_seconds` クエリを残したりしないでください。利用可能な操作カウンターとデータプレーン時間のメトリクスを使います。

Calico IPAM のアドレス使用率は次のように確認できます。

```promql
sum by (ippool) (
  max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
)
/ max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})
```

pool/node ごとに `max` を使うと、同じコントローラー観測値の重複計上を避けられます。その後、合計でノード間の割り当て数を求めます。これは**アドレス使用率**であり、使用中ブロック数でも、特定ノードで割り当て可能な容量の保証でもありません。pool selector、strict affinity、ブロック上限、予約済み/トンネル用アドレスなどの制約も関係します。VPC CNI の割り当ては表しません。空、欠落、容量ゼロのメトリクスは別途調査してください。

## アラートルール

次の例は上記の job、選択した単一クラスター、DaemonSet メトリクス用の kube-state-metrics を前提とします。存在する想定のコンポーネントに限って target 欠落ルールを有効にしてください。既存の監視を再利用する場合は selector を合わせ、しきい値と継続時間をワークロードに合わせて調整します。

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: calico-alerts
  namespace: monitoring
  labels:
    app.kubernetes.io/part-of: calico-monitoring
spec:
  groups:
  - name: calico.rules
    rules:
    - alert: CalicoDaemonSetUnavailable
      expr: kube_daemonset_status_number_unavailable{namespace="calico-system",daemonset="calico-node"}
        > 0
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: Calico DaemonSet has unavailable Pods
        description: Inspect the affected node, rollout and kube-state-metrics data.
    - alert: CalicoMetricsScrapeFailed
      expr: up{job=~"calico-(felix|typha|kube-controllers)"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Calico scrape failed for {{ $labels.job }} on {{ $labels.instance
          }}
    - alert: CalicoMetricsTargetsMissing
      expr: |-
        absent(up{job="calico-felix"})
        or absent(up{job="calico-typha"})
        or absent(up{job="calico-kube-controllers"})
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: No discovered metrics targets for {{ $labels.job }}
    - alert: CalicoDataplaneRetries
      expr: rate(felix_int_dataplane_failures{job="calico-felix"}[5m]) > 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Dataplane updates are being retried on {{ $labels.instance }}
    - alert: CalicoDataplaneMeanSlow
      expr: |-
        (rate(felix_int_dataplane_apply_time_seconds_sum{job="calico-felix"}[5m])
        / rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m])) > 0.5
        and (rate(felix_int_dataplane_apply_time_seconds_count{job="calico-felix"}[5m]) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: Mean dataplane update time exceeds 0.5s on {{ $labels.instance }}
    - alert: CalicoIPAMHighAddressUsage
      expr: |-
        (sum by (ippool) (
          max by (ippool, node) (ipam_allocations_in_use{job="calico-kube-controllers",ippool!="no_ippool"})
        )
        / max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"})) > 0.8
        and on (ippool)
        (max by (ippool) (ipam_ippool_size{job="calico-kube-controllers",ippool!="no_ippool"}) > 0)
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High address utilization in Calico IP pool {{ $labels.ippool }}
        description: Address utilization is {{ $value | humanizePercentage }}; inspect
          per-node eligibility and block constraints.
```

`up == 0` は検出済み target のスクレイピング失敗を検知します。target 自体が完全に消えた場合は検知しません。`absent` ルールは想定するコンポーネントの**全 target**が失われたことを検知します。正常なノードが残ったまま一台だけ欠落したことを見つけるには、想定されるノード/DaemonSet の一覧と比較します。メトリクスやルールが読み込まれていなければ、UI にアラートがないことは正常の証拠ではありません。

Typha 接続数の減少やリバランスカウンターの増加は、スケーリング時には想定どおりの場合があります。インシデントと判断する前に、ストリーミング/クライアントの遅延が続いているか、コンポーネントが利用可能かを照合します。同様に、ローカル Endpoint がゼロでも Felix が未 Ready とは限りません。実際の readiness/rollout 状態を確認し、許可/拒否の合成テストを別に行います。

## ログ分析とトラブルシューティング

### 影響を受けたワークロードとノードから調べる

CNI が呼び出される前に、Pending Pod がスケジュール不能な場合があります。まずイベントと `spec.nodeName` を調べます。CNI/IP 割り当てエラーでは、実際の割り当て元を特定し、影響ノードの kubelet/CNI ログを確認してください。すべての Pod IPAM エラーが Felix のプロセスログに記録されるわけではありません。

```bash
CALICO_NAMESPACE=calico-system
WORKLOAD_NAMESPACE=calico-demo
WORKLOAD_POD=replace-with-actual-pod

kubectl describe pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE"
CALICO_NODE=$(kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" \
  -o jsonpath='{.spec.nodeName}')
test -n "$CALICO_NODE" || { echo "Pod is not scheduled to a node" >&2; exit 1; }
kubectl get pods -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o wide

# Select the actual agent Pod on this node, including during a rollout.
CALICO_POD=replace-with-actual-calico-node-pod
kubectl logs -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node \
  --since=15m --tail=200 --timestamps
```

時刻範囲と末尾行数を明示してください。selector を使うと `kubectl logs` は短い tail を既定にすることがあります。指定した時間範囲だけでは、その範囲の全行を取得できた証拠になりません。コンテナが再起動している場合は、可能なら以前のログも確認します。取得エラーを「エラーなし」に置き換えず、そのまま残してください。

Felix のプロセスログは、プログラミング処理やコンポーネントの動作を記録します。`logSeverityScreen` を Debug にしても、パケットごとのポリシー判定ログは作成されません。一時的な変更の前に元のフィールドと設定管理元を記録し、以前が Info だったと決めつけず、実際の元の値または未設定状態に戻してください。ファイル/syslog 出力は設定されたパスと実行環境にも依存します。

### アドレス割り当てと接続性

| 症状 | 状態を変更する前に確認すること |
| --- | --- |
| ノードにスケジュールされない | Scheduler イベント、容量、affinity、taint。まだ IPAM の診断段階ではない |
| CNI の割り当て失敗 | 実際の割り当て元のログ、pool/アドレス容量、selector 適合性、ブロック/affinity 上限、API アクセス |
| Pod IP に届くが Service が失敗 | Endpoint/EndpointSlice、Service ポート、kube-proxy または BPF による Service 処理、DNS、ポリシー |
| 小さいパケットは通るが大きいパケットは失敗 | アンダーレイ/オーバーレイ MTU、断片化/PMTUD、戻り経路 |
| 意図したポリシーが拒否しない | 実際の Endpoint ID/ラベル、方向、namespace selector、tier/順序、先行する allow ルール、host-network/他インターフェイスの制約、既存接続 |

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip route show
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- ip -d link show
calicoctl get networkpolicy -n "$WORKLOAD_NAMESPACE" -o yaml
calicoctl get globalnetworkpolicy -o yaml
calicoctl get tier -o yaml
calicoctl get workloadendpoint -n "$WORKLOAD_NAMESPACE" -o yaml
kubectl get pod "$WORKLOAD_POD" -n "$WORKLOAD_NAMESPACE" --show-labels
```

クラスターで最初に見つかった `calico-node` Pod を選び、障害中のワークロードと同じノード上だと思い込まないでください。ICMP の成功/失敗だけでは TCP や HTTP のポリシーを検証できません。既知のツールと、アプリケーションが実際に使うプロトコル/ポートを備えた承認済みの診断ワークロードを使います。

Calico IPAM では上記の読み取り専用コマンドと[IPAM クリーンアップ手順](07-advanced-topics.md)を使ってください。pool CIDR と blockSize は変更できません。新しい CIDR をその場で拡張するのではなく、適用可能で重複しない pool を追加する計画的な容量変更を行います。原因を確認する前にアドレスを解放したり Agent を再起動したりしないでください。

Operator インストールでは、MTU とアドレス自動検出を `Installation.spec.calicoNetwork` に設定します。トンネル固有の Felix フィールドがあれば、文書化されたものを使います。`FelixConfiguration.spec.mtu` と `ipAutoDetectionMethod` は確認済み API ではありません。[MTU/ネットワークのガイダンス](03-networking-modes.md)に従い、他の設定を維持し、新規 Pod と既存 Pod を個別に検証してください。

### BGP 診断

BGP を使うプロファイルに限って BGP を確認します。選択した `calico-node` Pod 上で、実際の BIRD ソケットを使います。

```bash
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols all
kubectl exec -n "$CALICO_NAMESPACE" "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
calicoctl get bgpconfiguration -o yaml
calicoctl get bgppeer -o yaml
calicoctl get bgpfilter -o yaml
```

IPv6 デーモンがデプロイされている場合は、対応する `bird6.ctl` を使います。ローカル/ピア ASN、選ばれた送信元アドレス、双方向の TCP 179、認証/TTL 設定、ルートフィルター、期待されるルート広告を確認してください。TCP 接続の成功だけでは、セッション確立や必要なプレフィックスの受理を証明できません。ログファイルがあると決めつけず、コンテナに含まれるログ設定を確認します。実際の出力先はリリース済みコンテナの BIRD 起動/ログスクリプトで決まります。[BGP の詳細](04-bgp-deep-dive.md)を参照してください。

## ヘルスチェックの自動化

次の**Operator インストール状態チェック**は、Bash、jq、互換性のある kubectl を備えた管理環境で実行します。読み取り専用の API/ログ要求を行い、観測した DaemonSet の generation とレプリカ利用可能数を調べ、要求が失敗した場合は失敗します。BGP ソケットを調査せず、パケット転送を検証せず、すべてのポリシーが正しいことも証明しません。

```bash
#!/usr/bin/env bash
# calico-status-check.sh: operator component status and bounded log collection.
set -euo pipefail
CALICO_NAMESPACE=${CALICO_NAMESPACE:-calico-system}

if ! calico_ds_json=$(kubectl get daemonset calico-node -n "$CALICO_NAMESPACE" \
  --request-timeout=20s -o json); then
  echo "Unable to read calico-node DaemonSet status" >&2
  exit 2
fi
if ! jq -e '
  .status.desiredNumberScheduled as $desired
  | ($desired > 0)
    and (.status.observedGeneration >= .metadata.generation)
    and (.status.updatedNumberScheduled == $desired)
    and (.status.numberReady == $desired)
    and (.status.numberAvailable == $desired)
    and ((.status.numberUnavailable // 0) == 0)
' <<<"$calico_ds_json" >/dev/null; then
  echo "Calico DaemonSet is not fully observed, updated and available" >&2
  exit 1
fi

if ! calico_status_json=$(kubectl get tigerastatus --request-timeout=20s -o json); then
  echo "Unable to read operator component status" >&2
  exit 2
fi
if ! jq -e '
  (.items | length) > 0 and all(.items[];
    any(.status.conditions[]?; .type == "Available" and .status == "True")
    and any(.status.conditions[]?; .type == "Progressing" and .status == "False")
    and any(.status.conditions[]?; .type == "Degraded" and .status == "False")
  )
' <<<"$calico_status_json" >/dev/null; then
  echo "Operator components are unavailable, progressing, degraded or missing conditions" >&2
  exit 1
fi

if ! calico_logs=$(kubectl logs -n "$CALICO_NAMESPACE" -l k8s-app=calico-node \
  -c calico-node --since=15m --tail=200 --timestamps --prefix \
  --request-timeout=20s); then
  echo "Unable to retrieve selected Calico logs; do not report no errors" >&2
  exit 2
fi
printf '%s\n' "$calico_logs"
echo "Component status checks passed; review these bounded logs and test application policy separately."
```

DaemonSet に Pod がない/未スケジュール、状態が古い、コンポーネント条件が欠けている場合はチェック成功ではありません。ログは指定した範囲/末尾行に限られ、解釈も必要です。カウンターや ERROR という文字だけでは、実際の障害とは判断できません。

CronJob にする場合は、まず承認済みイメージに必要なツールとスクリプトを梱包し、検証してください。専用 ServiceAccount に DaemonSet、Pod/Pod ログ、TigeraStatus の読み取り権限を付与します。特権を持つ `calico-node` の ID を流用しないでください。同時実行数、期限、失敗通知を設定します。`calico/ctl` イメージは汎用 Bash/kubectl 診断環境ではありません。通常の Job は意図的に追加のアクセスを与えない限り、別ノードの BIRD ソケットを調査できません。このローカルスクリプトが動作するクラスター内 CronJob を提供するものではありません。

## バージョンアップグレードと復旧

### 切り替えの準備

```bash
calicoctl version
kubectl version --output=yaml
kubectl get deployment tigera-operator -n tigera-operator \
  -o jsonpath='{.spec.template.spec.containers[*].image}'
kubectl get tigerastatus
kubectl get daemonset calico-node -n calico-system -o wide
helm get values calico -n tigera-operator -o yaml
```

Helm コマンドが対象とするのは Helm 管理のインストールだけです。実際に導入されたイメージ、CRD、データストア、ノード OS/カーネル、データプレーン、Kubernetes 互換性を棚卸しします。管理下にあるマニフェスト/values、ポリシー、テスト済み復旧計画を保持します。`kubectl version --short` は現行コマンドのオプションではありません。

実際の移行元バージョンとインストール方法に対応する[3.32 アップグレード手順](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)に従います。該当リリースをまたぐ場合は OwnerReference/UID の移行メモを確認してください。移行先バージョンを固定し、calicoctl も更新します。

Helm では、新しい Operator より先に Calico CRD の管理元を通じて対応する CRD を適用するか、`manageCRDs: true` を使い、Operator がインストールを完了してから新しいフィールドを使います。Operator の更新を理由に `--force-conflicts` でフィールド所有権を無条件に上書きしないでください。確認済みの変更後は Operator、calico-node、その他の設定済みコンポーネントを監視し、ロールアウト中と完了後に allow/deny 経路をテストします。

Operator は管理対象 DaemonSet を継続的に調整します。affinity patch で「canary」ノードから Agent を削除しても安全なカナリア配布にはならず、そのノードをポリシー適用のない状態にする場合があります。代表的な隔離環境でバージョン/設定をテストし、サポートされたロールアウト制御に従ってください。競合する二つ目のノード DaemonSet を独自に作らないでください。

### 復旧の制約

`helm rollback`、旧 Operator の適用、設定エクスポートの適用だけでは、CRD/データ移行を元に戻したりパケット処理状態を復元したりできません。復旧方法を選ぶ前に、移行元/移行先リリースがサポートするダウングレード経路と保存データを調べます。Installation リソースが残っていることは、データ損失がない証拠ではありません。

EKS コントロールプレーンを復旧する場合は、[パート 8](08-eks-integration.md)に記載された最新の適用条件と7日間のロールバック制限に従います。Calico/アドオンとアプリケーションの互換性は別途確認する必要があります。

## バックアップと災害復旧

### 設定一覧と状態復旧を分ける

| 対象 | 目的と制約 |
| --- | --- |
| Git 管理のマニフェスト/Helm values とバージョン記録 | 望ましい設定と所有者を示す。対応する CRD 定義とイメージも保持する |
| Calico ポリシー、tier、set、pool、BGP/filter、controller 設定 | 実際に使われる名前空間単位、段階適用、グローバルのリソースを含む設定一覧 |
| Kubernetes NetworkPolicy、namespace/ServiceAccount のラベル、関連 RBAC | Calico 単独エクスポートでは欠落するポリシー ID と依存関係 |
| Host/node/Endpoint、IPAM 状態 | 実行時/トポロジー依存データ。古いノードアドレスや割り当てを別クラスターへ安易に再生しない |
| データストアのバックアップとアプリケーションデータ | 一貫性のある復旧方法と、別途保護する資格情報/データ。YAML の一覧はデータストアのアトミックスナップショットではない |

`kubectl export` コマンドはありません。`calicoctl get TYPE -o yaml` はリソースをエクスポートします。`--export` フラグには前述の名前付きリソースに関する制約があります。セルフマネージド Kubernetes/etcd では、対応バージョンと復元テストを含む[Kubernetes etcd のバックアップ/復旧手順](https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/)に従ってください。マネージドサービスでは各サービスがサポートする復旧方法が必要です。これは EKS etcd へのアクセス手段を提供するものではありません。

### 保護された設定一覧の例

次のスクリプトは Calico IPAM を使う 3.32 Operator インストールから、**宣言した範囲だけ**をエクスポートします。Bash、calicoctl、kubectl、sha256sum が必要です。出力先ディレクトリは存在していてはいけません。途中で失敗したエクスポートには `STATE=incomplete` が残ります。Secret、外部 IAM/ネットワーク機器、Operator の全カスタムリソース、完全な IPAM 割り当て状態は収集しません。導入済み機能に応じて一覧を意図的に拡張し、資格情報のバックアップは別に保護してください。

```bash
#!/usr/bin/env bash
# calico-config-inventory.sh: protected configuration inventory, not a datastore snapshot.
set -euo pipefail
umask 077
CALICO_EXPORT_DIR=${1:?Usage: calico-config-inventory.sh NEW_EXPORT_DIRECTORY}
mkdir -m 700 -- "$CALICO_EXPORT_DIR"
printf '%s\n' incomplete > "$CALICO_EXPORT_DIR/STATE"

for calico_kind in node ippool ipreservation bgpconfiguration bgppeer bgpfilter \
  globalnetworkpolicy stagedglobalnetworkpolicy globalnetworkset \
  felixconfiguration kubecontrollersconfiguration ipamconfiguration \
  tier hostendpoint profile; do
  calicoctl get "$calico_kind" -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
for calico_kind in networkpolicy stagednetworkpolicy stagedkubernetesnetworkpolicy \
  networkset workloadendpoint; do
  calicoctl get "$calico_kind" -A -o yaml > "$CALICO_EXPORT_DIR/$calico_kind.yaml"
done
kubectl get installation default -o yaml > "$CALICO_EXPORT_DIR/installation.yaml"
kubectl get networkpolicies.networking.k8s.io -A -o yaml \
  > "$CALICO_EXPORT_DIR/kubernetes-networkpolicies.yaml"
kubectl get namespaces -o yaml > "$CALICO_EXPORT_DIR/namespaces.yaml"
kubectl get serviceaccounts -A -o yaml > "$CALICO_EXPORT_DIR/serviceaccounts.yaml"
(
  cd -- "$CALICO_EXPORT_DIR"
  sha256sum ./*.yaml > SHA256SUMS
)
printf '%s\n' complete > "$CALICO_EXPORT_DIR/STATE"
echo "Configuration inventory completed: $CALICO_EXPORT_DIR"
```

`complete` マーカーは宣言したクエリとチェックサムの処理が完了したことを示すだけです。スナップショットのトランザクション一貫性や、災害復旧テスト済みであることを示しません。エクスポートは機密性のあるインフラデータとして扱います。チェックサムを検証し、障害ドメイン外にもコピーを保管し、実際のデータストア/バージョンを使って復旧をリハーサルしてください。

### 復元計画

1. 選んだ復旧方法で、互換性のあるコントロールプレーン/データストアと必要な CRD/Operator を復元します。新規クラスターと同一クラスターの復旧では、ID/IPAM に関する要件が異なります。
2. namespace/ServiceAccount の ID、ラベル、RBAC を確認します。次に、依存順序を守り、依存ポリシーより先に tier と set を含む管理対象の宣言的設定を復元します。
3. クラスター固有のメタデータ、生成/コントローラー管理オブジェクト、古いノードアドレス、割り当てを確認します。生のダンプを移植可能な望ましい状態のマニフェストとして再生しないでください。
4. 通常の変更作業を再開する前に、IP 割り当ての一意性、ルート、暗号化、Service/DNS の動作、許可/拒否双方のトラフィックを検証します。

`calicoctl datastore migrate export/import` はデータストアロックとロールバック境界を伴う、実際の**etcd から Kubernetes への移行**ワークフローです。既存の Kubernetes データストア向け汎用バックアップではありません。ロック中は新しい Pod に影響し、文書化された移行は Kubernetes データストアのロック解除後にロールバックできません。[移行手順](https://docs.tigera.io/calico/latest/operations/datastore-migration)を参照してください。

## 運用のベストプラクティス

### ポリシーとアクセス

必要な DNS、API、ID、監視、アプリケーション依存先を用意した選択済みテスト名前空間で、default-deny の検証を始めます。空のグローバル `all()` ポリシーや、根拠のない API server/ノードのラベル selector は必須通信を遮断するおそれがあります。Pod Endpoint と host Endpoint ではポリシー経路が異なります。範囲を限定した例、tier の意味、host Endpoint 制御は[パート 5](05-network-policy.md)を参照してください。独立して使える復旧経路を保持し、範囲を広げる前に拒否ケースをテストします。

### フローの可観測性

現行の OSS Operator/Helm インストールでは Goldmane と Whisker を利用できます。[OSS フローログガイド](https://docs.tigera.io/calico/latest/observability/view-flow-logs)はこの機能をテクニカルプレビューとしており、パケット/接続ごとに1レコードを生成するのではなく、集約したフローを説明しています。旧形式のファイル/DNS logger フィールドと、存在しない `FlowLogsFileReporter` 名は OSS の有効な設定ではありません。

```bash
kubectl get goldmane,whisker
kubectl port-forward -n calico-system service/whisker 8081:8081
```

ポートフォワードはデフォルトでローカルに bind します。Whisker/Goldmane には機密性のあるワークロード/ネットワークデータが含まれるため、外部に公開する前に認証とアクセス制御を設定してください。これらのコンポーネントが導入される前のバージョンからアップグレードする場合は、該当するカスタムリソースを意図して有効にします。プロセスの Debug ログ、ポリシーの Log action、集約フローログ、Prometheus メトリクスでは分かることが異なります。

### パフォーマンスとリソース

Endpoint/ポリシーの変更頻度、データプレーンの設定時間、キュー滞留、メモリ、実際のアプリケーショントラフィックを測定します。再同期/更新間隔は Kubernetes API のポーリング間隔ではありません。値を増やしても常に API 負荷を最適化できるわけではありません。削除済みの `...Secs` 形式ではなく、実際の duration フィールド `iptablesPostWriteCheckInterval` を使います。インストール管理者がサポートするリソース上書きと Operator のスケーリング設定を保持してください。

汎用チューニングとして BPF、DSR、根拠のないインターフェイスパターンを有効にしないでください。[パート 6](06-ebpf-dataplane.md)でカーネル/プラットフォーム要件、Service 処理、kube-proxy との競合、ロールバックを説明しています。conntrack map を大きくするとメモリを消費しますが、すべてのボトルネックがなくなるわけではありません。データプレーンやリソースを変更する正当な理由がある場合は、関連するワークロード/障害テストを再実行してください。

このガイドに付属するチェックは、オフラインの schema、クエリ、スクリプト用 fixture の検証です。本番容量、クラスターアップグレードの成功、災害復旧を証明するものではありません。

## 参考資料

- [Calico の要件](https://docs.tigera.io/calico/latest/getting-started/kubernetes/requirements)
- [Calico Installation API](https://docs.tigera.io/calico/latest/reference/installation/api)
- [コンポーネントメトリクスの監視](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
- [Felix メトリクス](https://docs.tigera.io/calico/latest/reference/felix/prometheus)
- [Typha メトリクス](https://docs.tigera.io/calico/latest/reference/typha/prometheus)
- [kube-controllers メトリクス](https://docs.tigera.io/calico/latest/reference/kube-controllers/prometheus)
- [Calico のトラブルシューティング](https://docs.tigera.io/calico/latest/operations/troubleshoot/troubleshooting)
- [Calico のアップグレード手順](https://docs.tigera.io/calico/latest/operations/upgrading/kubernetes-upgrade)
- [Prometheus Operator API](https://prometheus-operator.dev/docs/api-reference/api/)

## 次のステップとクイズ

[用語集](glossary.md)、[高度なトピック](07-advanced-topics.md)、[EKS 統合](08-eks-integration.md)、[運用クイズ](../../quizzes/networking/calico/09-operations-quiz.md)を確認してください。
