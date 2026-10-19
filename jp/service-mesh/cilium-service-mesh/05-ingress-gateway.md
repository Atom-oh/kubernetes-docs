# Cilium Service Mesh の Ingress と Gateway

> **レビュー基準**：Cilium 1.20.3、Gateway API 1.6.3、AWS Load Balancer Controller 3.6.0。
> **最終レビュー日**：2026年10月16日。Kubernetes/EKS の対応マトリクスは[インストールの前提条件](./README.md)を参照してください。新しいリリースであることだけでは互換性は確認できません。

## 概要

Cilium は Kubernetes Ingress と Gateway API のリソースを使ってデータプレーンを構成します。eBPF が Service の転送を処理し、L7 トラフィックをノードローカルの Envoy にリダイレクトします。Envoy は HTTP ルーティングと TLS 終端を行います。不透明な TCP/TLS トラフィック経路では利用できる機能が異なります。以下の例は異なる入口の選択肢であり、アプリケーション全体のデプロイ手順ではありません。

## アーキテクチャ

![論理構成とトラフィック要素。クラウドロードバランサーが Cilium Service のフロントエンドに到達し、eBPF が L7 トラフィックを Envoy にリダイレクトします。Envoy の設定は Ingress または Gateway API リソースから導出されます。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-0.html)

図の Gateway/Ingress ボックスは設定を表し、パケットを受信するプロセスではありません。L7 トラフィックの実際の経路は、ロードバランサー → Service/NodePort フロントエンド → eBPF/TPROXY → Envoy → backend です。Cilium は外部の `world` から `ingress` への境界と、`ingress` から backend への境界の両方でポリシーを適用します。ポリシーは両方の通信を許可する必要があります。クラウドロードバランサーの可用性とターゲット登録は別途満たす必要があります。

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

以下は、計画済みの Cilium インストールに適用する Helm の**上書き設定**です。インストールガイドにある、プラットフォーム固有の CNI/IPAM と到達可能な API server の設定にマージしてください。稼働中クラスターで kube-proxy replacement を変更することは移行作業であり、通常の機能切り替えではありません。適用前に、バージョンを固定した 1.20.3 chart をレンダリングしてレビューしてください。

`ingressController.default` は `cilium` **IngressClass を既定に指定**します。fallback backend を構成する設定ではありません。chart は `cilium` class を作成します。`ingressController.ingressClassName` はサポートされている値ではありません。`spec.ingressClassName` を明示すると、クラスターの既定値への依存を避けられます。

共有モードでは、Cilium が管理する Ingress リソースは Helm release の namespace（ここでは `kube-system`）にある共有 `cilium-ingress` Service を使います。Ingress ごとの mode annotation で専用モードを選べます。他の controller や Gateway API リソースがこのフロントエンドを自動的に共有するわけではありません。モードを変更するとアドレスが変わり、接続が中断する可能性があります。`LoadBalancer` には、その Service をプロビジョニング/調整できる実装が必要です。AWS LBC が Service を管理する場合は、以下の EKS overlay を使ってください。

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

`default` namespace に名前付き Service を作成し、それぞれ Service port 80 と Ready な endpoint を用意してください。`app.example.com` をカバーする証明書を `app-tls-secret` に設定し、DNS をこのフロントエンドに向けます。TLS セクションは Envoy でクライアント TLS を終端します。図の backend port は暗号化されていない HTTP です。Cilium の既定 `enforceHttps: true` は、TLS 対応 host への HTTP を redirect します。これは workload 間 mTLS を構成するものではありません。

### パスベースのルーティング

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

`Prefix` はパス要素に一致します。`/users` と `/users/42` には一致しますが、`/users-old` には一致しません。`Exact` は `/health` だけに一致します。Cilium Ingress の優先順位は Exact、ImplementationSpecific/regex、Prefix の順で、各グループ内では長い一致が先です。Gateway API には独自の優先順位規則があり、YAML のリスト順が一般的なルーティング優先度になるわけではありません。

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

placeholder の Base64 を適用せず、**実際の PEM ファイル**から Secret を生成してください。両方の例で同じ Secret を使う場合、その証明書の SAN は `app.example.com` と `secure.example.com` の両方をカバーする必要があります。そうでなければ Secret を分けてください。PKI を通じて公的に信頼された、または明示的に信頼されたプライベート証明書を用意し、更新計画を立ててください。

```bash
openssl x509 -in ./tls.crt -noout -dates -ext subjectAltName
kubectl -n default create secret tls app-tls-secret \
  --cert=./tls.crt --key=./tls.key --dry-run=client -o yaml
```

最後のコマンドは Secret をレンダリングするだけです。選択した Secret 管理手順で内容をレビューして適用し、秘密鍵の出力を共有ログに書き込まないでください。

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

TLS を終端するのは backend であり、backend は `backend.example.com` 用の証明書を所有します。Cilium は TLS SNI に一致させます。passthrough Ingress には host 名とパス `/` が必要です。暗号化されたトラフィック内では HTTP path/header の書き換えはできません。backend が受け取るのは Envoy/ノードからの新しい接続であり、元のクライアント socket address ではありません。また Envoy はこの stream に HTTP forwarding header を挿入できません。

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

controller を有効化する前に、**Gateway API 1.6.3 Standard CRD** をインストールしてください。これは Cilium 1.20.3 のインストール資料が使用するバージョンです。同じクラスターを共有するすべての controller について、CRD の更新を確認してください。Cilium values ファイル全体をこの断片で置き換えないでください。これは上記の kube-proxy replacement/L7 前提条件に追加する設定です。

サポートされる key は `gatewayAPI.gatewayClass.create` と `gatewayAPI.secretsNamespace` です。以前の場所にある `secretNamespace` と `gatewayClassName` は無視されます。既定では、証明書参照先は引き続き Gateway と同じ namespace の Secret です。controller が Secret を同期する namespace を指定しても、ユーザーが指定した参照先は移動しません。

### GatewayClass

前述の chart 設定により、Cilium は controller 名 `io.cilium/gateway-controller` を持つ `cilium` GatewayClass を管理します。`kubectl get gatewayclass cilium -o yaml` で確認してください。同じ object の所有者を二重に作成しないでください。GatewayClass は controller と parameters を選び、共有の物理ロードバランサーを選ぶものではありません。

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

HTTPS を使う前に、listener の host 名をカバーする証明書を持つ `default` namespace の `wildcard-tls` を作成してください。`*.example.com` は `example.com` 自体や `a.b.example.com` のような階層の深い名前をカバーしません。ここで示す listener は HTTP/HTTPS を終端します。後続の TCP と TLS passthrough の例では、protocol と所有権を明確に分けるため別の Gateway を使います。生成される Gateway Service ごとに別のクラウドロードバランサーが必要になることがあります。

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

すべての backend は Route と同じ namespace にある既存 Service で、port 80 と Ready な endpoint を持ちます。`sectionName: https` により、この Route が HTTPS listener のみに接続されます。正しい `status.parents` entry の `Accepted` と `ResolvedRefs`、および Gateway/listener の `Programmed`/`Accepted` condition と最新の `observedGeneration` を確認してください。設定が Accepted でも、DNS、証明書の信頼性、target の健全性、アプリケーションへの到達性が確認されたことにはなりません。

### 重みによるトラフィック分割

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

重みは相対的な選択確率であり、10件ごとに安定トラフィックが必ず9件になるという約束ではありません。接続、retry、sampling によって観測数は変わります。この例は HTTPS のみを対象とし、API の例とは異なる host 名を使います。

### リクエスト/レスポンスの変換

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

header の値は**リテラル文字列**です。`X-Doc-Route` と `X-Doc-Gateway` は診断用 marker であり、自動生成される request ID や測定された応答時間ではありません。host の書き換えには `URLRewrite.hostname` を使います。`Host` header の変更を重ねて設定するものではありません。これらの header は呼び出し元を認証しません。レスポンスの `Server` header の扱いも controller による Envoy server-header 変換の影響を受けます。その動作を変更する場合は、検証済みの `CiliumGatewayClassConfig` を使ってください。

### Redirect

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

scheme redirect の接続先は **`http` のみ**です。そのため HTTPS request が同じ URL に戻り続けることはありません。他の2つの Route は `https` と限定された送信元 host 名だけに接続されます。308 permanent redirect と307 temporary redirect は request method/body を保持します。301/302 は client の挙動が異なるため、write 操作に一律推奨すべきではありません。最初の HTTP request を redirect しても、client がすでに送信した平文データを取り消すことはできません。RequestRedirect と URLRewrite は異なる filter であり、1つの rule で組み合わせられません。

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

Gateway API 1.6.3 では TCPRoute は **v1** で提供され、古い `v1alpha2` は提供されません。TCPRoute は不透明な TCP stream を転送し、HTTP path を検査しません。TCP 上で HTTP や TLS を運べますが、この Route に HTTP routing や TLS 終端の意味が加わるわけではありません。Cilium 1.20.3 の L4 Gateway 変換は backend の EndpointSlice を使います。L7 Envoy frontend の endpoint 実装も同じだと仮定しないでください。

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

この基準環境では TLSRoute も **v1** で提供されます。上記の HTTPS 終端 listener ではなく、`mode: Passthrough` の互換性がある `TLS` listener が必要です。backend が `secure.example.com` の証明書を所有し、HTTP の内容を暗号化したまま SNI で backend を選びます。生成された Service、listener の status、エンドツーエンドの TLS 信頼性を確認してください。

## EKS との統合パターン

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

この NLB は設計上**内部向け**です。唯一の公開入口は CloudFront であり、CloudFront VPC origin を通じて NLB に到達します。security group が許可するのは VPC origin の security group（または CloudFront managed prefix list）だけにしてください。公開 CIDR を許可してはいけません。

この overlay が示すのは **AWS LBC 管理 NLB → EC2 NodePort → Cilium Ingress Envoy** です。AWS LBC 3.6.0 とその IAM/subnet/security group 前提条件、対象となる EC2 node、Cilium がサポートする EKS/CNI 構成、割り当て済み NodePort が必要です。EKS Auto Mode や Fargate 上の Cilium をインストールする手順ではありません。`service.k8s.aws/nlb` は AWS LBC を明示的に選びます。旧式の `aws-load-balancer-type: nlb` annotation では、その所有者を表現できません。

この L7 frontend では instance target を使ってください。Cilium 1.20.3 の共有 Ingress Service は、合成 EndpointSlice（`192.192.192.192:9999`、Pod target reference なし）を持ちます。AWS LBC の IP target resolver は Pod target reference を必要とし、この endpoint をスキップします。この Service を `ip` に切り替えるだけでは、ノードローカル Envoy process は検出**されません**。これは Cilium L7 frontend 固有の挙動です。通常の workload Service と現在の L4 Gateway EndpointSlice では異なります。

TCP health check が確認するのは NodePort での transport 到達性であり、アプリケーションの `/healthz`、TLS の有効性、host 固有の HTTP route ではありません。クロスゾーン負荷分散には現在の load-balancer attributes annotation を使い、コスト/トラフィックを確認してください。既存 Service の controller 所有者や LB type を、停止のない移行だと仮定してその場で変更しないでください。

**クライアント ID と任意の PROXY protocol**：Cilium は `Cluster` と `Local` の両方の external traffic policy で、HTTP Envoy 処理のために frontend で見える送信元を保持します。その送信元が元のクライアントかどうかは、まず上流 NLB と target group の属性で決まります。instance TCP target は通常 client IP を保持するため、PROXY protocol が常に必要なわけではありません。トポロジー上必要なら、NLB の設定と以下の overlay を連携してください。

```yaml
ingressController:
  enableProxyProtocol: true
  service:
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: '*'
```

この設定は NLB 側で PPv2 を有効にし、Cilium Ingress 側でその parser を有効にします。両側を合わせて rollout する必要があります。片側だけ有効にするとトラフィックが壊れます。parser は PROXY header を必須とするため、header を付けない直接の HTTP/TLS probe は失敗します。AWS LBC は PPv2 を instance target および `externalTrafficPolicy: Local` と併用しないよう警告しています。この例では `Cluster` を維持します。HTTP/HTTPS health check にも互換性のある parser が必要です。直接アクセスは信頼できる proxy 経路だけに制限してください。PP metadata と forwarding HTTP header は認証済み ID ではありません。`gatewayAPI.enableProxyProtocol` は Gateway API 用の別設定です。Ingress の flag では構成されません。

### ALB + Cilium

ALB → Cilium Envoy は組み合わせられますが、次の前提条件を実環境に合わせて設計し、テストする必要があります。前述の合成 L7 EndpointSlice には、一般に機能する `target-type: ip` の簡便な回避策はありません。

| 境界 | 必要な判断 |
|---|---|
| Controller と namespace | ALB Ingress は `spec.ingressClassName: alb` を使います。backend Service は**同じ namespace**に必要です。共有 `cilium-ingress` Service は通常 `default` ではなく `kube-system` にあります。 |
| Target | node ベースの経路では、計画済み NodePort Service と ALB `target-type: instance` を使います。対象 node、NodePort 割り当て、security group を確認してください。すでに NLB を所有する Service を黙って切り替えないでください。 |
| TLS | ALB で TLS を終端して HTTP と HTTPS のどちらを転送するか決めてください。ACM の server certificate のアタッチは client mTLS ではありません。ALB が HTTP を転送する場合、listener/redirect 動作を調整しないと Cilium の HTTPS redirect で loop が起きる可能性があります。 |
| Health | ALB health check は独自の Host header を使い、自動的に `app.example.com` を使うわけではありません。host 固有のアプリケーション route は 404 を返すことがあります。適切な health route/port を定義してテストしてください。 |
| Client attribution | 実際の proxy chain に合わせて Cilium の信頼する XFF hop 数を設定し、信頼できない header を除去し、ALB を迂回する backend への直接アクセスを防いでください。 |

以前の例には誤った namespace と IP target が記され、これらの判断も欠落していました。ここでは実装に必要な条件へ置き換えています。このガイドで本構成をデプロイしたり、負荷試験したりはしていません。

### ハイブリッドアーキテクチャ

![外部クライアントのトラフィックは AWS ALB と NLB に分岐します。ALB は Cilium Gateway に渡して L7 で Web アプリケーションと API server にルーティングし、NLB は Cilium LB に渡して L4 で gRPC Service に負荷分散します。](../../.gitbook/assets/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.png)

[🔍 インタラクティブな図を見る](https://www.atomai.click/kubernetes-docs/archmaps/en-service-mesh-cilium-service-mesh-05-ingress-gateway-1.html)

これは論理的な組み合わせを示す図であり、検証済みの deployment manifest ではありません。ALB 経路には上記の namespace/target/TLS/health/trust に関する判断が必要です。NLB の L4 経路は、個々の RPC method を認識せずに gRPC stream を転送できます。ALB の背後に Cilium を追加しても、ALB の料金はなくならず、ALB の機能が Cilium のネイティブ機能になるわけでもありません。

## マルチテナント Gateway

### Namespace ごとの Gateway

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

各 namespace と、それぞれで有効な TLS Secret を先に作成してください。GatewayClass `cilium-shared` を共有しても、両 Gateway が1つの Service/load balancer を共有することには**なりません**。`from: Same` は各 Gateway namespace 内に Route の接続を限定します。Gateway、Secret、Route、namespace label を誰が変更できるかは RBAC で別途制御する必要があります。

### Namespace をまたぐルーティング

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

`gateway-system` と、許可する host 名をカバーする `shared-tls` Secret を作成してください。namespace selector が許可するのは Route の接続であり、ユーザー認証やアプリケーション request の認可ではありません。管理者が `gateway-access` label を制御してください。

図の `app-service` backend は `app-team` 内にあるため ReferenceGrant は不要です。Route が代わりに `backend-team/shared-api` を参照する場合、backend namespace はその参照を明示的に許可する必要があります。

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

この代替構成を使う前に、Service port 80 で `backend-team/shared-api` を作成してください。Route → Gateway の namespace 間接続には `allowedRoutes` を使います。Route → backend Service の namespace 間参照には `ReferenceGrant` を使います。これは別々の権限チェックです。ReferenceGrant v1 は 1.6.3 で提供され、v1beta1 も引き続き提供されています。

## 高度な負荷分散設定

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

これは単独で完結する CEC chain です。Service port 80 → 名前付き Listener → HTTP route → EDS Cluster で構成されます。参照された Service の xDS endpoint 設定は Cilium が提供します。Ready な backend を持つ `default/my-service` を作成し、別の CEC や生成された Ingress/Gateway 設定にも同じ Service を割り当てないでください。CEC customization は controller 所有リソースの patch 機構ではありません。

すべての backend が実際に `Host: health-check.local` と `/health` を受け付ける必要があります。Envoy の status range は上限を含まないため、`[200, 300)` はすべての 2xx response をカバーします。active health check と passive outlier detection は別の機能です。ejection 上限や panic 動作によって、障害中のすべての endpoint が除外される保証はありません。backend の数と障害モデルに合わせて検証してください。

### Connection Pool の設定 {#connection-pool-configuration}

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

port 80 で `default/high-traffic-service` を作成し、cleartext HTTP/2（h2c）を明示的にサポートする backend を使ってください。型付き protocol option が upstream HTTP/2 を選びます。自動的な protocol negotiation ではありません。`accept_http_10` が受け入れるのは HTTP/1.0 だけであり、HTTP/1.1 connection pool の設定ではありません。HTTP/1 backend では、それに対応する明示的な HTTP/1 設定を選んでください。

Circuit breaker のしきい値は Envoy cluster/priority ごとに適用されます。fleet 全体の quota や容量の推奨値ではありません。`max_retries` は同時 retry 数の上限であり、request ごとの retry 回数ではありません。ここでの route は `num_retries: 0` を指定します。connection/stream 上限を上げる場合は、resource と backend をテストしてください。数値は例示です。

## AWS Load Balancer Controller との比較

| 機能 | Cilium Ingress/Gateway | AWS Load Balancer Controller 3.6 |
|---|---|---|
| Data plane | eBPF による Service/L4 転送、HTTP/TLS 機能には Envoy | AWS ALB または NLB |
| Gateway API | 固定した Cilium の feature/conformance 表を確認 | HTTPRoute/GRPCRoute は ALB、TCPRoute/UDPRoute/TLSRoute は NLB に対応。1つの Gateway で L4/L7 を混在させることは未対応 |
| TLS と ID | Ingress の TLS 終端/passthrough。workload の暗号化/認証は別途[セキュリティ設定](./03-security.md)が必要 | ACM server certificate。ALB client mTLS には mutual-authentication mode/trust store が必要 |
| コスト | node/proxy resource に加えて、プロビジョニングしたクラウド LB とネットワークの料金もかかります | プロビジョニングされた ALB/NLB、容量/使用量、ネットワークの料金 |
| カスタマイズ | サポート対象の Gateway API 機能と別管理の CEC。生成 object は引き続き controller が所有 | LBC API/annotation で公開される AWS listener/rule/target group 機能 |
| 性能 | 実際の topology、暗号化、workload で測定 | 同じ workload と Service 上限で測定。普遍的な latency 順位はありません |

LBC 3.6 がテスト済み基準として記載する Gateway API は **1.6.0** です。Cilium のインストール資料は **1.6.3** を使います。これらの CRD を共有するクラスターでは、catalog の最新項目がすべての controller でサポートされると仮定せず、互換性をテストしてください。

必要な AWS L7 連携には ALB、求める transport/target 動作には NLB、クラスター内 routing/policy 要件には Cilium の機能を選んでください。現在の NLB は新しい flow に対して **0～999** の重みを持つ target group をサポートします。controller がその機能を公開するかどうかと、特定 Route の意味は別の問題です。通常の重み変更は既存接続を維持しますが、target group の重みを **0** にすると、AWS 資料のとおり短時間の後に既存接続が切断されます。この操作を接続を維持する drain と説明しないでください。

以前の判断図は、根拠のないコスト、latency、mTLS、Gateway API に関する主張を繰り返していました。表はそれらの断定を置き換えるものであり、どちらかの統合方式を除外するものではありません。

## モニタリング

### Gateway のメトリクス

```bash
kubectl get gatewayclass cilium -o yaml
kubectl get gateway,httproute,tcproute,tlsroute -A
kubectl -n default describe gateway main-gateway
kubectl -n default get httproute api-routes -o yaml
kubectl -n kube-system exec ds/cilium -- cilium-dbg status --verbose
kubectl -n kube-system exec ds/cilium -- cilium-dbg envoy admin metrics -f downstream_rq
```

### Prometheus メトリクス

まず[可観測性ガイド](./04-observability.md)を使い、Cilium Envoy Prometheus endpoint を有効化して scrape してください。複数クラスターから1つの Prometheus に送る場合は、安定した `cluster` target label を設定します。ネイティブ Cilium Envoy image が公開するのは `envoy_http_conn_manager_prefix` で、生成値には `listener-insecure`、`listener-secure`、port ごとの値などがあります。固定値 `cilium-gateway` ではありません。同じ Envoy 上の複数 Gateway で prefix が再利用されることがあります。以下の例が示すのは**scrape 対象の proxy/HCM**であり、Gateway ごとの集計が保証されるわけではありません。dashboard を作る前に実際の label を確認してください。

以下の3つの query は、開始した request の rate、完了済み response counter のうち 5xx と分類された割合、p99 duration を**秒**単位で示します。欠落した 5xx numerator を埋めるのは、対応する観測済み denominator がある場合だけです。トラフィック/telemetry がない場合に正常なゼロとして扱うことはありません。正の denominator に絞る filter は idle series を除外します。Envoy の `downstream_rq_time` histogram の単位は**ミリ秒**なので `/ 1000` します。quantile を計算する前に `le` を保持したまま histogram bucket を集計してください。sample 数の少なさ、scrape の欠落、histogram の欠落は別途監視する必要があります。

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

- [ベストプラクティス](./06-best-practices.md)：運用上の前提条件と制約

## 参考資料

- [Cilium 1.20.3 Ingress](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/ingress.rst)
- [Cilium の通信、送信元 IP、policy](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/ingress-reference.rst)
- [Cilium Gateway API のインストール](https://github.com/cilium/cilium/blob/v1.20.3/Documentation/network/servicemesh/gateway-api/gateway-api.rst)
- [Cilium 1.20.3 Helm values](https://github.com/cilium/cilium/blob/v1.20.3/install/kubernetes/cilium/values.yaml)
- [Gateway API 1.6.3 CRD](https://github.com/kubernetes-sigs/gateway-api/tree/v1.6.3/config/crd/standard)
- [AWS LBC 3.6 NLB 設定](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/service/nlb.md)
- [AWS LBC 3.6 annotation](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/service/annotations.md)
- [AWS LBC 3.6 Gateway API](https://github.com/kubernetes-sigs/aws-load-balancer-controller/blob/v3.6.0/docs/guide/gateway/gateway.md)
- [NLB target group attribute](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/edit-target-group-attributes.html)
- [NLB listener の重み](https://docs.aws.amazon.com/elasticloadbalancing/latest/network/load-balancer-listeners.html)
- [Envoy 1.38 request 統計](https://www.envoyproxy.io/docs/envoy/v1.38.6/configuration/http/http_conn_man/stats)
