# Gateway API クイズ

このクイズでは、Kubernetes Gateway API のリソースモデル、実装、および Ingress からの移行に関する理解を確認します。

## クイズ問題

### 1. Gateway API が既存の Ingress API を改善している点ではないものはどれですか？

A. ロールベースのリソース分離（インフラストラクチャプロバイダー、クラスターオペレーター、アプリケーション開発者）
B. TCP、UDP、gRPC などのさまざまなプロトコルのネイティブサポート
C. アノテーションではなく標準化されたフィールドによる機能実装
D. すべてのネットワーク機能を単一のリソースに統合

<details>
<summary>解答を表示</summary>

**解答: D. すべてのネットワーク機能を単一のリソースに統合**

**解説:**
Gateway API の改善点:
- **ロール分離**: GatewayClass（インフラストラクチャ）、Gateway（オペレーター）、Routes（開発者）に責任を分離
- **複数プロトコル**: HTTPRoute、GRPCRoute、TCPRoute、TLSRoute、UDPRoute
- **標準化**: アノテーションを使用せず、明示的なフィールドで機能を定義
- **拡張性**: CRD に基づき新機能を容易に追加

Gateway API は複数のリソースに分離されているため、「単一リソースへの統合」は誤りです。

</details>

### 2. Gateway API のロール分離において、GatewayClass を管理するのは誰ですか？

A. アプリケーション開発者
B. クラスターオペレーター
C. インフラストラクチャプロバイダー
D. セキュリティ管理者

<details>
<summary>解答を表示</summary>

**解答: C. インフラストラクチャプロバイダー**

**解説:**
Gateway API のロール分離:

| ロール | 管理対象リソース | 責任 |
|------|------------------|----------------|
| **インフラストラクチャプロバイダー** | GatewayClass | 基本インフラストラクチャ設定の定義、controller の指定 |
| **クラスターオペレーター** | Gateway, ReferenceGrant | Load Balancer のプロビジョニング、namespace 権限の管理 |
| **アプリケーション開発者** | HTTPRoute, GRPCRoute, etc. | アプリケーションルーティングルールの定義 |

GatewayClass はクラウドプロバイダーまたはネットワークチームによって定義されます。

</details>

### 3. Gateway における TLS termination と passthrough の正しい違いは何ですか？

A. Terminate は TLS を backend に渡し、Passthrough は Gateway で termination する
B. Terminate は Gateway で TLS を termination し、Passthrough は TLS を backend に渡す
C. 両方のモードは同じ動作をする
D. Terminate は HTTP のみをサポートし、Passthrough は HTTPS のみをサポートする

<details>
<summary>解答を表示</summary>

**解答: B. Terminate は Gateway で TLS を termination し、Passthrough は TLS を backend に渡す**

**解説:**
TLS モード:

| モード | 説明 | ユースケース |
|------|-------------|----------|
| **Terminate** | TLS は Gateway で termination され、backend は平文を受信 | 標準 HTTPS、証明書の一元管理 |
| **Passthrough** | TLS はそのまま backend に渡される | エンドツーエンド暗号化、backend による証明書管理 |

```yaml
listeners:
  - name: https
    protocol: HTTPS
    tls:
      mode: Terminate  # or Passthrough
```

</details>

### 4. HTTPRoute でトラフィック分割（weight）を実装するにはどうしますか？

A. `trafficSplit` フィールドを使用する
B. 複数の `backendRefs` に `weight` フィールドを指定する
C. `canary` アノテーションを使用する
D. 個別の TrafficSplit CRD を作成する

<details>
<summary>解答を表示</summary>

**解答: B. 複数の `backendRefs` に `weight` フィールドを指定する**

**解説:**
HTTPRoute でのトラフィック分割:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
spec:
  rules:
    - backendRefs:
        - name: app-stable
          port: 80
          weight: 90  # 90%
        - name: app-canary
          port: 80
          weight: 10  # 10%
```

ユースケース:
- Canary Deployment
- A/B テスト
- Blue-green Deployment

weight の合計は 100 である必要はなく、比率として計算されます。

</details>

### 5. ReferenceGrant の主な目的は何ですか？

A. Gateway リソースの権限管理
B. namespace をまたぐ参照を許可する
C. API バージョンの互換性管理
D. TLS 証明書の認可

<details>
<summary>解答を表示</summary>

**解答: B. namespace をまたぐ参照を許可する**

**解説:**
ReferenceGrant の使用方法:

```yaml
apiVersion: gateway.networking.k8s.io/v1beta1
kind: ReferenceGrant
metadata:
  name: allow-routes
  namespace: backend-services
spec:
  from:
    - group: gateway.networking.k8s.io
      kind: HTTPRoute
      namespace: frontend
  to:
    - group: ""
      kind: Service
```

ユースケース:
- 他の namespace にある Service の参照を許可
- Gateway が他の namespace にある Secret（TLS 証明書）を参照
- セキュリティのための明示的な認可

namespace をまたぐ参照はデフォルトでブロックされます。

</details>

### 6. Gateway API の Standard channel に含まれないリソースはどれですか？

A. GatewayClass
B. Gateway
C. HTTPRoute
D. TCPRoute

<details>
<summary>解答を表示</summary>

**解答: D. TCPRoute**

**解説:**
Gateway API の channel 分類:

**Standard Channel (GA)**:
- GatewayClass
- Gateway
- HTTPRoute
- ReferenceGrant

**Experimental Channel (Beta/Alpha)**:
- GRPCRoute
- TCPRoute
- TLSRoute
- UDPRoute

Standard channel のリソースは `gateway.networking.k8s.io/v1` API バージョンを使用し、Experimental では `v1alpha2` または `v1beta1` を使用します。

</details>

### 7. リクエストを別の URL に変更する HTTPRoute filter type はどれですか？

A. RequestHeaderModifier
B. ResponseHeaderModifier
C. URLRewrite
D. RequestMirror

<details>
<summary>解答を表示</summary>

**解答: C. URLRewrite**

**解説:**
HTTPRoute filter type:

| Filter | 説明 |
|--------|-------------|
| RequestHeaderModifier | リクエストヘッダーの追加、変更、削除 |
| ResponseHeaderModifier | レスポンスヘッダーの追加、変更、削除 |
| **URLRewrite** | URL のパスまたは host を変更 |
| RequestRedirect | 別の URL へリダイレクト（3xx レスポンス） |
| RequestMirror | トラフィックをミラーリング（shadow Service にコピー） |

```yaml
filters:
  - type: URLRewrite
    urlRewrite:
      path:
        type: ReplacePrefixMatch
        replacePrefixMatch: /new-api
      hostname: "new-api.example.com"
```

</details>

### 8. Gateway API をサポートする実装ではないものはどれですか？

A. Istio
B. Cilium
C. kube-proxy
D. Envoy Gateway

<details>
<summary>解答を表示</summary>

**解答: C. kube-proxy**

**解説:**
Gateway API の実装:

| 実装 | Controller |
|----------------|------------|
| **Istio** | istio.io/gateway-controller |
| **Cilium** | io.cilium/gateway-controller |
| **Envoy Gateway** | gateway.envoyproxy.io/gatewayclass-controller |
| **AWS Gateway API Controller** | application-networking.k8s.aws/gateway-api-controller |
| **Contour** | projectcontour.io/gateway-controller |
| **NGINX Gateway Fabric** | gateway.nginx.org/nginx-gateway-controller |

kube-proxy は Service の ClusterIP/NodePort ルーティングを処理するものであり、Gateway API とは無関係です。

</details>

### 9. Ingress から Gateway API へ移行する際、Ingress annotation に対応する Gateway API の機能は何ですか？

A. Gateway metadata
B. HTTPRoute matches と filters
C. GatewayClass parameters
D. ReferenceGrant spec

<details>
<summary>解答を表示</summary>

**解答: B. HTTPRoute matches と filters**

**解説:**
Ingress annotation → Gateway API の対応:

| Ingress annotation | Gateway API |
|-------------------|-------------|
| `nginx.ingress.kubernetes.io/rewrite-target` | HTTPRoute filter: URLRewrite |
| `nginx.ingress.kubernetes.io/ssl-redirect` | HTTPRoute filter: RequestRedirect |
| `nginx.ingress.kubernetes.io/canary-weight` | HTTPRoute backendRefs weight |
| パスベースのルーティング | HTTPRoute matches path |
| ヘッダーベースのルーティング | HTTPRoute matches headers |

Gateway API はアノテーションではなく明示的なフィールドを使用するため、より高い移植性を実現します。

</details>

### 10. Gateway で特定の namespace からの Routes のみを許可する設定は何ですか？

A. `allowedRoutes.namespaces.from: All`
B. `allowedRoutes.namespaces.from: Same`
C. `allowedRoutes.namespaces.from: Selector`
D. B と C の両方が可能

<details>
<summary>解答を表示</summary>

**解答: D. B と C の両方が可能**

**解説:**
Gateway の allowedRoutes 設定:

```yaml
listeners:
  - name: https
    allowedRoutes:
      namespaces:
        from: All  # All namespaces
        # or
        from: Same  # Only same namespace as Gateway
        # or
        from: Selector  # Select by label selector
        selector:
          matchLabels:
            gateway-access: "true"
```

- **All**: すべての namespace からの Routes を許可
- **Same**: Gateway と同じ namespace からのみ許可
- **Selector**: 特定のラベルを持つ namespace からのみ許可

</details>

### 11. GRPCRoute で特定の Service の特定の method へルーティングするための matches 設定は何ですか？

A. `path.service` と `path.method`
B. `method.service` と `method.method`
C. `grpc.service` と `grpc.method`
D. `rpc.service` と `rpc.method`

<details>
<summary>解答を表示</summary>

**解答: B. `method.service` と `method.method`**

**解説:**
GRPCRoute のマッチング:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GRPCRoute
spec:
  rules:
    - matches:
        - method:
            service: "myapp.UserService"
            method: "GetUser"
      backendRefs:
        - name: user-service
          port: 50051
```

gRPC のルーティングオプション:
- Service のみ: その Service のすべての method
- Service + method: 特定の method のみ
- ヘッダーベースのルーティングもサポート

</details>

### 12. Gateway API と Ingress API の比較として正しくないものはどれですか？

A. Gateway API はロールベースの分離をサポートするが、Ingress はサポートしない
B. Gateway API は TCP/UDP をネイティブサポートするが、Ingress はサポートしない
C. Gateway API はトラフィック分割をネイティブサポートするが、Ingress ではアノテーションが必要
D. Gateway API は Ingress より少ないリソースタイプを使用する

<details>
<summary>解答を表示</summary>

**解答: D. Gateway API は Ingress より少ないリソースタイプを使用する**

**解説:**
Gateway API と Ingress の比較:

| 機能 | Ingress | Gateway API |
|---------|---------|-------------|
| リソース数 | 1 (Ingress) | 複数（GatewayClass、Gateway、Routes など） |
| ロール分離 | なし | 3 層分離 |
| TCP/UDP | 非対応 | ネイティブサポート |
| トラフィック分割 | Annotation | ネイティブ（weight） |
| 拡張性 | 制限あり | CRD ベース |

Gateway API はより多くのリソースタイプを使用しますが、これによりロール分離と柔軟性が実現されます。

</details>

---

## 追加学習リソース

- [Gateway API 公式ドキュメント](https://gateway-api.sigs.k8s.io/)
- [Gateway API GitHub](https://github.com/kubernetes-sigs/gateway-api)
- [実装固有のガイド](https://gateway-api.sigs.k8s.io/implementations/)
