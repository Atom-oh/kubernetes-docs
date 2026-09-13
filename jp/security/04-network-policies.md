# Network Policies

> **レビュー基準**: Kubernetes 1.35 OpenAPI、Cilium 1.20.1、Calico 3.32.2、および現行の AWS ドキュメント。オフライン確認ではクラスター互換性は確立されません。
> **最終更新**: September 13, 2026

Kubernetes Network Policies は、Pod 間のトラフィックを制御するファイアウォールルールです。このドキュメントでは、基本的な NetworkPolicy と Cilium/Calico 拡張を扱います。各セクションは独立した例です。すべてのポリシーをマージすると、有効な権限が変わります。クラスターまたはクラウドへのデプロイ、ライブ接続テストは実施していません。

## 目次

1. [Network Policy の概要](#network-policy-overview)
2. [Kubernetes NetworkPolicy Spec](#kubernetes-networkpolicy-spec)
3. [デフォルト拒否ポリシー](#default-deny-policies)
4. [ポリシーの順序と評価](#policy-order-and-evaluation)
5. [Cilium Network Policy 拡張](#cilium-network-policy-extensions)
6. [Calico Network Policy 拡張](#calico-network-policy-extensions)
7. [設計パターン](#design-patterns)
8. [Network Policies のテスト](#testing-network-policies)
9. [EKS の考慮事項](#eks-considerations)
10. [可視化ツール](#visualization-tools)

---

## Network Policy の概要 {#network-policy-overview}

### Network Policy とは

Kubernetes NetworkPolicy は自身の namespace 内の Pod を選択し、サポート対象の Ingress と Egress トラフィックを制御します。ある方向に対して選択するポリシーがない Pod は、その方向について NetworkPolicy により隔離されません。ルーティング、security group、NACL、その他のポリシーエンジンは、引き続き接続を防止できます。

Pod 間接続には**両方のエンドポイントの許可が必要**です。すなわち、送信元の有効な Egress ルールと送信先の有効な Ingress ルールの両方が許可しなければなりません。許可された接続の戻りトラフィックは暗黙的に許可されます。ポリシーは対応するネットワークプラグインによって非同期に実装されます。API オブジェクトだけでは強制を証明しません。Node/hostNetwork トラフィックおよび TCP/UDP/SCTP 以外のプロトコルには、実装固有の確認が必要です。以下の図はポリシーの意図を示しており、到達可能性を保証するものではありません。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    No Network Policy (Default State)                     │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │◀──────▶│  Pod B  │◀──────▶│  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│         ▲                  ▲                  ▲                         │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│              Free communication between all Pods                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    With Network Policy Applied                           │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │───────▶│  Pod B  │        │  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│                            ▲                                            │
│                            │ Allowed                                    │
│                       ┌────┴────┐                                       │
│                       │Controlled│                                      │
│                       │by Policy │                                      │
│                       └─────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Network Policy の特性

| プロパティ | 説明 |
|----------|-------------|
| **Namespace Scoped** | NetworkPolicy は namespace 内のリソースに適用されます |
| **Additive** | 選択する Kubernetes NetworkPolicy の許可ルールは、方向ごとに和集合を形成します。Cilium の拒否、Calico の Tier、AWS の管理ポリシーには別のセマンティクスがあります |
| **Selective Application** | podSelector で指定した対象 Pod |
| **Directional Control** | Ingress（受信）と Egress（送信）を個別に制御 |
| **CNI Dependent** | CNI プラグインが NetworkPolicy をサポートする必要があります |

### CNI による NetworkPolicy サポート

| CNI | 基本 NetworkPolicy | 拡張 | L7 ポリシー |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | 任意の Istio/Dikastes 統合。デプロイ済みの製品とバージョンを確認してください |
| **Weave Net (archived project)** | 過去にはサポート | レガシーな参照。新規デプロイでは保守されている実装を評価してください | ✗ |
| **Flannel alone** | 単体ではポリシーを強制しない | 別のサポート対象ポリシーエンジンが必要 | ✗ |
| **Amazon VPC CNI** | 対応する EC2 Linux node で有効化した場合 ✓ | 標準 NetworkPolicy、VPC CNI 1.21+ の ClusterNetworkPolicy | EKS Auto Mode node での DNS Egress。EKS の考慮事項を参照 |

---

## Kubernetes NetworkPolicy Spec {#kubernetes-networkpolicy-spec}

### 基本構造

`policyTypes` を明示的に指定します。省略した場合、Kubernetes は Ingress をデフォルトとし、少なくとも 1 つの Egress ルールがあれば Egress を追加します。空のルール配列だけでは両方向を意味しません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: default
spec:
  # Select Pods to apply policy
  podSelector:
    matchLabels:
      app: web

  # Policy types (auto-inferred if omitted)
  policyTypes:
    - Ingress
    - Egress

  # Ingress rules (inbound traffic)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
        - namespaceSelector:
            matchLabels:
              project: myproject
        - ipBlock:
            cidr: 172.17.0.0/16
            except:
              - 172.17.1.0/24
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443

  # Egress rules (outbound traffic)
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
      ports:
        - protocol: TCP
          port: 5432
```

### podSelector

ポリシーが自身の namespace 内で適用される Pod を選択します。以下はスタンドアロン API リソースではなく、代替の spec フラグメントです。

```yaml
# Apply to Pods with specific labels
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

---
# Apply to all Pods (empty selector)
spec:
  podSelector: {}

---
# Using matchExpressions
spec:
  podSelector:
    matchExpressions:
      - key: app
        operator: In
        values:
          - api
          - web
      - key: environment
        operator: NotIn
        values:
          - development
```

### namespaceSelector

現在の namespace が一致する場合を含め、ラベルで namespace を選択します。`name` は自動的に割り当てられる namespace ラベルではありません。厳密な namespace 名には、組み込みの不変ラベル `kubernetes.io/metadata.name` を使用してください。カスタムのテナンシーラベルを変更できる主体を制限してください。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        # Allow all Pods from monitoring namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
        # Allow specific Pods from production namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: production
          podSelector:
            matchLabels:
              role: frontend
```

**注:** `namespaceSelector` と `podSelector` を併用する場合の AND と OR の違い:

```yaml
# OR condition (two separate peer entries)
ingress:
  - from:
      - namespaceSelector:    # Rule 1
          matchLabels:
            kubernetes.io/metadata.name: team-a
      - podSelector:          # Rule 2
          matchLabels:
            role: frontend

---
# AND condition (single rule)
ingress:
  - from:
      - namespaceSelector:    # Both conditions must be met
          matchLabels:
            kubernetes.io/metadata.name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

`ipBlock` は、そのルール内で CIDR から `except` 範囲を除いた範囲を許可します。例外はグローバルな拒否ではなく、別のポリシーで許可できます。Service/load-balancer のアドレス変換により、CNI に見える送信元または送信先が変わることがあります。実際のパスを確認してください。以下のドキュメント用 CIDR は例示であり、到達可能な本番エンドポイントではありません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: public-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        # Example private source range; not a guarantee of the load balancer source IP
        - ipBlock:
            cidr: 10.0.0.0/8
        # Allow specific external IP
        - ipBlock:
            cidr: 203.0.113.0/24
  egress:
    - to:
        # Allow external API server access
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8      # Exclude internal networks
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### ports

許可するポートとプロトコルを指定します。`endPort` には数値の開始ポートと CNI による範囲サポートが必要です。名前付きポートを範囲の開始にはできません。API に受け入れられただけでは、すべてのプラグインによる強制を証明しません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: port-specific-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Ingress
  ingress:
    - ports:
        # Specific ports
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443
        # Port range (Kubernetes 1.25+)
        - protocol: TCP
          port: 8000
          endPort: 8080
        # Named port
        - protocol: TCP
          port: http
```

---

## デフォルト拒否ポリシー {#default-deny-policies}

空のベースラインは許可を何も付与しません。他の選択ポリシーでは依然としてトラフィックを許可できます。ポリシー変更後の既存接続の動作は実装に依存するため、別途テストする必要があります。

### デフォルト拒否 Ingress

自身の許可を持たない Ingress 隔離ベースラインです。他の選択ポリシーでは依然として Ingress を許可できます。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # Apply to all Pods
  policyTypes:
    - Ingress
  # No ingress rules = block all inbound traffic
```

### デフォルト拒否 Egress

自身の許可を持たない Egress 隔離ベースラインです。他の選択ポリシーでは依然として Egress を許可できます。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  # No egress rules = block all outbound traffic
```

### 完全拒否（Ingress + Egress）

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### DNS を許可するデフォルト拒否

このプロファイルは、`kube-system` 内で `k8s-app=kube-dns` を持つ Pod ベースの CoreDNS を前提とします。TCP と UDP の両方の 53 を許可します。DNS 自体に Ingress 隔離がある場合、そのポリシーもクライアントを許可する必要があります。NodeLocal DNSCache と Auto Mode node-local CoreDNS では、実際のリゾルバーパス/IP プロファイルが必要です。そこでこの Pod selector をそのまま適用しないでください。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress-allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Zero Trust Architecture のデフォルトポリシー

frontend→API の両方向が存在します。これは frontend への受信トラフィックも API→database も許可しません。レビュー済みのフローだけを追加してください。上記の Pod ベース DNS 前提を使用します。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zero-trust-default
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
```

## ポリシーの順序と評価 {#policy-order-and-evaluation}

### ポリシー評価ルール

各エンドポイントと方向について、以下のように選択する **Kubernetes NetworkPolicies** だけを評価します。その後、もう一方のエンドポイントの方向と、その他すべてのネットワーク制御を確認します。Ingress 専用ポリシーは Egress を隔離しません。

```
┌─────────────────────────────────────────────────────────────────┐
│                  NetworkPolicy Evaluation Flow                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Are there policies that apply to the Pod?                   │
│     │                                                           │
│     ├─ No → Allow all traffic (default behavior)                │
│     │                                                           │
│     └─ Yes → Start policy evaluation                            │
│              │                                                  │
│              ▼                                                  │
│  2. Is there a policy for this direction (Ingress/Egress)?      │
│     │                                                           │
│     ├─ No → Allow traffic in that direction                     │
│     │                                                           │
│     └─ Yes → Start rule matching                                │
│              │                                                  │
│              ▼                                                  │
│  3. Does traffic match one or more rules?                       │
│     │                                                           │
│     ├─ Matched → Allow traffic                                  │
│     │                                                           │
│     └─ Not matched → Block traffic                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 複数ポリシーの組み合わせ

複数の NetworkPolicies が同じ Pod に適用される場合、すべてのポリシールールが結合（和集合）されます。

```yaml
---
# Policy 1: Allow traffic from frontend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
# Policy 2: Allow traffic from monitoring
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**結果:** API の Ingress は、8080 の frontend Pod と、8080/9090 の monitoring namespace Pod を許可します。それらの Egress ルール、実際の listener、および他のネットワーク制御も接続を許可する必要があります。

### ポリシー評価順序

Kubernetes NetworkPolicy API には優先順位も明示的な拒否ルールもありません。その許可の和集合は、Calico のポリシー順序/Tier アクション、Cilium の明示的拒否、または AWS 管理ポリシー評価を表すものではありません。

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Policy A    Policy B    Policy C                              │
│   (allow X)   (allow Y)   (allow Z)                             │
│       │           │           │                                 │
│       └───────────┼───────────┘                                 │
│                   │                                             │
│                   ▼                                             │
│           ┌───────────────┐                                     │
│           │     Union     │                                     │
│           │ (X OR Y OR Z) │                                     │
│           └───────────────┘                                     │
│                   │                                             │
│                   ▼                                             │
│           Final allowed traffic:                                │
│           X, Y, Z all allowed                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cilium Network Policy 拡張 {#cilium-network-policy-extensions}

これらの例では、リリース済みの Cilium 1.20.1 ポリシースキーマを使用しており、すべてのクラスターをアップグレードする指示ではありません。HTTP ルールには、サポートされる L7 proxy パスが必要です。AWS VPC CNI chaining には L7 ポリシーを含む、文書化された高度な機能の制約があります。このモードでこれらの HTTP 例が動作すると想定しないでください。数値の Cilium security identity はラベルセットへの割り当てであり、恒久的なアプリケーション ID ではありません。

### CiliumNetworkPolicy

Cilium は、より強力な機能で基本 NetworkPolicy を拡張します。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cilium-l7-policy
  namespace: production
spec:
  # Endpoint selection
  endpointSelector:
    matchLabels:
      app: api

  # L3/L4 rules (similar to basic NetworkPolicy)
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          # L7 rules (Cilium extension)
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
              - method: POST
                path: "/api/v1/users"
                headers:
                  - 'Content-Type: application/json'
```

### L7 HTTP ポリシー

Cilium HTTP ルールは、その L7 proxy から見えるリクエストをフィルタリングします。API key を認証したり管理者ロールを確立したりするものではありません。呼び出し元は `X-User-Role` header を指定できます。この例ではメソッド、パス、および正確な `Content-Type` をフィルタリングします。認証と認可はアプリケーションまたは認証済み gateway で強制してください。エンドツーエンド TLS は HTTP 検査のために自動復号されません。同じトラフィックを L4 で許可する可能性がある他のポリシーを確認してください。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-api-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: web-frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/products
        - method: GET
          path: /api/v1/products/[0-9]+
        - method: POST
          path: /api/v1/orders
          headerMatches:
          - name: Content-Type
            value: application/json
```

[HTTP API — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/http.go)

### L7 Kafka ポリシー

リリース済みの Cilium 1.20.1 CNP スキーマは HTTP と DNS の L7 ルールをサポートしますが、`rules.kafka` はありません。以前の `role`、`topic`、`clientID` のレシピは、現在デプロイ可能な API ではありません。broker 接続は network policy で制限し、`orders` と `events` の producer/consumer 権限は Kafka 認証および ACL で強制してください。client ID は認証済み principal ではありません。

この L4 例は、TCP 9093 上で既に構成された TLS broker listener、同一 namespace の client、および別途認可された client Egress/DNS を前提としています。TLS、broker ACL、topic 権限は構成しません。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-client-network-access
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: producer
    - matchLabels:
        app: consumer
    toPorts:
    - ports:
      - port: '9093'
        protocol: TCP
```

[CNP schema — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)

### L7 DNS ポリシー

この例では Pod ベースの CoreDNS を使用します。port53 の `ANY` は UDP と TCP をカバーします。DNS query の許可と、返された IP への接続許可は別です。以下で database 名を解決しても database 接続は許可されません。例の domain を置き換え、DNS search suffix/cache/TTL を考慮し、実際のリゾルバープロファイルを確認してください。FQDN ルールは DNS から IP を学習します。SaaS tenant を認証したり、TLS/アプリケーション認可を置き換えたりするものではありません。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchName: api.example.com
        - matchName: database.production.svc.cluster.local
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

### CiliumClusterwideNetworkPolicy

このリソースは cluster-scoped ですが、selector により `production/app=api` に明示的に限定されています。TCP8080 上の gateway Pod を許可します。Ingress だけを制御します。Egress 隔離/DNS と gateway 自身の Egress には対応するポリシーが必要です。以前の、全 endpoint/世界を許可する例はデフォルト拒否ポリシーではありませんでした。

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-api-from-edge
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: gateway-system
        app: edge-proxy
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

### Cilium Entity-Based ポリシー

`host` には local node とその host-network container が含まれます。`cluster` にはアプリケーション Pod 以上のものが含まれます。`world` は cluster 外部の endpoint を対象とし、詳細な Internet/SaaS allowlist ではありません。外部アクセスを狭めるときは明示的な CIDR/FQDN ルールを使用してください。この例はラベル付き Kubernetes API client に TCP443 アクセスだけを与えます。API endpoint、TLS trust、credentials、RBAC は別途構成してください。managed-control-plane のネットワークパスでは source identity が変わる可能性があるため、Ingress をクラスター全体に広げるのではなく、実際の flow identity を検査してください。

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kubernetes-api-client
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: kubernetes-api-client
  egress:
  - toEntities:
    - kube-apiserver
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

## Calico Network Policy 拡張 {#calico-network-policy-extensions}

ポリシー/Tier 例は Calico Open Source3.32.2 リソースに従います。`projectcalico.org/v3` には、対応する Calico API server または一致する `calicoctl` workflow が必要です。これは raw Kubernetes `crd.projectcalico.org/v1` storage API ではありません。適用前にインストール済み datastore/API を確認してください。順序付きの Calico action と Tier delegation は、加算的な Kubernetes NetworkPolicy API とは異なります。

現行の Open Source ドキュメントでは、[Istio/Dikastes application-layer integration](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy) も説明されています。HTTPMatch API には別のセットアップが必要で、Ingress Allow ルールをサポートします。以下の Calico 例は L3/L4 ポリシーを扱います。このレビューでは L7 統合をデプロイまたはテストしていません。

### Calico NetworkPolicy

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: calico-policy
  namespace: production
spec:
  # Policy order (lower = evaluated first)
  order: 100

  selector: app == 'api'

  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports:
          - 8080

  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports:
          - 5432
```

### GlobalNetworkPolicy

これら 2 つの global resource は `production` namespace 内の workload のみを選択します。制約のない `selector: all()` は host endpoint にも影響する可能性があります。明示的な範囲と回復パスなしに cluster-wide deny を適用しないでください。Tier 内では低い `order` が先に評価されます。この例は Pod ベース DNS を許可し、それ以外は拒否ベースラインを提供します。レビュー済みアプリケーションフローを追加し、より上位 Tier の action を考慮してください。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-default-deny
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 1000
  types:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-allow-dns
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 100
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

### NetworkSet

NetworkSet selector はリソース名ではなく `metadata.labels` に一致します。最初の set は namespace-scoped です。blocked set は global で、以下の security-tier 例で使用されます。ここにあるすべての CIDR はドキュメント用範囲であり、レビュー済みの送信先に置き換える必要があります。Egress 例は、ラベル付き namespace-scoped set への TCP443 を許可します。DNS は別ルールです。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
  labels:
    network-role: external-api
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.10/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
  labels:
    network-role: blocked
spec:
  nets:
  - 192.0.2.0/24
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-external-apis
  namespace: production
spec:
  selector: app == 'web'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: TCP
    destination:
      selector: network-role == 'external-api'
      ports:
      - 443
```

### Tier-Based ポリシー

Tier は Enterprise のみではなく、参照している Calico Open Source release でも利用できます。選択する Tier は、ルールが action を実行しない場合、デフォルトで `Deny` になります。そのため deny-known-threats Tier は、無関係なトラフィックが後続のポリシーに到達できるよう、明示的に `defaultAction: Pass` を使用します。`Pass` は delegation であり、許可ではありません。アプリケーション Tier のポリシーを追加し、デプロイ前に最終 profile/default-tier の動作を確認してください。空の Tier を作成しても完全なアプリケーション隔離ポリシーにはなりません。 `global()` は `namespaceSelector` に指定し、別のラベルセレクターで `GlobalNetworkSet` を特定します。

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300
  defaultAction: Deny
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Ingress
  ingress:
  - action: Deny
    source:
      selector: network-role == 'blocked'
      namespaceSelector: global()
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

## 設計パターン {#design-patterns}

これらは**代替のポリシープロファイル**であり、同時に適用するバンドルではありません。`production` を再利用しても無関係な例が互換になるわけではありません。許可ルールが累積するからです。最初に namespace、workload ラベル、listen port、実際の DNS プロファイルを準備してください。例はローカルでスキーマ/意図を確認しており、クラスター上では実行していません。

### マイクロセグメンテーション

このプロファイルは、frontend→API TCP8080 と API→database TCP5432 を両側で許可し、さらに DNS を許可します。Internet Egress や外部から frontend への Ingress は意図的に含みません。必要な場合は、承認済みの送信先 CIDR/port または認証済み Egress gateway プロファイルを追加してください。0.0.0.0/0 から RFC1918 を除外しても SaaS allowlist にはなりません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
```

### Namespace 隔離

team profile には同じ team の Ingress **と Egress**、および DNS が含まれます。shared service には、加えて team-a を許可する送信先 Ingress と実際の TLS443 listener が必要です。namespace ラベルの管理を制限してください。team ラベルは独立した trust boundary ではありません。

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - &id001
      namespaceSelector:
        matchLabels:
          team: team-a
  egress:
  - to:
    - *id001
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-shared-services
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          shared-services: 'true'
      podSelector:
        matchLabels:
          exposed: 'true'
    ports:
    - protocol: TCP
      port: 443
```

### Database 保護

`database` namespace が存在する必要があります。production caller と monitoring Pod には自身の Egress 許可が必要です。TCP5432 peer ルールは、想定する PostgreSQL replication transport だけを許可します。database 認証/TLS は別途構成してください。TCP9187 は別途インストールされた exporter を想定しています。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-protection
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: postgresql
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          environment: production
      podSelector:
        matchLabels:
          database-access: 'true'
    ports:
    - protocol: TCP
      port: 5432
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9187
  - from:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### 3-Tier Architecture ポリシー

client TLS を終端し、TCP80 で web Pod に到達できる、既存の `gateway-system/app=edge-proxy` workload を想定します。gateway の Egress ポリシーはこの namespace の範囲外です。data peer の Ingress と Egress では TCP5432/6379 を使用します。追加の replication/cluster-bus/backup port は選択する database に依存し、暗黙に含まれるものではありません。実際のデプロイでは PostgreSQL と Redis selector を分割してください。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: gateway-system
      podSelector:
        matchLabels:
          app: edge-proxy
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: web
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: data
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  - from:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-dns
  namespace: production
spec:
  podSelector:
    matchExpressions:
    - key: tier
      operator: In
      values:
      - web
      - app
      - data
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

---

## Network Policies のテスト {#testing-network-policies}

### netshoot によるテスト

承認済みで、すでにプロビジョニングされた、固定 version の image とレビュー済み権限を持つ diagnostic Pod を使用してください。実際にポリシーを実行する source label/namespace/node placement を選択します。一般的なラベルなし Pod はアプリケーションを表しません。netshoot のプロビジョニングは workload を作成するため、Pod Security admission と競合することがあります。観測スクリプトの一部として固定の共有 `test-pod` 名を作成/削除しないでください。所有するテスト endpoint に対してのみ probe を実行してください。

### kubectl exec によるテスト

context、namespace、既存 Pod、container を明示的に設定してください。DNS 成功は TCP 成功ではありません。connection refusal、unhealthy listener、TLS error、policy drop はそれぞれ異なる結果です。これらのコマンドは接続性だけをテストし、response body は出力しません。このレビュー中にクラスターで実行していません。

```bash
# Both Pods already exist in the approved test environment.
kubectl --context="$CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- nslookup api-service.production.svc.cluster.local
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- curl --silent --show-error --output /dev/null \
  --connect-timeout 3 --max-time 5 http://api-service.production.svc.cluster.local:8080/health
```

### Cilium Connectivity Test

`cilium connectivity test` はテストリソースとトラフィックを作成します。read-only の status command ではありません。承認済みの隔離された cluster/namespace、互換性のある CLI と image、定義済みの外部送信先、および cleanup plan を使用してください。過去の test 名が存在すると想定するのではなく、インストール済み CLI のフィルターについて `cilium connectivity test --help` を参照してください。suite の成功は、すべてのアプリケーションポリシーまたは CNI chaining 機能を証明しません。

### 自動テストスクリプト

このスクリプトは、既存の 2 つの Pod で境界付き curl probe のみを実行します。cluster resource を作成または削除しません。`CONTEXT`、`NAMESPACE`、`ALLOW_POD`、`DENIED_POD`、`PROBE_CONTAINER`、および `/health` で終わる非 secret の `TARGET_URL` を設定してください。両 container に `sh` と `curl` が必要です。最初の Pod は、同じ送信先に対する既知の許可済み positive control です。このテストはアプリケーション health validation ではないため、HTTP error response もネットワーク到達可能性を確立します。

Exit1 は、blocked subject が予期せず接続したことを意味します。exit2 は unknown/error、exit3 は裏付けが必要な timeout を意味します。timeout が自動的に PASS になることは**決してありません**。endpoint health、route、SG/NACL control を確認しつつ、正確な source/destination/port/time を CNI policy-drop verdict と関連付けてください。ローカル mock test によりライブ強制を主張するものではありません。

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
: "${NAMESPACE:?Set the test namespace}"
: "${ALLOW_POD:?Set an existing positive-control Pod}"
: "${DENIED_POD:?Set a different existing policy-subject Pod}"
: "${PROBE_CONTAINER:?Set a container with sh and curl in both Pods}"
: "${TARGET_URL:?Set the same non-secret health URL for both probes}"
if [[ "$ALLOW_POD" == "$DENIED_POD" ||
      ! "$TARGET_URL" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]+)?/health$ ]]; then
  echo "Invalid probe inputs: use different Pods and a plain /health URL." >&2
  exit 2
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-probe.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
probe() {
  local pod=$1 result
  if ! result=$(kubectl --context="$CONTEXT" --request-timeout=15s \
      -n "$NAMESPACE" exec "$pod" -c "$PROBE_CONTAINER" -- \
      sh -c 'rc=0
        curl --silent --output /dev/null --connect-timeout 3 --max-time 5 "$1" || rc=$?
        printf "PROBE_EXIT=%s\n" "$rc"' sh "$TARGET_URL" \
      2>"$work/transport-error"); then
    echo "UNKNOWN: kubectl exec/authorization/transport failed." >&2
    return 2
  fi
  if [[ ! "$result" =~ ^PROBE_EXIT=([0-9]+)$ ]]; then
    echo "UNKNOWN: missing or malformed remote probe result." >&2
    return 2
  fi
  printf '%s\n' "${BASH_REMATCH[1]}"
}
allowed=$(probe "$ALLOW_POD") || exit 2
if [[ "$allowed" != 0 ]]; then
  echo "UNKNOWN: positive control could not reach the target." >&2
  exit 2
fi
denied=$(probe "$DENIED_POD") || exit 2
case "$denied" in
  0) echo "FAIL: the intended blocked Pod reached the target."; exit 1 ;;
  28) echo "INCONCLUSIVE: timeout; correlate an actual policy-drop verdict."; exit 3 ;;
  *) echo "UNKNOWN: DNS/TLS/refused/tool error is not proof of a policy drop."; exit 2 ;;
esac
```

## EKS の考慮事項 {#eks-considerations}

### Amazon VPC CNI と NetworkPolicy

Amazon VPC CNI は有効化後に network policy をサポートします。現行 AWS guide では、標準および admin policy の両方に VPC CNI 1.21+、互換性のある EKS platform、Linux kernel 5.10+ が必要です。強制はサポート対象の EC2 Linux node に適用され、Fargate または Windows には適用されません。現在サポートされる EKS version を使用し、互換性のある add-on release を確認してください。upstream Kubernetes release から EKS サポートを推測しないでください。

**EKS-managed** VPC CNI add-on では、文書化された文字列 `"enableNetworkPolicy": "true"` を設定する際に既存の configuration を保持してください。以下はレビュー後に選択した cluster を変更しますが、add-on version はアップグレードしません。インストール済み version に互換性がない場合は停止し、最初に文書化された upgrade procedure に従ってください。

```bash
# Requires AWS CLI, kubectl and jq; use an approved test cluster.
set -euo pipefail
: "${CLUSTER_NAME:?Set the approved test-cluster name}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --output json > vpc-cni-before.json
jq -e '(.addon.configurationValues // "{}") | if . == "" then {} else fromjson end
  | .enableNetworkPolicy = "true"' vpc-cni-before.json > vpc-cni-network-policy.json
# Review the saved current version/configuration and the complete merged JSON first.
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --configuration-values file://vpc-cni-network-policy.json --resolve-conflicts PRESERVE
```

rollout 前に update status と policy behavior を確認してください。`--resolve-conflicts PRESERVE` は replacement JSON document を自動でマージしません。この例では既存の value を明示的に引き継いでいます。recovery 用に snapshot を保持してください。Helm 所有のインストールでは、レビュー済み chart/values と `enableNetworkPolicy: true` を使用します。この managed-add-on command により所有権を取得しないでください。架空の `ENABLE_NETWORK_POLICY` environment variable を設定しても有効化手順ではありません。

標準 startup mode では、新しい Pod が policy をプログラムされるまで最初は許可されることがあります。`NETWORK_POLICY_ENFORCING_MODE=strict` は対象 Pod を拒否状態で開始し、DNS を含む完全な allow matrix を必要とします。これを変更すると workload が中断することがあります。controller-managed Pod は信頼できるテスト対象です。強制は primary Pod interface 上で行われるため、extra interface、IPv6-to-IPv4 Egress、host networking、NAT は個別に検査してください。同じ標準 policy を管理する 2 つの engine をインストールしたり、migration の近道として `aws-node` を削除したりしないでください。

### EKS Enhanced Network Security Policies（2025 年 12 月）

> **発表**: December 15, 2025 · [出典](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

この機能は実在しますが、resource は **`networking.k8s.aws/v1alpha1`** を使用します。`ClusterNetworkPolicy` は cluster scoped で、必須の `tier` があります。DNS ベース Egress は、以下の namespace 例では `ApplicationNetworkPolicy` を使用します。EC2 Linux 上の標準/admin VPC CNI policy サポートは、すべての compute mode がサポートされることを意味しません。DNS rule は、mixed cluster を含む **Auto Mode で起動された EC2 instance** でのみ強制されます。

**Auto Mode の前提条件:** 以下の policy を適用する前に Network Policy Controller を有効化してください。EKS-managed `vpc-cni` add-on の更新は別のパスであり、pure Auto Mode cluster の policy enforcement は有効になりません。必要な設定は ConfigMap `kube-system/amazon-vpc-cni` の `data.enable-network-policy-controller: "true"` です。以下の workflow は merge patch で他の ConfigMap data を保持し、不在の場合だけ作成し、read または write に失敗すると停止します。実行前に cluster context と既存 configuration をレビューしてください。

```bash
set -euo pipefail
config="$(kubectl get configmap amazon-vpc-cni -n kube-system --ignore-not-found -o name)"
if [ -n "$config" ]; then
  kubectl patch configmap amazon-vpc-cni -n kube-system --type merge \
    -p '{"data":{"enable-network-policy-controller":"true"}}'
else
  kubectl create configmap amazon-vpc-cni -n kube-system \
    --from-literal=enable-network-policy-controller=true
fi
kubectl get configmap amazon-vpc-cni -n kube-system -o json \
  | jq -e '.data["enable-network-policy-controller"] == "true"'
```

有効化後、対応する `PolicyEndpoints` object を検査し、選択した Auto Mode node で許可/拒否両方のトラフィックをテストしてください。保存済み flag または受理された policy object は、強制の証明ではありません。[Auto Mode network policy setup](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html) を参照してください。このドキュメント監査では cluster enforcement test を実行していません。

この Admin-tier 例は、同じ namespace の Pod を含め、namespace selector で選択した Pod から `isolated-demo` への受信トラフィックを拒否します。完全な external/host-network firewall や DNS allow policy ではありません。Admin Deny は namespace NetworkPolicy で上書きできません。他の action を追加する前に、実際にインストールされた CRD をレビューしてください。現行 upstream AWS controller schema では許可 action を `Accept` と呼びますが、user-guide prose では “Allow” を使用しています。

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ClusterNetworkPolicy
metadata:
  name: isolate-demo-namespace
spec:
  tier: Admin
  priority: 10
  subject:
    namespaces:
      matchLabels:
        kubernetes.io/metadata.name: isolated-demo
  ingress:
  - name: deny-pod-ingress
    action: Deny
    from:
    - namespaces:
        matchLabels: {}
```

FQDN 例は `production` 内の `app=backend` を選択します。**`10.100.0.10/32` を cluster の実際の Auto Mode CoreDNS IP に置き換えてください**。これは Service CIDR の network address に 10 を足した値です（IPv6 では `::a/128`）。pure Auto Mode CoreDNS は node 上で実行されます。通常の CoreDNS Pod selector と互換的に入れ替えることはできません。TCP と UDP の両方の DNS を許可してください。その namespace の NetworkPolicy と衝突しない一意な resource 名を使用してください。

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ApplicationNetworkPolicy
metadata:
  name: approved-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.100.0.10/32
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - domainNames:
      - api.stripe.com
    ports:
    - protocol: TCP
      port: 443
```

DNS proxy は許可された answer とその TTL を観測し、続いて data path が学習した destination IP/port を許可します。これは SaaS account を認証したり、peer の HTTP identity を証明したりするものではありません。shared IP と DNS behavior にはテストが必要です。TLS certificate verification、application authorization、route、Route 53 DNS Firewall rule は引き続き関連します。他の適用可能な policy と直接 backend path をまとめてレビューする必要があります。

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [Configuration](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode policies](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Pod の Security Groups

この binding 例は、EKS VPC Resource Controller、その **cluster-role** 権限、対応する trunking-compatible EC2 Linux node、およびレビュー済み VPC CNI configuration を想定しています。現行 AWS guide では Windows と EKS Auto Mode を対象外としています。Fargate は別の Pod-SG model を使用しており、security group を持つだけで VPC-CNI NetworkPolicy support を得るわけではありません。owner を通じ、新しい一致 workload Pod に binding を適用してください。既存 Pod は自動で retrofit されません。

Calico と Pod SG を併用する場合、AWS は `POD_SECURITY_GROUP_ENFORCING_MODE=standard` を持つ VPC CNI1.11.0+ を文書化しています。その最小値を推奨 version とみなすのではなく、現行 CNI requirement も使用してください。standard-mode の external SNAT では Pod SG ではなく node SG を使用することがあります。正確な path を確認してください。以前の bare PostgreSQL Pod には credentials/storage がなく、機能する database deployment ではありませんでした。

```yaml
# Binding example only: use an existing reviewed security group.
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

Terraform fragment は、レビュー済みの 1 つの app SG から DB Ingress を許可し、新規 Egress connection は開始しません。stateful return traffic は SG tracking により許可されます。必要な DNS、replication、backup、external Egress のみを個別に追加してください。variable は既存 operator input です。Terraform plan/apply は実行していません。

```hcl
# Fragment for an existing reviewed Terraform configuration.
# Supply the actual VPC and application SG; this is not a standalone module.
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.application_security_group_id]
  }
  egress = []
}
```

### VPC レベルの制御と NetworkPolicy の組み合わせ

NetworkPolicy、実際に適用された SG、NACL はすべて、該当パスを許可する必要があります。この Ingress 専用 NetworkPolicy は database Egress を制限しません。選択した Egress profile と source-Pod Egress を追加してください。複数の SG はその許可を結合します。NACL は**ステートレス**です。したがって、inbound5432 を許可する subnet rule には、client の ephemeral port への一致する return path と、client subnet 上の適切な rule が必要です。以下の fragment は完全にレビュー済みの ACL rule set を置き換えるものではありません。

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Fragments for a DB subnet NACL and an explicitly reviewed client CIDR.
# Choose the client's actual ephemeral port range; also review its subnet NACL.
resource "aws_network_acl_rule" "database_inbound" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = 5432
  to_port        = 5432
}
resource "aws_network_acl_rule" "database_return" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = var.client_ephemeral_port_start
  to_port        = var.client_ephemeral_port_end
}
```

### EKS での Cilium の使用

**AWS VPC CNI chaining** を選択するか、別途設計した完全な CNI/IPAM migration を選択してください。chaining mode では AWS VPC CNI が ENI/IPAM responsibility を維持し、Cilium が datapath を接続します。`aws-node` を保持してください。削除は installation shortcut ではありません。既存 add-on/Helm owner をレビューし、重複する policy-enforcement engine を避けてください。chaining policy が適用される前に既存 Pod の制御された再作成が必要です。中断と rollback を計画してください。

公式の1.20.1 chaining guide はこれらの value を提供していますが、L7/IPsec の制限も文書化しています。古い例示 output を含みますが、それらは現在の EKS environment の validation ではありません。chart repository/package を準備し、provenance を確認してから render してください。

```bash
# Render locally after verifying the official chart/package provenance.
# Rendering alone does not change a cluster or validate a migration.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native > cilium-reviewed.yaml
```

[AWS VPC CNI chaining — Cilium 1.20.1](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/)

## 可視化ツール {#visualization-tools}

### Cilium Network Policy Editor

policy editor は policy の作成に役立ちます。**Hubble UI は観測された service flow を可視化します**。これらは異なるツールです。Hubble/UI の有効化は cluster configuration を変更するため、installation owner が実施すべきです。既にインストールされ、認証済みの Hubble service がある場合は、既存 service を検査して local port-forward を使用してください。debugging shortcut として UI を公開しないでください。

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Cilium Policy Verdict Check

認証済み Hubble connection を使用してください。`DROPPED` には policy 以外の理由も含まれます。drop reason、endpoint identity、time、direction を検査してください。ある地点での `FORWARDED` 観測は end-to-end delivery の保証ではありません。


```bash
# Inspect observed policy decisions
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# Check traffic for specific Pod
hubble observe --pod production/api-server

# Output in JSON format
hubble observe --output json | jq '.flow.verdict'
```

### Calico Enterprise UI

Enterprise management UI には licensed product と実際の service/TLS/authentication configuration が必要です。Calico Open Source により自動でインストールされるものではありません。forwarding 前にインストール済み service name/port と access policy を検査してください。すべての installation に `cnx-manager` が存在すると想定しないでください。

### Network Policy 可視化ツール

Kubernetes policy selector/rule の検査には `kubectl get networkpolicy -n <namespace>` と `kubectl describe networkpolicy <name> -n <namespace>` を使用し、強制の検査にはインストール済み engine の認証済み flow tool を使用してください。third-party viewer/plugin の可用性と flag は、その project の current release に対して確認する必要があります。YAML だけの graph では dataplane enforcement を証明できません。

### Kube-hunter による Security Testing

kube-hunter は cluster exposure/security scanner であり、NetworkPolicy の allow/deny verifier ではありません。その scan は intrusive traffic を生成する可能性があります。明示的に承認された target/scope と、レビュー済み release/image を使用してください。一般的な policy tutorial から、固定されていない scanner を live namespace にデプロイしないでください。このレビューでは scanner を実行していません。

## ベストプラクティス

### 1. デフォルト拒否ポリシーを適用する

```yaml
# Applies only to this production namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### 2. 最小権限の原則

必要なトラフィックだけを明示的に許可します。

```yaml
# Explicit and specific rules
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-minimal-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8080
          protocol: TCP
```

### 3. ポリシーを文書化する

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: production
  annotations:
    description: "Allow traffic from frontend to API on port 8080"
    owner: "platform-team"
    review-ticket: "REPLACE_WITH_APPROVED_CHANGE"
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

### 4. 定期的なポリシー監査

この read-only inventory は、namespace 全体の空の許可ベースラインを Ingress と Egress で個別に一覧化します。空の `[]` と欠落した rule array を処理しますが、rule `{}` はトラフィックを許可するため、拒否ベースラインではありません。API/authorization error は、ポリシーゼロとして表示されるのではなく失敗します。リストされた baseline は**隔離の証明ではありません**。他の allow rule、extension policy、対象外 Pod、CNI state は引き続きレビューが必要です。

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-inventory.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
if ! kubectl --context="$CONTEXT" --request-timeout=15s get namespaces -o json >"$work/namespaces.json"; then
  echo "UNKNOWN: namespace inventory failed." >&2
  exit 2
fi
if ! kubectl --context="$CONTEXT" --request-timeout=15s get networkpolicies -A -o json >"$work/policies.json"; then
  echo "UNKNOWN: policy inventory failed." >&2
  exit 2
fi
jq -n --slurpfile ns "$work/namespaces.json" --slurpfile np "$work/policies.json" '
  def directions:
    (.spec.policyTypes // []) as $types |
    if ($types | length) > 0 then $types
    else ["Ingress"] + (if ((.spec.egress // []) | length) > 0 then ["Egress"] else [] end)
    end;
  def selects_all:
    ((.spec.podSelector.matchLabels // {}) | length) == 0 and
    ((.spec.podSelector.matchExpressions // []) | length) == 0;
  def empty_baseline($direction; $rules):
    select(selects_all and ((directions | index($direction)) != null) and
           ((.spec[$rules] // []) | length) == 0) | .metadata.name;
  {
    note: "Inventory only: other allow rules, extension policies and CNI enforcement are not evaluated.",
    namespaces: [
      $ns[0].items[] | .metadata.name as $name |
      [$np[0].items[] | select(.metadata.namespace == $name)] as $policies |
      {
        namespace: $name,
        policyCount: ($policies | length),
        ingressBaselines: [$policies[] | empty_baseline("Ingress"; "ingress")],
        egressBaselines: [$policies[] | empty_baseline("Egress"; "egress")]
      }
    ]
  }
'
```

## まとめ

Kubernetes Network Policies は、cluster 内の Pod 通信を制御する中核的な security mechanism です。

1. **基本 NetworkPolicy**: Namespace-scoped で、podSelector/namespaceSelector/ipBlock をサポート
2. **Cilium 拡張**: L7 policy、DNS FQDN ベース policy、cluster-wide policy
3. **Calico 拡張**: GlobalNetworkPolicy、NetworkSet、Tier-based policy
4. **EKS の考慮事項**: VPC CNI NetworkPolicy activation、Pod の Security Groups、ClusterNetworkPolicy、DNS（FQDN）ベース Egress control

### 推奨事項

- すべての production namespace にデフォルト拒否ポリシーを適用する
- 最小権限の原則に従い、必要なトラフィックだけを許可する
- 定期的なポリシー監査とテストを行う
- L7 policy が必要な場合は Cilium を検討する

---

## 参考資料

- [Kubernetes Network Policies 公式ドキュメント](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy ドキュメント](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico Network Policy ドキュメント](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS Security Best Practices - Network Security](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS Enhanced Network Security Policies (2025-12-15)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod security groups](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
