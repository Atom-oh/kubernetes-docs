# Part 5: ネットワークポリシー

> **レビュー基準**: Calico 3.32.2。Kubernetes 1.34～1.36 は Calico 3.32 のテスト済み範囲です。**最終更新日**: 2026年9月12日。
>
> 例は、標準の Calico API サーバー（`projectcalico.org/v3`）、Kubernetes datastore、およびポリシーを適用できる互換データプレーンを前提とします。既知のワークロードラベル、Ready なエンドポイント、正常な基準状態を備えた専用の `calico-demo` namespace を使用してください。各節は独立したパターンであり、1つのマニフェスト一式としてまとめて適用するものではありません。既存の優先度の高いポリシー、DNS の実装、Service NAT、ホストポリシー、アプリケーションの動作によって結果が変わります。このレビューでは、本番クラスター、admission サーバー、パケット転送をテストしていません。

## はじめに

NetworkPolicy は、ワークロードとほかのエンドポイントとの間で許可する接続を制御します。Calico は標準 Kubernetes API に、順序付きポリシー、明示的なアクション、グローバルスコープ、ホストエンドポイント制御を追加します。機能を利用できるかどうかは製品と適用経路によって異なります。DNS ドメインポリシーは商用版の拡張機能であり、Open Source の HTTP ポリシーにはドキュメントに記載された Istio/Dikastes 統合が必要です。

この詳細ガイドでは、Kubernetes 標準ポリシーと Calico の拡張機能の両方を取り上げ、エンタープライズのセキュリティ要件に対応するパターンと例を示します。

***

## Kubernetes 標準 NetworkPolicy

### NetworkPolicy の基本

Kubernetes NetworkPolicy は namespace スコープのリソースで、Pod を選択します。Ingress と egress の分離はそれぞれ独立しており、分離された方向で許可される通信は、該当する Kubernetes ポリシーの許可ルールの和集合です。両端が分離されている場合、新しい接続には送信元の egress と宛先の ingress の両方で許可が必要です。許可済み接続への応答に、逆方向の許可ルールを別途作成する必要はありません。

`from` / `to` リストの各項目は **OR** 条件です。同じ項目内の `namespaceSelector` と `podSelector` は **AND** 条件です。namespace セレクターを伴わない Pod セレクターは、そのポリシーが属する namespace を対象にします。

該当する Kubernetes ポリシーがない場合、その方向はこの API によって分離されません。ただし、ホストファイアウォール、Calico ポリシー、その他の制御を無効にするわけではありません。ポリシー変更が既存接続に与える影響は実装に依存するため、新しい接続で検証してください。Service やロードバランサーの NAT の前後で観測される `ipBlock` のアドレスも実装によって異なります。

![NetworkPolicy がない場合はすべての Pod が相互に自由に到達できる一方、NetworkPolicy によって許可する経路を1つに限定し、それ以外を遮断する比較図。](../../.gitbook/assets/en-networking-calico-05-network-policy-0.png)

[🔍 インタラクティブ図を表示](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-05-network-policy-0.html)

> 矢印は図示したポリシーにおける新しい接続を表し、許可済み接続への応答パケットは表しません。この例では、ほかのポリシー、ファイアウォール、経路上の制限がないものとします。NetworkPolicy が1つ存在するだけで、すべての Pod や方向が分離されるわけではありません。

### NetworkPolicy の基本構造

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: calico-demo
spec:
  # Which pods this policy applies to
  podSelector:
    matchLabels:
      app: web

  # Policy types: Ingress, Egress, or both
  policyTypes:
    - Ingress
    - Egress

  # Ingress rules (who can connect TO these pods)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
        - namespaceSelector:
            matchLabels:
              purpose: monitoring
        - ipBlock:
            cidr: 10.0.0.0/8
            except:
              - 10.0.1.0/24
      ports:
        - protocol: TCP
          port: 8080

  # Egress rules (where these pods can connect TO)
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: database
      ports:
        - protocol: TCP
          port: 5432
```

### Kubernetes NetworkPolicy の制約

| 機能 | Kubernetes NetworkPolicy | Calico の拡張機能 / 前提条件 |
| --- | --- | --- |
| スコープ | namespace 内の Pod に適用するポリシー | GlobalNetworkPolicy は複数 namespace のワークロードと HostEndpoint を選択可能 |
| 順序 / アクション | 許可ルールは加算式。ユーザー定義のポリシー順序はない | Tier / order と Allow、Deny、Log、Pass |
| ポート | TCP / UDP / SCTP、名前付きポート、`endPort` による数値範囲（1.25 で Stable。プラグインの対応が必要） | Calico のポート範囲構文、追加の IP プロトコル / ICMP 条件 |
| HTTP メソッド / パス | この API の対象外 | Open Source の `http` ルールには Istio/Dikastes を構成したアプリケーション層の適用が必要 |
| DNS ドメイン名 | この API の対象外 | 例: Calico Enterprise のドメインポリシー機能。`domains` は Open Source 3.32 の CRD に存在しない |
| ホストインターフェイス | 汎用ノードファイアウォールではない | HostEndpoint ポリシーで local / forwarded / failsafe を個別に扱う |

標準 NetworkPolicy オブジェクトのスコープと、新しい Kubernetes のクラスター向けポリシー API のスコープは別のものです。Kubernetes のネットワークセキュリティ API がすべて namespace 単位だと決めつけないでください。スキーマが受け付けることと実際に適用されることを同一視せず、選択したデータプレーンのプロトコルおよびログ機能の対応状況を確認してください。

***

## Calico NetworkPolicy の拡張機能

### 拡張プロトコルのサポート

SCTP の例には、互換性のある classic データプレーンが必要です。Calico 3.32 の eBPF は、SCTP ポリシーにも SCTP Service にも対応していません。

Calico は TCP と UDP 以外のプロトコルもサポートします。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: extended-protocols
  namespace: calico-demo
spec:
  selector: app == 'network-tools'

  ingress:
    # ICMP ping
    - action: Allow
      protocol: ICMP
      icmp:
        type: 8  # Echo Request
        code: 0

    # ICMPv6
    - action: Allow
      protocol: ICMPv6
      icmp:
        type: 128  # Echo Request

    # SCTP
    - action: Allow
      protocol: SCTP
      destination:
        ports:
          - 3868  # Diameter

    # UDP with port range
    - action: Allow
      protocol: UDP
      destination:
        ports:
          - "5000:6000"  # Port range
```

### ポート範囲と名前付きポート

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: port-examples
  namespace: calico-demo
spec:
  selector: app == 'multi-port-app'

  ingress:
    # Port range
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - "8080:8090"

    # Named ports (from pod spec)
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - http      # References containerPort name
          - metrics   # References containerPort name

    # Mix of specific ports and ranges
    - action: Allow
      protocol: TCP
      destination:
        ports:
          - 22
          - 80
          - 443
          - "3000:3100"
```

### 拡張セレクター構文

Calico は式形式のセレクターを使用します。以下のルールは選択肢を示しています。広範な Allow を1つのポリシーにまとめると、許可範囲が広がります。`app != 'untrusted'` は、そのラベルがないリソースにも一致します。これは信頼できることを意味しません。

`selector: !has(x)` は、対象範囲内でそのラベルを持たないリソースに一致します。`notSelector: has(x)` はパケット照合条件を否定するため、セレクターに含まれない外部アドレスにも一致する場合があります。ルールの `selector: all()` はすべてのパケットに一致するわけではありません。すべてのパケットを対象にするには、エンドポイントセレクター条件を省略します。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: selector-examples
  namespace: calico-demo
spec:
  # Label equality
  selector: app == 'web'

  ingress:
    # Set membership
    - action: Allow
      source:
        selector: app in {'frontend', 'api-gateway', 'monitoring'}

    # Negation
    - action: Allow
      source:
        selector: app != 'untrusted'

    # Label existence
    - action: Allow
      source:
        selector: has(security-cleared)

    # Combining conditions (AND)
    - action: Allow
      source:
        selector: app == 'backend' && tier == 'internal'

    # OR inside one selector expression
    - action: Allow
      source:
        selector: (app == 'frontend') || (app == 'api')

    # Namespace selector
    - action: Allow
      source:
        namespaceSelector: environment == 'production'
        selector: app == 'authorized-client'
```

***

## GlobalNetworkPolicy

GlobalNetworkPolicy は namespace に属さず、namespace をまたぐワークロードエンドポイントや HostEndpoint を選択できます。`selector: all()` だけでは「すべてのアプリケーション Pod のみ」を意味しません。以下の例では、システムおよびホストの通信を維持するため、対象ワークロードをデモ用 namespace に明示的に限定します。

### 明示的な例外を設けたデフォルト拒否

空のポリシーは両方向を選択します。`order` を省略すると、明示的に順序を指定したポリシーの後に配置されます。10,000 は「最も低い優先度」を表す特別な値ではありません。空のルールが先行する終端 Allow を上書きすることもありません。アプリケーションポリシーで覆せない制限が必要な場合は、別途管理する、より前の Tier を使用してください。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-default-deny
spec:
  tier: default
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-essential-egress
spec:
  tier: default
  order: 100
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: needs-platform == 'true'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      destination:
        services:
          name: kubernetes
          namespace: default
```

この例は `needs-platform=true` のラベルを持つワークロードに限り、プラットフォーム向け egress を許可します。Service 条件は **Kubernetes datastore** 上の実際の `kubernetes/default` エンドポイントとポートに従い、etcd datastore では無視されます。この Service 条件を宛先ポート、CIDR、セレクターと組み合わせないでください。API へのネットワークアクセスと API 認証 / RBAC は別の制御です。

実際の DNS 構成を確認してください。namespace セレクターと Pod セレクターを併用することで、`kube-dns` とラベル付けされた無関係な Pod が信頼するリゾルバーになるのを防ぎます。Node-local DNS を使う場合は、実際の経路に合う別の条件が必要です。システム依存関係を洗い出す前に `kube-system` に空のポリシーを作ると、クラスターが停止することがあります。このパターンを試す場合は、別のテスト namespace を使ってください。

### より前段の egress ガードレール

この独立した例では、選択したデモワークロードの IPv4 メタデータアドレスをブロックし、Tier の最後にほかの通信を次段へ委ねます。完全な SSRF 対策、特権プロセス / host-network プロセスの保護、あらゆるプラットフォームメタデータエンドポイントへの対応を主張するものではありません。

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: egress-guardrail
spec:
  order: 50
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: egress-guardrail.block-imds-v4
spec:
  tier: egress-guardrail
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Deny
      destination:
        nets: [169.254.169.254/32]
```

同じ Tier 内の後続制限より前に無条件の Pass を置かないでください。プラットフォームで必要な ID / DNS 経路を維持し、実際のワークロードからホストへの適用動作を確認してください。

***

## NetworkSet と GlobalNetworkSet

NetworkSet は再利用可能な IP / CIDR グループにラベルを付けるオブジェクトで、ポリシーセレクターはオブジェクト名ではなくラベルを参照します。以下のアドレス例は説明用であり、実在する国別フィードや脅威フィードではありません。ラベルセレクターは同じラベルを持つエンドポイントにも一致する可能性があるため、管理されたラベルと意図した namespace / global スコープを使用してください。

namespaced ポリシーの entity 条件で GlobalNetworkSet を選択するには、`namespaceSelector: global()` を使います。namespace 内の NetworkSet は、選択された namespace の範囲にとどまります。信頼する範囲とブロックする範囲が重なる場合は、先に Deny を評価してください。先行する Allow は終端アクションです。

### NetworkSet（namespace スコープ）

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: corporate-networks
  namespace: calico-demo
  labels:
    network-type: corporate
spec:
  nets:
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16

---
# Reference in policy
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-corporate
  namespace: calico-demo
spec:
  selector: app == 'internal-app'

  ingress:
    - action: Allow
      source:
        selector: network-type == 'corporate'  # References NetworkSet by label
```

### GlobalNetworkSet（クラスター スコープ）

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: external-trusted-ips
  labels:
    network-group: external-trusted
spec:
  nets:
    - 203.0.113.0/24     # Partner network
    - 198.51.100.0/24    # CDN network
    - 192.0.2.50/32      # Specific trusted IP

---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: demo-blocked-networks
  labels:
    network-group: blocked
spec:
  nets:
    # Illustrative test ranges, not geolocation or threat intelligence
    - 192.0.2.128/25
    - 203.0.113.128/25

---
# Reference in GlobalNetworkPolicy
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: external-access-control
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: has(external-facing)
  order: 200
  types:
    - Ingress

  ingress:
    # Deny overlaps before considering trusted ranges.
    - action: Deny
      source:
        namespaceSelector: global()
        selector: network-group == 'blocked'
    - action: Allow
      source:
        namespaceSelector: global()
        selector: network-group == 'external-trusted'
```

***

## Tier 化ポリシー

Tier は Calico Open Source 3.32 で利用できます。namespace 内の Calico ポリシーとグローバル Calico ポリシーをグループ化します。Kubernetes NetworkPolicy から GlobalNetworkPolicy へ進む段階を表すものではありません。

### 評価順序とデフォルト

通常のエンドポイントポリシーは、Tier を `order` の昇順で評価し、各 Tier 内のポリシーも `order` の昇順で評価します。ポリシーの order が未設定なら、明示的に順序を指定したポリシーの後に配置されます。選択されたエンドポイント**と通信方向**の両方を考慮してください。

| 状況 | 結果 |
| --- | --- |
| その Tier に該当エンドポイント / 方向を選択するポリシーがない | Tier をスキップ |
| ルールが Allow または Deny を返す | そのエンドポイント / 方向に対するポリシー判定を終了 |
| ルールが Log を返す | 次のルールへ進む |
| ルールが Pass を返す | この Tier の残りのポリシーを飛ばし、次に該当する Tier を評価 |
| 該当 Tier 内で終端ルールに一致しない | `defaultAction` を適用。既定値は Deny |
| 最後に該当した Tier が Pass を返す | エンドポイント Profile を評価。Profile に許可がなければ Deny |

「どのルールにも一致しなければ常に次の Tier へ進む」という動作ではありません。一方のエンドポイントでの Allow が、もう一方のエンドポイントに適用されるポリシーを迂回することもありません。Pre-DNAT および untracked のホストポリシーには異なるフォールスルー動作があり、後の節で説明します。

組み込み `default` Tier の order は固定値 **1,000,000** であり、1,000 や無限大ではありません。明示的な Tier を指定していない Kubernetes NetworkPolicy と Calico ポリシーは、この Tier に属します。現在の `kube-admin` と `kube-baseline` Tier は、それぞれ Kubernetes のクラスター向けポリシー統合で Pass を既定動作とする 1,000 と 10,000,000 を使用します。そのため、`default` が常に最後の Tier とは限りません。

### セキュリティ、プラットフォーム、アプリケーションの判定を分離する

以下の例では、セキュリティ / プラットフォーム Tier の最後に Pass を置き、その Tier に該当するルールをすべて評価してから次に委ねます。Tier の作成や順序変更には、中央で管理された権限が必要です。

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
  order: 500
  defaultAction: Deny
```

次の例では、ドキュメント専用の脅威アドレスを使い、その後に制限データ向けの別ルールを適用します。最初のセキュリティポリシーの末尾に Pass を置くと、2つ目のポリシーが評価されません。委譲を **Tier の最後**に置くことで、この迂回を防ぎます。制限データ用ラベルはセグメンテーションの例であり、PCI DSS への完全な準拠を示すものではありません。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: demo-threats
  labels:
    network-group: demo-threat
spec:
  nets:
    - 192.0.2.100/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-threats
spec:
  tier: security
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Ingress, Egress]
  ingress:
    - action: Deny
      source:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
  egress:
    - action: Deny
      destination:
        namespaceSelector: global()
        selector: network-group == 'demo-threat'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.restricted-data
spec:
  tier: security
  order: 20
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: data-scope == 'restricted'
  types: [Ingress]
  ingress:
    - action: Deny
      source:
        notSelector: data-scope == 'restricted'
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.dns
spec:
  tier: platform
  order: 10
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: application.frontend
  namespace: calico-demo
spec:
  tier: application
  order: 10
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

`namespaceSelector: global()` と別のラベルセレクターを組み合わせると、GlobalNetworkSet を選択できます。`global(label == 'value')` は有効な構文ではありません。プラットフォーム DNS の Allow は、選択したワークロードの egress に対する意図的な終端例外です。そのため、後続のアプリケーション Tier でこの例外をさらに制限することはできません。アプリケーションポリシーが対象にするのは選択された frontend のみで、namespace 内の全ワークロードではありません。

DNS 例は、namespace とラベルを確認済みの一般的な CoreDNS Pod を前提とします。NodeLocal DNSCache や EKS Auto Mode のノードローカル DNS には、そのリゾルバー経路に合うルールが必要です。Pod セレクターをそのまま流用しないでください。必要なリゾルバーへのアクセスを維持し、UDP と TCP の両方の問い合わせを検証してください。

### Tier RBAC の統合

Calico Tier の RBAC では、擬似リソース `tier.networkpolicies` と `tier.globalnetworkpolicies` に加え、対象 Tier に対する `get` が必要です。Calico authorizer は `application.*` のような合成名を明示的に確認します。これは通常の `networkpolicies` に対する Kubernetes `resourceNames` の汎用ワイルドカードではありません。

以下の完全な RoleBinding 例は、1つの ServiceAccount に application Tier 内の namespace ポリシー編集を許可します。Tier の作成 / 並べ替えやグローバルポリシーの管理権限は付与しません。

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: policy-editor
  namespace: calico-demo
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: demo-get-application-tier
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tiers"]
    resourceNames: ["application"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: demo-get-application-tier
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: demo-get-application-tier
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
rules:
  - apiGroups: ["projectcalico.org"]
    resources: ["tier.networkpolicies"]
    resourceNames: ["application.*"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: demo-edit-application-policies
  namespace: calico-demo
subjects:
  - kind: ServiceAccount
    name: policy-editor
    namespace: calico-demo
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: demo-edit-application-policies
```

グローバルポリシーを編集するには、意図した範囲に限定した ClusterRole / ClusterRoleBinding で `tier.globalnetworkpolicies` を使います。対象 Tier の `get` 権限と、Tier 順序の変更権限は分けてください。

この例は標準の Calico aggregated API server を前提にしています。native v3 CRD では、Tier の認可に admission webhook を使って create / update / delete を制御しますが、その webhook は GET / LIST / WATCH を制限できません。2つの方式で読み取りアクセスも同じように分離できるとは主張しないでください。`kubectl auth can-i` だけでは、Calico Tier の複合チェックを検証できません。より広いバインディングを持たない principal を使い、隔離した環境で実際の許可 / 拒否リクエストをテストしてください。Kubernetes RBAC は加算式なので、既存の広範な許可によって意図した制限が無効になることがあります。

***

## FQDN ベースの egress ポリシー

Open Source 3.32 の CRD には `destination.domains` も Felix の `dnsTrustedServers` フィールドもありません。`policySyncPathPrefix` を設定するとアプリケーション層統合向けの policy-sync 経路は有効になりますが、Open Source に DNS ドメインポリシーが追加されるわけではありません。

Calico Enterprise 3.23 では、egress Allow ルールで DNS ドメイン条件を使う方法が記載されています。コントローラーは信頼する DNS サーバーから A / AAAA / CNAME の応答を学習し、一致する宛先 IP を許可します。これは IP ベースの適用であり、HTTPS のホスト名認証ではありません。宛先 IP を共有するサービスやアプリケーション ID も引き続き考慮してください。クラスター内サービスにはワークロード / Service セレクターを使います。

次の商用版の例は、この機能が有効で、信頼するリゾルバーを検証済みであり、前段の終端 Allow による迂回がないことを前提とします。各ルールには `destination` マップを1つだけ記述してください。同じ YAML キーを繰り返すと、ドメイン制約が黙って破棄されるおそれがあります。

```yaml
# Calico Enterprise 3.23 example; NOT an Open Source 3.32 resource.
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-approved-domains
  namespace: calico-demo
spec:
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        domains:
          - api.github.com
          - "*.example.com"
        ports: [443]
```

ドキュメント用ドメインは、承認済みの実ドメインに置き換えてください。`*.example.com` は `api.example.com` と `deep.api.example.com` に一致しますが、apex ドメインの `example.com` には一致しません。ワイルドカードはドメインの構成要素全体に指定し、1つだけ使用できます。inline DNS ポリシーモードが対応するのは prefix wildcard です。prefix 以外の wildcard パターンには、適切なドキュメント記載のモードが必要です。`*.amazonaws.com` のような広いサフィックスは、AWS アカウントや IAM の境界を表しません。

実際のリゾルバーに UDP / TCP の両方で到達できるようにし、その IP を信頼する DNS の設定と一致させてください。ノードローカルリゾルバーには、デプロイ固有の設定が必要です。商用版ガイドでは、egress-gateway Pod の egress hook でドメインポリシーを使わないよう案内されています。ノード全体の DNS キャッシュにより、ドメインの一致が欠落したり不安定になったりする可能性があるためです。

Open Source では、独自のアプリケーション認可を備えた明示的な egress proxy / gateway を使うか、適切なサービスアドレス契約がある場合に保守された IP / CIDR NetworkSet を使用してください。一度だけの DNS lookup を、継続的に適用されるドメインポリシーの代わりにしないでください。

***

## HTTP メソッドによるフィルタリング（Layer 7）

Calico Open Source 3.32 は、ドキュメントに記載された **Istio + Dikastes** 統合を通じて HTTP ポリシーをサポートします。任意の Envoy proxy をインストールしたり、通常の CNI ポリシーに `http` フィールドを加えたりするだけでは、Layer 7 の適用は有効になりません。

前提条件には、Felix Policy Sync API、Calico CSI socket の mount、Dikastes の injection、対象通信経路での Envoy external authorization が含まれます。現行の統合ガイドは Kubernetes native-sidecar を使った Istio injection を説明し、Istio 1.28.1 を推奨しています。これは、より新しいすべての Istio バージョンに対する包括的な互換性保証ではありません。本番構成を選ぶ前に、保守中の [Istio インストールガイド](../../service-mesh/istio/01-installation.md)、両プロジェクトのサポート期間、実際の統合方法を確認してください。このレビューでは、その統合をデプロイしていません。

以下は、すでに統合済みのワークロードに対する **ingress Allow** の例です。HTTPS のメソッド / パスを検査するには、TLS 終端後の HTTP リクエストを適用 proxy が認識できる必要があります。送信元 Pod ラベルはワークロードを識別するもので、認証済みのエンドユーザーを識別するものではありません。統合で信頼するワークロード ID / mTLS の経路を構成し、DNS と Istio control plane に必要なネットワークアクセスも確保してください。ポリシーに依存する前に、許可 / 拒否されるリクエストと proxy / authorization service 障害時の動作を検証してください。

### HTTP 条件ルール

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: l7-http-policy
spec:
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'api-server'
  order: 300
  types:
    - Ingress

  ingress:
    # Allow only GET and HEAD for read-only clients
    - action: Allow
      source:
        selector: role == 'reader'
      http:
        methods:
          - GET
          - HEAD
        paths:
          - prefix: /api/v1/

    # Allow the listed methods for admin-labeled workloads
    - action: Allow
      source:
        selector: role == 'admin'
      http:
        methods:
          - GET
          - POST
          - PUT
          - DELETE
          - PATCH

    # Allow health checks
    - action: Allow
      http:
        methods:
          - GET
        paths:
          - exact: /health
          - exact: /ready
```

### パスによるフィルタリング

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: path-based-policy
  namespace: calico-demo
spec:
  selector: app == 'web-app'

  ingress:
    # Public endpoints
    - action: Allow
      http:
        paths:
          - prefix: /public/
          - exact: /

    # Admin endpoints - restricted
    - action: Allow
      source:
        selector: role == 'admin'
      http:
        paths:
          - prefix: /admin/

    # API endpoints - authenticated only
    - action: Allow
      source:
        selector: has(api-access)
      http:
        paths:
          - prefix: /api/
```

***

## HostEndpoint の保護

HostEndpoint は Calico が管理するノードインターフェイスを表します。作成すると、ホスト接続性が直ちに変わる可能性があります。`defaultEndpointToHostAction` はワークロードからローカルホストへの動作を制御しますが、HostEndpoint を作成する設定ではありません。`Installation.calicoNetwork.hostPorts` は hostPort のサポートを制御するもので、自動的にホストを保護する機能ではありません。

### 手動 HostEndpoint とポリシー

次の **フィールド例は完全なホストファイアウォールではありません**。自己管理のテストワーカー `demo-worker`（`10.0.1.10`）、bastion（`10.0.0.100`）、control plane の送信元（`10.0.1.5`）、インターフェイス `eth0` を前提とします。HostEndpoint を作成する前に、管理、DNS、DHCP、BGP、API、ヘルスチェック、egress に必要なルールをすべて確認し、実際の環境に置き換えてください。EKS 管理の control-plane ノードは想定していません。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-worker-ingress
spec:
  order: 100
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.100/32]
      destination:
        ports: [22]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.1.5/32]
      destination:
        ports: [10250]
---
apiVersion: projectcalico.org/v3
kind: HostEndpoint
metadata:
  name: demo-worker-eth0
  labels:
    host-demo: "true"
spec:
  node: demo-worker
  interfaceName: eth0
  expectedIPs: [10.0.1.10]
```

kubelet ルールは認証済みのワーカー 10250 エンドポイントを対象にします。認証のない旧式の read-only ポート 10255 をデフォルト要件として公開しないでください。この例が定義するのは ingress のみです。egress ポリシー / Profile がない状態で手動作成した HostEndpoint は、ホスト起点の通信を拒否する場合があります。実際の baseline を先に整えてください。

Calico のデフォルト failsafe には、受信 TCP 22 などの接続用ポートが含まれます。これらは前述の SSH ルールの制限意図を迂回するため、このルールだけでは SSH 接続を bastion に限定できません。failsafe リストと、テスト済みの復旧経路を確認してから変更してください。リストを無条件に空にしないでください。

### HostEndpoint の自動作成

ノードコントローラーの `KubeControllersConfiguration.spec.controllers.node.hostEndpoint.autoCreate` が自動作成を制御します。ほかのコントローラー設定を保持できるよう、merge patch を使ってください。

```bash
kubectl get kubecontrollersconfiguration.projectcalico.org default -o yaml
# Apply only after reviewing existing host endpoints and global policies.
kubectl patch kubecontrollersconfiguration.projectcalico.org default --type=merge \
  -p '{"spec":{"controllers":{"node":{"hostEndpoint":{"autoCreate":"Enabled"}}}}}'
```

この設定は条件に該当するすべてのノードに影響する可能性があります。自動作成されたエンドポイントには通常 default-allow Profile が付きますが、その Profile は一致するポリシーの Deny を上書きしません。カスタムテンプレートと `createDefaultHostEndpoint` を使って生成対象を絞れますが、既存デプロイで変更する場合は、先に既存エンドポイントとポリシーを確認してください。

### ローカル通信と転送通信

通常のホストポリシーでは `applyOnForward` はデフォルトで false です。true にすると転送通信にも適用されますが、その通信は該当するワークロードポリシーも通過しなければなりません。該当する転送ポリシーがエンドポイント / 方向を選択しなければ、転送通信はデフォルトで許可されます。選択した転送ポリシーに Allow がなければ拒否されます。ホストで終端するローカル通信では、Profile / failsafe の適用を受けるものの、デフォルトで拒否される動作が異なります。

## DoNotTrack と PreDNAT ポリシー

これは Linux ホストポリシーのパターンです。HostEndpoint に適用するものであり、選択した通常の Pod で tracking を無効にする方法ではありません。選択したデータプレーンでのサポートを確認してください。`doNotTrack` と `preDNAT` を同時に true にすることはできず、どちらも `applyOnForward: true` が必要です。

### DoNotTrack

untracked Allow は、一致する通信に対する connection tracking を省略します。常に性能が向上するわけではなく、conntrack を必要とする Service / NAT 経路と競合する場合があります。要求と応答の両方に明示的なルールが必要です。この例は、信頼するクライアントサブネットに直接応答する DNS プロセスがテストホスト上にあることを前提とします。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-untracked-dns
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 10
  types: [Ingress, Egress]
  doNotTrack: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: UDP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [53]
  egress:
    - action: Allow
      protocol: UDP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
    - action: Allow
      protocol: TCP
      source:
        ports: [53]
      destination:
        nets: [10.0.0.0/24]
```

通常のエンドポイントポリシーとは異なり、untracked 段階で一致するルールがない場合でも、Tier の最後で暗黙の drop にはなりません。後続の tracked ポリシーを適用できます。これはホスト全体を暗黙に deny-all にするファイアウォールではありません。

### PreDNAT

Pre-DNAT ポリシーは DNAT 前の元の宛先 IP / ポートを参照します。ingress のみが対象で、許可された通信の戻りには通常の connection tracking を使います。この例は、選択したホスト経路の TCP NodePort 30080 のみを保護します。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.demo-nodeport
spec:
  selector: host-demo == 'true' && !has(projectcalico.org/namespace)
  order: 20
  types: [Ingress]
  preDNAT: true
  applyOnForward: true
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.0.0.0/24]
      destination:
        ports: [30080]
    - action: Deny
      protocol: TCP
      destination:
        ports: [30080]
```

Pre-DNAT 段階にはデフォルト drop がありません。一致しない通信は後続のホスト / ワークロードポリシーへ進みます。2つ目の明示的なルールは、この NodePort 宛ての信頼できない通信を拒否します。ほかのポートはこの例の対象外です。ホストの NodePort を通らず Pod に直接到達する経路は、このルールでは保護されません。

***

## ポリシーのデバッグ

実際のラベル、namespace、Service エンドポイント、該当する全 Tier、両方向を確認してください。標準 Calico API server では、Tier selector を指定せずに一覧表示すると `default` Tier に限定される場合があります。`-A` は全 namespace を意味し、全 Tier を自動的に意味するわけではありません。

```bash
kubectl get networkpolicies.networking.k8s.io -n calico-demo -o yaml
kubectl get tiers.projectcalico.org -o yaml
for CALICO_TIER in $(kubectl get tiers.projectcalico.org -o jsonpath='{.items[*].metadata.name}'); do
  kubectl get networkpolicies.projectcalico.org -n calico-demo \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
  kubectl get globalnetworkpolicies.projectcalico.org \
    -l "projectcalico.org/tier=$CALICO_TIER" -o yaml
done
calicoctl get workloadendpoint -n calico-demo \
  --selector="app == 'frontend'" -o yaml
```

```bash
CALICO_NAMESPACE=calico-system
CALICO_NODE=demo-worker
CALICO_POD="$(kubectl -n "$CALICO_NAMESPACE" get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')"
test -n "$CALICO_POD"
kubectl -n "$CALICO_NAMESPACE" logs "$CALICO_POD" -c calico-node --tail=200
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  calico-node -felix-ready
```

```bash
# Assumes named, ready test Pods and an nc binary in the client image.
TARGET_POD=backend-test
TARGET_IP="$(kubectl -n calico-demo get pod "$TARGET_POD" -o jsonpath='{.status.podIP}')"
test -n "$TARGET_IP"
kubectl -n calico-demo exec frontend-client -- nc -z -w 3 "$TARGET_IP" 8080
```

`calico-node -felix-ready` コマンドが確認するのは readiness です。ポリシー trace やパケット単位の評価時間を測るコマンドではありません。Open Source の現行 `calicoctl` に、以前の `policy-trace` コマンドはありません。エンドポイント一覧やポリシー文の grep だけで、有効なポリシー全体を計算することもできません。

信頼するクライアント、信頼しないクライアント、誤ったポート、別 namespace のクライアント、リゾルバーへのアクセスについて、**新しい**接続でテストしてください。クライアントの一時的な送信元ポートではなく、宛先のポートを確認します。Pod に直接接続する場合と Service アドレスを使う場合を分けてテストし、ポリシーとエンドポイント / NAT / forwarding の問題を切り分けてください。そのため、kube-proxy またはその代替実装も関連します。

iptables データプレーンでは、正しいノード / network namespace 上にある実際の `cali-` chain を確認してください。仮の hash は実際の chain 名ではありません。iptables の Log アクションはホストの kernel log に書き込みます。一方、Felix の stdout は主にコンポーネント / コントローラーの診断情報です。stdout に記録がないことやカウンターがゼロであることだけでは、あらゆる経路でポリシーが未使用とは証明できません。eBPF / nftables では、それぞれのバックエンドに対応した診断方法が必要です。`tc filter show` だけでは、有効なポリシー判定は分かりません。

### 強制適用前に Stage する

Open Source 3.32 では `StagedNetworkPolicy`、`StagedGlobalNetworkPolicy`、`StagedKubernetesNetworkPolicy` を利用できます。Staged リソースはパケットの許可 / 拒否を適用しません。flow-log / Whisker パイプラインを構成すると、`policies.pending` を調べて観測された影響を事前に確認できます。

```yaml
apiVersion: projectcalico.org/v3
kind: StagedNetworkPolicy
metadata:
  name: default.preview-backend-egress
  namespace: calico-demo
spec:
  tier: default
  order: 100
  selector: app == 'frontend'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
```

この preview には backend 接続のみを意図的に含めています。同等の強制ポリシーを作る前に、必要な DNS やほかの通信が拒否されないか確認してください。通信が観測されないことは、その依存関係が不要である証明にはなりません。`action: Log` だけでは、常に audit-only になるわけではありません。評価は続き、最後に deny されることもあります。

***

## よく使うポリシーパターン

### Frontend → Backend → Database

このデモは、表示されているラベルと待ち受けポートを持ち、Ready なワークロードを前提とします。サーバーポートはすべて**宛先ポート**です。`source.ports: [8080]` にすると、一時的な送信元ポートを使うクライアントが通常は拒否されます。数値ポートルールはすべて TCP です。デモ用 gateway はアプリケーション fixture であり、特定の ingress controller がそのラベルを持つという前提はありません。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.frontend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'frontend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'gateway'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'backend'
        ports: [8080]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.backend
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'backend'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports: [8080]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports: [5432]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.database
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'database'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'backend'
      destination:
        ports: [5432]
  egress: []
```

DNS が必要なクライアントには、前提ラベルを指定した必須 egress パターンを使って、別途 DNS を許可してください。この単純化したパターンでは、データベースから新たな egress 接続は開始しませんが、stateful な応答通信は動作します。バックアップ、レプリケーション、外部依存関係には、それぞれ別途確認済みのルールが必要です。

### Tenant の分離

Calico の selector 内では `$(namespace.tenant)`、`${namespace.labels.tenant}`、`${namespace.name}` を展開できません。明示した tenant 値ごとにポリシーを生成するか、同じ namespace 内の分離には namespaced ポリシーを使用してください。

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.team-a-isolation
spec:
  order: 500
  namespaceSelector: tenant == 'team-a'
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        namespaceSelector: tenant == 'team-a'
  egress:
    - action: Allow
      destination:
        namespaceSelector: tenant == 'team-a'
    - action: Allow
      protocol: UDP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'kube-system'
        selector: k8s-app == 'kube-dns'
        ports: [53]
```

この設定は、namespace をまたいで team-a のラベルが付いた Pod 間の通信をすべて許可します。namespace ラベルの管理者とポリシー編集権限を制御してください。先行する Allow が意図した分離を覆すこともあります。異なる tenant 間と、ラベルのない namespace の両方をテストしてください。

### 同じ namespace 内の通信と共有サービス

この namespaced ポリシーでは、namespace selector を伴わない entity selector は `calico-demo` 内を対象にします。これは制限の厳しいマイクロサービスパターンの代替であり、そのパターンに重ねて適用する追加ポリシーではありません。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.namespace-and-shared
  namespace: calico-demo
spec:
  order: 200
  selector: all()
  types: [Ingress, Egress]
  ingress:
    - action: Allow
      source:
        selector: all()
  egress:
    - action: Allow
      destination:
        selector: all()
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'logging'
        selector: app == 'log-receiver'
        ports: [24224]
    - action: Allow
      protocol: TCP
      destination:
        namespaceSelector: kubernetes.io/metadata.name == 'auth'
        selector: app == 'identity-provider'
        ports: [8080]
```

必要なリゾルバーのルールは別途追加し、宛先側のポリシーでもクライアントを許可してください。ログ用ポートや identity provider のラベルは、デモ環境に関する明示的な前提です。実際の受信側プロトコル / ポートとアプリケーション認証を確認してください。

### Open Source の egress 制御

サービスのアドレス契約がある場合は、承認済みアドレスを NetworkSet で管理します。例の IP アドレスはドキュメント専用であり、実際の API エンドポイントでも、DNS を一度だけ引いた結果でもありません。

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: approved-api-ips
  namespace: calico-demo
  labels:
    destination-group: approved-api
spec:
  nets: [203.0.113.10/32]
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: default.approved-api-egress
  namespace: calico-demo
spec:
  order: 100
  selector: app == 'external-api-client'
  types: [Egress]
  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: destination-group == 'approved-api'
        ports: [443]
```

アプリケーションが名前を解決する場合は、前述の DNS ルールを使ってください。動的な外部サービスには、適切に認可した proxy か、別途記載された商用ドメインポリシーが必要です。すべての RFC1918 アドレスを許可しても「このクラスターだけ」に限定されず、無関係なプライベートネットワークへのアクセスを許す可能性があります。

### セキュリティ設計の一部としてのデフォルト拒否

範囲を限定した default-deny baseline を、必要な接続の明示許可、ラベル / RBAC の管理、アプリケーション認証と組み合わせてください。ネットワーク分離だけで完全なゼロトラストやコンプライアンス対応が実現するわけではありません。適用前にポリシーを Stage し、拒否されるべき経路もテストしてください。

***

## ポリシーの性能への影響

ポリシー数だけでは処理能力を測定できません。コストは、エンドポイント数、セレクターの変更、ルール構造、アクティブなフロー、更新頻度、選択したデータプレーンに左右されます。以前の「ポリシーが1,000個あると非常に遅い」「コストが線形に増える」という主張には、測定環境も生データもありませんでした。

等価性、集合への所属、ラベルの存在を調べるセレクターは、いずれも Calico の selector 最適化の効果を得られる場合があります。オブジェクト数を減らすことだけを目的に、許可範囲が広がる形でポリシーを統合しないでください。保守された NetworkSet を再利用し、ログ量を抑え、代表的な変更で収束時間を測定してください。

readiness check、「Policy sync」の grep、`iptables -L` の行数ではルール評価のレイテンシーを測定できません。文書化された Felix metrics endpoint を有効化して scrape し、metric の TYPE / HELP と単位を確認したうえで、制御されたワークロードで設定 / 更新の測定値と相関させます。

```bash
# After enabling the documented Felix metrics endpoint through its config owner:
kubectl -n "$CALICO_NAMESPACE" port-forward "pod/$CALICO_POD" 9091:9091
```

```bash
# In another terminal while the localhost port-forward remains active:
curl --fail --silent --show-error http://127.0.0.1:9091/metrics
```

Felix metrics はデフォルトで無効です。まず設定の管理元で `prometheusMetricsEnabled` を有効にしてください。選択したノードで endpoint に到達できる必要があります。ここでのコマンドはメトリクスを調べる例であり、公表済みの性能測定結果ではありません。ポリシーを変更しながら許可 / 拒否の両経路をテストし、Calico / Kubernetes / kernel の正確なバージョン、データプレーン、トポロジー、負荷、測定値を記録してください。

## 運用の原則

1. 隔離された namespace から始め、必要な通信を洗い出してから、明示ルールを Stage して適用する。
2. ラベル、namespace ラベル、ポリシー編集 RBAC を認可境界の一部として扱う。
3. Tier またはその順序を変更するたびに、終端 Allow / Pass の影響を確認する。
4. ホスト管理 / failsafe と Service / DNS の要件をアプリケーションルールから分離する。
5. ネットワーク分離をワークロード / エンドユーザー認証と組み合わせる。IP ルールだけであらゆる SSRF やコンプライアンス上の問題を防げるとは主張しない。

***

## 参考資料

* [Calico NetworkPolicy API](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
* [GlobalNetworkPolicy API](https://docs.tigera.io/calico/latest/reference/resources/globalnetworkpolicy)
* [Tier の評価](https://docs.tigera.io/calico/latest/reference/resources/tier)
* [Tier RBAC](https://docs.tigera.io/calico/latest/network-policy/policy-tiers/rbac-tiered-policies)
* [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
* [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
* [Open Source Istio / Dikastes アプリケーションポリシー](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy)
* [Enterprise ドメインポリシー](https://docs.tigera.io/calico-enterprise/latest/network-policy/domain-based-policy)
* [Staged ポリシー](https://docs.tigera.io/calico/latest/network-policy/staged-network-policies)
* [ホストの failsafe](https://docs.tigera.io/calico/latest/reference/host-endpoints/failsafe)
* [Pre-DNAT](https://docs.tigera.io/calico/latest/reference/host-endpoints/pre-dnat)
* [ホスト転送通信](https://docs.tigera.io/calico/latest/reference/host-endpoints/forwarded)
* [KubeControllersConfiguration](https://docs.tigera.io/calico/latest/reference/resources/kubecontrollersconfig)
* [ポリシーログ](https://docs.tigera.io/calico/latest/network-policy/policy-rules/log-rules)
* [コンポーネントのメトリクス](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)

* [Calico eBPF のプロトコルサポート](https://docs.tigera.io/calico/latest/operations/ebpf/install)
