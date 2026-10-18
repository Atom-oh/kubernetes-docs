# Gateway API クイズ

v1.6 API の基準と、ガイドに記載された実装固有の前提に基づいています。各コード例はそれぞれ独立したシナリオです。

## 1. Gateway API の設計目標ではないものはどれですか？

- A. インフラストラクチャ、operator、アプリケーションの各リソース所有者をより明確に分ける
- B. 複数のトラフィックプロトコルに対応した API 型を提供する
- C. サポートレベルが定義された標準フィールドを提供する
- D. すべてのネットワーク機能を 1 つのオブジェクトに統合する

<details>
<summary>解答を表示</summary>

D. GatewayClass、Gateway、Route リソースは責務を分離します。controller は、該当する API バージョン、profile、機能を実装する必要があり、RBAC／admission が所有権を強制します。標準フィールドによって移植性は高まりますが、実装固有の拡張がなくなるわけではありません。

</details>

## 2. ロール別モデルでは、通常、誰が GatewayClass を管理しますか？

- A. 各アプリケーション開発者が個別に管理する
- B. backend Service の所有者だけが管理する
- C. インフラストラクチャ提供者またはプラットフォーム／ネットワークチームが管理する
- D. 認証されていないアプリケーションクライアントが管理する

<details>
<summary>解答を表示</summary>

C. GatewayClass は、インストール済みの controller と、サポートされる実装固有のパラメーターを選択します。プラットフォーム運用者は Gateway と Route の接続ポリシーを管理し、開発者は Route を管理します。参照先 namespace の所有者は ReferenceGrant を管理します。これらは運用上の役割であり、Kubernetes 権限が自動的に付与されるわけではありません。

</details>

## 3. TLS termination と passthrough の違いは何ですか？

- A. Terminate は暗号化済みバイト列をそのまま通し、Passthrough では backend に TLS を終了させる
- B. Terminate は downstream TLS を Gateway で終了し、Passthrough は backend で終了させる
- C. どちらも同じ HTTPS listener を使い、モードだけ切り替える
- D. Termination では backend が必ず平文を受信する

<details>
<summary>解答を表示</summary>

B. HTTPS termination と TLS passthrough では listener の設定が異なります。termination 後に backend まで暗号化するかどうかは別の判断であり、サポート対象の BackendTLSPolicy または実装設定を使います。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-tls
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
  - name: tls-passthrough
    protocol: TLS
    port: 8443
    tls:
      mode: Passthrough
```

参照先の TLS Secret と適切な Route／backend が存在している必要があります。HTTPS listener の mode を変えるだけでは passthrough を有効にできません。

</details>

## 4. HTTPRoute で重み付き backend の振り分けを表すには、どの方法を使いますか？

- A. `trafficSplit` フィールド
- B. 複数の `backendRefs` に設定する `weight`
- C. 必須の canary annotation
- D. 別 API の TrafficSplit CRD

<details>
<summary>解答を表示</summary>

B. ガイドの Gateway／Namespace 設定と、既存の backend Service を使います。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-split
  namespace: production
spec:
  parentRefs:
  - name: production-gateway
    namespace: gateway-system
    sectionName: https
  hostnames:
  - api.example.com
  rules:
  - backendRefs:
    - name: app-stable
      port: 80
      weight: 90
    - name: app-canary
      port: 80
      weight: 10
```

weight は相対的な振り分け比率を表し、合計を 100 にする必要はありません。少ないリクエスト数では、実際の割合が指定値と一致しないことがあります。この設定は同じ Gateway の背後にある backend を選びます。旧 Ingress frontend と新 Gateway frontend の間でクライアントを切り替えるものではありません。

</details>

## 5. namespace をまたぐ backend 参照の ReferenceGrant は、どこに作成しますか？

- A. 常に Route の namespace に作成する
- B. 参照先 backend の namespace に、その所有者が作成する
- C. kube-system にだけ作成できる
- D. クライアントのワークステーションに作成する

<details>
<summary>解答を表示</summary>

B. 参照を受け入れる側が許可します。例:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-shared-api
  namespace: backend-services
spec:
  from:
  - group: gateway.networking.k8s.io
    kind: HTTPRoute
    namespace: production
  to:
  - group: ''
    kind: Service
    name: shared-api
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: shared-api
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
        type: PathPrefix
        value: /shared
    backendRefs:
    - name: shared-api
      namespace: backend-services
      port: 80
```

shared-api Service は backend-services に存在する必要があります。`to.name` により許可対象はその Service に限定されます。Route から Gateway への接続には `parentRefs` と `allowedRoutes` を使い、その接続自体に ReferenceGrant は不要です。ReferenceGrant はアプリケーションユーザーを認証しません。

</details>

## 6. Gateway API v1.6 Standard bundle に含まれないリソースはどれですか？

- A. GatewayClass
- B. GRPCRoute
- C. TCPRoute
- D. Istio VirtualService

<details>
<summary>解答を表示</summary>

D. VirtualService は Istio API です。v1.6 Standard bundle には、HTTPRoute、GRPCRoute、TCPRoute、TLSRoute、UDPRoute などが含まれます。TCPRoute が Experimental という古い解答は、現在は正しくありません。channel と API version は別の概念です。ReferenceGrant v1beta1 は v1 とともに Standard で引き続き提供されますが、Experimental bundle では v1 リソースに実験的フィールドが含まれることがあります。

</details>

## 7. クライアントへの redirect を返さず、upstream request を書き換える filter はどれですか？

- A. RequestHeaderModifier
- B. ResponseHeaderModifier
- C. URLRewrite
- D. RequestMirror

<details>
<summary>解答を表示</summary>

C. URLRewrite は upstream の path／Host を変更します。宛先 backend は引き続き `backendRefs` で選択します。RequestRedirect はクライアントに 3xx response を返します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: quiz-rewrite
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
```

この場合、`/old-api/users` は `/new-api/users` になります。ReplaceFullPath は path 全体を置き換えます。legacy rewrite を移行するときは、両者の動作の違いに注意してください。

</details>

## 8. Gateway API リソースを reconcile しないコンポーネントはどれですか？

- A. Istio の Gateway controller
- B. Cilium の Gateway controller
- C. kube-proxy
- D. Envoy Gateway

<details>
<summary>解答を表示</summary>

C. kube-proxy は Service の転送を処理し、backend へのネットワーク経路に関与する場合もありますが、GatewayClass／Gateway／Route リソースを reconcile しません。Gateway API の CRD をインストールしただけでは、ここに挙げた controller はインストールされません。

</details>

## 9. legacy Ingress 設定の HTTP path rewrite を Gateway API で表す construct はどれですか？

- A. Gateway オブジェクト名
- B. HTTPRoute の URLRewrite filter
- C. 任意の namespace からの ReferenceGrant
- D. namespace label だけ

<details>
<summary>解答を表示</summary>

B. `ReplaceFullPath` と `ReplacePrefixMatch` のどちらを選ぶかは、移行前に元の rewrite の動作を確認してください。ガイドにある固定値 `rewrite-target: /` では、suffix を残すのではなく path 全体を置き換える必要があります。ほかの Ingress annotation は Gateway 設定または controller policy CRD に対応する場合もありますが、サポート対象の代替がないものもあります。HTTP から HTTPS への redirect は HTTP listener に bind する必要があります。

</details>

## 10. Gateway に Route を接続できる namespace を制限するには、どう設定しますか？

- A. `from: All` は接続元を 1 つの namespace に制限する
- B. `from: Same` は Gateway 自身の namespace を許可する
- C. `from: Selector` は Namespace label で選択する
- D. B と C はどちらも有効で、許可範囲が異なる

<details>
<summary>解答を表示</summary>

D. `from` には、次のいずれか 1 つを選びます。Selector の場合:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: quiz-namespace-selector
  namespace: gateway-system
spec:
  gatewayClassName: istio
  listeners:
  - name: https
    protocol: HTTPS
    port: 443
    tls:
      mode: Terminate
      certificateRefs:
      - name: tls-cert
    allowedRoutes:
      namespaces:
        from: Selector
        selector:
          matchLabels:
            gateway-access: 'true'
```

label を付ける対象は Route や Pod ではなく Namespace です。Namespace label を変更できる主体を制御してください。`allowedRoutes` が制限するのは Route の接続先です。namespace をまたぐ backend 参照を許可するものでも、アプリケーション要求を認可するものでもありません。

</details>

## 11. GRPCRoute で特定の service の特定の method を選択する match はどれですか？

- A. `path.service` と `path.method`
- B. `method.service` と `method.method`
- C. `grpc.service` と `grpc.method`
- D. `rpc.service` と `rpc.method`

<details>
<summary>解答を表示</summary>

B. ガイドの gRPC listener では、次のように指定します。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
metadata:
  name: quiz-grpc
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
        method: GetUser
    backendRefs:
    - name: user-service
      port: 50051
```

既定の Exact match では、method 名の大文字と小文字が区別されます。backend は想定する gRPC transport を提供し、適切な TLS 設定を備えている必要があります。port 番号だけでは、それらを確認できません。service だけを指定した method match は、その service の全 method を対象にします。

</details>

## 12. Ingress との比較で、正しくない説明はどれですか？

- A. Gateway API は listener と Route の所有権をより明確に分離する
- B. Gateway API は専用の TCP／UDP／gRPC routing type を定義する
- C. Standard routing field には実装上のサポート要件がある
- D. Gateway API のリソース型は Ingress より少ない

<details>
<summary>解答を表示</summary>

D. Gateway API は複数のリソース型を導入しています。Ingress にも IngressClass があり、RBAC／admission を利用できます。Ingress に認可や所有権の制御がないとするのは正確ではありません。Gateway API では、いくつかの責務分担や namespace をまたぐ参照の handshakes が、より明示的になっています。すべての API field があらゆる実装で同じ動作をすると仮定せず、controller とバージョンのサポート状況を確認してください。

</details>

[ガイドに戻る](../../networking/04-gateway-api.md)
