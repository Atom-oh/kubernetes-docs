# Cilium Service Mesh Ingress & Gateway クイズ

このクイズでは、Cilium Ingress Controller、Gateway API、TLS termination、EKS 統合パターンについての理解を確認します。

## クイズ問題

### 1. Cilium Ingress Controller の loadbalancerMode オプションにおける「shared」モードとは何を意味しますか？

A. 各 Ingress 用に個別の load balancer を作成する
B. すべての Ingress が 1 つの load balancer を共有する
C. load balancer を使用せず NodePort のみを使用する
D. internal traffic のみを処理する

<details>
<summary>回答を表示</summary>

**回答: B. すべての Ingress が 1 つの load balancer を共有する**

**解説:**
loadbalancerMode: shared 設定により、すべての Ingress リソースが単一の共有 load balancer を使用します。これはコスト効率に優れており、dedicated モードでは各 Ingress 用に個別の load balancer が作成されます。

</details>

### 2. Gateway API の HTTPRoute における parentRefs フィールドの役割は何ですか？

A. 親 Pod を定義する
B. この route が接続する Gateway を指定する
C. 親 namespace を参照する
D. 継承する policy を定義する

<details>
<summary>回答を表示</summary>

**回答: B. この route が接続する Gateway を指定する**

**解説:**
parentRefs は、HTTPRoute が接続する Gateway を指定します。Gateway の名前と namespace を参照することで、route が適用される listener を決定します。

</details>

### 3. Cilium Ingress で TLS passthrough を有効にする annotation はどれですか？

A. ingress.cilium.io/tls-mode: passthrough
B. ingress.cilium.io/tls-passthrough: "true"
C. cilium.io/tls: passthrough
D. nginx.ingress.kubernetes.io/ssl-passthrough

<details>
<summary>回答を表示</summary>

**回答: B. ingress.cilium.io/tls-passthrough: "true"**

**解説:**
`ingress.cilium.io/tls-passthrough: "true"` annotation は、TLS traffic を termination せずに直接 backend service へ転送します。これは backend が TLS を処理する必要がある場合に役立ちます。

</details>

### 4. Gateway API の Gateway リソースで複数の protocol をサポートするために使用されるフィールドはどれですか？

A. protocols
B. listeners
C. endpoints
D. handlers

<details>
<summary>回答を表示</summary>

**回答: B. listeners**

**解説:**
Gateway の listeners フィールドには複数の listener を定義でき、HTTP、HTTPS、TCP、TLS などのさまざまな protocol をサポートします。各 listener では、protocol、port、hostname などを個別に設定できます。

</details>

### 5. EKS 上の Cilium Ingress で NLB を使用するために必要な annotation はどれですか？

A. service.kubernetes.io/load-balancer-type: nlb
B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
C. eks.amazonaws.com/load-balancer: nlb
D. aws.load-balancer/type: network

<details>
<summary>回答を表示</summary>

**回答: B. service.beta.kubernetes.io/aws-load-balancer-type: "nlb"**

**解説:**
AWS EKS で Network Load Balancer を使用するには、service に `service.beta.kubernetes.io/aws-load-balancer-type: "nlb"` annotation を追加します。scheme、target-type などの追加 annotation により、NLB の動作をさらに設定できます。

</details>

### 6. Gateway API の HTTPRoute で URL rewriting を設定するために使用される filter type はどれですか？

A. PathRewrite
B. URLRewrite
C. RequestTransform
D. PathModifier

<details>
<summary>回答を表示</summary>

**回答: B. URLRewrite**

**解説:**
HTTPRoute の filters セクションでは、type: URLRewrite を使用して request URL を書き換えます。path と hostname の両方を変更できます。

</details>

### 7. Cilium Gateway API で cross-namespace routing を許可するために必要な Gateway 設定はどれですか？

A. allowedRoutes.namespaces.from: All
B. allowedRoutes.namespaces.from: Selector
C. crossNamespace: true
D. routes.scope: cluster

<details>
<summary>回答を表示</summary>

**回答: B. allowedRoutes.namespaces.from: Selector**

**解説:**
Gateway の listeners で allowedRoutes.namespaces.from: Selector を設定すると、selector を使用して特定の label を持つ namespace からの route のみを許可します。'All' はすべての namespace を許可し、'Same' は同じ namespace のみを許可します。

</details>

### 8. CiliumEnvoyConfig で service health check を設定するために使用される Envoy resource type はどれですか？

A. envoy.config.listener.v3.Listener
B. envoy.config.cluster.v3.Cluster
C. envoy.config.route.v3.Route
D. envoy.config.endpoint.v3.Endpoint

<details>
<summary>回答を表示</summary>

**回答: B. envoy.config.cluster.v3.Cluster**

**解説:**
health check 設定は、Cluster resource の health_checks フィールドで定義します。HTTP health check、TCP health check、interval、threshold などを設定できます。

</details>

### 9. Gateway API で HTTP から HTTPS へ redirect する場合に推奨される statusCode はどれですか？

A. 302 (Found)
B. 307 (Temporary Redirect)
C. 301 (Moved Permanently)
D. 303 (See Other)

<details>
<summary>回答を表示</summary>

**回答: C. 301 (Moved Permanently)**

**解説:**
HTTP から HTTPS への permanent redirect には、status code 301 が推奨されます。これにより URL が恒久的に変更されたことが browser と search engine に通知され、caching と SEO に有効です。

</details>

### 10. Cilium と AWS Load Balancer Controller の主な違いは何ですか？

A. Cilium は L4 のみをサポートする
B. AWS LBC はより低い latency を提供する
C. Cilium は追加の LB コストなしで node resource のみを使用する
D. AWS LBC は Gateway API を完全にサポートする

<details>
<summary>回答を表示</summary>

**回答: C. Cilium は追加の LB コストなしで node resource のみを使用する**

**解説:**
Cilium Ingress/Gateway は node の eBPF と Envoy を使用して external traffic を処理するため、AWS load balancer の個別コストはかかりません。一方、AWS LBC は ALB/NLB を provision するため、追加コストが発生します。

</details>

### 11. Gateway API における TCPRoute の用途は何ですか？

A. HTTP traffic の routing
B. TLS termination が必要な traffic
C. raw TCP traffic（非 HTTP）の routing
D. UDP traffic のみ

<details>
<summary>回答を表示</summary>

**回答: C. raw TCP traffic（非 HTTP）の routing**

**解説:**
TCPRoute は、database connection や message queue などの HTTP ではない raw TCP traffic を routing するために使用されます。Gateway の TCP listener と連携し、非 HTTP service への external access を提供します。

</details>

### 12. Cilium Ingress で client IP を保持するために使用される NLB 設定はどれですか？

A. X-Forwarded-For header
B. Proxy Protocol
C. Disable Source NAT
D. Direct Server Return

<details>
<summary>回答を表示</summary>

**回答: B. Proxy Protocol**

**解説:**
NLB で client IP を保持するには、Proxy Protocol を有効にする必要があります。`service.beta.kubernetes.io/aws-load-balancer-proxy-protocol: "*"` annotation を使用します。Envoy は Proxy Protocol header から元の client IP を抽出します。

</details>
