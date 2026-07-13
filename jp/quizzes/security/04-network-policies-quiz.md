# Network Policies クイズ

このクイズでは、Kubernetes Network Policies、Cilium Network Policies、および microsegmentation についての理解を確認します。

## クイズ問題

### 1. Kubernetes NetworkPolicy のデフォルトの動作は何ですか？

A. すべてのトラフィックをブロックする
B. すべてのトラフィックを許可する
C. 受信のみをブロックする
D. 送信のみをブロックする

<details>
<summary>答えを表示</summary>

**答え: B. すべてのトラフィックを許可する**

**解説:**
NetworkPolicy がない場合、Kubernetes はデフォルトですべての Pods 間のトラフィックを許可します。NetworkPolicy を作成すると、その policy の podSelector に一致する Pods に対して「default deny」の動作が有効になります。

</details>

### 2. NetworkPolicy で特定の Pods を選択するフィールドはどれですか？

A. selector
B. podSelector
C. matchLabels
D. targetPods

<details>
<summary>答えを表示</summary>

**答え: B. podSelector**

**解説:**
NetworkPolicy の `spec.podSelector` フィールドは、policy が適用される Pods を選択します。
```yaml
spec:
  podSelector:
    matchLabels:
      app: web
```

空の podSelector (`{}`) は、namespace 内のすべての Pods を選択します。

</details>

### 3. NetworkPolicy で受信ルールと送信ルールを定義するフィールドはどれですか？

A. inbound/outbound
B. ingress/egress
C. input/output
D. incoming/outgoing

<details>
<summary>答えを表示</summary>

**答え: B. ingress/egress**

**解説:**
- **ingress**: 受信トラフィックルール
- **egress**: 送信トラフィックルール

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

### 4. CiliumNetworkPolicy では、L7 HTTP ルールはどこで定義されますか？

A. spec.http
B. spec.ingress.toPorts.rules.http
C. spec.rules.http
D. spec.layer7.http

<details>
<summary>答えを表示</summary>

**答え: B. spec.ingress.toPorts.rules.http**

**解説:**
CiliumNetworkPolicy の L7 ルールは、toPorts 内の rules セクションで定義されます。
```yaml
spec:
  ingress:
    - toPorts:
        - ports:
            - port: "80"
          rules:
            http:
              - method: GET
                path: "/api/.*"
```

</details>

### 5. default deny policy を実装するための正しい NetworkPolicy はどれですか？

A. policyTypes に Ingress のみを指定する
B. podSelector を空に設定し、policyTypes に Ingress と Egress を指定する
C. ingress ルールと egress ルールを空のままにする
D. B と C の両方

<details>
<summary>答えを表示</summary>

**答え: D. B と C の両方**

**解説:**
default deny policy の例:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
spec:
  podSelector: {}  # Select all Pods
  policyTypes:
    - Ingress
    - Egress
  # No ingress and egress rules = block all traffic
```

空の podSelector はすべての Pods を選択し、ルールがない場合、そのトラフィックタイプはブロックされます。

</details>

### 6. CiliumClusterwideNetworkPolicy の特徴は何ですか？

A. 特定の namespace にのみ適用される
B. クラスター全体に適用される
C. 外部トラフィックのみを制御する
D. L7 policies のみをサポートする

<details>
<summary>答えを表示</summary>

**答え: B. クラスター全体に適用される**

**解説:**
CiliumClusterwideNetworkPolicy は、namespace に関係なくクラスター全体に適用されます。共通のセキュリティルール（例: すべての namespaces から metadata service へのアクセスをブロックする）を実装する場合に役立ちます。

</details>

### 7. NetworkPolicy で特定の namespace からのすべての Pods を許可するにはどうすればよいですか？

A. namespaceSelector のみを使用する
B. podSelector のみを使用する
C. namespaceSelector と空の podSelector を組み合わせる
D. namespace フィールドを使用する

<details>
<summary>答えを表示</summary>

**答え: A. namespaceSelector のみを使用する**

**解説:**
```yaml
ingress:
  - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
```

namespaceSelector のみを使用すると、その namespace からのすべての Pods が許可されます。podSelector を一緒に使用すると、その namespace 内の特定の Pods のみが選択されます。

</details>

### 8. CiliumNetworkPolicy で FQDN ベースの egress ルールを定義するフィールドはどれですか？

A. toFQDNs
B. toDomains
C. toHosts
D. toEndpoints

<details>
<summary>答えを表示</summary>

**答え: A. toFQDNs**

**解説:**
CiliumNetworkPolicy の toFQDNs は、DNS 名に基づく egress トラフィックを許可します。
```yaml
spec:
  egress:
    - toFQDNs:
        - matchName: "api.example.com"
        - matchPattern: "*.amazonaws.com"
      toPorts:
        - ports:
            - port: "443"
```

</details>

### 9. NetworkPolicy の影響を受けないトラフィックはどれですか？

A. Pods 間のトラフィック
B. 同じ Pod 内の containers 間のトラフィック (localhost)
C. Services 経由のトラフィック
D. 外部ソースからのトラフィック

<details>
<summary>答えを表示</summary>

**答え: B. 同じ Pod 内の containers 間のトラフィック (localhost)**

**解説:**
NetworkPolicy は Pods 間のネットワークトラフィックに適用されます。同じ Pod 内の containers 間の localhost 通信は、NetworkPolicy の範囲外です。また、node の hostNetwork を使用する Pods にはいくつかの制限があります。

</details>

### 10. Cilium の Identity ベース policy の利点は何ですか？

A. IP アドレスの変更の影響を受けない
B. 処理速度が速い
C. メモリ使用量が少ない
D. DNS lookup が不要

<details>
<summary>答えを表示</summary>

**答え: A. IP アドレスの変更の影響を受けない**

**解説:**
Cilium Identity は Pod labels に基づいて生成されます。Pod が再起動して IP が変更されても、同じ labels を持っていれば同じ Identity を維持します。これにより、IP ベース policies の制限を克服できます。

</details>

### 11. 3-tier architecture における backend tier の正しい network policy はどれですか？

A. すべてのトラフィックを許可する
B. frontend からの ingress のみを許可する
C. frontend からの ingress を許可し、database への egress を許可する
D. database への egress のみを許可する

<details>
<summary>答えを表示</summary>

**答え: C. frontend からの ingress を許可し、database への egress を許可する**

**解説:**
3-tier microsegmentation では、backend について:
- **Ingress**: frontend tier からのみ許可
- **Egress**: database tier へのみ許可

これは最小権限の原則に従い、tiers 間のトラフィックフローを明確に制御します。

</details>

### 12. NetworkPolicy で ipBlock による CIDR 範囲を指定する際、特定の IPs を除外するフィールドはどれですか？

A. exclude
B. except
C. notIn
D. excludeCIDR

<details>
<summary>答えを表示</summary>

**答え: B. except**

**解説:**
ipBlock の except フィールドは、特定の CIDRs を除外できます。
```yaml
ingress:
  - from:
      - ipBlock:
          cidr: 10.0.0.0/8
          except:
            - 10.0.1.0/24
            - 10.0.2.0/24
```

これにより、10.0.1.0/24 と 10.0.2.0/24 を除く 10.0.0.0/8 範囲からのトラフィックが許可されます。

</details>
