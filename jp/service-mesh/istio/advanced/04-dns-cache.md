# DNS プロキシと DNS キャッシュ

> **検証基準**: Istio 1.31.0、Kubernetes 1.32～1.37
> **最終レビュー日**: 2026年10月16日

Istio の DNS 管理機能を使って、外部サービスへのアクセス性能を最適化し、DNS の名前解決を制御します。

## 目次

1. [DNS プロキシの概要](#dns-proxy-overview)
2. [DNS プロキシと DNS キャッシュの違い](#dns-proxy-vs-dns-caching)
3. [DNS プロキシの設定](#dns-proxy-configuration)
4. [ServiceEntry との統合](#serviceentry-integration)
5. [DNS キャッシュの設定](#dns-caching-configuration)
6. [アドレスの自動割り当て](#automatic-address-allocation)
7. [トラブルシューティング](#troubleshooting)
8. [ベストプラクティス](#best-practices)

## DNS プロキシの概要 {#dns-proxy-overview}

サイドカー方式では、アプリケーションの DNS 要求は Envoy の HTTP/DNS リスナーではなく、**istio-agent の Go DNS サーバー**に転送されます。Agent は Istiod から受け取った名前/IP テーブルを使って応答し、未知の名前は `/etc/resolv.conf` に指定された上流リゾルバーへ転送します。UDP と TCP の DNS に対応し、通常のサイドカー DNS ポートは 15053 です。

アンビエント方式では ztunnel が DNS を処理し、Istio 1.25 以降では DNS キャプチャが既定で有効です。サイドカー方式では明示的な有効化が必要です。DNS-over-HTTPS/TLS とアプリケーション管理のキャッシュは、通常のポート 53 キャプチャとは別の機能です。以下の EnvoyFilter と Agent の診断手順は**サイドカー方式**を対象にしています。

## DNS プロキシと DNS キャッシュの違い {#dns-proxy-vs-dns-caching}

| 層 | 役割 | 設定 |
|---|---|---|
| アプリケーション/OS のリゾルバーキャッシュ | アプリケーションの名前、TTL、ネガティブキャッシュ | アプリケーションのランタイム、OS、リゾルバー |
| Istio DNS プロキシ | メッシュ内の名前/IP テーブル。他の名前は上流へ転送 | サイドカーの `ISTIO_META_DNS_CAPTURE`、アンビエントの CNI/ztunnel |
| Envoy の DNS サービスディスカバリー | DNS ベースの上流クラスターのエンドポイントを更新 | ServiceEntry と生成される DNS クラスター設定 |
| Envoy dynamic forward proxy の DNS キャッシュ | リクエストの Host/SNI から動的な宛先を名前解決 | 別途設定する DYNAMIC_DNS/DFP |

`dns_refresh_rate` を設定しても、アプリケーションのすべての DNS 応答がキャッシュされるわけではありません。サイドカー Agent も、未知の名前に対する上流の応答を汎用キャッシュとして保持しません。既知の名前は CoreDNS への問い合わせを省けますが、上流エンドポイントの更新は別途行われます。両方の機能を有効にしても、性能が最適になるとは限りません。

## DNS プロキシの設定 {#dns-proxy-configuration}

### 1. グローバルな有効化

この `istioctl` 入力を既存のインストール設定に統合してください。削除済みのクラスター内 Operator に `kubectl apply` するリソースではありません。Helm でインストールした場合は、同等の meshConfig 値を既存 chart の設定に統合します。サイドカーのキャプチャ設定は新たに注入または起動された Pod から有効になるため、確認済みのワークロードに段階的に展開してください。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio
  namespace: istio-system
spec:
  meshConfig:
    defaultConfig:
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
```

現在のアドレス割り当ては Istiod コントローラーが担い、既定で有効です。新規インストールの前提として、旧式の `ISTIO_META_DNS_AUTO_ALLOCATE` メタデータを追加しないでください。

### 2. Namespace ごとの有効化

Namespace の注入ラベルだけでは DNS キャプチャは有効になりません。GitOps/Kustomize/Helm を使い、選択した Namespace の Deployment の Pod テンプレートに次の設定断片を統合してください。中央の `istio-sidecar-injector` ConfigMap を一部の値で置き換えても、Namespace 単位の設定にはなりません。既存の `proxy.istio.io/config` アノテーションにある他の項目も保持してください。

### 3. Pod ごとの有効化

```yaml
# Existing Deployment: merge into spec.template, not a complete workload
metadata:
  annotations:
    proxy.istio.io/config: |
      proxyMetadata:
        ISTIO_META_DNS_CAPTURE: "true"
```

既存のレガシー/リビジョン注入方式を維持し、選択した Pod を再作成してください。これはテンプレートの断片であり、`myapp:v1` イメージを仮定した完全な Pod 定義ではありません。アンビエント Pod では、既定のキャプチャ動作を確認し、必要なら `ambient.istio.io/dns-capture: "false"` で無効化してください。

### 4. リダイレクトと応答の確認

Pod のネットワーク名前空間における DNS リダイレクトは、インストール方式や CNI によって異なります。Proxy イメージに bash/iptables/tcpdump が含まれることや、net-admin 権限があることを前提にしないでください。本番 Pod の権限を増やす前に、以下の Agent の名前テーブル、DNS クエリ、上流エンドポイントを確認します。必要であれば、承認済みの診断環境で UDP/TCP のポート 53 と 15053 の経路を調べてください。

## ServiceEntry との統合 {#serviceentry-integration}

DNS プロキシは ServiceEntry と連携します。

### 基本的な ServiceEntry

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-api
  namespace: default
spec:
  hosts:
  - api.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

**DNS プロキシの動作**:

1. アプリケーションが `api.example.com` を DNS で名前解決します
2. Agent の DNS プロキシが割り当て済み VIP（例: `240.240.0.1`）を返します
3. アプリケーションが仮想 IP にリクエストを送信します
4. Envoy がこの宛先を、別途名前解決した実際の上流エンドポイントへルーティングします

### 複数ホストの登録

独立した上流サービスは、それぞれ具体的なホスト名で登録してください。ここにある example.com の名前は設定例です。実際の DNS/TLS と到達性を備えたバックエンドの名前に置き換えてください。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: partner-api
  namespace: default
spec:
  hosts: ["api.partner.example.com"]
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: assets-cdn
  namespace: default
spec:
  hosts: ["cdn.example.com"]
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

`*.example.com` のようなワイルドカードに `resolution: DNS` を指定しても、具体的なエンドポイントがなければすべてのサブドメインを名前解決できません。サイドカーでアプリケーション本来の宛先へ転送するワイルドカード方式は、別の `resolution: NONE` パターンを使い、DNS 応答は返しません。Istio 1.31 の `DYNAMIC_DNS` は Host/SNI に基づく別の方式です。アンビエントでは waypoint が必要で、raw TCP はサポートされません。現行 API と生成設定に基づいて方式を選んでください。

### エンドポイントの明示的な指定

`addresses` はクライアント側の VIP、`endpoints` は実際のバックエンドを指定します。CIDR プレフィックスはトラフィックの照合には使えますが、単一の DNS A/AAAA 応答ではありません。ここにある TEST-NET アドレスでデータベースが稼働するわけではありません。実際には競合しない VIP/バックエンド/TLS 設定を使ってください。

```yaml
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: external-database
  namespace: default
spec:
  hosts:
  - database.external.com
  addresses:
  - 198.51.100.10  # Explicit example VIP
  ports:
  - number: 3306
    name: mysql
    protocol: TCP
  location: MESH_EXTERNAL
  resolution: STATIC
  endpoints:
  - address: 203.0.113.10
  - address: 203.0.113.11
  - address: 203.0.113.12
```

## DNS キャッシュの設定 {#dns-caching-configuration}

### DNS ベースの上流更新

Istio 1.31 では通常の DNS クラスターに `respect_dns_ttl: true` が設定され、メッシュの `dnsRefreshRate` の既定値は 60 秒です。正常な応答には DNS TTL が使われます。失敗時や TTL が 0 の場合の動作は、生成されたリゾルバーとクラスターの設定に従います。概念を説明する別ページの「30 秒固定で変更不可」という記述は、このリリースのソースコードと一致しません。有効な設定を確認してください。

この低レベルの代替方法では、`app: frontend` を持つ `default` 名前空間に対し、**api.example.com:443 の DNS クラスター1つだけ**を変更します。`cluster.service` が照合するのは実際のサービス名であり、ワイルドカードのセレクターではありません。ルート名前空間からすべてのクラスターに広範なパッチを適用しないでください。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: external-api-dns-refresh
  namespace: default
spec:
  workloadSelector:
    labels:
      app: frontend
  configPatches:
  - applyTo: CLUSTER
    match:
      context: SIDECAR_OUTBOUND
      cluster:
        service: api.example.com
        portNumber: 443
    patch:
      operation: MERGE
      value:
        dns_refresh_rate: 30s
        respect_dns_ttl: true
        dns_failure_refresh_rate:
          base_interval: 5s
          max_interval: 30s
```

### TTL、失敗時の再試行、リゾルバー

`respect_dns_ttl: true` の場合、正常な名前解決をすべて 30 秒ごとに更新する設定にはなりません。`dns_failure_refresh_rate` が制御するのは失敗後の再試行間隔であり、レコードの TTL や古い応答の保持期間ではありません。`dns_query_timeout` は Cluster のフィールドではありません。リゾルバー固有の型付き設定を検証してください。IP ファミリーを一律に IPv4 のみにしたり AUTO に固定したりせず、Istio が選択したファミリーを維持してください。

protobuf の `MERGE` で既存の `respect_dns_ttl: true` を既定のスカラー値 `false` によって解除できる、と想定しないでください。Envoy では一部の DNS クラスターフィールドが非推奨ですが、Istio 1.31 は引き続きこの形式を生成します。アップグレード時には DNS クラスターの拡張設定とリゾルバー設定を再確認してください。

### 適用済み設定の確認

```bash
istioctl proxy-config clusters <client-pod> -n default --fqdn api.example.com -o json |
  jq '.[] | {name,type,dnsRefreshRate,respectDnsTtl,dnsFailureRefreshRate,dnsLookupFamily,typedDnsResolverConfig,loadAssignment}'
```

## アドレスの自動割り当て {#automatic-address-allocation}

### 割り当ての管理主体とステータス

既定で有効な Istiod の IP 割り当てコントローラーは、対象となる ServiceEntry のホストごとに VIP を割り当て、`host` と `value` を `status.addresses` に記録します。通常の `resolution: DNS` を使うワイルドカードは割り当て対象外ですが、`DYNAMIC_DNS` のワイルドカードには別のサポートされた経路があります。`spec.addresses` が明示されている項目や `networking.istio.io/enable-autoallocate-ip: "false"` が設定された項目は、同じ割り当て経路を使いません。

### アドレス範囲

リリース時点の既定プレフィックスは IPv4 が `240.240.0.0/16`、IPv6 が `2001:2::/48` です。これは**既定値を含む実際のコントロールプレーン設定**です。利用者のネットワーク、VPN、Service CIDR と重複しないようにしてください。

```yaml
# Advanced istioctl input: these are the released defaults, not new ranges.
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  values:
    pilot:
      env:
        PILOT_ENABLE_IP_AUTOALLOCATE: "true"
        PILOT_IP_AUTOALLOCATE_IPV4_PREFIX: "240.240.0.0/16"
        PILOT_IP_AUTOALLOCATE_IPV6_PREFIX: "2001:2::/48"
```

`defaultServiceExportTo` は可視性を制御し、`outboundTrafficPolicy` は未登録の外向きトラフィックに関係します。どちらも割り当てプレフィックスは変更しません。既存の VIP を変更すると DNS キャッシュ、接続、ルーティングに影響する可能性があります。したがって、プレフィックス変更を無停止で移行できると実証された方法として扱わないでください。コントローラーが管理する status を手動で編集しないでください。

### 割り当て済みアドレスの確認

```bash
kubectl get serviceentry external-api -n default -o json |
  jq '{hosts:.spec.hosts, explicitAddresses:.spec.addresses, allocatedAddresses:.status.addresses}'

# Inspect the client's mapping and the actual upstream separately.
istioctl proxy-config listeners <client-pod> -n default
istioctl proxy-config clusters <client-pod> -n default --fqdn api.example.com -o json
istioctl proxy-config endpoints <client-pod> -n default --cluster 'outbound|443||api.example.com'
```

割り当てられた VIP は、アプリケーションへの DNS 応答と宛先照合に使われます。DNS クラスターの `loadAssignment` には名前解決する実際のバックエンドホスト名が入り、実行時エンドポイントには解決後のアドレスが入ります。VIP を実際の外部上流 IP として説明しないでください。

## トラブルシューティング {#troubleshooting}

### DNS プロキシの動作確認

```bash
# Inspect classic or native sidecar metadata without assuming a shell in the image.
kubectl get pod <client-pod> -n default -o json |
  jq '[.spec.containers[], .spec.initContainers[]?] |
      .[] | select(.name == "istio-proxy") |
      {name,env:[.env[]? | select(.name == "ISTIO_META_DNS_CAPTURE")]}'

istioctl analyze -n default
istioctl proxy-status
kubectl get serviceentry external-api -n default -o yaml
kubectl logs -n default <client-pod> -c istio-proxy --tail=100

# Requires a reviewed diagnostic container with nslookup in this Pod's network namespace.
kubectl exec -n default <client-pod> -c <diagnostic-container> -- nslookup api.example.com
```

```bash
# Terminal 1: sidecar agent's local status server (not Envoy admin 15000)
kubectl port-forward -n default <client-pod> 15020:15020
```

```bash
# Terminal 2 while the forward remains active
curl --fail --silent http://127.0.0.1:15020/debug/ndsz |
  jq '.table["api.example.com"]'
curl --fail --silent http://127.0.0.1:15020/stats/prometheus |
  grep '^istio_agent_dns_'
```

Agent の `/debug/ndsz` が受け付けるのは localhost からのリクエストのみです。DNS または名前テーブルの状態を取得できない場合は 404 を返すことがあります。Envoy のポート 15000 のリスナー一覧に Agent のポート 15053 があるか探しても、有効な確認にはなりません。アプリケーションに nslookup がない場合は、ベースイメージを変更したり権限を追加したりせず、既定の診断手順を使ってください。

### よくある問題

1. **クエリが引き続き CoreDNS に届く**: 未知の名前が転送されるのは正常です。ローカルテーブルに存在する名前と存在しない名前を区別し、キャプチャ設定、検索ドメインと ndots、TCP フォールバック、アプリケーション側の DoH/TLS を確認してください。
2. **ServiceEntry が見つからない**: `exportTo`、Namespace の検出範囲と Sidecar スコープ、resolution、割り当て status、インジェクションとリビジョン、NDS/xDS の同期を確認してください。`istioctl analyze -n default` を使います。リソース種別や名前はこのコマンドの位置引数ではありません。「同期を強制する」目的で最初に Pod を削除しないでください。
3. **VIP への接続に失敗する**: VIP の照合と、上流 DNS/エンドポイント、ネットワーク経路、TLS の Host/SNI、証明書を分けて確認してください。ポート 443 の HTTPS サービスに `http://VIP` で接続しても、有効なテストにはなりません。

```bash
# Run inside an approved diagnostic container sharing the captured Pod network namespace.
# Replace VIP4 with the actual IPv4 status.addresses value, and keep the real Host/SNI.
VIP4=240.240.0.1
curl --fail --show-error --resolve "api.example.com:443:${VIP4}" https://api.example.com/
```

例の VIP を実際に割り当てられた値に置き換え、対象 Pod のネットワーク名前空間内で実行してください。このルーティング可能でないアドレスに別のホストから到達できるとは想定しないでください。証明書の検証は有効のままにし、直接 VIP に接続するテストとは別に、アプリケーションの DNS 経路も確認してください。

### Envoy Admin API とパケット調査

```bash
# Terminal 1
kubectl port-forward -n default <client-pod> 15000:15000
```

```bash
# Terminal 2: Envoy endpoint discovery, distinct from agent name-table metrics
curl --fail --silent http://127.0.0.1:15000/clusters
curl --fail --silent http://127.0.0.1:15000/config_dump > envoy-config.json
```

パケットキャプチャが必要な場合は、承認済みの診断用コンテナまたはノードを使う手順に従い、Pod のネットワーク名前空間で UDP/TCP の 53 と 15053 を調べてください。istio-proxy に tcpdump、tar、キャプチャ権限が含まれるとは限りません。DNS 名は機密情報になり得るため、キャプチャの時間、範囲、保持期間を制限し、分析後は定められた廃棄手順に従ってください。

## ベストプラクティス {#best-practices}

### 1. DNS プロキシの有効化方針

**推奨する方法**: 段階的な展開

![テスト、ステージング、本番環境へDNSプロキシを段階的に展開し、検証と監視のゲートで失敗時にトラブルシューティングまたはロールバックへ戻すフローチャート。](../../../.gitbook/assets/en-service-mesh-istio-advanced-04-dns-cache-3.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-04-dns-cache-3.html)

### 2. ServiceEntry の管理

```yaml
# Create separate ServiceEntry per external service
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: payment-api
  namespace: default
  labels:
    app: payment
    team: platform
spec:
  hosts:
  - payments.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
---
apiVersion: networking.istio.io/v1
kind: ServiceEntry
metadata:
  name: analytics-api
  namespace: default
  labels:
    app: analytics
    team: data
spec:
  hosts:
  - analytics.example.com
  ports:
  - number: 443
    name: https
    protocol: HTTPS
  location: MESH_EXTERNAL
  resolution: DNS
```

### 3. DNS キャッシュ TTL の設定

レコードの TTL、アプリケーションキャッシュ、Agent の名前テーブル、Envoy エンドポイントの更新をそれぞれ分けて観測してください。分類だけを根拠に、すべての CDN を 300 秒、すべての API クラスターを 10 秒と設定しないでください。自分で管理する DNS ゾーンでは、フェイルオーバーの目標とクエリ負荷に基づいて TTL を決めます。ServiceEntry の `exportTo` や Sidecar スコープはプロキシごとの不要なサービス検出を減らせますが、どちらもネットワークのセキュリティ境界ではありません。

特定の DNS クラスターで失敗時の再試行間隔を設定する場合は、上記のワークロード/ホスト/ポートを限定した例を使い、有効な設定と失敗時の動作を確認してください。

### 4. メトリクスの監視

これらは Istio 1.31 の**サイドカー Agent**が実際に提供するメトリクスです。Prometheus がポート 15020 の `/stats/prometheus` をスクレイプし、ターゲットラベル `namespace` と `pod` を付与する構成を前提としています。ztunnel や Envoy DFP キャッシュのメトリクスと混同しないでください。

```promql
# Application queries handled by the sidecar agent
sum by (namespace, pod) (
  rate(istio_agent_dns_requests_total{namespace="default"}[5m])
)

# Fraction forwarded upstream; not a DNS response-cache hit/miss ratio
100 *
sum by (namespace, pod) (
  rate(istio_agent_dns_upstream_requests_total{namespace="default"}[5m])
) /
sum by (namespace, pod) (
  rate(istio_agent_dns_requests_total{namespace="default"}[5m])
)

# Requests for which the agent synthesized SERVFAIL after upstream exchange failures
100 *
sum by (namespace, pod) (
  rate(istio_agent_dns_upstream_failures_total{namespace="default"}[5m])
) /
sum by (namespace, pod) (
  rate(istio_agent_dns_upstream_requests_total{namespace="default"}[5m])
)

# Upstream request duration p99, in seconds
histogram_quantile(0.99,
  sum by (le, namespace, pod) (
    rate(istio_agent_dns_upstream_request_duration_seconds_bucket{namespace="default"}[5m])
  )
)
```

`dns_upstream_failures_total` は、上流との通信失敗後に Agent が生成した SERVFAIL を数えます。有効な上流応答パケットで返された NXDOMAIN/SERVFAIL をすべて数えるものではありません。リクエストがない場合、比率や分位点は NaN になったり存在しなかったりします。トラフィックとスクレイプの正常性を併せて確認してください。これらの値から「キャッシュヒット率」を作り出さないでください。

### 5. セキュリティ上の考慮事項

DNS キャプチャ、ServiceEntry の登録、VIP の割り当ては、外部通信の許可リストを強制しません。サイドカーワークロードを選択する AuthorizationPolicy が評価するのは、そのワークロードへの**インバウンド**トラフィックであり、外向きの DNS/HTTPS リクエストではありません。Namespace 全体に適用する `DENY/notHosts` は、内部通信や HTTP 属性のない TCP 通信までブロックする可能性があります。

適切な CNI/NetworkPolicy、ファイアウォール/セキュリティグループの境界を使って外向き通信を制御してください。必要な場合は、迂回できない Egress Gateway を経由させ、ゲートウェイで認可します。TLS パススルー経路では HTTP Host を検査できないため、SNI/宛先の制約と証明書検証を別途扱う必要があります。[Egress Control（外向き通信の制御）](../traffic-management/11-egress-control.md) に記載された前提条件をすべて確認してください。

### 6. パフォーマンスの調整

ボトルネックを変更する前に、DNS 負荷、失敗数、名前解決時間に加え、Istiod の push 遅延とサイドカー Agent/Envoy の CPU・メモリを測定してください。Envoy のワーカー並列数は Agent の Go DNS サーバーの規模を決めません。Istiod のレプリカや HPA を増やすだけで、あらゆる DNS 経路が高速化するわけではありません。

アプリケーションキャッシュと ndots、DNS TTL、ServiceEntry の件数と可視性、プロキシレプリカ間の定期クエリ負荷、障害復旧中の古いエンドポイントや接続の挙動をテストしてください。測定せずに CPU/メモリ/HPA の値を固定しても、本番向けの最適化にはなりません。

## 参考資料

### 公式ドキュメント
- [Istio DNS プロキシ](https://istio.io/latest/docs/ops/configuration/traffic-management/dns-proxy/)
- [Envoy DNS キャッシュ](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/service_discovery)
- [ServiceEntry の仕様](https://istio.io/latest/docs/reference/config/networking/service-entry/)

- [Istio 1.31 DNS サーバー](https://raw.githubusercontent.com/istio/istio/1.31.0/pkg/dns/client/dns.go)
- [Istio 1.31 IP 割り当てとプレフィックス](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/features/pilot.go)
- [Istio 1.31 割り当て status](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/controllers/ipallocate/ipallocate.go)
- [Istio 1.31 DNS クラスターの生成](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/cluster_builder.go)
- [Istio 1.31 メッシュの既定値](https://raw.githubusercontent.com/istio/istio/1.31.0/pkg/config/mesh/mesh.go)
- [Istio 1.31 Agent の DNS メトリクス](https://raw.githubusercontent.com/istio/istio/1.31.0/pkg/dns/client/monitoring.go)
- [Istio 1.31 Agent の status エンドポイント](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/cmd/pilot-agent/status/server.go)
- [Envoy Cluster API](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/cluster/v3/cluster.proto)

### 関連ドキュメント
- [Istio アーキテクチャ - DNS 処理の仕組み](../03-architecture.md)
- [ServiceEntry の仕様](../traffic-management/12-service-entry.md)
- [Egress Control（外向き通信の制御）](../traffic-management/11-egress-control.md)
