# Network Policy クイズ

> **関連ドキュメント**: [Network Policy](../../../networking/calico/05-network-policy.md)
> **最終更新**: February 22, 2026

## クイズ

1. Calico が対応する、Kubernetes 標準 NetworkPolicy の主な制限は何ですか？
   - A) ポート番号を指定できない
   - B) egress rules をサポートしていない
   - C) Deny rules、global policies がなく、selector options が限定的
   - D) labels で Pod を選択できない

<details>
<summary>回答を表示</summary>

**回答: C) Deny rules、global policies がなく、selector options が限定的**

**解説:**
Kubernetes 標準 NetworkPolicy にはいくつかの制限があります。Allow rules のみをサポートし（明示的な Deny は不可）、クラスター全体の global policies を作成できず、selector options も限定的で、L7（application layer）filtering もサポートしていません。Calico は、明示的な Deny/Allow/Log/Pass actions、GlobalNetworkPolicy、advanced selectors、L7 policy support により NetworkPolicy を拡張します。

</details>

2. Calico NetworkPolicy の selectors の構文は何ですか？
   - A) 標準 Kubernetes のような YAML key-value pairs
   - B) `app == 'frontend'` のような expression-based syntax
   - C) regular expressions
   - D) JSON path expressions

<details>
<summary>回答を表示</summary>

**回答: B) `app == 'frontend'` のような expression-based syntax**

**解説:**
Calico は、`==`、`!=`、`in`、`not in`、`has()`、`!has()` などの operators をサポートする expression-based selector syntax を使用します。例: `app == 'frontend'`、`environment in {'prod', 'staging'}`、`has(role)`。これにより、標準 Kubernetes label selectors よりも高い柔軟性が得られます。

</details>

3. Calico NetworkPolicy rules で有効な action types は何ですか？
   - A) Accept、Reject
   - B) Allow、Deny、Log、Pass
   - C) Permit、Block、Audit
   - D) Enable、Disable、Monitor

<details>
<summary>回答を表示</summary>

**回答: B) Allow、Deny、Log、Pass**

**解説:**
Calico NetworkPolicy は 4 つの action types をサポートします。`Allow`（traffic を許可）、`Deny`（traffic を破棄）、`Log`（traffic をログに記録して evaluation を継続）、`Pass`（次の tier に進んで evaluation）です。これらの actions により、traffic handling をきめ細かく制御できます。

</details>

4. Calico における GlobalNetworkPolicy と NetworkPolicy の違いは何ですか？
   - A) GlobalNetworkPolicy の方が高速である
   - B) NetworkPolicy には namespace が必要で、GlobalNetworkPolicy はクラスター全体に適用される
   - C) GlobalNetworkPolicy は eBPF mode でのみ動作する
   - D) NetworkPolicy はより多くの features をサポートする

<details>
<summary>回答を表示</summary>

**回答: B) NetworkPolicy には namespace が必要で、GlobalNetworkPolicy はクラスター全体に適用される**

**解説:**
Calico NetworkPolicy は namespaced であり、Kubernetes NetworkPolicy と同様にその namespace 内の Pod にのみ適用されます。GlobalNetworkPolicy はクラスター全体に適用され、すべての namespaces にまたがるすべての Pod に適用できます。そのため、security baselines、compliance requirements、default deny policies などのクラスター全体の rules に最適です。

</details>

5. Calico では NetworkSet は何に使用されますか？
   - A) network interfaces のグループ化
   - B) 再利用可能な IP addresses/CIDRs の sets を定義する
   - C) network namespaces を設定する
   - D) network plugins を管理する

<details>
<summary>回答を表示</summary>

**回答: B) 再利用可能な IP addresses/CIDRs の sets を定義する**

**解説:**
NetworkSet は、network policies から参照できる IP addresses または CIDR blocks のセットを定義する Calico resource です。これにより、external IPs（database servers や trusted partners など）の groups を一度定義し、複数の policies から参照できるため、policy management が容易になり、保守性も向上します。

</details>

6. Calico の policy model では Tiers はどのように evaluation されますか？
   - A) 名前のアルファベット順
   - B) order field により、低い数値から先に evaluation される
   - C) ランダム
   - D) creation timestamp による

<details>
<summary>回答を表示</summary>

**回答: B) order field により、低い数値から先に evaluation される**

**解説:**
Tiers は `order` field に基づく順序で evaluation され、低い数値から先に evaluation されます。各 tier 内でも、policies は order field により evaluation されます。この階層構造により、組織は security policies（low order）、platform policies（medium order）、application policies（high order）を分離できます。

</details>

7. Calico policy rule の Pass action は何をしますか？
   - A) traffic を直ちに許可する
   - B) traffic を通知なく破棄する
   - C) evaluation を継続するため次の tier に進む
   - D) traffic をログに記録して許可する

<details>
<summary>回答を表示</summary>

**回答: C) evaluation を継続するため次の tier に進む**

**解説:**
`Pass` action により、policy evaluation は現在の tier 内の残りの policies をスキップし、次の tier で継続します。これは、より高い priority の tier（security など）が特定の traffic について最終判断を下すのではなく、より低い priority の tiers（application policies など）でさらに evaluation することを許可したい場合に有用です。

</details>

8. Calico で FQDN-based（domain name）policies を実装するにはどうしますか？
   - A) ingress rules の `hosts` field を使用する
   - B) destination specification の `domains` field を使用する
   - C) FQDN policies はサポートされていない
   - D) DNS NetworkPolicy CRD を使用する

<details>
<summary>回答を表示</summary>

**回答: B) destination specification の `domains` field を使用する**

**解説:**
Calico は egress rules の `domains` field を使用して FQDN-based policies をサポートします。`"*.amazonaws.com"` のような domain patterns や exact domains を指定できます。Calico はこれらの domains を IP addresses に解決し、適切な rules を作成します。この feature は Calico Enterprise で利用でき、open-source Calico では DNS proxy configuration が必要です。

</details>

9. GlobalNetworkPolicy の applyOnForward setting は何を制御しますか？
   - A) policy を host を通過する forwarded/routed traffic に適用するかどうか
   - B) policy を forward order または reverse order で適用するかどうか
   - C) policy violations を SIEM に転送するかどうか
   - D) policy を port forwarding に適用するかどうか

<details>
<summary>回答を表示</summary>

**回答: A) policy を host を通過する forwarded/routed traffic に適用するかどうか**

**解説:**
`applyOnForward` setting は、policy を host を経由して forwarding される traffic（host 自体を destination または origin としない traffic）に適用するかどうかを決定します。これは host endpoint policies や、node が他の endpoints 間の traffic の router として動作する scenarios において重要です。

</details>

10. Calico policy における doNotTrack の目的は何ですか？
    - A) policy logging を無効にする
    - B) connection tracking より前に policy を適用する（stateless）
    - C) audit logs で policy が追跡されないようにする
    - D) endpoint tracking を無効にする

<details>
<summary>回答を表示</summary>

**回答: B) connection tracking より前に policy を適用する（stateless）**

**解説:**
`doNotTrack` option は、Linux connection tracking（conntrack）より前に policy rules を適用します。これにより connection state を追跡しない stateless rules が作成され、高-performance scenarios や、traffic が connection tracking system に入る前に rules を適用する必要がある場合に有用です。request traffic と response traffic の両方を明示的に許可する必要があります。

</details>

11. Calico policy における preDNAT の目的は何ですか？
    - A) DNS resolution より前に policy を適用する
    - B) Destination NAT より前に policy を適用し、original destination を確認する
    - C) DNAT の実行を防ぐ
    - D) DNS traffic にのみ policy を適用する

<details>
<summary>回答を表示</summary>

**回答: B) Destination NAT より前に policy を適用し、original destination を確認する**

**解説:**
`preDNAT` option は Destination NAT が実行される前に policy を適用するため、translation 前の original destination IP/port を policy で確認できます。これは、DNAT により Pod IP へ translation される前に、original destination（external IPs など）に基づいて traffic を filter したい host endpoints 上の policies に有用です。

</details>

12. Calico で全 Pod に対する default deny policy を実装するにはどうしますか？
    - A) FelixConfiguration で cluster-wide flag を設定する
    - B) selector `all()` を持ち rules がない GlobalNetworkPolicy を作成する
    - C) 既存のすべての NetworkPolicies を削除する
    - D) IPPool で default deny を設定する

<details>
<summary>回答を表示</summary>

**回答: B) selector `all()` を持ち rules がない GlobalNetworkPolicy を作成する**

**解説:**
default deny を実装するには、すべての Pod を選択する GlobalNetworkPolicy（`selector: all()`）を `types: [Ingress, Egress]` とともに作成しますが、allow rules は指定しません。この policy は最後に evaluation されるよう、高い order number を設定する必要があります。他の policies によって明示的に許可されていない traffic は、この catch-all policy により deny されます。

</details>

13. Calico policy の order field は何を制御しますか？
    - A) Pod が選択される順序
    - B) tier 内の evaluation priority（低い値 = 先）
    - C) policy 内での rule application の順序
    - D) NetworkSets 内の IP addresses の順序

<details>
<summary>回答を表示</summary>

**回答: B) tier 内の evaluation priority（低い値 = 先）**

**解説:**
`order` field は tier 内の policies の evaluation priority を決定します。order values が低い policies から先に evaluation されます。policy が match して terminal action（Allow または Deny）を実行すると、evaluation は停止します。これにより、general rules の前に high-priority exceptions を作成できます。

</details>

14. Calico における Host Endpoint とは何ですか？
    - A) host network 上で実行される Pod
    - B) policy enforcement のための host's network interface の representation
    - C) API server endpoint
    - D) host 上の service endpoint

<details>
<summary>回答を表示</summary>

**回答: B) policy enforcement のための host's network interface の representation**

**解説:**
Host Endpoint は host node 上の network interface を表し、Calico policies を host 自体に出入りする traffic（Pod traffic だけではない）に適用できます。これにより、host の network interfaces を保護し、node services に到達できる traffic を制御し、host-level firewall rules を実装できます。

</details>

15. network policy が想定どおりに動作しない理由をどのように debug できますか？
    - A) policy YAML を読むだけで確認する
    - B) workload endpoints、calicoctl による policy evaluation、Felix logs を確認する
    - C) すべての Calico components を再起動する
    - D) network policy debugging はサポートされていない

<details>
<summary>回答を表示</summary>

**回答: B) workload endpoints、calicoctl による policy evaluation、Felix logs を確認する**

**解説:**
network policies を debug するには、次を実施します。1) `calicoctl get workloadendpoint -n <namespace>` を使用して endpoint が存在し正しい labels を持つことを確認する、2) `calicoctl get networkpolicy -A` と `globalnetworkpolicy` を使用してすべての policies を一覧表示する、3) Felix logs で policy-related messages を確認する、4) selector expressions が endpoint labels と一致することを確認する、5) eBPF mode では `tc filter show` を使用して適用済み rules を確認する。

</details>

---

[学習教材に戻る](../../../networking/calico/05-network-policy.md) | [前のクイズ: BGP Deep Dive](./04-bgp-deep-dive-quiz.md)
