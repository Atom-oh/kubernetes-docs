# EnvoyFilter

> **検証ベースライン**: Istio 1.31.0、Kubernetes 1.32～1.37。sidecarとIstio Envoy gateway
> **最終レビュー日**: 2026年10月16日

EnvoyFilterは、Envoy proxyの設定を直接カスタマイズするための高度な機能です。

## 目次

1. [概要](#overview)
2. [構造](#structure)
3. [主なユースケース](#main-use-cases)
4. [X-Forwarded-Forとホップ設定](#x-forwarded-for-and-hop-settings)
5. [静的レスポンスの設定](#static-response-configuration)
6. [実践例](#practical-examples)
7. [ベストプラクティス](#best-practices)
8. [トラブルシューティング](#troubleshooting)

## 概要 {#overview}

以下はそれぞれ独立した代替例です。すべての例を同じワークロードに適用すると、filter、route、policyが積み重なります。実際のnamespace、label、listenerを確認し、既存設定と統合したうえで、テスト環境において生成されたEnvoy設定とリクエストの動作を検証してください。EnvoyFilterはEnvoy内部APIに依存するため、Istioをアップグレードするたびに再検証が必要です。ambient waypointではサポートされません。

EnvoyFilterを使うと、次のことができます。
- カスタムheaderの追加、変更、削除
- Rate limiting
- 外部認可
- WASM pluginの統合

## 構造 {#structure}

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: custom-filter
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                request_handle:headers():replace("x-custom-header", "value")
              end
```

## 主なユースケース {#main-use-cases}

### 1. カスタムheaderの追加

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: add-header
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_OUTBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                request_handle:headers():replace("x-client-service", "myapp")
              end
```

### 2. Rate limiting

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: ratelimit
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
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
            tokens_per_fill: 10
            fill_interval: 1s
          filter_enabled:
            default_value: {numerator: 100, denominator: HUNDRED}
          filter_enforced:
            default_value: {numerator: 100, denominator: HUNDRED}
```

これは各proxyプロセス内のbucketで、初期burstは100 token、補充は毎秒10 tokenです。レプリカをまたいだグローバル制限ではありません。明示的に有効化し、enforceの割合を設定すると拒否が有効になります。

### 3. WASM plugin

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: wasm-filter
  namespace: default
spec:
  workloadSelector:
    labels:
      app: myapp
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
        name: envoy.filters.http.wasm
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm
          config:
            vm_config:
              runtime: "envoy.wasm.runtime.v8"
              code:
                local:
                  filename: "/var/local/lib/wasm-filters/my_plugin.wasm"
```

このローカルWasm例は、proxyコンテナ内の指定パスに、互換性のあるmoduleが読み取り専用volume経由ですでにmountされていることを前提とします。applicationコンテナ内のファイルが自動的に見えるわけではなく、このYAMLがmoduleをダウンロードするわけでもありません。module、ABI、runtime、障害時の動作を検証してください。配布には[WasmPlugin API](https://istio.io/latest/docs/reference/config/proxy_extensions/wasm-plugin/)を優先してください。

## X-Forwarded-Forとホップ設定 {#x-forwarded-for-and-hop-settings}

### X-Forwarded-Forの概要

HTTP proxyは通常、自身のアドレスではなく、**proxyへ接続したクライアントのアドレス**を追加します。ALBのデフォルト`append`モードでは、クライアントが直接接続する場合、Gatewayが受け取る値は`203.0.113.5`です。CloudFront経由の場合は`203.0.113.5, 192.0.2.20`になります。Gatewayの直接のpeerはALBです。これらのドキュメント用アドレスは、実際のCloudFront IP範囲ではありません。

### XFFの設定方法

`gatewayTopology.numTrustedProxies`を使う公式の[gateway topology設定](https://istio.io/latest/docs/ops/configuration/traffic-management/network-topologies/)を優先してください。次の内容は**Pod templateの断片**なので、既存のingress Deploymentに統合してください。影響するGateway Podを再起動し、有効な設定を確認します。

```yaml
# Existing ingress Deployment: spec.template fragment, not a complete Deployment
metadata:
  annotations:
    proxy.istio.io/config: |
      gatewayTopology:
        numTrustedProxies: 1
```

より低レベルの代替手段として、このEnvoyFilterを使えます。両方の方法で競合する値を設定しないでください。実際のingress namespaceと`istio: ingressgateway` Pod labelを確認します。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: gateway-xff-config
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: NETWORK_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
    patch:
      operation: MERGE
      value:
        name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          use_remote_address: true
          xff_num_trusted_hops: 1
          skip_xff_append: false
          via: istio-gateway
```

| オプション | 意味 |
|---|---|
| `use_remote_address: true`、hop 0 | 直接接続したpeerを使用する |
| `true`、hop N>0 | 受信したXFFの右からN番目のアドレスを使う |
| `false`、hop N | 右からN+1番目のアドレスを使う |
| XFFアドレスが不足 | 直接接続したpeerにfallbackする。アクセスが許可されるという意味ではない |
| `skip_xff_append: true` | ここではXFFへの追加を省略する。アドレス選択とは別の設定 |
| `via` | request/responseにVia識別子を追加する。認証機能ではない |

サービスが内部向けだからという理由だけで`use_remote_address: false`を設定しないでください。呼び出し元が指定したXFFを信頼する可能性があります。まず実際の接続とheader変換を確認してください。Gatewayの判断は**Gateway自身のrequest streamに属する性質**であり、backend Envoyの信頼された`remote.ip`に自動的に引き継がれるわけではありません。

### シナリオ別の設定

以下の値は、`use_remote_address: true`であり、各HTTP proxyが接続peerを追加し、迂回経路が遮断されていることを前提とします。

| 経路 | Gatewayが受け取るXFF | 直接接続したpeer | 信頼するhop数 |
|---|---|---|---|
| Client → ALB → Gateway | `203.0.113.5` | ALB | 1 |
| Client → CloudFront → ALB → Gateway | `203.0.113.5, 192.0.2.20` | ALB | 2 |
| Client → CloudFront → NLB → ALB → Gateway | NLBのALB target構成でclient addressが維持される場合は同じ | ALB | 2 |
| Client → Gatewayへ直接接続 | 呼び出し元が任意に指定した値 | Client | 0 |

NLBはL4で動作し、XFFを書き換えません。ただし、すべてのNLB構成で元のsocket addressが維持されるという意味ではありません。target type、サポート対象のlistener/target port、アドレス保持、実際に受信するheaderを検証してください。ALBの`preserve`/`remove`モード、追加CDN、PROXY protocol、別経路については個別の分析が必要です。

### 実際のクライアントIPを抽出する例

XFFの一番左の値を信頼済みとして解析しないでください。上記の信頼境界を設定したGatewayでは、診断目的に限りEnvoyが計算したアドレスを使います。Lua APIが返すのは**string**です。IPv6やport表記が含まれる場合もあり、アドレスobjectではありません。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: gateway-client-address
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
            subFilter:
              name: envoy.filters.http.router
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(handle)
                local address = handle:streamInfo():downstreamRemoteAddress()
                handle:headers():replace("x-client-address", address)
              end
```

`x-client-address`はapplication認証の仕組みではありません。信頼されたGatewayが値を上書きし、backendへの直接アクセスを防いでいる場合に限り、診断目的で使ってください。アドレス/headerのlogについて、プライバシーと保持期間の上限を定めてください。

### アプリごとの選択的なIP制限（Gateway + AuthorizationPolicy）

元のIPを判定する**Gatewayで**、HTTP Hostに基づいてApp F/Gへの外部IP制限を適用します。App A～EはこのDENY ruleに一致しません。既存のmesh/namespace/Gateway policyとapplication認証も引き続き適用されます。アプリ固有のpolicy fileがないからといって、アクセスが保証されるわけではありません。

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: restricted-app-ingress
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: DENY
  rules:
  - from:
    - source:
        notRemoteIpBlocks: ["203.0.113.0/24"]
    to:
    - operation:
        hosts:
        - "app-f.example.com"
        - "app-f.example.com:*"
        - "app-g.example.com"
        - "app-g.example.com:*"
```

GatewayでHTTPを終端し、それぞれのHostを意図したappへrouteする必要があります。HTTPを終端する専用Gatewayを使ってください。TCP passthrough listenerが混在する場合は、policyを確認済みのworkload portに限定します。HTTP属性が欠けるとDENY ruleに一致することがあります。F/Gを公開しうる別名、wildcard host、他のrouteも確認してください。たとえば、実際のGateway service accountだけを許可するmTLSとAuthorizationPolicyで、backendへの迂回を別途防いでください。IP制限はユーザー認証の代わりにはなりません。

### XFFに基づくIPアクセス制御

以下は**専用API Gateway**で使う、それぞれ独立した代替例です。どれかのALLOW policyがworkloadを選択した後は、requestが一致するALLOW ruleを必要とします。複数のALLOW policyは加算的に適用されます。他のappへの影響を考慮せずに、これらを共有Gatewayへ重ねて適用しないでください。

#### 1. IP allow listとdeny list

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-ip-allowlist
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.10/32", "203.0.113.11/32", "2001:db8:1234::/48"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-ip-denylist
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: DENY
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.11/32"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
```

ALLOW対象の`203.0.113.11`もDENY ruleによって拒否されます。IstioはCUSTOM、DENY、ALLOWの順に評価します。AUDITは判定を変えません。実際の接続に応じて、信頼されたXFF/PROXY protocolから得る元アドレスには`remoteIpBlocks`、受信packetのsourceには`ipBlocks`を使ってください。

#### 2. IP + path + method

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-path-ip-policy
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.10/32"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/admin", "/admin/*"]
  - from:
    - source:
        remoteIpBlocks: ["10.0.0.0/8"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/api/v1/*"]
        methods: ["GET"]
  - to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/api/v1/public/*"]
        methods: ["GET", "POST"]
```

`/admin`と`/admin/*`の両方を保護してください。public routeのsource条件を省くと、IPv4に加えてIPv6も対象になります。`10.0.0.0/8` ruleが意味を持つのは、そのアドレスが実際に観測されるprivate-client経路に限られます。internet NATの背後で隠されたアドレスを復元することはできません。

### XFFの検証とdebug

```bash
# Local CLI reads the effective gateway configuration; no curl binary in proxy required.
istioctl proxy-config listeners <gateway-pod> -n istio-system -o json |
  jq '.. | objects |
      select(.["@type"]? == "type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager") |
      {useRemoteAddress, xffNumTrustedHops, skipXffAppend}'

# Through the real ALB/CDN path, from a source outside the allowed NAT range:
curl -i https://app-f.example.com/
curl -i -H "X-Forwarded-For: 203.0.113.10" https://app-f.example.com/
# Both must be denied. A user-supplied header must not grant access.

# Run this separately from the real approved NAT egress:
curl -i https://app-f.example.com/

kubectl get authorizationpolicy -n istio-system
kubectl logs -n istio-system <gateway-pod> -c istio-proxy
```

許可されないsourceからのXFFに許可IPを前置しても、requestは失敗しなければなりません。許可されたaccessは、実際に承認されたNAT egressからテストしてください。偽造headerを付けた直接Gatewayへのrequestが成功するなら、それは検証の成功ではなく迂回を示します。IPv6、XFFなし/短いXFF、Gatewayへの直接接続、Host別名、別routeもテストします。

access logでは、`%DOWNSTREAM_DIRECT_REMOTE_ADDRESS%`（socket peer）、`%DOWNSTREAM_REMOTE_ADDRESS%`（計算されたアドレス）、`%REQ(X-FORWARDED-FOR)%`、`%RESPONSE_CODE_DETAILS%`を区別してください。Telemetryでlogを有効にし、選択したmesh access-log providerのformatを設定します。[ProxyConfigとobservability設定](#envoy-configuration-with-proxyconfig)を参照してください。

### セキュリティ上の考慮事項

各下流hopを、ALB → Gateway、CloudFront → ALBなど、**実際に信頼するproxy**に限定してください。security group/networkとorigin accessの制御を使います。hop数は送信者を認証しません。また、`use_remote_address: true`だけではspoofingを防げません。後段のLuaでheaderを削除しても、すでに計算されたアドレスや、それ以前の認可判定は取り消せません。

## 静的レスポンスの設定 {#static-response-configuration}

特定のrequestに対して、backend serviceを経由せずに直接静的レスポンスを返せます。メンテナンスモード、エラーページ、health checkレスポンスなどに利用できます。

### 静的レスポンスの概要

![クライアントrequestがEnvoy proxyに到着し、一致条件を満たす場合はEnvoyが直接クライアントに静的レスポンスを返し、それ以外の場合だけbackend serviceへproxyする流れを示す図。](../../../.gitbook/assets/en-service-mesh-istio-advanced-03-envoy-filter-7.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-istio-advanced-03-envoy-filter-7.html)

### ユースケース

1. **メンテナンスモード**: 503 Service Unavailableを返す
2. **Health check endpoint**: 200 OKを返す
3. **カスタムエラーページ**: JSONまたはHTMLのエラーレスポンス
4. **テスト/mock response**: 特定pathへの事前定義済みresponse
5. **即時拒否**: 認証失敗時に401 Unauthorizedをすぐに返す

### 実装方法の選択ガイド

Istioには静的レスポンスを実装する方法がいくつかあります。

| 方法 | 使用する場合 | 利点 | 欠点 |
|------|----------|------|------|
| **VirtualService** | 単純な静的レスポンス、またはrouting ruleとの統合 | 宣言的で理解しやすい | カスタマイズに制限がある |
| **AuthorizationPolicy** | IP/headerに基づくaccess制御 | security policyと統合できる | 静的レスポンス専用ではない |
| **EnvoyFilter** | 上記の方法では不十分な場合のみ | 柔軟性が最大 | 複雑でupgrade時のリスクがある |

**推奨:** 可能な場合はまず**VirtualService**と**AuthorizationPolicy**を使い、必要な場合にのみEnvoyFilterを使ってください。

### VirtualServiceによる静的レスポンスの実装

#### 1. 基本的な静的レスポンス（directResponse）

時刻は固定された例示用文字列であり、現在時刻ではありません。生成されたroute設定におけるresponse bodyの上限を確認してください。Istio 1.31では、これらのoutbound VirtualService routeの上限は1 MiBです。変更していないEnvoyのデフォルトは4 KiBです。大きな静的bodyはproxyのmemoryを消費します。これらのmesh-outbound VirtualServiceは独立した代替例です。同じhostに重ねて適用しないでください。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service
  namespace: default
spec:
  hosts:
  - api-service
  http:
  # Maintenance mode
  - match:
    - uri:
        exact: "/api/v1"
    - uri:
        prefix: "/api/v1/"
    directResponse:
      status: 503
      body:
        string: |
          {
            "error": {
              "code": "SERVICE_UNAVAILABLE",
              "message": "The service is currently under maintenance",
              "timestamp": "2025-11-26T10:00:00Z",
              "retry_after": 3600
            }
          }
    headers:
      response:
        set:
          content-type: "application/json"
          retry-after: "3600"
```

**結果:**
```text
$ curl -i http://api-service/api/v1/users
HTTP/1.1 503 Service Unavailable
content-type: application/json
retry-after: 3600

{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "The service is currently under maintenance",
    "timestamp": "2025-11-26T10:00:00Z",
    "retry_after": 3600
  }
}
```

#### 2. Health check endpoint

静的な200 responseが確認するのはproxy routingだけです。Kubernetes readinessやALB target healthにapplicationのhealthを反映させる必要がある場合は、実際のbackend probeを使ってください。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-health
  namespace: default
spec:
  hosts:
  - api-service
  http:
  # Health check path
  - match:
    - uri:
        exact: "/health"
    directResponse:
      status: 200
      body:
        string: "OK"

  # Normal traffic
  - route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

#### 3. 特定pathの遮断

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: block-admin
  namespace: default
spec:
  hosts:
  - api-service
  http:
  # Block Admin paths
  - match:
    - uri:
        exact: "/admin"
    - uri:
        prefix: "/admin/"
    directResponse:
      status: 403
      body:
        string: |
          {
            "error": "Access to admin endpoints is forbidden"
          }
    headers:
      response:
        set:
          content-type: "application/json"

  # Normal traffic
  - route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

#### 4. Fault injectionによるエラーのシミュレーション

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: fault-injection
  namespace: default
spec:
  hosts:
  - api-service
  http:
  - fault:
      abort:
        httpStatus: 503
        percentage:
          value: 100  # Apply to 100% traffic
    route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

### AuthorizationPolicyによるaccess制御

`ipBlocks`が評価するのは、受信したpacketのsourceです。sourceを保持するL4 ingressでは元のclientの場合もありますが、ALBなどのproxy/NATが間にある場合はそれらのアドレスとなることがあります。XFF由来のアドレスには、上記のGateway `remoteIpBlocks`の例を使ってください。選択されたALLOW policyは、不一致のrequestをすでに拒否します。対応するDENYを重複して作る必要はありません。

#### カスタムDENY response

これは**このGatewayがローカルで生成するすべてのHTTP 403 response**を統一します。backendの403や、あらゆるTCP拒否を変換するものではありません。bodyの文面からIP拒否だと推定せず、汎用の`FORBIDDEN` codeを使ってください。先行するRBAC filterがrequestを拒否すると、後続のLua filterが実行されない場合があります。既存のmapperと統合するときはHCM `local_reply_config`と順序/scopeを確認してください。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: custom-local-forbidden
  namespace: istio-system
spec:
  workloadSelector:
    labels:
      istio: ingressgateway
  configPatches:
  - applyTo: NETWORK_FILTER
    match:
      context: GATEWAY
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
    patch:
      operation: MERGE
      value:
        name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          local_reply_config:
            mappers:
            - filter:
                status_code_filter:
                  comparison:
                    op: EQ
                    value:
                      default_value: 403
                      runtime_key: local_reply_403
              body_format_override:
                json_format:
                  error: "Access denied"
                  code: "FORBIDDEN"
```

### ProxyConfigによるEnvoy設定 {#envoy-configuration-with-proxyconfig}

`networking.istio.io`のProxyConfig resourceは、meshの`ProxyConfig` messageとは異なるfieldを持ちます。`concurrency`、`environmentVariables`、`image`などのoptionを公開しますが、任意のlogging、tracing、connection pool fieldは無効です。変更を反映するには、影響するPodの再起動が必要です。

#### Workloadのthread数とobservability

```yaml
apiVersion: networking.istio.io/v1beta1
kind: ProxyConfig
metadata:
  name: api-service-config
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  concurrency: 4
---
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: api-observability
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  accessLogging:
  - providers:
    - name: envoy
  tracing:
  - providers:
    - name: otel-tracing
    randomSamplingPercentage: 1
```

`envoy` access-log providerと`otel-tracing` trace providerは、meshのextensionProvidersにあらかじめ登録されている必要があります。そこでlog format/outputとOTLP endpoint/TLSを設定します。`concurrency: 4`はworker threadを4つ要求します。CPU容量と負荷を確認してください。head samplingを1%に設定しても、traceがすべて保持されるとは限りません。

#### 統計情報と終了猶予時間

```yaml
# Existing application Deployment: spec.template fragment
metadata:
  annotations:
    proxy.istio.io/config: |
      terminationDrainDuration: 5s
      proxyStatsMatcher:
        inclusionRegexps:
        - ".*outlier_detection.*"
        - ".*upstream_rq_retry.*"
        inclusionSuffixes:
        - upstream_rq_timeout
```

既存application DeploymentのPod templateに統合し、影響するPodを再起動してください。Kubernetesのtermination grace periodは、applicationのshutdownとproxy drainingに十分な長さが必要です。Envoy統計情報を追加すると、series数とmemoryコストが増加します。

#### 宛先のconnection pool

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: api-outbound-pool
  namespace: default
spec:
  host: api-service.default.svc.cluster.local
  trafficPolicy:
    connectionPool:
      tcp:
        connectTimeout: 10s
        maxConnections: 10000
```

これは指定した宛先へのproxyごとのoutbound connection設定です。Gateway全体の同時request数上限や、application timeoutではありません。負荷をかけて例示の上限値を検証してください。

### 統合例: VirtualService + AuthorizationPolicy

これは独立した**HTTP labの断片**です。port 80を公開する既存ingress Gateway Deployment/Service、healthy endpointを持つService port 8080の`default/api-service`、動作するDNS/ALB routing、上記の検証済みXFF信頼設定が必要です。外部利用には、レビュー済みのTLS境界とbackend迂回の防止も必要です。この断片はデプロイも本番負荷テストも実施していません。

認可とroutingは同じGatewayで評価されます。public、health、retired pathは明示的に許可し、それ以外の一致しないpathは拒否します。`/health`が示すのはproxy routeへの到達性だけであり、application/databaseのhealthではありません。一般routeのmesh retryは0に設定されています。このrouteはwriteを含む場合があります。

```yaml
apiVersion: networking.istio.io/v1
kind: Gateway
metadata:
  name: api-lab
  namespace: istio-system
spec:
  selector:
    istio: ingressgateway
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts: ["api.example.com"]
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-access-control
  namespace: istio-system
spec:
  selector:
    matchLabels:
      istio: ingressgateway
  action: ALLOW
  rules:
  - from:
    - source:
        remoteIpBlocks: ["203.0.113.10/32"]
    to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/api/v1/admin", "/api/v1/admin/*"]
  - to:
    - operation:
        hosts: ["api.example.com", "api.example.com:*"]
        paths: ["/health", "/api/v0/*", "/api/v1/public/*"]
---
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: api-service-routes
  namespace: default
spec:
  hosts: ["api.example.com"]
  gateways: ["istio-system/api-lab"]
  http:
  - match:
    - uri:
        exact: /health
    directResponse:
      status: 200
      body:
        string: '{"status":"proxy-route-reachable"}'
    headers:
      response:
        set:
          content-type: application/json
          cache-control: no-store
  - match:
    - uri:
        prefix: /api/v0/
    directResponse:
      status: 410
      body:
        string: '{"error":"API v0 is retired","supported_versions":["v1","v2"]}'
    headers:
      response:
        set:
          content-type: application/json
          cache-control: no-store
  - route:
    - destination:
        host: api-service.default.svc.cluster.local
        port:
          number: 8080
    timeout: 30s
    retries:
      attempts: 0
```

### Luaによる動的な静的レスポンス

Lua scriptは、条件に基づいて動的に静的レスポンスを生成できます。

#### メンテナンス時間帯の自動検出

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: maintenance-window
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              local function is_maintenance(hour)
                return hour >= 2 and hour < 4
              end

              function envoy_on_request(request_handle)
                -- Current time (UTC)
                local current_hour = tonumber(os.date("!%H"))

                -- Daily maintenance window 2-4 AM
                if is_maintenance(current_hour) then
                  request_handle:respond(
                    {[":status"] = "503",
                     ["content-type"] = "application/json",
                     ["retry-after"] = "60",
                     ["cache-control"] = "no-store"},
                    '{"error": "Maintenance in progress", "window": "02:00-04:00 UTC"}'
                  )
                end
              end
```

#### request headerに基づくresponse

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: header-based-response
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                local api_version = request_handle:headers():get("x-api-version")

                -- Unsupported API version
                if api_version and api_version == "v1" then
                  request_handle:respond(
                    {[":status"] = "410",
                     ["content-type"] = "application/json"},
                    '{"error": "API v1 is deprecated", "supported_versions": ["v2", "v3"]}'
                  )
                end
              end
```

### VirtualServiceとの統合

1つの`directResponse`でメンテナンス状態とbodyを設定できます。宛先側のLua filterで、送信元側VirtualServiceがすでに生成したfaultを書き換えることはできません。また、response headerにrequestの`:path`は含まれません。これは独立したmesh-outbound例であり、認可の仕組みではありません。ingressでは前述の例のように、gatewayと外部hostを明示的にbindしてください。

```yaml
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: maintenance-response
  namespace: default
spec:
  hosts: ["api-service"]
  http:
  - match:
    - uri:
        exact: /maintenance
    - uri:
        prefix: /maintenance/
    directResponse:
      status: 503
      body:
        string: '{"message":"Service under maintenance"}'
    headers:
      response:
        set:
          content-type: application/json
          cache-control: no-store
          retry-after: "60"
  - route:
    - destination:
        host: api-service
    retries:
      attempts: 0
```

### 実践的なシナリオ

#### シナリオ1: Blue/Green deployment中の通信を遮断する

これは、選択したv1 workloadへのすべてのinbound HTTP routeを意図的に503へ変更します。ゼロダウンタイムの切り替えやconnection drainを実装するものではありません。Protobufの`MERGE`はRoute actionのoneofをdirect_responseに変更しますが、先行filterによる拒否やTCP経路は制御しません。`cutoff_date`は固定の例示値であり、実際のdeployment予定に合わせて置き換えてください。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: deployment-block
  namespace: production
spec:
  workloadSelector:
    labels:
      app: api-service
      version: v1  # Block only old version
  configPatches:
  - applyTo: HTTP_ROUTE
    match:
      context: SIDECAR_INBOUND
    patch:
      operation: MERGE
      value:
        direct_response:
          status: 503
          body:
            inline_string: |
              {
                "message": "This version is being deprecated",
                "migration": {
                  "new_endpoint": "https://api-v2.example.com",
                  "cutoff_date": "2025-12-31"
                }
              }
        response_headers_to_add:
        - header:
            key: "Content-Type"
            value: "application/json"
        - header:
            key: "X-Migration-Required"
            value: "true"
```

#### シナリオ2: Rate limit超過時に429を返す

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: ratelimit-response
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  # Rate Limit filter
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.local_ratelimit
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
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
          local_rate_limit_per_downstream_connection: false
          # Custom 429 response
          status:
            code: 429
          response_headers_to_add:
          - header:
              key: x-local-rate-limit
              value: "true"
            append_action: OVERWRITE_IF_EXISTS_OR_ADD
```

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: local-rate-limit-json
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
  configPatches:
  - applyTo: NETWORK_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: envoy.filters.network.http_connection_manager
    patch:
      operation: MERGE
      value:
        name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          local_reply_config:
            mappers:
            - filter:
                status_code_filter:
                  comparison:
                    op: EQ
                    value:
                      default_value: 429
                      runtime_key: local_reply_429
              body_format_override:
                json_format:
                  error: "Too many requests"
                  code: "RATE_LIMIT_EXCEEDED"
```

両方のresourceは同じworkloadを選択します。mapperはローカル生成の429 responseをJSON形式にしますが、upstreamの429 responseは変更しません。tokenの補充によって、各呼び出し元の再試行がいつ成功するかは保証されません。そのため、根拠のない`Retry-After: 60`は返しません。

#### シナリオ3: Canary deploymentのテストresponse

分離されたテストworkloadでのみ使用してください。呼び出し元はこのheaderを自分で指定できます。200 responseが返っても、認証、backendの実行、versionの健全性を証明しません。運用環境に公開する場合は、認可とheaderの信頼性を別途検証する必要があります。

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: canary-test-response
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
      version: canary
  configPatches:
  - applyTo: HTTP_FILTER
    match:
      context: SIDECAR_INBOUND
      listener:
        filterChain:
          filter:
            name: "envoy.filters.network.http_connection_manager"
            subFilter:
              name: "envoy.filters.http.router"
    patch:
      operation: INSERT_BEFORE
      value:
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                local test_header = request_handle:headers():get("x-canary-test")

                -- Return predefined response if canary test header present
                if test_header == "dry-run" then
                  request_handle:respond(
                    {[":status"] = "200",
                     ["content-type"] = "application/json",
                     ["x-canary-version"] = "v2.0.0"},
                    '{"message": "Canary version response", "version": "v2.0.0"}'
                  )
                end
              end
```

### テストと検証

#### 静的レスポンスのテスト

選択した例を実装するproxyを実際に通るtest clientを使ってください。`/health`や説明用headerだけでは、認証/認可を検証できません。

```bash
curl -i http://api-service:8080/api/v1
curl -i http://api-service:8080/health
curl -i http://api-service:8080/admin
curl -i http://api-service:8080/admin/users
```

隔離したLua harnessで、UTC時刻のhourが1、2、3、4のときmaintenance predicateがそれぞれfalse、true、true、falseを返すことをテストします。Pod/nodeの時計は変更しないでください。実際のfilter integration testでは、隔離環境で制御されたtest-time inputかレビュー済みの一時functionを使い、終わったら通常functionに戻してください。

Rate limitingでは、既知のproxyを1つ対象にし、初期100 token、毎秒10 tokenの補充、経過時間、実際の429件数を同時に測定します。curlを順番に150回実行しても、429が発生するとは限りません。レプリカ数と負荷分散は別途テストが必要です。

#### Envoy設定の確認

```bash
# 1. Verify static response route
istioctl proxy-config routes <pod-name> -n default -o json | \
  jq '.[] | .virtualHosts[]? | .routes[]? | select(.directResponse != null)'

# 2. Check full route configuration
istioctl proxy-config routes <pod-name> -n default

# 3. Verify EnvoyFilter applied
kubectl get envoyfilter -n default maintenance-window -o yaml

# 4. Verify via Envoy Admin API
kubectl port-forward -n default <pod-name> 15000:15000
# Run in a second local terminal while port-forward is active:
curl http://127.0.0.1:15000/config_dump | jq '.configs[] | select(.["@type"] == "type.googleapis.com/envoy.admin.v3.RoutesConfigDump")'
```

### ベストプラクティス {#best-practices}

1. **明確なエラーメッセージ**:
   - 原因と解決方法を利用者に示す
   - `Retry-After` headerで再試行時刻を指定する

2. **一貫したエラー形式**:
   - すべてのerror responseで同じJSON schemaを使う
   - HTTP status codeとerror codeの整合性を維持する

3. **Loggingとmonitoring**:
   - 静的responseを返したときに記録する
   - 静的responseの頻度をmetricで追跡する

4. **段階的な適用**:
   - maintenance modeへ切り替えるときは段階的に適用する
   - 全体に適用する前にcanary deploymentでテストする

5. **Rollback計画**:
   - レビュー済みの設定を復元し、xDSでの受理、route、requestを確認する
   - 緊急時の自動rollback scriptを用意する

### 注意点

1. **優先順位**: responseの動作は、処理するproxy、filter順序、生成routeによって変わります。
2. **性能**: Lua scriptはrequestごとに実行されるため、性能への影響を考慮してください。
3. **セキュリティ**: error messageに機密情報を含めないようにします。
4. **Caching**: 静的responseにも`Cache-Control` headerが必要です。
5. **Metrics**: response_code/details/flagsとreporterを確認してください。静的response用のmetric familyが別途作成されるとは限りません。

## 実践例 {#practical-examples}

### 例1: Request/Response Logging

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: request-response-logging
  namespace: default
spec:
  workloadSelector:
    labels:
      app: api-service
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
        name: envoy.filters.http.lua
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.http.lua.v3.Lua
          default_source_code:
            inline_string: |
              function envoy_on_request(request_handle)
                request_handle:logInfo("Request method: " .. (request_handle:headers():get(":method") or "unknown"))
              end

              function envoy_on_response(response_handle)
                response_handle:logInfo("Response: " .. (response_handle:headers():get(":status") or "unknown"))
              end
```

### 例2: JWT検証

IstioのRequestAuthenticationとAuthorizationPolicyを使ってください。issuer/audience/JWKS URLの例示値を実際のprovider値に置き換え、検証側からDNS/TLS/JWKSへ到達できることを確認します。RequestAuthenticationだけではtokenがないrequestも受け入れます。ALLOW policyは検証済みprincipalを要求します。同じworkloadに別のALLOW policyがあり、より広いaccessを許可していないことも確認してください。

```yaml
apiVersion: security.istio.io/v1
kind: RequestAuthentication
metadata:
  name: api-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  jwtRules:
  - issuer: https://issuer.example.com/
    audiences: ["api.example.com"]
    jwksUri: https://issuer.example.com/.well-known/jwks.json
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: api-require-jwt
  namespace: default
spec:
  selector:
    matchLabels:
      app: api-service
  action: ALLOW
  rules:
  - from:
    - source:
        requestPrincipals: ["*"]
```

## ベストプラクティス

1. **workloadSelectorを使う**: 対象を特定のworkloadに限定する
2. **最初にテスト環境で確認する**: 本番適用前に十分にテストする
3. **Istio versionとの互換性を確認する**: versionごとにAPIを確認する
4. **性能を監視する**: EnvoyFilter追加後の性能を監視する

## トラブルシューティング {#troubleshooting}

```bash
# Check EnvoyFilter
kubectl get envoyfilter -A

# Verify Envoy configuration
istioctl proxy-config listeners <pod-name> -n <namespace> -o json

# Check logs
kubectl logs -n <namespace> <pod-name> -c istio-proxy
```

## 参照

- [EnvoyFilter Reference](https://istio.io/latest/docs/reference/config/networking/envoy-filter/)
- [Envoy Documentation](https://www.envoyproxy.io/docs/envoy/latest/)
- [WASM Plugins](https://istio.io/latest/docs/concepts/wasm/)
- [XFF / trusted addresses](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/headers)
- [Istio ingress authorization](https://istio.io/latest/docs/tasks/security/authorization/authz-ingress/)
- [ALB X-Forwarded headers](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/x-forwarded-headers.html)
- [CloudFront request behavior](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/RequestAndResponseBehaviorCustomOrigin.html)
- [NLB application-load-balancer targets](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/application-load-balancer-target.html)
- [Lua filter API](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/lua_filter)
- [Local reply configuration](https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_conn_man/local_reply)
- [ProxyConfig resource](https://istio.io/latest/docs/reference/config/networking/proxy-config/)
- [Telemetry API](https://istio.io/latest/docs/reference/config/telemetry/)
- [Mesh ProxyConfig and statistics](https://istio.io/latest/docs/reference/config/istio.mesh.v1alpha1/)
- [RequestAuthentication](https://istio.io/latest/docs/reference/config/security/request_authentication/)
- [Istio 1.31 direct-response limit](https://raw.githubusercontent.com/istio/istio/1.31.0/pilot/pkg/networking/core/route/route.go)
