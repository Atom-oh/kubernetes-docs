# Cilium Service Mesh セキュリティクイズ

このクイズでは、Cilium Service Mesh における mTLS、network policy、暗号化、Identity ベースのセキュリティ、ゼロトラストネットワーキングについての理解を確認します。

## クイズ問題

### 1. Cilium Service Mesh は、透過的な mTLS を実装するためにどの技術を使用しますか？

A. Istio sidecar
B. SPIFFE/SPIRE integration
C. Nginx proxy
D. HAProxy

<details>
<summary>回答を表示</summary>

**回答: B. SPIFFE/SPIRE integration**

**解説:**
Cilium Service Mesh は、透過的な mTLS を実装するために SPIFFE（Secure Production Identity Framework for Everyone）および SPIRE と統合します。これにより、application code を変更することなく workload 間の通信を暗号化できます。

</details>

### 2. authentication mode が 'required' に設定されている場合、CiliumNetworkPolicy はどのように動作しますか？

A. authentication なしですべての traffic を許可する
B. mutual authentication に成功した traffic のみを許可する
C. authentication に失敗した場合は警告のみをログに記録する
D. mTLS を無効にする

<details>
<summary>回答を表示</summary>

**回答: B. mutual authentication に成功した traffic のみを許可する**

**解説:**
authentication mode が 'required' に設定されている場合、mutual authentication を正常に完了した traffic のみが許可されます。authentication に失敗した traffic はブロックされます。これはゼロトラストセキュリティモデルを実装するうえで不可欠です。

</details>

### 3. Cilium における WireGuard encryption の利点ではないものはどれですか？

A. kernel level で動作する高い performance
B. automatic key management
C. IETF standard protocol
D. ChaCha20Poly1305 encryption

<details>
<summary>回答を表示</summary>

**回答: C. IETF standard protocol**

**解説:**
WireGuard は standard protocol ではありません。IPsec は IETF standard protocol です。ただし、WireGuard は Linux kernel 5.6+ に組み込まれており、高い performance、automatic key management、ChaCha20Poly1305 encryption を提供します。

</details>

### 4. CiliumNetworkPolicy で L7 HTTP rules を使用して特定の path と method を制限する正しい設定はどれですか？

A. toEndpoints で path と method を指定する
B. toPorts.rules.http で method と path を指定する
C. ingress.http で直接指定する
D. spec.http で rules を定義する

<details>
<summary>回答を表示</summary>

**回答: B. toPorts.rules.http で method と path を指定する**

**解説:**
CiliumNetworkPolicy では、L7 HTTP rules は toPorts section 内の rules.http で定義されます。ここでは、きめ細かな access control のために method（GET、POST など）と path（regex support あり）を指定できます。

</details>

### 5. Cilium Identity ベースのセキュリティの主な利点は何ですか？

A. IP address の変更の影響を受けない
B. MAC address ベースのためより安全である
C. manual ID management が可能である
D. VLAN tagging をサポートする

<details>
<summary>回答を表示</summary>

**回答: A. IP address の変更の影響を受けない**

**解説:**
Cilium Identity は Pod label に基づいて生成されるため、Pod が再起動して IP address が変更されても、同じ Identity を維持します。これにより、IP ベースの security policy の制限を克服できます。

</details>

### 6. Cilium で DNS L7 policy を使用して外部 domain access を制限するには、どの rules を使用しますか？

A. toFQDNs と dns rules の組み合わせ
B. toEndpoints のみ
C. toCIDR のみ
D. toEntities のみ

<details>
<summary>回答を表示</summary>

**回答: A. toFQDNs と dns rules の組み合わせ**

**解説:**
外部 domain access の制限は、2 つの手順で設定します。1) DNS L7 rules（toPorts.rules.dns）で特定の domain query のみを許可する、2) toFQDNs でそれらの domain への実際の connection を許可する。この組み合わせにより、workload の外部 access をきめ細かく制御できます。

</details>

### 7. CiliumClusterwideNetworkPolicy で default deny policy を実装する場合、通常どの traffic を許可する必要がありますか？

A. すべての外部 traffic
B. DNS query と host network traffic
C. すべての internet traffic
D. 特定の IP range のみ

<details>
<summary>回答を表示</summary>

**回答: B. DNS query と host network traffic**

**解説:**
default deny policy を実装する場合、cluster が正常に機能するためには、少なくとも kube-dns（port 53/UDP）への DNS query と host network traffic（reserved:host）を許可する必要があります。これらがなければ、service discovery と node communication は不可能になります。

</details>

### 8. SPIRE における workload attestation の役割は何ですか？

A. Certificate issuance
B. workload identity の検証
C. network policy の適用
D. traffic encryption

<details>
<summary>回答を表示</summary>

**回答: B. workload identity の検証**

**解説:**
workload attestation は、SPIRE Agent が workload の identity を検証するプロセスです。Kubernetes environment では、workload に適切な SVID（SPIFFE Verifiable Identity Document）を発行するために、その Pod の service account、namespace、label などを検証します。

</details>

### 9. audit mode で network policy をテストする場合、Cilium はどのように動作しますか？

A. すべての traffic をブロックする
B. policy violation をログに記録するが、traffic は許可する
C. policy を完全に無効にする
D. alert のみを送信する

<details>
<summary>回答を表示</summary>

**回答: B. policy violation をログに記録するが、traffic は許可する**

**解説:**
audit mode（cilium.io/audit-mode: "true" annotation）では、policy に違反する traffic はブロックされず、ログに記録されるだけです。これにより、新しい policy を production に適用する前に影響を評価できます。

</details>

### 10. 3-tier architecture で microsegmentation を実装する場合、backend service に対する正しい policy はどれですか？

A. すべての traffic を許可する
B. frontend からの ingress のみを許可し、database への egress のみを許可する
C. すべての ingress をブロックする
D. internet access を許可する

<details>
<summary>回答を表示</summary>

**回答: B. frontend からの ingress のみを許可し、database への egress のみを許可する**

**解説:**
microsegmentation では、backend service は最小権限の原則に従います。frontend tier からの ingress のみを許可し、database tier への egress のみを許可します。これにより、各 tier 間の traffic を明確に定義して制御できます。

</details>

### 11. Cilium における IPsec と WireGuard encryption の違いを正しく説明しているものはどれですか？

A. kernel で動作するのは IPsec のみである
B. WireGuard では manual key management が必要である
C. IPsec は IETF standard、WireGuard は non-standard である
D. node-to-node encryption をサポートするのは WireGuard のみである

<details>
<summary>回答を表示</summary>

**回答: C. IPsec は IETF standard、WireGuard は non-standard である**

**解説:**
IPsec は IETF standard protocol である一方、WireGuard は non-standard です。両方とも kernel で動作し、WireGuard は automatic key management を提供します。両方とも node-to-node encryption をサポートします。

</details>

### 12. Hubble で policy violation を監視するために使用する command はどれですか？

A. hubble observe --verdict FORWARDED
B. hubble observe --verdict DROPPED
C. hubble policy list
D. hubble status --violations

<details>
<summary>回答を表示</summary>

**回答: B. hubble observe --verdict DROPPED**

**解説:**
`hubble observe --verdict DROPPED` command は、network policy によって拒否（DROPPED）された traffic を監視します。これにより、policy violation をリアルタイムで検出して分析できます。

</details>
