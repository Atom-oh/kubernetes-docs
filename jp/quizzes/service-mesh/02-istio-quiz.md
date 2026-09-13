# Istioクイズ

> **最終更新**: September 11, 2026 · 例の確認環境: Istio 1.31.0 / Argo Rollouts 1.10.0

このクイズは[保守されているIstioガイド](../../service-mesh/istio/README.md)を対象とします。互換性は[インストールガイド](../../service-mesh/istio/01-installation.md)で確認してください。一般的なKubernetes最小要件はサポート表ではありません。例は学習補助で、本番テスト済みデプロイではありません。例示の名前空間、ホスト名、ID、バックエンドエンドポイントを検証済み入力に置き換えます。

## 問1: サービスメッシュの基本概念

<details>
<summary>サービスメッシュとは何で、主な機能は何ですか？</summary>

サービスメッシュはサービス通信にインフラ層の制御と観測を追加します。ルーティング/負荷分散、明示的に予算を設定した再試行/タイムアウト、ワークロードIDと転送セキュリティ、認可、メトリクス、アクセスログ、トレース統合などを提供します。

Istioにはサイドカーとambientのデータプレーンがあり、L4/L7機能やポリシーの接続方法が異なります。多くの制御は業務ロジック変更を要しませんが、アプリはトレースコンテキスト伝播、安全な終了、永続的な冪等性に引き続き関与します。メッシュは非冪等な再試行を自動的に安全にせず、全可観測性バックエンドをインストールするわけでもありません。

</details>

## 問2: Istioアーキテクチャ

<details>
<summary>コントロールプレーンとデータプレーンの役割は何ですか？</summary>

- **Istiod**はサービス/設定状態を監視し、設定を変換してプロキシに配布します。CRDオブジェクトはKubernetesが永続化します。ワークロード証明書の発行/更新は、Istiodに設定したCA統合を使います。
- **サイドカーモード**は参加アプリケーションPodごとにEnvoyを配置し、捕捉したトラフィックを扱います。
- **Ambientモード**はL4転送/IDにノードレベルztunnel、対応L7機能に任意のEnvoy waypointを使います。
- **ゲートウェイ**は選択したIngress/Egress経路を扱います。そのDeployment/コントローラーはルーティング設定リソースとは別です。

「全トラフィックが捕捉される」かは除外、プロトコル、参加状態の確認が必要です。普遍的な85%リソース削減はありません。実プロキシ数、requests/limits、使用量、waypoint容量、ノードへの配置効率、運用費用を比較します。[アーキテクチャ](../../service-mesh/istio/03-architecture.md)と[ambientのリソースモデル](../../service-mesh/istio/advanced/01-ambient-mode.md)を参照してください。

</details>

## 問3: トラフィック管理とArgo Rollouts統合

<details>
<summary>カナリアロールアウトでIstioルーティングとArgo分析をどう組み合わせますか？</summary>

Argoは安定版/カナリアのバックエンド選択を維持し、名前付きIstio HTTPルートの重みを変えます。Rolloutにはセレクター、Podテンプレート、実Service、名前空間の参加、対応VirtualServiceも必要です。以下は[完全なロールアウトガイド](../../service-mesh/istio/advanced/08-argo-rollouts.md)のホストベース例を使う、**Rollout.spec下の断片のみ**です。

```yaml
strategy:
  canary:
    stableService: test-stable
    canaryService: test-canary
    maxSurge: 1
    maxUnavailable: 0
    trafficRouting:
      istio:
        virtualService:
          name: test
          routes:
          - primary
    steps:
    - setWeight: 10
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 50
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
    - setWeight: 80
    - pause:
        duration: 5m
    - analysis:
        templates:
        - templateName: success-rate
        args:
        - name: service-name
          value: test-canary
        - name: namespace
          value: rollouts-demo
```

以下の名前付き成功率テンプレートは有限回の分析です。両プロキシを二重計上しないようreporterを片側に限定し、**カナリアService**のリクエスト量とHTTP可用性の両方を確認します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.95
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

Prometheusバックエンドが存在し、該当プロキシをスクレイプする必要があります。サイドカー例はsource-reporter HTTPメトリクスと実カナリアトラフィックを期待します。ambient L4経路だけではこのL7測定値は提供されません。

ArgoのPrometheus結果は配列なので、長さ確認後にのみresult[0]を調べます。空、NaN、無限大の結果を通してはいけません。分子のゼロへのフォールバックは全失敗トラフィックを扱い、量の判定はゼロ/欠損トラフィックを正常と扱うのを防ぎます。ここでの「可用性」は5xxとコード0を除外し、業務成功や2xxのみの応答を保証しません。

旧スカラーresult >= 0.95、未指定providerアドレス、欠けたレイテンシーテンプレート、不完全Rolloutでは完全な自動化手順になりませんでした。failureLimitは**許容失敗数**です。2は2回許可して3回目で失敗します。例は0を使います。実反応時間は測定間隔、コントローラー調整、ルート伝播に依存し、即時ロールバックの約束ではありません。

</details>

## 問4: セキュリティ機能

<details>
<summary>mTLS、認可、JWT検証はどう異なりますか？</summary>

PeerAuthenticationは受け入れるワークロード受信mTLSを制御し、クライアントの送信TLSポリシーは作りません。以下の名前空間ポリシーは呼び出し元がSTRICTに対応済みという前提です。メッシュのルート名前空間に置くと影響は広がります。

```yaml
apiVersion: security.istio.io/v1
kind: PeerAuthentication
metadata:
  name: default
  namespace: app
spec:
  mtls:
    mode: STRICT
```

**サイドカー参加済み**のバックエンドPodに対し、これらのポリシーはフロントエンドワークロードID、検証済みJWT、許可GETパスを同時に要求します。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-default-deny
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: backend-read
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  action: ALLOW
  rules:
  - from:
    - source:
        principals:
        - cluster.local/ns/app/sa/frontend
        requestPrincipals:
        - '*'
    to:
    - operation:
        methods:
        - GET
        paths:
        - /api/*
---
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: backend-jwt
  namespace: app
spec:
  selector:
    matchLabels:
      app: backend
  jwtRules:
  - issuer: https://auth.example.com
    jwksUri: https://auth.example.com/.well-known/jwks.json
    audiences:
    - backend-api
```

最初は選択バックエンドへの空の**ALLOW**ポリシーで、ALLOWルールに一致するまでデフォルト拒否となります。後続allowより優先する明示DENYではありません。他の一致ALLOWポリシーがアクセスを広げ得るため、全ポリシーを確認します。

RequestAuthenticationは提供JWTを検証しますが、それだけではJWTなし要求も受け入れます。ここで検証済みJWTを必須にするのはrequestPrincipals条件です。issuer、JWKS URL、audienceは実プロバイダーに置き換えるプレースホルダーです。ワークロードprincipalとJWT principalは異なるIDです。

ambientのL7ポリシーには対応waypointへの接続が必要です。サイドカーのセレクターベースHTTPポリシーをztunnelへコピーしないでください。targetRefs、移行、信頼境界は[セキュリティガイド](../../service-mesh/istio/security/README.md)を参照します。

</details>

## 問5: GatewayとIngress

<details>
<summary>ゲートウェイのTLS終端とアプリルーティングはどう設定しますか？</summary>

例はKubernetes Gateway APIでなく**Istio Gateway**を使います。ゲートウェイDeployment、一致するPodラベル、Serviceポートは設定済みである必要があります。アプリはbookinfo、ゲートウェイワークロードと認証情報はistio-ingressにあります。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: bookinfo-gateway
  namespace: istio-ingress
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 443
      name: https
      protocol: HTTPS
    tls:
      mode: SIMPLE
      credentialName: bookinfo-secret
    hosts:
    - bookinfo.example.com
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - bookinfo.example.com
    tls:
      httpsRedirect: true
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: bookinfo
  namespace: bookinfo
spec:
  hosts:
  - bookinfo.example.com
  gateways:
  - istio-ingress/bookinfo-gateway
  http:
  - route:
    - destination:
        host: productpage.bookinfo.svc.cluster.local
        port:
          number: 9080
    timeout: 10s
    retries:
      attempts: 0
```

SIMPLEが下流TLSを終端し、その後VirtualServiceがHTTPルーティングを使います。HTTPリスナーは許可した例のドメインのみリダイレクトします。書き込みを含めルートの再試行を明示無効にします。使用前に所有ドメインと実名前空間/Service/セレクター値を置き換えます。

```bash
kubectl -n istio-ingress create secret tls bookinfo-secret \
  --key=bookinfo.key \
  --cert=bookinfo-fullchain.pem
```

既存証明書/キーをまとめるもので、証明書発行やクライアント信頼の確立はしません。SAN、チェーン、有効期限、ゲートウェイの認証情報アクセスを確認します。Kubernetes Gateway APIはこのスキーマでなく、GatewayClass/Gateway/HTTPRoute接続とコントローラー状態を使います。

</details>

## 問6: 可観測性ツール

<details>
<summary>テレメトリーコンポーネントは何を測定し、何を設定する必要がありますか？</summary>

Prometheusはメトリクスを収集し、Grafanaはダッシュボードを表示し、Kialiは設定済みテレメトリーとメッシュ状態を使います。Jaegerなどのトレースバックエンドは設定済みprovider/collector経由で送られたトレースを保存します。これらは統合先であり、Istioデフォルトプロファイルが自動インストールするツールではありません。

以下のクエリはapp内reviewsのsource-reporterストリーム1つを選びます。レイテンシー出力は**秒**、通信量は**リクエスト/秒**、エラーは5xxとコード0を含みます。

```promql
# latency
histogram_quantile(0.95, sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))) / 1000

# traffic
sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# error
(sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app",response_code=~"5..|0"}[5m])) or vector(0)) / sum(rate(istio_requests_total{reporter="source",destination_service_name="reviews",destination_service_namespace="app"}[5m]))

# cpu
sum(rate(container_cpu_usage_seconds_total{namespace="app",container="istio-proxy",pod!=""}[5m]))
```

CPUクエリはistio-proxyを含む架空Pod名でなく、**container**ラベルを選択します。結果は消費CPUコア数で、それ自体は飽和率ではありません。limits/容量やスロットリングと比較します。対応kubelet/cAdvisorメトリクスが必要です。空/ゼロ通信の分母はno-data/NaNとなり、健全性の証明ではありません。分子のフォールバックが0を意味するのは正の合計がある場合だけです。

トレースには実OTLP gRPC receiverと名前付きproviderを設定し、Telemetryで選択します。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  meshConfig:
    enableTracing: true
    extensionProviders:
    - name: otel
      opentelemetry:
        service: otel-collector.observability.svc.cluster.local
        port: 4317
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: tracing
  namespace: app
spec:
  tracing:
  - providers:
    - name: otel
    randomSamplingPercentage: 1.0
```

IstioOperatorブロックはistioctlインストール入力で、collectorやJaegerをデプロイしません。1%サンプリングは例示で、普遍的目標ではありません。アプリはコンテキストを伝播する必要があります。変更前にバックエンドプロトコル、保持、サンプリング費用を調べます。

ダッシュボードコマンドはインストール済みで検出可能なバックエンドに接続するだけです。

```bash
istioctl dashboard kiali
istioctl dashboard prometheus
istioctl dashboard grafana
istioctl dashboard jaeger
```

</details>

## 問7: Ambientモード

<details>
<summary>ambientとサイドカーモードはどう異なりますか？</summary>

| 観点 | サイドカー | Ambient |
|---|---|---|
| 配置 | 参加アプリPodごとにEnvoyを併設 | ノードレベルztunnelと選択waypoint |
| L4転送 | ワークロードプロキシ | ztunnel/HBONE |
| L7機能 | 対応Envoy機能とAPI範囲 | 適切なwaypointと対応接続/APIが必要 |
| リソース | Pod数、ワークロード、設定に依存 | ノード、waypointデプロイ/容量、ワークロードに依存 |
| 導入 | 対象Podへの注入/再作成 | CNIと参加の前提条件。既存サイドカー移行には管理されたロールアウトが必要 |
| 性能 | 実ワークロードを測定 | L4/L7経路を別測定。固定の優位性や節約率はない |

[ambientインストール/移行ガイド](../../service-mesh/istio/advanced/01-ambient-mode.md)を使います。任意の共有インストールへprofile=ambientを適用しdefaultにラベルを付けるだけでは、安全な完全移行手順ではありません。CNI互換性、NetworkPolicy/HBONE、競合サイドカーラベル、waypoint機能、実効参加状態を確認します。

```bash
kubectl get namespace app --show-labels
istioctl ztunnel-config workloads -n istio-system
```

これらの読み取り専用確認自体はワークロードを参加させず、L7ポリシー適用も証明しません。Service数、Pod数、固定の「ノードあたり50MB」では使用量や節約を十分に予測できません。

</details>

## 問8: 耐障害性パターン

<details>
<summary>外れ値検出、接続プール制限、レート制限はどう異なりますか？</summary>

外れ値検出は観測障害に基づき異常エンドポイントを除外します。接続プールのサーキットブレーカーは接続数、保留リクエスト、アクティブリクエストなど選択リソースを制限します。毎秒リクエスト数のクォータは課しません。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
```

現在のフィールドはconsecutive5xxErrorsです。連続失敗検出は即時経路で動作でき、intervalは毎回除外前に30秒待つ約束ではありません。再除外でbaseEjectionTimeが増える場合があり、プロキシごとのエンドポイント/容量動作も重要です。maxEjectionPercentを全体可用性保証と読まないでください。

9080の**サイドカー受信**HTTPリスナーでは、以下のローカルトークンバケット例は初期バースト容量100、毎秒10トークン補充です。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: reviews-local-rate-limit
  namespace: app
spec:
  workloadSelector:
    labels:
      app: reviews
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        portNumber: 9080
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
          '@type': type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
          stat_prefix: http_local_rate_limiter
          token_bucket:
            max_tokens: 100
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            runtime_key: local_rate_limit_enabled
            default_value:
              numerator: 100
              denominator: HUNDRED
          filter_enforced:
            runtime_key: local_rate_limit_enforced
            default_value:
              numerator: 100
              denominator: HUNDRED
```

型URL、ワークロード/リスナー/ルーター一致、enable/enforce比率は例の必須部分です。設定しても有効化/適用しないバケットは実効制限になりません。デフォルトではプロキシプロセス単位なので、レプリカ数に応じて総容量が増え、メッシュ全体のクォータではありません。waypointでのEnvoyFilter使用は未対応です。グローバル制限にはレート制限サービスと一致するdescriptorが必要です。[レート制限](../../service-mesh/istio/resilience/02-rate-limiting.md)を参照します。

</details>

## 問9: EKSのローカリティ負荷分散

<details>
<summary>ローカリティ優先は何を提供し、何を保証しませんか？</summary>

ローカリティはエンドポイント/送信元のトポロジー情報で適切な宛先を優先します。前のreviews DestinationRuleの**代替**である以下は、外れ値検出とリージョン/ゾーン優先順位を使います。

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: reviews
  namespace: app
spec:
  host: reviews.app.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        http2MaxRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
    loadBalancer:
      localityLbSetting:
        enabled: true
        failoverPriority:
        - topology.kubernetes.io/region
        - topology.kubernetes.io/zone
```

1つのローカリティ設定でdistributeとfailoverまたはfailoverPriorityを組み合わせないでください。80/20 distributeは正常時も意図的に20%をリモートへ送り、「障害時のみリモート」ではありません。フェイルオーバーには検出済みで到達可能なエンドポイントと十分な容量が必要です。Service選択から除外された、またはレジストリにないリモートAZ/クラスターには届きません。

```bash
kubectl get nodes -L topology.kubernetes.io/region,topology.kubernetes.io/zone
```

実ラベルとプロキシエンドポイントのローカリティを確認します。AZ名はAWSアカウント間で異なる場合があるため、物理ゾーン比較には適切なAZ-ID対応を使います。費用は通信量と正確なEC2/ロードバランサー/ネットワーク経路に依存します。ローカリティ有効化で普遍的な$0.01/GB、固定レイテンシー、85%節約が成立するわけではありません。

</details>

## 問10: Amazon EKS統合とベストプラクティス

<details>
<summary>EKSにIstioをインストール・運用する前に何を確認しますか？</summary>

1. 正確にサポートされるIstio/Kubernetes/EKSの共通範囲と固定CLI/チャートを使います。組み込みproductionプロファイルはありません。所有者を通じてレビュー済みHelm/istioctl設定を使います。
2. ロードバランサーコントローラーを特定します。AWS Load Balancer Controller、EKS Auto Mode、従来プロビジョニングは所有権/設定が異なります。Serviceセレクター/ポートを実ゲートウェイに合わせます。TLS終端をNLBかゲートウェイかで決め、TLSリスナーへ平文を送ったり意図しない二重TLSを加えたりしないようにします。
3. AWS権限はロードバランサーコントローラーやテレメトリーcollectorなど、AWS APIを呼ぶコンポーネントに限定します。Envoyは転送だけでIAMロールを必要としません。IRSAまたは対応EKS Pod Identity統合の信頼と権限を設定します。アノテーションだけでは完全設定ではありません。
4. 必要な方向のネットワーク経路だけを開きます。プロキシ捕捉ポートはセキュリティグループで無差別公開するリストではありません。該当するWebhook/xDS、ヘルスチェック、実Ingress/ambient経路を含めます。
5. ワークロードの証拠からIstiod/プロキシのサイズを決め、スケジューリング/可用性容量を確保します。PDBは一部の自発的中断に対応し、レプリカ数だけではゾーン分散や全障害からの保護は保証されません。
6. メトリクス、ログ、トレースを別々に設定します。Fluent Bitのcloudwatch_logs出力断片だけではContainer Insightsでも完全なCRI入力/パーサー/IAM/ログストリームのパイプラインでもありません。

コントロールプレーンHPAとプロキシrequests/limitsのインストール入力例は次のとおりです。

```yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
spec:
  components:
    pilot:
      k8s:
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
        hpaSpec:
          minReplicas: 3
          maxReplicas: 5
  values:
    global:
      proxy:
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 1Gi
```

3–5レプリカとリソース量は例で、検証済み本番サイズではありません。HPAメトリクス、配置、使用可能容量を確認します。実際のリソース/請求測定でambientと設定範囲を評価してください。一般的な85%や30–50%の節約保証はありません。

完全手順は[AWS統合ガイド](../../service-mesh/istio/04-aws-integration.md)と[ベストプラクティス](../../service-mesh/istio/best-practices.md)を使います。

</details>

## 追加問題: 段階的デリバリー

<details>
<summary>段階的デリバリーの分析が役立つ条件と限界は何ですか？</summary>

完全なロールアウトには実ルーティング対象、安定した容量、明示的な分析引数、有限で意味のある測定方針が必要です。以下はカナリアService例を拡張し、リクエスト量、HTTP可用性、P95レイテンシーを確認します。

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: comprehensive-analysis
  namespace: rollouts-demo
spec:
  args:
  - name: service-name
  - name: namespace
  metrics:
  - name: request-volume
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 20
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: sum(increase(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: http-availability
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] >= 0.99
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code!~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
  - name: latency-p95
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.5
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          histogram_quantile(0.95,
            sum by (le) (rate(istio_request_duration_milliseconds_bucket{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
          ) / 1000
    count: 5
  - name: http-error-rate
    interval: 30s
    successCondition: len(result) == 1 && !isNaN(result[0]) && !isInf(result[0]) && result[0] <= 0.01
    failureLimit: 0
    provider:
      prometheus:
        address: http://prometheus.istio-system.svc.cluster.local:9090
        query: |-
          (sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}",response_code=~"5..|0"}[2m])) or vector(0))
          /
          sum(rate(istio_requests_total{reporter="source",destination_service_name="{{args.service-name}}",destination_service_namespace="{{args.namespace}}"}[2m]))
    count: 5
```

完全Rolloutの対応analysisステップから参照します。不完全な例で欠けたセレクター/テンプレート/Serviceの代わりにはなりません。しきい値は例示です。クエリセレクター、単位、通信量、業務SLOが一致する必要があります。

測定失敗、providerエラー、不確定結果、中止、その後の旧リビジョンのデプロイは別状態です。AnalysisRun/Rollout状態を確認し、すべて即時ロールバックと呼ばないでください。中止はDB書き込みや他の副作用を元に戻せません。コントローラー間隔、安定版バックエンドの可用性、設定伝播が復旧を制約します。

自動化は反復判断を減らせますが、どのメトリクス判定も普遍的な安全なデプロイを成立させず、人の診断不要を保証しません。無通信、欠損系列、全失敗、NaN/無限大、復旧をテストします。[完全ロールアウトガイド](../../service-mesh/istio/advanced/08-argo-rollouts.md)に周囲のリソースと検証境界があります。

</details>

## 自己評価

11の解答から復習するトピックを特定してください。高得点は本番運用の準備完了の証拠ではありません。管理された環境で設定レビューと実践検証を含めます。

## 学習資料

- [保守されているIstioドキュメント](../../service-mesh/istio/README.md)
- [Istio公式ドキュメント](https://istio.io/latest/docs/)
- [Argo RolloutsのIstio統合](https://argo-rollouts.readthedocs.io/en/stable/features/traffic-management/istio/)
- [Argo分析の意味](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [Prometheusインスタントクエリ結果](https://argo-rollouts.readthedocs.io/en/stable/analysis/prometheus/)
- [Istio TLS設定](https://istio.io/latest/docs/ops/configuration/traffic-management/tls-configuration/)
- [Istio APIリファレンス](https://istio.io/latest/docs/reference/config/)
