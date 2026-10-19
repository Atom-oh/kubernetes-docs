# Kubernetes Gateway API

> **APIベースライン**: Gateway API v1.6 Standard。コントローラーがサポートする正確なバンドルを選択してください。
> **最終更新日**: 2026年10月16日

## 概要

Gateway APIは、既存のIngress APIの制限を克服し、より表現力と拡張性に優れたネットワークルーティング機能を提供するために設計された、Kubernetes向けの次世代Ingress APIです。SIG-Networkが開発しており、Istio、Cilium、Envoy Gatewayなど、さまざまな実装でサポートされています。

### Ingress APIの制限

| 問題 | 説明 |
|---------|-------------|
| **表現力の制限** | HTTPルーティング以外のTCP/UDP/gRPCのサポートが不十分 |
| **責任の複合** | RBAC/IngressClassでアクセスを制限できますが、リスナーとルートに関する責務の分離が明確ではありません |
| **アノテーションの乱用** | 実装固有の機能をアノテーションで処理するため、移植性が低下します |
| **拡張性の制限** | 新しいプロトコルや機能を追加することが困難 |
| **Namespaceをまたぐルーティング** | Namespaceをまたぐルーティングが複雑 |

### Gateway APIのメリット

![Gateway APIの4つの設計目標：表現力、責任の分離、移植性、拡張性。](../.gitbook/assets/en-networking-04-gateway-api-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-04-gateway-api-0.html)

表現力、責任の分離、移植性、拡張性は、それぞれ独立した設計目標です。実際にサポートされる機能は、コントローラーと適合プロファイルによって異なります。各リソースを変更できるユーザーは、Kubernetes RBACとAdmissionポリシーによって制御されます。

## リソースモデル

Gateway APIは階層型のリソースモデルを使用します。

![一般的な実装におけるGatewayClass、Gateway、RouteとバックエンドServiceの関係。Gatewayインフラストラクチャの実際の構成はコントローラー固有です。](../.gitbook/assets/en-networking-04-gateway-api-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-04-gateway-api-1.html)

この図は、リソース間の関係と一般的なGatewayのデプロイモデルを示しています。Gatewayが常に1つのクラウドロードバランサーに対応するとは限りません。IstioではプロキシのDeployment/Serviceをプロビジョニングできますが、VPC Latticeではサービスネットワークに対応付けられます。**参照先Namespace**の所有者は、ReferenceGrantを使って、Namespaceをまたぐバックエンド/Secretへのアクセスを許可します。

### 役割の分離

| 役割 | 管理するリソース | 責任 |
|------|------------------|----------------|
| **インフラストラクチャプロバイダー** | GatewayClass | 基本的なインフラストラクチャ構成を定義する |
| **クラスターオペレーター** | Gateway | GatewayインフラストラクチャとRouteのアタッチポリシーを管理する |
| **参照先Namespaceの所有者** | ReferenceGrant | 所有するバックエンド/Secretへの参照を許可する |
| **アプリケーション開発者** | HTTPRoute、GRPCRouteなど | アプリケーションのルーティングルールを定義する |

## GatewayClass

GatewayClassは、Gatewayの作成時に使用するコントローラーと構成を定義します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: istio
spec:
  controllerName: istio.io/gateway-controller
  description: Istio Gateway Controller for production workloads
```

GatewayClassは、すでにインストールされているコントローラーを選択します。このクラスを作成しても、コントローラーはインストールされません。以下の定義は代替案です。`Accepted`条件がtrueのクラスを使用し、例にあるクラス名は、クラスターで受け入れられている名前に置き換えてください。

`parametersRef`のサポートと、そのgroup/kindは実装によって異なります。Istio 1.31では、GatewayごとのConfigMapは、そのGatewayのNamespaceにある`Gateway.spec.infrastructure.parametersRef`で指定します。クラス全体のデフォルト値には、IstioのルートNamespaceにある`gateway.istio.io/defaults-for-class`ラベル付きのConfigMapを使用します。以下のALB→Istioの例では、Gatewayごとに設定する方法を示します。

### 実装ごとのGatewayClass

```yaml
# Istio
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: istio
spec:
  controllerName: istio.io/gateway-controller
---
# Cilium
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium
spec:
  controllerName: io.cilium/gateway-controller
---
# AWS Gateway API Controller
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
# Envoy Gateway
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: envoy-gateway
spec:
  controllerName: gateway.envoyproxy.io/gatewayclass-controller
---
# Contour
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: contour
spec:
  controllerName: projectcontour.io/gateway-controller
---
# NGINX Gateway Fabric
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: nginx
spec:
  controllerName: gateway.nginx.org/nginx-gateway-controller
```

## Gateway

Gatewayは、トラフィックを処理するインフラストラクチャとリスナーを記述します。プロキシのワークロード、管理対象ロードバランサー、サービスネットワークのどれに対応付けられるかは、コントローラーによって異なります。

### Gatewayの基本構成

以下は個別の構成例であり、すべてのRouteをまとめて適用する単一の構成ではありません。同じホスト/リスナー上でRouteが重複すると、優先順位が変わることがあります。まず、選択したコントローラーと互換性のあるCRDをインストールし、`gateway-system`を作成したうえで、指定されたService、準備完了状態のエンドポイント、TLS Secretを用意してください。証明書は構成済みのDNS名をカバーする必要があります。データプレーンのService公開設定、DNS、プラットフォームのネットワーク制御を構成してください。GatewayClassや要求されたIPアドレスだけでは、外部アドレスは予約されません。

HTTP/gRPC/TCP/TLSの例ではIstio 1.31を使用しています。UDPの例では別のEnvoy Gatewayインスタンスを使用します。Istio 1.31はUDPリスナーを明示的に拒否するためです。Envoy Gateway 1.9にはGateway API 1.6.1と、公開されているKubernetesのバージョン組み合わせが必要です。共有CRDのバージョン/チャネルを変更する前に、内容を確認してください。

基本例のNamespaceには`gateway-access: "true"`が設定されています。これは**Namespaceラベル**であり、これを変更する権限はGatewayアクセスを管理する管理者に限定してください。`allowedRoutes`はアプリケーションのクライアントを認証しません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    gateway-access: 'true'
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: production-gateway
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: tls-cert
        namespace: gateway-system
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
```

### Gatewayの高度な構成

以下は`multi-protocol-gateway`という別のGatewayです。下記のgRPC、TLS、TCPのRouteは、それぞれ対応するリスナー名にアタッチされます。データベース用とその他のTCP用には別々のリスナーがあるため、どちらも同じL4リスナーを取り合うことなく使用できます。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: multi-protocol-gateway
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
  - name: https-wildcard
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: wildcard-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: HTTPRoute
  - name: grpc
    protocol: HTTPS
    port: 443
    hostname: grpc.example.com
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: grpc-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: GRPCRoute
  - name: tcp-passthrough
    protocol: TLS
    port: 8443
    tls:
      mode: Passthrough
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: TLSRoute
  - name: tcp
    protocol: TCP
    port: 9000
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: TCPRoute
  - name: database
    protocol: TCP
    port: 5432
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: TCPRoute
```

### TLSモード

Terminateは、Gatewayで下流側のTLS接続を終端します。バックエンドへの接続は別途構成し、サポートされているBackendTLSPolicyなどを使ってHTTPまたはTLSを使用できます。Passthroughでは、`mode: Passthrough`の`TLS`リスナーを使用し、バックエンドでTLSを終端します。`mode`を変更するだけで、`HTTPS`リスナーをpassthroughに切り替えることはできません。

| モード | 説明 | ユースケース |
|------|-------------|----------|
| **Terminate** | GatewayでTLSを終端 | 標準的なHTTPS |
| **Passthrough** | TLSをバックエンドに転送 | エンドツーエンド暗号化 |

```yaml
# TLS Terminate example
listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
        - kind: Secret
          name: server-cert
---
# TLS Passthrough example
listeners:
  - name: tls-passthrough
    protocol: TLS
    port: 443
    tls:
      mode: Passthrough
```

## HTTPRoute

HTTPRouteは、HTTP/HTTPSトラフィックのルーティングルールを定義します。

### HTTPRouteの基本例

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: basic-route
  namespace: production
spec:
  # Gateway to attach to
  parentRefs:
    - name: production-gateway
      namespace: gateway-system
      sectionName: https  # Target specific listener

  # Host matching
  hostnames:
    - "api.example.com"
    - "www.example.com"

  # Routing rules
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api/v1
      backendRefs:
        - name: api-v1-service
          port: 80

    - matches:
        - path:
            type: PathPrefix
            value: /api/v2
      backendRefs:
        - name: api-v2-service
          port: 80

    # Default path
    - backendRefs:
        - name: default-service
          port: 80
```

### 高度なマッチングルール

1つの`matches`項目内のフィールドはAND条件で評価され、複数の項目はOR条件で評価されます。PathPrefixは任意の文字列のプレフィックスではなく、パス要素に対してマッチします。RegularExpressionのサポートと構文は実装によって異なります。以下のデモ用テナントヘッダーは、どのクライアントでも指定できるルーティングセレクターであり、管理アプリケーションの認証には使えません。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: advanced-matching
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: Exact
        value: /health
    backendRefs:
    - name: health-service
      port: 80
  - matches:
    - path:
        type: RegularExpression
        value: /users/[0-9]+
    backendRefs:
    - name: user-service
      port: 80
  - matches:
    - headers:
      - name: X-Version
        value: v2
    backendRefs:
    - name: api-v2-service
      port: 80
  - matches:
    - queryParams:
      - name: debug
        value: 'true'
    backendRefs:
    - name: debug-service
      port: 80
  - matches:
    - method: POST
      path:
        type: PathPrefix
        value: /api/data
    backendRefs:
    - name: write-service
      port: 80
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /api/data
    backendRefs:
    - name: read-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /admin
      headers:
      - name: X-Demo-Tenant
        type: Exact
        value: operations
    backendRefs:
    - name: admin-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /api
    - path:
        type: PathPrefix
        value: /v1
    backendRefs:
    - name: api-service
      port: 80
```

### フィルター

ヘッダー変更機能は、リテラル値を設定します。`X-Example-Source: gateway-demo`は固定の識別子であり、一意なリクエストIDを生成するものではありません。IDには、プロキシ/アプリケーションのトレース機能を使用してください。ミラーリングの例では独自の`/mirror`パスを使うため、先行する`/api`ルールに隠されることはありません。GETリクエストをシャドウバックエンドにコピーし、そのバックエンドのレスポンスは無視します。副作用を分離し、シャドウサービスにコピーされるデータ/認証情報を確認してください。公開キャッシュヘッダーを使うのは、実際に公開キャッシュしても安全なコンテンツに限ります。

フィルターを使うと、リクエスト/レスポンスを変更できます。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: filtered-route
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    filters:
    - type: RequestHeaderModifier
      requestHeaderModifier:
        add:
        - name: X-Example-Source
          value: gateway-demo
        set:
        - name: X-Api-Version
          value: v1
        remove:
        - X-Internal-Header
    backendRefs:
    - name: api-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /public
    filters:
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        add:
        - name: Cache-Control
          value: public, max-age=3600
        set:
        - name: X-Content-Type-Options
          value: nosniff
    backendRefs:
    - name: public-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /old-api
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /new-api
        hostname: new-api.example.com
    backendRefs:
    - name: new-api-service
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /legacy
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        hostname: new.example.com
        port: 443
        statusCode: 301
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /modern
  - matches:
    - method: GET
      path:
        type: PathPrefix
        value: /mirror
    filters:
    - type: RequestMirror
      requestMirror:
        backendRef:
          name: shadow-service
          port: 80
    backendRefs:
    - name: main-service
      port: 80
```

### トラフィック分割（重み）

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: canary-route
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - app.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

### タイムアウトと再試行

v1.6 Standardスキーマには`timeouts`が含まれますが、`HTTPRoute.rules.retry`は含まれません。Experimentalスキーマでは再試行フィールドが追加されますが、Admissionや実装に関する要件は別途あります。以下の例で設定するのはGETリクエストの予算だけです。`backendRequest`は、0以外に設定した合計`request`予算を超えてはなりません。

再試行フィールドを省略しても、クライアント、Gateway、メッシュプロキシ、SDKのいずれも再試行しないという保証にはなりません。特に冪等でない書き込みでは、該当する各レイヤーを構成し、動作を確認してください。再試行回数を0にしても、最小値が1であるExperimental v1.6の`retry.attempts`フィールドを無効化する有効な方法にはなりません。実装で文書化されている制御機能と、アプリケーションの冪等性動作を使用してください。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: resilient-route
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
      method: GET
    timeouts:
      request: 30s
      backendRequest: 25s
    backendRefs:
    - name: api-service
      port: 80
```

## GRPCRoute

バックエンドは、想定されるgRPC/HTTP2トランスポートと適切なTLS構成を提供する必要があります。ポート番号を指定しただけでは、その動作は構成されません。

gRPCトラフィックのルーティングルールを定義します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata:
  name: grpc-route
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: grpc
  hostnames:
  - grpc.example.com
  rules:
  - matches:
    - method:
        service: myapp.UserService
    backendRefs:
    - name: user-grpc-service
      port: 50051
  - matches:
    - method:
        service: myapp.OrderService
        method: CreateOrder
    backendRefs:
    - name: order-grpc-service
      port: 50052
  - matches:
    - headers:
      - name: x-environment
        value: staging
    backendRefs:
    - name: staging-grpc-service
      port: 50051
  - backendRefs:
    - name: default-grpc-service
      port: 50051
```

## TCPRoute

TCPトラフィックのルーティングを定義します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: database-route
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: database
  rules:
  - backendRefs:
    - name: database-service
      port: 5432
---
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: tcp-loadbalance
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: tcp
  rules:
  - backendRefs:
    - name: tcp-backend-1
      port: 9000
      weight: 50
    - name: tcp-backend-2
      port: 9000
      weight: 50
```

## TLSRoute

TLSパススルーのトラフィックルーティングを定義します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: TLSRoute
metadata:
  name: tls-passthrough-route
  namespace: production
spec:
  parentRefs:
  - name: multi-protocol-gateway
    namespace: gateway-system
    sectionName: tcp-passthrough
  hostnames:
  - secure.example.com
  rules:
  - backendRefs:
    - name: secure-backend
      port: 8443
```

## UDPRoute

このシナリオでは、`envoy-gateway`クラスが受け入れられた状態のEnvoy Gatewayコントローラー、そのコントローラーと互換性のあるGateway APIバンドル、およびUDPバックエンドの`dns-service`がインストールされている必要があります。UDPポート5300を公開し、バックエンドポート53にルーティングします。EnvoyのUDPプロキシは透過型ではないため、バックエンドからはGatewayの送信元IP/ポートが見えます。プラットフォームのロードバランサー/ServiceがこのUDP公開をサポートしていることを確認してください。

UDPトラフィックのルーティングを定義します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: udp-gateway
  namespace: gateway-system
spec:
  gatewayClassName: envoy-gateway
  listeners:
  - name: udp
    protocol: UDP
    port: 5300
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
      kinds:
      - kind: UDPRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: UDPRoute
metadata:
  name: dns-route
  namespace: production
spec:
  parentRefs:
  - name: udp-gateway
    namespace: gateway-system
    sectionName: udp
  rules:
  - backendRefs:
    - name: dns-service
      port: 53
```

## ReferenceGrant

ReferenceGrantは、**参照されるServiceまたはSecretを含むNamespace**で、そのNamespaceの所有者が作成します。`from`は参照元のgroup/kind/namespaceを選択し、`to.name`で参照先の名前を制限できます。Grantは追加的に適用され、参照を許可するものであって、アプリケーションの呼び出し元を許可するものではありません。

NamespaceをまたぐRoute→Gatewayのアタッチには、ReferenceGrantではなく、`parentRefs`とGatewayリスナーの`allowedRoutes`によるハンドシェイクを使用します。以下の例のように、バックエンドと証明書の参照にはReferenceGrantを使用します。指定された`shared-api` Serviceと`shared-tls` Secretは、あらかじめ存在している必要があります。Grantだけでは作成されません。

ReferenceGrantは、Namespaceをまたぐ参照を許可します。

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-routes-to-backend
  namespace: backend-services
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: production
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: staging
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-gateway-to-secrets
  namespace: cert-management
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: Gateway
    namespace: gateway-system
  to:
  - group: ''
    kind: Secret
    name: shared-tls
```

## 実装の比較

### 主な実装

| 実装 | コントローラー | 機能 |
|----------------|------------|----------|
| **Istio** | istio.io/gateway-controller | Service Mesh統合、高度なトラフィック管理 |
| **Cilium** | io.cilium/gateway-controller | L7処理にEnvoyを使用するCiliumネットワーキング |
| **Envoy Gateway** | gateway.envoyproxy.io/gatewayclass-controller | Envoyベース、標準準拠 |
| **AWS Gateway API Controller** | application-networking.k8s.aws/gateway-api-controller | VPC Lattice統合 |
| **Contour** | projectcontour.io/gateway-controller | Envoyベース、シンプルな構成 |
| **NGINX Gateway Fabric** | gateway.nginx.org/nginx-gateway-controller | NGINXベース |
| **Traefik** | traefik.io/gateway-controller | 動的構成 |

### バージョン別の実装上の注意

APIのリリースチャネル、機能のCore/Extended/実装固有のサポートレベル、コントローラーの適合プロファイルは、それぞれ異なる概念です。CRDがフィールドを受け付けても、コントローラーがその機能を実装しているとは限りません。該当する場合は`Accepted`、`ResolvedRefs`、`Programmed`などのリソース条件も含め、公開されている適合結果を確認してください。

| 確認済みの実装 | 検証済みの範囲と重要な制限 |
|---|---|
| Istio **1.31.2** | HTTP/gRPCおよびv1 TCP/TLS Routeに対応。UDPリスナーは明示的に非サポート。構成可能なEnvoyデータプレーンですが、Gateway APIのすべての拡張がサポートされる保証はありません |
| Cilium **1.20.3** | TCPRoute/UDPRouteを含むGateway API **1.6.3**。L7処理にはEnvoyを使用し、Ciliumネットワーキングと組み合わせます |
| Envoy Gateway **1.9.2** | Gateway API **1.6.1**。公開されているKubernetesのバージョン範囲は**1.33–1.36**です。UDPルーティングとTLSパススルーを、文書化されたトランスポート動作とともにサポートします |
| AWS Load Balancer Controller **3.6.0** | Gateway API **1.6.0**。ALBはHTTP/gRPCを、NLBはL4 Routeを処理します。NLBリスナーごとに、アタッチされたL4 Routeのうち最も古いものだけが対象となります。リスナーごとに1つのRouteを使用してください |
| AWS Gateway API Controller **2.1.3** | VPC Lattice統合。v2.1にはGateway API **1.5**+が必要です。HTTPRoute、GRPCRoute、TLSRouteをサポートします。TCPリソースアクセスは、汎用的なTCPRoute/UDPRouteサポートではなく、Latticeの別個のリソース構成モデルです |
| Contour **1.33.7** | Gateway API **1.3.0**を組み込んでおり、Kubernetes **1.32–1.34**でリリーステスト済みです。HTTP/gRPC/TCP/TLS Routeを文書化しています。新しいバンドルをそのまま適用するのではなく、対応するチャネル/プロビジョニング構成を使用してください |
| NGINX Gateway Fabric **2.8.0** | Gateway API **1.6.3**。公開されているKubernetesの最低バージョンは**1.32**です。v1 TCPRoute/UDPRouteをサポートします（2.7.0で追加）。終了したコミュニティ版ingress-nginxとは別の製品です |

これらの注意事項は、バージョンを示さない機能の可否一覧に代わるものです。個々のフィルター、TLSポリシー、拡張機能、サポートバージョン、運用要件については、各実装のドキュメントを参照してください。Contourの同梱互換性ページには1.33.7固有の項目がありません。上記のAPI依存関係とKubernetesのバージョン範囲は、このリリースのmoduleファイルとリリースノートから取得しています。

## AWS Load Balancer ControllerのGateway APIサポート

Gateway APIは、**2026年1月23日のLBC v3.0.0**でGAになりました。既存のIngress APIとService APIも引き続きサポートされるため、Gatewayへの移行はコントローラーのアップグレードとは別に計画できます。現行のv3.6.0には、[LBCインストールガイド](./03-aws-lb-controller.md)に記載された、互換性のあるGateway APIとLBC Gateway CRDが必要です。EKS Auto Modeには別個のマネージド実装があります。セルフマネージドLBCの機能が、そのままAuto Modeにも当てはまるわけではありません。

終了したコントローラーは、Kubernetesコミュニティの**ingress-nginx**プロジェクトです。このプロジェクトのメンテナンスは2026年3月に終了しました。これは、Kubernetes Ingress APIやF5のその他のNGINX製品が終了したという意味ではありません。

v3.0のリリースノートにある`keepTLSSecret=false`の回避策は、cert-managerの所有権バグの影響を受ける**旧バージョンを使い続けるユーザー**を対象としたものです。v3.0にアップグレードしたユーザーには修正が適用されているため、この追加作業は不要でした。過去の回避策をすべてのアップグレードに適用せず、現行のChartにおける証明書管理オプションに従ってください。

### LBC v3.4.0の移行ツール

**2026年6月3日**のリリースで、実際に使用できる`lbc-migrate` CLIとMigration Consoleが導入されました。これらの対象は、稼働中の**LBC Ingress**リソースです。すべてのIngress実装に対応する汎用コンバーターではありません。

- `lbc-migrate`はファイルを読み込みます。また、`--from-cluster`を指定すると、クラスターのリソースを一覧表示/取得します。サポート対象のアノテーションを変換し、Gateway APIリソースを出力します。デフォルトの出力にはLBC Gatewayのdry-runアノテーションが含まれます。
- Migration Consoleは、コントローラーが生成したリソース計画を比較します。適切な計画アノテーション、機能構成、読み取りアクセスが必要です。計画はアクセス制限やマスキングが必要になる場合がある構成データとして扱ってください。
- レビュー済みの稼働中のGatewayマニフェストを適用すると、既存のALBに加えて**新しいALB**が作成されます。これらを検証し、フロントエンドのトラフィックは別途切り替えてください。1つのHTTPRoute内のバックエンド重みでは、このフロントエンド移行は行えません。

選択したLBCリリースからビルドしたバイナリを使う場合、ファイルベースの変換は次のコマンドで開始できます。

```bash
lbc-migrate -f ingress.yaml --output-dir ./gateway-output/
```

このコンバーターは、既存のDeployment/Serviceを生成せず、Ingressのすべてのアノテーションを再検証するわけでもありません。サポートされないアノテーション、Service/IngressClassParamsの上書き、NamespaceをまたぐIngressGroupのメンバーシップ、ルールの優先順位、TLS設定を確認してください。旧ALBにすでに関連付けられている外部ターゲットグループを、新しいALBにも同時に単純にアタッチすることはできません。互換性のある複製/切り替え戦略を計画してください。

このツールは移行のワークフローを提供するものであり、ダウンタイムがゼロになることを保証するものではありません。[バージョン別移行ガイド](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/ingress2gateway/migrate_from_ingress.md)と[CLIリファレンス](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/ingress2gateway/lbc_migrate_reference.md)を参照してください。

## IngressからGateway APIへの移行

### 段階的な移行ガイド

#### ステップ1: 既存のIngressを分析する

以下は、Istio Gateway APIへの手動構成変換を説明するための、**過去のコミュニティ版ingress-nginxの入力例**です。新たにingress-nginxをインストールする推奨例ではなく、上記のLBC専用コンバーターへの入力でもありません。設定名だけでなく、実際のリクエスト動作を維持してください。

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: 'true'
  namespace: default
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /api/v1
        pathType: Prefix
        backend:
          service:
            name: api-v1
            port:
              number: 80
      - path: /api/v2
        pathType: Prefix
        backend:
          service:
            name: api-v2
            port:
              number: 80
```

#### ステップ2: GatewayとGatewayClassを作成する

新しいGatewayの名前は`migration-gateway`です。既存の`api-tls` Secretは`default`に残します。このGatewayのNamespaceから参照できるように、そのNamespaceにReferenceGrantを作成して明示的に許可します。`api.example.com`に対して有効な証明書を用意してください。`default` Namespaceには、ルートアタッチメントのセレクターとして使用できる組み込みの名前ラベルがあります。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: production
spec:
  controllerName: istio.io/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: migration-tls
  namespace: default
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: Gateway
    namespace: gateway-system
  to:
  - group: ''
    kind: Secret
    name: api-tls
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: migration-gateway
  namespace: gateway-system
spec:
  gatewayClassName: production
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            kubernetes.io/metadata.name: default
    hostname: api.example.com
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: api-tls
        namespace: default
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            kubernetes.io/metadata.name: default
    hostname: api.example.com
```

#### ステップ3: HTTPRouteを作成する

リダイレクトRouteはHTTPリスナーにのみアタッチします。HTTPS Routeはアプリケーションのリクエストを転送します。元の`rewrite-target: /`の例では、マッチしたリクエストパス全体が`/`に置き換わるため、変換後の例では**ReplaceFullPath**を使用します。ReplacePrefixMatchではサフィックスが保持される（`/api/v1/users` → `/users`）ため、動作が変わります。切り替え前に、ルートパス、サブパス、クエリー文字列、リダイレクトを旧アプリケーションと比較してテストしてください。

以下のリダイレクトでは、リクエストメソッド/ボディを維持するingress-nginxのデフォルトである**308**を想定しています。`http-redirect-code`の上書き設定がないか確認してください。また、この書き換えアノテーションは、そのホストで大文字と小文字を区別しない正規表現ロケーションも有効にします。一方、Gateway APIのPathPrefixは大文字と小文字を区別し、パス要素にマッチします。そのため、`/API/V1`や`/api/v10`の動作が異なる場合があります。この例は、より厳格なPathPrefixポリシーを示すもので、完全に同一のマッチング動作を実現するものではありません。クライアントが旧動作に依存している場合は、切り替え前に、サポートされる正規表現マッチまたは別の明示的な互換ルールを設計してテストしてください。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-route
  namespace: default
spec:
  parentRefs:
  - name: migration-gateway
    namespace: gateway-system
    sectionName: http
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-route-https
  namespace: default
spec:
  parentRefs:
  - name: migration-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api/v1
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplaceFullPath
          replaceFullPath: /
    backendRefs:
    - name: api-v1
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /api/v2
    filters:
    - type: URLRewrite
      urlRewrite:
        path:
          type: ReplaceFullPath
          replaceFullPath: /
    backendRefs:
    - name: api-v2
      port: 80
```

#### ステップ4: フロントエンドのトラフィックを切り替える

クライアントを移行する前に、新しいGatewayのアドレス、証明書、HTTPリダイレクト、Routeのマッチング、バックエンドの動作、可観測性を検証してください。レビュー済みのDNS/ロードバランサールーティングなど、フロントエンドに適した方法でトラフィックを切り替え、その後、障害やレイテンシーを監視します。DNSキャッシュ、永続接続、セッションを考慮してください。旧フロントエンドにトラフィックを戻す、テスト済みの手段を確保してください。

HTTPRouteのバックエンド重みは、**選択済みのGateway内**のトラフィックを制御します。この動作については、トラフィック分割の専用セクションで説明しています。フロントエンドの移行中は、クライアントが移行し、必要なドレイン/ロールバック確認が完了するまで、旧Ingress/コントローラーを残してください。

### 移行チェックリスト

- [ ] 既存のIngressアノテーションを分析する
- [ ] 実装を選択し、GatewayClassを作成する
- [ ] Gatewayリソースを作成し、リスナーを構成する
- [ ] ルーティングルールをHTTPRouteに変換する
- [ ] アタッチ用のallowedRoutesと、バックエンド/Secret参照用のReferenceGrantを構成する
- [ ] TLS証明書を移行する
- [ ] テスト済みのロールバック手順を用意したうえで、検証し、フロントエンドのトラフィックを切り替える
- [ ] 監視とログ記録を設定する
- [ ] 切り替えとドレイン/ロールバック確認が完了してから、旧Ingressリソースを削除する

## EKSのパターン

### AWS Gateway API Controller（VPC Lattice）

[ VPC Latticeガイド](./02-vpc-lattice.md)に従ってインストール済みコントローラー、レビュー済みの`AWS_IAM`ポリシーを持つ`my-network`サービスネットワーク、呼び出し元の権限、`service-stable:8080`バックエンドを使用します。Gateway名はネットワークを選択しますが、ネットワークを作成するわけではありません。この別個のRouteには、独自のLatticeサービスとドメインがあります。以下のIAMAuthPolicyはそのサービスを保護します。調整中もネットワークレベルのポリシーを維持してください。Routeに割り当てられたドメインを取得し、ガイドにある署名付きHTTPSクライアントを使用してください。`unused`証明書参照は、一般的なKubernetes Secretの読み込みではなく、このコントローラーで文書化されているAWS管理証明書の動作に基づいています。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: amazon-vpc-lattice
spec:
  controllerName: application-networking.k8s.aws/gateway-api-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: my-network
  namespace: lattice-demo
spec:
  gatewayClassName: amazon-vpc-lattice
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: unused
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: lattice-route
  namespace: lattice-demo
spec:
  parentRefs:
  - name: my-network
    sectionName: https
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /api
    backendRefs:
    - name: service-stable
      port: 8080
---
apiVersion: application-networking.k8s.aws/v1alpha1
kind: IAMAuthPolicy
metadata:
  name: lattice-route-auth
  namespace: lattice-demo
spec:
  targetRef:
    group: gateway.networking.k8s.io
    kind: HTTPRoute
    name: lattice-route
  policy: '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/MyAppRole"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*","Condition":{"StringLike":{"vpc-lattice-svcs:RequestPath":["/api","/api/*"]}}}]}'
```

### ALB Controllerとの併用

このトポロジーでは、アプリケーションでIstio Gatewayの動作が必要な場合に、Istio Gatewayの前段にALBを配置します。ConfigMapでは、Istioに文書化されているインフラストラクチャパラメーターを使って、生成されるServiceをClusterIPに設定します。ALB Ingressは、そのServiceと**同じNamespace**にあり、生成された名前`internal-gateway-istio`を参照します。

アプリケーションのHTTPRouteは、ラベルが設定された`production` Namespaceにあり、そこに既存の`api-service:80`があることを前提としています。ACM ARNを置き換え、LBC/ネットワークの前提条件を構成してください。この例ではALBでTLSを終端し、Istioへの接続にはHTTPを使用します。実際のGatewayトラフィックとヘルスポートを、ネットワークのセキュリティ制御で許可してください。`15021`の`/healthz/ready`はGatewayの準備状態を確認するものであり、各アプリケーションのヘルスを確認するものではありません。Routeの条件とアプリケーションのレスポンスは別々に検証してください。

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: internal-gateway-options
  namespace: istio-system
data:
  service: |
    spec:
      type: ClusterIP
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: internal-gateway
  namespace: istio-system
spec:
  gatewayClassName: istio
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
  infrastructure:
    parametersRef:
      group: ''
      kind: ConfigMap
      name: internal-gateway-options
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: alb-internal-route
  namespace: production
spec:
  parentRefs:
  - name: internal-gateway
    namespace: istio-system
    sectionName: http
  hostnames:
  - api.example.com
  rules:
  - backendRefs:
    - name: api-service
      port: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: alb-to-gateway
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP":80},{"HTTPS":443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/12345678-1234-1234-1234-123456789012
    alb.ingress.kubernetes.io/healthcheck-port: '15021'
    alb.ingress.kubernetes.io/healthcheck-path: /healthz/ready
  namespace: istio-system
spec:
  ingressClassName: alb
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: internal-gateway-istio
            port:
              number: 80
```

## APIチャネルと成熟度

### チャネルとAPIバージョンは別の概念

| Gateway API v1.6.0バンドル | 含まれるリソース/フィールド |
|---|---|
| Standard | GatewayClass、Gateway、HTTPRoute、GRPCRoute、TLSRoute、TCPRoute、UDPRoute、ReferenceGrant、BackendTLSPolicy、ListenerSet |
| Experimental | Standardの内容に加えて、HTTPRouteの再試行/セッション永続化などのExperimentalフィールド、およびXBackend、XBackendTrafficPolicy、XMesh |

現在のStandardの例では、Routeタイプに`v1`を使用しています。v1.6.0 Standardバンドルでは、以前のTLSRoute/TCPRoute/UDPRouteのalphaバージョンは、もう**提供されません**。Experimentalバンドルでは一部の非推奨バージョンが引き続き提供されるため、そこで動作するマニフェストがStandardでも動作するとは限りません。

ReferenceGrantは、「Standardなら常にv1のみ」という考えに反する例です。v1.6.0バンドルでは`v1`と`v1beta1`の両方が提供され、ストレージバージョンは`v1beta1`です。ここにあるReferenceGrantの例では、引き続き提供されているbetaバージョンを使用しています。

新しいExperimentalのXリソースでは`gateway.networking.x-k8s.io`を使用します。一方、既存リソースのExperimentalフィールドは引き続き`gateway.networking.k8s.io`に置かれる場合があります。Experimentalチャネル全体が別のgroupに移ったわけではありません。Experimentalの互換性保証はStandardとは異なり、Admissionポリシーによってチャネル/フィールドの境界が保護されます。変更を強制するために共有CRDやAdmissionポリシーを削除するのではなく、公開されているアップグレード手順を確認してください。

### v1.6リリースの背景

Gateway API v1.6.0は**2026年6月29日UTC / 2026年6月30日KST**に公開されました。TCPRouteとUDPRouteはStandardの`v1`に昇格しました。GRPCRouteとTLSRouteも、現在のStandardバンドルに含まれています。カタログで最新のバージョンを選ぶのではなく、選択した実装がサポートするバンドル/チャネルを選んでください。

## Ingress APIとの比較

| 項目 | Ingress | Gateway API |
|---|---|---|
| リソースモデル | IngressとIngressClass。リスナーとルーティングの責務は大部分が一体化 | GatewayClass、Gateway、個別のRouteタイプ |
| 認可 | Kubernetes RBAC/Admissionで所有権を制限可能 | RBAC/Admissionに加え、明示的なアタッチメントと参照のハンドシェイク |
| HTTPルーティング | 標準的なHTTPルーティング | 標準のHTTPRouteフィールド。ただし機能ごとにサポートレベルが異なる |
| TCP/UDP/gRPC | Ingress API以外のコントローラー固有の拡張機能 | 専用のAPIタイプ。実際のサポート状況はコントローラー/バージョンによる |
| TLSパススルー / トラフィック分割 / 書き換え | コントローラー固有の構成 | 関連するRoute/フィルターフィールドと実装側のサポート要件 |
| Namespaceをまたぐ参照 | 実装固有の動作 | バックエンド/SecretにはReferenceGrant、GatewayのアタッチにはallowedRoutes |
| 移植性 | アノテーションの意味の違いによって低下 | 標準フィールドと適合性によって向上。ただし拡張機能には依然として違いがある |

## ベストプラクティス

### 1. 役割の分離に従う

```yaml
# Infrastructure team: Manage GatewayClass
# Platform team: Manage Gateway
# App team: Manage HTTPRoute
```

### 2. ReferenceGrantに最小権限を適用する

```yaml
# Explicitly allow only required namespaces
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: minimal-access
  namespace: backend
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: frontend  # Specific namespace only
  to:
    - group: ""
      kind: Service
      name: specific-service  # Specific service only
```

### 3. Gatewayを分離する

```yaml
# Separate Gateway by environment
# production-gateway, staging-gateway

# Separate Gateway by protocol
# http-gateway, grpc-gateway
```

### 4. 監視を構成する

```yaml
# Prometheus metrics collection (varies by implementation)
# - Request count, latency, error rate
# - Backend status
# - TLS certificate expiry
```

---

## 参考資料

- [Gateway API公式ドキュメント](https://gateway-api.sigs.k8s.io/)
- [Gateway API GitHub](https://github.com/kubernetes-sigs/gateway-api)
- [Istio Gateway APIサポート](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)
- [Cilium Gateway API](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/gateway-api/gateway-api.rst)
- [AWS Gateway API Controller](https://github.com/aws/aws-application-networking-k8s/tree/v2.1.3/docs)
- [Envoy Gateway](https://gateway.envoyproxy.io/)

- [Gateway API 1.6のバージョン管理](https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.0/site/content/en/docs/concepts/versioning.md)
- [ReferenceGrantとアタッチメントに関する例外](https://github.com/kubernetes-sigs/gateway-api/blob/v1.6.0/site/content/en/reference/api-types/referencegrant.md)
- [Envoy Gatewayの互換性](https://github.com/envoyproxy/gateway/blob/v1.9.2/site/content/en/news/releases/matrix.md)
- [NGINX Gateway Fabric 2.8のリリース](https://github.com/nginx/nginx-gateway-fabric/blob/v2.8.0/CHANGELOG.md)
- [Contour 1.33.7のリリース](https://github.com/projectcontour/contour/releases/tag/v1.33.7)
- [コミュニティ版ingress-nginxの終了](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)

- [従来のingress-nginxにおけるリダイレクトと書き換えの動作](https://github.com/kubernetes/ingress-nginx/blob/main/docs/user-guide/nginx-configuration/annotations.md)
- [従来のingress-nginxにおけるリダイレクトコードの構成](https://github.com/kubernetes/ingress-nginx/blob/main/docs/user-guide/nginx-configuration/configmap.md)
