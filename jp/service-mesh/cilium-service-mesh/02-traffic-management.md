# Cilium Service Mesh のトラフィック管理

> **レビュー基準**: Cilium 1.20.3、Gateway API 1.6.3（2026年10月16日）。Kubernetes／EKS のテストマトリクスとプラットフォーム要件については[概要](./README.md)を参照してください。

## 概要

Cilium Service Mesh のトラフィック管理は、eBPF ベースの L4 ロードバランシングと Envoy ベースの L7 ルーティングを組み合わせます。この章では、CiliumEnvoyConfig、CiliumNetworkPolicy の L7 ルール、Gateway API との統合を使った高度なトラフィック管理機能を説明します。

## トラフィック管理アーキテクチャ

![クライアントのリクエストが、サーバーに到達する前に Cilium の 3 つのトラフィック管理レイヤー（L7 Envoy HTTP ルーティング、L4 eBPF ロードバランシング、L3 eBPF IP ルーティング）を通過し、各レイヤーのその他の機能もまとめて示しています。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-02-traffic-management-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-02-traffic-management-0.html)

図はレイヤーごとに機能をまとめたものです。必須のパケット処理順序を示すものではありません。L3／L4 のみのトラフィックは Envoy を経由しないことがあり、実際の Egress／Ingress／Service の経路は設定によって異なります。

## CiliumEnvoyConfig

これらは**それぞれ独立した設定例**であり、すべてをまとめてインストールするリソースではありません。複数の例が同じ frontend Service を対象にするため、競合する Listener を避けるために設定の所有者を 1 つ選んでください。例を使うには、`l7Proxy: true`、`envoyConfig.enabled: true`、適切な kube-proxy replacement／ルーティング設定、必要な CRD を備えた Cilium の準備済みインストールが必要です。

名前を指定する各 frontend／backend Service は、適切な selector と Ready な HTTP endpoint を持ち、`default` Namespace に port **8080** で事前に存在している必要があります。Kafka と gRPC の節には、それぞれ固有の Namespace／port の前提条件があります。CEC の例は、ワークロード、Service、証明書を作成しません。

`services` はリダイレクト先の frontend を選び、その backend を同期します。`backendServices` は、他の backend の frontend トラフィックをリダイレクトせずに同期します。EDS Cluster リソースは引き続き存在する必要があります。Cilium は省略された Listener のアドレス／xDS ソースを意図的に補います。Kubernetes がリソースを受け付けただけでは不十分です。Agent／Envoy のエラーを調べ、実際のリクエストを検証してください。所有関係と検証範囲は[アーキテクチャの章](./01-architecture.md)を参照してください。

### 基本構造

CiliumEnvoyConfig は、特定の Service 向けの Envoy 設定を定義します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: my-service-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: backend-v1
    namespace: default
  - name: backend-v2
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: my-service-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: my-service-listener
          route_config:
            name: my-service-listener-routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  weighted_clusters:
                    clusters:
                    - name: default/backend-v1
                      weight: 50
                    - name: default/backend-v2
                      weight: 50
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/backend-v1
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/backend-v2
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

この完全な例は、明示的に名前を指定した 2 つの backend 間にリクエストを分散します。Listener、HTTP Route、EDS Cluster はそれぞれ別の構成要素です。backend Service を列挙するだけでは Cluster は定義されません。

### HTTP ルーティング

#### パスベースのルーティング

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: path-routing
  namespace: default
spec:
  services:
  - name: api-gateway
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: users-service
    namespace: default
  - name: orders-service
    namespace: default
  - name: products-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: api-gateway-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-gateway
          codec_type: AUTO
          route_config:
            name: api_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /users
                route:
                  cluster: default/users-service
              - match:
                  path_separated_prefix: /orders
                route:
                  cluster: default/orders-service
              - match:
                  path_separated_prefix: /products
                route:
                  cluster: default/products-service
              - match:
                  prefix: /
                direct_response:
                  status: 404
                  body:
                    inline_string: Not Found
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/orders-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/products-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/users-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Envoy はこれらの Route を記載順に評価します。`path_separated_prefix` は `/users` と `/users/123` に一致しますが、`/users-old` には一致しません。最後の `/` ルールがフォールバックです。任意の文字列 prefix とは挙動が異なります。

#### ヘッダーベースのルーティング

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-routing
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-v1
    namespace: default
  - name: api-v2
    namespace: default
  - name: api-beta
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-routing-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: header_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: X-API-Version
                    string_match:
                      exact: v2
                route:
                  cluster: default/api-v2
              - match:
                  prefix: /
                  headers:
                  - name: X-Beta-User
                    string_match:
                      exact: 'true'
                route:
                  cluster: default/api-beta
              - match:
                  prefix: /
                route:
                  cluster: default/api-v1
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-beta
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-v1
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-v2
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

最初に一致したルールが選ばれます。両方のヘッダーを持つリクエストは v2 を選択します。クライアントが設定できる version／beta ヘッダーはルーティングのヒントであり、その backend へのアクセスをユーザーに認可する証明ではありません。

#### メソッドベースのルーティング

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: method-routing
  namespace: default
spec:
  services:
  - name: rest-api
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: read-service
    namespace: default
  - name: write-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: method-routing-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: rest-api
          route_config:
            name: method_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(GET|HEAD)$
                route:
                  cluster: default/read-service
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(POST|PUT|DELETE|PATCH)$
                route:
                  cluster: default/write-service
              - match:
                  prefix: /
                direct_response:
                  status: 405
                response_headers_to_add:
                - header:
                    key: allow
                    value: GET, HEAD, POST, PUT, DELETE, PATCH
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/read-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/write-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

GET／HEAD は読み取り用 Service を選び、POST／PUT／DELETE／PATCH は書き込み用 Service を選びます。それ以外のメソッドには 405 が返ります。必要な OPTIONS／CORS やアプリケーション固有の挙動は、意図を明確にして追加してください。書き込みを専用 backend にルーティングしても、それだけで認可や冪等性が実装されるわけではありません。

## L7 トラフィックポリシー

### CiliumNetworkPolicy の L7 ルール

CiliumNetworkPolicy は L7 レベルできめ細かなトラフィック制御を可能にします。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: l7-http-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: backend-api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: frontend
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: ^GET$
          path: ^/api/users/.*$
        - method: ^GET$
          path: ^/api/products/.*$
        - method: ^POST$
          path: ^/api/orders$
        - method: ^GET$
          path: ^/api/admin/.*$
          headerMatches:
          - name: X-API-Version
            value: v1
```

各ルールは独立した許可条件であり、ヘッダー条件が適用されるのは admin path のルールだけです。`X-API-Version: v1` は厳密なルーティング／バージョン条件であり、管理者の認証情報ではありません。ユーザー認証と認可はアプリケーションで実施してください。このポリシーは指定した Namespace からの Ingress トラフィックを選択します。他の適用ポリシーがアクセス許可を広げる場合があります。

### 各種プロトコルのサポート

#### Kafka: ネットワーク境界と Broker ACL

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-l4-policy
  namespace: kafka
spec:
  endpointSelector:
    matchLabels:
      k8s:app: kafka-broker
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: kafka-producer
        k8s:io.kubernetes.pod.namespace: kafka
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
  - fromEndpoints:
    - matchLabels:
        k8s:app: kafka-consumer
        k8s:io.kubernetes.pod.namespace: kafka
    toPorts:
    - ports:
      - port: '9092'
        protocol: TCP
```

Cilium 1.20.3 の L7 ポリシー API がサポートするのは HTTP と DNS です。旧 `rules.kafka` API はなく、リリース済み CRD はこの Kafka rules オブジェクトを拒否します。L7 ルールを削除すると L4 の許可だけが残り、Topic 単位の認可は行われません。この置き換え例が許可するのは、列挙されたクライアントから事前設定済み Broker Listener の TCP 9092 への接続だけです。Topic、Consumer Group、操作の認可には Kafka TLS／SASL と Broker ACL を別途設定してください。このネットワークポリシーでは Produce と Fetch を区別できません。

#### DNS L7 ポリシー

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: web-app
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: UDP
      - port: '53'
        protocol: TCP
      rules:
        dns:
        - matchPattern: '*.example.com'
        - matchPattern: api.external-service.io
        - matchName: database.internal.svc.cluster.local
```

この例で許可されるのは、選択されたクラスター DNS Resolver 宛ての UDP／TCP による **DNS Query のみ**です。返されたアドレスへの HTTPS／データベース接続は許可されません。意図する宛先について、別途 `toFQDNs`／endpoint と port のルールを追加してください。`*.example.com` は apex の `example.com` や任意の階層のサブドメインには一致しません。Resolver の search list による Query も考慮が必要です。NodeLocal DNS には、別途検証した宛先ルールが必要です。名前を制限しても、データ流出、DoH、許可済みドメインの悪用を防げるとは限りません。

#### gRPC L7 ポリシー

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: grpc-l7-policy
  namespace: default
spec:
  endpointSelector:
    matchLabels:
      k8s:app: grpc-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:app: grpc-client
        k8s:io.kubernetes.pod.namespace: default
    toPorts:
    - ports:
      - port: '50051'
        protocol: TCP
      rules:
        http:
        - method: ^POST$
          path: ^/myapp\.UserService/GetUser$
        - method: ^POST$
          path: ^/myapp\.UserService/ListUsers$
        - method: ^POST$
          path: ^/myapp\.OrderService/.*$
```

これらの HTTP/2 ルールは、gRPC の `POST /package.Service/Method` パスに一致します。package 名のピリオドはエスケープされ、式にはアンカーが付いています。対応していて検査可能な HTTP/2 パスを前提とします。暗号化されたアプリケーショントラフィックには、それに応じた TLS 設定が必要です。Health／Reflection や他のメソッドは暗黙に許可されず、HTTP ポリシーで protobuf メッセージ内部のフィールドを認可することもできません。

## ロードバランシング

### L4 ロードバランシング（eBPF）

eBPF ベースの L4 ロードバランシングは kube-proxy を置き換えます。

```yaml
kubeProxyReplacement: true
k8sServiceHost: <reachable-api-server-host>
k8sServicePort: 6443
loadBalancer:
  algorithm: maglev
  mode: snat
nodePort:
  enableHealthCheck: true
```

Bootstrap 時に API endpoint へ到達できる必要があります。実際の port（EKS では通常 443）を使ってください。選択したプラットフォームの IPAM／ルーティング設定を維持してください。`nodePort.enableHealthCheck` が Chart のキーです。以前の `loadBalancer.healthCheckNodePort` は設定になりませんでした。`loadBalancer.serviceTopology` はトポロジー対応ルーティングの設定であり、ClientIP セッションアフィニティとは別です。DSR の Dispatch／Routing の組み合わせは別途設計が必要です。文書化された Dispatch の選択肢は `opt` と `geneve` であり、`ipip` ではありません。[アーキテクチャの解説](./01-architecture.md#kube-proxy-replacement)も参照してください。

#### Maglev ハッシュ

Maglev は、該当する外部トラフィックのフローキーを Lookup Table 経由で backend に割り当てます。backend の集合が変わったときの再割り当てを最小限にしますが、削除された backend 上のセッションを維持したり、`Service.spec.sessionAffinity: ClientIP` の代わりになったりするものではありません。

Cilium 1.20.3 の eBPF Maglev テーブルサイズの既定値は **16,381** です。対応するサイズには **65,521** が含まれます。一方、**65,537** は後述する Envoy MAGLEV の例で使う値であり、Cilium の `maglev.tableSize` ではサポートされません。すべてのノードで一貫した設定が必要です。Socket レベルの東西方向の Service 変換には、この Maglev 経路は適用されません。

### L7 ロードバランシング（Envoy）

L7 ロードバランシングは Envoy が提供します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: l7-load-balancing
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: l7-load-balancer
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: l7-load-balancer
          route_config:
            name: l7-load-balancer-routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: /health
        expected_statuses:
        - start: 200
          end: 300
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 1000
        max_pending_requests: 1000
        max_requests: 1000
        max_retries: 3
```

有効な `/health` Probe、受動的な Outlier Detection、Circuit Breaker による容量上限は、それぞれ別の仕組みです。HTTP ヘルスチェックの範囲は `[200, 300)` なので 299 が含まれます。backend がヘルスエンドポイントを実装し、ポリシーで Probe のパスを許可する必要があります。Outlier Ejection は、すべてのリクエストが障害 endpoint を回避する保証ではありません。`circuit_breakers.thresholds` の `max_retries` は、同時に使われるリトライ用リソースの上限であり、リクエストごとのリトライ回数ではありません。

#### ロードバランシング・アルゴリズムの選択肢

以下の Cluster 断片から**1 つを選択**してください。相互に置き換えて使う選択肢であり、`lb_policy` キーを繰り返す YAML マッピングではありません。リクエストにアプリケーションキーを使って一貫した選択をする場合、RING_HASH／MAGLEV には適切な Route の `hash_policy` も必要です。ハッシュが渡されない場合、ランダムキーにフォールバックすることがあります。Envoy の L7 MAGLEV テーブルは Cilium の eBPF Maglev テーブルとは別です。

```yaml
lb_policy: ROUND_ROBIN
```

```yaml
lb_policy: LEAST_REQUEST
least_request_lb_config:
  choice_count: 2
```

```yaml
lb_policy: RANDOM
```

```yaml
lb_policy: RING_HASH
ring_hash_lb_config:
  hash_function: XX_HASH
  minimum_ring_size: 1024
  maximum_ring_size: 8388608
```

```yaml
lb_policy: MAGLEV
maglev_lb_config:
  table_size: 65537
```

## トラフィック分割（カナリアデプロイ）

### 重みベースのトラフィック分割

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: canary-deployment
  namespace: default
spec:
  services:
  - name: frontend
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: frontend-stable
    namespace: default
  - name: frontend-canary
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: canary-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: frontend
          route_config:
            name: canary_routes
            virtual_hosts:
            - name: frontend
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  weighted_clusters:
                    clusters:
                    - name: default/frontend-stable
                      weight: 90
                    - name: default/frontend-canary
                      weight: 10
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/frontend-canary
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/frontend-stable
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

重み 90 と 10 は相対的な選択確率を表し、10 リクエストごとの正確な件数や、ユーザー／セッションごとの選択を保証するものではありません。現在の Envoy は重みの合計を使い、非推奨の `total_weight` フィールドは省略されています。これはトラフィックの選択だけを行い、自動のヘルス分析、昇格、ロールバックのループはありません。

### ヘッダーベースのカナリア

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-canary
  namespace: default
spec:
  services:
  - name: api
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-stable
    namespace: default
  - name: api-canary
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-canary-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api
          route_config:
            name: header_canary_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: X-Canary
                    string_match:
                      exact: 'true'
                route:
                  cluster: default/api-canary
              - match:
                  prefix: /
                route:
                  cluster: default/api-stable
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-canary
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-stable
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

正確に `X-Canary: true` の値を持つ場合だけカナリアが選択され、それ以外は stable が選択されます。認証済みの境界で制御されない限り、このヘッダーを信頼できない入力として扱ってください。stable／canary 間のアプリケーション状態と互換性要件をロールアウト計画に含めてください。

## リトライとタイムアウト

### リトライの設定 {#retry-configuration}

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: retry-config
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: api-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: retry-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: retry_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      exact: GET
                route:
                  cluster: default/api-backend
                  timeout: 7s
                  retry_policy:
                    retry_on: 5xx,reset,connect-failure
                    num_retries: 2
                    per_try_timeout: 2s
                    retry_back_off:
                      base_interval: 0.025s
                      max_interval: 0.25s
                    retriable_request_headers:
                    - name: :method
                      string_match:
                        exact: GET
              - match:
                  prefix: /
                route:
                  cluster: default/api-backend
                  timeout: 7s
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          early_header_mutation_extensions:
          - name: envoy.http.early_header_mutation.header_mutation
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.http.early_header_mutation.header_mutation.v3.HeaderMutation
              mutations:
              - remove: x-envoy-retry-on
              - remove: x-envoy-retry-grpc-on
              - remove: x-envoy-max-retries
              - remove: x-envoy-hedge-on-per-try-timeout
              - remove: x-envoy-retriable-header-names
              - remove: x-envoy-retriable-status-codes
              - remove: x-envoy-upstream-rq-timeout-ms
              - remove: x-envoy-upstream-rq-per-try-timeout-ms
              - remove: x-envoy-expected-rq-timeout-ms
              - remove: x-envoy-upstream-stream-duration-ms
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

リトライの対象は GET リクエストのみで、**追加試行は最大 2 回**です。試行ごとのタイムアウトは 2 秒、Route のタイムアウトは 7 秒です。試行ごとのタイムアウトには最初の試行も含まれ、リトライ間の待ち時間ではありません。バックオフは別に設定します。GET 以外のフォールバックでは `num_retries: 0` を明示しています。

Early Header Mutation 拡張機能は、ルーティングとタイムアウト計算の前に Envoy のリトライ／タイムアウト上書きヘッダーを削除します。Cilium 1.20.3 の Proxy イメージにはこの拡張機能がコンパイル済みですが、通常の HTTP `header_mutation` と Lua Filter はそのビルドで有効になっていません。以前の `previous_priorities` リトライ優先度拡張機能も、このイメージでは利用できません。すべての上流 Envoy 拡張機能が使用できるとは想定しないでください。

この例は、GET 操作を安全に繰り返せる HTTP endpoint に使ってください。アプリケーション／クライアントや別の Proxy が独自に再試行することはあります。アプリケーションがレビュー済みの冪等性機構を提供しない限り、書き込みは単一試行にしてください。`retriable_headers` は **上流レスポンス**のヘッダーに関する設定で、`retry_on: retriable-headers` と合わせて参照されます。一方の `retriable_request_headers` は、リトライ対象になるリクエストを制限します。両者は置き換え可能ではありません。`retriable-4xx` はすべての 4xx を再試行する設定ではありません。

### タイムアウトの設定

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: timeout-config
  namespace: default
spec:
  services:
  - name: slow-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: timeout-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: slow-service
          common_http_protocol_options:
            idle_timeout: 300s
            headers_with_underscores_action: REJECT_REQUEST
          stream_idle_timeout: 60s
          request_timeout: 0s
          route_config:
            name: timeout_routes
            virtual_hosts:
            - name: slow-service
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /long-running
                route:
                  cluster: default/slow-service
                  timeout: 300s
                  idle_timeout: 300s
                  retry_policy:
                    num_retries: 0
              - match:
                  path_separated_prefix: /stream
                route:
                  cluster: default/slow-service
                  timeout: 0s
                  idle_timeout: 60s
                  retry_policy:
                    num_retries: 0
              - match:
                  prefix: /
                route:
                  cluster: default/slow-service
                  timeout: 60s
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
          early_header_mutation_extensions:
          - name: envoy.http.early_header_mutation.header_mutation
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.http.early_header_mutation.header_mutation.v3.HeaderMutation
              mutations:
              - remove: x-envoy-retry-on
              - remove: x-envoy-retry-grpc-on
              - remove: x-envoy-max-retries
              - remove: x-envoy-hedge-on-per-try-timeout
              - remove: x-envoy-retriable-header-names
              - remove: x-envoy-retriable-status-codes
              - remove: x-envoy-upstream-rq-timeout-ms
              - remove: x-envoy-upstream-rq-per-try-timeout-ms
              - remove: x-envoy-expected-rq-timeout-ms
              - remove: x-envoy-upstream-stream-duration-ms
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/slow-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

特定パスの Route はフォールバックより先に評価されます。`/long-running` には 300 秒の Route／Stream Idle 予算が適用されます。`/stream` は Route 全体のレスポンスタイムアウトだけを無効にし、60 秒の Idle 上限は維持します。それ以外のパスでは 60 秒の Route タイムアウトが使われます。`/streaming` は `/stream` に一致しません。

Upstream Cluster の `connect_timeout` は接続確立の上限です。`common_http_protocol_options.idle_timeout` は Downstream 接続の Idle 上限です。HCM の `request_timeout` は backend 処理ではなくクライアントリクエストの受信を制限します。この例ではストリーミングリクエストに対して無効です。公開サービスには、これに対応する Edge／Header／Body／Connection 制御が必要です。ゼロ以外の Stream Idle タイムアウト、クライアントの Deadline、インフラストラクチャ上の制限、接続切断によって Stream が終了することがあります。`timeout: 0s` は接続が無期限に続く保証ではありません。

## レート制限

### ローカルレート制限

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: local-ratelimit
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: ratelimit-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: ratelimit_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 1000
                tokens_per_fill: 100
                fill_interval: 1s
              status:
                code: TooManyRequests
              filter_enabled:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              filter_enforced:
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              enable_x_ratelimit_headers: DRAFT_VERSION_03
              local_rate_limit_per_downstream_connection: false
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

この Token Bucket の Burst 容量は 1,000 で、トークンは **Envoy プロセスごと**に 1 秒あたり 100 個補充され、各プロセスの Worker 間で共有されます。クラスター全体のクォータではありません。Enable／Enforce の割合は両方とも明示されています。`enable_x_ratelimit_headers: DRAFT_VERSION_03` は Filter が提供する実際の limit／remaining／reset ヘッダーを要求します。独自の Dynamic Metadata キーを作っても、残りトークン数を確実に取得できません。

### Route ごとのレート制限

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: per-route-ratelimit
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: per-route-ratelimit-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: ratelimit_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /auth
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: auth_rate_limiter
                    token_bucket:
                      max_tokens: 10
                      tokens_per_fill: 5
                      fill_interval: 60s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
              - match:
                  path_separated_prefix: /search
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: search_rate_limiter
                    token_bucket:
                      max_tokens: 100
                      tokens_per_fill: 50
                      fill_interval: 1s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
                typed_per_filter_config:
                  envoy.filters.http.local_ratelimit:
                    '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
                    stat_prefix: default_rate_limiter
                    token_bucket:
                      max_tokens: 1000
                      tokens_per_fill: 100
                      fill_interval: 1s
                    filter_enabled:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    filter_enforced:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    local_rate_limit_per_downstream_connection: false
                    enable_x_ratelimit_headers: DRAFT_VERSION_03
          http_filters:
          - name: envoy.filters.http.local_ratelimit
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
              stat_prefix: http_local_rate_limiter
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

各 Route では、Enable／Enforce の割合を含む完全な Local Rate Limit Override を指定します。auth は Burst 10、60 秒ごとに 5 個を補充します。search は Burst 100、1 秒ごとに 50 個を補充します。default は Burst 1,000、1 秒ごとに 100 個を補充します。これらはプロセス内の Bucket であり、ユーザーごとの上限ではありません。有効化／適用割合を設定しない Bucket は、既定で実効的な強制が行われません。

## URL 書き換えとヘッダー操作

### URL の書き換え

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: url-rewrite
  namespace: default
spec:
  services:
  - name: api-gateway
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: users-service
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: rewrite-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-gateway
          route_config:
            name: rewrite_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              routes:
              - match:
                  path_separated_prefix: /api/v1/users
                route:
                  cluster: default/users-service
                  prefix_rewrite: /users
              - match:
                  safe_regex:
                    google_re2: {}
                    regex: ^/v([0-9]+)/(.*)$
                route:
                  cluster: default/users-service
                  regex_rewrite:
                    pattern:
                      google_re2: {}
                      regex: ^/v([0-9]+)/([^?]*)(\?.*)?$
                    substitution: /api/v\1/\2\3
              - match:
                  path: /legacy
                route:
                  cluster: default/users-service
                  host_rewrite_literal: legacy.internal.svc.cluster.local
                  prefix_rewrite: /
              - match:
                  prefix: /legacy/
                route:
                  cluster: default/users-service
                  host_rewrite_literal: legacy.internal.svc.cluster.local
                  prefix_rewrite: /
              - match:
                  prefix: /
                direct_response:
                  status: 404
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/users-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

`/api/v1/users/123` は `/users/123` になり、`/v2/users?active=1` は既存の Query String を保持したまま `/api/v2/users?active=1` になります。Root／Child の個別の旧式 Match によって、意図しない二重スラッシュを避けています。Host の書き換えは、選択された Cluster に送る HTTP Authority を変更します。それだけで別の backend Service を解決するものではありません。

### ヘッダー操作

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: header-manipulation
  namespace: default
spec:
  services:
  - name: api-service
    namespace: default
    ports:
    - 8080
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: header-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: api-service
          route_config:
            name: header_routes
            virtual_hosts:
            - name: api
              domains:
              - '*'
              request_headers_to_add:
              - header:
                  key: X-Forwarded-By
                  value: cilium-envoy
                append_action: OVERWRITE_IF_EXISTS_OR_ADD
              response_headers_to_add:
              - header:
                  key: X-Served-By
                  value: cilium-service-mesh
                append_action: OVERWRITE_IF_EXISTS_OR_ADD
              response_headers_to_remove:
              - server
              - x-powered-by
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/api-service
                request_headers_to_add:
                - header:
                    key: X-Request-Start
                    value: '%START_TIME(%s.%3f)%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                - header:
                    key: X-Envoy-Original-Path
                    value: '%REQ(:PATH)%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                response_headers_to_add:
                - header:
                    key: X-Response-Time
                    value: '%RESPONSE_DURATION%ms'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
                - header:
                    key: X-Upstream-Host
                    value: '%UPSTREAM_HOST%'
                  append_action: OVERWRITE_IF_EXISTS_OR_ADD
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/api-service
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Route のヘッダー変更は、`RouteAction` の中ではなく `route` アクションの隣に置きます。レスポンス時間 Formatter は Response Header の作成時に評価され、まだ Stream されていない Body の完了時間は報告できません。Upstream Host の診断情報は内部ルーティング情報を公開するため、こうした診断ヘッダーは適切なテスト／内部インターフェイスだけで使ってください。

## Gateway API との統合

### GatewayClass と Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium
spec:
  controllerName: io.cilium/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: api-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Same
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: api-gateway-tls
    allowedRoutes:
      namespaces:
        from: Same
```

Gateway API 1.6.3 の CRD と、Cilium の `gatewayAPI.enabled: true`、`kubeProxyReplacement: true`、`l7Proxy: true` が前提条件です。示されている GatewayClass はコントローラーとの紐付けを表します。インストールツールがすでに `cilium` を所有している場合は、競合する所有者を作らず既存のものを使ってください。ホスト名に対応する証明書を含む、有効な TLS Secret `api-gateway-tls` を `default` に準備してください。LoadBalancer の公開方法とアドレスはプラットフォームによって異なります。GatewayClass／Gateway の Accepted／Programmed 条件と Listener 参照を検証してください。このマニフェストだけでは、完全な EKS 公開設計は構築されません。

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-routes
  namespace: default
spec:
  parentRefs:
  - name: api-gateway
    namespace: default
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /users
    backendRefs:
    - name: users-service
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /orders
    backendRefs:
    - name: orders-service
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /
      headers:
      - name: X-API-Version
        value: v2
    backendRefs:
    - name: api-v2
      port: 8080
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api-stable
      port: 8080
      weight: 90
    - name: api-canary
      port: 8080
      weight: 10
```

この Route が接続するのは `https` Listener だけです。Frontend Listener の port 80／443 は backend Service の port 8080 とは別です。HTTP Listener は自動で HTTPS へリダイレクトしません。必要であれば HTTP 用に別の Listener Route を設定してください。Gateway API の Match には仕様で定めた優先順位（例: Path の具体性、Header Match）があり、すべてのルールを YAML の記載順だけで評価するとは限りません。Accepted／ResolvedRefs と実際の Listener 状態を確認してください。

### HTTPRoute の高度な機能

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: advanced-routes
  namespace: default
spec:
  parentRefs:
  - name: api-gateway
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: RequestHeaderModifier
      requestHeaderModifier:
        set:
        - name: X-Doc-Route
          value: api-v1
        remove:
        - X-Internal-Header
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: X-Frame-Options
          value: DENY
        - name: X-Content-Type-Options
          value: nosniff
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /v1
    backendRefs:
    - name: api-service
      port: 8080
  - matches:
    - path:
        type: Exact
        value: /old-endpoint
      method: GET
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        hostname: new.example.com
        path:
          type: ReplaceFullPath
          replaceFullPath: /new-endpoint
        statusCode: 301
  hostnames:
  - api.example.com
```

ここにある Header 値は、移植可能な Gateway API のリテラル設定です。API は Envoy の `%REQ(...)%` テンプレートを定義していません。適切なアプリケーション／Proxy レイヤーで Request ID を保持／生成してください。実際の Transport に関係なく `X-Forwarded-Proto: https` を強制しないでください。URLRewrite はクライアントをリダイレクトせずに Upstream Path を変更します。旧式の Redirect は GET だけに一致します。301 はクライアントによってメソッドを変更することがあるため、任意の書き込みを暗黙にリダイレクトしないでください。

## トラフィックミラーリング

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: traffic-mirror
  namespace: default
spec:
  services:
  - name: production-service
    namespace: default
    ports:
    - 8080
  backendServices:
  - name: production-backend
    namespace: default
  - name: shadow-backend
    namespace: default
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: mirror-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: production-service
          route_config:
            name: mirror_routes
            virtual_hosts:
            - name: production
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                  headers:
                  - name: :method
                    string_match:
                      safe_regex:
                        google_re2: {}
                        regex: ^(GET|HEAD)$
                route:
                  cluster: default/production-backend
                  request_mirror_policies:
                  - cluster: default/shadow-backend
                    runtime_fraction:
                      default_value:
                        numerator: 100
                        denominator: HUNDRED
                    trace_sampled: false
              - match:
                  prefix: /
                route:
                  cluster: default/production-backend
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/production-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/shadow-backend
    connect_timeout: 5s
    type: EDS
    lb_policy: ROUND_ROBIN
```

Mirror が受信するのは、**選択された GET／HEAD** リクエストの 100% です。他のメソッドのフォールバックには Mirror Policy がありません。合成トラフィックまたは承認済みの読み取り専用トラフィックと、本番状態を変更したり外部副作用を起こしたりできない隔離済みの Shadow Backend でテストしてください。Mirror はリソースを消費し、リクエストデータを複製します。別途設定しない限り Authority に `-shadow` が付加される場合があります。Mirror のレスポンスは呼び出し元に返されませんが、ユーザーへの影響がゼロになる保証ではありません。

## 次のステップ

- [セキュリティ](./03-security.md): 認証、暗号化、L7 ネットワークポリシーを確認する
- [オブザーバビリティ](./04-observability.md): Hubble でトラフィックを監視する
- [Ingress と Gateway](./05-ingress-gateway.md): 外部トラフィックを管理する

## 参考資料

- [Cilium 1.20.3 L7 ポリシー](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer7.rst)
- [Cilium L3／FQDN ポリシー](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/security/policy/layer3.rst)
- [Cilium CEC の例](https://github.com/cilium/cilium/blob/v1.20.3/examples/kubernetes/servicemesh/envoy/envoy-traffic-management-test.yaml)
- [Cilium Envoy Parser](https://github.com/cilium/cilium/blob/v1.20.3/pkg/ciliumenvoyconfig/cec_resource_parser.go)
- [Cilium kube-proxy replacement](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/kubernetes/kubeproxy-free.rst)
- [Cilium Gateway API のインストール](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/gateway-api/installation.rst)
- [Cilium 1.20.3 Chart の値](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Cilium Proxy の拡張機能一覧](https://github.com/cilium/proxy/blob/766ccfb37260a43e9d228837aa84ce3faf9f64e7/envoy_build_config/extensions_build_config.bzl)
- [Envoy 1.38.6 Routing API](https://github.com/envoyproxy/envoy/blob/v1.38.6/api/envoy/config/route/v3/route_components.proto)
- [Envoy のリトライ実装](https://github.com/envoyproxy/envoy/blob/v1.38.6/source/common/router/retry_state_impl.cc)
- [Envoy Router のタイミングとヘッダー処理](https://github.com/envoyproxy/envoy/blob/v1.38.6/source/common/router/router.cc)
- [Envoy Early Header Mutation](https://github.com/envoyproxy/envoy/blob/v1.38.6/api/envoy/extensions/http/early_header_mutation/header_mutation/v3/header_mutation.proto)
- [Envoy Local Rate Limit](https://github.com/envoyproxy/envoy/blob/v1.38.6/api/envoy/extensions/filters/http/local_ratelimit/v3/local_rate_limit.proto)
- [Envoy のタイムアウト定義](https://github.com/envoyproxy/envoy/blob/v1.38.6/docs/root/faq/configuration/timeouts.rst)
- [Gateway API 1.6.3 HTTPRoute 仕様](https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.3/apis/v1/httproute_types.go)
- [Kafka Broker ACL](https://kafka.apache.org/41/security/authorization-and-acls/)
