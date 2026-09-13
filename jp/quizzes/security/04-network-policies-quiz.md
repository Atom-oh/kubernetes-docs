# Network Policies クイズ

> **最終更新**: September 13, 2026

このクイズでは、Kubernetes Network Policies、Cilium Network Policies、およびマイクロセグメンテーション（microsegmentation）に関する理解度を確認します。

## クイズ問題

### 1. Kubernetes NetworkPolicy のデフォルト動作はどれですか？

A. すべてのトラフィックをブロックする
B. 選択するポリシーが存在しない方向では NetworkPolicy による分離は行われない
C. 受信のみをブロックする
D. 送信のみをブロックする

<details>
<summary>解答を表示</summary>

**解答: B. 選択するポリシーが存在しない方向では NetworkPolicy による分離は行われない**

**解説:**
ingress と egress は別々に評価されます。ある方向を選択するポリシーが存在しない場合、NetworkPolicy はその方向を分離しません。ただし、CNI／ルート／SG／NACL などの他のポリシーによって接続がブロックされる可能性はあります。ingress のみを選択するポリシーがあっても、egress が同時に分離されるわけではありません。Pod 間トラフィックでは、送信元の egress と宛先の ingress の両方が接続を許可している必要があります。

</details>

### 2. NetworkPolicy で特定の Pod を選択するフィールドはどれですか？

A. selector
B. podSelector
C. matchLabels
D. targetPods

<details>
<summary>解答を表示</summary>

**解答: B. podSelector**

**解説:**
NetworkPolicy の `spec.podSelector` フィールドは、ポリシーを適用する Pod を選択します:
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

空の podSelector (`{}`) は、その namespace 内のすべての Pod を選択します。

</details>

### 3. NetworkPolicy で受信ルールと送信ルールを定義するフィールドはどれですか？

A. inbound/outbound
B. ingress/egress
C. input/output
D. incoming/outgoing

<details>
<summary>解答を表示</summary>

**解答: B. ingress/egress**

**解説:**
- **ingress**: 受信トラフィックのルール
- **egress**: 送信トラフィックのルール

```yaml
spec:
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
```

</details>

### 4. CiliumNetworkPolicy において L7 HTTP ルールはどこで定義しますか？

A. spec.http
B. spec.ingress[].toPorts[].rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>解答を表示</summary>

**解答: B. spec.ingress[].toPorts[].rules.http**

**解説:**
HTTP ルールは ingress ルールの `toPorts[].rules.http` の下（送信方向のフィルタリングであれば egress ルールの下）にネストされます。これらはサポートされている L7 プロキシ経路を必要とします。エンドツーエンドの TLS は自動的に検査されず、ユーザーが指定する role／API キーのヘッダーは認証にはなりません。Cilium の AWS VPC CNI チェイニングモードには文書化された L7 の制限があります。

</details>

<span id="_5-what-is-the-correct-networkpolicy-for-implementing-a-default-deny-policy"></span>

### 5. 双方向に対して namespace 全体のデフォルト拒否（default-deny）のベースラインを作成するのはどれですか？

A. policyTypes に Ingress のみを指定する
B. podSelector を空にし、policyTypes に Ingress と Egress を指定する
C. ingress ルールと egress ルールを空のままにする
D. B と C の両方

<details>
<summary>解答を表示</summary>

**解答: D. B と C の両方**

**解説:**
**双方向**で namespace 全体のベースラインを作るには、B と C を組み合わせます。空のセレクターはポリシー自身の namespace 内のすべての Pod を選択し、明示的な Ingress／Egress タイプに許可ルールを持たせないことで双方向が分離されます。他に選択する Kubernetes NetworkPolicy があれば許可を追加できます。ベースラインがそれらを上書きすることはありません。より狭い範囲を意図する場合は、ingress のみのベースラインも可能です。

</details>

### 6. CiliumClusterwideNetworkPolicy の特徴はどれですか？

A. スコープを選択するために metadata.namespace が必要である
B. クラスタースコープのリソースであり、エンドポイントセレクターが対象を制御する
C. 外部トラフィックのみを制御する
D. L7 ポリシーのみをサポートする

<details>
<summary>解答を表示</summary>

**解答: B. クラスタースコープのリソースであり、エンドポイントセレクターが対象を制御する**

**解説:**
CiliumClusterwideNetworkPolicy は namespace に属しません。そのエンドポイントセレクターは複数の namespace を対象にすることもでき、対象を 1 つの namespace／アプリケーションへ明示的に絞り込むこともできます。クラスタースコープであることは、すべてのエンドポイントが選択されることを意味せず、`cluster`／`world` を広く許可するルールがデフォルト拒否になることも意味しません。

</details>

### 7. NetworkPolicy で特定の namespace のすべての Pod を許可する方法はどれですか？

A. namespaceSelector のみを使用する
B. podSelector のみを使用する
C. namespaceSelector と app=api を要求する podSelector を組み合わせる
D. namespace フィールドを使用する

<details>
<summary>解答を表示</summary>

**解答: A. namespaceSelector のみを使用する**

**解説:**
`namespaceSelector.matchLabels.kubernetes.io/metadata.name: monitoring` を使用して、その namespace 内のすべての Pod を選択します。同じピア内に**空の** podSelector を追加した場合も、すべての Pod が選択されます。一方、選択肢 C は Pod を `app=api` に限定します。1 つのピア内のセレクターは AND で結合され、別々のピアのエントリは OR で結合されます。カスタムの `name` ラベルは自動的には作成されません。

</details>

### 8. CiliumNetworkPolicy で FQDN ベースの egress ルールを定義するフィールドはどれですか？

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>解答を表示</summary>

**解答: A. toFQDNs**

**解説:**
`toFQDNs` は DNS から得られた IP を、指定されたポートルールとともに使用します。実際のリゾルバー経路と必要な DNS クエリは、UDP53 だけでなく TCP も含めて個別に許可してください。キャッシュ／TTL、検索サフィックス、宛先 IP の共有、TLS／アプリケーションレベルの認可も依然として重要です。ドメインが一致したことは、SaaS のテナント同一性の証明にはなりません。

</details>

### 9. NetworkPolicy の影響を受け**ない**トラフィックはどれですか？

A. Pod 間のトラフィック
B. 同一 Pod 内のコンテナ間トラフィック（localhost）
C. Service 経由のトラフィック
D. 外部からのトラフィック

<details>
<summary>解答を表示</summary>

**解答: B. 同一 Pod 内のコンテナ間トラフィック（localhost）**

**解説:**
1 つの Pod 内のコンテナはネットワーク namespace を共有しており、その localhost 通信は通常の Kubernetes NetworkPolicy による適用の範囲外です。Node／hostNetwork の扱いや TCP/UDP/SCTP 以外のプロトコルには、実装固有の制限があります。Pod のポリシーからホスト全体の分離を推測しないでください。

</details>

### 10. Cilium の Identity ベースのポリシーの利点は何ですか？

A. IP アドレスの変更に影響されない
B. 処理速度が速い
C. メモリ使用量が少ない
D. DNS ルックアップが不要である

<details>
<summary>解答を表示</summary>

**解答: A. IP アドレスの変更に影響されない**

**解説:**
ラベルベースのエンドポイントポリシーでは、一時的な Pod IP をハードコードする必要がありません。データパスは、関連するラベルセットに対応するセキュリティアイデンティティへ現在のエンドポイントをマッピングします。数値のアイデンティティは再割り当てされる可能性があり、恒久的なアプリケーション識別子ではありません。ラベルの変更、namespace／クラスターのコンテキスト、伝播についても引き続き考慮する必要があります。

</details>

### 11. 3 層アーキテクチャにおいて backend 層に適切なネットワークポリシーはどれですか？

A. すべてのトラフィックを許可する
B. frontend からの ingress のみを許可する
C. frontend からの ingress を許可し、database への egress を許可する
D. database への egress のみを許可する

<details>
<summary>解答を表示</summary>

**解答: C. frontend からの ingress を許可し、database への egress を許可する**

**解説:**
C は backend のアプリケーション経路、つまり確認済みのポートにおける frontend からの ingress と database への egress を表しています。加えて、frontend の egress と database の ingress、さらに必要に応じて選択した DNS／ヘルスチェック／モニタリングの経路も許可してください。そうしなければ、相手側エンドポイントのデフォルト拒否ポリシーによって接続がブロックされる可能性があります。許可された接続の戻りトラフィックは暗黙的に許可されます。

</details>

### 12. NetworkPolicy で ipBlock により CIDR 範囲を指定する際、特定の IP を除外するフィールドはどれですか？

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>解答を表示</summary>

**解答: B. except**

**解説:**
`except` は、その ipBlock の許可ルールから CIDR を差し引きます。これはグローバルな拒否ではありません。別の選択するポリシーが、除外されたアドレスを許可することがあります。アドレス変換によってプラグインが評価する IP が変わる場合があるため、実際の CNI とロードバランサー／Service の経路を確認してください。

</details>

---

[Network policies guide](../../security/04-network-policies.md)
