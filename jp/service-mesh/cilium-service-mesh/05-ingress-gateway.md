# Cilium Service Mesh Ingress & Gateway

> **レビュー基準**: Cilium 1.20.1; Gateway API 1.6.1; AWS Load Balancer Controller 3.5.0。
> **最終確認**: September 11, 2026。Kubernetes/EKS の対応表については[インストールの前提条件](./README.md)を参照してください。新しいリリースであることだけでは互換性は確立されません。

## 概要

Cilium は Kubernetes Ingress および Gateway API リソースを使用してデータプレーンを設定します。eBPF は Service 転送を処理し、L7 トラフィックをノードローカルの Envoy にリダイレクトします。Envoy は HTTP ルーティングと TLS 終端を提供します。不透明な TCP/TLS パスには異なる機能があります。以下の例は代替のエントリポイントを示すものであり、完全なアプリケーションデプロイではありません。

## アーキテクチャ

![論理的な設定とトラフィックのコンポーネント: クラウドロードバランサーが Cilium Service フロントエンドに到達し、eBPF が L7 トラフィックを Envoy にリダイレクトします。Envoy の設定は Ingress または Gateway API リソースから導出されます。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.html)

Gateway/Ingress ボックスはパケットを受信するプロセスではなく、設定を表します。L7 トラフィックの実際のパスは、ロードバランサー → Service/NodePort フロントエンド → eBPF/TPROXY → Envoy → バックエンドです。Cilium は外部の `world` → `ingress` 境界でポリシーを適用し、さらに `ingress` からバックエンドにも適用します。ポリシーは両方の経路を許可する必要があります。クラウドロードバランサーの可用性とターゲット登録は別の前提条件です。

## Cilium Ingress Controller

### インストールと有効化

```yaml
kubeProxyReplacement: true
l7Proxy: true
envoy:
  enabled: true
ingressController:
  enabled: true
  loadbalancerMode: shared
  default: false
  service:
    type: LoadBalancer
```

これらは、すでに計画済みの Cilium インストールに対する Helm の**オーバーライド**です。インストールガイドにある、プラットフォーム固有の CNI/IPAM および到達可能な API server 設定とマージしてください。稼働中のクラスターで kube-proxy replacement を変更することは移行であり、通常の機能トグルではありません。変更を適用する前に、固定した 1.20.1 chart をレンダリングしてレビューしてください。

`ingressController.default` は `cilium` **IngressClass をデフォルトとしてマーク**します。フォールバックバックエンドを設定するものではありません。chart は class `cilium` を作成します。`ingressController.ingressClassName` はサポートされる値ではありません。明示的な `spec.ingressClassName` により、クラスターのデフォルトへの依存を回避できます。

shared モードでは、Cilium が管理する Ingress リソースは Helm release namespace（ここでは `kube-system`）内の共有 `cilium-ingress` Service を使用します。Ingress ごとのモードアノテーションで dedicated モードを選択できます。他の controller および Gateway API リソースがこのフロントエンドを自動的に共有することはありません。モードの変更はアドレスを変更し、接続を中断する可能性があります。`LoadBalancer` にはそれをプロビジョニング/調整できる実装が必要です。AWS LBC が Service を所有する場合は、以下の EKS オーバーレイを使用してください。

### Ingress リソースの例

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  namespace: default
  annotations:
    ingress.cilium.io/loadbalancer-mode: shared
    ingress.cilium.io/tls-passthrough: 'false'
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - app.example.com
    secretName: app-tls-secret
  rules:
  - host: app.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

名前付き Service と ready endpoint を `default` に作成し、それぞれで Service port 80 を公開します。`app.example.com` をカバーする証明書を含む `app-tls-secret` を用意し、このフロントエンドへ DNS を向けます。TLS セクションは Envoy で client TLS を終端します。表示したバックエンド port は平文 HTTP です。Cilium のデフォルト `enforceHttps: true` は、TLS が有効な host に対する HTTP をリダイレクトします。これは workload 間 mTLS を確立するものではありません。

### パスベースルーティング

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: path-routing
  namespace: default
spec:
  ingressClassName: cilium
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /users
        pathType: Prefix
        backend:
          service:
            name: users-service
            port:
              number: 80
      - path: /orders
        pathType: Prefix
        backend:
          service:
            name: orders-service
            port:
              number: 80
      - path: /products
        pathType: Prefix
        backend:
          service:
            name: products-service
            port:
              number: 80
      - path: /health
        pathType: Exact
        backend:
          service:
            name: health-service
            port:
              number: 80
```

`Prefix` はパス要素に一致します。`/users` と `/users/42` は一致し、`/users-old` は一致しません。`Exact` は `/health` のみに一致します。Cilium の Ingress の順序は Exact、次に ImplementationSpecific/regex、次に Prefix であり、各グループ内では長い一致が先です。Gateway API には独自の優先順位ルールがあります。YAML のリスト順序は、一般的なルーティング優先度の仕組みではありません。

### TLS 終端

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  namespace: default
spec:
  ingressClassName: cilium
  tls:
  - hosts:
    - secure.example.com
    secretName: app-tls-secret
  rules:
  - host: secure.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: secure-app
            port:
              number: 80
```

プレースホルダーの Base64 を適用するのではなく、**実際の PEM ファイル**から Secret を生成してください。両方の例で同じ Secret を使用する場合は、`app.example.com` と `secure.example.com` の両方を SAN がカバーする証明書を含める必要があります。それ以外の場合は別の Secret を使用します。PKI を通じて公開信頼済みまたは明示的に信頼済みのプライベート証明書をプロビジョニングし、更新を計画してください。

```bash
openssl x509 -in ./tls.crt -noout -dates -ext subjectAltName
kubectl -n default create secret tls app-tls-secret \
  --cert=./tls.crt --key=./tls.key --dry-run=client -o yaml
```

最後のコマンドは Secret をレンダリングするだけです。選択した secret-management workflow を通じてレビューし、適用してください。private-key output を共有ログに書き込むことは避けてください。

### TLS パススルー

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-passthrough
  namespace: default
  annotations:
    ingress.cilium.io/tls-passthrough: 'true'
spec:
  ingressClassName: cilium
  rules:
  - host: backend.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: tls-backend
            port:
              number: 443
```

バックエンドが TLS を終端し、`backend.example.com` の証明書を所有します。Cilium は TLS SNI に一致させます。passthrough Ingress には hostname と path `/` が必要です。暗号化トラフィック内では HTTP path/header rewriting は利用できません。バックエンドには元の client socket address ではなく Envoy/node からの新しい接続が見え、Envoy はこのストリームに HTTP forwarding header を挿入できません。

## Gateway API

### Gateway API の有効化

```yaml
gatewayAPI:
  enabled: true
  gatewayClass:
    create: true
  secretsNamespace:
    create: true
    name: cilium-secrets
    sync: true
```

controller を有効化する前に、**Gateway API 1.6.1 Standard CRD** をインストールしてください。これは Cilium 1.20.1 のインストールリファレンスで使用されるバージョンです。クラスターを共有するすべての controller について CRD upgrade をレビューしてください。このフラグメントで Cilium values file 全体を置き換えないでください。これは上記の kube-proxy replacement/L7 前提条件を補足するものです。

サポートされる key は `gatewayAPI.gatewayClass.create` と `gatewayAPI.secretsNamespace` です。以前の場所にある `secretNamespace` と `gatewayClassName` は無視されます。certificate reference はデフォルトで Gateway の namespace 内の Secret を引き続き指定します。controller の同期済み Secret namespace によりユーザーの reference が移動することはありません。

### GatewayClass

前述の chart 設定では、Cilium は controller name `io.cilium/gateway-controller` を持つ `cilium` GatewayClass を管理します。`kubectl get gatewayclass cilium -o yaml` で確認してください。同じ object の2番目の owner を作成しないでください。GatewayClass は controller と parameter を選択するものであり、共有物理ロードバランサーではありません。

### Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: main-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: http
    protocol: HTTP
    port: 80
    hostname: '*.example.com'
    allowedRoutes:
      namespaces:
        from: Same
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: wildcard-tls
        namespace: default
    allowedRoutes:
      namespaces:
        from: Same
```

HTTPS を使用する前に、listener hostname 用の証明書を含む `wildcard-tls` を `default` に作成してください。`*.example.com` は、ベアの `example.com` や `a.b.example.com` のような深い名前をカバーしません。これらの listener は HTTP/HTTPS を終端します。後述する TCP および TLS-passthrough の例では、protocol と ownership を明確に保つために別の Gateway を使用します。生成される各 Gateway Service には、別々のクラウドロードバランサーが必要になる場合があります。

### HTTPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: api-routes
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    namespace: default
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /v1/users
    backendRefs:
    - name: users-v1
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /v2/users
    backendRefs:
    - name: users-v2
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /api
      headers:
      - name: X-API-Version
        value: '2'
    backendRefs:
    - name: api-v2
      port: 80
  - matches:
    - path:
        type: PathPrefix
        value: /
    backendRefs:
    - name: api-v1
      port: 80
```

すべてのバックエンドは、Route namespace 内に存在し、port 80 と ready endpoint を持つ Service です。`sectionName: https` は、この Route を HTTPS listener に意図的に限定します。正しい `status.parents` entry の `Accepted` と `ResolvedRefs`、および現在の `observedGeneration` を持つ Gateway/listener の `Programmed`/`Accepted` condition を確認してください。設定が Accepted であるだけでは、DNS、証明書の信頼、ターゲットの正常性、またはアプリケーションへの到達可能性は証明されません。

### weight ベースのトラフィック分割

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: canary-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
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

weight は相対的な選択確率であり、10 リクエストごとに必ず stable リクエストが9件含まれるという約束ではありません。接続、retry、sampling により観測される件数は変化し得ます。この例は HTTPS にのみ接続し、API の例とは異なる hostname を使用します。

### リクエスト/レスポンス変換

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: transform-route
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
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
          value: api-v2
        remove:
        - X-Internal-Header
    - type: URLRewrite
      urlRewrite:
        hostname: internal-api.default.svc
        path:
          type: ReplacePrefixMatch
          replacePrefixMatch: /v2/api
    - type: ResponseHeaderModifier
      responseHeaderModifier:
        set:
        - name: X-Doc-Gateway
          value: cilium
    backendRefs:
    - name: api-service
      port: 80
  hostnames:
  - transform.example.com
```

header value は**リテラル文字列**です。`X-Doc-Route` と `X-Doc-Gateway` は診断マーカーであり、生成された request ID や測定された response time ではありません。host rewriting には `URLRewrite.hostname` を使用します。`Host` header mutation として重複させるものではありません。これらの header は caller を認証しません。response `Server` の処理は controller の Envoy server-header transformation の影響も受けます。この動作を変更する場合は、検証済みの `CiliumGatewayClassConfig` を使用してください。

### リダイレクト

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-http
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: http
  hostnames:
  - '*.example.com'
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /
    filters:
    - type: RequestRedirect
      requestRedirect:
        scheme: https
        port: 443
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-path
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - old.example.com
  rules:
  - matches:
    - path:
        type: Exact
        value: /old-path
    filters:
    - type: RequestRedirect
      requestRedirect:
        path:
          type: ReplaceFullPath
          replaceFullPath: /new-path
        statusCode: 308
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: redirect-host
  namespace: default
spec:
  parentRefs:
  - name: main-gateway
    sectionName: https
  hostnames:
  - old.example.com
  rules:
  - matches:
    - path:
        type: PathPrefix
        value: /legacy
    filters:
    - type: RequestRedirect
      requestRedirect:
        hostname: legacy.example.com
        statusCode: 307
```

scheme redirect は**`http` のみに**接続するため、HTTPS リクエストが同じ URL へ無期限にリダイレクトされることはありません。他の2つの Route は `https` と限定された source hostname にのみ接続します。308 permanent redirect と 307 temporary redirect は request method/body を保持します。301/302 の client 動作は異なるため、write に対して普遍的に推奨すべきではありません。最初の HTTP リクエストをリダイレクトしても、client がすでに送信した平文データを取り消すことはできません。RequestRedirect と URLRewrite は別の filter であり、1つの rule に組み合わせることはできません。

### TCPRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: tcp-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: tcp
    protocol: TCP
    port: 9000
    allowedRoutes:
      namespaces:
        from: Same
      kinds:
      - kind: TCPRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: TCPRoute
metadata:
  name: tcp-route
  namespace: default
spec:
  parentRefs:
  - name: tcp-gateway
    sectionName: tcp
  rules:
  - backendRefs:
    - name: tcp-service
      port: 9000
```

Gateway API 1.6.1 は TCPRoute を **v1** で提供します。古い `v1alpha2` バージョンは提供されません。TCPRoute は不透明な TCP stream を転送し、HTTP path を検査しません。TCP は HTTP または TLS を搬送できますが、この Route に HTTP routing や TLS termination の意味論を与えるものではありません。Cilium 1.20.1 の L4 Gateway translation は backend EndpointSlice を使用します。L7 Envoy frontend の endpoint 実装と同一であると想定しないでください。

### TLSRoute

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: tls-gateway
  namespace: default
spec:
  gatewayClassName: cilium
  listeners:
  - name: tls
    protocol: TLS
    port: 443
    hostname: secure.example.com
    tls:
      mode: Passthrough
    allowedRoutes:
      namespaces:
        from: Same
      kinds:
      - kind: TLSRoute
---
apiVersion: gateway.networking.k8s.io/v1
kind: TLSRoute
metadata:
  name: tls-route
  namespace: default
spec:
  parentRefs:
  - name: tls-gateway
    sectionName: tls
  hostnames:
  - secure.example.com
  rules:
  - backendRefs:
    - name: tls-backend
      port: 443
```

この基準では TLSRoute も **v1** で提供されます。上記の HTTPS termination listener ではなく、`mode: Passthrough` を持つ互換性のある `TLS` listener が必要です。バックエンドが `secure.example.com` の証明書を所有します。HTTP content が暗号化されたままである一方、SNI がバックエンドを選択します。生成された Service、listener status、end-to-end TLS trust を検証してください。

## EKS 統合パターン

### NLB + Cilium Ingress

```yaml
ingressController:
  enabled: true
  loadbalancerMode: shared
  enableProxyProtocol: false
  service:
    type: LoadBalancer
    loadBalancerClass: service.k8s.aws/nlb
    allocateLoadBalancerNodePorts: true
    externalTrafficPolicy: Cluster
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-scheme: internal
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
      service.beta.kubernetes.io/aws-load-balancer-attributes: load_balancing.cross_zone.enabled=true
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: TCP
      service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: traffic-port
```

この NLB は設計上**internal**です。唯一の public entry point は CloudFront であり、CloudFront VPC origin を通じて到達します。その security group は、VPC-origin security group（または CloudFront managed prefix list）からのみ許可し、public CIDR は決して許可してはなりません。

このオーバーレイは **AWS LBC-managed NLB → EC2 NodePort → Cilium Ingress Envoy** を示します。AWS LBC 3.5.0、その IAM/subnet/security-group 前提条件、対象となる EC2 node、Cilium がサポートする EKS/CNI 設定、および割り当て済み NodePort が必要です。これは EKS Auto Mode または Fargate Cilium のインストールレシピではありません。`service.k8s.aws/nlb` は AWS LBC を明示的に選択します。レガシーの `aws-load-balancer-type: nlb` annotation はその ownership を表現しません。

この L7 frontend には instance target を使用してください。Cilium 1.20.1 の共有 Ingress Service には、synthetic EndpointSlice（Pod target reference のない `192.192.192.192:9999`）があります。AWS LBC の IP target resolver は Pod target reference を必要とし、これらの endpoint をスキップします。この Service を単に `ip` に切り替えても、node-local Envoy process は検出され**ません**。これは Cilium L7 frontend に固有です。通常の workload Service および現在の L4 Gateway EndpointSlice は異なります。

TCP health check は NodePort での transport reachability を確認するものであり、application `/healthz`、TLS validity、host 固有の HTTP route を確認するものではありません。cross-zone balancing は現在の load-balancer attributes annotation を使用し、cost/traffic review が必要です。既存 Service の controller ownership または LB type を、zero-downtime migration と想定してその場で変更しないでください。

**Client identity と任意の PROXY protocol:** Cilium は、`Cluster` と `Local` の両方の external traffic policy で HTTP Envoy processing のために frontend から見える source を保持します。その source が元の client であるかは、まず上流 NLB と target-group attribute に依存します。instance TCP target は通常 client IP を保持します。PROXY protocol は普遍的に必要ではありません。トポロジーで必要な場合は、次の NLB 設定と追加オーバーレイを調整してください。

```yaml
ingressController:
  enableProxyProtocol: true
  service:
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: '*'
```

これにより NLB の PPv2 と Cilium Ingress の parser が有効になります。これは協調した rollout です。片方だけを有効にするとトラフィックが壊れます。parser は PROXY header を必要とするため、それを含まない直接 HTTP/TLS probe は失敗します。AWS LBC は PPv2 を instance target および `externalTrafficPolicy: Local` と組み合わせないよう警告しています。この例では `Cluster` のままです。HTTP/HTTPS health check にも互換性のある parser が必要です。信頼できる proxy path への direct access を制限してください。PP metadata と forwarded HTTP header は認証済み identity ではありません。`gatewayAPI.enableProxyProtocol` は Gateway API 用の別設定です。Ingress flag はこれを設定しません。

### ALB + Cilium

ALB → Cilium Envoy は構成できますが、実際の環境に応じて次の前提条件を設計し、テストする必要があります。上記で説明した synthetic L7 EndpointSlice に対して、一般に動作する `target-type: ip` の近道はありません。

| 境界 | 必要な判断 |
|---|---|
| Controller と namespace | ALB Ingress は `spec.ingressClassName: alb` を使用します。その backend Service は**同じ namespace**に存在する必要があります。共有 `cilium-ingress` Service は通常 `default` ではなく `kube-system` にあります。 |
| Target | node-based path では、明示的に計画した NodePort Service と ALB `target-type: instance` を使用してください。対象 node、NodePort allocation、security group を検証します。すでに NLB を所有する Service を暗黙に変換しないでください。 |
| TLS | ALB が TLS を終端して HTTP または HTTPS を転送するかを決定します。ACM server-certificate attachment は client mTLS ではありません。ALB が HTTP を転送する場合、listener/redirect behavior を調整しなければ Cilium の HTTPS redirect が loop を引き起こす可能性があります。 |
| Health | ALB health check は独自の Host header を使用し、`app.example.com` を自動的に使用するわけではありません。host 固有の application route は 404 を返す可能性があります。適切な health route/port を定義してテストしてください。 |
| Client attribution | 実際の proxy chain に対して Cilium の trusted XFF hop count を設定し、untrusted header をサニタイズして、ALB を迂回する direct backend access を防止してください。 |

以前のサンプルは誤った namespace と IP target を参照し、これらの判断を省略していました。そのため、これらの実装要件に置き換えられています。このガイドでは、この構成をデプロイまたは load-test していません。

### ハイブリッドアーキテクチャ

![外部 client トラフィックは AWS ALB と NLB に分岐します。ALB は Cilium Gateway に入り L7 routing により web app と API server へ、NLB は Cilium LB に入り L4 load balancing により gRPC service へ向かいます。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.png)

[🔍 インタラクティブな図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.html)

これは論理的な構成図であり、検証済みの deployment manifest ではありません。ALB path には、上記の namespace/target/TLS/health/trust に関する判断が必要です。NLB L4 path は個々の RPC method を理解せずに gRPC stream を搬送できます。ALB の背後に Cilium を追加しても、ALB の料金がなくなったり、ALB feature が native Cilium feature になったりはしません。

## マルチテナント Gateway

### namespace ごとの Gateway

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: cilium-shared
spec:
  controllerName: io.cilium/gateway-controller
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-a-gateway
  namespace: team-a
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.team-a.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-a-tls
    allowedRoutes:
      namespaces:
        from: Same
---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: team-b-gateway
  namespace: team-b
spec:
  gatewayClassName: cilium-shared
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.team-b.example.com'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: team-b-tls
    allowedRoutes:
      namespaces:
        from: Same
```

各 namespace とその有効な TLS Secret を先に作成してください。GatewayClass `cilium-shared` を共有しても、両方の Gateway が1つの Service/load balancer を共有することを意味しません。`from: Same` は Route attachment を各 Gateway namespace に限定します。RBAC は、Gateway、Secret、Route、namespace label を変更できるユーザーを別途制御する必要があります。

### namespace をまたぐルーティング

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: shared-gateway
  namespace: gateway-system
spec:
  gatewayClassName: cilium
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    hostname: '*.example.com'
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
    tls:
      mode: Terminate
      certificateRefs:
      - kind: Secret
        name: shared-tls
---
apiVersion: v1
kind: Namespace
metadata:
  name: app-team
  labels:
    gateway-access: 'true'
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
  namespace: app-team
spec:
  parentRefs:
  - name: shared-gateway
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
    - name: app-service
      port: 80
```

`gateway-system` と、許可する hostname をカバーするその `shared-tls` Secret を作成してください。namespace selector は Route attachment を認可します。ユーザーを認証したり、application request を認可したりするものではありません。administrator が `gateway-access` label を制御する必要があります。

表示している `app-service` backend は `app-team` にローカルであるため、ReferenceGrant は不要です。Route が代わりに `backend-team/shared-api` を参照する場合は、backend namespace がその reference を明示的に許可する必要があります。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: ReferenceGrant
metadata:
  name: allow-app-team
  namespace: backend-team
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: app-team
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api-route
  namespace: app-team
spec:
  parentRefs:
  - name: shared-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - shared-api.example.com
  rules:
  - backendRefs:
    - name: shared-api
      namespace: backend-team
      port: 80
```

この代替を使用する前に、Service port 80 を持つ `backend-team/shared-api` を作成してください。Route → Gateway の cross-namespace attachment には `allowedRoutes` を使用します。Route → backend Service の cross-namespace reference には `ReferenceGrant` を使用します。これらは異なる permission check です。ReferenceGrant v1 は 1.6.1 で提供されます。v1beta1 も引き続き提供されます。

## 高度な Load Balancing 設定

### Service Health Check

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: health-check-config
  namespace: default
spec:
  services:
  - name: my-service
    namespace: default
    ports:
    - 80
    listener: health-check-config-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: health-check-config-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: health-check-config
          route_config:
            name: health-check-config-routes
            virtual_hosts:
            - name: app
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/my-service
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/my-service
    connect_timeout: 5s
    type: EDS
    health_checks:
    - timeout: 5s
      interval: 10s
      unhealthy_threshold: 3
      healthy_threshold: 2
      http_health_check:
        path: /health
        host: health-check.local
        expected_statuses:
        - start: 200
          end: 300
    outlier_detection:
      consecutive_5xx: 5
      interval: 10s
      base_ejection_time: 30s
      max_ejection_percent: 50
      enforcing_consecutive_5xx: 100
```

これは完全なスタンドアロン CEC chain です。Service port 80 → named Listener → HTTP route → EDS Cluster。Cilium は参照する Service の xDS endpoint configuration を提供します。ready backend を持つ `default/my-service` を作成し、他の CEC または生成された Ingress/Gateway configuration にも割り当てないでください。CEC customization は controller-owned resource の patch 機構ではありません。

すべての backend は実際に `Host: health-check.local` と `/health` を受け入れる必要があります。Envoy の status range は上限を含まないため、`[200, 300)` はすべての 2xx response をカバーします。active health check と passive outlier detection は異なる仕組みです。ejection limit と panic behavior は、失敗するすべての endpoint が除外されることを保証しません。backend count と failure model でそれらを検証してください。

### Connection Pool 設定

```yaml
apiVersion: cilium.io/v2
kind: CiliumEnvoyConfig
metadata:
  name: connection-pool
  namespace: default
spec:
  services:
  - name: high-traffic-service
    namespace: default
    ports:
    - 80
    listener: connection-pool-listener
  resources:
  - '@type': type.googleapis.com/envoy.config.listener.v3.Listener
    name: connection-pool-listener
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          '@type': type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: connection-pool
          route_config:
            name: connection-pool-routes
            virtual_hosts:
            - name: app
              domains:
              - '*'
              routes:
              - match:
                  prefix: /
                route:
                  cluster: default/high-traffic-service
                  retry_policy:
                    num_retries: 0
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              '@type': type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  - '@type': type.googleapis.com/envoy.config.cluster.v3.Cluster
    name: default/high-traffic-service
    connect_timeout: 5s
    type: EDS
    typed_extension_protocol_options:
      envoy.extensions.upstreams.http.v3.HttpProtocolOptions:
        '@type': type.googleapis.com/envoy.extensions.upstreams.http.v3.HttpProtocolOptions
        explicit_http_config:
          http2_protocol_options:
            max_concurrent_streams: 1000
            initial_stream_window_size: 65536
            initial_connection_window_size: 1048576
    circuit_breakers:
      thresholds:
      - priority: DEFAULT
        max_connections: 10000
        max_pending_requests: 10000
        max_requests: 10000
        max_retries: 5
```

cleartext HTTP/2 (h2c) を明示的にサポートする backend を持つ、port 80 の `default/high-traffic-service` を作成してください。typed protocol option は上流 HTTP/2 を選択します。これは自動的な protocol negotiation ではありません。`accept_http_10` は HTTP/1.0 のみを受け入れるものであり、HTTP/1.1 connection-pool 設定ではありません。HTTP/1 backend には、代わりに対応する明示的な HTTP/1 設定を選択してください。

circuit-breaker threshold は Envoy cluster/priority ごとのものであり、fleet 全体の quota や capacity recommendation ではありません。`max_retries` は concurrent retry を制限します。request ごとの retry 回数ではありません。ここでの route は `num_retries: 0` を設定します。connection/stream limit を上げるには、resource と backend のテストが必要です。数値は例示です。

## AWS Load Balancer Controller との比較

| 機能 | Cilium Ingress/Gateway | AWS Load Balancer Controller 3.5 |
|---|---|---|
| データプレーン | eBPF Service/L4 forwarding、HTTP/TLS feature には Envoy | AWS ALB または NLB |
| Gateway API | 固定した Cilium feature/conformance table を確認 | HTTPRoute/GRPCRoute は ALB にマップ。TCPRoute/UDPRoute/TLSRoute は NLB にマップ。1つの Gateway 上での L4/L7 混在は未サポート |
| TLS と identity | Ingress TLS termination/passthrough。workload encryption/authentication は別の[security configuration](./03-security.md) | ACM server certificate。ALB client mTLS には mutual-authentication mode/trust store が必要 |
| コスト | Node/proxy resource **に加え、プロビジョニングされたクラウド LB と network charge** | プロビジョニングされた ALB/NLB、capacity/usage および network charge |
| カスタマイズ | サポートされる Gateway API feature と個別管理の CEC。生成 object は controller-owned のまま | LBC API/annotation を通じて公開される AWS listener/rule/target-group feature |
| パフォーマンス | 実際の topology、encryption、workload を測定 | 同じ workload と service limit を測定。普遍的な latency ranking はない |

LBC 3.5 は Gateway API **1.6.0** をテスト済みの基準として文書化しています。Cilium のインストールリファレンスでは **1.6.1** を使用しています。これらの CRD を共有するクラスターには、すべての controller で最新の catalog entry がサポートされると想定するのではなく、互換性テストが必要です。

必要な AWS L7 integration には ALB、必要な transport/target behavior には NLB、in-cluster routing/policy 要件に応じて Cilium feature を選択してください。NLB は現在、新規 flow に対して weight **0–999** の weighted target group をサポートしています。controller が公開するかどうかと、特定の Route の意味論は別の問題です。通常の weight 変更は既存の connection を保持しますが、AWS ドキュメントによれば target group の weight を **0** に設定すると、短時間の後に既存 connection が閉じられます。その操作を connection-preserving drain と説明しないでください。

古い判断図は、サポートされていない cost、latency、mTLS、Gateway API の主張を繰り返していました。table はそれらの主張を置き換えるものであり、どちらの integration option も削除しません。

## モニタリング

### Gateway メトリクス

```bash
kubectl get gatewayclass cilium -o yaml
kubectl get gateway,httproute,tcproute,tlsroute -A
kubectl -n default describe gateway main-gateway
kubectl -n default get httproute api-routes -o yaml
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics -f downstream_rq
```

### Prometheus メトリクス

まず、[observability guide](./04-observability.md)を使用して Cilium Envoy Prometheus endpoint を有効化し、scrape してください。複数のクラスターが1つの Prometheus に送信する場合は、安定した `cluster` target label を設定してください。native Cilium Envoy image は `envoy_http_conn_manager_prefix` を公開し、`listener-insecure`、`listener-secure`、port 固有の variant などの生成値を持ちます。固定の `cilium-gateway` 値ではありません。同じ Envoy 上の Gateway 間で prefix は再利用され得ます。これらの例は**scrape された proxy/HCM**を説明するものであり、Gateway ごとの accounting を保証するものではありません。dashboard を作成する前に実際の label を確認してください。

以下の3つの query は、開始リクエスト率、完了 response counter のうち 5xx に分類される割合、および**秒**単位の p99 duration を示します。存在しない 5xx numerator は、一致する観測済み denominator からのみ補完されます。traffic/telemetry がないことを正常なゼロとして扱いません。positive-denominator filter は idle series を除外します。Envoy の `downstream_rq_time` histogram は**milliseconds**単位であるため、`/ 1000` です。quantile を計算する前に `le` を保持して histogram bucket を集計してください。low sample count、scrape gap、missing histogram には引き続き別の monitoring が必要です。

```promql
sum by (cluster, instance, envoy_http_conn_manager_prefix) (
  rate(envoy_http_downstream_rq_total[5m])
)
```

```promql
100 *
(
  sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx{envoy_response_code_class="5"}[5m])
  )
  or
  0 * sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx[5m])
  )
)
/
(
  sum by (cluster, instance, envoy_http_conn_manager_prefix) (
    rate(envoy_http_downstream_rq_xx[5m])
  ) > 0
)
```

```promql
histogram_quantile(
  0.99,
  sum by (cluster, instance, envoy_http_conn_manager_prefix, le) (
    rate(envoy_http_downstream_rq_time_bucket[5m])
  )
) / 1000
```

## 次のステップ

- [ベストプラクティス](./06-best-practices.md): 運用上の前提条件と制限

## 参考資料

- [Cilium 1.20.1 Ingress](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/ingress.rst)
- [Cilium のトラフィック、source IP、ポリシー](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/ingress-reference.rst)
- [Cilium Gateway API のインストール](https://github.com/cilium/cilium/blob/v1.20.1/Documentation/network/servicemesh/gateway-api/gateway-api.rst)
- [Cilium 1.20.1 Helm values](https://github.com/cilium/cilium/blob/v1.20.1/install/kubernetes/cilium/values.yaml)
- [Gateway API 1.6.1 CRD](https://github.com/kubernetes-sigs/gateway-api/tree/v1.6.1/config/crd/standard)
- [AWS LBC 3.5 NLB 設定](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/nlb.md)
- [AWS LBC 3.5 annotation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/service/annotations.md)
- [AWS LBC 3.5 Gateway API](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.5.0/docs/guide/gateway/gateway.md)
- [NLB target group attribute](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html)
- [NLB listener weight](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [Envoy 1.37 request statistics](https://www.envoyproxy.io/docs/envoy/v1.37.5/configuration/http/http_conn_man/stats)
