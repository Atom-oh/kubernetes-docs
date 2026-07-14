# Linkerd アーキテクチャクイズ

このクイズでは、Linkerd アーキテクチャの理解度を確認します。

## クイズ問題

### 1. Linkerd control planeのコアコンポーネントではないものはどれですか？

A. Destination Controller
B. Identity Controller
C. Proxy Injector
D. Envoy Proxy

<details>
<summary>回答を表示</summary>

**回答: D. Envoy Proxy**

**解説:**
Linkerd control planeは、Destination、Identity、Proxy Injectorで構成されます。EnvoyはIstioのdata plane proxyであり、LinkerdはRustで記述された独自のlinkerd2-proxyを使用します。

</details>

### 2. linkerd2-proxyはどのプログラミング言語で記述されていますか？

A. Go
B. C++
C. Rust
D. Java

<details>
<summary>回答を表示</summary>

**回答: C. Rust**

**解説:**
linkerd2-proxyはRustで記述されており、メモリ安全性と高いパフォーマンスを実現します。使用するメモリは約10MBで、追加されるp99レイテンシは1ms未満です。

</details>

### 3. Destination Controllerの主な役割ではないものはどれですか？

A. Service discovery
B. Certificate issuance
C. ServiceProfile information delivery
D. Endpoint updates

<details>
<summary>回答を表示</summary>

**回答: B. Certificate issuance**

**解説:**
Certificate issuanceはIdentity Controllerの役割です。Destination Controllerは、Service discovery、Endpoint updates、ServiceProfileおよびTrafficSplitポリシーの配布を担当します。

</details>

### 4. Linkerdのcertificate hierarchyの最上位にあるものは何ですか？

A. Workload Certificate
B. Identity Issuer
C. Trust Anchor
D. Proxy Certificate

<details>
<summary>回答を表示</summary>

**回答: C. Trust Anchor**

**解説:**
certificate hierarchyは、Trust Anchor (Root CA) → Identity Issuer (Intermediate CA) → Workload Certificateです。Trust AnchorはPKIのルートであり、すべてのcertificate chainにおける信頼の基盤です。

</details>

### 5. workload certificateのデフォルトの有効期間はどれですか？

A. 1 hour
B. 24 hours
C. 7 days
D. 30 days

<details>
<summary>回答を表示</summary>

**回答: B. 24 hours**

**解説:**
Linkerdのworkload certificateのデフォルト有効期間は24時間です。Proxyは有効期限が切れる前にcertificateを自動更新します。有効期間を短くすることで、certificateが侵害された場合のリスクを最小限に抑えます。

</details>

### 6. Proxy InjectorはどのKubernetesメカニズムを使用しますか？

A. DaemonSet
B. CronJob
C. Admission Webhook
D. Custom Controller

<details>
<summary>回答を表示</summary>

**回答: C. Admission Webhook**

**解説:**
Proxy InjectorはMutating Admission Webhookとして動作します。Pod作成リクエストをインターセプトし、linkerd-proxy sidecarとlinkerd-init init containerを自動的にinjectします。

</details>

### 7. linkerd-init containerの役割は何ですか？

A. Download proxy configuration
B. Set up iptables rules
C. Generate certificates
D. Collect metrics

<details>
<summary>回答を表示</summary>

**回答: B. Set up iptables rules**

**解説:**
linkerd-initはInit containerとして実行され、iptables rulesを設定します。これらのrulesは、すべてのinbound/outbound trafficをlinkerd-proxyにリダイレクトします。

</details>

### 8. Linkerd proxyのinbound portはどれですか？

A. 4140
B. 4143
C. 4191
D. 8080

<details>
<summary>回答を表示</summary>

**回答: B. 4143**

**解説:**
Linkerd proxyのportsは、4143（inbound）、4140（outbound）、4191（admin/metrics）です。inbound portは他のServiceからのtrafficを受け取ります。

</details>

### 9. 正しいSPIFFE ID formatはどれですか？

A. `spiffe://cluster/namespace/service`
B. `spiffe://trust-domain/ns/namespace/sa/service-account`
C. `https://linkerd.io/identity/namespace/pod`
D. `urn:linkerd:identity:namespace:pod`

<details>
<summary>回答を表示</summary>

**回答: B. `spiffe://trust-domain/ns/namespace/sa/service-account`**

**解説:**
LinkerdのSPIFFE IDは、`spiffe://<trust-domain>/ns/<namespace>/sa/<service-account>`のformatに従います。例: `spiffe://root.linkerd.cluster.local/ns/production/sa/web-server`

</details>

### 10. IstioのEnvoyと比較したlinkerd2-proxyの特性ではないものはどれですか？

A. Lower memory usage
B. Wasm extension support
C. Lower latency
D. Smaller binary size

<details>
<summary>回答を表示</summary>

**回答: B. Wasm extension support**

**解説:**
linkerd2-proxyはWasm extensionsをサポートしません（extensibilityは限定的です）。その代わり、~10MBのmemory（Envoyは~50-100MB）、1ms未満のp99 latency（Envoyは2-5ms）、~10MBのbinary（Envoyは~60MB）と、よりlightweightです。

</details>

### 11. Identity Controllerはcertificateを発行する前に何を検証しますか？

A. Pod's IP address
B. ServiceAccount token
C. Namespace labels
D. ConfigMap settings

<details>
<summary>回答を表示</summary>

**回答: B. ServiceAccount token**

**解説:**
Identity Controllerは、proxyが送信したCSRに添付されたServiceAccount tokenを検証します。これにより、proxyのidentity（SPIFFE ID）が実際のworkloadと一致することを確認します。

</details>

### 12. Linkerd proxy admin port（4191）が提供しないものはどれですか？

A. Prometheus metrics
B. Health check endpoints
C. Traffic routing configuration
D. Proxy version information

<details>
<summary>回答を表示</summary>

**回答: C. Traffic routing configuration**

**解説:**
admin port（4191）は、Prometheus metrics（/metrics）、health checks（/ready、/live）、およびproxy informationを提供します。Traffic routing configurationは、Destination ControllerからgRPC経由でproxiesに配信されます。

</details>
