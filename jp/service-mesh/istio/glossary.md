# Istio 用語集

> **レビュー対象バージョン**: Istio 1.31.0
> **最終更新**: September 13, 2026

この用語集では、Istio と Service Mesh に関連する主要な用語を、グループ化したリファレンスセクションとして整理しています。

> **参照言語:** 以下の Architecture および DestinationRule セクションのリンクは、メンテナンスされている英語版ガイドを使用しています。これらのリンクは、各ロケールの翻訳がまだ同期されていない箇所について、最新のリファレンスを提供します。

## 目次

- [A-C](#a-c)
- [D-F](#d-f)
- [G-I](#g-i)
- [J-L](#j-l)
- [M-O](#m-o)
- [P-R](#p-r)
- [S-U](#s-u)
- [V-Z](#v-z)

---

## A-C

### AuthorizationPolicy

選択したワークロードまたは対象リソースに対して、ALLOW、DENY、CUSTOM、AUDIT の動作を定義する Istio のセキュリティポリシーです。認証と認可は別個のものであり、waypoint のポリシーでは targetRefs を使用します。

### Control Plane

設定、ディスカバリー、アイデンティティ管理を担うレイヤーで、istiod として実装されています。アプリケーションのペイロードは istiod を経由するのではなく、データプレーンのプロキシを流れます。

### Ambient Mode

Istio 1.18 で alpha として初めて提供され、Istio 1.24 以降で一般提供 (GA) となったデータプレーンモードで、Sidecar Proxy なしで Service Mesh の機能を提供します。

**特徴**:
- Sidecar コンテナが不要
- ノードレベルで ztunnel を使用
- リソース効率の向上
- L4 機能と L7 機能の分離

**関連ドキュメント**: [Ambient Mode](advanced/01-ambient-mode.md)

---

### Certificate Authority (CA)

サービス間の mTLS 通信に使用する証明書を発行・管理する機関です。

**Istio における役割**:
- Istiod の Citadel 機能が CA の役割を担う
- SPIFFE ID に基づいて証明書を発行
- 証明書の自動更新 (デフォルト TTL: 24 時間)

**関連用語**: [Citadel](#citadel), [SPIFFE](#spiffe-secure-production-identity-framework-for-everyone), [mTLS](#mtls-mutual-tls)

---

### Circuit Breaker

障害が発生したサービスへのリクエストを遮断し、障害がシステム全体に伝播することを防ぐパターンです。

**動作の仕組み**:
1. **Closed**: 正常動作
2. **Open**: 連続した失敗の後にリクエストを遮断
3. **Half-Open**: 一定時間の経過後に一部のリクエストを許可

**Istio での実装**: コネクションプールのサーキットブレイキングとエンドポイント単位の outlier ejection は、この 3 状態のステートマシンをそのまま公開するものではありません。
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-1
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**関連ドキュメント**: [Circuit Breaker](traffic-management/07-circuit-breaker.md)

---

### Citadel

Istio 1.4 まで独立して存在していたセキュリティコンポーネントです。現在は Istiod に統合されています。

**主な機能**:
- Certificate Authority (CA) の管理
- SPIFFE ID の発行と管理
- X.509 証明書の生成と更新

**現在の状況**: Istio 1.5 以降では Istiod 内部の機能として存在します

**関連用語**: [Istiod](#istiod), [Certificate Authority](#certificate-authority-ca)

---

### CDS (Cluster Discovery Service)

Envoy がアップストリームサービス (クラスター) の設定を動的に受け取るための xDS API の 1 つです。

**提供される情報**:
- クラスター名と種別
- ロードバランシングポリシー
- ヘルスチェック設定
- Circuit Breaker 設定
- TLS 設定

**関連用語**: [xDS](#xds-discovery-service), [Envoy](#envoy-proxy)

---

## D-F

### Data Plane

Service Mesh において実際のトラフィックを処理するレイヤーです。

**Istio の Data Plane**:
- Envoy サイドカー、または ambient の ztunnel と任意の L7 waypoint
- メッシュに参加させたトラフィックを処理する。除外設定やプロトコルの制限が適用される
- mTLS の暗号化/復号
- メトリクスの収集

**関連用語**: [Control Plane](#control-plane), [Envoy](#envoy-proxy)

---

### DestinationRule

VirtualService によってルーティングされたトラフィックに対するポリシーを定義する Istio の CRD です。

**主な機能**:
- Subset の定義 (バージョン、リージョンなど)
- ロードバランシングポリシー
- Connection Pool の設定
- Circuit Breaker の設定
- TLS 設定

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
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

**関連ドキュメント**: [DestinationRule](traffic-management/03-destination-rule.md)

---

### eBPF (Extended Berkeley Packet Filter)

Linux カーネル内でプログラムを安全に実行できるようにする技術です。

Istio は、Cilium のような eBPF ベースのプライマリ CNI と共存できます。Istio CNI はリダイレクトを設定する別個のチェーン型プラグイン/ノードエージェントであり、ambient は eBPF を必要とせず、プライマリ CNI を置き換えるものでもありません。

**利点**:
- 低いオーバーヘッド
- カーネルレベルでの処理
- 動的なプログラミングが可能

**関連用語**: [Ambient Mode](#ambient-mode), [iptables](#iptables)

---

### EDS (Endpoint Discovery Service)

クラスター内の実際のエンドポイント (Pod IP) を動的に提供する xDS API の 1 つです。

**提供される情報**:
- エンドポイントの IP アドレスとポート
- ヘルス状態
- ロードバランシングの重み
- ローカリティ情報

**例**:
```json
{
  "cluster_name": "outbound|9080||reviews",
  "endpoints": [
    {
      "lb_endpoints": [
        {"endpoint": {"address": {"socket_address": {"address": "10.244.1.5", "port_value": 9080}}}},
        {"endpoint": {"address": {"socket_address": {"address": "10.244.2.8", "port_value": 9080}}}}
      ]
    }
  ]
}
```

**関連用語**: [xDS](#xds-discovery-service), [CDS](#cds-cluster-discovery-service)

---

### Envoy Proxy

Istio の Data Plane を構成する高性能な L7 プロキシです。

**歴史**:
- 2016 年に Lyft の Matt Klein によって開発
- 2017 年に CNCF Incubating プロジェクト
- 2018 年に CNCF Graduated プロジェクト

**主な特徴**:
- C++ で書かれた高性能プロキシ
- xDS API による動的な設定
- HTTP/1.1、HTTP/2、gRPC のサポート
- 豊富なオブザーバビリティ

**コンポーネント**:
- Listeners: ポートのリスニング
- Filters: リクエスト/レスポンスの処理
- Routers: ルーティングの決定
- Clusters: アップストリームサービス

**関連ドキュメント**: [Architecture - Envoy Proxy](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#data-plane-envoy-proxy)

---

## G-I

### Galley

Istio 1.4 まで独立して存在していた設定検証コンポーネントです。現在は Istiod に統合されています。

**主な機能**:
- Istio 設定の検証
- Kubernetes リソースの処理
- 設定のデプロイ前のエラーチェック

**現在の状況**: Istio 1.5 以降では Istiod 内部の機能として存在します

**関連用語**: [Istiod](#istiod)

---

### Gateway

Service Mesh に入ってくる外部トラフィックのエントリーポイントを定義する Istio の CRD です。

**種類**:
1. **Ingress Gateway**: 外部から内部へのトラフィック
2. **Egress Gateway**: 内部から外部へのトラフィック

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: my-gateway
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "example.com"
```

**関連ドキュメント**: [Gateway and VirtualService](traffic-management/01-gateway-virtualservice.md)

---

### gRPC

Google が開発した高性能な RPC (Remote Procedure Call) フレームワークです。

**Istio との関係**:
- xDS API は gRPC ベース
- Istiod と Envoy 間の通信に使用
- HTTP/2 ベース (多重化をサポート)

**利点**:
- 双方向ストリーミング
- 低レイテンシー
- Protocol Buffers を使用

**関連用語**: [xDS](#xds-discovery-service)

---

### Identity

Service Mesh 内におけるワークロードのアイデンティティ (識別情報) を表します。

**Istio の Identity**:
- SPIFFE ID 形式を使用
- Kubernetes ServiceAccount に基づく
- X.509 証明書によって証明される

**例**:
```
spiffe://cluster.local/ns/default/sa/reviews
```

**関連用語**: [SPIFFE](#spiffe-secure-production-identity-framework-for-everyone), [mTLS](#mtls-mutual-tls)

---

### iptables

Linux でネットワークトラフィックを制御するファイアウォールツールです。

**Istio における役割**:
- istio-init または Istio CNI ノードエージェントがトラフィックのリダイレクトを設定
- Pod のすべてのトラフィックを Envoy にリダイレクト
- NAT テーブル (PREROUTING、OUTPUT チェーン) を使用

**簡略化したルール (説明用であり、インストールスクリプトではありません)**:
```bash
# Outbound: All traffic except Envoy -> 15001
iptables -t nat -A OUTPUT -p tcp -m owner ! --uid-owner 1337 -j REDIRECT --to-port 15001

# Inbound: All traffic -> 15006
iptables -t nat -A PREROUTING -p tcp -j REDIRECT --to-port 15006
```

**セットアップの代替手段**: Istio CNI はノードレベルで特権的なネットワーク設定を行います。

**関連ドキュメント**: [Architecture - iptables](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#iptables-and-traffic-interception)

---

### Istiod

Istio 1.5 以降における統合された Control Plane コンポーネントです。

**統合された機能**:
- **Pilot**: Service Discovery、Traffic Management
- **Citadel**: Certificate Authority、Identity
- **Galley**: 設定の検証

**実行方式**:
- 単一の Go バイナリ: `pilot-discovery`
- すべての機能が単一プロセス内で動作
- デフォルトポート: 15012 (xDS)、15017 (Webhook)

**利点**:
- 複雑さの低減
- 運用の簡素化
- リソース効率

**関連ドキュメント**: [Architecture - Istiod](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#control-plane-istiod)

---

## J-L

### LDS (Listener Discovery Service)

Envoy がリスニングするポートとフィルターチェーンを動的に受け取るための xDS API の 1 つです。

**提供される情報**:
- Listener のアドレスとポート
- プロトコル (HTTP、TCP)
- フィルターチェーンの構成
- TLS 設定

**Istio のデフォルト Listener**:
- `0.0.0.0:15001`: Outbound TCP
- `0.0.0.0:15006`: Inbound TCP
- `0.0.0.0:15021`: ヘルスチェック
- `0.0.0.0:15090`: Prometheus メトリクス

**関連用語**: [xDS](#xds-discovery-service), [Envoy](#envoy-proxy)

---

### Locality-aware Load Balancing

ローカリティ (Region、Zone) の情報を考慮するロードバランシング方式です。

**優先順位**:
1. 同一 Zone のエンドポイント
2. 同一 Region 内の別 Zone
3. 別 Region

**設定例**:
```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-2
spec:
  host: reviews
  trafficPolicy:
    loadBalancer:
      localityLbSetting:
        enabled: true
        distribute:
        - from: us-west/zone-1a/*
          to:
            "us-west/zone-1a/*": 80
            "us-west/zone-1b/*": 20
```

**関連ドキュメント**: [Zone Aware Routing](resilience/03-zone-aware-routing.md)

---

## M-O

### Mixer

Istio 1.4 まで存在していたポリシーとテレメトリーのコンポーネントです。

**主な機能**:
- ポリシーの適用 (Rate Limiting、Access Control)
- テレメトリーの収集

**削除された理由**:
- パフォーマンスのオーバーヘッド (リクエストごとに Mixer を呼び出す)
- 複雑なアーキテクチャ

**現在の状況**: 1.5 への移行時に非推奨となり、残っていた Mixer の機能は 1.8 で削除されました

**関連用語**: [Istiod](#istiod)

---

### mTLS (Mutual TLS)

クライアントとサーバーが相互に認証を行う双方向の TLS 通信方式です。

**Istio の mTLS**:
- 証明書の自動発行と更新
- SPIFFE ID ベースの認証
- TLS の暗号スイートはネゴシエートされ、AES-256-GCM に固定されているわけではありません

**モード**:
1. **STRICT**: mTLS のみ許可
2. **PERMISSIVE**: mTLS + 平文を許可 (移行用)
3. **DISABLE**: サイドカーモードで Istio のトランスポート mTLS を無効化。ambient では未サポート

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

**関連ドキュメント**: [mTLS](security/01-mtls.md)

---

### Outlier Detection

異常な挙動を示すエンドポイントを自動的に除外する機能です。

**検出条件**:
- 連続エラー数
- エラー率
- 接続の失敗/タイムアウト。レイテンシーのみでは outlier ejection のしきい値になりません

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-3
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**関連ドキュメント**: [Outlier Detection](resilience/01-outlier-detection.md)

---

## P-R

### Downstream

Envoy の観点では、**リクエストを送る側**を指します。すなわち、Envoy への接続を開始するクライアントです。

**Envoy の Downstream**:
- Envoy に入ってくる接続 (Inbound)
- リクエストを送信するクライアント
- Listener が受け付ける接続

**トラフィックフロー**:
```
Downstream (Client)  ->  Envoy Proxy  ->  Upstream (Backend)
```

**シナリオ例**:

#### 1. Sidecar モード - Outbound リクエスト

![Sidecar モードでは、アプリケーション (Downstream) が同じ Pod 内の Envoy sidecar にリクエストを送り、Envoy がそれをバックエンドサービス (Upstream) に転送する様子を示しています。](../../.gitbook/assets/en-service-mesh-istio-glossary-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-0.html)

**観点**:
- **Envoy から見ると**: アプリケーションが Downstream (リクエストの送信側)
- **Envoy から見ると**: バックエンドサービスが Upstream (リクエストの受信側)

#### 2. Ingress Gateway - 外部からのリクエスト

![Ingress Gateway の Envoy から見ると、外部クライアントが Downstream 側であり、ルーティング先の内部サービスが Upstream 側になることを示しています。](../../.gitbook/assets/en-service-mesh-istio-glossary-1.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-1.html)

**Downstream 関連の Envoy 設定**:

```yaml
# Listener - Receive Downstream connections
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: downstream-config
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: LISTENER
    match:
      context: SIDECAR_INBOUND
    patch:
      operation: MERGE
      value:
        per_connection_buffer_limit_bytes: 32768  # Downstream buffer
```

**Downstream のメトリクス**:
```bash
# Downstream connection count
envoy_listener_downstream_cx_active

# Downstream request count
envoy_http_downstream_rq_total

# Downstream response time
envoy_http_downstream_rq_time
```

**関連用語**: [Upstream](#upstream), [Envoy](#envoy-proxy), [Listener](#lds-listener-discovery-service)

---

### Upstream

Envoy の観点では、**リクエストを受け取る側**を指します。すなわち、Envoy が接続を開始する先のバックエンドサービスです。

**Envoy の Upstream**:
- Envoy から出ていく接続 (Outbound)
- リクエストを処理するバックエンドサービス
- Cluster が管理するエンドポイント

**トラフィックフロー**:
```
Downstream (Client)  ->  Envoy Proxy  ->  Upstream (Backend)
```

**Upstream の構成要素**:

#### 1. Cluster (Upstream のグループ)

```yaml
# Define Upstream Cluster with DestinationRule
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
spec:
  host: reviews  # Upstream service
  trafficPolicy:
    loadBalancer:
      simple: ROUND_ROBIN
    connectionPool:
      tcp:
        maxConnections: 100      # Upstream connection limit
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5        # Upstream failure detection
      interval: 30s
```

#### 2. Endpoint (実際の Upstream インスタンス)

```bash
# Check upstream endpoints
istioctl proxy-config endpoints <pod-name> | grep reviews

# Example output:
# ENDPOINT              STATUS      CLUSTER
# 10.244.1.5:9080       HEALTHY     outbound|9080||reviews.default.svc.cluster.local
# 10.244.2.8:9080       HEALTHY     outbound|9080||reviews.default.svc.cluster.local
# 10.244.3.12:9080      UNHEALTHY   outbound|9080||reviews.default.svc.cluster.local
```

**Upstream のトラフィックポリシー**:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-4
spec:
  host: reviews
  trafficPolicy:
    # Upstream load balancing
    loadBalancer:
      consistentHash:
        httpHeaderName: "x-user-id"

    # Upstream connection pool
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 30s
      http:
        h2UpgradePolicy: UPGRADE

    # Upstream TLS
    tls:
      mode: ISTIO_MUTUAL

    # Upstream Circuit Breaker
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
```

**Upstream と Downstream の比較**:

| 項目 | Downstream | Upstream |
|------|-----------|----------|
| **方向** | Envoy に入ってくる (Inbound) | Envoy から出ていく (Outbound) |
| **役割** | リクエストの送信 (Client) | リクエストの受信 (Server) |
| **Envoy の設定** | Listener、Filter Chain | Cluster、Endpoint |
| **例** | 外部ユーザー、他のサービス | バックエンド API、データベース |
| **メトリクス** | `downstream_cx_*`, `downstream_rq_*` | `upstream_cx_*`, `upstream_rq_*` |

**実際の例**:

#### シナリオ 1: Service A -> Service B の呼び出し

```
+---------------------------------------------------------+
| Service A Pod                                           |
|                                                         |
|  App --> Envoy Sidecar                                 |
|          |                                              |
|          | Downstream: App                              |
|          | Upstream: Service B                          |
+----------|-------------------------------------------------+
           |
           v
+---------------------------------------------------------+
| Service B Pod                                           |
|                                                         |
|          Envoy Sidecar --> App                          |
|          |                                              |
|          | Downstream: Service A Envoy                  |
|          | Upstream: Local App (Service B)              |
+---------------------------------------------------------+
```

**Service A の Envoy から見た場合**:
- Downstream: Service A のアプリケーション
- Upstream: Service B

**Service B の Envoy から見た場合**:
- Downstream: Service A の Envoy
- Upstream: Service B のアプリケーション (ローカル)

#### シナリオ 2: Ingress Gateway

```
External Client (Downstream)
        |
Ingress Gateway (Envoy)
        |
Internal Service (Upstream)
```

**Upstream のメトリクス**:

```bash
# Upstream connection count
envoy_cluster_upstream_cx_active

# Upstream request counter; derive success/error rates from response-class counters
envoy_cluster_upstream_rq_total

# Upstream response time
envoy_cluster_upstream_rq_time

# Upstream health check
envoy_cluster_health_check_success

# Upstream Circuit Breaker
envoy_cluster_circuit_breakers_default_remaining_rq
```

**Upstream のパッシブなヘルス検出**: アクティブなヘルスチェックの統計情報には別途設定が必要です。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-5
spec:
  host: reviews
  trafficPolicy:
    outlierDetection:
      # Upstream health detection
      consecutiveGatewayErrors: 5
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

**デバッグ**:

```bash
# 1. Check upstream cluster
istioctl proxy-config clusters <pod-name> --fqdn reviews.default.svc.cluster.local

# 2. Check upstream endpoint status
istioctl proxy-config endpoints <pod-name> --cluster "outbound|9080||reviews.default.svc.cluster.local"

# 3. Check upstream metrics
kubectl exec <pod-name> -c istio-proxy -- \
  curl -s localhost:15000/stats/prometheus | grep upstream

# 4. Check upstream connections
istioctl proxy-config all <pod-name> -o json | \
  jq '.configs[] | select(.["@type"] | contains("ClustersConfigDump"))'
```

**関連用語**: [Downstream](#downstream), [Envoy](#envoy-proxy), [Cluster](#cds-cluster-discovery-service), [Endpoint](#eds-endpoint-discovery-service)

---

### Pilot

Istio 1.4 まで独立して存在していたトラフィック管理コンポーネントです。現在は Istiod に統合されています。

**主な機能**:
- Service Discovery
- Traffic Management (VirtualService、DestinationRule の処理)
- xDS Server

**現在の状況**: Istio 1.5 以降では Istiod 内部の機能として存在します

**関連用語**: [Istiod](#istiod), [xDS](#xds-discovery-service)

---

### RDS (Route Discovery Service)

HTTP のルーティングルールを動的に提供する xDS API の 1 つです。

**提供される情報**:
- ルートのマッチングルール (パス、ヘッダーなど)
- 重みベースのルーティング
- リダイレクトとリライトのルール
- Timeout と Retry の設定

**VirtualService との関係**:
- VirtualService -> Istiod が変換 -> RDS の設定

**関連用語**: [xDS](#xds-discovery-service), [VirtualService](#virtualservice)

---

### Rate Limiting

単位時間あたりに許可するリクエスト数を制限する機能です。

**実装方式**:
1. **Local Rate Limiting**: Envoy がローカルで処理
2. **Global Rate Limiting**: 外部の Rate Limit サービスを使用

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: filter-local-ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
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
```

**関連ドキュメント**: [Rate Limiting](resilience/02-rate-limiting.md)

---

## S-U

### SDS (Secret Discovery Service)

TLS 証明書と鍵を動的に提供する xDS API の 1 つです。

**提供される情報**:
- X.509 証明書
- Private Key
- CA ルート証明書

**利点**:
- ファイルシステムが不要
- 証明書の自動更新
- ダウンタイムなしの更新

**関連用語**: [xDS](#xds-discovery-service), [mTLS](#mtls-mutual-tls)

---

### Service Entry

Service Mesh の外部にあるサービスをメッシュに登録する Istio の CRD です。

**ユースケース**:
- 外部 API へのアクセス制御
- 外部サービスへの Istio 機能の適用 (Retry、Timeout など)
- Egress Gateway との連携

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
spec:
  hosts:
  - api.external.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

**関連ドキュメント**: [ServiceEntry](traffic-management/12-service-entry.md)

---

### Service Mesh

マイクロサービス間の通信を管理するインフラストラクチャレイヤーです。

**主要機能**:
- トラフィック管理 (ルーティング、ロードバランシング)
- セキュリティ (mTLS、認証/認可)
- オブザーバビリティ (メトリクス、ログ、トレーシング)
- 回復性 (Retry、Circuit Breaker)

**主な実装**:
- Istio
- Linkerd
- Consul Connect
- AWS App Mesh ([サポートは 2026 年 9 月 30 日に終了](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html))

---

### SigV4 (AWS Signature Version 4)

AWS API リクエストを認証するための署名プロトコルです。

**動作の仕組み**:

![Envoy が送信元クライアントのリクエストに AWS SigV4 の認証情報で透過的に署名し、AWS サービスへ転送してレスポンスを返すまでを示すシーケンス図。](../../.gitbook/assets/en-service-mesh-istio-glossary-2.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-glossary-2.html)

**署名の構成要素**:

1. **Canonical Request**: リクエストを標準化した形式
   - HTTP メソッド
   - URI パス
   - クエリ文字列
   - ヘッダー
   - ペイロードのハッシュ

2. **String to Sign**: 署名対象の文字列
   - アルゴリズム: `AWS4-HMAC-SHA256`
   - タイムスタンプ
   - Credential Scope
   - Canonical Request のハッシュ

3. **Signing Key**: 署名鍵の計算
   ```
   HMAC(HMAC(HMAC(HMAC("AWS4" + SecretKey, Date), Region), Service), "aws4_request")
   ```

4. **Signature**: 最終的な署名
   ```
   HMAC(SigningKey, StringToSign)
   ```

**Istio との統合**:

AWS SDK および AWS CLI は、IRSA または EKS Pod Identity から提供される一時的な認証情報を使用して HTTPS リクエストに署名します。これにより、署名はワークロードの AWS 権限に紐付いた状態が保たれます。Istio の mTLS アイデンティティと AWS IAM のアイデンティティは別個のものです。

Envoy の `aws_request_signing` HTTP フィルターは、上級者向けの代替手段です。この拡張を含む Envoy ビルド、**プロキシコンテナ**が利用できる認証情報、正しい AWS サービス/リージョン、そして意図した AWS 宛先に限定したフィルターのマッチ条件が必要です。フィルターは router の前、かつ署名に影響するヘッダー/パスのリライトの後に挿入します。アプリケーション由来の HTTPS はこの HTTP フィルターからは不透明です。Envoy は暗号化された TLS の内部に署名を追加できません。プロキシ署名の設計では、署名プロキシに対して HTTP を提示し、アップストリームへは検証済みの TLS を確立する必要があります。二重の TLS 確立や、意図したローカルプロキシ経路を超えて未署名の HTTP を露出することは避けてください。

上の図は、明示的に設定した署名プロキシ経路を説明したものであり、Istio のデフォルト機能ではありません。アプリケーションの ServiceAccount に IRSA のアノテーションを付けただけでは、Gateway やサイドカーが必要とする認証情報の環境やトークンのマウントが備わっている証明にはなりません。

**認証は JWT の検証ではありません**:

SigV4 は HMAC によるリクエスト署名であり、JWT ではありません。`https://sts.amazonaws.com/.well-known/jwks` は、AWS API の署名を検証するための JWT 発行者エンドポイントではありません。Istio の RequestAuthentication は、実在する OIDC 発行者からの JWT を検証します。CUSTOM の AuthorizationPolicy には、さらに外部認可を実装する `extensionProviders` サービスの設定が必要であり、その実装なしに SigV4 を検証することはできません。AWS API へのアクセスには、IAM 認証された AWS エンドポイントまたは AWS SDK の利用を推奨します。

**読み取り専用の検証例** (ワークロードに AWS CLI がインストールされ、意図した IAM ロールが付与されている場合):

```bash
aws sts get-caller-identity
aws s3api head-object --bucket my-bucket --key object.txt --region us-west-2
```

**運用上の考慮事項**:

- ワークロードには必要な AWS のアクションとリソースのみを付与してください。共有のノードインスタンスロールに依存しないようにします。
- 選択した認証情報プロバイダーが一時的な認証情報と更新をサポートしていることを確認してください。セッション期間は設定可能であり、一律で 1 時間というわけではありません。
- CloudTrail の管理イベントとデータイベントではカバー範囲が異なり、S3 のオブジェクトアクセスには適切なデータイベントの設定が必要です。
- プロキシの設定を確認して、フィルターの配置位置を検証してください。config dump は個々のライブリクエストの Authorization ヘッダーを表示しませんし、HTTPS 越しの未署名 curl は SigV4 のテストにはなりません。
- 実際のリクエストサイズに対する署名/バッファリング/認証情報取得のオーバーヘッドを測定してください。固定のミリ秒単位のオーバーヘッドが保証されるわけではありません。

**関連用語**: [AuthorizationPolicy](#authorizationpolicy), [ServiceEntry](#service-entry), [EnvoyFilter](advanced/03-envoy-filter.md)

**参考資料**:
- [AWS Signature Version 4](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html)
- [Envoy AWS Request Signing](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/aws_request_signing_filter)
- [AWS Integration](04-aws-integration.md)

---

### Sidecar

アプリケーションコンテナと並べてデプロイされる補助コンテナのパターンです。

**Istio の Sidecar**:
- コンテナ名: `istio-proxy`
- イメージ: `istio/proxyv2`
- Envoy Proxy を実行
- init コンテナまたは Istio CNI のリダイレクトにより、設定されたトラフィックをインターセプト

**インジェクション方式**:
1. **自動**: Namespace のラベル
2. **手動**: `istioctl kube-inject`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: example-mesh
  labels:
    istio-injection: enabled  # Automatic injection
```

**関連ドキュメント**: [Sidecar Injection](advanced/07-sidecar-injection.md)

---

### Sidecar リソース

Envoy が受け取るサービス情報を制限する Istio の CRD です。

**目的**:
- メモリ使用量の削減
- 設定のプッシュ時間の短縮
- 設定のスコープ制御。ネットワークのセキュリティ境界ではありません

```yaml
apiVersion: networking.istio.io/v1
kind: Sidecar
metadata:
  name: default
  namespace: default
spec:
  egress:
  - hosts:
    - "./*"  # Same namespace only
    - "istio-system/*"
```

**効果**:
- インポートするサービスを減らすことでメモリと設定処理を削減できる可能性があります。実際の削減量は測定してください。

**関連ドキュメント**: [Architecture - Sidecar Resource](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#optimization-with-sidecar-resource)

---

### SPIFFE (Secure Production Identity Framework for Everyone)

クラウドネイティブ環境においてワークロードのアイデンティティを証明するための標準です。

**SPIFFE ID の形式**:
```
spiffe://trust-domain/path
```

**Istio での例**:
```
spiffe://cluster.local/ns/default/sa/reviews
  |         |           |     |      |    |
  |         |           |     |      |    +- ServiceAccount name
  |         |           |     |      +----- "sa" (ServiceAccount)
  |         |           |     +------------ Namespace name
  |         |           +------------------ "ns" (Namespace)
  |         +------------------------------ Trust Domain
  +---------------------------------------- Protocol
```

**構成要素**:
- **SPIFFE ID**: ワークロードの識別子
- **SVID (SPIFFE Verifiable Identity Document)**: X.509-SVID または JWT-SVID。Istio の mTLS は X.509-SVID を使用します

**関連用語**: [Identity](#identity), [mTLS](#mtls-mutual-tls)

---

### Subset

DestinationRule で定義する、サービスの論理的なグループです。

**一般的な用途**:
- バージョン別: `v1`, `v2`, `v3`
- デプロイ段階別: `stable`, `canary`, `test`
- リージョン別: `us-west`, `us-east`, `eu-central`

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: glossary-example-6
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

**関連ドキュメント**: [DestinationRule - Subset Concept](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/traffic-management/03-destination-rule#subset-concept)

---

## V-Z

### Waypoint Proxy

Ambient Mode で L7 機能を提供する任意のプロキシです。

**役割**:
- namespace、Service、または Pod のラベルで選択されます。ServiceAccount ごとに自動で作られるわけではありません
- Envoy Proxy をベースとする
- L7 トラフィック管理機能に特化
- ztunnel と連携して動作

**提供される機能**:
- L7 ルーティング (Path、Header ベース)
- Retry と Timeout
- Circuit Breaker
- Fault Injection
- ヘッダーの操作

**デプロイ例**:
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: reviews-waypoint
  namespace: default
spec:
  gatewayClassName: istio-waypoint
  listeners:
  - name: mesh
    port: 15008
    protocol: HBONE
```

**特徴**:
- ztunnel は L4 のみを処理し、waypoint が L7 を処理
- 必要なサービスに対してのみ選択的に利用
- Sidecar よりリソース効率が高い (共有型のアプローチ)
- namespace、Service、または Pod のラベルで選択されます。ServiceAccount ごとに自動で作られるわけではありません

**関連用語**: [Ambient Mode](#ambient-mode), [ztunnel](#ztunnel-zero-trust-tunnel)

---

waypoint を作成した後は、対象のサービスを参加させます。例: `kubectl label service reviews istio.io/use-waypoint=reviews-waypoint --overwrite`。Gateway をデプロイするだけでは、トラフィックはそこを経由しません。

### VirtualService

Service Mesh 内でトラフィックをどのようにルーティングするかを定義する Istio の CRD です。

**主な機能**:
- URI、ヘッダー、クエリパラメーターに基づくルーティング
- 重みベースのトラフィック分配
- Retry と Timeout の設定
- Fault Injection

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: reviews
spec:
  hosts:
  - reviews
  http:
  - match:
    - uri:
        prefix: "/v2"
    route:
    - destination:
        host: reviews
        subset: v2
  - route:
    - destination:
        host: reviews
        subset: v1
```

**関連ドキュメント**: [Gateway and VirtualService](traffic-management/01-gateway-virtualservice.md)

---

### WASM (WebAssembly)

Web ブラウザーで実行することを目的に設計されたバイナリ命令形式です。Istio では、Envoy プロキシの機能を拡張するために使用されます。

**Istio での用途**:
- Envoy Filter としてカスタムロジックを追加
- 再デプロイなしで機能を動的に拡張
- さまざまな言語で記述可能 (Rust、C++、Go など)
- サンドボックス環境で安全に実行

**主なユースケース**:
1. **カスタム認証/認可**: 複雑なビジネスロジックの実装
2. **リクエスト/レスポンスの変換**: ヘッダーの操作、ペイロードの変換
3. **高度なルーティング**: カスタムのルーティングロジック
4. **メトリクスの収集**: 特化したテレメトリー

以下のレジストリ URL、ダイジェスト、認証情報、pluginConfig のフィールドは、自分でビルドしたプラグイン用のプレースホルダーです。Istio はこれらの例のイメージを提供しませんし、プラグイン固有のオプションを解釈することもありません。file:// のモジュールはプロキシコンテナ内に存在する必要があります。

**WASM プラグインの例**:
```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: custom-auth
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  url: oci://ghcr.io/my-org/custom-auth:v1.0.0
  phase: AUTHN
  pluginConfig:
    api_key_header: "X-API-Key"
    validate_endpoint: "https://auth.example.com/validate"
```

**デプロイ方式**:

#### 1. OCI レジストリ経由のデプロイ (推奨)

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: rate-limiter
spec:
  url: oci://ghcr.io/my-org/rate-limit:v1.0.0
  imagePullPolicy: Always
  imagePullSecret: registry-credential
```

#### 2. HTTP URL 経由のデプロイ

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: custom-filter
spec:
  url: https://example.com/filters/custom-filter.wasm
  # Add sha256: with the actual 64-character module digest before deployment
```

#### 3. ローカルファイルによるデプロイ

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: local-filter
spec:
  url: file:///etc/istio/filters/custom.wasm
```

**WASM 開発例 (Rust)**:

```rust
use proxy_wasm::traits::*;
use proxy_wasm::types::*;

proxy_wasm::main! {{
    proxy_wasm::set_http_context(|_, _| -> Box<dyn HttpContext> {
        Box::new(CustomFilter)
    });
}}

struct CustomFilter;
impl Context for CustomFilter {}

impl HttpContext for CustomFilter {
    fn on_http_request_headers(&mut self, _: usize, _: bool) -> Action {
        // Demonstrate header mutation, not production API-key authentication.
        self.set_http_request_header("x-mesh-demo", Some("wasm"));
        Action::Continue
    }
}
```

**ビルドとデプロイの前提条件**:

Rust の `cdylib` クレートと、互換性のある `proxy-wasm` 依存関係、そして固定した依存バージョンを使用します。上記のコールバックは[公式 Rust SDK の例](https://github.com/proxy-wasm/proxy-wasm-rust-sdk/tree/main/examples/http_headers)に従っています。`wasm32-unknown-unknown` ターゲットをインストールしてモジュールをビルドし、生成された `.wasm` をサポートされている OCI Wasm イメージにパッケージ化したうえで、WasmPlugin から参照してください。Dockerfile のない一般的な `docker build` では、そのパッケージ化は行われません。

```bash
rustup target add wasm32-unknown-unknown
cargo build --target wasm32-unknown-unknown --release
```

対象のプラグインについて、起動時間、メモリ、リクエストごとのオーバーヘッドを測定してください。Wasm はプロキシプロセス内のランタイムサンドボックスで実行されます。別プロセスではなく、また無条件のセキュリティ/パフォーマンスの保証でもありません。

**Ambient Mode のサポート**:

```yaml
apiVersion: extensions.istio.io/v1alpha1
kind: WasmPlugin
metadata:
  name: waypoint-filter
spec:
  targetRefs:
  - group: gateway.networking.k8s.io
    kind: Gateway
    name: reviews-waypoint
  url: oci://ghcr.io/filters/custom:latest
  phase: AUTHN
```

**デバッグ**:

```bash
# Check WASM plugin status
kubectl get wasmplugin -A

# Check WASM-related logs in Envoy logs
kubectl logs <pod-name> -c istio-proxy | grep wasm

# Check WASM module load
istioctl proxy-config all <pod-name> -o json | jq '.. | objects | select(has("@type")) | select(.["@type"] | test("wasm"; "i"))'
```

**セキュリティ上の考慮事項**:
1. **サンドボックスによる分離**: Envoy 内部のランタイムサンドボックス。プラグインの信頼性とリソース使用量を確認してください
2. **リソース制限**: CPU とメモリの制限を設定可能
3. **完全性の検証**: SHA256 はコンテンツを検証しますが、公開者を認証するものではありません
4. **最小権限**: 必要な権限のみを付与

**利点**:
- 高いパフォーマンス (ネイティブコードレベル)
- 安全なサンドボックス実行
- 再デプロイなしで更新可能
- 複数言語のサポート
- 標準的な OCI イメージ形式

**制限事項**:
- 一部のシステムコールが制限される
- ファイル I/O が限定的
- ネットワーク呼び出しは Envoy API 経由のみ

**関連用語**: [Envoy](#envoy-proxy), [Waypoint Proxy](#waypoint-proxy), [Ambient Mode](#ambient-mode)

**参考資料**:
- [Istio WASM Plugin](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/)
- [Proxy-Wasm SDK](https://github.com/proxy-wasm)
- [WebAssembly Official Site](https://webassembly.org/)
- [Ambient Mode - WASM](https://istio.io/latest/docs/ambient/usage/extend-waypoint-wasm/)

---

### xDS (Discovery Service)

Envoy Proxy を動的に設定するための API 群です。

**「xDS」の意味**:
- `x`: さまざまな種別を表す変数
- `DS`: Discovery Service

**xDS API の種類**:

| API | 名称 | 役割 |
|-----|------|------|
| **LDS** | Listener Discovery Service | リスニングポートとフィルターチェーン |
| **RDS** | Route Discovery Service | HTTP のルーティングルール |
| **CDS** | Cluster Discovery Service | アップストリームサービスの設定 |
| **EDS** | Endpoint Discovery Service | 実際の Pod IP の一覧 |
| **SDS** | Secret Discovery Service | TLS 証明書と鍵 |

**通信方式**:
- プロトコル: gRPC
- ポート: 15012 (Istiod)
- 双方向ストリーミング

**順序**:
```
Agent bootstraps identity -> Envoy subscribes to ADS resources
Istiod pushes LDS/CDS/EDS/RDS updates; local agent serves SDS certificates
```

**関連ドキュメント**: [Architecture - xDS API Communication](https://www.atomai.click/kubernetes-docs/en/service-mesh/istio/03-architecture#xds-api-communication)

---

### Zone

Kubernetes の Availability Zone を表します。

**ラベルの形式**:
```yaml
topology.kubernetes.io/zone: us-west-1a
```

**Istio での用途**:
- Locality-aware Load Balancing
- Zone Aware Routing
- 同一 Zone を優先するルーティング

**関連用語**: [Locality-aware Load Balancing](#locality-aware-load-balancing)

---

### ztunnel (Zero Trust Tunnel)

Ambient Mode のコアコンポーネントで、ノードレベルで動作する軽量な L4 プロキシです。

**役割**:
- 各ノードに DaemonSet としてデプロイ
- すべての Pod の L4 トラフィックを処理
- Sidecar なしで Service Mesh の機能を提供
- CNI プラグインと統合

**提供される機能**:
- **mTLS**: 自動的な暗号化/復号
- **L4 テレメトリー**: メトリクスの収集
- **Identity**: Service Account ベースの認証
- **L4 ロードバランシング**: 基本的なロードバランシング

**技術的な特徴**:
- Rust で記述 (高性能)
- Istio CNI が管理するトラフィックのリダイレクト
- Init Container が不要
- L4 プロキシのリソースを共有。ノードの実測ワークロードに基づいてサイジングしてください

**デプロイ例**:
```bash
# Use the reviewed istioctl version and the complete ambient installation profile
istioctl install --set profile=ambient
kubectl rollout status daemonset/ztunnel -n istio-system
```

既存のサイドカーワークロードでは、ambient に参加させる前に、インジェクション/revision のラベルを削除して Pod を再起動し、サイドカーを取り除いてください。新規のサイドカーなしのワークロードでは再起動は不要です。

**Namespace の有効化**:
```bash
# Enable Ambient Mode
kubectl label namespace default istio-injection- istio.io/rev-
kubectl label namespace default istio.io/dataplane-mode=ambient --overwrite
```

**利点**:
- メモリ削減の可能性は、ノード/ワークロードおよび waypoint のキャパシティに依存します
- Pod の再起動が不要
- アプリケーションに対して透過的
- 初期レイテンシーの最小化

**制限事項**:
- L7 機能には Waypoint Proxy が必要
- サポートされている Linux の Kubernetes プラットフォーム、プライマリ CNI、Istio CNI の前提条件が必要

**関連用語**: [Ambient Mode](#ambient-mode), [Waypoint Proxy](#waypoint-proxy), [eBPF](#ebpf-extended-berkeley-packet-filter)

---

## 参考資料

### 公式ドキュメント
- [Istio Glossary](https://istio.io/latest/docs/reference/glossary/)
- [Envoy Terminology](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/intro/terminology)
- [SPIFFE Specification](https://github.com/spiffe/spiffe/tree/main/standards)

### 関連ドキュメント
- [Istio Architecture](03-architecture.md)
- [Traffic Management](traffic-management/README.md)
- [Security](security/README.md)
- [Observability](observability/README.md)

---

**最終更新**: September 13, 2026

- [Destination Rule](https://istio.io/latest/docs/reference/config/networking/destination-rule/)
- [Install the Istio CNI node agent](https://istio.io/latest/docs/setup/additional-setup/cni/)
- [Ztunnel traffic redirection](https://istio.io/latest/docs/ambient/architecture/traffic-redirection/)
- [Install with istioctl](https://istio.io/latest/docs/ambient/install/istioctl/)
- [Configure waypoint proxies](https://istio.io/latest/docs/ambient/usage/waypoint/)
- [Enabling Rate Limits using Envoy](https://istio.io/latest/docs/tasks/policy-enforcement/rate-limit/)
- [Wasm Plugin](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/)
- [Proxy-Wasm Rust SDK HTTP example](https://raw.githubusercontent.com/proxy-wasm/proxy-wasm-rust-sdk/main/examples/http_headers/src/lib.rs)
- [AWS Signature Version 4 for API requests - AWS Identity and Access Management](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv.html)
- [AWS Request Signing](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/aws_request_signing_filter)
- [Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)
- [Istio 1.8 Change Notes](https://istio.io/latest/news/releases/1.8.x/announcing-1.8/change-notes/)
- [What Is AWS App Mesh? - AWS App Mesh](https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html)

- [CloudTrail data event coverage](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html)
