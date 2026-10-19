# Cilium Service Mesh のベストプラクティス

> **レビュー対象バージョン**：Cilium 1.20.3、Cilium CLI 0.20.1。
> **最終レビュー日**：2026年10月16日。[インストールガイド](./README.md)で Kubernetes、EKS、およびオプションコンポーネントの互換性を個別に確認してください。

## 概要

運用計画では、CNI の所有範囲、プロキシ機能、ポリシー適用、容量、復旧を結び付けてください。以下の値は、特定のクラスターに照らして確認する例です。本番環境でテスト済みのサイジング保証、CNI 移行手順、または EKS の完全なインストール手順ではありません。

## 本番デプロイのチェックリスト

- [ ] サポートされる Kubernetes/Cilium/プラットフォームの組み合わせ、CPU アーキテクチャ、ノード OS を選びます。一般的な最低カーネルは 5.10 です。RHEL 8.10 の 4.18 など、文書化された同等のものもあります。高度な機能には、より新しいカーネルが必要な場合があります。
- [ ] 現在の CNI、IPAM、Pod/Service/VPC CIDR、ルート、MTU、kube-proxy の所有者を記録します。kube-proxy 置き換えを有効にする前に、API サーバーへの到達可能なアドレスを確認します。
- [ ] ワークロードごとに L7 の所有者を選択します。Cilium Ingress/Gateway には、文書化された kube-proxy 置き換えと L7 の前提条件があります。Istio との共存では設定が異なります。
- [ ] 認証、暗号化、認可を個別に選びます。default deny を強制する前に、許可/拒否するフロー、DNS、必須のインフラアクセスを検証します。
- [ ] メトリクスの目標、実際のラベル、ログ、アラートのルーティング、証明書の更新を確立します。データ欠落時の挙動をテストします。
- [ ] レプリカの配置と保守に十分な適格ノードを確保します。Operator/Relay の準備状態、disruption budget、DaemonSet の更新戦略を確認します。
- [ ] テスト済みのロールバック地点、保持する chart/values/CRD、ワークロード/ポリシーの一覧を記録します。実環境を代表する環境でリハーサルします。

### 確認する Helm Values

この**リソースおよび可用性のオーバーレイ**を、インストールガイドのプラットフォーム設定に統合してください。汎用 IPAM 範囲の選択、kube-proxy の無効化、またはすべてのオプションセキュリティ機能の有効化は意図していません。

```yaml
agent: true
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
operator:
  replicas: 2
  podDisruptionBudget:
    enabled: true
    maxUnavailable: 1
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 1000m
      memory: 1Gi
l7Proxy: true
envoy:
  enabled: true
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 2000m
      memory: 2Gi
hubble:
  enabled: true
  relay:
    enabled: true
    replicas: 2
    podDisruptionBudget:
      enabled: true
      maxUnavailable: 1
    affinity:
      podAntiAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
        - topologyKey: kubernetes.io/hostname
          labelSelector:
            matchLabels:
              k8s-app: hubble-relay
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 1000m
        memory: 1Gi
updateStrategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1
```

`agent` は boolean です。Agent のリソース要求/上限は `agent.resources` ではなく、トップレベルの `resources` に設定します。競合していた元のリソース定義2つは統合しました。CPU/メモリの値は出発点の例です。ポリシー数、変更頻度、トラフィック、障害シナリオで測定してください。

Operator chart の affinity は、レプリカをホスト名ごとに分散します。ここでの Relay anti-affinity も、配置可能なノードが2台あることを必要とします。アベイラビリティゾーン間の分散は強制されないため、クラスターに適した topology 条件を追加してください。配置可能なノードや依存先が機能しない状態では、レプリカを2つにしても HA にはなりません。PDB が対象とするのは条件を満たす自発的な退避であり、あらゆる障害や DaemonSet controller の rollout ではありません。Pod を直接削除する操作も退避保護を迂回します。

外部 etcd は、ノード数があるしきい値に達したら必ず追加するものではなく、固有の運用要件を持つアーキテクチャ上の選択です。選んだ identity 割り当てモードを一貫させ、変更する場合は文書化された移行手順に従ってください。

### 認証と暗号化

以下は、任意の out-of-band 認証と WireGuard を組み合わせる構成例です。

```yaml
encryption:
  enabled: true
  type: wireguard
  nodeEncryption: false
authentication:
  enabled: true
  mutual:
    spire:
      enabled: true
```

[セキュリティガイド](./03-security.md)のカーネル、ポート、SPIRE ストレージ/identity、ポリシーの前提条件を満たす場合にのみ有効にしてください。SPIRE の設定に加えて `authentication.enabled` が必要です。認証を強制するには、ルールで認証を要求する必要があります。WireGuard は条件を満たすノード間トラフィックを保護します。SPIRE による out-of-band 認証によって、各アプリケーション接続が Istio 形式の mTLS セッションになるわけではありません。`nodeEncryption` は別の条件に従う設定で、この例では false のままです。

Cilium 1.20.3 には **Beta の ztunnel ワークロード mTLS** もあり、別途セキュリティガイドに記載されています。デフォルトの内部 CA、namespace の enrollment、TCP/HBONE/ポリシー上の制限は、SPIRE out-of-band 経路とは異なります。明示的に設計を選択してください。チェックボックスの文言や Helm feature flag だけでは、同等のセキュリティ範囲を証明できません。

## サイジングの指針

### コンポーネントごとの測定

| コンポーネント | 測定する容量要因 | 上限を増やす前の確認事項 |
|---|---|---|
| Agent | Endpoint、identity、policy selector/rule、接続の変更頻度、BPF map、イベント量 | Working set、CPU/スロットリング、map 圧迫、policy 再生成、drop の理由 |
| Envoy | 同時接続/stream、TLS 処理、request/response サイズ、buffering、filter の負荷 | Heap/RSS、CPU、queueing、upstream の飽和、固定した workload における p99 |
| Operator | IPAM/identity/node の変更頻度、API latency/rate limit | Reconciliation backlog、EC2/Kubernetes throttling、割り当て失敗 |
| Hubble Relay/UI | 観測する flow 量、同時 observer、flow buffer、query 範囲 | イベント欠落、Relay リソース、query latency、レプリカ配置 |

以前のノード数別テーブルと `512Mi + Pods × 1Mi`、`256Mi + connections/second × 0.1Mi` の式には、ベンチマークの根拠がありません。汎用的なメモリモデルとして使えません。同時接続のピーク、buffer の保持時間、トラフィック構成、ポリシー数が重要です。requests/second の数値だけでは、保持されるメモリ量は決まりません。実測した配置要件から request を設定し、テスト済みの headroom を確保して、負荷急増時と1ノード喪失時に上限を検証してください。

### eBPF Map のサイジング

以下は、1つの明示的な static sizing 例です。1つの YAML mapping に複数の代替案を並べたものではありません。

```yaml
bpf:
  ctTcpMax: 2097152
  ctAnyMax: 1048576
  natMax: 2097152
  policyMapMax: 65536
```

現在の chart key は `ctTcpMax`、`ctAnyMax`、`natMax` です。以前の `ctGlobalTcpMax`、`ctGlobalAnyMax`、`natGlobalMax` は無視されます。Agent ConfigMap の flag は `bpf-ct-global-tcp-max` などの名前を使うため、chart key と daemon flag を混同しないでください。NAT 容量は TCP/その他の CT 容量合計の3分の2を超えてはいけません。この値は上限内です。map entry の上限は、アプリケーションセッション数を保証しません。

map サイズを増やすと、ノード/カーネルメモリを多く使います。map をリサイズしたり実装を変えたりすると、state や接続に影響する場合があります。render した ConfigMap と実際の map 使用量を確認してください。ノード数から容量を推定したり、人が読める CLI 出力行を正確な使用量として数えたりしないでください。

## パフォーマンスの調整

### eBPF の設定

```yaml
bpf:
  preallocateMaps: true
  mapDynamicSizeRatio: 0.0025
bpfClockProbe: false
```

Preallocation は、先に多くのメモリを使う代わりに、一部の割り当て処理を避けます。メモリ節約用の切り替えではありません。この代替案は dynamic sizing ratio を使用します。static map の例と安易に組み合わせないでください。明示サイズは計算されたサイズを上書きし、distributed LRU には追加の制約があります。`bpfClockProbe` はトップレベルの key です。既存 CT state がある環境で clock 表現を変更する場合は、文書化された移行上の注意に従ってください。

`socketLB` もトップレベルにあり、`bpf` の下にはありません。Istio との共存では `hostNamespaceOnly` の設定が重要です。socket acceleration を無差別に有効にすると、想定される proxy interception を迂回する場合があります。以前の `bpf.lbBypassFIBLookup` はサポートされる chart value ではありません。

公開済み tuning guide の netkit/BIG TCP profile には、カーネル/NIC と移行の前提条件があります（その profile にはカーネル6.8が必要です）。既存の veth Pod は、value を切り替えるだけでは変換できません。文書化されたノード単位/新規ノードでの移行方法を使い、拡大する前に暗号化、ルーティング、アプリケーションの挙動を検証してください。

### ネットワークスタック

最初にノードの設定を確認します。

```bash
sysctl net.core.somaxconn net.ipv4.tcp_max_syn_backlog \
  net.core.netdev_max_backlog net.ipv4.tcp_fin_timeout net.ipv4.tcp_tw_reuse
```

関連する queue または接続状態のボトルネックを特定し、対象カーネルの意味を確認してから sysctl を変更してください。以前のグローバルな `sysctl -w` 一覧は、特定 workload に対する tuning 結果ではありません。特に `tcp_fin_timeout` は汎用 TIME_WAIT cleanup 用の設定ではなく、TIME_WAIT reuse の設定も一般的な latency 対策ではありません。元の設定を保持し、レビュー済みの rollout には管理されたノード設定を使ってください。

### Envoy

`CiliumEnvoyConfig.spec.resources` が受け付けるのは特定の xDS resource type であり、Bootstrap object ではありません。元の例のように overload manager を含む Bootstrap を CEC に入れても適用されません。固定 heap monitor だけでは overload action も定義されません。

chart の resource limit と、完全な[接続プールの例](./05-ingress-gateway.md#connection-pool-configuration)は、それぞれの目的に使います。overload manager は、サポートされる action と threshold を指定して process bootstrap に置きます。`envoy.bootstrapConfigMap` を使用する場合は、Cilium に必要な bootstrap 配線を維持し、実際にリリースされた Envoy image で検証してください。Bootstrap 全体の置き換えは高度な統合であり、安全な部分 CEC patch ではありません。

### ベンチマークの根拠

以前の図は、根拠となる出典、バージョン、topology、負荷、暗号化設定、再現データを示さずに、native/Cilium/Istio の p99 値を 0.1/0.3/2.5 ms としていました。検証済みの測定結果としては掲載しません。根拠がある場合は、実際のベンチマークのバージョンと日付を記録してください。古い結果に新しいリリース名を付けないでください。

有用な比較では、ハードウェア、カーネル/CNI/mesh のバージョン、request サイズ、同時実行数、接続数、TLS/policy/filter の設定、warm-up、sample 数、throughput、error rate、tail latency を記録します。Cilium のすべての経路が Envoy を通らない mesh だと仮定せず、同等の L4 または L7/セキュリティ動作を比較してください。

## Sidecar Mesh からの移行

### CNI の移行と Mesh の移行を分ける

既存 CNI の隣に2つ目の CNI をインストールするだけでは不十分です。公式の dual-overlay 移行手順では、異なる Pod CIDR と encapsulation、ノードごとの制御、ワークロードの再作成、policy enforcement 上のトレードオフへの明示的な対応が必要です。テストされていない組み合わせなど制約もあります。実際のプラットフォーム構成をリハーサルしてください。以前の図にあった「既存 CNI と並行してインストールする」という一般的な手順には、不可欠な要件が抜けていました。

すでに Cilium がネットワークを提供している場合、mesh との共存は別の作業です。Cilium の Istio 統合ガイドでは、kube-proxy を残す経路を説明しています。

```yaml
kubeProxyReplacement: false
cni:
  exclusive: false
```

kube-proxy の完全置き換えを計画する場合は、次を参照してください。

```yaml
kubeProxyReplacement: true
socketLB:
  hostNamespaceOnly: true
cni:
  exclusive: false
```

必要な API サーバー、CNI/IPAM、プラットフォーム設定を維持してください。`cni.exclusive: false` は Istio CNI など他の CNI 設定を保持します。`socketLB.hostNamespaceOnly: true` は Pod レベルの proxy capture への干渉を避けます。古い `tunnel: vxlan` key は現在の移行手順ではありません。overlay を独立して選ぶ場合、現在の key は `routingMode` と `tunnelProtocol` です。適切な routing/MTU 要件も設定してください。

### ワークロードを計画的に切り替える

変更前に、`istio-injection`、revision label、Pod injection annotation、ambient enrollment、既存 sidecar を記録します。namespace label が影響するのは今後の admission であり、実行中の sidecar は削除しません。revision label や Pod ごとの設定は、単純な namespace 計画を上書きすることがあります。可用性を確認し、置き換え後の policy を検証してから、選択した workload だけを再作成してください。

移行中はワークロードごとに L7 policy の所有者を1つにしてください。Cilium は Istio で暗号化されたトラフィック内部の HTTP rule を強制できません。HTTP の可視性を得るためだけに Istio mTLS を無効化するのは、セキュリティを変更する行為であり、自動的な変換手順ではありません。Ambient HBONE も、L4 で Cilium が観測できる内容を変えます。その経路が残る場合は、ワークロード identity と内部トラフィックの policy を Istio に任せてください。

### ルーティング変換の例

前提：Pod port 9080 で HTTP を提供する、`app: reviews` かつ `version: v1` または `v2` の準備完了 Pod。別々の Service にすることで version の選択を明示します。

```yaml
apiVersion: v1
kind: Service
metadata:
  name: reviews
  namespace: default
spec:
  selector:
    app: reviews
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v1
  namespace: default
spec:
  selector:
    app: reviews
    version: v1
  ports:
  - name: http
    port: 9080
    targetPort: 9080
---
apiVersion: v1
kind: Service
metadata:
  name: reviews-v2
  namespace: default
spec:
  selector:
    app: reviews
    version: v2
  ports:
  - name: http
    port: 9080
    targetPort: 9080
```

Istio の routing 設定には VirtualService と subset 定義の両方が必要です。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews-route
  namespace: default
spec:
  hosts:
  - reviews
  http:
  - match:
    - headers:
        end-user:
          exact: jason
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
---
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews-subsets
  namespace: default
spec:
  host: reviews
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

L7 の所有権を移した workload では、完全な Cilium CEC によって次の header 選択動作を実装できます。

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: reviews-route
  namespace: default
spec:
  services:
  - name: reviews
    namespace: default
    ports:
    - 9080
    listener: reviews-listener
  backendServices:
  - name: reviews-v1
    namespace: default
  - name: reviews-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: reviews-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: reviews-migration
          route_config:
            name: reviews-routes
            virtual_hosts:
            - name: reviews
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: end-user
                    string_match:
                      exact: jason
                route:
                  cluster: default/reviews-v2
              - match:
                  prefix: /
                route:
                  cluster: default/reviews-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v1
    type: EDS
    connect_timeout: 5s
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/reviews-v2
    type: EDS
    connect_timeout: 5s
```

CEC には Listener、HCM/router、2つの EDS Cluster、実際の backend Service 参照があります。Cilium が dynamic endpoint 設定を提供します。`end-user: jason` は信頼できない routing 入力であり、認証情報ではありません。この例は Istio のすべての timeout/retry/mTLS/telemetry 動作を再現しません。別途比較し、書き込みを保護する場合は[retry の指針](./02-traffic-management.md#retry-configuration)に従ってください。両方の実装を同じ有効なトラフィック経路に接続して、同じ所有権であると想定しないでください。

### 認可は機械的に変換できません

Pod port 8080 の Istio 管理下 `app: httpbin` workload では、受信 mTLS を必須にし、認証済みの特定 service-account principal を許可します。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: httpbin-strict
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  selector:
    matchLabels:
      app: httpbin
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/default/sa/sleep
    to:
    - operation:
        methods:
        - GET
        paths:
        - /info*
        ports:
        - '8080'
```

同じ namespace/service-account label の選択と GET/path の意図を持つ Cilium policy の候補は次のとおりです。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: httpbin
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: httpbin
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: default
        k8s:io.cilium.k8s.policy.serviceaccount: sleep
    authentication:
      mode: required
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/info.*$
```

これには別途インストールされた Cilium authentication system が必要です。Istio の証明書 principal は利用しません。security identity、trust domain、認証 exchange、暗号化範囲も異なります。port は **Pod の宛先 port**であり、Service port とは限りません。どちらのシステムでも、他の allow policy がアクセスを広げる場合があります。また、この ingress rule は Cilium egress を拒否しません。移行と同等性を判断する前に、許可された GET、拒否される method/path、誤った service account、認証欠落、暗号化/非暗号化の経路をテストしてください。

### ロールバック計画

元の workload template、label、policy、Secret/証明書の所有範囲、Helm values をデプロイシステムに保持します。移行が所有する resource を正確に記録してください。まず選択した旧トラフィック/policy 経路を復元し、その identity/enforcement を検証してから、テスト済みの順序で置き換えた移行 resource だけを削除します。

以前の script は namespace 内の **すべての CiliumNetworkPolicy を削除**していました。無関係な default-deny 保護まで削除する恐れがあるため、取り除きました。injection label を1つ再有効化して、すべての Deployment を再起動するだけでも不十分です。revision 管理の injection、ambient enrollment、StatefulSet、Job には対応できません。CNI/IPAM のロールバックでは、ノードと Pod の再作成が必要な場合があり、別の復旧手順です。

## 段階的な導入

Cilium に L3/L4 のネットワークと policy だけを担わせる場合は、対象の Cilium L7 feature を明示的に無効にします。

```yaml
l7Proxy: false
envoy:
  enabled: false
ingressController:
  enabled: false
gatewayAPI:
  enabled: false
```

`envoy.enabled: false` だけでは、L7 が有効なときに embedded Envoy mode を選択します。Cilium の L7 動作がすべて無効になるわけではありません。機能を削除する前に、既存の L7 policy、Ingress/Gateway resource、CEC を一覧にしてください。Istio ambient では、通常の平文トラフィックと同じように Cilium が元の内部 workload flow を見るのではなく、HBONE transport を観測します。

| 段階 | L7 の所有範囲と終了条件 |
|---|---|
| ネットワークを確立 | 現在の mesh が意図したトラフィックの所有権を維持したまま、Cilium CNI/L3/L4 の動作を検証します |
| 選択した workload を切り替え | 所有権を workload ごとに分け、negative test も使って routing、identity、暗号化、retry、telemetry を比較します |
| 旧コンポーネントを廃止 | すべての依存 workload と復旧手順を検証した後にのみ削除します |

以前の移行図は、ポリシーを一括削除するロールバックを繰り返し、共存を単純化しすぎていました。この表がその手順に代わります。

## 監視とアラート

### Scrape Label を明示する

先に Prometheus Operator CRD をインストールし、その ServiceMonitor/PrometheusRule selector を設定します。この overlay は例の job 名と cluster label を固定します。実際のクラスター identity に合わせて `example-cluster` を一貫して置き換え、`release` selector も調整してください。

```yaml
prometheus:
  enabled: true
  serviceMonitor:
    enabled: true
    labels:
      release: prometheus
    relabelings:
    - sourceLabels:
      - __meta_kubernetes_pod_node_name
      targetLabel: node
    - targetLabel: cluster
      replacement: example-cluster
    - targetLabel: job
      replacement: cilium-agent
envoy:
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
      labels:
        release: prometheus
      relabelings:
      - sourceLabels:
        - __meta_kubernetes_pod_node_name
        targetLabel: node
      - targetLabel: cluster
        replacement: example-cluster
      - targetLabel: job
        replacement: cilium-envoy
```

Hubble HTTPv2 の context と recording rule は、[可観測性ガイド](./04-observability.md)で別に設定します。必要な可視性があるトラフィックだけが L7 observation を生成します。信頼できる内部 metrics 経路を使ってください。この値はリモート Prometheus への到達性を設定しません。

### 運用ルール

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cilium-operational-signals
  namespace: monitoring
  labels:
    release: prometheus
spec:
  groups:
  - name: cilium.operational
    rules:
    - alert: CiliumMetricsScrapeFailed
      expr: up{job=~"cilium-agent|cilium-envoy"} == 0
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: Known Cilium metrics target cannot be scraped
    - alert: HighObservedPacketDrops
      expr: sum by (cluster, node, direction, reason) (rate(cilium_drop_count_total[5m]))
        > 1000
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: High observed packet drop count
    - alert: HighBPFMapPressure
      expr: cilium_bpf_map_pressure > 0.8
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: High pressure in an instrumented BPF map
```

`up` scrape の失敗は target へのアクセス失敗を示しますが、Agent/Envoy process の停止とは限りません。discovery が target を除外すると `up` series 自体が消える場合があります。期待される node/DaemonSet の一覧も別途比較してください。`cilium_proxy_redirects` はインストールされた redirect の数です。正当に0になる場合があり、Envoy の稼働状態を示すものではありません。

以前の `cilium_datapath_conntrack_active/max` ratio は存在しない metric を使っていました。CT GC の観測値は瞬時の全容量 gauge ではありません。map-pressure metric は計測対象の map と出力条件をカバーします。どの map が存在するか確認してください。drop/pressure のしきい値は例示であり、トラフィック、理由、継続時間、想定される policy deny に合わせて調整する必要があります。

### Dashboard のインポート

これは Grafana UI にインポートする独立した classic dashboard JSON であり、HTTP API wrapper ではありません。Prometheus data source を選び、まず可観測性ガイドの `cilium_hubble:*` recording rule をインストールしてください。

```json
{
  "__inputs": [
    {
      "name": "DS_PROMETHEUS",
      "label": "Prometheus",
      "type": "datasource",
      "pluginId": "prometheus",
      "pluginName": "Prometheus"
    }
  ],
  "id": null,
  "uid": "cilium-operational",
  "title": "Cilium operational signals",
  "tags": [
    "cilium",
    "hubble"
  ],
  "schemaVersion": 38,
  "version": 1,
  "timezone": "browser",
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "refresh": "30s",
  "panels": [
    {
      "id": 10,
      "title": "Successfully scraped agent targets",
      "type": "stat",
      "gridPos": {
        "x": 0,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "sum by (cluster) (up{job=\"cilium-agent\"})",
          "legendFormat": "{{cluster}}"
        }
      ]
    },
    {
      "id": 1,
      "title": "Observed HTTP responses/s",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 0,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_responses:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "reqps"
        },
        "overrides": []
      }
    },
    {
      "id": 2,
      "title": "Observed HTTP5xx (%)",
      "type": "timeseries",
      "gridPos": {
        "x": 0,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "cilium_hubble:http_5xx_percent:rate5m",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "percent"
        },
        "overrides": []
      }
    },
    {
      "id": 3,
      "title": "Observed HTTP P99",
      "type": "timeseries",
      "gridPos": {
        "x": 12,
        "y": 8,
        "w": 12,
        "h": 8
      },
      "datasource": {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}"
      },
      "targets": [
        {
          "refId": "A",
          "expr": "histogram_quantile(0.99, cilium_hubble:http_latency_bucket:rate5m)",
          "legendFormat": "{{cluster}} / {{destination_namespace}} / {{destination_workload}}"
        }
      ],
      "fieldConfig": {
        "defaults": {
          "unit": "s"
        },
        "overrides": []
      }
    }
  ]
}
```

health panel は正常に scrape できた Agent target を数えるもので、「healthy Pod」の数ではありません。HTTP panel は recording rule の server-side 境界、namespace/workload/cluster の範囲、numerator 欠落時の動作を引き継ぎます。no-data は失敗ゼロではありません。この dashboard には指定された source と label が必要です。

## アップグレード戦略

### Rollout 前に確認する

Cilium がテストするアップグレードとロールバックは、連続した minor release 間のみです。最初に現在の minor を最新 patch に更新し、途中にある各 release の必須変更を確認してください。以下の対象は1.20.3です。古い1.16/1.17の例から直接移行できる、サポートされた upgrade path ではありません。

`upgradeCompatibility` には、任意に選んだ target/current version ではなく、**最初にインストールされた minor version**を記録します。既存の user values を export し、名前変更/削除された key を確認して、新しい設定を `reviewed-values.yaml` として保存してください。機密情報が含まれる場合は、このファイルと export した values を非公開に保ちます。

```bash
set -eu
umask 077
CILIUM_TARGET_VERSION=1.20.3
: "${INITIAL_CILIUM_MINOR:?Set the initial installed Cilium minor, for example 1.19}"
helm get values cilium -n kube-system -o yaml > old-values.yaml
helm history cilium -n kube-system
helm repo add cilium https://helm.cilium.io/
helm repo update cilium
test -s reviewed-values.yaml
helm template cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" > candidate.yaml
```

次の手順に進む前に、生成された resource と公式の事前確認手順をレビューしてください。`helm diff` は別途インストールする任意の plugin であり、Helm 標準機能ではありません。version 変更時に `--reuse-values` を避けてください。新しく導入された chart default が隠れる可能性があります。

サポートされた path と保守/復旧計画を確認してから、同じ shell/session でレビュー済みの変更を実行できます。

```bash
set -eu
: "${CILIUM_TARGET_VERSION:?Use the previously reviewed target version}"
: "${INITIAL_CILIUM_MINOR:?Use the previously reviewed initial installed minor}"
helm upgrade cilium cilium/cilium -n kube-system \
  --version "$CILIUM_TARGET_VERSION" -f reviewed-values.yaml \
  --set-string "upgradeCompatibility=$INITIAL_CILIUM_MINOR" --wait --timeout 10m
cilium status --wait
kubectl -n kube-system get daemonset cilium cilium-envoy
kubectl -n kube-system get deployment cilium-operator hubble-relay
```

`cilium connectivity test` は、テスト workload とネットワークトラフィックを作成する有用な **active test** です。読み取り専用の状態確認だと見なさず、計画されたテスト環境で実行してください。コンポーネントの準備状態に加えて、アプリケーション固有の negative policy test と長時間接続も確認します。

### Canary 戦略

ノード label だけでは別バージョンの Cilium は選択できません。重複する2つ目の Cilium DaemonSet をデプロイして canary にしないでください。Agent はノード単位のネットワーク資源とクラスター設定を共有します。まず実環境を代表するテストクラスターで release を検証します。ノードごとに制御された rollout を行う場合は、サポートされる単一所有者の仕組みを使い、Operator/共有 ConfigMap の変更を考慮し、一時的な version skew を制限します。通常運用では Cilium の全コンポーネントを同一 release にします。

### ロールバック

CRD/feature/state の追加で安全な downgrade が妨げられないか確認してから、**互換性をレビューした** Helm revision を選んでください。

```bash
set -eu
helm history cilium -n kube-system
: "${CILIUM_ROLLBACK_REVISION:?Set the reviewed, compatible Helm revision}"
helm rollback cilium "$CILIUM_ROLLBACK_REVISION" \
  -n kube-system --wait --timeout 10m
cilium status --wait
```

1.15 に無条件で downgrade したり、Helm revision の rollback によってノードネットワーク、CRD schema、使用済みのすべての feature が元に戻ると想定したりしないでください。変更に release 固有の rollback 前提条件と復旧テストを含めます。

## トラブルシューティング

### ノードと Policy の状態

```bash
cilium status --wait
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
kubectl -n kube-system exec ds/cilium -- cilium-dbg policy get
kubectl -n kube-system exec ds/cilium -- cilium-dbg service list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ct list global
```

host 上の `cilium` CLI はインストールを管理します。Agent 内の `cilium-dbg` はローカル datapath state を調査します。`exec ds/cilium` は Pod を1つ選ぶため、障害対応中は影響を受けた実際のノードの Pod を対象にしてください。CT entry の一覧は大量の出力を生成する場合があります。`wc -l` による正確な使用量測定としては信頼できません。

### Envoy と Latency

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config listeners
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config routes
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin config clusters
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics
```

認証されていない port 9901 の TCP listener や、コンテナ内の `curl` binary を想定せず、サポートされる admin command/socket 経路を使ってください。L7 redirect の欠如、upstream の利用不可、policy deny、接続の飽和、アプリケーション応答の遅延を区別します。Ingress/Gateway と可観測性ガイドにある histogram の単位と label を正しく使います。

### 一時的なデバッグとログ

```yaml
debug:
  enabled: true
  verbose: flow envoy policy
```

`debug.verbose` は、boolean の mapping ではなく、空白区切りの string です。調査範囲を限定して必要な group だけ有効にし、終了後は元の logging level に戻してください。

```bash
kubectl -n kube-system logs -l k8s-app=cilium -c cilium-agent --since=30m --tail=1000
kubectl -n kube-system logs -l k8s-app=cilium-envoy -c cilium-envoy --since=30m --tail=1000
cilium sysdump --output-filename cilium-audit
```

別の Envoy DaemonSet は `k8s-app=cilium-envoy` selector を使用します。sysdump はクラスターへのアクセスを伴う収集操作で、機密性のある設定/ログを含む場合があります。共有前に archive を確認してください。単独の host `cilium-bugtool` 実行ではありません。

## EKS 固有の指針

### ENI Mode と AWS VPC CNI Chaining

これは異なる設計です。Cilium ENI IPAM は Operator を通じて ENI/address を管理します。AWS VPC CNI chaining は AWS VPC CNI に address 割り当てを残し、独自の L7/暗号化上の制限を持ちます。対応するインストール手順を使ってください。

IPv4 ENI overlay の例です。

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
ipv4:
  enabled: true
ipv6:
  enabled: false
cluster:
  name: example-cluster
```

`eni.enabled` は AWS Operator の動作と関連 chart default を選択します。ENI garbage collection の所有者が曖昧にならないよう、一意のクラスター名を保ってください。ENI mode に汎用の `10.0.0.0/8` cluster-pool range を追加しないでください。実際のノード device と routing 要件を確認せずに masquerade interface を固定しないでください。

`enableAWSSecurityGroups` は chart value ではありません。ENI security group には、サポートされた `eni.nodeSpec.securityGroups`/`securityGroupTags`、または文書化された継承動作を使います。Kubernetes policy を AWS SecurityGroupPolicy object に自動変換するものではありません。

**一般的な ENI IPAM リファレンスは、dual-stack subnet/prefix と IAM の前提条件を含む IPv6 を Beta として記載しています。一方、1.20.3 の EKS インストールページは IPv4 のみと記載しています**。この例は意図的に IPv4 を使用し、その source 間の差異を記録しています。一般リファレンスだけを根拠に Beta feature を削除したり、検証済みの EKS IPv6 手順だと主張したりしないでください。

EKS Auto Mode と Fargate は、この代替 CNI DaemonSet のインストール経路をサポートしません。EKS Hybrid Nodes は AWS がサポートする独自の Cilium 指針と互換性一覧を持ちます。そのサポート情報を、任意の self-managed EC2 Cilium release に当てはめないでください。

### Node OS と容量

EKS は **2025年11月26日** に EKS 最適化 AL2 AMI の公開を終了しました。最後の Kubernetes series は1.32です。サポートされる AL2023 または Bottlerocket AMI を選び、実際のカーネル/アーキテクチャと Cilium feature 要件を確認してください。一般的な Linux 互換性一覧に AL2 があることは、現在の EKS AMI lifecycle support を意味しません。

instance family と size は、CPU、メモリ、ネットワーク/packet limit、ENI/IP capacity、可用性、コストの実測値から選びます。以前の固定的な m6i/c6i/r6i 推奨は、サイジングベンチマークではありません。AMD64 と Arm64 を混在させる場合は、すべての DaemonSet/workload image を両アーキテクチャで確認してください。

### IAM

サポートされるインストールの identity 方式で、Cilium Operator 専用の role を使用します。trust policy と credential access は個別に確認してください。以前の policy は `AttachNetworkInterface`、`DescribeInstanceTypes`、`DescribeRouteTables`、`CreateTags` などの必須操作を欠いており、完全な ENI allocator policy ではありません。

バージョン管理された ENI reference には基本と条件付きの API 権限が記載されています。ENI garbage collection、余分な IP の解放、instance filter、オプションの IPv6 割り当てを考慮してください。AWS service authorization がサポートする範囲で、read/list と変更権限を分けます。サポートされる変更権限は、対象の region/resource/tag に限定してください。一部の describe operation は `Resource: "*"` が必要です。したがって、wildcard だけでは設定の正しさも過剰な権限も証明されません。完全な account 固有の least-privilege policy には実際の IAM/resource context と API 検証も必要です。このガイドは、そのような policy をプロビジョニング済みとは主張しません。

## さらに読む

前提条件と全例については、[セキュリティ](./03-security.md)、[可観測性](./04-observability.md)、[Ingress/Gateway](./05-ingress-gateway.md) のガイドも参照してください。

- [Cilium 1.20.3 Helm values](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [システム要件](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/system_requirements.rst)
- [Performance tuning](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/performance/tuning.rst)
- [アップグレード手順](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/upgrade.rst)
- [アップグレードとロールバックの制約](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/operations/upgrade-warning.rst)
- [Istio integration](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/istio.rst)
- [CNI 移行](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/k8s-install-migration.rst)
- [CEC resource parser](https://github.com/cilium/cilium/blob/v1.20.3/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [ENI 割り当て、security group、権限](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/concepts/ipam/eni.rst)
- [EKS インストールの注意事項](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/installation/requirements-eks.rst)
- [EKS AL2 AMI の廃止](https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html)
- [EKS の代替 CNI サポート](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)
- [Cilium Envoy の診断](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/cmdref/cilium-dbg_envoy_admin_config.md)
- [Linux TCP sysctl](https://docs.kernel.org/networking/ip-sysctl.html)
- [Kubernetes disruption budget](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [IAM resource-level permission のトラブルシューティング](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_policies.html)
