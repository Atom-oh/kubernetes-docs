# Network Policies

> **検証ベースライン**: Kubernetes 1.35 OpenAPI、Cilium 1.20.1、Calico 3.32.2 および現行の AWS ドキュメント。オフラインチェックはクラスターの互換性を保証するものではありません。
> **最終更新**: September 13, 2026

Kubernetes Network Policy (ネットワークポリシー) は、Pod 間のトラフィックを制御するファイアウォールルールです。このドキュメントでは、基本的な NetworkPolicy と Cilium/Calico の拡張機能について説明します。各セクションは独立した例であり、すべてのポリシーをマージすると実効的な権限が変わります。クラスター/クラウドへのデプロイや実環境での接続性テストは実施していません。

## 目次

1. [Network Policy の概要](#network-policy-overview)
2. [Kubernetes NetworkPolicy の仕様](#kubernetes-networkpolicy-spec)
3. [デフォルト拒否ポリシー](#default-deny-policies)
4. [ポリシーの順序と評価](#policy-order-and-evaluation)
5. [Cilium Network Policy の拡張](#cilium-network-policy-extensions)
6. [Calico Network Policy の拡張](#calico-network-policy-extensions)
7. [設計パターン](#design-patterns)
8. [Network Policy のテスト](#testing-network-policies)
9. [EKS における考慮事項](#eks-considerations)
10. [可視化ツール](#visualization-tools)

---

## Network Policy の概要 {#network-policy-overview}

### Network Policy とは

Kubernetes NetworkPolicy は自身の namespace 内の Pod を選択し、サポートされる ingress および egress トラフィックを制御します。ある方向について自身を選択するポリシーが存在しない Pod は、その方向において NetworkPolicy による分離を受けません。ただし、ルーティング、security group、NACL、その他のポリシーエンジンによって接続が遮断される可能性は残ります。

Pod 間の接続には**両端のエンドポイントが許可すること**が必要です。すなわち、送信元の実効的な egress ルールと宛先の実効的な ingress ルールの両方が許可しなければなりません。許可された接続の戻りトラフィックは暗黙的に許可されます。ポリシーはサポートするネットワークプラグインによって非同期に実装されるため、API オブジェクトが存在するだけでは適用が保証されたことにはなりません。Node/hostNetwork のトラフィックや TCP/UDP/SCTP 以外のプロトコルは、実装固有の確認が必要です。以下の図はポリシーの意図を示すもので、到達性の保証ではありません。

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
| **Namespace スコープ** | NetworkPolicy は namespace 内のリソースに適用される |
| **加算的** | 選択している Kubernetes NetworkPolicy の allow ルールは方向ごとに和集合を形成する。Cilium の deny、Calico の tier、AWS の管理ポリシーはそれぞれ異なるセマンティクスを持つ |
| **選択的な適用** | 対象 Pod は podSelector で指定する |
| **方向ごとの制御** | Ingress (受信) と Egress (送信) を個別に制御する |
| **CNI 依存** | CNI プラグインが NetworkPolicy をサポートしている必要がある |

### CNI の NetworkPolicy サポート状況

| CNI | 基本的な NetworkPolicy | 拡張 | L7 ポリシー |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy、CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy、NetworkSet、Tier | Istio/Dikastes 連携はオプション。デプロイ済みの製品とバージョンを確認すること |
| **Weave Net (アーカイブ済みプロジェクト)** | 過去にサポート | 参考情報としての位置付け。新規デプロイではメンテナンスされている実装を評価すること | ✗ |
| **Flannel 単体** | 単体ではポリシーを適用しない | 別途サポートされたポリシーエンジンが必要 | ✗ |
| **Amazon VPC CNI** | サポート対象の EC2 Linux ノードで有効化した場合は ✓ | 標準の NetworkPolicy。VPC CNI 1.21 以降では ClusterNetworkPolicy | EKS Auto Mode ノードでの DNS egress。EKS の考慮事項を参照 |

---

## Kubernetes NetworkPolicy の仕様 {#kubernetes-networkpolicy-spec}

### 基本構造

`policyTypes` は明示的に指定してください。省略した場合、Kubernetes はデフォルトで Ingress を設定し、egress ルールが 1 つ以上あれば Egress を追加します。空のルール配列だけで両方向が指定されるわけではありません。

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

自身の namespace 内で、ポリシーを適用する Pod を選択します。以下は代替となる spec の断片であり、単独で成立する API リソースではありません。

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

ラベルによって namespace を選択します。条件に一致すれば現在の namespace も含まれます。`name` は自動的に付与される namespace ラベルではありません。正確な namespace 名を指定するには、組み込みの変更不可なラベル `kubernetes.io/metadata.name` を使用し、カスタムのテナンシーラベルを変更できる主体を制限してください。

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

**注意:** `namespaceSelector` と `podSelector` を併用する場合の AND と OR の違い:

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

`ipBlock` は、そのルール内で CIDR から `except` の範囲を除いた範囲を許可します。例外指定はグローバルな拒否ではなく、別のポリシーがそれを許可することもあります。Service やロードバランサーによるアドレス変換により、CNI から見える送信元や宛先が変わる場合があるため、実際の経路を確認してください。以下のドキュメント用 CIDR は説明のためのものであり、到達可能な本番エンドポイントではありません。

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

許可するポートとプロトコルを指定します。`endPort` には数値の開始ポートと CNI による範囲指定のサポートが必要で、名前付きポートを範囲の開始にすることはできません。API が受け付けるだけでは、すべてのプラグインで適用されることの証明にはなりません。

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

空のベースラインは許可を一切追加しません。他に選択しているポリシーがあれば、依然としてトラフィックを許可できます。ポリシー変更後の既存接続の挙動は実装依存であり、別途テストが必要です。

### デフォルトで Ingress を拒否

自身は許可を持たない ingress 分離ベースラインです。他に選択しているポリシーがあれば ingress を許可できます。

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

### デフォルトで Egress を拒否

自身は許可を持たない egress 分離ベースラインです。他に選択しているポリシーがあれば egress を許可できます。

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

### 完全拒否 (Ingress + Egress)

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

### DNS を許可したデフォルト拒否

このプロファイルは、`kube-system` 内で `k8s-app=kube-dns` を持つ Pod ベースの CoreDNS を前提としています。TCP と UDP の 53 番ポートの両方を許可します。DNS 自体に ingress 分離が適用されている場合は、そのポリシーでもクライアントを許可する必要があります。NodeLocal DNSCache や Auto Mode のノードローカル CoreDNS では、実際のリゾルバーの経路/IP に応じたプロファイルが必要です。この Pod セレクターをそのまま適用しないでください。

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

### ゼロトラストアーキテクチャのデフォルトポリシー

frontend→API の両方向が定義されています。これは frontend への受信トラフィックや API→database を許可するものではありません。レビュー済みのフローのみを追加してください。上記の Pod ベース DNS の前提を使用します。

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

### ポリシー評価のルール

各エンドポイントと方向について、以下のように自身を選択している **Kubernetes NetworkPolicy** のみを評価します。その後、もう一方のエンドポイントの該当方向と、その他すべてのネットワーク制御を確認します。ingress のみのポリシーは egress を分離しません。

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

同じ Pod に複数の NetworkPolicy が適用される場合、すべてのポリシールールが結合されます (和集合):

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

**結果:** API の ingress は、frontend Pod からの 8080 と monitoring namespace の Pod からの 8080/9090 を許可します。接続が成立するには、それらの egress ルール、実際のリスナー、その他のネットワーク制御も許可している必要があります。

### ポリシーの評価順序

Kubernetes NetworkPolicy API には優先度や明示的な拒否ルールがありません。その allow の和集合は、Calico のポリシー順序/tier のアクション、Cilium の明示的な deny、AWS の管理ポリシーの評価を表すものではありません。

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

## Cilium Network Policy の拡張 {#cilium-network-policy-extensions}

これらの例はリリース済みの Cilium 1.20.1 のポリシースキーマを使用しており、すべてのクラスターをアップグレードするよう指示するものではありません。HTTP ルールにはサポートされた L7 プロキシ経路が必要です。AWS VPC CNI チェイニングには L7 ポリシーを含む高度な機能の制限が文書化されているため、これらの HTTP の例がそのモードで動作すると想定しないでください。Cilium の数値のセキュリティアイデンティティはラベルセットに対する割り当てであり、恒久的なアプリケーション ID ではありません。

### CiliumNetworkPolicy

Cilium は基本的な NetworkPolicy をより強力な機能で拡張します。

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

Cilium の HTTP ルールは、その L7 プロキシから見えるリクエストをフィルタリングするものであり、API キーの認証や管理者ロールの確立は行いません。呼び出し側は `X-User-Role` ヘッダーを自由に付与できます。この例はメソッド、パス、および完全一致の `Content-Type` をフィルタリングします。認証と認可はアプリケーション、または認証済みのゲートウェイで適用してください。エンドツーエンドの TLS が HTTP 検査のために自動的に復号されることはありません。同じトラフィックを L4 で許可している可能性のある他のポリシーも確認してください。

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

リリース済みの Cilium 1.20.1 の CNP スキーマは HTTP と DNS の L7 ルールをサポートしますが、`rules.kafka` はありません。かつての `role`、`topic`、`clientID` を用いたレシピは、現在デプロイ可能な API ではありません。ネットワークポリシーでブローカーへの接続性を制限した上で、`orders` と `events` に対する producer/consumer の権限は Kafka の認証と ACL で適用してください。クライアント ID は認証されたプリンシパルではありません。

この L4 の例は、TCP 9093 で TLS ブローカーリスナーが既に設定されていること、クライアントが同一 namespace にあること、クライアントの egress/DNS が別途認可されていることを前提としています。TLS、ブローカーの ACL、トピック権限の設定は行いません。

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

この例は Pod ベースの CoreDNS を使用します。ポート 53 の `ANY` は UDP と TCP の両方を対象とします。DNS クエリの許可と、返された IP への接続許可は別物です。以下でデータベース名を解決できることは、データベースへの接続を許可するものではありません。例のドメインは置き換え、DNS の検索サフィックス/キャッシュ/TTL を考慮し、実際のリゾルバーのプロファイルを確認してください。FQDN ルールは DNS から IP を学習するもので、SaaS のテナントを認証したり、TLS やアプリケーションの認可を代替するものではありません。

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

このリソースはクラスタースコープですが、そのセレクターによって明示的に `production/app=api` に限定されています。gateway の Pod に TCP 8080 を許可します。制御するのは ingress のみであり、egress の分離/DNS やゲートウェイ自身の egress にはそれぞれ対応するポリシーが必要です。以前の全エンドポイントに対する cluster/world の許可の例は、デフォルト拒否ポリシーではありませんでした。

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

### Cilium のエンティティベースポリシー

`host` にはローカルノードとその host ネットワークのコンテナが含まれ、`cluster` にはアプリケーション Pod 以外も含まれます。`world` はクラスター外のエンドポイントを対象とし、きめ細かなインターネット/SaaS の許可リストではありません。外部アクセスを狭める場合は、明示的な CIDR/FQDN ルールを使用してください。この例はラベル付けされた Kubernetes API クライアントに TCP 443 のアクセスのみを与えます。API エンドポイント、TLS の信頼、認証情報、RBAC は別途設定してください。マネージドコントロールプレーンのネットワーク経路をまたぐと送信元アイデンティティが変わり得るため、ingress をクラスター全体に広げるのではなく、実際のフローのアイデンティティを確認してください。

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

## Calico Network Policy の拡張 {#calico-network-policy-extensions}

ポリシー/Tier の例は Calico Open Source 3.32.2 のリソースに準拠しています。`projectcalico.org/v3` にはサポートされた Calico API server または対応する `calicoctl` のワークフローが必要で、Kubernetes の生の `crd.projectcalico.org/v1` ストレージ API ではありません。適用前にインストール済みのデータストア/API を確認してください。Calico の順序付きアクションと tier の委譲は、加算的な Kubernetes NetworkPolicy API とは異なります。

現行の Open Source ドキュメントには [Istio/Dikastes によるアプリケーション層の連携](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy) も記載されています。HTTPMatch API はその個別のセットアップを必要とし、ingress の Allow ルールをサポートします。以下の Calico の例は L3/L4 ポリシーを扱っており、本レビューでは L7 連携のデプロイやテストは行っていません。

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

これら 2 つのグローバルリソースは `production` namespace のワークロードのみを選択します。制約のない `selector: all()` は host endpoint にも影響し得るため、明示的なスコープと復旧手段なしにクラスター全体の拒否を適用しないでください。tier 内では `order` の値が小さいものが先に評価されます。この例は Pod ベースの DNS を許可し、それ以外は拒否ベースラインを提供します。レビュー済みのアプリケーションフローを追加し、上位 tier のアクションも考慮してください。

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

NetworkSet のセレクターはリソース名ではなく `metadata.labels` に一致します。1 つ目のセットは namespace スコープで、ブロック対象のセットはグローバルであり、後述のセキュリティ tier の例で使用されます。ここに登場する CIDR はすべてドキュメント用の範囲であり、レビュー済みの宛先に置き換える必要があります。egress の例は、ラベル付けされた namespace スコープのセットへの TCP 443 を許可します。DNS は別のルールです。

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

### Tier ベースのポリシー

Tier は参照している Calico Open Source リリースで利用可能であり、Enterprise 限定の機能ではありません。選択している tier でどのルールも作用しない場合、デフォルトは `Deny` になります。そのため deny-known-threats の tier では明示的に `defaultAction: Pass` を使用し、無関係なトラフィックが後続のポリシーに到達できるようにしています。`Pass` は委譲であり、許可ではありません。`global()` は `namespaceSelector` に記述するもので、GlobalNetworkSet を識別するのは別のラベルセレクターです。デプロイ前に application tier のポリシーを整備し、最終的な profile/default tier の挙動を確認してください。空の Tier を作成するだけでは、完全なアプリケーション分離ポリシーにはなりません。

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

これらは**代替となるポリシープロファイル**であり、まとめて適用するためのセットではありません。`production` を再利用しても無関係な例が互換になるわけではなく、それぞれの allow ルールが積み上がってしまいます。まず namespace、ワークロードのラベル、リッスンするポート、実際の DNS プロファイルを準備してください。これらの例はローカルでスキーマと意図を確認したのみで、クラスター上で実行してはいません。

### マイクロセグメンテーション

このプロファイルは frontend→API の TCP 8080 と API→database の TCP 5432 を双方向で許可し、加えて DNS を許可します。インターネットへの egress や外部からの frontend への ingress は意図的に含めていません。必要な場合は、承認済みの宛先 CIDR/ポート、または認証済みの egress ゲートウェイのプロファイルを追加してください。0.0.0.0/0 から RFC1918 を除外することは SaaS の許可リストにはなりません。

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

### Namespace の分離

このチーム向けプロファイルには、同一チーム内の ingress **と egress**、および DNS が含まれます。共有サービスについてはさらに、宛先側の ingress で team-a を許可することと、実際に TLS 443 でリッスンしていることが必要です。namespace ラベルの管理権限は制限してください。チームラベルは独立した信頼境界ではありません。

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

### データベースの保護

`database` namespace が存在している必要があります。production 側の呼び出し元と monitoring の Pod には、それぞれ独自の egress 許可が必要です。TCP 5432 のピアルールは、想定される PostgreSQL のレプリケーショントランスポートのみを許可します。データベースの認証/TLS は別途設定してください。TCP 9187 は別途インストールされた exporter を前提としています。

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

### 3 層アーキテクチャのポリシー

クライアントの TLS を終端し、web Pod へ TCP 80 で到達し得る `gateway-system/app=edge-proxy` のワークロードが既に存在することを前提とします。ゲートウェイの egress ポリシーはこの namespace の対象外です。data 層のピア間 ingress と egress は TCP 5432/6379 を使用します。レプリケーション、クラスターバス、バックアップ用の追加ポートは選択するデータベースに依存し、ここでは含意されていません。実際のデプロイでは PostgreSQL と Redis のセレクターを分けてください。

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

## Network Policy のテスト {#testing-network-policies}

### netshoot を使ったテスト

承認済みで既にプロビジョニングされた診断用 Pod を、固定されたイメージとレビュー済みの権限で使用してください。ポリシーを実際に検証できる送信元のラベル/namespace/ノード配置を選択してください。ラベルのない汎用的な Pod はアプリケーションを代表しません。netshoot をプロビジョニングするとワークロードが作成され、Pod Security admission と競合する可能性があります。観測用スクリプトの一部として、固定された共有名 `test-pod` を作成/削除しないでください。プローブは自分が所有するテストエンドポイントに対してのみ実行してください。

### kubectl exec を使ったテスト

コンテキスト、namespace、既存の Pod、コンテナを明示的に指定してください。DNS の成功は TCP の成功ではありません。接続拒否、リスナーの異常、TLS エラー、ポリシーによるドロップはそれぞれ異なる結果です。以下のコマンドは接続性のみをテストし、レスポンス本文は出力しません。本レビューではクラスターに対して実行していません。

```bash
# Both Pods already exist in the approved test environment.
kubectl --context="$CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- nslookup api-service.production.svc.cluster.local
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- curl --silent --show-error --output /dev/null \
  --connect-timeout 3 --max-time 5 http://api-service.production.svc.cluster.local:8080/health
```

### Cilium 接続性テスト

`cilium connectivity test` はテスト用リソースとトラフィックを作成するもので、読み取り専用のステータスコマンドではありません。承認済みの隔離されたクラスター/namespace、互換性のある CLI とイメージ、定義済みの外部宛先、そしてクリーンアップ計画を用意してください。過去のテスト名が今も存在すると想定せず、インストール済み CLI のフィルターは `cilium connectivity test --help` で確認してください。スイートが成功しても、すべてのアプリケーションポリシーや CNI チェイニング機能が証明されるわけではありません。

### 自動テストスクリプト

このスクリプトは既存の 2 つの Pod で範囲を限定した curl プローブを実行するだけで、クラスターリソースの作成や削除は行いません。`CONTEXT`、`NAMESPACE`、`ALLOW_POD`、`DENIED_POD`、`PROBE_CONTAINER`、および `/health` で終わる非機密の `TARGET_URL` を設定してください。両方のコンテナに `sh` と `curl` が必要です。1 つ目の Pod は同じ宛先に対する既知の許可済みポジティブコントロールです。HTTP のエラーレスポンスであってもネットワーク到達性は成立するため、このテストはアプリケーションのヘルス検証ではありません。

終了コード 1 はブロック対象の被験 Pod が予期せず接続できたことを意味し、終了コード 2 は不明/エラー、終了コード 3 は裏付けが必要なタイムアウトを意味します。タイムアウトが自動的に PASS になることは**決してありません**。正確な送信元/宛先/ポート/時刻を CNI のポリシードロップ判定と突き合わせ、同時にエンドポイントの健全性、ルート、SG/NACL の制御も確認してください。ローカルのモックテストによって実環境での適用が証明されるわけではありません。

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

## EKS における考慮事項 {#eks-considerations}

### Amazon VPC CNI と NetworkPolicy

Amazon VPC CNI は有効化後にネットワークポリシーをサポートします。現行の AWS ガイドでは、標準ポリシーと管理ポリシーの両方について VPC CNI 1.21 以降、互換性のある EKS プラットフォーム、および Linux カーネル 5.10 以降が必要です。適用対象はサポートされる EC2 Linux ノードであり、Fargate や Windows は対象外です。現在サポートされている EKS バージョンを使用し、その互換 add-on リリースを確認してください。upstream の Kubernetes リリースから EKS のサポート状況を推測しないでください。

**EKS マネージド**の VPC CNI add-on の場合は、既存の設定を保持したうえで、ドキュメントに記載された文字列 `"enableNetworkPolicy": "true"` を設定してください。以下はレビュー後に選択したクラスターを変更するものであり、add-on のバージョンをアップグレードするものではありません。インストール済みバージョンが非互換の場合は中止し、まずドキュメントに記載されたアップグレード手順に従ってください。

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

ロールアウト前に更新ステータスとポリシーの挙動を確認してください。`--resolve-conflicts PRESERVE` は置き換え用の JSON ドキュメントをマージしてくれるわけではないため、この例では既存の値を明示的に引き継いでいます。復旧のためにスナップショットを保管してください。Helm が管理するインストールでは、レビュー済みのチャート/values と `enableNetworkPolicy: true` を使用し、このマネージド add-on コマンドで所有権を奪わないでください。存在しない `ENABLE_NETWORK_POLICY` 環境変数を設定することは、有効化の手順ではありません。

標準の起動モードでは、ポリシーがプログラムされるまで新しい Pod が一時的に許可される場合があります。`NETWORK_POLICY_ENFORCING_MODE=strict` は対象となる Pod を拒否状態で起動させ、DNS を含む完全な許可マトリクスを必要とします。この設定変更はワークロードを中断させる可能性があります。信頼できるテスト対象はコントローラー管理下の Pod です。適用は Pod のプライマリインターフェースに対して行われるため、追加のインターフェース、IPv6 から IPv4 への egress、host ネットワーキング、NAT は個別に確認してください。同じ標準ポリシーを管理するエンジンを 2 つインストールしたり、移行の近道として `aws-node` を削除したりしないでください。

### EKS 拡張ネットワークセキュリティポリシー (2025 年 12 月)

> **発表**: December 15, 2025 · [出典](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

この機能は実在しますが、そのリソースは **`networking.k8s.aws/v1alpha1`** を使用します。`ClusterNetworkPolicy` はクラスタースコープで `tier` が必須です。以下の namespace の例では、DNS ベースの egress に `ApplicationNetworkPolicy` を使用します。EC2 Linux 上で VPC CNI の標準/管理ポリシーがサポートされていることは、すべてのコンピュートモードがサポートすることを意味しません。DNS ルールは、混在クラスターの場合も含め、**Auto Mode で起動された EC2 インスタンス**でのみ適用されます。

この Admin tier の例は、namespace で選択された Pod から `isolated-demo` への受信トラフィックを、その同一 namespace 内の Pod も含めて拒否します。これは完全な外部/host ネットワークのファイアウォールでも、DNS の許可ポリシーでもありません。Admin の Deny は namespace の NetworkPolicy で上書きできません。他のアクションを追加する前に、実際にインストールされている CRD を確認してください。現行の upstream AWS コントローラーのスキーマでは許可アクションの名称は `Accept` ですが、ユーザーガイドの本文では「Allow」と記載されています。

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

FQDN の例は `production` の `app=backend` を選択します。**`10.100.0.10/32` はクラスターの実際の Auto Mode CoreDNS の IP に置き換えてください**。これは Service CIDR のネットワークアドレスに 10 を加えたもの (IPv6 では `::a/128`) です。純粋な Auto Mode の CoreDNS はノード上で動作するため、従来の CoreDNS Pod セレクターとは互換ではありません。DNS は TCP と UDP の両方を許可してください。その namespace の NetworkPolicy と衝突しない一意のリソース名を使用してください。

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

DNS プロキシは許可された応答とその TTL を観測し、その後データパスが学習した宛先 IP/ポートを許可します。これは SaaS アカウントを認証したり、ピアの HTTP アイデンティティを証明するものではありません。共有 IP や DNS の挙動についてはテストが必要です。TLS 証明書の検証、アプリケーションの認可、ルート、および Route 53 DNS Firewall のルールは依然として関係します。適用される他のポリシーやバックエンドへの直接経路も併せて確認する必要があります。

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [設定](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Auto Mode のポリシー](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Security Groups for Pods

このバインディングの例は、EKS VPC Resource Controller、その **cluster-role** 権限、トランキングに対応したサポート対象の EC2 Linux ノード、およびレビュー済みの VPC CNI 設定を前提としています。現行の AWS ガイドでは Windows と EKS Auto Mode は対象外です。Fargate は別の Pod 用 SG モデルを使用し、security group を持つだけで VPC CNI の NetworkPolicy サポートが得られるわけではありません。バインディングは、オーナー経由で新しく作成される該当ワークロードの Pod に適用されます。既存の Pod に自動で後付けされることはありません。

Calico と Pod 用 SG を併用する場合、AWS は VPC CNI 1.11.0 以降と `POD_SECURITY_GROUP_ENFORCING_MODE=standard` を文書化しています。その最小要件を推奨バージョンと見なさず、現行の CNI 要件も併せて確認してください。standard モードの外部 SNAT では、Pod の SG ではなくノードの SG が使用される場合があります。実際の経路を確認してください。以前の素の PostgreSQL Pod は認証情報とストレージを欠いており、機能するデータベースのデプロイではありませんでした。

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

この Terraform の断片は、レビュー済みのアプリケーション SG 1 つからの DB への ingress を許可し、新たな egress 接続を開始しません。ステートフルな戻りトラフィックは SG のトラッキングによって許可されます。必要な DNS、レプリケーション、バックアップ、外部への egress のみを別途追加してください。変数は既存の運用者による入力であり、Terraform の plan/apply は実行していません。

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

NetworkPolicy、実際に適用されている SG、および NACL のすべてが該当経路を許可している必要があります。この ingress のみの NetworkPolicy はデータベースの egress を制限しないため、選択した egress プロファイルと送信元 Pod の egress を追加してください。複数の SG はそれぞれの許可が結合されます。NACL は**ステートレス**であるため、サブネットで受信 5432 を許可するルールには、クライアントのエフェメラルポートへ戻る経路のルールと、クライアント側サブネットの適切なルールが必要です。以下の断片は、完全にレビューされた ACL ルールセットの代替にはなりません。

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

### EKS で Cilium を使用する

**AWS VPC CNI チェイニング**か、別途設計した完全な CNI/IPAM 移行のいずれかを選択してください。チェイニングモードでは AWS VPC CNI が ENI/IPAM の責務を保持し、Cilium が自身のデータパスを接続します。`aws-node` は保持してください。削除はインストールの近道ではありません。既存の add-on/Helm の所有者を確認し、ポリシー適用エンジンが重複しないようにしてください。チェイニングのポリシーが適用されるには既存 Pod の制御された再作成が必要であるため、影響とロールバックを計画してください。

公式の 1.20.1 チェイニングガイドはこれらの values を提示していますが、L7/IPsec の制限も文書化しています。ガイドには古い説明用の出力が含まれており、それは現在の EKS 環境の検証結果ではありません。チャートのリポジトリ/パッケージを準備し、出自を検証してから、まずレンダリングしてください。

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

ポリシーエディターはポリシーの作成を支援し、**Hubble UI は観測されたサービスフローを可視化**します。これらは異なるツールです。Hubble/UI を有効化するとクラスターの設定が変わるため、これはインストールの所有者の責務です。既にインストールされ認証済みの Hubble サービスがある場合は、既存の Service を確認してローカルの port-forward を使用してください。デバッグの近道として UI を公開しないでください。

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Cilium のポリシー判定の確認

認証済みの Hubble 接続を使用してください。`DROPPED` にはポリシー以外の理由も含まれるため、ドロップ理由、エンドポイントのアイデンティティ、時刻、方向を確認してください。ある地点での `FORWARDED` の観測は、エンドツーエンドの配送を保証するものではありません。


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

Enterprise の管理 UI にはライセンス製品と、その実際の Service/TLS/認証の設定が必要であり、Calico Open Source によって自動的にインストールされるものではありません。port-forward の前に、インストール済みの Service 名/ポートとアクセスポリシーを確認してください。`cnx-manager` がすべてのインストールに存在すると想定しないでください。

### Network Policy の可視化ツール

Kubernetes ポリシーのセレクター/ルールの確認には `kubectl get networkpolicy -n <namespace>` と `kubectl describe networkpolicy <name> -n <namespace>` を使用し、適用状況の確認にはインストール済みエンジンの認証済みフローツールを使用してください。サードパーティのビューアー/プラグインの提供状況やフラグは、そのプロジェクトの現行リリースで確認する必要があります。YAML のグラフだけではデータプレーンでの適用を証明できません。

### Kube-hunter によるセキュリティテスト

kube-hunter はクラスターの露出/セキュリティスキャナーであり、NetworkPolicy の許可/拒否の検証ツールではありません。そのスキャンは侵襲的なトラフィックを生成し得るため、明示的に承認された対象/スコープと、レビュー済みのリリース/イメージを使用してください。一般的なポリシーチュートリアルを見て、バージョン固定していないスキャナーを稼働中の namespace にデプロイしないでください。本レビューではスキャナーを実行していません。

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

必要なトラフィックのみを明示的に許可します:

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

この読み取り専用のインベントリは、namespace 全体を対象とする空の allow ベースラインを ingress と egress で別々に列挙します。空の `[]` とルール配列の欠如は扱えますが、ルール `{}` はトラフィックを許可するものであり、拒否ベースラインではありません。API/認可のエラーはゼロ件のポリシーとして表示されるのではなく、失敗として扱われます。列挙されたベースラインは**分離の証明にはなりません**。他の allow ルール、拡張ポリシー、対象外の Pod、CNI の状態については依然として確認が必要です。

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

Kubernetes Network Policy は、クラスター内の Pod 間通信を制御する中核的なセキュリティメカニズムです:

1. **基本的な NetworkPolicy**: namespace スコープで、podSelector/namespaceSelector/ipBlock をサポート
2. **Cilium の拡張**: L7 ポリシー、DNS FQDN ベースのポリシー、クラスター全体のポリシー
3. **Calico の拡張**: GlobalNetworkPolicy、NetworkSet、Tier ベースのポリシー
4. **EKS における考慮事項**: VPC CNI NetworkPolicy の有効化、Security Groups for Pods、ClusterNetworkPolicy と DNS (FQDN) ベースの egress 制御

### 推奨事項

- すべての production namespace にデフォルト拒否ポリシーを適用する
- 最小権限の原則に従い、必要なトラフィックのみを許可する
- 定期的なポリシー監査とテストを実施する
- L7 ポリシーが必要な場合は Cilium を検討する

---

## 参考資料

- [Kubernetes Network Policies Official Documentation](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Cilium Network Policy Documentation](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Calico Network Policy Documentation](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [EKS Security Best Practices - Network Security](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Amazon EKS Enhanced Network Security Policies (2025-12-15)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [EKS Pod security groups](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Calico Tier](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [Calico NetworkSet](https://docs.tigera.io/calico/latest/reference/resources/networkset)
