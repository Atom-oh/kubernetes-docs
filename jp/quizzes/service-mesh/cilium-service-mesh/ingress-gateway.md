# Cilium Service Mesh Ingress・Gateway クイズ

確認するバージョン: Cilium 1.20.3、Gateway API 1.6.3、AWS LBC 3.6.0。 [ガイド](../../../service-mesh/cilium-service-mesh/05-ingress-gateway.md) と、そこに記載された一次資料を確認してください。

## クイズ問題

### 1. Cilium Ingress の `loadbalancerMode: shared` で共有されるものは何ですか?

- A. クラスター内のすべてのコントローラーが使う 1 つのフロントエンド
- B. このモードを使うリソース向けの、共有 Cilium Ingress Service
- C. 内部 NodePort だけ
- D. すべての Gateway API Gateway

<details>
<summary>答えを表示</summary>

**答え: B. このモードを使うリソース向けの、共有 Cilium Ingress Service**

この設定が適用されるのは、shared モードを使う Cilium 管理の Ingress リソースです。dedicated モードへの個別指定や、別のコントローラーはそれぞれ独立しています。また、GatewayClass を共有しても、クラウドロードバランサーが 1 つになるとは限りません。

</details>

### 2. HTTPRoute を Gateway の HTTPS listener だけに明示的に接続するには、どうしますか?

- A. 親 Pod を指定する
- B. `parentRefs` に Gateway 名と `sectionName: https` を指定する
- C. Route の namespace だけを設定する
- D. 任意の listener annotation を使う

<details>
<summary>答えを表示</summary>

**答え: B. `parentRefs` に Gateway 名と `sectionName: https` を指定する**

section name は listener 名と一致する必要があります。また、その listener の `allowedRoutes` が接続を許可し、hostname と protocol にも互換性が必要です。正しい parent status entry の Accepted/ResolvedRefs を確認してください。parent reference があるだけでは、到達可能であることの証明にはなりません。

</details>

### 3. Cilium Ingress で TLS passthrough を有効にする annotation はどれですか?

- A. `ingress.cilium.io/tls-mode: passthrough`
- B. `ingress.cilium.io/tls-passthrough: "true"`
- C. `cilium.io/tls: passthrough`
- D. nginx 固有の annotation

<details>
<summary>答えを表示</summary>

**答え: B. `ingress.cilium.io/tls-passthrough: "true"`**

TLS はバックエンドで終端します。Ingress には host と `/` path が必要で、Cilium は HTTP path を調べずに SNI を使います。バックエンドが受け取るのは Envoy/ノードからの接続であり、元のクライアントソケットアドレスではありません。

</details>

### 4. Gateway の protocol と port はどこで設定しますか?

- A. `protocols`
- B. `listeners`
- C. `endpoints`
- D. `handlers`

<details>
<summary>答えを表示</summary>

**答え: B. `listeners`**

各 listener で protocol と port、および該当する hostname、TLS、Route 接続の設定を定義します。実際に利用できる protocol の組み合わせはコントローラーによって異なります。たとえば LBC 3.6 は、1 つの Gateway 内で L4/NLB listener と L7/ALB listener を混在させる構成をサポートしていません。

</details>

### 5. このガイドの Cilium shared Ingress NLB フロントエンドで AWS LBC を選択する設定はどれですか?

- A. 従来の `aws-load-balancer-type: nlb` annotation だけを指定する
- B. Service の `spec.loadBalancerClass: service.k8s.aws/nlb`、instance target、割り当て済み NodePort を使う
- C. EndpointSlice を確認せず IP target を使う
- D. 任意の EKS namespace label を使う

<details>
<summary>答えを表示</summary>

**答え: B. Service の `spec.loadBalancerClass: service.k8s.aws/nlb`、instance target、割り当て済み NodePort を使う**

Helm では `ingressController.service.loadBalancerClass` に相当します。Cilium の L7 shared Ingress EndpointSlice は合成されたもので、Pod target への参照を持ちません。そのため LBC の IP resolver はこれをスキップします。EC2 instance と NodePort に関する前提条件も検証が必要です。

</details>

### 6. クライアントをリダイレクトせずに、上流へ転送する hostname/path を書き換える HTTPRoute filter はどれですか?

- A. `PathRewrite`
- B. `URLRewrite`
- C. `RequestTransform`
- D. `RequestRedirect`

<details>
<summary>答えを表示</summary>

**答え: B. `URLRewrite`**

URLRewrite はバックエンドへ転送する request を変更します。RequestRedirect はクライアントに redirect を返します。ガイド内の header 値はリテラル文字列であり、UUID や latency を自動生成するものではありません。

</details>

### 7. 承認済み label のある namespace からの Route だけを、listener で他 namespace から接続できるようにする設定はどれですか?

- A. `allowedRoutes.namespaces.from: All`
- B. `allowedRoutes.namespaces.from: Selector` と一致する selector
- C. `crossNamespace: true`
- D. `routes.scope: cluster`

<details>
<summary>答えを表示</summary>

**答え: B. `allowedRoutes.namespaces.from: Selector` と一致する selector**

All でも namespace をまたぐ接続は許可されますが、label による制限はありません。Same は Gateway と同じ namespace に限定します。別 namespace のバックエンド Service を参照するには、バックエンド側の namespace に ReferenceGrant も必要です。これは Route の接続許可とは別の検査です。

</details>

### 8. Envoy の active health check はどこで設定しますか?

- A. listener の name
- B. Cluster の `health_checks`
- C. Route の name
- D. Endpoint の namespace

<details>
<summary>答えを表示</summary>

**答え: B. Cluster の `health_checks`**

有効な CEC には Service→Listener→Route→Cluster のつながりも必要です。HTTP health check の host/path が実際のバックエンドで機能することを確認してください。期待する status code の上限は範囲に含まれないため、開始値を 200、終了値を 300 にすれば 2xx 全体を対象にできます。

</details>

### 9. HTTP→HTTPS Route をどう接続すると、request method/body を維持する恒久的な redirect にできますか?

- A. HTTP と HTTPS の両方で 302 を使う
- B. HTTP と HTTPS の両方で 307 を使う
- C. HTTP listener のみで 308 を使う
- D. HTTPS listener のみで 303 を使う

<details>
<summary>答えを表示</summary>

**答え: C. HTTP listener のみで 308 を使う**

308 は恒久 redirect で method/body を維持します。307 は一時 redirect に相当します。scheme redirect を HTTP listener だけに結び付けると、HTTPS 自身への redirect ループを避けられます。最初の平文 request ですでに送信されたデータを redirect で保護することはできません。

</details>

### 10. コストと機能の比較として正しいものはどれですか?

- A. Cilium はクラウドロードバランサーを必要としない
- B. AWS LBC は常に高速である
- C. Cilium のノード/プロキシ費用とクラウド LB 料金が併存する場合があるため、バージョンごとの機能を比較する
- D. すべてのコントローラーが Gateway API の全機能をサポートする

<details>
<summary>答えを表示</summary>

**答え: C. Cilium のノード/プロキシ費用とクラウド LB 料金が併存する場合があるため、バージョンごとの機能を比較する**

Cilium を ALB/NLB の背後で動かす構成では、ロードバランサーの料金も発生します。LBC 3.6 は HTTP/GRPC Route を ALB に、TCP/UDP/TLS Route を NLB に対応付けます。ワークロードの mTLS と ACM のサーバー証明書は異なる仕組みです。性能を比べるには、条件をそろえた測定が必要です。

</details>

### 11. Gateway API 1.6.3 の基準環境において、TCPRoute はどのように動作しますか?

- A. HTTP path を調べる
- B. 既定で TLS を終端する
- C. 提供されている v1 API を使って、不透明な TCP stream を転送する
- D. UDP だけを処理する

<details>
<summary>答えを表示</summary>

**答え: C. 提供されている v1 API を使って、不透明な TCP stream を転送する**

TCP は HTTP や TLS を運べますが、TCPRoute にそれらの L7 意味論が加わるわけではありません。この基準環境では古い TCPRoute v1alpha2 API は提供されていません。SNI routing 用の TLSRoute v1 には、互換性のある TLS passthrough listener が必要です。

</details>

### 12. この Cilium Ingress 構成で NLB PPv2 を有効にする場合、何を連携して設定する必要がありますか?

- A. クライアントの X-Forwarded-For header だけ
- B. NLB 側の送信設定と Cilium の `enableProxyProtocol` 受信設定、health check、信頼できるアクセス経路
- C. 受信側の変更は不要
- D. すべての NLB で PPv2 が必須

<details>
<summary>答えを表示</summary>

**答え: B. NLB 側の送信設定と Cilium の `enableProxyProtocol` 受信設定、health check、信頼できるアクセス経路**

parser は PROXY header を必要とするため、片側だけ有効にすると通信が壊れます。PPv2 は任意です。また、クライアント IP の保持は target type とその属性にも左右されます。AWS LBC は instance target と `externalTrafficPolicy: Local` の組み合わせで PPv2 を使わないよう警告しています。PROXY metadata は認証済みの識別情報ではありません。

</details>
