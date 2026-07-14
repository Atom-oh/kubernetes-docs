# BGP 詳細クイズ

> **関連ドキュメント**: [BGP 詳細](../../../networking/calico/04-bgp-deep-dive.md)
> **最終更新**: February 22, 2026

## クイズ

1. BGP は何の略ですか？
   - A) Basic Gateway Protocol
   - B) Border Gateway Protocol
   - C) Bridge Gateway Protocol
   - D) Bandwidth Gateway Protocol

<details>
<summary>答えを表示</summary>

**回答: B) Border Gateway Protocol**

**解説:**
BGP は Border Gateway Protocol の略です。これはインターネットを支えるルーティングプロトコルであり、Autonomous System 間でルーティング情報を交換できます。Calico では、BGP を使用して node 間で Pod ネットワークルートを配布し、必要に応じて外部ネットワークインフラストラクチャにも配布します。

</details>

2. iBGP と eBGP の違いは何ですか？
   - A) iBGP は高速で、eBGP はより安全である
   - B) iBGP は同じ AS 内、eBGP は異なる AS 間で使用される
   - C) iBGP は TCP を使用し、eBGP は UDP を使用する
   - D) iBGP は IPv4 用、eBGP は IPv6 用である

<details>
<summary>答えを表示</summary>

**回答: B) iBGP は同じ AS 内、eBGP は異なる AS 間で使用される**

**解説:**
iBGP (Internal BGP) は、同じ Autonomous System (AS) 内の router 間の BGP session を指します。eBGP (External BGP) は、異なる Autonomous System の router 間の BGP session を指します。Calico cluster では、通常、cluster 内（同じ AS）で iBGP を使用し、外部ネットワークインフラストラクチャ（異なる AS）との peering に eBGP を使用する場合があります。

</details>

3. Calico cluster で使用できる private AS number の範囲は何ですか？
   - A) 1-64511
   - B) 64512-65534
   - C) 65535-65600
   - D) 100000-200000

<details>
<summary>答えを表示</summary>

**回答: B) 64512-65534**

**解説:**
private AS number の範囲は、64512-65534（16-bit ASN 用）および 4200000000-4294967294（32-bit ASN 用）です。これらの範囲は private use 用に指定されており、private IP address range と同様にグローバルルーティングできません。Calico cluster では、64512-65534 の範囲の AS number が一般的に使用されます。

</details>

4. full-mesh BGP topology において、N 個の node がある cluster ではいくつの BGP session が確立されますか？
   - A) N sessions
   - B) N * 2 sessions
   - C) N * (N-1) / 2 sessions
   - D) N^2 sessions

<details>
<summary>答えを表示</summary>

**回答: C) N * (N-1) / 2 sessions**

**解説:**
full-mesh BGP topology では、すべての node が他のすべての node と peering します。session 数は N * (N-1) / 2 として計算されます。ここで、N は node 数です。たとえば、10-node cluster には 10 * 9 / 2 = 45 の BGP session があります。これが、大規模な cluster で Route Reflector が推奨される理由です。

</details>

5. BGP Route Reflector の主な役割は何ですか？
   - A) BGP traffic を暗号化する
   - B) route を client に反映して BGP session 数を削減する
   - C) 悪意のある route をフィルタリングする
   - D) iBGP を eBGP に変換する

<details>
<summary>答えを表示</summary>

**回答: B) route を client に反映して BGP session 数を削減する**

**解説:**
Route Reflector は、client から route を受信し、それを他の client に「反映」することで、cluster で必要な BGP session 数を削減します。full mesh での N*(N-1)/2 session の代わりに、client は Route Reflector とだけ peering すればよくなります。これは大規模な cluster で BGP をスケーリングするために不可欠です。

</details>

6. Route Reflector configuration における Cluster ID の目的は何ですか？
   - A) Kubernetes cluster を識別する
   - B) Route Reflector 間の routing loop を防止する
   - C) node に IP address を割り当てる
   - D) BGP session を暗号化する

<details>
<summary>答えを表示</summary>

**回答: B) Route Reflector 間の routing loop を防止する**

**解説:**
Cluster ID は、複数の Route Reflector がデプロイされている場合に routing loop を防止するために使用されます。Route Reflector は自身の Cluster ID を持つ route を受信すると、その route がすでにこの RR cluster を通過したことを認識し、破棄します。同じ cluster 内のすべての Route Reflector は同じ Cluster ID を共有する必要があります。

</details>

7. BGPPeer resource の nodeSelector field は何を制御しますか？
   - A) BGP を使用できる Pod
   - B) BGP peering を確立する node
   - C) advertisement される route
   - D) peer を使用できる namespace

<details>
<summary>答えを表示</summary>

**回答: B) BGP peering を確立する node**

**解説:**
BGPPeer resource の `nodeSelector` field は、定義された peer との BGP session を確立する node を指定します。これは、cluster 内のすべての node ではなく、特定の rack 内の node のみがローカル ToR (Top of Rack) switch と peering すべき rack-aware peering で役立ちます。

</details>

8. 自動 node-to-node mesh を無効にする BGPConfiguration setting はどれですか？
   - A) meshEnabled: false
   - B) nodeToNodeMeshEnabled: false
   - C) disableMesh: true
   - D) bgpMesh: disabled

<details>
<summary>答えを表示</summary>

**回答: B) nodeToNodeMeshEnabled: false**

**解説:**
BGPConfiguration resource で `nodeToNodeMeshEnabled: false` を設定すると、すべての node 間の自動 full-mesh BGP peering が無効になります。full mesh は不要になり、大規模な deployment ではオーバーヘッドが発生するため、Route Reflector または外部 BGP peering を使用する場合にこれを設定する必要があります。

</details>

9. Calico はどの種類の Service IP を BGP 経由で advertisement できますか？
   - A) ClusterIPs のみ
   - B) LoadBalancer IPs のみ
   - C) ClusterIPs、ExternalIPs、LoadBalancer IPs
   - D) NodePort Service のみ

<details>
<summary>答えを表示</summary>

**回答: C) ClusterIPs、ExternalIPs、LoadBalancer IPs**

**解説:**
Calico は、BGP 経由で複数種類の Service IP を advertisement できます。具体的には、ClusterIPs（内部 Service IP）、ExternalIPs（Service に割り当てられた外部 IP）、LoadBalancer IPs です。これは BGPConfiguration resource で、それぞれ `serviceClusterIPs`、`serviceExternalIPs`、`serviceLoadBalancerIPs` field を使用して設定します。

</details>

10. Calico における BGP community の目的は何ですか？
    - A) access control 用の user group を作成する
    - B) policy decision 用の metadata を route にタグ付けする
    - C) 特定の route を暗号化する
    - D) routing table を圧縮する

<details>
<summary>答えを表示</summary>

**回答: B) policy decision 用の metadata を route にタグ付けする**

**解説:**
BGP community は、router が policy decision を行うために使用できる route に付加されたタグです。Calico では、advertisement される prefix に community tag を設定でき、downstream router はこれらのタグに基づいて特定の policy（traffic engineering や filtering など）を適用できます。community は AS:value の組として表されます（例: 64512:100）。

</details>

11. Calico で BGP session を保護するために使用できる authentication method は何ですか？
    - A) TLS certificate
    - B) MD5 authentication
    - C) OAuth token
    - D) Kerberos

<details>
<summary>答えを表示</summary>

**回答: B) MD5 authentication**

**解説:**
Calico は、BGP session を保護するための MD5 authentication をサポートしています。これは、peer 間の BGP message を authentication する TCP MD5 signature option です。暗号化は提供しませんが、認可されていない device が node と BGP session を確立することを防ぎます。password は BGPPeer resource で設定します。

</details>

12. BGP context における Graceful Restart とは何ですか？
    - A) configuration を失わずに BGP を再起動する方法
    - B) BGP daemon の再起動中に forwarding state を維持する mechanism
    - C) 新しい BGP peer を段階的に追加する方法
    - D) route withdrawal を遅延させる技術

<details>
<summary>答えを表示</summary>

**回答: B) BGP daemon の再起動中に forwarding state を維持する mechanism**

**解説:**
Graceful Restart は、BGP daemon の再起動中も forwarding plane の動作を継続できる BGP capability です。再起動する router は peer に再起動中であることを通知し、peer はその router からの route を猶予期間中維持します。これにより、software update や短時間の failure 中の traffic disruption を防止します。

</details>

13. BIRD daemon で BGP protocol status を確認するために使用する command は何ですか？
    - A) bird status
    - B) birdcl show protocols
    - C) bird show peers
    - D) birdctl status bgp

<details>
<summary>答えを表示</summary>

**回答: B) birdcl show protocols**

**解説:**
`birdcl show protocols` command は、BIRD daemon 内のすべての BGP protocol の status を表示します。これにより、BGP session が確立されているか、peer state、route exchange statistics を確認できます。ほかに、routing table を表示する `birdcl show route` や、詳細な session 情報を表示する `birdcl show protocols all <name>` も便利な command です。

</details>

14. Spine-Leaf data center topology において、Calico node は通常どのように peering すべきですか？
    - A) すべての node がすべての Spine switch と peering する
    - B) node がローカル ToR (Leaf) switch と peering する
    - C) master node のみがネットワークインフラストラクチャと peering する
    - D) node が switch を介さず直接相互に peering する

<details>
<summary>答えを表示</summary>

**回答: B) node がローカル ToR (Leaf) switch と peering する**

**解説:**
Spine-Leaf topology では、Calico node は通常、ローカル Top-of-Rack (ToR/Leaf) switch と peering します。次に Leaf switch が Spine switch と peering します。これは data center network の階層設計に従うものであり、BGPPeer resource の nodeSelector を使用して、node が自身の rack の ToR switch とのみ peering することを保証します。

</details>

15. nodeToNodeMeshEnabled が true の状態で Route Reflector も設定すると、何が起こりますか？
    - A) Route Reflector が優先され、mesh は無効になる
    - B) mesh と Route Reflector の両方の session が確立される（最適ではない）
    - C) configuration error となり、Calico は起動に失敗する
    - D) Route Reflector は無視される

<details>
<summary>答えを表示</summary>

**回答: B) mesh と Route Reflector の両方の session が確立される（最適ではない）**

**解説:**
Route Reflector が設定されているにもかかわらず nodeToNodeMeshEnabled が true のままである場合、full mesh session と Route Reflector session の両方が確立されます。これは最適ではなく、無駄です。Route Reflector を使用する場合は、`nodeToNodeMeshEnabled: false` を設定して自動 mesh を無効にし、route distribution を Route Reflector のみに依存する必要があります。

</details>

---

[学習資料に戻る](../../../networking/calico/04-bgp-deep-dive.md) | [前のクイズ: Networking Modes](./03-networking-modes-quiz.md) | [次のクイズ: Network Policy](./05-network-policy-quiz.md)
